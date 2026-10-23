"""
Version Manager - Git-like version control for addon iterations.

Manages:
- Version creation, branching, merging
- Diff visualization between versions
- Changelog generation
- Rollback and restore
- Preview image comparison
- Migration scripts between versions
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.versioned_state import (
    VersionedAddonState,
    AddonVersion,
    VersionDiff,
    UserFeedback,
    FeedbackType,
    DeviceTier,
    VPPerformanceProfile,
)

logger = logging.getLogger(__name__)


@dataclass
class VersionTag:
    """A named tag for a version (like git tags)."""
    name: str
    version: str
    message: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "user"


@dataclass
class MergeRequest:
    """Request to merge two versions."""
    source_version: str
    target_version: str
    strategy: str = "auto"  # auto, manual, theirs, ours
    conflicts: list[dict] = field(default_factory=list)
    status: str = "pending"  # pending, resolved, merged, rejected
    created_at: datetime = field(default_factory=datetime.utcnow)


class VersionManager:
    """
    Manages addon versions with git-like operations.
    """

    def __init__(self, state: VersionedAddonState):
        self.state = state

    def create_version(
        self,
        version: str = None,
        base_version: str = None,
        branch: str = "main",
        created_by: str = "user",
        changelog: str = "",
        auto_increment: bool = True,
    ) -> AddonVersion:
        """Create a new version."""
        current = self.state.get_current_version()

        # Auto-generate version if not provided
        if version is None and auto_increment:
            version = self._next_version(current.version if current else "0.0.0")
        elif version is None:
            version = "0.0.1"

        base = base_version or (current.version if current else "")

        new_version = self.state.create_version(
            version=version,
            base_version=base,
            branch=branch,
            created_by=created_by,
            changelog=changelog,
        )

        logger.info(f"Created version {version} from {base} on branch {branch}")
        return new_version

    def _next_version(self, current: str) -> str:
        """Calculate next patch version."""
        parts = current.split(".")
        if len(parts) >= 3:
            try:
                patch = int(parts[2].split("-")[0]) + 1
                parts[2] = str(patch)
                return ".".join(parts)
            except ValueError:
                pass
        return "0.0.1"

    def create_branch(self, branch_name: str, from_version: str = None) -> str:
        """Create a new branch from a version."""
        base = from_version or self.state.current_version
        if base not in self.state.versions:
            raise ValueError(f"Base version {base} not found")

        self.state.branches[branch_name] = base
        self.state.versions[base].branch_name = branch_name
        logger.info(f"Created branch {branch_name} from {base}")
        return base

    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a branch."""
        if branch_name not in self.state.branches:
            return False

        version = self.state.branches[branch_name]
        return self.state.load_version(version)

    def merge_branch(self, source_branch: str, target_branch: str = "main") -> MergeRequest:
        """Create merge request between branches."""
        if source_branch not in self.state.branches or target_branch not in self.state.branches:
            raise ValueError("Branch not found")

        source_ver = self.state.branches[source_branch]
        target_ver = self.state.branches[target_branch]

        # Check for conflicts
        diff = self.state.get_diff(target_ver, source_ver)
        conflicts = self._detect_conflicts(diff)

        mr = MergeRequest(
            source_version=source_ver,
            target_version=target_ver,
            conflicts=conflicts,
        )

        if not conflicts:
            mr.status = "resolved"
            # Auto-merge
            self._perform_merge(mr)

        return mr

    def _detect_conflicts(self, diff: VersionDiff) -> list[dict]:
        """Detect merge conflicts."""
        conflicts = []

        # If same asset modified in both branches
        for asset in diff.modified_assets:
            conflicts.append({
                "type": "modified_asset",
                "asset": asset,
                "resolution": "manual",
            })

        return conflicts

    def _perform_merge(self, mr: MergeRequest):
        """Perform the merge."""
        # Create new version with merged changes
        target_ver = self.state.versions[mr.target_version]
        source_ver = self.state.versions[mr.source_version]

        new_ver = f"{target_ver.version}-merge-{mr.source_version.split('.')[-1]}"
        merged = self.state.create_version(
            version=new_ver,
            base_version=mr.target_version,
            branch=mr.target_version,
            created_by="agent:version_manager",
            changelog=f"Merged {mr.source_version} into {mr.target_version}",
        )

        # Copy assets from source that aren't in target
        for asset in source_ver.bp_assets + source_ver.rp_assets:
            name = asset.metadata.get("name", "")
            if not any(a.metadata.get("name") == name for a in merged.bp_assets + merged.rp_assets):
                if asset in source_ver.bp_assets:
                    merged.bp_assets.append(asset)
                else:
                    merged.rp_assets.append(asset)

        for texture in source_ver.rp_textures:
            if not any(t.texture_id == texture.texture_id for t in merged.rp_textures):
                merged.rp_textures.append(texture)

        mr.status = "merged"
        logger.info(f"Merged {mr.source_version} into {mr.target_version} as {new_ver}")

    def tag_version(self, version: str, tag_name: str, message: str = "") -> VersionTag:
        """Tag a version (like git tag)."""
        if version not in self.state.versions:
            raise ValueError(f"Version {version} not found")

        tag = VersionTag(
            name=tag_name,
            version=version,
            message=message,
        )

        # Store in version metadata
        ver = self.state.versions[version]
        if not hasattr(ver, 'tags'):
            ver.tags = []
        ver.tags.append(tag)

        logger.info(f"Tagged {version} as {tag_name}")
        return tag

    def get_diff(self, from_version: str, to_version: str) -> VersionDiff:
        """Get diff between two versions."""
        return self.state.get_diff(from_version, to_version)

    def get_diff_summary(self, from_version: str, to_version: str) -> dict:
        """Get human-readable diff summary."""
        diff = self.get_diff(from_version, to_version)

        return {
            "from_version": from_version,
            "to_version": to_version,
            "summary": diff.summary,
            "added": len(diff.added_assets),
            "modified": len(diff.modified_assets),
            "removed": len(diff.removed_assets),
            "lore_changes": len(diff.lore_changes),
            "script_changes": len(diff.script_changes),
            "texture_changes": len(diff.texture_changes),
            "model_changes": len(diff.model_changes),
            "performance_delta": diff.performance_delta,
            "added_assets": diff.added_assets[:20],
            "modified_assets": diff.modified_assets[:20],
            "removed_assets": diff.removed_assets[:20],
        }

    def rollback(self, version: str) -> bool:
        """Rollback to a previous version (make it current)."""
        if version not in self.state.versions:
            return False

        # Create new version as copy of target
        target = self.state.versions[version]
        new_version = self._next_version(self.state.current_version)

        rolled_back = self.state.create_version(
            version=new_version,
            base_version=version,
            branch=self.state.versions[self.state.current_version].branch_name,
            created_by="user:rollback",
            changelog=f"Rollback to version {version}",
        )

        # Copy all assets from target
        rolled_back.bp_assets = [a for a in target.bp_assets]
        rolled_back.rp_assets = [a for a in target.rp_assets]
        rolled_back.rp_textures = [t for t in target.rp_textures]
        rolled_back.bp_manifest = target.bp_manifest
        rolled_back.rp_manifest = target.rp_manifest
        rolled_back.lore = target.lore
        rolled_back.generation_plan = target.generation_plan.copy()
        rolled_back.performance_profiles = target.performance_profiles.copy()

        logger.info(f"Rolled back to {version} as new version {new_version}")
        return True

    def restore_asset(self, version: str, asset_type: str, asset_name: str) -> bool:
        """Restore a specific asset from a previous version."""
        source = self.state.versions.get(version)
        current = self.state.get_current_version()

        if not source or not current:
            return False

        # Find asset in source
        asset = None
        for a in source.bp_assets + source.rp_assets:
            if a.metadata.get("name") == asset_name and a.asset_type.value == asset_type:
                asset = a
                break

        if not asset:
            for t in source.rp_textures:
                if t.texture_id == asset_name:
                    asset = t
                    break

        if not asset:
            return False

        # Add to current version
        if isinstance(asset, GeneratedAsset):
            if asset.asset_type.value in ["entity", "item", "block", "loot_table", "spawn_rule", "recipe", "script"]:
                current.bp_assets.append(asset)
            else:
                current.rp_assets.append(asset)
        else:
            current.rp_textures.append(asset)

        current.updated_at = datetime.utcnow()
        return True

    def list_versions(self, branch: str = None) -> list[dict]:
        """List all versions, optionally filtered by branch."""
        versions = []
        for v_str in self.state.version_history:
            v = self.state.versions.get(v_str)
            if v and (branch is None or v.branch_name == branch):
                versions.append({
                    "version": v.version,
                    "status": v.status.value if hasattr(v.status, 'value') else str(v.status),
                    "branch": v.branch_name,
                    "created_at": v.created_at.isoformat(),
                    "created_by": v.created_by,
                    "changelog": v.changelog,
                    "has_preview": bool(v.preview_image_b64),
                    "has_mcaddon": bool(v.mcaddon_path),
                    "asset_count": len(v.bp_assets) + len(v.rp_assets),
                    "feedback_count": len(v.feedback),
                    "tags": [t.name for t in getattr(v, 'tags', [])],
                })
        return versions

    def get_version_tree(self) -> dict:
        """Get version tree for visualization."""
        tree = {"branches": {}, "versions": {}}

        for branch_name, version in self.state.branches.items():
            tree["branches"][branch_name] = {
                "head": version,
                "versions": [],
            }

        for v_str in self.state.version_history:
            v = self.state.versions.get(v_str)
            if v:
                tree["versions"][v.version] = {
                    "version": v.version,
                    "base_version": v.base_version,
                    "branch": v.branch_name,
                    "status": v.status.value if hasattr(v.status, 'value') else str(v.status),
                    "created_at": v.created_at.isoformat(),
                    "changelog": v.changelog,
                }

        return tree

    def export_version(self, version: str, output_dir: Path) -> bool:
        """Export a version as standalone addon files."""
        ver = self.state.versions.get(version)
        if not ver:
            return False

        output_dir.mkdir(parents=True, exist_ok=True)

        # Export BP
        bp_dir = output_dir / "BP"
        bp_dir.mkdir(exist_ok=True)

        for asset in ver.bp_assets:
            asset_dir = bp_dir / asset.asset_type.value + "s"
            asset_dir.mkdir(exist_ok=True)
            with open(asset_dir / f"{asset.metadata.get('name', 'asset')}.json", "w") as f:
                json.dump(asset.content, f, indent=2)

        # Export RP
        rp_dir = output_dir / "RP"
        rp_dir.mkdir(exist_ok=True)

        for asset in ver.rp_assets:
            asset_dir = rp_dir / asset.asset_type.value + "s"
            asset_dir.mkdir(exist_ok=True)
            with open(asset_dir / f"{asset.metadata.get('name', 'asset')}.json", "w") as f:
                json.dump(asset.content, f, indent=2)

        for texture in ver.rp_textures:
            tex_dir = rp_dir / "textures" / texture.metadata.get("texture_type", "entity")
            tex_dir.mkdir(parents=True, exist_ok=True)
            with open(tex_dir / f"{texture.texture_id}.png", "wb") as f:
                f.write(texture.texture_data)

        # Export manifests
        if ver.bp_manifest:
            with open(bp_dir / "manifest.json", "w") as f:
                json.dump(ver.bp_manifest.__dict__, f, indent=2, default=str)

        if ver.rp_manifest:
            with open(rp_dir / "manifest.json", "w") as f:
                json.dump(ver.rp_manifest.__dict__, f, indent=2, default=str)

        # Export metadata
        with open(output_dir / "version_info.json", "w") as f:
            json.dump({
                "version": ver.version,
                "base_version": ver.base_version,
                "branch": ver.branch_name,
                "created_at": ver.created_at.isoformat(),
                "changelog": ver.changelog,
            }, f, indent=2)

        return True

    def compare_performance(self, versions: list[str]) -> dict:
        """Compare performance profiles across versions."""
        comparison = {}
        for v_str in versions:
            v = self.state.versions.get(v_str)
            if v:
                comparison[v_str] = {}
                for tier, profile in v.performance_profiles.items():
                    comparison[v_str][tier.value] = {
                        "ram_mb": profile.estimated_ram_mb,
                        "texture_mb": profile.estimated_texture_memory_mb,
                        "fps": profile.target_fps,
                        "texture_res": profile.texture_resolution,
                        "pbr": profile.use_pbr,
                        "lod": profile.use_lod_models,
                        "entities": profile.max_entities,
                        "particles": profile.max_particles,
                    }
        return comparison

    def cleanup_old_versions(self, keep_last: int = 10, keep_tagged: bool = True) -> int:
        """Clean up old versions to save space."""
        if len(self.state.version_history) <= keep_last:
            return 0

        to_remove = []
        for v_str in self.state.version_history[:-keep_last]:
            v = self.state.versions.get(v_str)
            if v and keep_tagged and hasattr(v, 'tags') and v.tags:
                continue  # Keep tagged versions
            to_remove.append(v_str)

        for v_str in to_remove:
            del self.state.versions[v_str]
            self.state.version_history.remove(v_str)

        logger.info(f"Cleaned up {len(to_remove)} old versions")
        return len(to_remove)


# Singleton manager per state
_managers: dict[str, VersionManager] = {}


def get_version_manager(state: VersionedAddonState) -> VersionManager:
    """Get or create VersionManager for a state."""
    key = state.job_id or state.thread_id or "default"
    if key not in _managers:
        _managers[key] = VersionManager(state)
    return _managers[key]


# Convenience functions
async def create_version(
    state: VersionedAddonState,
    version: str = None,
    changelog: str = "",
    **kwargs
) -> AddonVersion:
    """Create a new version."""
    manager = get_version_manager(state)
    return manager.create_version(version=version, changelog=changelog, **kwargs)


async def rollback_version(state: VersionedAddonState, version: str) -> bool:
    """Rollback to a version."""
    manager = get_version_manager(state)
    return manager.rollback(version)


async def get_version_diff(state: VersionedAddonState, from_v: str, to_v: str) -> dict:
    """Get diff summary between versions."""
    manager = get_version_manager(state)
    return manager.get_diff_summary(from_v, to_v)
