"""
Community Learner Agent - Learns from top GitHub community addons.

Scans GitHub for popular Bedrock addons, analyzes their internal structure,
extracts patterns for entities, animations, scripts, textures, and applies
learned patterns to improve generation quality.
"""
from __future__ import __annotations__

import asyncio
import json
import logging
import os
import re
import tempfile
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from core.state import (
    VersionedAddonState,
    GenerationStatus,
    AssetType,
    GeneratedAsset,
    DeviceTier,
)
from core.versioned_state import VPPerformanceProfile
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class AddonPattern:
    """A learned pattern from community addons."""
    pattern_type: str  # "entity_ai", "texture_palette", "script_architecture", "animation_setup", etc.
    name: str
    description: str
    source_repos: list[str]
    frequency: int  # How many repos use this pattern
    code_example: str
    applicable_contexts: list[str]  # When to use this pattern
    quality_score: float  # 0.0 - 1.0
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RepoAnalysis:
    """Analysis results for a single repository."""
    repo_url: str
    repo_name: str
    stars: int
    last_updated: datetime
    structure: dict[str, Any]  # File/folder structure
    entities: list[dict] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    scripts: list[dict] = field(default_factory=list)
    animations: list[dict] = field(default_factory=list)
    render_controllers: list[dict] = field(default_factory=list)
    textures: list[dict] = field(default_factory=list)
    particles: list[dict] = field(default_factory=list)
    ui: list[dict] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)
    patterns_found: list[str] = field(default_factory=list)
    innovations: list[str] = field(default_factory=list)
    performance_tricks: list[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


class CommunityLearner:
    """
    Learns from community addons on GitHub.
    - Searches for popular Bedrock addon repos
    - Clones and analyzes internal structure
    - Extracts reusable patterns
    - Updates pattern database weekly
    """

    def __init__(self, github_token: str = None, cache_dir: str = "./community_cache"):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_db = self.cache_dir / "patterns.json"
        self.repos_db = self.cache_dir / "repos.json"
        self.router = get_router()
        self._load_patterns()

    def _load_patterns(self):
        """Load learned patterns from cache."""
        self.patterns: list[AddonPattern] = []
        self.analyzed_repos: list[RepoAnalysis] = []

        if self.patterns_db.exists():
            try:
                with open(self.patterns_db) as f:
                    data = json.load(f)
                self.patterns = [AddonPattern(**p) for p in data.get("patterns", [])]
                logger.info(f"Loaded {len(self.patterns)} community patterns")
            except Exception as e:
                logger.warning(f"Failed to load patterns: {e}")

        if self.repos_db.exists():
            try:
                with open(self.repos_db) as f:
                    data = json.load(f)
                self.analyzed_repos = [RepoAnalysis(**r) for r in data.get("repos", [])]
                logger.info(f"Loaded {len(self.analyzed_repos)} analyzed repos")
            except Exception as e:
                logger.warning(f"Failed to load repos: {e}")

    def _save_patterns(self):
        """Save patterns to cache."""
        try:
            with open(self.patterns_db, "w") as f:
                json.dump({
                    "patterns": [p.__dict__ for p in self.patterns],
                    "updated_at": datetime.utcnow().isoformat(),
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")

        try:
            with open(self.repos_db, "w") as f:
                json.dump({
                    "repos": [r.__dict__ for r in self.analyzed_repos],
                    "updated_at": datetime.utcnow().isoformat(),
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save repos: {e}")

    async def learn(self, state: VersionedAddonState, force_refresh: bool = False) -> VersionedAddonState:
        """Main learning routine - discovers and analyzes community addons."""
        current = state.get_current_version()
        if not current:
            return state

        # Check if we need to refresh (weekly)
        if not force_refresh and self._is_cache_fresh():
            state.add_log(f"Using cached patterns ({len(self.patterns)} patterns from {len(self.analyzed_repos)} repos)")
            await self._apply_learned_patterns(state)
            return state

        state.set_status(GenerationStatus.RESEARCHING, "community_learner",
                        "Discovering community addons on GitHub...")
        state.add_log("Searching GitHub for popular Bedrock addons...")

        # Discover repos
        repos = await self._discover_repos()
        state.add_log(f"Found {len(repos)} candidate repositories")

        # Analyze top repos (limit to avoid rate limits)
        analyzed = []
        for repo in repos[:10]:  # Top 10 per run
            try:
                analysis = await self._analyze_repo(repo)
                if analysis:
                    analyzed.append(analysis)
                    state.add_log(f"Analyzed: {analysis.repo_name} ({analysis.stars} stars)")
            except Exception as e:
                logger.warning(f"Failed to analyze {repo.get('full_name', 'unknown')}: {e}")

        # Extract patterns
        new_patterns = await self._extract_patterns(analyzed)
        state.add_log(f"Extracted {len(new_patterns)} new patterns")

        # Merge with existing patterns
        self._merge_patterns(new_patterns)
        self.analyzed_repos.extend(analyzed)
        self._save_patterns()

        # Apply to current generation
        await self._apply_learned_patterns(state)

        current.last_community_sync = datetime.utcnow()
        state.set_status(GenerationStatus.RESEARCHING, "community_learner",
                        f"Learning complete: {len(self.patterns)} total patterns")
        return state

    def _is_cache_fresh(self, max_age_days: int = 7) -> bool:
        """Check if pattern cache is fresh."""
        if not self.patterns:
            return False
        oldest = min(p.extracted_at for p in self.patterns)
        return (datetime.utcnow() - oldest).days < max_age_days

    async def _discover_repos(self) -> list[dict]:
        """Search GitHub for Bedrock addon repositories."""
        repos = []

        queries = [
            "minecraft bedrock addon stars:>100",
            "mcaddon stars:>50",
            "bedrock behavior pack stars:>50",
            "minecraft bedrock script stars:>50",
            "bedrock resource pack stars:>50",
        ]

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for query in queries:
                try:
                    url = "https://api.github.com/search/repositories"
                    params = {
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 20,
                    }
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("items", []):
                            repos.append({
                                "full_name": item["full_name"],
                                "url": item["html_url"],
                                "clone_url": item["clone_url"],
                                "stars": item["stargazers_count"],
                                "description": item["description"],
                                "language": item["language"],
                                "updated_at": item["updated_at"],
                                "topics": item.get("topics", []),
                            })
                    else:
                        logger.warning(f"GitHub search failed: {resp.status_code}")
                except Exception as e:
                    logger.warning(f"GitHub search error: {e}")

                await asyncio.sleep(1)  # Rate limit

        # Deduplicate and sort by stars
        seen = set()
        unique = []
        for r in repos:
            if r["full_name"] not in seen:
                seen.add(r["full_name"])
                unique.append(r)

        return sorted(unique, key=lambda x: x["stars"], reverse=True)

    async def _analyze_repo(self, repo: dict) -> Optional[RepoAnalysis]:
        """Clone and analyze a single repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / repo["full_name"].replace("/", "_")

            # Clone repo (shallow)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "git", "clone", "--depth", "1", "--branch", "main", repo["clone_url"], str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.wait(), timeout=60)
            except Exception:
                return None

            # Analyze structure
            structure = self._analyze_structure(repo_path)
            if not self._is_valid_addon(structure):
                return None

            # Extract assets
            analysis = RepoAnalysis(
                repo_url=repo["url"],
                repo_name=repo["full_name"],
                stars=repo["stars"],
                last_updated=datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00")),
                structure=structure,
            )

            # Parse BP assets
            bp_path = repo_path / "BP" / "behavior_packs" / "*"
            if not list(repo_path.glob("BP/*/manifest.json")):
                bp_path = repo_path / "behavior_pack"
            if not list(bp_path.glob("manifest.json")):
                bp_path = repo_path / "BP"

            rp_path = repo_path / "RP" / "resource_packs" / "*"
            if not list(repo_path.glob("RP/*/manifest.json")):
                rp_path = repo_path / "resource_pack"
            if not list(rp_path.glob("manifest.json")):
                rp_path = repo_path / "RP"

            analysis.entities = self._parse_json_files(bp_path / "entities", "entity")
            analysis.items = self._parse_json_files(bp_path / "items", "item")
            analysis.blocks = self._parse_json_files(bp_path / "blocks", "block")
            analysis.scripts = self._parse_scripts(bp_path / "scripts")
            analysis.manifest = self._parse_manifest(bp_path / "manifest.json")

            # Parse RP assets
            analysis.animations = self._parse_json_files(rp_path / "animations", "animation")
            analysis.render_controllers = self._parse_json_files(rp_path / "render_controllers", "render_controller")
            analysis.textures = self._scan_textures(rp_path / "textures")
            analysis.particles = self._parse_json_files(rp_path / "particles", "particle")
            analysis.ui = self._parse_json_files(rp_path / "ui", "ui")

            return analysis

    def _analyze_structure(self, path: Path) -> dict:
        """Analyze repository folder structure."""
        structure = {"folders": [], "files": [], "has_bp": False, "has_rp": False}
        for item in path.rglob("*"):
            rel = item.relative_to(path)
            if item.is_dir():
                structure["folders"].append(str(rel))
            else:
                structure["files"].append(str(rel))

        structure["has_bp"] = any("behavior" in f.lower() or "bp" in f.lower() for f in structure["folders"])
        structure["has_rp"] = any("resource" in f.lower() or "rp" in f.lower() for f in structure["folders"])
        return structure

    def _is_valid_addon(self, structure: dict) -> bool:
        """Check if repo contains a valid addon structure."""
        return structure["has_bp"] or structure["has_rp"]

    def _parse_json_files(self, path: Path, asset_type: str) -> list[dict]:
        """Parse all JSON files in a directory."""
        results = []
        if not path.exists():
            return results

        for json_file in path.rglob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                data["_source_file"] = str(json_file)
                data["_asset_type"] = asset_type
                results.append(data)
            except Exception:
                pass
        return results

    def _parse_scripts(self, path: Path) -> list[dict]:
        """Parse script files (JS/TS)."""
        results = []
        if not path.exists():
            return results

        for script_file in path.rglob("*.js"):
            try:
                with open(script_file) as f:
                    content = f.read()
                results.append({
                    "file": str(script_file),
                    "content": content[:5000],  # First 5000 chars
                    "lines": content.count("\n"),
                    "imports": self._extract_imports(content),
                    "exports": self._extract_exports(content),
                })
            except Exception:
                pass
        return results

    def _extract_imports(self, content: str) -> list[str]:
        """Extract import statements from JS."""
        imports = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("import ") or line.startswith("const ") and "require(" in line:
                imports.append(line[:200])
        return imports[:20]

    def _extract_exports(self, content: str) -> list[str]:
        """Extract export statements from JS."""
        exports = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("export ") or line.startswith("module.exports"):
                exports.append(line[:200])
        return exports[:20]

    def _parse_manifest(self, path: Path) -> dict:
        """Parse manifest.json."""
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _scan_textures(self, path: Path) -> list[dict]:
        """Scan texture files."""
        results = []
        if not path.exists():
            return results

        for tex_file in path.rglob("*.png"):
            try:
                rel = tex_file.relative_to(path)
                results.append({
                    "path": str(rel),
                    "size": tex_file.stat().st_size,
                    "name": tex_file.stem,
                })
            except Exception:
                pass
        return results

    async def _extract_patterns(self, analyses: list[RepoAnalysis]) -> list[AddonPattern]:
        """Extract reusable patterns from analyzed repos."""
        if not analyses:
            return []

        # Prepare summary for LLM
        summary = {
            "repos_analyzed": len(analyses),
            "total_entities": sum(len(a.entities) for a in analyses),
            "total_items": sum(len(a.items) for a in analyses),
            "total_scripts": sum(len(a.scripts) for a in analyses),
            "total_animations": sum(len(a.animations) for a in analyses),
            "common_structure": self._find_common_structure(analyses),
        }

        # Get example code snippets
        entity_examples = []
        for a in analyses[:3]:
            for e in a.entities[:2]:
                entity_examples.append({"repo": a.repo_name, "entity": e})

        script_examples = []
        for a in analyses[:3]:
            for s in a.scripts[:1]:
                script_examples.append({"repo": a.repo_name, "script": s})

        animation_examples = []
        for a in analyses[:3]:
            for anim in a.animations[:2]:
                animation_examples.append({"repo": a.repo_name, "animation": anim})

        prompt = f"""Analyze these community Bedrock addon repositories and extract reusable patterns.

**Repository Summary:**
{json.dumps(summary, indent=2)}

**Entity Examples (sample):**
{json.dumps(entity_examples[:5], indent=2)[:10000]}

**Script Examples (sample):**
{json.dumps(script_examples[:3], indent=2)[:10000]}

**Animation Examples (sample):**
{json.dumps(animation_examples[:5], indent=2)[:10000]}

**Extract patterns in these categories:**
1. entity_ai - AI goal patterns, behavior trees
2. entity_components - Component combinations that work well
3. script_architecture - Module structure, event handling, systems
4. animation_setup - Animation controller patterns, blend trees
5. render_controller - Layer setup, material switching, geometry switching
6. texture_palette - Color schemes, style consistency
7. particle_systems - Emitter patterns, performance tricks
8. ui_patterns - Custom UI, HUDs, radial menus (itzriyo157 style)
9. performance_tricks - Object pooling, culling, LOD, atlasing
10. manifest_config - Dependencies, versioning, module setup

**Output JSON array of patterns:**
```json
[
  {{
    "pattern_type": "entity_ai",
    "name": "Descriptive name",
    "description": "What this pattern does and when to use it",
    "source_repos": ["repo1", "repo2"],
    "frequency": 5,
    "code_example": "Representative code snippet",
    "applicable_contexts": ["boss_mob", "pet", "npc"],
    "quality_score": 0.9
  }}
]
```"""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                task_type=TaskType.REASONING,
                temperature=0.3,
                max_tokens=12000,
            )
            patterns_data = json.loads(self._extract_json(response.content))

            patterns = []
            for p in patterns_data:
                patterns.append(AddonPattern(
                    pattern_type=p.get("pattern_type", "unknown"),
                    name=p.get("name", "Unnamed"),
                    description=p.get("description", ""),
                    source_repos=p.get("source_repos", []),
                    frequency=p.get("frequency", 1),
                    code_example=p.get("code_example", ""),
                    applicable_contexts=p.get("applicable_contexts", []),
                    quality_score=p.get("quality_score", 0.5),
                ))

            return patterns

        except Exception as e:
            logger.error(f"Pattern extraction failed: {e}")
            return []

    def _find_common_structure(self, analyses: list[RepoAnalysis]) -> dict:
        """Find common folder/file structures."""
        folder_counts = {}
        for a in analyses:
            for f in a.structure.get("folders", []):
                folder_counts[f] = folder_counts.get(f, 0) + 1

        return {
            "universal_folders": [f for f, c in folder_counts.items() if c == len(analyses)],
            "common_folders": [f for f, c in folder_counts.items() if c > len(analyses) * 0.5],
        }

    def _merge_patterns(self, new_patterns: list[AddonPattern]):
        """Merge new patterns with existing, updating frequency and quality."""
        for new_p in new_patterns:
            # Find existing similar pattern
            existing = None
            for p in self.patterns:
                if p.pattern_type == new_p.pattern_type and p.name == new_p.name:
                    existing = p
                    break

            if existing:
                # Update existing
                existing.frequency += new_p.frequency
                existing.source_repos = list(set(existing.source_repos + new_p.source_repos))
                existing.quality_score = max(existing.quality_score, new_p.quality_score)
                existing.extracted_at = datetime.utcnow()
            else:
                # Add new
                self.patterns.append(new_p)

    async def _apply_learned_patterns(self, state: VersionedAddonState):
        """Apply learned patterns to current generation."""
        current = state.get_current_version()
        if not current:
            return

        # Store patterns in version for downstream agents
        current.learned_patterns = {
            "patterns": [
                {
                    "type": p.pattern_type,
                    "name": p.name,
                    "description": p.description,
                    "code": p.code_example,
                    "contexts": p.applicable_contexts,
                    "quality": p.quality_score,
                    "sources": p.source_repos,
                }
                for p in self.patterns
            ],
            "repo_count": len(self.analyzed_repos),
            "last_sync": current.last_community_sync.isoformat() if current.last_community_sync else None,
        }

        # Also add to state for global access
        state.learned_patterns = current.learned_patterns

    def get_patterns_for_context(self, context: str, pattern_type: str = None) -> list[AddonPattern]:
        """Get patterns applicable to a specific context."""
        results = []
        for p in self.patterns:
            if context in p.applicable_contexts or "all" in p.applicable_contexts:
                if pattern_type is None or p.pattern_type == pattern_type:
                    results.append(p)
        return sorted(results, key=lambda x: x.quality_score, reverse=True)

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
_learner: CommunityLearner | None = None


def get_community_learner() -> CommunityLearner:
    global _learner
    if _learner is None:
        _learner = CommunityLearner()
    return _learner
