"""
Enhanced Versioned State Schema for Addon Generation.

Extends AddonState with:
- Git-like version history (v0.0.1, v0.0.2, ...)
- Branching support for experimental changes
- Diff tracking between versions
- Preview images per version
- Changelog generation
- Device-tier performance profiles
- Community learning integration
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4
import json

from core.state import (
    AddonState,
    GenerationStatus,
    AssetType,
    GeneratedAsset,
    TextureAsset,
    ManifestData,
    LoreData,
    Edition,
)


# =============================================================================
# Version Control Types
# =============================================================================

class VersionStatus(str, Enum):
    """Status of a specific version."""
    DRAFT = "draft"              # Being worked on
    GENERATED = "generated"      # Successfully generated
    VALIDATED = "validated"      # Passed validation
    PUBLISHED = "published"      # Released to user
    ARCHIVED = "archived"        # Superseded
    FAILED = "failed"            # Generation failed


class DeviceTier(str, Enum):
    """Target device performance tiers."""
    LOW_32BIT_2GB = "low_32bit_2gb"      # 32-bit, 2GB RAM - minimal
    MID_64BIT_4GB = "mid_64bit_4gb"      # 64-bit, 4GB RAM - balanced
    HIGH_64BIT_8GB = "high_64bit_8gb"    # 64-bit, 8GB+ RAM - full quality
    AUTO = "auto"                         # Auto-detect at runtime


class FeedbackType(str, Enum):
    """Types of user feedback for version iteration."""
    CANON_CORRECTION = "canon_correction"       # "Novel says X, not Y"
    BALANCE_CHANGE = "balance_change"           # "Too OP/weak"
    BUG_REPORT = "bug_report"                   # "Crashes when..."
    FEATURE_REQUEST = "feature_request"         # "Add Z mechanic"
    STYLE_ADJUSTMENT = "style_adjustment"       # "Make it more anime"
    PERFORMANCE_ISSUE = "performance_issue"     # "Lags on my phone"
    UI_UX_ISSUE = "ui_ux_issue"                 # "Button hard to reach"


@dataclass
class VersionDiff:
    """Represents changes between two versions."""
    from_version: str
    to_version: str
    added_assets: list[str] = field(default_factory=list)
    modified_assets: list[str] = field(default_factory=list)
    removed_assets: list[str] = field(default_factory=list)
    lore_changes: list[dict[str, Any]] = field(default_factory=list)
    script_changes: list[dict[str, Any]] = field(default_factory=list)
    texture_changes: list[dict[str, Any]] = field(default_factory=list)
    model_changes: list[dict[str, Any]] = field(default_factory=list)
    performance_delta: dict[str, float] = field(default_factory=dict)
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserFeedback:
    """User feedback on a specific version."""
    id: str = field(default_factory=lambda: str(uuid4()))
    version: str = ""
    feedback_type: FeedbackType = FeedbackType.FEATURE_REQUEST
    title: str = ""
    description: str = ""
    canon_reference: str = ""           # e.g., "Chapter 234, paragraph 3"
    affected_assets: list[str] = field(default_factory=list)
    suggested_fix: str = ""
    priority: int = 3                   # 1=critical, 5=low
    status: str = "open"                # open, acknowledged, in_progress, resolved, rejected
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_version: str = ""


@dataclass
class PerformanceProfile:
    """Performance metrics for a specific device tier."""
    tier: DeviceTier
    estimated_ram_mb: float = 0.0
    estimated_texture_memory_mb: float = 0.0
    estimated_entity_count: int = 0
    target_fps: int = 60
    texture_resolution: int = 64
    use_pbr: bool = False
    use_lod_models: bool = False
    max_particles: int = 100
    max_entities: int = 50
    atlas_textures: bool = True
    simplify_models: bool = True
    reduced_animations: bool = False
    custom_settings: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def for_tier(cls, tier: DeviceTier) -> PerformanceProfile:
        """Get default profile for a device tier."""
        profiles = {
            DeviceTier.LOW_32BIT_2GB: cls(
                tier=tier,
                estimated_ram_mb=40.0,
                estimated_texture_memory_mb=20.0,
                target_fps=20,
                texture_resolution=32,
                use_pbr=False,
                use_lod_models=True,
                max_particles=30,
                max_entities=20,
                atlas_textures=True,
                simplify_models=True,
                reduced_animations=True,
            ),
            DeviceTier.MID_64BIT_4GB: cls(
                tier=tier,
                estimated_ram_mb=120.0,
                estimated_texture_memory_mb=60.0,
                target_fps=60,
                texture_resolution=64,
                use_pbr=True,
                use_lod_models=True,
                max_particles=100,
                max_entities=50,
                atlas_textures=True,
                simplify_models=False,
                reduced_animations=False,
            ),
            DeviceTier.HIGH_64BIT_8GB: cls(
                tier=tier,
                estimated_ram_mb=250.0,
                estimated_texture_memory_mb=150.0,
                target_fps=60,
                texture_resolution=128,
                use_pbr=True,
                use_lod_models=False,
                max_particles=300,
                max_entities=100,
                atlas_textures=False,
                simplify_models=False,
                reduced_animations=False,
            ),
            DeviceTier.AUTO: cls(
                tier=tier,
                estimated_ram_mb=120.0,
                estimated_texture_memory_mb=60.0,
                target_fps=60,
                texture_resolution=64,
                use_pbr=True,
                use_lod_models=True,
                max_particles=100,
                max_entities=50,
                atlas_textures=True,
                simplify_models=False,
                reduced_animations=False,
            ),
        }
        return profiles.get(tier, profiles[DeviceTier.MID_64BIT_4GB])


@dataclass
class AddonVersion:
    """A complete versioned addon snapshot."""
    version: str                          # e.g., "0.0.1", "0.0.2-beta"
    status: VersionStatus = VersionStatus.DRAFT
    base_version: str = ""                # Parent version (for branching)
    branch_name: str = "main"             # Git-like branch

    # Core addon data (snapshots)
    bp_assets: list[GeneratedAsset] = field(default_factory=list)
    rp_assets: list[GeneratedAsset] = field(default_factory=list)
    rp_textures: list[TextureAsset] = field(default_factory=list)
    bp_manifest: Optional[ManifestData] = None
    rp_manifest: Optional[ManifestData] = None

    # Lore & planning (can evolve)
    lore: Optional[LoreData] = None
    generation_plan: dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"            # "system", "user", "agent:name"
    changelog: str = ""
    preview_image_b64: str = ""           # Base64 encoded preview
    mcaddon_path: str = ""                # Path to generated .mcaddon
    zip_path: str = ""                    # Path to generated .zip

    # Performance
    performance_profiles: dict[DeviceTier, PerformanceProfile] = field(default_factory=dict)
    active_profile: DeviceTier = DeviceTier.AUTO

    # Feedback & iteration
    feedback: list[UserFeedback] = field(default_factory=list)
    resolved_feedback_ids: list[str] = field(default_factory=list)

    # Validation
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    schema_version: str = "1.26.40"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
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
            elif isinstance(value, dict):
                data[key] = {k: v.value if isinstance(v, Enum) else v for k, v in value.items()}
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AddonVersion:
        """Deserialize from dictionary."""
        # This is simplified - real implementation needs full deserialization
        version = cls(version=data.get("version", "0.0.1"))
        for key, value in data.items():
            if hasattr(version, key) and key not in ("version",):
                setattr(version, key, value)
        return version


@dataclass
class VersionedAddonState(AddonState):
    """
    Extended AddonState with full version control.
    Maintains backward compatibility with base AddonState.
    """

    # Version control
    versions: dict[str, AddonVersion] = field(default_factory=dict)
    current_version: str = "0.0.1"
    version_history: list[str] = field(default_factory=list)  # Ordered list of version strings
    branches: dict[str, str] = field(default_factory=dict)    # branch_name -> version

    # Global feedback across all versions
    all_feedback: list[UserFeedback] = field(default_factory=list)

    # Community learning
    learned_patterns: dict[str, Any] = field(default_factory=dict)
    last_community_sync: Optional[datetime] = None

    # Device targeting
    target_tiers: list[DeviceTier] = field(default_factory=lambda: [
        DeviceTier.LOW_32BIT_2GB,
        DeviceTier.MID_64BIT_4GB,
        DeviceTier.HIGH_64BIT_8GB,
    ])

    # Generation settings (persisted across versions)
    generation_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        # Initialize with first version if empty
        if not self.versions:
            self._create_initial_version()

    def _create_initial_version(self):
        """Create the initial v0.0.1 version."""
        v = AddonVersion(version="0.0.1", status=VersionStatus.DRAFT)
        self.versions["0.0.1"] = v
        self.current_version = "0.0.1"
        self.version_history = ["0.0.1"]
        self.branches["main"] = "0.0.1"

    def get_current_version(self) -> AddonVersion:
        """Get the currently active version."""
        return self.versions.get(self.current_version)

    def create_version(
        self,
        version: str,
        base_version: str = "",
        branch: str = "main",
        created_by: str = "system",
        changelog: str = "",
    ) -> AddonVersion:
        """Create a new version based on an existing one."""
        base = base_version or self.current_version
        base_ver = self.versions.get(base)
        if not base_ver:
            raise ValueError(f"Base version {base} not found")

        new_ver = AddonVersion(
            version=version,
            base_version=base,
            branch_name=branch,
            created_by=created_by,
            changelog=changelog,
            # Copy assets from base
            bp_assets=[a for a in base_ver.bp_assets],
            rp_assets=[a for a in base_ver.rp_assets],
            rp_textures=[t for t in base_ver.rp_textures],
            bp_manifest=base_ver.bp_manifest,
            rp_manifest=base_ver.rp_manifest,
            lore=base_ver.lore,
            generation_plan=base_ver.generation_plan.copy(),
            performance_profiles=base_ver.performance_profiles.copy(),
            active_profile=base_ver.active_profile,
            schema_version=base_ver.schema_version,
        )

        self.versions[version] = new_ver
        self.version_history.append(version)
        self.branches[branch] = version
        self.current_version = version

        return new_ver

    def get_version(self, version: str) -> Optional[AddonVersion]:
        """Get a specific version."""
        return self.versions.get(version)

    def get_diff(self, from_version: str, to_version: str) -> VersionDiff:
        """Compute diff between two versions."""
        v1 = self.versions.get(from_version)
        v2 = self.versions.get(to_version)
        if not v1 or not v2:
            raise ValueError("Version not found")

        # Simple asset name comparison
        v1_bp = {a.metadata.get("name", "") for a in v1.bp_assets}
        v2_bp = {a.metadata.get("name", "") for a in v2.bp_assets}
        v1_rp = {a.metadata.get("name", "") for a in v1.rp_assets}
        v2_rp = {a.metadata.get("name", "") for a in v2.rp_assets}

        diff = VersionDiff(
            from_version=from_version,
            to_version=to_version,
            added_assets=list((v2_bp | v2_rp) - (v1_bp | v1_rp)),
            modified_assets=list((v1_bp | v1_rp) & (v2_bp | v2_rp)),  # Simplified
            removed_assets=list((v1_bp | v1_rp) - (v2_bp | v2_rp)),
        )

        # Performance delta
        for tier in DeviceTier:
            p1 = v1.performance_profiles.get(tier)
            p2 = v2.performance_profiles.get(tier)
            if p1 and p2:
                diff.performance_delta[f"{tier.value}_ram_mb"] = p2.estimated_ram_mb - p1.estimated_ram_mb
                diff.performance_delta[f"{tier.value}_fps"] = p2.target_fps - p1.target_fps

        diff.summary = f"Version {from_version} → {to_version}: {len(diff.added_assets)} added, {len(diff.modified_assets)} modified, {len(diff.removed_assets)} removed"
        return diff

    def add_feedback(self, feedback: UserFeedback) -> str:
        """Add user feedback to the current version and global list."""
        current = self.get_current_version()
        if current:
            current.feedback.append(feedback)
        self.all_feedback.append(feedback)
        return feedback.id

    def resolve_feedback(self, feedback_id: str, resolved_version: str = "") -> bool:
        """Mark feedback as resolved."""
        for fb in self.all_feedback:
            if fb.id == feedback_id:
                fb.status = "resolved"
                fb.resolved_at = datetime.utcnow()
                fb.resolved_version = resolved_version or self.current_version
                current = self.get_current_version()
                if current and feedback_id not in current.resolved_feedback_ids:
                    current.resolved_feedback_ids.append(feedback_id)
                return True
        return False

    def sync_current_to_base(self):
        """Sync the current working state to the current version."""
        current = self.get_current_version()
        if not current:
            return

        # Sync base AddonState fields to version
        current.bp_assets = self.bp_assets.copy()
        current.rp_assets = self.rp_assets.copy()
        current.rp_textures = self.rp_textures.copy()
        current.bp_manifest = self.bp_manifest
        current.rp_manifest = self.rp_manifest
        current.lore = self.lore
        current.generation_plan = self.generation_plan.copy()
        current.updated_at = datetime.utcnow()

    def load_version(self, version: str) -> bool:
        """Load a version into the current working state."""
        ver = self.versions.get(version)
        if not ver:
            return False

        self.bp_assets = ver.bp_assets.copy()
        self.rp_assets = ver.rp_assets.copy()
        self.rp_textures = ver.rp_textures.copy()
        self.bp_manifest = ver.bp_manifest
        self.rp_manifest = ver.rp_manifest
        self.lore = ver.lore
        self.generation_plan = ver.generation_plan.copy()
        self.current_version = version
        return True

    def get_timeline(self) -> list[dict[str, Any]]:
        """Get version timeline for UI display."""
        timeline = []
        for v_str in self.version_history:
            v = self.versions.get(v_str)
            if v:
                timeline.append({
                    "version": v.version,
                    "status": v.status.value,
                    "branch": v.branch_name,
                    "created_at": v.created_at.isoformat(),
                    "changelog": v.changelog,
                    "has_preview": bool(v.preview_image_b64),
                    "has_mcaddon": bool(v.mcaddon_path),
                    "asset_count": len(v.bp_assets) + len(v.rp_assets),
                    "feedback_count": len(v.feedback),
                })
        return timeline

    def export_version_data(self, version: str) -> dict[str, Any]:
        """Export complete version data for download/backup."""
        ver = self.versions.get(version)
        if not ver:
            return {}
        return {
            "version": ver.to_dict(),
            "diff_from_base": self.get_diff(ver.base_version, version).to_dict() if ver.base_version else None,
            "timeline": self.get_timeline(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Full serialization including version history."""
        base_dict = super().to_dict()
        base_dict.update({
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "current_version": self.current_version,
            "version_history": self.version_history,
            "branches": self.branches,
            "all_feedback": [f.__dict__ for f in self.all_feedback],
            "learned_patterns": self.learned_patterns,
            "last_community_sync": self.last_community_sync.isoformat() if self.last_community_sync else None,
            "target_tiers": [t.value for t in self.target_tiers],
            "generation_config": self.generation_config,
        })
        return base_dict


