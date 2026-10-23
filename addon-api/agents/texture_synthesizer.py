"""
Texture Synthesizer Agent - AI-powered texture generation with PBR support.

Generates professional textures including:
- Albedo, Normal, Roughness, Metallic, AO, Emission maps
- Style presets: Faithful, Vanilla+, RTX/PBR, Anime, Medieval, Modern
- Texture atlasing for performance
- Custom UI textures (itzriyo157-style buttons, radial menus, HUDs)
- Resolution scaling (16-256px) per device tier
"""
from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from core.state import (
    VersionedAddonState,
    GenerationStatus,
    AssetType,
    TextureAsset,
    DeviceTier,
)
from core.versioned_state import VPPerformanceProfile
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


class TextureStyle(str, Enum):
    """Texture style presets."""
    FAITHFUL = "faithful"           # Canon-accurate
    VANILLA_PLUS = "vanilla_plus"   # Minecraft style, enhanced
    RTX_PBR = "rtx_pbr"             # Full PBR maps
    ANIME_CEL = "anime_cel"         # Cel-shaded, toon outlines
    MEDIEVAL = "medieval"           # Hand-painted fantasy
    MODERN = "modern"               # Photo-realistic
    CUSTOM = "custom"               # User reference images


class TextureType(str, Enum):
    """Types of textures to generate."""
    ENTITY = "entity"
    ITEM = "item"
    BLOCK = "block"
    UI_BUTTON = "ui_button"
    UI_PANEL = "ui_panel"
    UI_HUD = "ui_hud"
    UI_RADIAL = "ui_radial"
    PARTICLE = "particle"
    GUI_ICON = "gui_icon"
    PAINTING = "painting"


@dataclass
class PBRMaps:
    """Complete PBR texture set."""
    albedo: Optional[Image.Image] = None
    normal: Optional[Image.Image] = None
    roughness: Optional[Image.Image] = None
    metallic: Optional[Image.Image] = None
    ao: Optional[Image.Image] = None  # Ambient Occlusion
    emission: Optional[Image.Image] = None
    height: Optional[Image.Image] = None  # Displacement/Parallax


@dataclass
class TextureSpec:
    """Specification for a texture to generate."""
    name: str
    texture_type: TextureType
    style: TextureStyle = TextureStyle.VANILLA_PLUS
    resolution: int = 64
    description: str = ""
    reference_images: list[str] = field(default_factory=list)  # Base64 or paths
    pbr_maps: list[str] = field(default_factory=lambda: ["albedo", "normal", "roughness"])
    color_palette: list[str] = field(default_factory=list)  # Hex colors
    metadata: dict = field(default_factory=dict)


@dataclass
class GeneratedTextureSet:
    """Result of texture generation."""
    spec: TextureSpec
    pbr: PBRMaps
    atlas_coords: dict = field(default_factory=dict)  # For atlasing
    generation_time: float = 0.0
    model_used: str = ""


