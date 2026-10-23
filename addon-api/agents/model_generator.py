"""
Model Generator Agent - Professional Blockbench-compatible 3D models.

Generates optimized geo.json models with:
- LOD (Level of Detail) variants
- Bone merging for performance
- Animation-ready rigging
- Molang-driven animations
- Render controller integration
- Particle attachment points
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
    DeviceTier,
)
from core.versioned_state import VPPerformanceProfile
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class ModelSpec:
    """Specification for a model to generate."""
    name: str
    entity_type: str  # "mob", "boss", "item", "block", "projectile"
    description: str
    geometry_type: str = "humanoid"  # humanoid, quadruped, flying, serpent, custom
    size: tuple[float, float, float] = (1.0, 1.0, 1.0)  # width, height, depth
    texture_size: tuple[int, int] = (64, 64)
    bones: list[dict] = field(default_factory=list)
    animations: list[str] = field(default_factory=list)  # Animation names to support
    particles: list[dict] = field(default_factory=list)  # Particle attachment points
    lod_levels: int = 1  # 1=single, 2=high/low, 3=high/med/low
    merge_bones: bool = True
    optimize_for_tier: str = "mid_64bit_4gb"


@dataclass
class GeneratedModel:
    """Generated model with all LODs and metadata."""
    spec: ModelSpec
    geometry: dict  # geo.json format
    lods: list[dict] = field(default_factory=list)  # LOD geometries
    animations: dict = field(default_factory=dict)  # animation_name -> animation.json
    anim_controller: dict = field(default_factory=dict)  # animation_controller.json
    render_controller: dict = field(default_factory=dict)  # render_controller.json
    metadata: dict = field(default_factory=dict)


class ModelGenerator:
    """
    Generates professional Blockbench-compatible models for Bedrock.
    Supports LOD, bone optimization, animation-ready rigs.
    """

    def __init__(self):
        self.router = get_router()
        self.base_rigs = self._load_base_rigs()

    def _load_base_rigs(self) -> dict[str, dict]:
        """Load base rig templates for common entity types."""
        return {
            "humanoid": {
                "bones": [
                    {"name": "root", "pivot": [0, 0, 0], "cubes": []},
                    {"name": "body", "parent": "root", "pivot": [0, 12, 0], "cubes": [{"origin": [-4, 0, -2], "size": [8, 12, 4], "uv": [0, 0]}]},
                    {"name": "head", "parent": "body", "pivot": [0, 24, 0], "cubes": [{"origin": [-4, 0, -4], "size": [8, 8, 8], "uv": [0, 16]}]},
                    {"name": "left_arm", "parent": "body", "pivot": [5, 22, 0], "cubes": [{"origin": [-1, -2, -2], "size": [4, 12, 4], "uv": [32, 48]}]},
                    {"name": "right_arm", "parent": "body", "pivot": [-5, 22, 0], "cubes": [{"origin": [-3, -2, -2], "size": [4, 12, 4], "uv": [40, 16]}]},
                    {"name": "left_leg", "parent": "root", "pivot": [2, 12, 0], "cubes": [{"origin": [-2, -12, -2], "size": [4, 12, 4], "uv": [16, 48]}]},
                    {"name": "right_leg", "parent": "root", "pivot": [-2, 12, 0], "cubes": [{"origin": [-2, -12, -2], "size": [4, 12, 4], "uv": [0, 48]}]},
                ],
                "animations": ["idle", "walk", "run", "attack", "hurt", "death", "sleep"],
            },
            "quadruped": {
                "bones": [
                    {"name": "root", "pivot": [0, 0, 0], "cubes": []},
                    {"name": "body", "parent": "root", "pivot": [0, 8, 0], "cubes": [{"origin": [-5, -5, -3], "size": [10, 10, 6], "uv": [0, 0]}]},
                    {"name": "head", "parent": "body", "pivot": [0, 5, -8], "cubes": [{"origin": [-3, -3, -6], "size": [6, 6, 6], "uv": [0, 16]}]},
                    {"name": "front_left_leg", "parent": "body", "pivot": [4, 3, -5], "cubes": [{"origin": [-1, 0, -1], "size": [2, 10, 2], "uv": [24, 0]}]},
                    {"name": "front_right_leg", "parent": "body", "pivot": [-4, 3, -5], "cubes": [{"origin": [-1, 0, -1], "size": [2, 10, 2], "uv": [24, 0]}]},
                    {"name": "back_left_leg", "parent": "body", "pivot": [4, 3, 5], "cubes": [{"origin": [-1, 0, -1], "size": [2, 10, 2], "uv": [24, 0]}]},
                    {"name": "back_right_leg", "parent": "body", "pivot": [-4, 3, 5], "cubes": [{"origin": [-1, 0, -1], "size": [2, 10, 2], "uv": [24, 0]}]},
                    {"name": "tail", "parent": "body", "pivot": [0, 0, 5], "cubes": [{"origin": [-1, -1, 0], "size": [2, 2, 8], "uv": [32, 0]}]},
                ],
                "animations": ["idle", "walk", "run", "attack", "hurt", "death", "sleep", "eat"],
            },
            "flying": {
                "bones": [
                    {"name": "root", "pivot": [0, 0, 0], "cubes": []},
                    {"name": "body", "parent": "root", "pivot": [0, 0, 0], "cubes": [{"origin": [-3, -2, -4], "size": [6, 4, 8], "uv": [0, 0]}]},
                    {"name": "head", "parent": "body", "pivot": [0, 0, -6], "cubes": [{"origin": [-2, -2, -4], "size": [4, 4, 4], "uv": [0, 12]}]},
                    {"name": "left_wing", "parent": "body", "pivot": [3, 0, 0], "cubes": [{"origin": [0, -1, -3], "size": [10, 2, 6], "uv": [16, 0]}]},
                    {"name": "right_wing", "parent": "body", "pivot": [-3, 0, 0], "cubes": [{"origin": [-10, -1, -3], "size": [10, 2, 6], "uv": [16, 0]}]},
                    {"name": "tail", "parent": "body", "pivot": [0, 0, 4], "cubes": [{"origin": [-1, -1, 0], "size": [2, 2, 6], "uv": [32, 0]}]},
                ],
                "animations": ["idle", "fly", "hover", "attack", "hurt", "death"],
            },
            "serpent": {
                "bones": [
                    {"name": "root", "pivot": [0, 0, 0], "cubes": []},
                ] + [
                    {"name": f"segment_{i}", "parent": "root" if i == 0 else f"segment_{i-1}",
                     "pivot": [0, 0, i * 3], "cubes": [{"origin": [-1.5, -1.5, 0], "size": [3, 3, 3], "uv": [0, 0]}]}
                    for i in range(8)
                ],
                "animations": ["idle", "slither", "coil", "strike", "hurt", "death"],
            },
        }

    async def generate_models(
        self,
        state: VersionedAddonState,
        specs: list[ModelSpec],
        target_tier: DeviceTier = DeviceTier.MID_64BIT_4GB,
    ) -> VersionedAddonState:
        """Generate models for all specs."""
        current = state.get_current_version()
        if not current:
            return state

        state.set_status(GenerationStatus.GENERATING_MODELS, "model_generator",
                        f"Generating {len(specs)} models for {target_tier.value}...")
        state.add_log(f"Starting model generation: {len(specs)} specs")

        profile = VPPerformanceProfile.for_tier(target_tier)
        generated_models = []

        for i, spec in enumerate(specs):
            # Adjust LOD for tier
            if not profile.use_lod_models:
                spec.lod_levels = 1

            state.add_log(f"Generating model {i+1}/{len(specs)}: {spec.name} ({spec.geometry_type})")

            model = await self._generate_model(spec, profile)
            generated_models.append(model)

            # Create assets for version
            self._create_model_assets(current, model)

        state.set_status(GenerationStatus.GENERATING_MODELS, "model_generator",
                        f"Generated {len(generated_models)} models with LODs and animations")
        return state

    async def _generate_model(self, spec: ModelSpec, profile: VPPerformanceProfile) -> GeneratedModel:
        """Generate a complete model with all LODs and animations."""
        # Get base rig
        base_rig = self.base_rigs.get(spec.geometry_type, self.base_rigs["humanoid"])

        # Scale bones to spec size
        bones = self._scale_bones(base_rig["bones"], spec.size)

        # Add custom bones from spec
        bones.extend(spec.bones)

        # Optimize bones if requested
        if spec.merge_bones and profile.simplify_models:
            bones = self._merge_similar_bones(bones)

        # Generate geometry
        geometry = self._create_geometry(spec, bones)

        # Generate LODs
        lods = []
        if spec.lod_levels > 1:
            for lod_level in range(1, spec.lod_levels):
                lod_bones = self._create_lod_bones(bones, lod_level, spec.lod_levels)
                lod_geometry = self._create_geometry(spec, lod_bones, lod_level)
                lods.append(lod_geometry)

        # Generate animations
        animations = {}
        for anim_name in spec.animations:
            animations[anim_name] = self._create_animation(spec, anim_name, bones)

        # Generate animation controller
        anim_controller = self._create_anim_controller(spec, list(animations.keys()))

        # Generate render controller
        render_controller = self._create_render_controller(spec)

        return GeneratedModel(
            spec=spec,
            geometry=geometry,
            lods=lods,
            animations=animations,
            anim_controller=anim_controller,
            render_controller=render_controller,
            metadata={
                "name": spec.name,
                "entity_type": spec.entity_type,
                "geometry_type": spec.geometry_type,
                "bone_count": len(bones),
                "lod_count": len(lods) + 1,
                "animation_count": len(animations),
                "texture_size": spec.texture_size,
                "tier": profile.tier.value if hasattr(profile, 'tier') else "unknown",
                "generated_at": datetime.utcnow().isoformat(),
            },
        )

    def _scale_bones(self, bones: list[dict], size: tuple[float, float, float]) -> list[dict]:
        """Scale bone pivots and cubes to target size."""
        sx, sy, sz = size
        scaled = []
        for bone in bones:
            new_bone = bone.copy()
            if "pivot" in bone:
                new_bone["pivot"] = [
                    bone["pivot"][0] * sx,
                    bone["pivot"][1] * sy,
                    bone["pivot"][2] * sz,
                ]
            if "cubes" in bone:
                new_bone["cubes"] = []
                for cube in bone["cubes"]:
                    new_cube = cube.copy()
                    if "origin" in cube:
                        new_cube["origin"] = [
                            cube["origin"][0] * sx,
                            cube["origin"][1] * sy,
                            cube["origin"][2] * sz,
                        ]
                    if "size" in cube:
                        new_cube["size"] = [
                            cube["size"][0] * sx,
                            cube["size"][1] * sy,
                            cube["size"][2] * sz,
                        ]
                    new_bone["cubes"].append(new_cube)
            scaled.append(new_bone)
        return scaled

    def _merge_similar_bones(self, bones: list[dict]) -> list[dict]:
        """Merge bones that are very similar (symmetrical pairs)."""
        # Simple implementation: merge left/right pairs if they have identical cubes
        bone_dict = {b["name"]: b for b in bones}
        merged = []
        processed = set()

        for bone in bones:
            if bone["name"] in processed:
                continue

            # Check for symmetrical counterpart
            if bone["name"].startswith("left_"):
                right_name = "right_" + bone["name"][5:]
                if right_name in bone_dict:
                    right_bone = bone_dict[right_name]
                    # Check if cubes are mirror images
                    if self._cubes_are_mirror(bone.get("cubes", []), right_bone.get("cubes", [])):
                        # Create merged bone
                        merged_bone = bone.copy()
                        merged_bone["name"] = bone["name"][5:]  # Remove "left_"
                        merged_bone["merged_from"] = [bone["name"], right_name]
                        merged.append(merged_bone)
                        processed.add(bone["name"])
                        processed.add(right_name)
                        continue

            merged.append(bone)
            processed.add(bone["name"])

        return merged

    def _cubes_are_mirror(self, cubes1: list, cubes2: list) -> bool:
        """Check if two cube lists are mirror images."""
        if len(cubes1) != len(cubes2):
            return False
        for c1, c2 in zip(cubes1, cubes2):
            if c1.get("size") != c2.get("size"):
                return False
            o1, o2 = c1.get("origin", [0,0,0]), c2.get("origin", [0,0,0])
            if abs(o1[0] + o2[0] + c1["size"][0]) > 0.01:  # Mirror on X
                return False
            if o1[1] != o2[1] or o1[2] != o2[2]:
                return False
        return True

    def _create_geometry(self, spec: ModelSpec, bones: list[dict], lod_level: int = 0) -> dict:
        """Create geo.json format geometry."""
        geo_name = f"geometry.{spec.name}" + (f".lod{lod_level}" if lod_level > 0 else "")

        return {
            "format_version": "1.21.0",
            "minecraft:geometry": [{
                "description": {
                    "identifier": geo_name,
                    "texture_width": spec.texture_size[0],
                    "texture_height": spec.texture_size[1],
                    "visible_bounds_width": spec.size[0] * 2,
                    "visible_bounds_height": spec.size[1] * 2,
                    "visible_bounds_offset": [0, spec.size[1], 0],
                },
                "bones": bones,
            }]
        }

    def _create_lod_bones(self, bones: list[dict], lod_level: int, max_lod: int) -> list[dict]:
        """Create simplified bones for LOD level."""
        reduction = lod_level / max_lod
        lod_bones = []

        for bone in bones:
            # Skip detail bones at lower LODs
            if "detail" in bone["name"].lower() and lod_level > 0:
                continue

            new_bone = bone.copy()
            if "cubes" in bone:
                # Reduce cube count
                keep_count = max(1, int(len(bone["cubes"]) * (1 - reduction * 0.5)))
                new_bone["cubes"] = bone["cubes"][:keep_count]
            lod_bones.append(new_bone)

        return lod_bones

    def _create_animation(self, spec: ModelSpec, anim_name: str, bones: list[dict]) -> dict:
        """Create animation.json for an animation."""
        bone_names = [b["name"] for b in bones]

        # Animation templates
        templates = {
            "idle": self._idle_animation(bone_names),
            "walk": self._walk_animation(bone_names, spec.geometry_type),
            "run": self._run_animation(bone_names, spec.geometry_type),
            "attack": self._attack_animation(bone_names, spec.geometry_type),
            "hurt": self._hurt_animation(bone_names),
            "death": self._death_animation(bone_names),
            "sleep": self._sleep_animation(bone_names),
            "fly": self._fly_animation(bone_names),
            "hover": self._hover_animation(bone_names),
            "slither": self._slither_animation(bone_names),
            "coil": self._coil_animation(bone_names),
            "strike": self._strike_animation(bone_names),
            "eat": self._eat_animation(bone_names),
        }

        anim_data = templates.get(anim_name, self._generic_animation(bone_names, anim_name))

        return {
            "format_version": "1.10.0",
            "animations": {
                f"animation.{spec.name}.{anim_name}": anim_data
            }
        }

    def _idle_animation(self, bones: list[str]) -> dict:
        return {
            "loop": True,
            "animation_length": 4.0,
            "bones": {
                "body": {"rotation": [f"math.sin(query.life_time * 20) * 2", 0, 0]},
                "head": {"rotation": [f"math.sin(query.life_time * 30) * 3", f"math.sin(query.life_time * 25) * 5", 0]},
            }
        }

    def _walk_animation(self, bones: list[str], geo_type: str) -> dict:
        leg_bones = [b for b in bones if "leg" in b.lower() or "foot" in b.lower()]
        arm_bones = [b for b in bones if "arm" in b.lower() or "hand" in b.lower()]

        bone_anims = {}
        for i, bone in enumerate(leg_bones):
            phase = math.pi if i % 2 == 0 else 0
            bone_anims[bone] = {
                "rotation": [
                    f"math.cos(query.life_time * 400 + {phase}) * 30",
                    0, 0
                ]
            }

        for i, bone in enumerate(arm_bones):
            phase = math.pi if i % 2 == 0 else 0
            bone_anims[bone] = {
                "rotation": [
                    f"math.cos(query.life_time * 400 + {phase}) * -20",
                    0, 0
                ]
            }

        return {
            "loop": True,
            "animation_length": 1.0,
            "bones": bone_anims
        }

    def _run_animation(self, bones: list[str], geo_type: str) -> dict:
        walk = self._walk_animation(bones, geo_type)
        walk["animation_length"] = 0.6
        # Speed up rotations
        for bone, data in walk.get("bones", {}).items():
            if "rotation" in data:
                data["rotation"] = [r.replace("400", "700") for r in data["rotation"]]
        return walk

    def _attack_animation(self, bones: list[str], geo_type: str) -> dict:
        bone_anims = {}
        # Find arm/hand bones
        for bone in bones:
            if any(kw in bone.lower() for kw in ["arm", "hand", "claw", "weapon"]):
                bone_anims[bone] = {
                    "rotation": [
                        "variable.attack_time * -90",
                        "variable.attack_time * 20 * math.sin(variable.attack_time * 10)",
                        0
                    ]
                }
            elif "head" in bone.lower():
                bone_anims[bone] = {
                    "rotation": [
                        "variable.attack_time * -15",
                        0, 0
                    ]
                }
        return {"loop": False, "animation_length": 0.5, "bones": bone_anims}

    def _hurt_animation(self, bones: list[str]) -> dict:
        return {
            "loop": False,
            "animation_length": 0.3,
            "bones": {
                "body": {"rotation": ["variable.hurt_time * 20", 0, 0]},
                "head": {"rotation": ["variable.hurt_time * -30", 0, 0]},
            }
        }

    def _death_animation(self, bones: list[str]) -> dict:
        return {
            "loop": False,
            "animation_length": 2.0,
            "bones": {
                "body": {"rotation": ["variable.death_time * -90", 0, 0]},
            }
        }

    def _sleep_animation(self, bones: list[str]) -> dict:
        return {
            "loop": True,
            "animation_length": 3.0,
            "bones": {
                "head": {"rotation": [-30, 0, 0]},
                "body": {"rotation": [10, 0, 0]},
            }
        }

    def _fly_animation(self, bones: list[str]) -> dict:
        wing_bones = [b for b in bones if "wing" in b.lower()]
        bone_anims = {}
        for i, bone in enumerate(wing_bones):
            phase = math.pi if i == 1 else 0  # left/right opposite
            bone_anims[bone] = {
                "rotation": [
                    f"math.sin(query.life_time * 500 + {phase}) * 45",
                    0,
                    f"math.cos(query.life_time * 500 + {phase}) * 10"
                ]
            }
        return {"loop": True, "animation_length": 0.8, "bones": bone_anims}

    def _hover_animation(self, bones: list[str]) -> dict:
        return {
            "loop": True,
            "animation_length": 2.0,
            "bones": {
                "body": {"position": [0, "math.sin(query.life_time * 100) * 0.2", 0]},
            }
        }

    def _slither_animation(self, bones: list[str]) -> dict:
        segment_bones = [b for b in bones if "segment" in b.lower()]
        bone_anims = {}
        for i, bone in enumerate(segment_bones):
            bone_anims[bone] = {
                "rotation": [
                    0,
                    f"math.sin(query.life_time * 200 + {i * 0.5}) * 20",
                    0
                ]
            }
        return {"loop": True, "animation_length": 1.5, "bones": bone_anims}

    def _coil_animation(self, bones: list[str]) -> dict:
        segment_bones = [b for b in bones if "segment" in b.lower()]
        bone_anims = {}
        for i, bone in enumerate(segment_bones):
            bone_anims[bone] = {
                "rotation": [
                    0,
                    f"variable.coil_progress * {i * 30}",
                    0
                ]
            }
        return {"loop": False, "animation_length": 1.0, "bones": bone_anims}

    def _strike_animation(self, bones: list[str]) -> dict:
        head_bones = [b for b in bones if "head" in b.lower() or "segment_0" in b]
        bone_anims = {}
        for bone in head_bones:
            bone_anims[bone] = {
                "position": [
                    0, 0, "variable.strike_progress * 3"
                ]
            }
        return {"loop": False, "animation_length": 0.4, "bones": bone_anims}

    def _eat_animation(self, bones: list[str]) -> dict:
        return {
            "loop": False,
            "animation_length": 1.5,
            "bones": {
                "head": {"rotation": ["variable.eat_progress * -40", 0, 0]},
            }
        }

    def _generic_animation(self, bones: list[str], name: str) -> dict:
        return {
            "loop": True,
            "animation_length": 1.0,
            "bones": {}
        }

    def _create_anim_controller(self, spec: ModelSpec, animations: list[str]) -> dict:
        """Create animation controller with states and transitions."""
        states = {}
        transitions = []

        # Default state
        states["default"] = {
            "animations": [f"animation.{spec.name}.idle"],
            "transitions": [
                {"walk": "variable.is_moving && !variable.is_sprinting"},
                {"run": "variable.is_sprinting"},
                {"attack": "variable.is_attacking"},
                {"hurt": "variable.is_hurt"},
                {"death": "variable.is_dead"},
            ]
        }

        # Movement states
        states["walk"] = {"animations": [f"animation.{spec.name}.walk"]}
        states["run"] = {"animations": [f"animation.{spec.name}.run"]}

        # Action states
        if "attack" in animations:
            states["attack"] = {
                "animations": [f"animation.{spec.name}.attack"],
                "transitions": [{"default": "!variable.is_attacking"}]
            }
        if "hurt" in animations:
            states["hurt"] = {
                "animations": [f"animation.{spec.name}.hurt"],
                "transitions": [{"default": "!variable.is_hurt"}]
            }
        if "death" in animations:
            states["death"] = {
                "animations": [f"animation.{spec.name}.death"],
                "transitions": []
            }

        # Special states
        if "fly" in animations:
            states["fly"] = {"animations": [f"animation.{spec.name}.fly"]}
        if "hover" in animations:
            states["hover"] = {"animations": [f"animation.{spec.name}.hover"]}
        if "slither" in animations:
            states["slither"] = {"animations": [f"animation.{spec.name}.slither"]}
        if "sleep" in animations:
            states["sleep"] = {
                "animations": [f"animation.{spec.name}.sleep"],
                "transitions": [{"default": "!variable.is_sleeping"}]
            }

        return {
            "format_version": "1.10.0",
            "animation_controllers": {
                f"controller.animation.{spec.name}": {
                    "initial_state": "default",
                    "states": states
                }
            }
        }

    def _create_render_controller(self, spec: ModelSpec) -> dict:
        """Create render controller with geometry, materials, textures."""
        return {
            "format_version": "1.10.0",
            "render_controllers": {
                f"controller.render.{spec.name}": {
                    "geometry": {
                        "default": f"geometry.{spec.name}"
                    },
                    "materials": [{
                        "*": f"material.{spec.name}"
                    }],
                    "textures": [{
                        "*": f"texture.{spec.name}"
                    }],
                    "particle_emitters": spec.particles if spec.particles else [],
                }
            }
        }

    def _create_model_assets(self, version: 'AddonVersion', model: GeneratedModel):
        """Create GeneratedAsset entries for the model."""
        spec = model.spec

        # Geometry
        version.bp_assets.append(GeneratedAsset(
            asset_type=AssetType.GEOMETRY,
            content=model.geometry,
            metadata={
                "name": spec.name,
                "entity_type": spec.entity_type,
                "lod_level": 0,
            }
        ))

        # LOD geometries
        for i, lod in enumerate(model.lods):
            version.bp_assets.append(GeneratedAsset(
                asset_type=AssetType.GEOMETRY,
                content=lod,
                metadata={
                    "name": f"{spec.name}.lod{i+1}",
                    "entity_type": spec.entity_type,
                    "lod_level": i+1,
                }
            ))

        # Animations
        for anim_name, anim_data in model.animations.items():
            version.rp_assets.append(GeneratedAsset(
                asset_type=AssetType.ANIMATION,
                content=anim_data,
                metadata={"name": f"{spec.name}.{anim_name}"}
            ))

        # Animation controller
        if model.anim_controller:
            version.rp_assets.append(GeneratedAsset(
                asset_type=AssetType.ANIM_CONTROLLER,
                content=model.anim_controller,
                metadata={"name": f"controller.animation.{spec.name}"}
            ))

        # Render controller
        if model.render_controller:
            version.rp_assets.append(GeneratedAsset(
                asset_type=AssetType.RENDER_CONTROLLER,
                content=model.render_controller,
                metadata={"name": f"controller.render.{spec.name}"}
            ))

    def create_entity_model_spec(self, entity: LoreEntity, tier: DeviceTier = DeviceTier.MID_64BIT_4GB) -> ModelSpec:
        """Create ModelSpec from LoreEntity."""
        profile = VPPerformanceProfile.for_tier(tier)

        # Determine geometry type from entity
        geo_type = "humanoid"
        if "dragon" in entity.name.lower() or "flying" in entity.name.lower():
            geo_type = "flying"
        elif "worm" in entity.name.lower() or "serpent" in entity.name.lower() or "snake" in entity.name.lower():
            geo_type = "serpent"
        elif entity.entity_type == "mob" and "legs" in entity.description.lower():
            geo_type = "quadruped"

        # Size from stats or defaults
        size = (1.0, 1.0, 1.0)
        if entity.stats:
            health = entity.stats.get("health", 20)
            scale = min(max(health / 20.0, 0.5), 3.0)
            size = (scale, scale, scale)

        return ModelSpec(
            name=entity.name,
            entity_type=entity.entity_type,
            description=entity.description,
            geometry_type=geo_type,
            size=size,
            texture_size=(profile.texture_resolution, profile.texture_resolution),
            animations=["idle", "walk", "attack", "hurt", "death"] + (
                ["fly", "hover"] if geo_type == "flying" else
                ["slither", "coil", "strike"] if geo_type == "serpent" else
                ["sleep", "eat"] if geo_type == "quadruped" else []
            ),
            lod_levels=3 if profile.use_lod_models else 1,
            merge_bones=profile.simplify_models,
            optimize_for_tier=tier.value,
        )


# Singleton
_generator: ModelGenerator | None = None


def get_model_generator() -> ModelGenerator:
    global _generator
    if _generator is None:
        _generator = ModelGenerator()
    return _generator