# =============================================================================
# Convenience Functions
# =============================================================================

def create_versioned_state(theme: str, description: str = "", **kwargs) -> VersionedAddonState:
    """Create a new VersionedAddonState with initial version."""
    state = VersionedAddonState(theme=theme, description=description, **kwargs)
    state.generation_config = kwargs.get("generation_config", {})
    return state


def migrate_from_addon_state(old_state: AddonState) -> VersionedAddonState:
    """Migrate from old AddonState to VersionedAddonState."""
    new_state = VersionedAddonState(
        theme=old_state.theme,
        description=old_state.description,
        edition=old_state.edition,
        mc_version=old_state.mc_version,
        style=old_state.style,
        texture_resolution=old_state.texture_resolution,
        include_pbr=old_state.include_pbr,
        include_animations=old_state.include_animations,
        include_models=old_state.include_models,
        include_sounds=old_state.include_sounds,
        include_scripts=old_state.include_scripts,
        include_particles=old_state.include_particles,
        include_ui=old_state.include_ui,
        lore=old_state.lore,
        generation_plan=old_state.generation_plan,
        bp_assets=old_state.bp_assets,
        rp_assets=old_state.rp_assets,
        rp_textures=old_state.rp_textures,
        bp_manifest=old_state.bp_manifest,
        rp_manifest=old_state.rp_manifest,
        status=old_state.status,
        progress=old_state.progress,
        current_step=old_state.current_step,
        step_details=old_state.step_details,
        error_message=old_state.error_message,
        logs=old_state.logs,
        job_id=old_state.job_id,
        thread_id=old_state.thread_id,
    )
    return new_state
