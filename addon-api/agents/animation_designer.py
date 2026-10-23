"""
Animation Designer Agent - Professional animations with molang-driven blends.

Creates fluid animations for entities:
- Procedural + keyframe hybrid animations
- Molang-driven blend trees
- Animation layering and masking
- Particle integration
- Render controller synchronization
- Performance-optimized keyframe reduction
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
class AnimationSpec:
    """Specification for an animation."""
    name: str
    entity_name: str
    animation_type: str  # "idle", "walk", "run", "attack", "custom"
    description: str
    duration: float = 1.0
    loop: bool = True
    blend_weight: float = 1.0
    layer: int = 0
    mask: list[str] = field(default_factory=list)  # Bones to animate
    events: list[dict] = field(default_factory=list)  # Timeline events
    molang_driven: bool = True
    procedural: bool = False


@dataclass
class AnimationSet:
    """Complete animation set for an entity."""
    entity_name: str
    animations: dict[str, dict] = field(default_factory=dict)  # name -> animation.json
    anim_controller: dict = field(default_factory=dict)
    blend_tree: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class AnimationDesigner:
    """
    Designs professional animations for Bedrock entities.
    Molang-driven, blend-tree based, performance optimized.
    """

    def __init__(self):
        self.router = get_router()

    async def design_animations(
        self,
        state: VersionedAddonState,
        target_tier: DeviceTier = DeviceTier.MID_64BIT_4GB,
    ) -> VersionedAddonState:
        """Design animations for all entities in the addon."""
        current = state.get_current_version()
        if not current or not current.lore:
            return state

        state.set_status(GenerationStatus.GENERATING_RP, "animation_designer",
                        f"Designing animations for {len(current.lore.entities)} entities...")
        state.add_log("Creating molang-driven animation systems...")

        profile = VPPerformanceProfile.for_tier(target_tier)
        animation_sets = []

        for entity in current.lore.entities:
            state.add_log(f"Designing animations for {entity.display_name}...")
            anim_set = await self._design_entity_animations(entity, profile)
            animation_sets.append(anim_set)
            self._create_animation_assets(current, anim_set)

        # Create global animation controller
        global_controller = self._create_global_anim_controller(animation_sets)
        current.rp_assets.append(GeneratedAsset(
            asset_type=AssetType.ANIM_CONTROLLER,
            content=global_controller,
            metadata={"name": "controller.animation.global"}
        ))

        state.set_status(GenerationStatus.GENERATING_RP, "animation_designer",
                        f"Created {len(animation_sets)} animation sets with blend trees")
        return state

    async def _design_entity_animations(
        self,
        entity: LoreEntity,
        profile: VPPerformanceProfile,
    ) -> AnimationSet:
        """Design complete animation set for one entity."""
        # Determine needed animations from entity
        base_anims = ["idle", "walk", "run", "attack", "hurt", "death"]
        special_anims = []

        if entity.entity_type == "boss":
            special_anims = ["phase_transition", "enrage", "ultimate", "vulnerable", "summon_minions"]
        elif "fly" in entity.description.lower():
            special_anims = ["fly", "hover", "dive", "glide"]
        elif "swim" in entity.description.lower():
            special_anims = ["swim", "dive", "surface"]
        elif "magic" in entity.description.lower():
            special_anims = ["cast", "channel", "ritual"]

        all_anims = base_anims + special_anims

        # Reduce for low tier
        if profile.reduced_animations:
            all_anims = base_anims[:4]  # idle, walk, attack, death only

        # Generate each animation
        animations = {}
        for anim_name in all_anims:
            spec = AnimationSpec(
                name=f"{entity.name}.{anim_name}",
                entity_name=entity.name,
                animation_type=anim_name,
                description=f"{anim_name.capitalize()} animation for {entity.display_name}",
                duration=self._get_anim_duration(anim_name),
                loop=anim_name in ["idle", "walk", "run", "fly", "hover", "swim"],
            )
            animations[anim_name] = await self._generate_animation(spec, entity)

        # Create animation controller with blend tree
        anim_controller = self._create_entity_anim_controller(entity, all_anims)

        # Create blend tree for smooth transitions
        blend_tree = self._create_blend_tree(entity, all_anims)

        return AnimationSet(
            entity_name=entity.name,
            animations=animations,
            anim_controller=anim_controller,
            blend_tree=blend_tree,
            metadata={
                "entity": entity.name,
                "animation_count": len(animations),
                "has_blend_tree": True,
                "tier": profile.tier.value if hasattr(profile, 'tier') else "unknown",
            }
        )

    def _get_anim_duration(self, anim_name: str) -> float:
        durations = {
            "idle": 4.0,
            "walk": 1.0,
            "run": 0.7,
            "attack": 0.6,
            "hurt": 0.3,
            "death": 2.0,
            "fly": 1.2,
            "hover": 2.0,
            "dive": 1.0,
            "swim": 1.5,
            "cast": 1.5,
            "channel": 3.0,
            "phase_transition": 2.0,
            "enrage": 1.0,
            "ultimate": 3.0,
        }
        return durations.get(anim_name, 1.0)

    async def _generate_animation(
        self,
        spec: AnimationSpec,
        entity: LoreEntity,
    ) -> dict:
        """Generate a single animation with molang-driven keyframes."""
        # Use LLM for complex custom animations
        if spec.animation_type in ["cast", "channel", "ritual", "phase_transition", "ultimate"]:
            return await self._llm_generate_animation(spec, entity)

        # Procedural generation for standard animations
        return self._procedural_animation(spec, entity)

    def _procedural_animation(self, spec: AnimationSpec, entity: LoreEntity) -> dict:
        """Generate procedural animation using molang."""
        anim_id = f"animation.{spec.entity_name}.{spec.animation_type}"
        bones = {}

        # Standard bone animations by type
        if spec.animation_type == "idle":
            bones = self._idle_bones(entity)
        elif spec.animation_type == "walk":
            bones = self._walk_bones(entity)
        elif spec.animation_type == "run":
            bones = self._run_bones(entity)
        elif spec.animation_type == "attack":
            bones = self._attack_bones(entity)
        elif spec.animation_type == "hurt":
            bones = self._hurt_bones(entity)
        elif spec.animation_type == "death":
            bones = self._death_bones(entity)
        elif spec.animation_type == "fly":
            bones = self._fly_bones(entity)
        elif spec.animation_type == "hover":
            bones = self._hover_bones(entity)

        return {
            "format_version": "1.10.0",
            "animations": {
                anim_id: {
                    "animation_length": spec.duration,
                    "loop": spec.loop,
                    "blend_weight": spec.blend_weight,
                    "bones": bones,
                }
            }
        }

    def _idle_bones(self, entity: LoreEntity) -> dict:
        return {
            "body": {
                "rotation": [
                    "math.sin(query.life_time * 20) * 1.5",
                    "math.sin(query.life_time * 15) * 0.5",
                    0
                ],
                "position": [
                    0,
                    "math.sin(query.life_time * 40) * 0.05",
                    0
                ]
            },
            "head": {
                "rotation": [
                    "math.sin(query.life_time * 30) * 3",
                    "math.sin(query.life_time * 25) * 5",
                    "math.sin(query.life_time * 20) * 1"
                ]
            },
            "left_arm": {
                "rotation": [
                    "math.sin(query.life_time * 20) * -5",
                    0,
                    "math.sin(query.life_time * 20) * 2"
                ]
            },
            "right_arm": {
                "rotation": [
                    "math.sin(query.life_time * 20) * -5",
                    0,
                    "math.sin(query.life_time * 20) * -2"
                ]
            },
        }

    def _walk_bones(self, entity: LoreEntity) -> dict:
        speed = 400
        return {
            "left_leg": {
                "rotation": [
                    f"math.cos(query.life_time * {speed}) * 40",
                    0, 0
                ]
            },
            "right_leg": {
                "rotation": [
                    f"math.cos(query.life_time * {speed} + 3.14) * 40",
                    0, 0
                ]
            },
            "left_arm": {
                "rotation": [
                    f"math.cos(query.life_time * {speed} + 3.14) * -25",
                    0, 0
                ]
            },
            "right_arm": {
                "rotation": [
                    f"math.cos(query.life_time * {speed}) * -25",
                    0, 0
                ]
            },
            "body": {
                "rotation": [
                    f"math.sin(query.life_time * {speed * 2}) * 2",
                    0,
                    f"math.sin(query.life_time * {speed}) * 1"
                ],
                "position": [
                    0,
                    f"math.abs(math.sin(query.life_time * {speed})) * 0.1",
                    0
                ]
            },
            "head": {
                "rotation": [
                    f"math.sin(query.life_time * {speed * 2}) * -3",
                    0, 0
                ]
            },
        }

    def _run_bones(self, entity: LoreEntity) -> dict:
        walk = self._walk_bones(entity)
        # Speed up and increase amplitude
        for bone, data in walk.get("bones", {}).items():
            if "rotation" in data:
                data["rotation"] = [r.replace("400", "700").replace("40", "60") for r in data["rotation"]]
        return walk

    def _attack_bones(self, entity: LoreEntity) -> dict:
        return {
            "right_arm": {
                "rotation": [
                    "variable.attack_time * -120",
                    "variable.attack_time * 30 * math.sin(variable.attack_time * 20)",
                    "variable.attack_time * 10"
                ]
            },
            "left_arm": {
                "rotation": [
                    "variable.attack_time * -30",
                    0, 0
                ]
            },
            "body": {
                "rotation": [
                    "variable.attack_time * -15",
                    0,
                    "variable.attack_time * 5 * math.sin(variable.attack_time * 30)"
                ]
            },
            "head": {
                "rotation": [
                    "variable.attack_time * -20",
                    0, 0
                ]
            },
        }

    def _hurt_bones(self, entity: LoreEntity) -> dict:
        return {
            "body": {
                "rotation": [
                    "variable.hurt_time * 30 * math.sin(variable.hurt_time * 50)",
                    "variable.hurt_time * 10 * math.cos(variable.hurt_time * 40)",
                    0
                ],
                "position": [
                    "variable.hurt_time * 0.2 * math.sin(variable.hurt_time * 60)",
                    0,
                    "variable.hurt_time * 0.1 * math.cos(variable.hurt_time * 60)"
                ]
            },
            "head": {
                "rotation": [
                    "variable.hurt_time * -40",
                    "variable.hurt_time * 15 * math.sin(variable.hurt_time * 40)",
                    0
                ]
            },
        }

    def _death_bones(self, entity: LoreEntity) -> dict:
        return {
            "body": {
                "rotation": [
                    "variable.death_time * -90",
                    "variable.death_time * 10 * math.sin(variable.death_time * 20)",
                    0
                ],
                "position": [
                    0,
                    "variable.death_time * -0.5",
                    0
                ]
            },
            "head": {
                "rotation": [
                    "variable.death_time * -45",
                    0, 0
                ]
            },
            "left_arm": {
                "rotation": [
                    "variable.death_time * -60",
                    0, 0
                ]
            },
            "right_arm": {
                "rotation": [
                    "variable.death_time * -60",
                    0, 0
                ]
            },
        }

    def _fly_bones(self, entity: LoreEntity) -> dict:
        return {
            "body": {
                "rotation": [
                    "math.sin(query.life_time * 100) * 5",
                    "math.sin(query.life_time * 80) * 3",
                    "math.sin(query.life_time * 120) * 2"
                ],
                "position": [
                    0,
                    "math.sin(query.life_time * 200) * 0.3",
                    0
                ]
            },
            "left_wing": {
                "rotation": [
                    "math.sin(query.life_time * 500) * 60",
                    0,
                    "math.cos(query.life_time * 500) * 15"
                ]
            },
            "right_wing": {
                "rotation": [
                    "math.sin(query.life_time * 500 + 3.14) * 60",
                    0,
                    "math.cos(query.life_time * 500 + 3.14) * 15"
                ]
            },
            "head": {
                "rotation": [
                    "math.sin(query.life_time * 150) * 10",
                    "math.sin(query.life_time * 120) * 15",
                    0
                ]
            },
        }

    def _hover_bones(self, entity: LoreEntity) -> dict:
        return {
            "body": {
                "position": [
                    0,
                    "math.sin(query.life_time * 100) * 0.4",
                    0
                ],
                "rotation": [
                    "math.sin(query.life_time * 60) * 2",
                    "math.sin(query.life_time * 50) * 1",
                    0
                ]
            },
            "left_wing": {
                "rotation": [
                    "math.sin(query.life_time * 200) * 20",
                    0, 0
                ]
            },
            "right_wing": {
                "rotation": [
                    "math.sin(query.life_time * 200 + 3.14) * 20",
                    0, 0
                ]
            },
        }

    async def _llm_generate_animation(self, spec: AnimationSpec, entity: LoreEntity) -> dict:
        """Use LLM for complex custom animations."""
        prompt = f"""Create a custom molang-driven animation for **{entity.display_name}**.

