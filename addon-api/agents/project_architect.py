"""
Project Architect Agent - Creates the master plan for addon generation.

Analyzes lore research and creates a detailed execution plan for all downstream agents.
Determines asset dependencies, generation order, and resource allocation.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.state import (
    AddonState,
    LoreEntity,
    LoreItem,
    LoreBlock,
    LoreBiome,
    LoreMechanic,
    AssetType,
    Edition,
    GenerationStatus,
)
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


# =============================================================================
# Architect Prompts
# =============================================================================

ARCHITECT_SYSTEM_PROMPT = """You are the Project Architect for a Minecraft Bedrock addon generation system.
Your job is to analyze researched lore data and create a comprehensive, executable plan
for generating a complete addon (Behavior Pack + Resource Pack).

You must think like a Minecraft addon developer: understand dependencies, load order,
JSON schema requirements, scripting APIs, and resource pack structure."""

ARCHITECT_USER_PROMPT = """Create a master generation plan for the addon: **{theme}**

**Lore Summary:**
{summary}

**Researched Assets:**
- Entities: {entity_count} ({entity_names})
- Items: {item_count} ({item_names})
- Blocks: {block_count} ({block_names})
- Biomes: {biome_count} ({biome_names})
- Mechanics: {mechanic_count} ({mechanic_names})

**User Preferences:**
- Minecraft Version: {mc_version}
- Edition: {edition}
- Style: {style}
- Texture Resolution: {resolution}x
- Include PBR: {include_pbr}
- Include Animations: {include_animations}
- Include Sounds: {include_sounds}
- Include Scripts: {include_scripts}

**Output a detailed JSON plan:**

