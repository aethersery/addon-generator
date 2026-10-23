"""
Particle Designer Agent - Custom particle effects with shaders.

Creates magical, combat, environmental, and UI particle effects:
- Custom particle textures and shaders
- Molang-driven particle behavior
- Physics simulation (gravity, wind, collision)
- Performance budgets per device tier
- Integration with animations and render controllers
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from core.state import (
    VersionedAddonState,
    GenerationStatus,
    AssetType,
    GeneratedAsset,
    LoreEntity,
    LoreMechanic,
    DeviceTier,
)
from core.versioned_state import VPPerformanceProfile
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class ParticleSpec:
    """Specification for a particle effect."""
    name: str
    effect_type: str  # "magic", "combat", "environmental", "ui", "trail", "explosion"
    description: str
    texture: str = "particle_smoke"
    color_begin: tuple[float, float, float, float] = (1, 1, 1, 1)
    color_end: tuple[float, float, float, float] = (1, 1, 1, 0)
    size_begin: float = 0.5
    size_end: float = 0.0
    lifetime: float = 1.0
    emission_rate: float = 10.0
    emitter_shape: str = "point"  # point, sphere, box, circle, line
    emitter_size: tuple[float, float, float] = (0, 0, 0)
    gravity: float = 0.0
    drag: float = 0.0
    wind: tuple[float, float, float] = (0, 0, 0)
    molang_driven: bool = True
    shader: str = "particles.blend"
    render_mode: str = "additive"  # additive, alpha_blend, opaque


@dataclass
class ParticleSystem:
    """Complete particle system for an addon."""
    name: str
    particles: dict[str, dict] = field(default_factory=dict)  # name -> particle.json
    particle_textures: list[str] = field(default_factory=list)
    shaders: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class ParticleDesigner:
    """
    Designs custom particle effects for Bedrock addons.
    Molang-driven, shader-enhanced, performance budgeted.
    """

    def __init__(self):
        self.router = get_router()
        self.base_particles = self._load_base_particles()

    def _load_base_particles(self) -> dict[str, dict]:
        """Load base particle templates."""
        return {
            "magic_sparkle": {
                "texture": "particle_glint",
                "color_begin": (0.5, 0.2, 1.0, 1.0),
                "color_end": (0.2, 0.0, 0.5, 0.0),
                "size_begin": 0.15,
                "size_end": 0.0,
                "lifetime": 0.8,
                "emission_rate": 20,
                "gravity": -0.5,
                "shader": "particles.glint",
            },
            "dark_magic": {
                "texture": "particle_smoke",
                "color_begin": (0.1, 0.0, 0.2, 0.8),
                "color_end": (0.0, 0.0, 0.1, 0.0),
                "size_begin": 0.4,
                "size_end": 0.8,
                "lifetime": 2.0,
                "emission_rate": 15,
                "gravity": -0.2,
                "shader": "particles.dark",
            },
            "fire": {
                "texture": "particle_flame",
                "color_begin": (1.0, 0.5, 0.1, 1.0),
                "color_end": (1.0, 0.1, 0.0, 0.0),
                "size_begin": 0.3,
                "size_end": 0.6,
                "lifetime": 0.6,
                "emission_rate": 30,
                "gravity": -0.8,
                "shader": "particles.flame",
            },
            "blood": {
                "texture": "particle_droplet",
                "color_begin": (0.6, 0.0, 0.0, 1.0),
                "color_end": (0.4, 0.0, 0.0, 0.0),
                "size_begin": 0.2,
                "size_end": 0.1,
                "lifetime": 1.0,
                "emission_rate": 25,
                "gravity": 1.0,
                "drag": 0.5,
            },
            "electric": {
                "texture": "particle_lightning",
                "color_begin": (0.2, 0.6, 1.0, 1.0),
                "color_end": (0.0, 0.2, 0.8, 0.0),
                "size_begin": 0.2,
                "size_end": 0.0,
                "lifetime": 0.3,
                "emission_rate": 40,
                "gravity": 0.0,
                "shader": "particles.electric",
            },
            "heal": {
                "texture": "particle_heart",
                "color_begin": (0.2, 1.0, 0.3, 1.0),
                "color_end": (0.1, 0.5, 0.1, 0.0),
                "size_begin": 0.3,
                "size_end": 0.0,
                "lifetime": 1.5,
                "emission_rate": 10,
                "gravity": -0.5,
                "shader": "particles.glint",
            },
            "void": {
                "texture": "particle_void",
                "color_begin": (0.05, 0.0, 0.15, 0.9),
                "color_end": (0.0, 0.0, 0.0, 0.0),
                "size_begin": 0.5,
                "size_end": 1.0,
                "lifetime": 3.0,
                "emission_rate": 8,
                "gravity": 0.0,
                "shader": "particles.void",
            },
        }

    async def design_particles(
        self,
        state: VersionedAddonState,
        target_tier: DeviceTier = DeviceTier.MID_64BIT_4GB,
    ) -> VersionedAddonState:
        """Design particle effects for the addon."""
        current = state.get_current_version()
        if not current or not current.lore:
            return state

        state.set_status(GenerationStatus.GENERATING_RP, "particle_designer",
                        f"Designing particles for {target_tier.value}...")
        state.add_log("Creating custom particle effects with shaders...")

        profile = VPPerformanceProfile.for_tier(target_tier)
        particle_system = await self._design_particle_system(state, profile)

        # Create assets
        self._create_particle_assets(current, particle_system)

        state.set_status(GenerationStatus.GENERATING_RP, "particle_designer",
                        f"Created {len(particle_system.particles)} particle effects")
        return state

    async def _design_particle_system(
        self,
        state: VersionedAddonState,
        profile: VPPerformanceProfile,
    ) -> ParticleSystem:
        """Design complete particle system based on lore."""
        current = state.get_current_version()
        lore = current.lore

        # Determine needed particles from entities, mechanics, items
        specs = []

        # Entity-based particles
        for entity in lore.entities:
            specs.extend(self._entity_particles(entity))

        # Mechanic-based particles
        for mechanic in lore.mechanics:
            specs.extend(self._mechanic_particles(mechanic))

        # Item-based particles
        for item in lore.items:
            specs.extend(self._item_particles(item))

        # UI particles
        specs.extend(self._ui_particles(state.theme))

        # Limit for low tier
        if profile.max_particles < 50:
            specs = specs[:profile.max_particles // 5]

        # Generate each particle
        particles = {}
        textures_needed = set()
        shaders_needed = set()

        for spec in specs:
            particle = await self._generate_particle(spec, profile)
            particles[spec.name] = particle
            textures_needed.add(spec.texture)
            if spec.shader != "particles.blend":
                shaders_needed.add(spec.shader)

        return ParticleSystem(
            name=f"{state.theme}_particles",
            particles=particles,
            particle_textures=list(textures_needed),
            shaders=list(shaders_needed),
            metadata={
                "total_particles": len(particles),
                "textures": list(textures_needed),
                "shaders": list(shaders_needed),
                "tier": profile.tier.value if hasattr(profile, 'tier') else "unknown",
            }
        )

    def _entity_particles(self, entity: LoreEntity) -> list[ParticleSpec]:
        """Generate particle specs from entity."""
        specs = []
        name_base = entity.name

        # Death particles
        specs.append(ParticleSpec(
            name=f"{name_base}_death",
            effect_type="combat",
            description=f"Death effect for {entity.display_name}",
            texture="particle_smoke",
            color_begin=(0.3, 0.1, 0.1, 1),
            color_end=(0.1, 0.0, 0.0, 0),
            size_begin=0.5,
            size_end=1.0,
            lifetime=2.0,
            emission_rate=30,
            gravity=0.0,
        ))

        # Hit particles
        specs.append(ParticleSpec(
            name=f"{name_base}_hit",
            effect_type="combat",
            description=f"Hit effect for {entity.display_name}",
            texture="particle_spark",
            color_begin=(1.0, 0.8, 0.3, 1),
            color_end=(1.0, 0.3, 0.0, 0),
            size_begin=0.1,
            size_end=0.0,
            lifetime=0.3,
            emission_rate=15,
            gravity=0.0,
        ))

        # Ability particles based on abilities
        for ability in entity.abilities:
            if "shadow" in ability.lower():
                specs.append(ParticleSpec(
                    name=f"{name_base}_{ability.lower().replace(' ', '_')}",
                    effect_type="magic",
                    description=f"{ability} particle effect",
                    **self.base_particles["dark_magic"],
                ))
            elif "fire" in ability.lower():
                specs.append(ParticleSpec(
                    name=f"{name_base}_{ability.lower().replace(' ', '_')}",
                    effect_type="magic",
                    description=f"{ability} particle effect",
                    **self.base_particles["fire"],
                ))
            elif "lightning" in ability.lower() or "electric" in ability.lower():
                specs.append(ParticleSpec(
                    name=f"{name_base}_{ability.lower().replace(' ', '_')}",
                    effect_type="magic",
                    description=f"{ability} particle effect",
                    **self.base_particles["electric"],
                ))
            elif "heal" in ability.lower() or "regen" in ability.lower():
                specs.append(ParticleSpec(
                    name=f"{name_base}_{ability.lower().replace(' ', '_')}",
                    effect_type="magic",
                    description=f"{ability} particle effect",
                    **self.base_particles["heal"],
                ))

        return specs

    def _mechanic_particles(self, mechanic: LoreMechanic) -> list[ParticleSpec]:
        """Generate particle specs from mechanic."""
        specs = []
        name_base = mechanic.name

        # Generic mechanic particles
        specs.append(ParticleSpec(
            name=f"{name_base}_active",
            effect_type="magic",
            description=f"Active effect for {mechanic.name}",
            texture="particle_glint",
            color_begin=(0.4, 0.2, 0.8, 0.8),
            color_end=(0.1, 0.0, 0.3, 0),
            size_begin=0.3,
            size_end=0.6,
            lifetime=1.0,
            emission_rate=10,
            gravity=-0.3,
            molang_driven=True,
        ))

        return specs

    def _item_particles(self, item: Any) -> list[ParticleSpec]:
        """Generate particle specs from item."""
        specs = []
        name_base = item.name if hasattr(item, 'name') else str(item)

        # Enchanted/legendary items
        if hasattr(item, 'rarity') and item.rarity in ["epic", "legendary"]:
            specs.append(ParticleSpec(
                name=f"{name_base}_glint",
                effect_type="magic",
                description=f"Legendary glint for {name_base}",
                **self.base_particles["magic_sparkle"],
            ))

        # Consumables
        if hasattr(item, 'item_type') and item.item_type == "consumable":
            specs.append(ParticleSpec(
                name=f"{name_base}_consume",
                effect_type="magic",
                description=f"Consume effect for {name_base}",
                **self.base_particles["heal"],
            ))

        return specs

    def _ui_particles(self, theme: str) -> list[ParticleSpec]:
        """Generate UI particle specs."""
        specs = []

        # Button press ripple
        specs.append(ParticleSpec(
            name="ui_button_ripple",
            effect_type="ui",
            description="Button press ripple effect",
            texture="particle_circle",
            color_begin=(1, 1, 1, 0.5),
            color_end=(1, 1, 1, 0),
            size_begin=0.5,
            size_end=1.5,
            lifetime=0.2,
            emission_rate=1,
            emitter_shape="circle",
            emitter_size=(0.5, 0, 0.5),
            gravity=0,
        ))

        # Radial menu open
        specs.append(ParticleSpec(
            name="ui_radial_open",
            effect_type="ui",
            description="Radial menu open animation",
            texture="particle_arc",
            color_begin=(0.3, 0.1, 0.6, 0.8),
            color_end=(0.1, 0.0, 0.2, 0),
            size_begin=0.2,
            size_end=1.0,
            lifetime=0.4,
            emission_rate=8,
            emitter_shape="circle",
            emitter_size=(1.0, 0, 1.0),
            gravity=0,
        ))

        # HUD resource gain
        specs.append(ParticleSpec(
            name="ui_resource_gain",
            effect_type="ui",
            description="Resource counter increase",
            texture="particle_coin",
            color_begin=(1, 0.8, 0.2, 1),
            color_end=(1, 0.5, 0, 0),
            size_begin=0.4,
            size_end=0.0,
            lifetime=0.8,
            emission_rate=5,
            emitter_shape="point",
            gravity=-0.5,
        ))

        return specs

    async def _generate_particle(self, spec: ParticleSpec, profile: VPPerformanceProfile) -> dict:
        """Generate particle.json for a spec."""
        # Adjust for performance tier
        emission_rate = spec.emission_rate
        lifetime = spec.lifetime

        if profile.tier == "low_32bit_2gb":
            emission_rate *= 0.3
            lifetime *= 0.5
        elif profile.tier == "mid_64bit_4gb":
            emission_rate *= 0.7
            lifetime *= 0.8

        # Build molang expressions for dynamic behavior
        molang = {}
        if spec.molang_driven:
            molang = {
                "scale": "variable.particle_size * math.sin(query.life_time * 10) * 0.5 + 1",
                "alpha": "math.lerp(1, 0, query.life_time / query.lifetime)",
                "color": {
                    "r": f"math.lerp({spec.color_begin[0]}, {spec.color_end[0]}, query.life_time / query.lifetime)",
                    "g": f"math.lerp({spec.color_begin[1]}, {spec.color_end[1]}, query.life_time / query.lifetime)",
                    "b": f"math.lerp({spec.color_begin[2]}, {spec.color_end[2]}, query.life_time / query.lifetime)",
                    "a": f"math.lerp({spec.color_begin[3]}, {spec.color_end[3]}, query.life_time / query.lifetime)",
                },
            }

        # Emitter configuration
        emitter = {
            "type": spec.emitter_shape,
            "rate": emission_rate,
            "lifetime": lifetime,
            "lifetime_multiplier": 1.0,
        }

        if spec.emitter_shape != "point":
            emitter["size"] = list(spec.emitter_size)

        # Physics
        physics = {}
        if spec.gravity != 0:
            physics["gravity"] = spec.gravity
        if spec.drag != 0:
            physics["drag"] = spec.drag
        if any(spec.wind):
            physics["wind"] = list(spec.wind)

        return {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {
                    "identifier": f"particle.{spec.name}",
                    "basic_render_parameters": {
                        "material": spec.shader,
                        "texture": spec.texture,
                        "render_mode": spec.render_mode,
                    },
                },
                "components": {
                    "minecraft:emitter_rate_steady": emitter,
                    "minecraft:emitter_lifetime_once": {"lifetime": lifetime} if spec.emitter_shape == "point" else {},
                    "minecraft:emitter_shape_point": {} if spec.emitter_shape == "point" else
                    "minecraft:emitter_shape_sphere": {"radius": spec.emitter_size[0]} if spec.emitter_shape == "sphere" else
                    "minecraft:emitter_shape_box": {"half_dimensions": list(spec.emitter_size)} if spec.emitter_shape == "box" else
                    "minecraft:emitter_shape_circle": {"radius": spec.emitter_size[0]} if spec.emitter_shape == "circle" else {},
                    "minecraft:particle_lifetime_expression": {"max_lifetime": lifetime},
                    "minecraft:particle_initial_speed": 1.0,
                    "minecraft:particle_motion_dynamic": physics if physics else {},
                    "minecraft:particle_appearance_billboard": {
                        "size": [spec.size_begin, spec.size_end],
                        "facing_camera_mode": "lookat_xyz",
                        "uv": {"texture_width": 16, "texture_height": 16, "uv": [0, 0], "uv_size": [16, 16]},
                    },
                    "minecraft:particle_appearance_tinting": {
                        "color": {
                            "interpolant": "query.life_time / query.lifetime",
                            "gradient": {
                                "0.0": list(spec.color_begin),
                                "1.0": list(spec.color_end),
                            }
                        }
                    },
                } | ({"minecraft:particle_molang": molang} if molang else {}),
            }
        }

    def _create_particle_assets(self, version: 'AddonVersion', system: ParticleSystem):
        """Create GeneratedAsset entries for particles."""
        for name, particle_data in system.particles.items():
            version.rp_assets.append(GeneratedAsset(
                asset_type=AssetType.PARTICLE,
                content=particle_data,
                metadata={"name": name}
            ))

        # Note: textures and shaders would be generated by TextureSynthesizer
        # Here we just track what's needed
        version.metadata = version.metadata or {}
        version.metadata["particle_textures_needed"] = system.particle_textures
        version.metadata["particle_shaders_needed"] = system.shaders


# Singleton
_particle_designer: ParticleDesigner | None = None


def get_particle_designer() -> ParticleDesigner:
    global _particle_designer
    if _particle_designer is None:
        _particle_designer = ParticleDesigner()
    return _particle_designer
