"""
Lore Deep Researcher Agent - Comprehensive multi-source lore aggregation.

Researches fictional universes from 50+ sources per work:
- Official wikis, Fandom, Reddit, Discord, official novels
- Produces 50 structured "virtual PDFs" (JSON domains) per work
- 5000+ pages equivalent of structured knowledge
- Canon confidence scoring and contradiction resolution
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from core.state import (
    VersionedAddonState,
    LoreData,
    LoreEntity,
    LoreItem,
    LoreBlock,
    LoreBiome,
    LoreMechanic,
    GenerationStatus,
)
from core.versioned_state import UserFeedback, FeedbackType
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


# =============================================================================
# Research Domain Definitions (50 Virtual PDFs)
# =============================================================================

RESEARCH_DOMAINS = [
    # Universe Foundation (1-5)
    ("universe_overview", "Universe Overview", "Setting, cosmology, history, geography, timeline"),
    ("power_system_detailed", "Power System", "Magic/abilities with exact mechanics, progression, limitations"),
    ("cosmology_metaphysics", "Cosmology & Metaphysics", "Planes, dimensions, gods, creation myths, afterlife"),
    ("history_timeline", "Historical Timeline", "Major eras, wars, cataclysms, golden ages, current year"),
    ("geography_worlds", "Geography & Worlds", "Continents, nations, cities, landmarks, special zones"),

    # Factions & Organizations (6-10)
    ("factions_major", "Major Factions", "Nations, empires, guilds, orders - structure, hierarchy, goals"),
    ("factions_minor", "Minor Factions", "Clans, cults, mercenary groups, merchant houses"),
    ("factions_relationships", "Faction Relationships", "Alliances, wars, trade, espionage, diplomacy"),
    ("organizations_secret", "Secret Organizations", "Hidden societies, conspiracies, ancient orders"),
    ("leadership_figures", "Leadership Figures", "Kings, guild masters, archmages, council members"),

    # Characters (11-18)
    ("characters_protagonists", "Protagonists", "Main characters - stats, abilities, progression, equipment"),
    ("characters_antagonists", "Antagonists", "Villains, rivals, dark lords - motivations, powers, minions"),
    ("characters_supporting", "Supporting Cast", "Mentors, companions, love interests, rivals"),
    ("characters_npcs", "Notable NPCs", "Shopkeepers, quest givers, trainers, lore keepers"),
    ("characters_legendary", "Legendary Figures", "Historical heroes, ancient beings, mythical entities"),
    ("character_relationships", "Character Relationships", "Family, romance, rivalry, master-student, betrayal"),
    ("character_progression", "Character Progression", "Leveling, awakening, evolution, class changes"),
    ("character_customization", "Character Customization", "Races, classes, backgrounds, appearance options"),

    # Items & Equipment (19-26)
    ("items_weapons", "Weapons", "Every named weapon - stats, abilities, lore, evolution paths"),
    ("items_armor", "Armor & Clothing", "Sets, bonuses, materials, enchantments, appearances"),
    ("items_accessories", "Accessories", "Rings, amulets, belts, artifacts, relics"),
    ("items_consumables", "Consumables", "Potions, elixirs, food, scrolls, bombs, reagents"),
    ("items_materials", "Crafting Materials", "Ores, herbs, monster parts, essences, crystals"),
    ("items_quest", "Quest Items", "Keys, documents, artifacts, macguffins"),
    ("items_currency", "Currency & Economy", "Coins, trade goods, reputation, alternative currencies"),
    ("items_unique", "Unique/Legendary Items", "One-of-a-kind artifacts with special lore"),

    # Blocks & World (27-32)
    ("blocks_natural", "Natural Blocks", "Ores, stone variants, soil, wood, plants, liquids"),
    ("blocks_constructed", "Constructed Blocks", "Bricks, planks, decorative, functional, redstone"),
    ("blocks_magical", "Magical Blocks", "Rune blocks, portal frames, enchanting tables, altars"),
    ("blocks_dimension", "Dimensional Blocks", "Blocks unique to other dimensions/planes"),
    ("blocks_mechanical", "Mechanical Blocks", "Gears, pistons, conveyors, automation"),
    ("blocks_special", "Special Blocks", "Unbreakable, physics-defying, lore-significant"),

    # Biomes & Dimensions (33-37)
    ("biomes_surface", "Surface Biomes", "Forests, deserts, jungles, tundras, oceans, variants"),
    ("biomes_subterranean", "Subterranean Biomes", "Caves, deepslate, underground forests, fungal"),
    ("biomes_dimensions", "Other Dimensions", "Nether-like, End-like, custom planes, pocket dimensions"),
    ("biomes_hazards", "Environmental Hazards", "Corruption, radiation, miasma, cursed zones"),
    ("biome_transitions", "Biome Transitions", "Edges, ecotones, magical boundaries, borders"),

    # Mechanics & Systems (38-45)
    ("mechanics_combat", "Combat Mechanics", "Formulas, action economy, cooldowns, combos, stances"),
    ("mechanics_progression", "Progression Systems", "XP, levels, skills, talents, prestige, rebirth"),
    ("mechanics_crafting", "Crafting Systems", "Recipes, stations, quality, experimentation, discovery"),
    ("mechanics_enchanting", "Enchanting/Upgrading", "Enchantments, runes, gems, reforging, corruption"),
    ("mechanics_economy", "Economy Systems", "Shops, trading, auction, player markets, inflation"),
    ("mechanics_social", "Social Systems", "Guilds, parties, marriage, reputation, factions"),
    ("mechanics_exploration", "Exploration Mechanics", "Mapping, fast travel, waypoints, secrets"),
    ("mechanics_pvp", "PvP Systems", "Arenas, duels, bounties, territory control, karma"),

    # Entities & Creatures (46-50)
    ("entities_wildlife", "Wildlife & Beasts", "Animals, magical beasts, variants, taming"),
    ("entities_monsters", "Monsters & Hostiles", "Common enemies, variants, behaviors, drops"),
    ("entities_bosses", "Bosses & Raids", "Phases, mechanics, arena, rewards, strategies"),
    ("entities_summons", "Summons & Minions", "Familiars, undead, constructs, elementals"),
    ("entities_unique", "Unique Entities", "Named NPCs, wandering merchants, world bosses"),

    # Bonus Domains (51-60)
    ("lore_books", "In-Universe Books", "Readable books, scrolls, tablets, bestiaries"),
    ("lore_quests", "Questlines & Stories", "Main quest, side quests, world events, choices"),
    ("lore_dialogue", "Dialogue & Voice", "Character voices, catchphrases, memorable lines"),
    ("lore_art_concepts", "Visual Concepts", "Color palettes, architecture styles, fashion, symbols"),
    ("lore_audio_concepts", "Audio Concepts", "Music themes, sound design, voice acting notes"),
    ("canon_vs_fanon", "Canon vs Fanon", "Verified facts vs community theories vs headcanons"),
    ("contradictions", "Contradictions Resolved", "Conflicting sources + chosen interpretation"),
    ("minecraft_mapping", "Minecraft Translation", "Direct 1:1 mapping decisions for each element"),
    ("performance_budget", "Performance Budget", "Polygon counts, texture limits, entity caps per tier"),
    ("ui_ux_concepts", "UI/UX Concepts", "Custom interfaces, HUDs, menus inspired by work's aesthetic"),
]


@dataclass
class ResearchSource:
    """A single source of lore information."""
    url: str
    title: str
    content: str
    source_type: str  # wiki, fandom, reddit, official, novel, video
    credibility: float  # 0.0 - 1.0
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    domain_relevance: dict[str, float] = field(default_factory=dict)  # domain -> relevance score


@dataclass
class ResearchResult:
    """Result of researching one domain."""
    domain_id: str
    domain_name: str
    content: str  # Markdown/JSON content
    sources: list[ResearchSource]
    confidence: float  # Overall confidence 0.0-1.0
    canon_status: str  # "canon", "semi-canon", "fanon", "contradicted"
    contradictions: list[str] = field(default_factory=list)
    minecraft_notes: list[str] = field(default_factory=list)


# =============================================================================
# Source Fetchers
# =============================================================================

class SourceFetcher:
    """Base class for fetching lore from different source types."""

    async def fetch(self, query: str, max_results: int = 10) -> list[ResearchSource]:
        raise NotImplementedError


class WikiFetcher(SourceFetcher):
    """Fetches from MediaWiki-based wikis (Fandom, Gamepedia, custom)."""

    def __init__(self, base_url: str, api_path: str = "/api.php"):
        self.base_url = base_url.rstrip("/")
        self.api_url = urljoin(self.base_url, api_path)
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        resp = await self.client.get(self.api_url, params=params)
        resp.raise_for_status()
        return resp.json().get("query", {}).get("search", [])

    async def get_page(self, page_id: int) -> dict:
        params = {
            "action": "parse",
            "pageid": page_id,
            "prop": "text|sections|categories|links",
            "format": "json",
        }
        resp = await self.client.get(self.api_url, params=params)
        resp.raise_for_status()
        return resp.json().get("parse", {})

    async def fetch(self, query: str, max_results: int = 10) -> list[ResearchSource]:
        sources = []
        try:
            results = await self.search(query, max_results)
            for r in results[:max_results]:
                page = await self.get_page(r["pageid"])
                html = page.get("text", {}).get("*", "")
                soup = BeautifulSoup(html, "html.parser")

                # Remove navigation, infoboxes, references
                for tag in soup(["table", "nav", "aside", "sup", "script", "style"]):
                    tag.decompose()

                text = soup.get_text(separator="\n", strip=True)
                if len(text) > 500:  # Filter stubs
                    sources.append(ResearchSource(
                        url=f"{self.base_url}/wiki/{r['title'].replace(' ', '_')}",
                        title=r["title"],
                        content=text[:50000],  # Limit per page
                        source_type="wiki",
                        credibility=0.85,
                    ))
        except Exception as e:
            logger.warning(f"Wiki fetch failed for {self.base_url}: {e}")
        return sources


class WebSearchFetcher(SourceFetcher):
    """Fetches from general web search (DuckDuckGo HTML scrape fallback)."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def fetch(self, query: str, max_results: int = 10) -> list[ResearchSource]:
        sources = []
        try:
            # Use duckduckgo HTML
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query}
            headers = {"User-Agent": "Mozilla/5.0 (compatible; AddonGenerator/1.0)"}
            resp = await self.client.post(url, data=params, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")

            results = soup.select(".result__snippet")[:max_results]
            for i, snippet in enumerate(results):
                link = snippet.find_previous("a", class_="result__url")
                sources.append(ResearchSource(
                    url=link.get("href", "") if link else "",
                    title=f"Web Result {i+1}: {query}",
                    content=snippet.get_text(strip=True)[:10000],
                    source_type="web",
                    credibility=0.5,
                ))
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
        return sources


class RedditFetcher(SourceFetcher):
    """Fetches Reddit discussions about the work."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch(self, query: str, max_results: int = 10) -> list[ResearchSource]:
        sources = []
        try:
            # Use Reddit JSON API (no auth needed for public)
            subreddits = ["fantasy", "lightnovels", "webnovels", "anime", "manga"]
            for sub in subreddits:
                url = f"https://www.reddit.com/r/{sub}/search.json"
                params = {"q": query, "restrict_sr": "on", "limit": 3, "sort": "relevance"}
                headers = {"User-Agent": "AddonGenerator/1.0"}
                resp = await self.client.get(url, params=params, headers=headers)
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    p = post["data"]
                    if p.get("selftext"):
                        sources.append(ResearchSource(
                            url=f"https://reddit.com{p['permalink']}",
                            title=p["title"],
                            content=p["selftext"][:10000],
                            source_type="reddit",
                            credibility=0.4,
                        ))
        except Exception as e:
            logger.warning(f"Reddit fetch failed: {e}")
        return sources


# =============================================================================
# Lore Deep Researcher Agent
# =============================================================================

class LoreDeepResearcher:
    """
    Orchestrates deep research across 50+ domains using multiple sources.
    Produces structured knowledge equivalent to 50 PDFs × 100 pages each.
    """

    def __init__(self):
        self.router = get_router()
        self.fetchers: list[SourceFetcher] = []

    def add_fetcher(self, fetcher: SourceFetcher):
        self.fetchers.append(fetcher)

    async def research(self, state: VersionedAddonState) -> VersionedAddonState:
        """Main entry point - researches all domains for the theme."""
        state.set_status(GenerationStatus.RESEARCHING, "lore_deep_researcher",
                        f"Starting deep research for: {state.theme}")

        # Initialize fetchers if not already
        if not self.fetchers:
            self._initialize_fetchers(state.theme)

        # Phase 1: Gather sources for all domains
        state.add_log("Phase 1: Gathering sources from wiki, web, reddit...")
        domain_sources = await self._gather_all_sources(state.theme, state.description)

        # Phase 2: LLM synthesis per domain
        state.add_log("Phase 2: Synthesizing 50+ knowledge domains...")
        domain_results = await self._synthesize_domains(state, domain_sources)

        # Phase 3: Cross-domain validation & contradiction resolution
        state.add_log("Phase 3: Cross-referencing and resolving contradictions...")
        validated_results = await self._validate_and_resolve(state, domain_results)

        # Phase 4: Build structured LoreData
        state.add_log("Phase 4: Building structured LoreData...")
        lore = await self._build_lore_data(state, validated_results)

        # Phase 5: Generate Minecraft mapping & performance budgets
        state.add_log("Phase 5: Creating Minecraft translation map...")
        await self._generate_minecraft_mapping(state, lore, validated_results)

        # Store research results in version
        current = state.get_current_version()
        if current:
            current.lore = lore

        state.lore = lore
        state.set_status(GenerationStatus.RESEARCHING, "lore_deep_researcher",
                        f"Research complete: {len(validated_results)} domains")
        return state

    def _initialize_fetchers(self, theme: str):
        """Initialize fetchers based on theme."""
        # Try to detect wiki URLs
        wiki_urls = self._guess_wiki_urls(theme)
        for url in wiki_urls:
            self.fetchers.append(WikiFetcher(url))

        # Always add web and reddit
        self.fetchers.append(WebSearchFetcher())
        self.fetchers.append(RedditFetcher())

    def _guess_wiki_urls(self, theme: str) -> list[str]:
        """Guess likely wiki URLs for a theme."""
        slug = theme.lower().replace(" ", "-").replace("'", "")
        return [
            f"https://{slug}.fandom.com",
            f"https://{slug}.wiki",
            f"https://{slug}.gamepedia.com",
        ]

    async def _gather_all_sources(self, theme: str, description: str) -> dict[str, list[ResearchSource]]:
        """Gather sources for all 50+ domains in parallel."""
        domain_sources = {}

        async def fetch_domain(domain_id: str, domain_name: str, domain_desc: str):
            query = f"{theme} {domain_name} {domain_desc}"
            all_sources = []
            for fetcher in self.fetchers:
                sources = await fetcher.fetch(query, max_results=5)
                all_sources.extend(sources)
            domain_sources[domain_id] = all_sources
            logger.info(f"Domain {domain_name}: {len(all_sources)} sources")

        # Run in batches to avoid rate limits
        batch_size = 5
        domains = list(RESEARCH_DOMAINS)
        for i in range(0, len(domains), batch_size):
            batch = domains[i:i+batch_size]
            await asyncio.gather(*[
                fetch_domain(d[0], d[1], d[2]) for d in batch
            ])
            await asyncio.sleep(1)  # Rate limit courtesy

        return domain_sources

    async def _synthesize_domains(
        self,
        state: VersionedAddonState,
        domain_sources: dict[str, list[ResearchSource]]
    ) -> dict[str, ResearchResult]:
        """Use LLM to synthesize each domain from gathered sources."""
        results = {}

        for domain_id, domain_name, domain_desc in RESEARCH_DOMAINS:
            sources = domain_sources.get(domain_id, [])
            if not sources:
                logger.warning(f"No sources for domain: {domain_name}")
                results[domain_id] = ResearchResult(
                    domain_id=domain_id,
                    domain_name=domain_name,
                    content="",
                    sources=[],
                    confidence=0.0,
                    canon_status="unknown",
                )
                continue

            # Prepare source context for LLM
            source_context = self._format_sources_for_llm(sources)

            # Synthesis prompt
            prompt = f"""You are a lore researcher for: **{state.theme}**

**Domain:** {domain_name}
**Description:** {domain_desc}

**Sources ({len(sources)} sources):**
{source_context}

**Task:** Synthesize a comprehensive, structured analysis of this domain.
Be extremely detailed - this will drive Minecraft addon generation.

**Output JSON:**
```json
{{
  "content": "Detailed markdown content (equivalent to 100-page PDF)",
  "confidence": 0.0-1.0,
  "canon_status": "canon|semi-canon|fanon|contradicted",
  "contradictions": ["List of contradictions found"],
  "minecraft_notes": ["How this translates to Minecraft mechanics"]
}}
```"""

            try:
                response = await self.router.complete(
                    messages=[LLMMessage(role="user", content=prompt)],
                    task_type=TaskType.LORE_RESEARCH,
                    temperature=0.3,
                    max_tokens=8000,
                )

                data = self._parse_llm_json(response.content)
                results[domain_id] = ResearchResult(
                    domain_id=domain_id,
                    domain_name=domain_name,
                    content=data.get("content", ""),
                    sources=sources,
                    confidence=data.get("confidence", 0.5),
                    canon_status=data.get("canon_status", "semi-canon"),
                    contradictions=data.get("contradictions", []),
                    minecraft_notes=data.get("minecraft_notes", []),
                )
                logger.info(f"Synthesized {domain_name}: confidence={results[domain_id].confidence:.2f}")

            except Exception as e:
                logger.error(f"Failed to synthesize {domain_name}: {e}")
                results[domain_id] = ResearchResult(
                    domain_id=domain_id,
                    domain_name=domain_name,
                    content=f"ERROR: {e}",
                    sources=sources,
                    confidence=0.0,
                    canon_status="error",
                )

        return results

    def _format_sources_for_llm(self, sources: list[ResearchSource]) -> str:
        """Format sources for LLM consumption."""
        parts = []
        for i, s in enumerate(sources[:8]):  # Limit to top 8 sources
            parts.append(f"""### Source {i+1}: {s.title} ({s.source_type}, credibility: {s.credibility:.2f})
URL: {s.url}
Content:
{s.content[:8000]}
---""")
        return "\n".join(parts)

    def _parse_llm_json(self, content: str) -> dict:
        """Extract JSON from LLM response."""
        content = content.strip()
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()
        return json.loads(content)

    async def _validate_and_resolve(
        self,
        state: VersionedAddonState,
        domain_results: dict[str, ResearchResult]
    ) -> dict[str, ResearchResult]:
        """Cross-reference domains and resolve contradictions."""
        # Find cross-domain references
        all_content = "\n\n".join([
            f"## {r.domain_name}\n{r.content}"
            for r in domain_results.values() if r.content
        ])

        validation_prompt = f"""Cross-reference the following lore domains for **{state.theme}** and identify:
1. Contradictions between domains
2. Missing critical information
3. Canon confidence adjustments

**All Domains:**
{all_content[:50000]}

**Output JSON:**
```json
{{
  "cross_contradictions": [
    {{"domains": ["domain1", "domain2"], "issue": "Description", "resolution": "Chosen interpretation"}}
  ],
  "missing_critical": ["domain: what's missing"],
  "confidence_adjustments": {{"domain_id": 0.0-1.0}},
  "canon_hierarchy": ["Most canon domain", "..."]
}}
```"""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=validation_prompt)],
                task_type=TaskType.REASONING,
                temperature=0.2,
                max_tokens=4000,
            )
            validation = self._parse_llm_json(response.content)

            # Apply adjustments
            for domain_id, adj_confidence in validation.get("confidence_adjustments", {}).items():
                if domain_id in domain_results:
                    domain_results[domain_id].confidence = adj_confidence

            for contra in validation.get("cross_contradictions", []):
                for d_id in contra["domains"]:
                    if d_id in domain_results:
                        domain_results[d_id].contradictions.append(
                            f"Cross-domain: {contra['issue']} → {contra['resolution']}"
                        )

            # Store validation in state for later use
            current = state.get_current_version()
            if current:
                current.lore = current.lore or LoreData(universe_name=state.theme)
                current.lore.references = current.lore.references or []
                current.lore.references.append({
                    "type": "validation",
                    "data": validation,
                    "timestamp": datetime.utcnow().isoformat(),
                })

        except Exception as e:
            logger.warning(f"Cross-validation failed: {e}")

        return domain_results

    async def _build_lore_data(
        self,
        state: VersionedAddonState,
        domain_results: dict[str, ResearchResult]
    ) -> LoreData:
        """Build structured LoreData from domain results."""
        # Use LLM to extract structured entities, items, etc.
        synthesis_prompt = f"""Convert the following research domains for **{state.theme}** into structured Minecraft addon data.

**Domains:**
{json.dumps({k: {"name": v.domain_name, "content": v.content[:5000], "confidence": v.confidence, "mc_notes": v.minecraft_notes} for k, v in domain_results.items()}, indent=2)[:80000]}

**Output JSON matching this structure:**
```json
{{
  "universe_name": "Exact canonical name",
  "source_type": "anime|manga|light_novel|web_novel|movie|game|book|series",
  "summary": "2-3 paragraph overview",
  "entities": [
    {{"name": "internal_id", "display_name": "Display Name", "description": "...", "entity_type": "mob|boss|npc|player", "role": "...", "abilities": [], "stats": {{"health": 100, "damage": 10}}, "loot_table": [], "spawn_conditions": {{}}, "minecraft_hints": []}}
  ],
  "items": [
    {{"name": "internal_id", "display_name": "Display Name", "description": "...", "item_type": "sword|armor|consumable|material", "rarity": "common|uncommon|rare|epic|legendary", "stats": {{}}, "crafting_recipe": {{}}, "minecraft_hints": []}}
  ],
  "blocks": [
    {{"name": "internal_id", "display_name": "Display Name", "description": "...", "block_type": "natural|constructed|magical|mechanical", "properties": {{}}, "minecraft_hints": []}}
  ],
  "biomes": [
    {{"name": "internal_id", "display_name": "Display Name", "description": "...", "climate": "...", "features": [], "entities": [], "blocks": [], "is_dimension": false}}
  ],
  "mechanics": [
    {{"name": "internal_id", "description": "...", "implementation_hints": [], "related_entities": [], "related_items": []}}
  ],
  "references": []
}}
```"""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=synthesis_prompt)],
                task_type=TaskType.JSON_SCHEMA,
                temperature=0.2,
                max_tokens=12000,
            )
            lore_data = self._parse_llm_json(response.content)

            # Convert to LoreData objects
            lore = LoreData(
                universe_name=lore_data.get("universe_name", state.theme),
                source_type=lore_data.get("source_type", "unknown"),
                summary=lore_data.get("summary", ""),
                entities=[LoreEntity(**e) for e in lore_data.get("entities", [])],
                items=[LoreItem(**i) for i in lore_data.get("items", [])],
                blocks=[LoreBlock(**b) for b in lore_data.get("blocks", [])],
                biomes=[LoreBiome(**b) for b in lore_data.get("biomes", [])],
                mechanics=[LoreMechanic(**m) for m in lore_data.get("mechanics", [])],
                references=lore_data.get("references", []),
            )

            # Add domain research as extended references
            lore.references.extend([
                {
                    "domain": r.domain_id,
                    "name": r.domain_name,
                    "confidence": r.confidence,
                    "canon_status": r.canon_status,
                    "contradictions": r.contradictions,
                    "minecraft_notes": r.minecraft_notes,
                    "source_count": len(r.sources),
                }
                for r in domain_results.values()
            ])

            return lore

        except Exception as e:
            logger.error(f"Failed to build LoreData: {e}")
            return LoreData(universe_name=state.theme, summary="Research synthesis failed")

    async def _generate_minecraft_mapping(
        self,
        state: VersionedAddonState,
        lore: LoreData,
        domain_results: dict[str, ResearchResult]
    ):
        """Generate detailed Minecraft translation mapping and performance budgets."""
        current = state.get_current_version()
        if not current:
            return

        mapping_prompt = f"""Create a detailed Minecraft Bedrock 1.26.40+ translation map for **{state.theme}**.

**Lore Summary:** {lore.summary}
**Entities:** {len(lore.entities)} | **Items:** {len(lore.items)} | **Blocks:** {len(lore.blocks)} | **Biomes:** {len(lore.biomes)} | **Mechanics:** {len(lore.mechanics)}

**Domain Research Notes:**
{json.dumps({k: v.minecraft_notes for k, v in domain_results.items() if v.minecraft_notes}, indent=2)[:20000]}

**Output JSON:**
```json
{{
  "entity_mapping": [
    {{"lore_entity": "internal_id", "mc_entity_id": "namespace:id", "components": ["minecraft:health", "minecraft:damage"], "scripts": [], "animations": [], "particles": [], "sounds": []}}
  ],
  "item_mapping": [
    {{"lore_item": "internal_id", "mc_item_id": "namespace:id", "components": ["minecraft:durability", "minecraft:cooldown"], "custom_components": []}}
  ],
  "block_mapping": [],
  "biome_mapping": [],
  "mechanic_implementation": [
    {{"mechanic": "internal_id", "approach": "script|component|molang|animation", "complexity": "low|medium|high", "performance_cost": "low|medium|high", "dependencies": []}}
  ],
  "performance_budgets": {{
    "low_32bit_2gb": {{"max_entities": 20, "max_texture_mb": 20, "texture_res": 32, "use_pbr": false, "use_lod": true}},
    "mid_64bit_4gb": {{"max_entities": 50, "max_texture_mb": 60, "texture_res": 64, "use_pbr": true, "use_lod": true}},
    "high_64bit_8gb": {{"max_entities": 100, "max_texture_mb": 150, "texture_res": 128, "use_pbr": true, "use_lod": false}}
  }},
  "ui_concepts": [
    {{"type": "radial_menu|hud|custom_screen", "theme": "description", "inspiration": "itzriyo157-style buttons"}}
  ]
}}
```"""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=mapping_prompt)],
                task_type=TaskType.PLANNING,
                temperature=0.3,
                max_tokens=8000,
            )
            mapping = self._parse_llm_json(response.content)

            # Store in version
            current.lore = current.lore or lore
            current.lore.references = current.lore.references or []
            current.lore.references.append({
                "type": "minecraft_mapping",
                "data": mapping,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Initialize performance profiles
            budgets = mapping.get("performance_budgets", {})
            for tier in DeviceTier:
                tier_key = tier.value
                if tier_key in budgets:
                    b = budgets[tier_key]
                    current.performance_profiles[tier] = PerformanceProfile(
                        tier=tier,
                        estimated_ram_mb=b.get("max_texture_mb", 60) * 2,
                        estimated_texture_memory_mb=b.get("max_texture_mb", 60),
                        target_fps=60 if tier != DeviceTier.LOW_32BIT_2GB else 20,
                        texture_resolution=b.get("texture_res", 64),
                        use_pbr=b.get("use_pbr", False),
                        use_lod_models=b.get("use_lod", True),
                        max_entities=b.get("max_entities", 50),
                    )
                else:
                    current.performance_profiles[tier] = PerformanceProfile.for_tier(tier)

        except Exception as e:
            logger.warning(f"Minecraft mapping generation failed: {e}")
            # Default profiles
            for tier in DeviceTier:
                current.performance_profiles[tier] = PerformanceProfile.for_tier(tier)


# Singleton
_researcher: LoreDeepResearcher | None = None


def get_lore_deep_researcher() -> LoreDeepResearcher:
    global _researcher
    if _researcher is None:
        _researcher = LoreDeepResearcher()
    return _researcher


async def research_theme_deep(theme: str, description: str = "") -> LoreData:
    """Standalone deep research function."""
    researcher = get_lore_deep_researcher()
    state = VersionedAddonState(theme=theme, description=description)
    state = await researcher.research(state)
    if state.lore is None:
        raise RuntimeError(state.error_message or "Deep research failed")
    return state.lore