```json
{
  "addon_metadata": {
    "name": "Addon Display Name",
    "description": "One-line description",
    "version": [1, 0, 0],
    "min_engine_version": [1, 26, 0],
    "uuid_bp": "generated-uuid-v4",
    "uuid_rp": "generated-uuid-v4",
    "dependencies": []
  },
  "behavior_pack": {
    "entities": [
      {
        "lore_entity": "entity_internal_name",
        "file_path": "entities/entity_name.json",
        "priority": 1,
        "dependencies": [],
        "components_needed": ["minecraft:health", "minecraft:movement", "minecraft:behavior.nearest_attackable_target", "..."],
        "custom_components": ["custom:ability_name"],
        "scripts_needed": ["ability_name"],
        "spawn_rules_needed": true,
        "loot_table_needed": true
      }
    ],
    "items": [
      {
        "lore_item": "item_internal_name",
        "file_path": "items/item_name.json",
        "priority": 1,
        "dependencies": [],
        "components_needed": ["minecraft:max_stack_size", "minecraft:hand_equipped", "..."],
        "custom_components": [],
        "recipe_needed": true,
        "recipe_type": "shaped|shapeless|smithing|smelting"
      }
    ],
    "blocks": [
      {
        "lore_block": "block_internal_name",
        "file_path": "blocks/block_name.json",
        "priority": 2,
        "dependencies": ["item:drop_item"],
        "components_needed": ["minecraft:destroy_time", "minecraft:explosion_resistance", "..."],
        "block_entity": false,
        "permutations": []
      }
    ],
    "loot_tables": [
      {
        "entity": "entity_internal_name",
        "file_path": "loot_tables/entities/entity_name.json",
        "pools": [
          {"rolls": 1, "entries": [{"type": "item", "name": "item_id", "weight": 10}]}
        ]
      }
    ],
    "spawn_rules": [
      {
        "entity": "entity_internal_name",
        "file_path": "spawn_rules/entity_name.json",
        "conditions": {"biome_tags": ["tag1"], "difficulty": "normal", "weight": 10}
      }
    ],
    "recipes": [
      {
        "output_item": "item_internal_name",
        "type": "shaped|shapeless|smithing|smelting|stonecutting",
        "pattern": ["###", "# #", "###"],
        "key": {"#": "material_item_id"},
        "file_path": "recipes/item_name.json"
      }
    ],
    "scripts": {
      "main_file": "scripts/server/main.js",
      "typescript_source": "scripts/server/main.ts",
      "systems": [
        {
          "name": "system_name",
          "description": "What this system handles",
          "entities": ["entity1", "entity2"],
          "items": ["item1"],
          "events": ["event1", "event2"],
          "commands": ["command1"],
          "dependencies": []
        }
      ],
      "shared_constants": ["CONSTANT_NAME"],
      "data_driven": true
    }
  },
  "resource_pack": {
    "models": [
      {
        "lore_entity": "entity_internal_name",
        "file_path": "models/entity/entity_name.geo.json",
        "priority": 1,
        "geometry_type": "humanoid|quadruped|flying|custom",
        "texture_width": 64,
        "texture_height": 64,
        "bones": ["bone1", "bone2"],
        "animations_needed": ["idle", "walk", "attack", "death"],
        "render_controller_needed": true
      }
    ],
    "animations": [
      {
        "model": "entity_internal_name",
        "file_path": "animations/entity_name.animation.json",
        "animations": [
          {"name": "animation.idle", "loop": true, "bones": ["body", "head"]},
          {"name": "animation.walk", "loop": true, "bones": ["legs"]},
          {"name": "animation.attack", "loop": false, "bones": ["arms"]},
          {"name": "animation.death", "loop": false, "bones": ["body"]}
        ]
      }
    ],
    "animation_controllers": [
      {
        "entity": "entity_internal_name",
        "file_path": "animation_controllers/entity_name.ac.json",
        "states": ["idle", "walk", "attack", "death"],
        "transitions": {
          "idle->walk": "query.modified_move_speed > 0",
          "walk->idle": "query.modified_move_speed <= 0",
          "idle->attack": "query.is_attacking",
          "attack->idle": "!query.is_attacking",
          "any->death": "query.is_dead"
        }
      }
    ],
    "render_controllers": [
      {
        "entity": "entity_internal_name",
        "file_path": "render_controllers/entity_name.rc.json",
        "geometry": "geometry.entity_name",
        "materials": [{"*": "material.entity"}],
        "textures": ["texture.entity_name"],
        "arrays": {}
      }
    ],
    "particles": [
      {
        "name": "particle_name",
        "file_path": "particles/particle_name.json",
        "type": "emitter|system",
        "used_by": ["entity1", "item1", "spell1"]
      }
    ],
    "textures": {
      "entities": ["entity1", "entity2"],
      "items": ["item1", "item2"],
      "blocks": ["block1"],
      "animated": ["entity1", "item_special"],
      "pbr_maps": ["normal", "roughness", "metallic", "emissive"]
    },
    "sounds": [
      {
        "entity": "entity1",
        "events": ["ambient", "hurt", "death", "attack", "step"],
        "file_path": "sounds/entity/entity_name.json"
      }
    ],
    "ui": [
      {
        "name": "ui_name",
        "type": "screen|form|hud",
        "file_path": "ui/ui_name.json",
        "scripts": ["ui_script_name"]
      }
    ]
  },
  "generation_order": [
    "bp_manifest",
    "bp_entities",
    "bp_items",
    "bp_blocks",
    "bp_loot_tables",
    "bp_spawn_rules",
    "bp_recipes",
    "bp_scripts",
    "rp_manifest",
    "rp_models",
    "rp_textures",
    "rp_animations",
    "rp_anim_controllers",
    "rp_render_controllers",
    "rp_particles",
    "rp_sounds",
    "rp_ui"
  ],
  "parallel_groups": [
    ["bp_entities", "bp_items", "bp_blocks"],
    ["bp_loot_tables", "bp_spawn_rules", "bp_recipes"],
    ["rp_models", "rp_textures"],
    ["rp_animations", "rp_anim_controllers", "rp_render_controllers"],
    ["rp_particles", "rp_sounds", "rp_ui"]
  ],
  "estimates": {
    "total_assets": 0,
    "estimated_tokens": 0,
    "estimated_time_seconds": 0,
    "complexity_score": 0
  }
}
```

