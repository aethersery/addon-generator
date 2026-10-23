"""
Addon Generator Core Package.

Exports core state management, versioned state, and shared types.
"""
from __future__ import annotations

from .state import (
    AddonState,
    LoreData,
    LoreEntity,
    LoreItem,
    LoreBlock,
    LoreBiome,
    LoreMechanic,
    GenerationStatus,
    Edition,
    AssetType,
    GeneratedAsset,
    TextureAsset,
    ManifestData,
    DeviceTier,
    PerformanceProfile,
)

from .versioned_state import (
    VersionedAddonState,
    AddonVersion,
    VersionDiff,
    UserFeedback,
    FeedbackType,
    VersionStatus,
    PerformanceProfile as VPPerformanceProfile,
    DeviceTier as VDeviceTier,
    create_versioned_state,
    migrate_from_addon_state,
)

__all__ = [
    # Base state
    "AddonState",
    "LoreData",
    "LoreEntity",
    "LoreItem",
    "LoreBlock",
    "LoreBiome",
    "LoreMechanic",
    "GenerationStatus",
    "Edition",
    "AssetType",
    "GeneratedAsset",
    "TextureAsset",
    "ManifestData",
    "DeviceTier",
    "PerformanceProfile",

    # Versioned state
    "VersionedAddonState",
    "AddonVersion",
    "VersionDiff",
    "UserFeedback",
    "FeedbackType",
    "VersionStatus",
    "VPPerformanceProfile",
    "VDeviceTier",
    "create_versioned_state",
    "migrate_from_addon_state",
]
