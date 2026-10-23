"""
MC Schema Expert Agent - Bedrock 1.26.40+ JSON schema authority.

Maintains up-to-date schemas, validates generated JSON, handles migrations,
and provides schema-aware generation hints.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx

from core.state import (
    VersionedAddonState,
    GenerationStatus,
    AssetType,
    GeneratedAsset,
    Edition,
)
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


# =============================================================================
# Schema Definitions
# =============================================================================

BEDROCK_SCHEMAS_URL = "https://raw.githubusercontent.com/bedrock-studio/bedrock-json-schemas/main/schemas"

# Core schema files for Bedrock 1.26.40+
SCHEMA_FILES = {
    # Behavior Pack
    "entity": "entity.json",
    "item": "item.json",
    "block": "block.json",
    "loot_table": "loot_table.json",
    "spawn_rule": "spawn_rule.json",
    "recipe": "recipe.json",
    "trade_table": "trade_table.json",
    "biome": "biome.json",
    "feature": "feature.json",
    "structure": "structure.json",
    "script": "script.json",

    # Resource Pack
    "entity_rp": "entity.resource.json",
    "render_controller": "render_controller.json",
    "animation": "animation.json",
    "animation_controller": "animation_controller.json",
    "geometry": "geometry.json",
    "material": "material.json",
    "particle": "particle.json",
    "sound": "sound.json",
    "ui": "ui.json",

    # Manifests
    "manifest_bp": "manifest.behavior_pack.json",
    "manifest_rp": "manifest.resource_pack.json",
}


@dataclass
class SchemaInfo:
    """Information about a schema."""
    name: str
    version: str
    file_path: str
    schema: dict[str, Any]
    last_updated: datetime
    description: str = ""


@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    asset_type: str = ""
    asset_name: str = ""


class MCSchemaExpert:
    """
    Bedrock JSON Schema Expert.
    - Auto-syncs schemas from GitHub
    - Validates all generated assets
    - Provides schema-aware generation hints
    - Handles version migrations
    """

    def __init__(self, cache_dir: str = "./schema_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.schemas: dict[str, SchemaInfo] = {}
        self.router = get_router()
        self._load_cached_schemas()

    def _load_cached_schemas(self):
        """Load schemas from local cache."""
        for name, filename in SCHEMA_FILES.items():
            path = self.cache_dir / filename
            if path.exists():
                try:
                    with open(path) as f:
                        schema = json.load(f)
                    self.schemas[name] = SchemaInfo(
                        name=name,
                        version="1.26.40",
                        file_path=str(path),
                        schema=schema,
                        last_updated=datetime.fromtimestamp(path.stat().st_mtime),
                    )
                except Exception as e:
                    logger.warning(f"Failed to load cached schema {name}: {e}")

    async def sync_schemas(self, force: bool = False) -> dict[str, bool]:
        """Sync schemas from GitHub repository."""
        results = {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for name, filename in SCHEMA_FILES.items():
                if not force and name in self.schemas:
                    results[name] = True
                    continue

                url = f"{BEDROCK_SCHEMAS_URL}/{filename}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        schema = resp.json()
                        path = self.cache_dir / filename
                        with open(path, "w") as f:
                            json.dump(schema, f, indent=2)

                        self.schemas[name] = SchemaInfo(
                            name=name,
                            version="1.26.40",
                            file_path=str(path),
                            schema=schema,
                            last_updated=datetime.utcnow(),
                        )
                        results[name] = True
                        logger.info(f"Synced schema: {name}")
                    else:
                        results[name] = False
                        logger.warning(f"Schema not found: {url}")
                except Exception as e:
                    results[name] = False
                    logger.error(f"Failed to sync {name}: {e}")

        return results

    def get_schema(self, asset_type: AssetType | str) -> Optional[dict]:
        """Get schema for an asset type."""
        if isinstance(asset_type, AssetType):
            key = asset_type.value
        else:
            key = asset_type

        # Map asset types to schema keys
        mapping = {
            "entity": "entity",
            "item": "item",
            "block": "block",
            "loot_table": "loot_table",
            "spawn_rule": "spawn_rule",
            "recipe": "recipe",
            "biome": "biome",
            "render_controller": "render_controller",
            "animation": "animation",
            "anim_controller": "animation_controller",
            "geometry": "geometry",
            "particle": "particle",
            "sound": "sound",
            "ui": "ui",
            "manifest": "manifest_bp",
        }

        schema_key = mapping.get(key, key)
        info = self.schemas.get(schema_key)
        return info.schema if info else None

    def validate_asset(self, asset: GeneratedAsset) -> ValidationResult:
        """Validate a generated asset against its schema."""
        schema = self.get_schema(asset.asset_type)
        if not schema:
            return ValidationResult(
                valid=True,
                warnings=[f"No schema for {asset.asset_type}"],
                asset_type=asset.asset_type.value,
                asset_name=asset.metadata.get("name", "unknown"),
            )

        # Basic validation (jsonschema would be better but adds dependency)
        errors = []
        warnings = []

        content = asset.content
        if not isinstance(content, dict):
            errors.append("Content is not a valid JSON object")
            return ValidationResult(
                valid=False,
                errors=errors,
                asset_type=asset.asset_type.value,
                asset_name=asset.metadata.get("name", "unknown"),
            )

        # Check required fields based on asset type
        required = self._get_required_fields(asset.asset_type)
        for field in required:
            if field not in content:
                errors.append(f"Missing required field: {field}")

        # Check format_version
        if "format_version" not in content:
            warnings.append("Missing format_version")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            asset_type=asset.asset_type.value,
            asset_name=asset.metadata.get("name", "unknown"),
        )

    def _get_required_fields(self, asset_type: AssetType) -> list[str]:
        """Get required fields for an asset type."""
        base = ["format_version"]
        specific = {
            AssetType.ENTITY: ["minecraft:entity"],
            AssetType.ITEM: ["minecraft:item"],
            AssetType.BLOCK: ["minecraft:block"],
            AssetType.LOOT_TABLE: ["pools"],
            AssetType.SPAWN_RULE: ["minecraft:spawn_rules"],
            AssetType.RECIPE: ["type"],
            AssetType.ANIMATION: ["animation"],
            AssetType.ANIM_CONTROLLER: ["animation_controllers"],
            AssetType.RENDER_CONTROLLER: ["render_controllers"],
            AssetType.GEOMETRY: ["geometry"],
            AssetType.PARTICLE: ["particle_effect"],
            AssetType.MANIFEST: ["header", "modules"],
        }
        return base + specific.get(asset_type, [])

    def get_generation_hints(self, asset_type: AssetType) -> dict[str, Any]:
        """Get schema-aware generation hints for an asset type."""
        schema = self.get_schema(asset_type)
        if not schema:
            return {}

        hints = {
            "required_fields": self._get_required_fields(asset_type),
            "common_components": self._get_common_components(asset_type),
            "format_version": self._get_latest_format_version(asset_type),
            "examples": self._get_examples(asset_type),
        }
        return hints

    def _get_common_components(self, asset_type: AssetType) -> list[str]:
        """Get commonly used components for an asset type."""
        components = {
            AssetType.ENTITY: [
                "minecraft:type_family",
                "minecraft:health",
                "minecraft:movement",
                "minecraft:navigation.walk",
                "minecraft:behavior.nearest_attackable_target",
                "minecraft:behavior.melee_attack",
                "minecraft:loot",
                "minecraft:damage_sensor",
            ],
            AssetType.ITEM: [
                "minecraft:max_stack_size",
                "minecraft:hand_equipped",
                "minecraft:durability",
                "minecraft:cooldown",
                "minecraft:food",
                "minecraft:enchantable",
            ],
            AssetType.BLOCK: [
                "minecraft:destructible_by_mining",
                "minecraft:destructible_by_explosion",
                "minecraft:flammable",
                "minecraft:map_color",
                "minecraft:light_emission",
            ],
        }
        return components.get(asset_type, [])

    def _get_latest_format_version(self, asset_type: AssetType) -> str:
        """Get latest format_version for asset type (Bedrock 1.26.40+)."""
        versions = {
            AssetType.ENTITY: "1.20.10",
            AssetType.ITEM: "1.20.0",
            AssetType.BLOCK: "1.21.0",
            AssetType.LOOT_TABLE: "1.21.0",
            AssetType.SPAWN_RULE: "1.21.0",
            AssetType.RECIPE: "1.12.0",
            AssetType.ANIMATION: "1.10.0",
            AssetType.ANIM_CONTROLLER: "1.10.0",
            AssetType.RENDER_CONTROLLER: "1.10.0",
            AssetType.GEOMETRY: "1.21.0",
            AssetType.PARTICLE: "1.10.0",
            AssetType.MANIFEST: "2",
        }
        return versions.get(asset_type, "1.20.0")

    def _get_examples(self, asset_type: AssetType) -> dict:
        """Get example JSON for asset type."""
        examples = {
            AssetType.ENTITY: {
                "format_version": "1.20.10",
                "minecraft:entity": {
                    "description": {
                        "identifier": "namespace:entity_name",
                        "is_spawnable": True,
                        "is_summonable": True,
                        "is_experimental": False,
                    },
                    "components": {
                        "minecraft:type_family": {"family": ["mob"]},
                        "minecraft:health": {"value": 20, "max": 20},
                        "minecraft:movement": {"value": 0.25},
                    },
                },
            },
            AssetType.ITEM: {
                "format_version": "1.20.0",
                "minecraft:item": {
                    "description": {"identifier": "namespace:item_name"},
                    "components": {
                        "minecraft:max_stack_size": 1,
                        "minecraft:hand_equipped": True,
                        "minecraft:durability": {"max_durability": 100},
                    },
                },
            },
        }
        return examples.get(asset_type, {})

    async def validate_all_assets(self, state: VersionedAddonState) -> VersionedAddonState:
        """Validate all assets in current version."""
        current = state.get_current_version()
        if not current:
            return state

        state.set_status(GenerationStatus.VALIDATING, "mc_schema_expert",
                        "Validating all assets against Bedrock schemas...")

        all_errors = []
        all_warnings = []

        for asset in current.bp_assets + current.rp_assets:
            result = self.validate_asset(asset)
            if not result.valid:
                all_errors.extend([f"{result.asset_name}: {e}" for e in result.errors])
            all_warnings.extend([f"{result.asset_name}: {w}" for w in result.warnings])

        # Validate manifests
        if current.bp_manifest:
            result = self.validate_asset(GeneratedAsset(
                asset_type=AssetType.MANIFEST,
                content=current.bp_manifest.__dict__,
                metadata={"name": "manifest_bp"},
            ))
            all_errors.extend([f"BP Manifest: {e}" for e in result.errors])

        if current.rp_manifest:
            result = self.validate_asset(GeneratedAsset(
                asset_type=AssetType.MANIFEST,
                content=current.rp_manifest.__dict__,
                metadata={"name": "manifest_rp"},
            ))
            all_errors.extend([f"RP Manifest: {e}" for e in result.errors])

        current.validation_errors = all_errors
        current.validation_warnings = all_warnings

        if all_errors:
            state.set_status(GenerationStatus.VALIDATING, "mc_schema_expert",
                            f"Validation failed: {len(all_errors)} errors")
            state.error_message = f"Schema validation errors: {len(all_errors)}"
        else:
            state.set_status(GenerationStatus.VALIDATING, "mc_schema_expert",
                            f"Validation passed: {len(all_warnings)} warnings")

        return state

    async def migrate_asset(self, asset: GeneratedAsset, from_version: str, to_version: str) -> GeneratedAsset:
        """Migrate asset between schema versions."""
        # This would use LLM to intelligently migrate
        prompt = f"""Migrate this Bedrock {asset.asset_type.value} JSON from format_version {from_version} to {to_version}.

**Current JSON:**
{json.dumps(asset.content, indent=2)}

**Output:** Migrated JSON with updated format_version and any required schema changes.
Only output the JSON, no explanation."""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                task_type=TaskType.JSON_SCHEMA,
                temperature=0.1,
                max_tokens=4000,
            )
            migrated = json.loads(self._extract_json(response.content))
            asset.content = migrated
            asset.metadata["migrated_from"] = from_version
            asset.metadata["migrated_to"] = to_version
            asset.metadata["migrated_at"] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"Migration failed: {e}")

        return asset

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
_expert: MCSchemaExpert | None = None


def get_mc_schema_expert() -> MCSchemaExpert:
    global _expert
    if _expert is None:
        _expert = MCSchemaExpert()
    return _expert