**Critical Rules:**
1. Entities with custom behaviors NEED scripts - plan the script systems first
2. Items used in recipes must be defined BEFORE recipes
3. Loot tables reference items - items must exist
4. Spawn rules reference entities - entities must exist
5. Models need textures - plan texture generation alongside models
6. Animations need animation controllers - pair them
7. Render controllers need models and textures - last in RP chain
8. Scripts should be data-driven (read from JSON, not hardcoded)
9. Use Component Groups for entity variants/states
10. Plan for Minecraft {mc_version}+ features (custom components, molang v1.20+)
11. For Java edition: note which assets need Fabric/Forge equivalents
12. Assign priorities: 1=critical path, 2=important, 3=nice-to-have"""


# =============================================================================
# Project Architect Agent
# =============================================================================

class ProjectArchitect:
    """Agent that creates the master execution plan from lore research."""

    def __init__(self):
        self.router = get_router()

    async def create_plan(self, state: AddonState) -> AddonState:
        """
        Analyze lore and create comprehensive generation plan.
        Updates state.plan and planned_* lists.
        """
        state.set_status(GenerationStatus.PLANNING, "project_architect", f"Creating plan for {state.theme}")

        if not state.lore:
            state.error_message = "No lore data available for planning"
            state.set_status(GenerationStatus.FAILED, "project_architect", "Missing lore")
            return state

        # Build context from lore
        entity_names = [e.name for e in state.lore.entities]
        item_names = [i.name for i in state.lore.items]
        block_names = [b.name for b in state.lore.blocks]
        biome_names = [b.name for b in state.lore.biomes]
        mechanic_names = [m.name for m in state.lore.mechanics]

        messages = [
            LLMMessage(role="system", content=ARCHITECT_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=ARCHITECT_USER_PROMPT.format(
                    theme=state.theme,
                    summary=state.lore.summary[:2000],
                    entity_count=len(entity_names),
                    entity_names=", ".join(entity_names[:20]),
                    item_count=len(item_names),
                    item_names=", ".join(item_names[:20]),
                    block_count=len(block_names),
                    block_names=", ".join(block_names[:15]),
                    biome_count=len(biome_names),
                    biome_names=", ".join(biome_names[:10]),
                    mechanic_count=len(mechanic_names),
                    mechanic_names=", ".join(mechanic_names[:10]),
                    mc_version=state.mc_version,
                    edition=state.edition.value,
                    style=state.style_preference,
                    resolution=state.texture_resolution,
                    include_pbr=state.include_pbr,
                    include_animations=state.include_animations,
                    include_sounds=state.include_sounds,
                    include_scripts=state.include_scripts,
                ),
            ),
        ]

        try:
            response = await self.router.complete(
                messages=messages,
                task_type=TaskType.PLANNING,
                temperature=0.2,  # Very low for structured planning
                max_tokens=8192,
            )

            state.tokens_used += response.usage.get("total_tokens", 0)
            state.api_calls += 1

            plan = self._parse_plan_response(response.content)
            state.plan = plan

            # Extract planned asset lists for quick access
            state.planned_entities = [e["lore_entity"] for e in plan.get("behavior_pack", {}).get("entities", [])]
            state.planned_items = [i["lore_item"] for i in plan.get("behavior_pack", {}).get("items", [])]
            state.planned_blocks = [b["lore_block"] for b in plan.get("behavior_pack", {}).get("blocks", [])]
            state.planned_biomes = [b["lore_block"] for b in plan.get("behavior_pack", {}).get("biomes", [])]  # biome blocks
            state.planned_mechanics = [m["name"] for m in plan.get("behavior_pack", {}).get("scripts", {}).get("systems", [])]

            state.plan_complete = True
            state.add_log(f"Plan created: {len(state.planned_entities)} entities, {len(state.planned_items)} items, {len(state.planned_blocks)} blocks, {len(plan.get('behavior_pack', {}).get('scripts', {}).get('systems', []))} script systems")

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            state.error_message = f"Planning failed: {str(e)}"
            state.set_status(GenerationStatus.FAILED, "project_architect", str(e))

        return state

    def _parse_plan_response(self, content: str) -> dict[str, Any]:
        """Parse and validate architect's plan response."""
        json_str = self._extract_json(content)

        try:
            plan = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            logger.debug(f"Raw content: {content[:2000]}")
            raise ValueError(f"Invalid JSON from architect: {e}")

        # Validate required sections
        required = ["addon_metadata", "behavior_pack", "resource_pack", "generation_order", "parallel_groups"]
        for section in required:
            if section not in plan:
                raise ValueError(f"Missing required plan section: {section}")

        return plan

    def _extract_json(self, content: str) -> str:
        """Extract JSON from markdown code blocks or raw response."""
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


# Singleton instance
_architect: ProjectArchitect | None = None


def get_project_architect() -> ProjectArchitect:
    global _architect
    if _architect is None:
        _architect = ProjectArchitect()
    return _architect