class TextureSynthesizer:
    """
    Generates professional textures for Minecraft Bedrock addons.
    Supports PBR, style presets, atlasing, and custom UI.
    """

    def __init__(self, output_dir: str = "./generated_textures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = get_router()
        self.style_prompts = self._load_style_prompts()

    def _load_style_prompts(self) -> dict[TextureStyle, str]:
        """Load style-specific generation prompts."""
        return {
            TextureStyle.FAITHFUL: "Faithful to source material, canon-accurate colors and details, clean edges",
            TextureStyle.VANILLA_PLUS: "Minecraft vanilla style, 16x aesthetic but enhanced, subtle shading, noise texture",
            TextureStyle.RTX_PBR: "Physically based rendering, photorealistic materials, proper normal maps, roughness variation, metallic accuracy",
            TextureStyle.ANIME_CEL: "Anime cel-shaded style, flat colors with sharp toon outlines, dramatic lighting, vibrant palette",
            TextureStyle.MEDIEVAL: "Hand-painted medieval fantasy, worn textures, brush strokes, muted earth tones, weathered look",
            TextureStyle.MODERN: "Modern realistic, photo-sourced, high detail, contemporary materials",
            TextureStyle.CUSTOM: "Custom style based on reference images",
        }

    async def generate_textures(
        self,
        state: VersionedAddonState,
        specs: list[TextureSpec],
        target_tier: DeviceTier = DeviceTier.MID_64BIT_4GB,
    ) -> VersionedAddonState:
        """Generate textures for all specs."""
        current = state.get_current_version()
        if not current:
            return state

        state.set_status(GenerationStatus.GENERATING_TEXTURES, "texture_synthesizer",
                        f"Generating {len(specs)} texture sets for {target_tier.value}...")
        state.add_log(f"Starting texture generation: {len(specs)} specs, style={specs[0].style.value if specs else 'mixed'}")

        profile = VPPerformanceProfile.for_tier(target_tier)
        generated_sets = []

        for i, spec in enumerate(specs):
            # Adjust resolution for tier
            spec.resolution = min(spec.resolution, profile.texture_resolution)
            if not profile.use_pbr:
                spec.pbr_maps = ["albedo"]  # Only albedo for low tier

            state.add_log(f"Generating texture {i+1}/{len(specs)}: {spec.name} ({spec.resolution}px)")

            texture_set = await self._generate_texture_set(spec, profile)
            generated_sets.append(texture_set)

            # Save to disk
            await self._save_texture_set(texture_set, target_tier)

            # Create TextureAsset for version
            asset = self._create_texture_asset(texture_set, target_tier)
            current.add_texture(asset)

        # Generate atlas if beneficial
        if profile.atlas_textures and len(generated_sets) > 4:
            atlas = await self._create_atlas(generated_sets, target_tier)
            current.add_texture(atlas)
            state.add_log(f"Created texture atlas: {atlas.metadata.get('atlas_size', 'unknown')}")

        # Generate custom UI textures (itzriyo157 style)
        ui_textures = await self._generate_ui_textures(state, target_tier)
        for ui_tex in ui_textures:
            current.add_texture(ui_tex)

        state.set_status(GenerationStatus.GENERATING_TEXTURES, "texture_synthesizer",
                        f"Generated {len(generated_sets)} texture sets + {len(ui_textures)} UI textures")
        return state

    async def _generate_texture_set(self, spec: TextureSpec, profile: VPPerformanceProfile) -> GeneratedTextureSet:
        """Generate a complete texture set for one spec."""
        start_time = datetime.utcnow()

        # Build generation prompt
        prompt = self._build_generation_prompt(spec)

        # Use LLM to generate detailed texture description
        # In production, this would call an image generation API (Midjourney, DALL-E, Stable Diffusion)
        # For now, we create procedural textures as placeholders
        pbr = await self._generate_procedural_pbr(spec, profile)

        generation_time = (datetime.utcnow() - start_time).total_seconds()

        return GeneratedTextureSet(
            spec=spec,
            pbr=pbr,
            generation_time=generation_time,
            model_used="procedural_v1",
        )

    def _build_generation_prompt(self, spec: TextureSpec) -> str:
        """Build prompt for texture generation."""
        style_desc = self.style_prompts.get(spec.style, "")
        palette = f", color palette: {', '.join(spec.color_palette)}" if spec.color_palette else ""

        return f"""Generate a {spec.texture_type.value} texture for Minecraft Bedrock.
Name: {spec.name}
Description: {spec.description}
Style: {spec.style.value} - {style_desc}{palette}
Resolution: {spec.resolution}x{spec.resolution}
Required PBR maps: {', '.join(spec.pbr_maps)}
Reference: {spec.reference_images[:3] if spec.reference_images else 'None'}
"""

    async def _generate_procedural_pbr(self, spec: TextureSpec, profile: VPPerformanceProfile) -> PBRMaps:
        """Generate procedural PBR textures (placeholder for AI generation)."""
        res = spec.resolution
        pbr = PBRMaps()

        # Base color from palette or random
        base_color = self._get_base_color(spec)

        # Albedo - base color with noise
        pbr.albedo = self._create_albedo(res, base_color, spec.texture_type)

        # Normal map - simulated surface detail
        if "normal" in spec.pbr_maps:
            pbr.normal = self._create_normal_map(res, spec.texture_type)

        # Roughness - material roughness variation
        if "roughness" in spec.pbr_maps:
            pbr.roughness = self._create_roughness_map(res, spec.texture_type)

        # Metallic - metalness map
        if "metallic" in spec.pbr_maps:
            pbr.metallic = self._create_metallic_map(res, spec.texture_type)

        # AO - ambient occlusion
        if "ao" in spec.pbr_maps:
            pbr.ao = self._create_ao_map(res, spec.texture_type)

        # Emission - glowing parts
        if "emission" in spec.pbr_maps:
            pbr.emission = self._create_emission_map(res, spec)

        # Height - displacement
        if "height" in spec.pbr_maps:
            pbr.height = self._create_height_map(res, spec.texture_type)

        return pbr

    def _get_base_color(self, spec: TextureSpec) -> tuple[int, int, int]:
        """Get base color from palette or generate."""
        if spec.color_palette:
            hex_color = spec.color_palette[0].lstrip("#")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        # Default colors by type
        defaults = {
            TextureType.ENTITY: (100, 100, 100),
            TextureType.ITEM: (150, 150, 150),
            TextureType.BLOCK: (120, 120, 120),
            TextureType.UI_BUTTON: (60, 60, 80),
            TextureType.UI_PANEL: (40, 40, 50),
            TextureType.UI_HUD: (20, 20, 30),
            TextureType.UI_RADIAL: (50, 50, 70),
            TextureType.PARTICLE: (200, 200, 200),
            TextureType.GUI_ICON: (180, 180, 180),
        }
        return defaults.get(spec.texture_type, (128, 128, 128))

    def _create_albedo(self, res: int, color: tuple, tex_type: TextureType) -> Image.Image:
        """Create albedo/base color map."""
        img = Image.new("RGBA", (res, res), color + (255,))

        # Add procedural noise for vanilla feel
        noise = Image.effect_noise((res, res), 0.5).convert("L")
        noise = ImageEnhance.Brightness(noise).enhance(0.1)
        img = Image.composite(
            Image.new("RGBA", (res, res), tuple(min(255, c + 20) for c in color) + (255,)),
            img,
            noise
        )

        # Add type-specific details
        if tex_type == TextureType.UI_BUTTON:
            # Button style: gradient + border
            draw = ImageDraw.Draw(img)
            margin = res // 8
            draw.rounded_rectangle(
                [margin, margin, res-margin, res-margin],
                radius=res//6,
                outline=tuple(min(255, c + 60) for c in color) + (255,),
                width=max(1, res//32),
            )
            # Highlight
            draw.rounded_rectangle(
                [margin*2, margin*2, res-margin*2, res//2],
                radius=res//8,
                fill=(255, 255, 255, 30),
            )

        elif tex_type == TextureType.UI_RADIAL:
            # Radial menu base
            draw = ImageDraw.Draw(img)
            center = res // 2
            radius = res // 2 - res // 8
            draw.ellipse(
                [center-radius, center-radius, center+radius, center+radius],
                fill=tuple(min(255, c + 30) for c in color) + (200,),
                outline=tuple(min(255, c + 80) for c in color) + (255,),
                width=max(1, res//32),
            )

        return img

    def _create_normal_map(self, res: int, tex_type: TextureType) -> Image.Image:
        """Create normal map (simulated surface detail)."""
        # Flat normal (pointing up) = (128, 128, 255)
        img = Image.new("RGB", (res, res), (128, 128, 255))

        # Add noise for surface detail
        noise = Image.effect_noise((res, res), 0.3).convert("L")
        # Convert to normal perturbation
        normal_noise = Image.new("RGB", (res, res))
        for x in range(res):
            for y in range(res):
                n = noise.getpixel((x, y))
                # Perturb normal slightly
                dx = (n - 128) / 128 * 0.1
                dy = (n - 128) / 128 * 0.1
                normal_noise.putpixel((x, y), (
                    int(128 + dx * 127),
                    int(128 + dy * 127),
                    255,
                ))

        return Image.blend(img, normal_noise, 0.3).convert("RGBA")

    def _create_roughness_map(self, res: int, tex_type: TextureType) -> Image.Image:
        """Create roughness map (0=smooth, 1=rough)."""
        # Default roughness by type
        base_roughness = {
            TextureType.ENTITY: 0.7,
            TextureType.ITEM: 0.5,
            TextureType.BLOCK: 0.8,
            TextureType.UI_BUTTON: 0.3,
            TextureType.UI_PANEL: 0.4,
            TextureType.UI_HUD: 0.2,
            TextureType.UI_RADIAL: 0.3,
            TextureType.PARTICLE: 0.9,
        }.get(tex_type, 0.5)

        val = int(base_roughness * 255)
        img = Image.new("L", (res, res), val)

        # Add variation
        noise = Image.effect_noise((res, res), 0.5).convert("L")
        noise = ImageEnhance.Contrast(noise).enhance(0.3)
        img = Image.blend(img, noise, 0.3)

        return img.convert("RGBA")

    def _create_metallic_map(self, res: int, tex_type: TextureType) -> Image.Image:
        """Create metallic map (0=dielectric, 1=metal)."""
        base_metallic = {
            TextureType.ITEM: 0.8,  # Tools/weapons often metal
            TextureType.BLOCK: 0.1,
            TextureType.UI_BUTTON: 0.2,
        }.get(tex_type, 0.0)

        val = int(base_metallic * 255)
        return Image.new("L", (res, res), val).convert("RGBA")

    def _create_ao_map(self, res: int, tex_type: TextureType) -> Image.Image:
        """Create ambient occlusion map."""
        # Start with white (no occlusion)
        img = Image.new("L", (res, res), 255)

        # Add corner/edge darkening
        draw = ImageDraw.Draw(img)
        margin = res // 8
        for i in range(margin):
            alpha = int(255 * (1 - i / margin * 0.5))
            draw.rectangle([i, i, res-i-1, res-i-1], outline=alpha)

        return img.convert("RGBA")

    def _create_emission_map(self, res: int, spec: TextureSpec) -> Image.Image:
        """Create emission map (glowing parts)."""
        img = Image.new("RGBA", (res, res), (0, 0, 0, 0))

        # Add glow for magical/energy items
        if "magic" in spec.description.lower() or "energy" in spec.description.lower():
            draw = ImageDraw.Draw(img)
            center = res // 2
            for r in range(res//4, 0, -1):
                alpha = int(255 * (r / (res//4)) ** 2)
                draw.ellipse(
                    [center-r, center-r, center+r, center+r],
                    outline=(0, 200, 255, alpha),
                )

        return img

    def _create_height_map(self, res: int, tex_type: TextureType) -> Image.Image:
        """Create height/displacement map."""
        img = Image.new("L", (res, res), 128)  # Mid-gray = flat

        # Add subtle height variation
        noise = Image.effect_noise((res, res), 0.3).convert("L")
        noise = ImageEnhance.Brightness(noise).enhance(0.2)
        img = Image.blend(img, noise, 0.5)

        return img.convert("RGBA")

    def _create_texture_asset(self, texture_set: GeneratedTextureSet, tier: DeviceTier) -> TextureAsset:
        """Create TextureAsset from generated set."""
        spec = texture_set.spec
        pbr = texture_set.pbr

        # Save albedo as primary texture
        primary = pbr.albedo or Image.new("RGBA", (spec.resolution, spec.resolution), (128, 128, 128, 255))

        # Convert to bytes
        buffer = BytesIO()
        primary.save(buffer, format="PNG")
        texture_bytes = buffer.getvalue()

        # Build metadata with all PBR map info
        metadata = {
            "name": spec.name,
            "texture_type": spec.texture_type.value,
            "style": spec.style.value,
            "width": spec.resolution,
            "height": spec.resolution,
            "pbr_maps": {
                "albedo": True,
                "normal": pbr.normal is not None,
                "roughness": pbr.roughness is not None,
                "metallic": pbr.metallic is not None,
                "ao": pbr.ao is not None,
                "emission": pbr.emission is not None,
                "height": pbr.height is not None,
            },
            "tier": tier.value,
            "generation_time": texture_set.generation_time,
            "model_used": texture_set.model_used,
        }

        return TextureAsset(
            texture_id=spec.name,
            texture_data=texture_bytes,
            metadata=metadata,
        )

    async def _save_texture_set(self, texture_set: GeneratedTextureSet, tier: DeviceTier):
        """Save texture set to disk."""
        spec = texture_set.spec
        pbr = texture_set.pbr

        tier_dir = self.output_dir / tier.value / spec.texture_type.value / spec.name
        tier_dir.mkdir(parents=True, exist_ok=True)

        map_names = {
            "albedo": pbr.albedo,
            "normal": pbr.normal,
            "roughness": pbr.roughness,
            "metallic": pbr.metallic,
            "ao": pbr.ao,
            "emission": pbr.emission,
            "height": pbr.height,
        }

        for name, img in map_names.items():
            if img:
                img.save(tier_dir / f"{name}.png")

        # Save spec
        with open(tier_dir / "spec.json", "w") as f:
            json.dump({
                "name": spec.name,
                "type": spec.texture_type.value,
                "style": spec.style.value,
                "resolution": spec.resolution,
                "description": spec.description,
                "pbr_maps": list(map_names.keys()),
            }, f, indent=2)

    async def _create_atlas(self, texture_sets: list[GeneratedTextureSet], tier: DeviceTier) -> TextureAsset:
        """Create texture atlas from multiple textures."""
        # Simple grid atlas
        count = len(texture_sets)
        cols = int(count ** 0.5) + 1
        rows = (count + cols - 1) // cols
        tile_size = texture_sets[0].spec.resolution
        atlas_size = (cols * tile_size, rows * tile_size)

        atlas = Image.new("RGBA", atlas_size, (0, 0, 0, 0))
        coords = {}

        for i, ts in enumerate(texture_sets):
            x = (i % cols) * tile_size
            y = (i // cols) * tile_size
            img = ts.pbr.albedo
            if img:
                atlas.paste(img, (x, y))
            coords[ts.spec.name] = {
                "x": x, "y": y, "width": tile_size, "height": tile_size,
                "u1": x / atlas_size[0], "v1": y / atlas_size[1],
                "u2": (x + tile_size) / atlas_size[0], "v2": (y + tile_size) / atlas_size[1],
            }

        buffer = BytesIO()
        atlas.save(buffer, format="PNG")

        return TextureAsset(
            texture_id=f"atlas_{tier.value}",
            texture_data=buffer.getvalue(),
            metadata={
                "name": f"atlas_{tier.value}",
                "texture_type": "atlas",
                "atlas_size": atlas_size,
                "tile_size": tile_size,
                "coords": coords,
                "tile_count": count,
                "tier": tier.value,
            },
        )

    async def _generate_ui_textures(self, state: VersionedAddonState, tier: DeviceTier) -> list[TextureAsset]:
        """Generate itzriyo157-style custom UI textures."""
        current = state.get_current_version()
        if not current or not current.lore:
            return []

        theme = state.theme
        profile = VPPerformanceProfile.for_tier(tier)
        res = min(64, profile.texture_resolution)

        ui_specs = [
            TextureSpec(
                name="ui_button_primary",
                texture_type=TextureType.UI_BUTTON,
                style=TextureStyle.VANILLA_PLUS,
                resolution=res,
                description=f"Primary action button for {theme} - glowing, animated states",
                color_palette=["#1a1a2e", "#16213e", "#0f3460", "#e94560"],
            ),
            TextureSpec(
                name="ui_button_secondary",
                texture_type=TextureType.UI_BUTTON,
                style=TextureStyle.VANILLA_PLUS,
                resolution=res,
                description=f"Secondary button for {theme} - subdued",
                color_palette=["#1a1a2e", "#16213e", "#0f3460"],
            ),
            TextureSpec(
                name="ui_radial_menu",
                texture_type=TextureType.UI_RADIAL,
                style=TextureStyle.VANILLA_PLUS,
                resolution=res * 2,
                description=f"Radial menu base for {theme} - 8 segments, center hub",
                color_palette=["#0d0d1a", "#1a1a2e", "#16213e", "#e94560"],
            ),
            TextureSpec(
                name="ui_hud_background",
                texture_type=TextureType.UI_HUD,
                style=TextureStyle.VANILLA_PLUS,
                resolution=res,
                description=f"HUD background panel for {theme} - semi-transparent",
                color_palette=["#000000", "#1a1a2e"],
            ),
            TextureSpec(
                name="ui_slot_empty",
                texture_type=TextureType.GUI_ICON,
                style=TextureStyle.VANILLA_PLUS,
                resolution=res,
                description=f"Empty inventory slot for {theme}",
                color_palette=["#3d3d5c"],
            ),
            TextureSpec(
                name="ui_slot_filled",
                texture_type=TextureType.GUI_ICON,
                style=TextureStyle.VANILLA_PLUS,
                resolution=res,
                description=f"Filled inventory slot highlight for {theme}",
                color_palette=["#e94560", "#ff6b6b"],
            ),
        ]

        ui_assets = []
        for spec in ui_specs:
            texture_set = await self._generate_texture_set(spec, profile)
            asset = self._create_texture_asset(texture_set, tier)
            ui_assets.append(asset)
            await self._save_texture_set(texture_set, tier)

        return ui_assets

    def texture_to_base64(self, texture: TextureAsset) -> str:
        """Convert texture to base64 for web preview."""
        return base64.b64encode(texture.texture_data).decode('utf-8')


# Singleton
_synthesizer: TextureSynthesizer | None = None


def get_texture_synthesizer() -> TextureSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = TextureSynthesizer()
    return _synthesizer