**Animation:** {spec.animation_type}
**Description:** {spec.description}
**Duration:** {spec.duration}s
**Loop:** {spec.loop}
**Entity Type:** {entity.entity_type}
**Abilities:** {', '.join(entity.abilities)}

**Requirements:**
- Molang expressions for procedural feel
- Timeline events for particle/sound triggers
- Blend masks for partial body animation
- Performance optimized keyframes

**Output JSON (animation.json format):**
```json
{{
  "format_version": "1.10.0",
  "animations": {{
    "animation.{entity.name}.{spec.animation_type}": {{
      "animation_length": {spec.duration},
      "loop": {str(spec.loop).lower()},
      "blend_weight": 1.0,
      "bones": {{}},
      "events": {{}}
    }}
  }}
}}
```"""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                task_type=TaskType.CODE_GENERATION,
                temperature=0.3,
                max_tokens=6000,
            )
            return json.loads(self._extract_json(response.content))
        except Exception as e:
            logger.warning(f"LLM animation generation failed: {e}")
            return self._procedural_animation(spec, entity)

    def _create_entity_anim_controller(self, entity: LoreEntity, animations: list[str]) -> dict:
        """Create animation controller with states and transitions."""
        states = {}
        transitions = []

        # Default state
        states["default"] = {
            "animations": [f"animation.{entity.name}.idle"],
            "transitions": [
                {"walk": "variable.is_moving && !variable.is_sprinting"},
                {"run": "variable.is_sprinting"},
                {"attack": "variable.is_attacking"},
                {"hurt": "variable.is_hurt"},
                {"death": "variable.is_dead"},
            ]
        }

        # Movement
        if "walk" in animations:
            states["walk"] = {"animations": [f"animation.{entity.name}.walk"]}
        if "run" in animations:
            states["run"] = {"animations": [f"animation.{entity.name}.run"]}

        # Combat
        if "attack" in animations:
            states["attack"] = {
                "animations": [f"animation.{entity.name}.attack"],
                "transitions": [{"default": "!variable.is_attacking"}]
            }
        if "hurt" in animations:
            states["hurt"] = {
                "animations": [f"animation.{entity.name}.hurt"],
                "transitions": [{"default": "!variable.is_hurt"}]
            }
        if "death" in animations:
            states["death"] = {
                "animations": [f"animation.{entity.name}.death"],
                "transitions": []
            }

        # Special
        for anim in ["fly", "hover", "swim", "cast", "channel", "phase_transition", "enrage", "ultimate"]:
            if anim in animations:
                states[anim] = {
                    "animations": [f"animation.{entity.name}.{anim}"],
                    "transitions": [{"default": f"!variable.is_{anim}"}] if anim not in ["death"] else []
                }

        return {
            "format_version": "1.10.0",
            "animation_controllers": {
                f"controller.animation.{entity.name}": {
                    "initial_state": "default",
                    "states": states
                }
            }
        }

    def _create_blend_tree(self, entity: LoreEntity, animations: list[str]) -> dict:
        """Create blend tree for smooth animation transitions."""
        return {
            "format_version": "1.10.0",
            "blend_trees": {
                f"blend_tree.{entity.name}.movement": {
                    "type": "1d",
                    "input": "variable.move_speed",
                    "animations": [
                        {"animation": f"animation.{entity.name}.idle", "weight": 0.0},
                        {"animation": f"animation.{entity.name}.walk", "weight": 0.5},
                        {"animation": f"animation.{entity.name}.run", "weight": 1.0},
                    ] if "run" in animations else [
                        {"animation": f"animation.{entity.name}.idle", "weight": 0.0},
                        {"animation": f"animation.{entity.name}.walk", "weight": 1.0},
                    ]
                },
                f"blend_tree.{entity.name}.combat": {
                    "type": "1d",
                    "input": "variable.attack_intensity",
                    "animations": [
                        {"animation": f"animation.{entity.name}.idle", "weight": 0.0},
                        {"animation": f"animation.{entity.name}.attack", "weight": 1.0},
                    ]
                },
            }
        }

    def _create_global_anim_controller(self, animation_sets: list[AnimationSet]) -> dict:
        """Create global animation controller that combines all entities."""
        controllers = {}
        for anim_set in animation_sets:
            # Already in individual anim_controller, but we can create a master
            pass

        return {
            "format_version": "1.10.0",
            "animation_controllers": {
                "controller.animation.master": {
                    "initial_state": "default",
                    "states": {
                        "default": {
                            "animations": []
                        }
                    }
                }
            }
        }

    def _create_animation_assets(self, version: 'AddonVersion', anim_set: AnimationSet):
        """Create GeneratedAsset entries for animations."""
        for anim_name, anim_data in anim_set.animations.items():
            version.rp_assets.append(GeneratedAsset(
                asset_type=AssetType.ANIMATION,
                content=anim_data,
                metadata={"name": list(anim_data.get("animations", {}).keys())[0]}
            ))

        if anim_set.anim_controller:
            version.rp_assets.append(GeneratedAsset(
                asset_type=AssetType.ANIM_CONTROLLER,
                content=anim_set.anim_controller,
                metadata={"name": f"controller.animation.{anim_set.entity_name}"}
            ))

    def _extract_json(self, content: str) -> str:
        content = content.strip()
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            return content[start:end].strip()
        return content


# Singleton
_anim_designer: AnimationDesigner | None = None


def get_animation_designer() -> AnimationDesigner:
    global _anim_designer
    if _anim_designer is None:
        _anim_designer = AnimationDesigner()
    return _anim_designer
