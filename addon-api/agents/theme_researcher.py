"""
Theme Researcher Agent - Deep lore research for anime, novels, movies, games.

Uses LLMs with large context (Gemini 1.5 Pro, GPT-4o, Claude 3.5) to research
universes and extract entities, items, blocks, biomes, and mechanics.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.state import (
    AddonState,
    LoreData,
    LoreEntity,
    LoreItem,
    LoreBlock,
    LoreBiome,
    LoreMechanic,
    GenerationStatus,
)
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


# =============================================================================
# Research Prompts
# =============================================================================

RESEARCH_SYSTEM_PROMPT = """You are an expert lore researcher for Minecraft addon creation.
Your job is to deeply analyze a fictional universe (anime, manga, light novel, web novel, movie, game, book)
and extract structured data for creating a comprehensive Minecraft Bedrock addon.

You must be thorough, accurate to the source material, and think about how each element
translates to Minecraft mechanics (entities, items, blocks, biomes, gameplay systems)."""

RESEARCH_USER_PROMPT = """Research the universe: **{theme}**

{description}

Provide a comprehensive lore analysis in the following JSON structure. Be extremely detailed - this will drive the entire addon generation.

```json
{
  "universe_name": "Exact canonical name",
  "source_type": "anime|manga|light_novel|web_novel|movie|game|book|series",
  "summary": "2-3 paragraph overview of the universe, its setting, power systems, and key factions",
  "entities": [
    {
      "name": "internal_id (snake_case, no spaces)",
      "display_name": "Display Name",
      "description": "Detailed description of the entity, its lore, behavior, and role",
      "role": "boss|minion|neutral|pet|mount|npc",
      "abilities": ["ability1", "ability2", "..."],
      "visual_description": "Detailed visual description for texture/model generation",
      "size_category": "small|medium|large|giant",
      "biome_tags": ["biome1", "biome2"],
      "loot_drops": ["item1", "item2"],
      "health": 100,
      "damage": 15,
      "speed": 0.3,
      "is_tameable": false,
      "is_rideable": false
    }
  ],
  "items": [
    {
      "name": "internal_id",
      "display_name": "Display Name",
      "description": "Lore description, effects, and significance",
      "item_type": "sword|bow|armor|consumable|material|special|tool",
      "rarity": "common|uncommon|rare|epic|legendary|mythic",
      "abilities": ["ability1", "ability2"],
      "visual_description": "Detailed visual for texture generation",
      "durability": 0,
      "damage": 0,
      "cooldown": 0.0,
      "stack_size": 64,
      "crafting_materials": ["material1", "material2"]
    }
  ],
  "blocks": [
    {
      "name": "internal_id",
      "display_name": "Display Name",
      "description": "Lore description and function",
      "block_type": "ore|decorative|functional|storage|special",
      "hardness": 3.0,
      "resistance": 6.0,
      "harvest_tool": "pickaxe",
      "harvest_level": 2,
      "light_level": 0,
      "visual_description": "Detailed visual for texture/model",
      "drops": ["item1"]
    }
  ],
  "biomes": [
    {
      "name": "internal_id",
      "display_name": "Display Name",
      "description": "Lore description of the biome/dimension",
      "temperature": 0.5,
      "humidity": 0.5,
      "features": ["feature1", "feature2"],
      "entities": ["entity_id1", "entity_id2"],
      "blocks": ["block_id1", "block_id2"],
      "is_dimension": false
    }
  ],
  "mechanics": [
    {
      "name": "mechanic_name",
      "description": "Detailed explanation of the mechanic/system",
      "implementation_hints": ["hint1", "hint2"],
      "related_entities": ["entity_id1"],
      "related_items": ["item_id1"]
    }
  ],
  "references": ["https://wiki.url", "https://fandom.url"]
}
```

**Guidelines:**
- Include 10-30 entities (mobs, bosses, NPCs, pets, mounts)
- Include 15-50 items (weapons, armor, tools, consumables, materials, special items)
- Include 5-20 blocks (ores, decorative, functional, dimensional)
- Include 3-10 biomes/dimensions
- Include 5-15 mechanics (power systems, progression, crafting, combat, magic)
- Be faithful to source material - cite specific arcs, chapters, episodes if possible
- Think Minecraft: how does each thing work in-game? (spawning, crafting, durability, enchantments, etc.)
- For web novels/light novels: include progression systems, cultivation realms, skill trees
- For anime: include signature moves, transformations, equipment
- Use internal_ids in snake_case for all references (cross-references must match)"""


REFINEMENT_PROMPT = """You previously researched **{theme}**. The user wants to refine the research:

