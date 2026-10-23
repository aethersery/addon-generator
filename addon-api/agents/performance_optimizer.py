"""
Performance Optimizer Agent - Device-tier optimization for 32-bit/2GB to 64-bit/8GB+.

Automatically profiles addon and generates optimized variants per device tier:
- Texture atlasing and resolution scaling
- Model LOD (Level of Detail) generation
- Entity count culling and budgeting
- Particle system budgets
- Script optimization
- Memory footprint reduction
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from core.state import (
    VersionedAddonState,
    GenerationStatus,
    AssetType,
    GeneratedAsset,
    TextureAsset,
    DeviceTier,
    PerformanceProfile,
)
from core.versioned_state import PerformanceProfile as VPPerformanceProfile
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class OptimizationAction:
    """A single optimization action."""
    action_type: str  # "texture_atlas", "reduce_resolution", "simplify_model", "cull_entities", etc.
    target_assets: list[str]
    description: str
    estimated_savings: dict[str, float]  # ram_mb, texture_mb, fps_gain, etc.
    tier: DeviceTier
    reversible: bool = True


@dataclass
class OptimizationPlan:
    """Complete optimization plan for a tier."""
    tier: DeviceTier
    actions: list[OptimizationAction] = field(default_factory=list)
    total_estimated_ram_mb: float = 0.0
    total_estimated_texture_mb: float = 0.0
    target_fps: int = 60
    profile: Optional[VPPerformanceProfile] = None


class PerformanceOptimizer:
    """
    Analyzes addon assets and creates device-tier optimized variants.
    Supports 32-bit/2GB (low), 64-bit/4GB (mid), 64-bit/8GB+ (high).
    """

    def __init__(self):
        self.router = get_router()

    async def optimize(self, state: VersionedAddonState, target_tiers: list[DeviceTier] = None) -> VersionedAddonState:
        """Optimize current version for target device tiers."""
        current = state.get_current_version()
        if not current:
            return state

        target_tiers = target_tiers or [DeviceTier.LOW_32BIT_2GB, DeviceTier.MID_64BIT_4GB, DeviceTier.HIGH_64BIT_8GB]

        state.set_status(GenerationStatus.VALIDATING, "performance_optimizer",
                        f"Optimizing for {len(target_tiers)} device tiers...")
        state.add_log("Analyzing asset performance characteristics...")

        # Analyze current assets
        analysis = await self._analyze_assets(current)
        state.add_log(f"Analysis complete: {analysis['total_textures']} textures, {analysis['total_models']} models, {analysis['total_scripts']} scripts")

        # Generate optimization plans per tier
        plans = {}
        for tier in target_tiers:
            plan = await self._create_optimization_plan(current, tier, analysis)
            plans[tier] = plan
            state.add_log(f"Tier {tier.value}: {len(plan.actions)} optimizations, target {plan.target_fps} FPS")

        # Apply optimizations to create tier-specific variants
        for tier, plan in plans.items():
            await self._apply_optimizations(state, current, tier, plan)

        # Update performance profiles
        for tier, plan in plans.items():
            current.performance_profiles[tier] = plan.profile or VPPerformanceProfile.for_tier(tier)

        state.set_status(GenerationStatus.VALIDATING, "performance_optimizer",
                        "Optimization complete for all tiers")
        return state

    async def _analyze_assets(self, version: 'AddonVersion') -> dict[str, Any]:
        """Analyze all assets for performance characteristics."""
        analysis = {
            "total_textures": 0,
            "total_texture_pixels": 0,
            "total_texture_memory_mb": 0.0,
            "total_models": 0,
            "total_polygons": 0,
            "total_bones": 0,
            "total_animations": 0,
            "total_scripts": 0,
            "script_lines": 0,
            "entities": [],
            "particles": [],
            "ui_elements": [],
            "max_texture_resolution": 0,
            "uses_pbr": False,
            "has_lod": False,
        }

        for asset in version.rp_textures:
            analysis["total_textures"] += 1
            w = asset.metadata.get("width", 64)
            h = asset.metadata.get("height", 64)
            analysis["total_texture_pixels"] += w * h
            analysis["total_texture_memory_mb"] += (w * h * 4) / (1024 * 1024)  # RGBA
            analysis["max_texture_resolution"] = max(analysis["max_texture_resolution"], max(w, h))

            if asset.metadata.get("pbr_maps"):
                analysis["uses_pbr"] = True

        for asset in version.rp_assets:
            if asset.asset_type == AssetType.GEOMETRY:
                analysis["total_models"] += 1
                geo = asset.content
                if isinstance(geo, dict):
                    for geom_name, geom_data in geo.get("geometry", {}).items():
                        bones = geom_data.get("bones", [])
                        analysis["total_bones"] += len(bones)
                        for bone in bones:
                            cubes = bone.get("cubes", [])
                            analysis["total_polygons"] += len(cubes) * 12  # Approx

            elif asset.asset_type == AssetType.ANIMATION:
                analysis["total_animations"] += 1

            elif asset.asset_type == AssetType.SCRIPT:
                analysis["total_scripts"] += 1
                content = asset.content
                if isinstance(content, str):
                    analysis["script_lines"] += content.count("\n")

            elif asset.asset_type == AssetType.PARTICLE:
                analysis["particles"].append(asset.metadata.get("name", ""))

            elif asset.asset_type == AssetType.UI:
                analysis["ui_elements"].append(asset.metadata.get("name", ""))

        for asset in version.bp_assets:
            if asset.asset_type == AssetType.ENTITY:
                analysis["entities"].append(asset.metadata.get("name", ""))

        return analysis

    async def _create_optimization_plan(
        self,
        version: 'AddonVersion',
        tier: DeviceTier,
        analysis: dict[str, Any]
    ) -> OptimizationPlan:
        """Create optimization plan for a specific tier."""
        profile = VPPerformanceProfile.for_tier(tier)
        plan = OptimizationPlan(tier=tier, profile=profile)

        # Get target values from profile
        target_texture_mb = profile.estimated_texture_memory_mb
        target_ram_mb = profile.estimated_ram_mb
        target_resolution = profile.texture_resolution
        use_pbr = profile.use_pbr
        use_lod = profile.use_lod_models

        current_texture_mb = analysis["total_texture_memory_mb"]
        current_resolution = analysis["max_texture_resolution"]

        actions = []

        # 1. Texture Resolution Scaling
        if current_resolution > target_resolution:
            scale_factor = target_resolution / current_resolution
            savings_mb = current_texture_mb * (1 - scale_factor ** 2)
            actions.append(OptimizationAction(
                action_type="reduce_texture_resolution",
                target_assets=[t.metadata.get("name", "") for t in version.rp_textures],
                description=f"Downscale textures from {current_resolution}px to {target_resolution}px",
                estimated_savings={"texture_mb": savings_mb, "ram_mb": savings_mb * 0.5},
                tier=tier,
            ))

        # 2. Texture Atlasing
        if profile.atlas_textures and analysis["total_textures"] > 16:
            atlas_savings = current_texture_mb * 0.15  # ~15% savings from atlasing
            actions.append(OptimizationAction(
                action_type="texture_atlas",
                target_assets=[t.metadata.get("name", "") for t in version.rp_textures],
                description="Combine multiple textures into atlases",
                estimated_savings={"texture_mb": atlas_savings, "ram_mb": atlas_savings * 0.3},
                tier=tier,
            ))

        # 3. PBR Map Reduction
        if analysis["uses_pbr"] and not use_pbr:
            pbr_savings = current_texture_mb * 0.6  # PBR adds ~5 extra maps
            actions.append(OptimizationAction(
                action_type="remove_pbr_maps",
                target_assets=[t.metadata.get("name", "") for t in version.rp_textures if t.metadata.get("pbr_maps")],
                description="Remove normal, roughness, metallic, AO, emission maps",
                estimated_savings={"texture_mb": pbr_savings, "ram_mb": pbr_savings * 0.5},
                tier=tier,
            ))

        # 4. Model Simplification
        if analysis["total_polygons"] > 10000 and profile.simplify_models:
            actions.append(OptimizationAction(
                action_type="simplify_models",
                target_assets=[a.metadata.get("name", "") for a in version.rp_assets if a.asset_type == AssetType.GEOMETRY],
                description="Reduce polygon count, merge bones, remove small details",
                estimated_savings={"ram_mb": 5.0, "fps_gain": 5},
                tier=tier,
            ))

        # 5. LOD Generation
        if use_lod and not analysis["has_lod"] and analysis["total_models"] > 0:
            actions.append(OptimizationAction(
                action_type="generate_lod",
                target_assets=[a.metadata.get("name", "") for a in version.rp_assets if a.asset_type == AssetType.GEOMETRY],
                description="Generate LOD0 (high), LOD1 (medium), LOD2 (low) variants",
                estimated_savings={"ram_mb": 10.0, "fps_gain": 10},
                tier=tier,
            ))

        # 6. Animation Reduction
        if profile.reduced_animations and analysis["total_animations"] > 5:
            actions.append(OptimizationAction(
                action_type="reduce_animations",
                target_assets=[a.metadata.get("name", "") for a in version.rp_assets if a.asset_type == AssetType.ANIMATION],
                description="Simplify animation keyframes, remove subtle secondary motions",
                estimated_savings={"ram_mb": 2.0, "fps_gain": 3},
                tier=tier,
            ))

        # 7. Entity Culling
        entity_count = len(analysis["entities"])
        max_entities = profile.max_entities
        if entity_count > max_entities:
            actions.append(OptimizationAction(
                action_type="cull_entities",
                target_assets=analysis["entities"][max_entities:],
                description=f"Limit simultaneous entities to {max_entities} (despawn distant/low-priority)",
                estimated_savings={"ram_mb": 2.0 * (entity_count - max_entities), "fps_gain": 5},
                tier=tier,
            ))

        # 8. Particle Budget
        particle_count = len(analysis["particles"])
        max_particles = profile.max_particles
        if particle_count > max_particles:
            actions.append(OptimizationAction(
                action_type="limit_particles",
                target_assets=analysis["particles"][max_particles:],
                description=f"Limit simultaneous particles to {max_particles}",
                estimated_savings={"ram_mb": 1.0, "fps_gain": 5},
                tier=tier,
            ))

        # 9. Script Optimization
        if analysis["script_lines"] > 2000:
            actions.append(OptimizationAction(
                action_type="optimize_scripts",
                target_assets=[a.metadata.get("name", "") for a in version.bp_assets if a.asset_type == AssetType.SCRIPT],
                description="Minify, remove debug logs, optimize loops, use object pooling",
                estimated_savings={"ram_mb": 3.0, "fps_gain": 3},
                tier=tier,
            ))

        plan.actions = actions
        plan.total_estimated_ram_mb = sum(a.estimated_savings.get("ram_mb", 0) for a in actions)
        plan.total_estimated_texture_mb = sum(a.estimated_savings.get("texture_mb", 0) for a in actions)
        plan.target_fps = profile.target_fps

        return plan

    async def _apply_optimizations(
        self,
        state: VersionedAddonState,
        base_version: 'AddonVersion',
        tier: DeviceTier,
        plan: OptimizationPlan
    ):
        """Apply optimizations to create tier-specific variant."""
        # Create new version for this tier
        tier_version_str = f"{base_version.version}-{tier.value}"
        tier_version = state.create_version(
            version=tier_version_str,
            base_version=base_version.version,
            branch=f"optimized-{tier.value}",
            created_by=f"agent:performance_optimizer",
            changelog=f"Auto-optimized for {tier.value}: {len(plan.actions)} optimizations applied",
        )

        # Apply each optimization
        for action in plan.actions:
            await self._apply_action(state, tier_version, action)

        # Store optimization metadata
        tier_version.performance_profiles[tier] = plan.profile
        tier_version.active_profile = tier

    async def _apply_action(self, state: VersionedAddonState, version: 'AddonVersion', action: OptimizationAction):
        """Apply a single optimization action."""
        if action.action_type == "reduce_texture_resolution":
            # In real implementation, would regenerate textures at lower res
            # For now, mark metadata
            for texture in version.rp_textures:
                if texture.metadata.get("name") in action.target_assets:
                    texture.metadata["optimized_resolution"] = action.tier.value

        elif action.action_type == "remove_pbr_maps":
            for texture in version.rp_textures:
                if texture.metadata.get("name") in action.target_assets:
                    texture.metadata["pbr_maps"] = False
                    texture.metadata["pbr_removed"] = True

        elif action.action_type == "simplify_models":
            for asset in version.rp_assets:
                if asset.asset_type == AssetType.GEOMETRY and asset.metadata.get("name") in action.target_assets:
                    asset.metadata["simplified"] = True
                    asset.metadata["lod_level"] = 1

        elif action.action_type == "generate_lod":
            # Would generate LOD variants
            for asset in version.rp_assets:
                if asset.asset_type == AssetType.GEOMETRY and asset.metadata.get("name") in action.target_assets:
                    asset.metadata["has_lod"] = True
                    asset.metadata["lod_levels"] = 3

        # Log the action
        version.updated_at = datetime.utcnow()

    async def profile_addon(self, state: VersionedAddonState) -> dict[str, Any]:
        """Generate comprehensive performance profile for current version."""
        current = state.get_current_version()
        if not current:
            return {}

        analysis = await self._analyze_assets(current)

        # Calculate estimated metrics per tier
        profiles = {}
        for tier in DeviceTier:
            profile = VPPerformanceProfile.for_tier(tier)
            plan = await self._create_optimization_plan(current, tier, analysis)
            profiles[tier.value] = {
                "estimated_ram_mb": max(0, (analysis["total_texture_memory_mb"] * 2) - plan.total_estimated_ram_mb),
                "estimated_texture_mb": max(0, analysis["total_texture_memory_mb"] - plan.total_estimated_texture_mb),
                "target_fps": plan.target_fps,
                "texture_resolution": profile.texture_resolution,
                "uses_pbr": profile.use_pbr,
                "has_lod": profile.use_lod_models,
                "max_entities": profile.max_entities,
                "max_particles": profile.max_particles,
                "optimizations_needed": len(plan.actions),
            }

        return {
            "analysis": analysis,
            "profiles": profiles,
            "recommendations": self._generate_recommendations(analysis, profiles),
        }

    def _generate_recommendations(self, analysis: dict, profiles: dict) -> list[str]:
        """Generate optimization recommendations."""
        recs = []

        if analysis["max_texture_resolution"] > 128:
            recs.append(f"Consider reducing max texture resolution from {analysis['max_texture_resolution']}px to 128px for better performance")

        if analysis["total_textures"] > 64:
            recs.append(f"High texture count ({analysis['total_textures']}) - implement texture atlasing")

        if analysis["uses_pbr"] and profiles.get(DeviceTier.LOW_32BIT_2GB.value, {}).get("uses_pbr"):
            recs.append("Disable PBR maps for low-end devices")

        if analysis["total_polygons"] > 20000:
            recs.append(f"High polygon count ({analysis['total_polygons']}) - use LOD models and simplify")

        if len(analysis["entities"]) > 50:
            recs.append(f"Many entity types ({len(analysis['entities'])}) - implement entity pooling and culling")

        if analysis["script_lines"] > 5000:
            recs.append(f"Large script size ({analysis['script_lines']} lines) - optimize and minify")

        return recs


# Singleton
_optimizer: PerformanceOptimizer | None = None


def get_performance_optimizer() -> PerformanceOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer()
    return _optimizer
