"""
Shared State Schema for Addon Generation.

Defines the complete state that flows through the LangGraph orchestration.
All agents read from and write to this shared state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================

class Edition(str, Enum):
    BEDROCK = "bedrock"
    JAVA = "java"
    BOTH = "both"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    RESEARCHING = "researching"
    PLANNING = "planning"
    GENERATING_BP = "generating_bp"
    GENERATING_RP = "generating_rp"
    GENERATING_TEXTURES = "generating_textures"
    GENERATING_MODELS = "generating_models"
    VALIDATING = "validating"
    PACKAGING = "packaging"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(str, Enum):
    ENTITY = "entity"
    ITEM = "item"
    BLOCK = "block"
    LOOT_TABLE = "loot_table"
    SPAWN_RULE = "spawn_rule"
    RECIPE = "recipe"
    SCRIPT = "script"
    MODEL = "model"
    ANIMATION = "animation"
    ANIM_CONTROLLER = "anim_controller"
    RENDER_CONTROLLER = "render_controller"
    PARTICLE = "particle"
    SOUND = "sound"
    TEXTURE = "texture"
    UI = "ui"
    MANIFEST = "manifest"


# =============================================================================
# Lore / Research Data
# =============================================================================

@dataclass
class LoreEntity:
    """An entity (mob, boss, NPC) from the source universe."""
    name: str
    display_name: str
    description: str
    role: str  # boss, minion, neutral, pet, mount
    abilities: list[str]
    visual_description: str
    size_category: str  # small, medium, large, giant
    biome_tags: list[str] = field(default_factory=list)
    loot_drops: list[str] = field(default_factory=list)
    health: int = 20
    damage: int = 3
    speed: float = 0.25
    is_tameable: bool = False
    is_rideable: bool = False


@dataclass
class LoreItem:
    """An item (weapon, tool, consumable, material) from the source universe."""
    name: str
    display_name: str
    description: str
    item_type: str  # sword, bow, armor, consumable, material, special
    rarity: str  # common, uncommon, rare, epic, legendary, mythic
    abilities: list[str] = field(default_factory=list)
    visual_description: str = ""
    durability: int = 0
    damage: int = 0
    cooldown: float = 0.0
    stack_size: int = 64
    crafting_materials: list[str] = field(default_factory=list)


@dataclass
class LoreBlock:
    """A block from the source universe."""
    name: str
    display_name: str
    description: str
    block_type: str  # ore, decorative, functional, storage, special
    hardness: float = 1.0
    resistance: float = 1.0
    harvest_tool: str = "pickaxe"
    harvest_level: int = 0
    light_level: int = 0
    visual_description: str = ""
    drops: list[str] = field(default_factory=list)


@dataclass
class LoreBiome:
    """A biome/dimension from the source universe."""
    name: str
    display_name: str
    description: str
    temperature: float = 0.5
    humidity: float = 0.5
    features: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    is_dimension: bool = False


@dataclass
class LoreMechanic:
    """A gameplay mechanic/system from the source universe."""
    name: str
    description: str
    implementation_hints: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    related_items: list[str] = field(default_factory=list)


@dataclass
class LoreData:
    """Complete lore research for a universe."""
    universe_name: str
    source_type: str  # anime, manga, light_novel, web_novel, movie, game, book
    summary: str
    entities: list[LoreEntity] = field(default_factory=list)
    items: list[LoreItem] = field(default_factory=list)
    blocks: list[LoreBlock] = field(default_factory=list)
    biomes: list[LoreBiome] = field(default_factory=list)
    mechanics: list[LoreMechanic] = field(default_factory=list)
    references: list[str] = field(default_factory=list)  # URLs, wiki pages
    researched_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Generated Assets
# =============================================================================

@dataclass
class GeneratedAsset:
    """A generated asset file."""
    asset_type: AssetType
    file_path: str  # Relative path in BP or RP
    content: dict[str, Any] | str  # JSON dict or raw text (scripts)
    minecraft_version: str = "26.40"
    edition: Edition = Edition.BEDROCK
    metadata: dict[str, Any] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TextureAsset:
    """A generated texture with variants."""
    name: str
    base_path: str  # e.g., "textures/entity/shadow_slave"
    diffuse: bytes  # Base color / albedo
    normal: Optional[bytes] = None
    roughness: Optional[bytes] = None
    metallic: Optional[bytes] = None
    emissive: Optional[bytes] = None
    height: Optional[bytes] = None
    animated_frames: list[bytes] = field(default_factory=list)
    frame_duration: int = 100  # ms per frame
    resolution: tuple[int, int] = (64, 64)
    format: str = "png"


@dataclass
class ModelAsset:
    """A 3D model (Blockbench .geo.json or GLB)."""
    name: str
    geometry: dict[str, Any]  # .geo.json content
    texture_mappings: dict[str, str] = field(default_factory=dict)  # bone -> texture path
    animations: list[str] = field(default_factory=list)  # Animation names
    glb_data: Optional[bytes] = None  # Raw GLB if available


# =============================================================================
# Manifest
# =============================================================================

@dataclass
class ManifestData:
    """Manifest.json for BP or RP."""
    name: str
    description: str
    uuid: str
    version: list[int] = field(default_factory=lambda: [1, 0, 0])
    min_engine_version: list[int] = field(default_factory=lambda: [1, 26, 0])
    modules: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    pack_scope: str = "world"


# =============================================================================
# Validation
# =============================================================================

@dataclass
class ValidationError:
    """A validation error for an asset."""
    asset_path: str
    error_type: str  # schema, syntax, reference, logic
    message: str
    severity: str = "error"  # error, warning, info
    line: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None


# =============================================================================
# Main State
# =============================================================================

@dataclass
class AddonState:
    """
    Complete state for addon generation.
    This flows through all agents in the LangGraph.
    """
    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------
    session_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # -------------------------------------------------------------------------
    # User Input
    # -------------------------------------------------------------------------
    theme: str = ""  # "Shadow Slave", "Naruto", "Elden Ring", etc.
    description: str = ""  # User's custom description
    mc_version: str = "26.40"
    edition: Edition = Edition.BEDROCK
    style_preference: str = "vanilla"  # vanilla, rtx, medieval, modern, anime
    texture_resolution: int = 64  # 16, 32, 64, 128, 256
    include_pbr: bool = True
    include_animations: bool = True
    include_sounds: bool = False
    include_scripts: bool = True

    # -------------------------------------------------------------------------
    # Research Phase
    # -------------------------------------------------------------------------
    lore: Optional[LoreData] = None
    research_complete: bool = False
    research_notes: str = ""

    # -------------------------------------------------------------------------
    # Planning Phase
    # -------------------------------------------------------------------------
    plan: Optional[dict[str, Any]] = None  # Architect's plan
    planned_entities: list[str] = field(default_factory=list)
    planned_items: list[str] = field(default_factory=list)
    planned_blocks: list[str] = field(default_factory=list)
    planned_biomes: list[str] = field(default_factory=list)
    planned_mechanics: list[str] = field(default_factory=list)
    plan_complete: bool = False

    # -------------------------------------------------------------------------
    # Generated Assets (Behavior Pack)
    # -------------------------------------------------------------------------
    bp_assets: list[GeneratedAsset] = field(default_factory=list)
    bp_entities: list[GeneratedAsset] = field(default_factory=list)
    bp_items: list[GeneratedAsset] = field(default_factory=list)
    bp_blocks: list[GeneratedAsset] = field(default_factory=list)
    bp_loot_tables: list[GeneratedAsset] = field(default_factory=list)
    bp_spawn_rules: list[GeneratedAsset] = field(default_factory=list)
    bp_recipes: list[GeneratedAsset] = field(default_factory=list)
    bp_scripts: list[GeneratedAsset] = field(default_factory=list)
    bp_manifest: Optional[ManifestData] = None

    # -------------------------------------------------------------------------
    # Generated Assets (Resource Pack)
    # -------------------------------------------------------------------------
    rp_assets: list[GeneratedAsset] = field(default_factory=list)
    rp_models: list[ModelAsset] = field(default_factory=list)
    rp_animations: list[GeneratedAsset] = field(default_factory=list)
    rp_anim_controllers: list[GeneratedAsset] = field(default_factory=list)
    rp_render_controllers: list[GeneratedAsset] = field(default_factory=list)
    rp_particles: list[GeneratedAsset] = field(default_factory=list)
    rp_sounds: list[GeneratedAsset] = field(default_factory=list)
    rp_textures: list[TextureAsset] = field(default_factory=list)
    rp_ui: list[GeneratedAsset] = field(default_factory=list)
    rp_manifest: Optional[ManifestData] = None

    # -------------------------------------------------------------------------
    # Validation & Testing
    # -------------------------------------------------------------------------
    validation_errors: list[ValidationError] = field(default_factory=list)
    validation_passed: bool = False
    test_results: dict[str, Any] = field(default_factory=dict)
    tests_passed: bool = False

    # -------------------------------------------------------------------------
    # Packaging
    # -------------------------------------------------------------------------
    bp_zip_path: Optional[str] = None
    rp_zip_path: Optional[str] = None
    mcaddon_path: Optional[str] = None
    mcpack_paths: list[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Status & Progress
    # -------------------------------------------------------------------------
    status: GenerationStatus = GenerationStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    current_step: str = ""
    step_details: str = ""
    error_message: Optional[str] = None
    logs: list[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    generation_time_seconds: float = 0.0
    tokens_used: int = 0
    api_calls: int = 0
    estimated_cost_usd: float = 0.0

    def add_log(self, message: str):
        """Add a log entry with timestamp."""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        self.updated_at = datetime.utcnow()

    def set_status(self, status: GenerationStatus, step: str = "", details: str = ""):
        """Update status and progress."""
        self.status = status
        self.current_step = step
        self.step_details = details
        self.add_log(f"Status: {status.value} - {step}: {details}")

    def add_asset(self, asset: GeneratedAsset):
        """Add a generated asset to appropriate list."""
        self.bp_assets.append(asset)
        if asset.asset_type == AssetType.ENTITY:
            self.bp_entities.append(asset)
        elif asset.asset_type == AssetType.ITEM:
            self.bp_items.append(asset)
        elif asset.asset_type == AssetType.BLOCK:
            self.bp_blocks.append(asset)
        elif asset.asset_type == AssetType.LOOT_TABLE:
            self.bp_loot_tables.append(asset)
        elif asset.asset_type == AssetType.SPAWN_RULE:
            self.bp_spawn_rules.append(asset)
        elif asset.asset_type == AssetType.RECIPE:
            self.bp_recipes.append(asset)
        elif asset.asset_type == AssetType.SCRIPT:
            self.bp_scripts.append(asset)
        elif asset.asset_type == AssetType.MANIFEST:
            self.bp_manifest = ManifestData(**asset.content) if isinstance(asset.content, dict) else None
        self.updated_at = datetime.utcnow()

    def add_rp_asset(self, asset: GeneratedAsset):
        """Add a resource pack asset."""
        self.rp_assets.append(asset)
        if asset.asset_type == AssetType.MODEL:
            self.rp_models.append(ModelAsset(**asset.content))
        elif asset.asset_type == AssetType.ANIMATION:
            self.rp_animations.append(asset)
        elif asset.asset_type == AssetType.ANIM_CONTROLLER:
            self.rp_anim_controllers.append(asset)
        elif asset.asset_type == AssetType.RENDER_CONTROLLER:
            self.rp_render_controllers.append(asset)
        elif asset.asset_type == AssetType.PARTICLE:
            self.rp_particles.append(asset)
        elif asset.asset_type == AssetType.SOUND:
            self.rp_sounds.append(asset)
        elif asset.asset_type == AssetType.UI:
            self.rp_ui.append(asset)
        elif asset.asset_type == AssetType.MANIFEST:
            self.rp_manifest = ManifestData(**asset.content) if isinstance(asset.content, dict) else None
        self.updated_at = datetime.utcnow()

    def add_texture(self, texture: TextureAsset):
        """Add a texture asset."""
        self.rp_textures.append(texture)
        self.updated_at = datetime.utcnow()

    def get_asset(self, asset_type: AssetType, name: str) -> Optional[GeneratedAsset]:
        """Find an asset by type and name."""
        for asset in self.bp_assets + self.rp_assets:
            if asset.asset_type == asset_type and asset.metadata.get("name") == name:
                return asset
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict (for Redis/DB storage)."""
        # Custom serialization for complex types
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, (datetime, UUID)):
                data[key] = str(value)
            elif isinstance(value, Enum):
                data[key] = value.value
            elif isinstance(value, list):
                data[key] = [v.to_dict() if hasattr(v, 'to_dict') else v for v in value]
            elif hasattr(value, 'to_dict'):
                data[key] = value.to_dict()
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AddonState:
        """Deserialize from dict."""
        # This is a simplified version - real implementation would need full deserialization
        state = cls()
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state