**User Feedback:** {feedback}

**Current Research Summary:**
- Entities: {entity_count}
- Items: {item_count}
- Blocks: {block_count}
- Biomes: {biome_count}
- Mechanics: {mechanic_count}

Update the research JSON to address the feedback. Keep the same structure.
Focus on: {focus_areas}"""


# =============================================================================
# Theme Researcher Agent
# =============================================================================

class ThemeResearcher:
    """Agent responsible for deep lore research of fictional universes."""

    def __init__(self):
        self.router = get_router()

    async def research(self, state: AddonState) -> AddonState:
        """
        Main research entry point.
        Updates state.lore with comprehensive LoreData.
        """
        state.set_status(GenerationStatus.RESEARCHING, "theme_researcher", f"Researching {state.theme}")

        if not state.theme:
            state.error_message = "No theme provided for research"
            state.set_status(GenerationStatus.FAILED, "theme_researcher", "Missing theme")
            return state

        # Build messages
        messages = [
            LLMMessage(role="system", content=RESEARCH_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=RESEARCH_USER_PROMPT.format(
                    theme=state.theme,
                    description=state.description or "No additional description provided.",
                ),
            ),
        ]

        # Use best provider for lore research (large context, deep knowledge)
        try:
            response = await self.router.complete(
                messages=messages,
                task_type=TaskType.LORE_RESEARCH,
                temperature=0.3,  # Lower temp for factual accuracy
                max_tokens=8192,
            )

            state.tokens_used += response.usage.get("total_tokens", 0)
            state.api_calls += 1

            # Parse JSON response
            lore_data = self._parse_research_response(response.content, state.theme)
            state.lore = lore_data
            state.research_complete = True
            state.research_notes = f"Researched using {response.provider.value} ({response.model})"
            state.add_log(f"Research complete: {len(lore_data.entities)} entities, {len(lore_data.items)} items, {len(lore_data.blocks)} blocks, {len(lore_data.biomes)} biomes, {len(lore_data.mechanics)} mechanics")

        except Exception as e:
            logger.error(f"Research failed: {e}")
            state.error_message = f"Research failed: {str(e)}"
            state.set_status(GenerationStatus.FAILED, "theme_researcher", str(e))

        return state

    async def refine_research(self, state: AddonState, feedback: str, focus_areas: list[str]) -> AddonState:
        """
        Refine research based on user feedback.
        """
        state.set_status(GenerationStatus.RESEARCHING, "theme_researcher", "Refining research based on feedback")

        if not state.lore:
            state.error_message = "No existing research to refine"
            return state

        messages = [
            LLMMessage(role="system", content=RESEARCH_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=REFINEMENT_PROMPT.format(
                    theme=state.theme,
                    feedback=feedback,
                    entity_count=len(state.lore.entities),
                    item_count=len(state.lore.items),
                    block_count=len(state.lore.blocks),
                    biome_count=len(state.lore.biomes),
                    mechanic_count=len(state.lore.mechanics),
                    focus_areas=", ".join(focus_areas),
                ),
            ),
        ]

        try:
            response = await self.router.complete(
                messages=messages,
                task_type=TaskType.LORE_RESEARCH,
                temperature=0.3,
                max_tokens=8192,
            )

            state.tokens_used += response.usage.get("total_tokens", 0)
            state.api_calls += 1

            lore_data = self._parse_research_response(response.content, state.theme)
            state.lore = lore_data
            state.research_notes += f" | Refined: {feedback[:50]}"
            state.add_log(f"Research refined: {len(lore_data.entities)} entities, {len(lore_data.items)} items")

        except Exception as e:
            logger.error(f"Research refinement failed: {e}")
            state.error_message = f"Refinement failed: {str(e)}"

        return state

    def _parse_research_response(self, content: str, theme: str) -> LoreData:
        """Parse and validate LLM research response."""
        # Extract JSON from response (handle markdown code blocks)
        json_str = self._extract_json(content)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse research JSON: {e}")
            logger.debug(f"Raw content: {content[:2000]}")
            raise ValueError(f"Invalid JSON from LLM: {e}")

        # Validate and convert to LoreData
        return self._validate_and_convert(data, theme)

    def _extract_json(self, content: str) -> str:
        """Extract JSON from markdown code blocks or raw response."""
        content = content.strip()

        # Check for markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            return content[start:end].strip()

        # Assume entire response is JSON
        return content

    def _validate_and_convert(self, data: dict[str, Any], theme: str) -> LoreData:
        """Validate and convert raw dict to LoreData with defaults."""
        # Entities
        entities = []
        for e in data.get("entities", []):
            entities.append(LoreEntity(
                name=e.get("name", "unknown"),
                display_name=e.get("display_name", e.get("name", "Unknown")),
                description=e.get("description", ""),
                role=e.get("role", "neutral"),
                abilities=e.get("abilities", []),
                visual_description=e.get("visual_description", ""),
                size_category=e.get("size_category", "medium"),
                biome_tags=e.get("biome_tags", []),
                loot_drops=e.get("loot_drops", []),
                health=e.get("health", 20),
                damage=e.get("damage", 3),
                speed=e.get("speed", 0.25),
                is_tameable=e.get("is_tameable", False),
                is_rideable=e.get("is_rideable", False),
            ))

        # Items
        items = []
        for i in data.get("items", []):
            items.append(LoreItem(
                name=i.get("name", "unknown"),
                display_name=i.get("display_name", i.get("name", "Unknown")),
                description=i.get("description", ""),
                item_type=i.get("item_type", "special"),
                rarity=i.get("rarity", "common"),
                abilities=i.get("abilities", []),
                visual_description=i.get("visual_description", ""),
                durability=i.get("durability", 0),
                damage=i.get("damage", 0),
                cooldown=i.get("cooldown", 0.0),
                stack_size=i.get("stack_size", 64),
                crafting_materials=i.get("crafting_materials", []),
            ))

        # Blocks
        blocks = []
        for b in data.get("blocks", []):
            blocks.append(LoreBlock(
                name=b.get("name", "unknown"),
                display_name=b.get("display_name", b.get("name", "Unknown")),
                description=b.get("description", ""),
                block_type=b.get("block_type", "decorative"),
                hardness=b.get("hardness", 1.0),
                resistance=b.get("resistance", 1.0),
                harvest_tool=b.get("harvest_tool", "pickaxe"),
                harvest_level=b.get("harvest_level", 0),
                light_level=b.get("light_level", 0),
                visual_description=b.get("visual_description", ""),
                drops=b.get("drops", []),
            ))

        # Biomes
        biomes = []
        for b in data.get("biomes", []):
            biomes.append(LoreBiome(
                name=b.get("name", "unknown"),
                display_name=b.get("display_name", b.get("name", "Unknown")),
                description=b.get("description", ""),
                temperature=b.get("temperature", 0.5),
                humidity=b.get("humidity", 0.5),
                features=b.get("features", []),
                entities=b.get("entities", []),
                blocks=b.get("blocks", []),
                is_dimension=b.get("is_dimension", False),
            ))

        # Mechanics
        mechanics = []
        for m in data.get("mechanics", []):
            mechanics.append(LoreMechanic(
                name=m.get("name", "unknown"),
                description=m.get("description", ""),
                implementation_hints=m.get("implementation_hints", []),
                related_entities=m.get("related_entities", []),
                related_items=m.get("related_items", []),
            ))

        return LoreData(
            universe_name=data.get("universe_name", theme),
            source_type=data.get("source_type", "unknown"),
            summary=data.get("summary", ""),
            entities=entities,
            items=items,
            blocks=blocks,
            biomes=biomes,
            mechanics=mechanics,
            references=data.get("references", []),
        )


# Singleton instance
_researcher: ThemeResearcher | None = None


def get_theme_researcher() -> ThemeResearcher:
    global _researcher
    if _researcher is None:
        _researcher = ThemeResearcher()
    return _researcher


# Convenience function for direct use
async def research_theme(theme: str, description: str = "") -> LoreData:
    """Standalone research function."""
    researcher = get_theme_researcher()
    state = AddonState(theme=theme, description=description)
    state = await researcher.research(state)
    if state.lore is None:
        raise RuntimeError(state.error_message or "Research failed")
    return state.lore
