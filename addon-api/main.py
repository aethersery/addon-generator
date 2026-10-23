"""
Main FastAPI Application for Addon Generator API v2.

Provides REST endpoints for:
- Deep theme research (50+ virtual PDFs)
- Versioned addon generation with feedback loops
- Status monitoring with real-time streaming
- File download (.mcaddon, .zip)
- Version management (diff, rollback, branch)
- Performance profiles per device tier
- Community pattern learning
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings
from core.versioned_state import (
    VersionedAddonState,
    Edition,
    GenerationStatus,
    DeviceTier,
    UserFeedback,
    FeedbackType,
    PerformanceProfile,
)
from orchestration.graph_v2 import run_generation_v2, run_generation_stream_v2, get_dynamic_graph
from agents.version_manager import get_version_manager, create_version, rollback_version, get_version_diff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# In-memory job store (replace with Redis/PlanetScale in production)
jobs: dict[str, VersionedAddonState] = {}


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Addon Generator API v2...")
    logger.info(f"Available LLM providers: {settings.available_providers}")

    # Create output directories
    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    # Initialize dynamic graph
    get_dynamic_graph()

    yield

    # Shutdown
    logger.info("Shutting down Addon Generator API v2...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Minecraft Bedrock/Java addon generator with multi-agent orchestration, version control, and self-evolution",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models
# =============================================================================

class ResearchRequest(BaseModel):
    theme: str = Field(..., description="Theme/universe name (e.g., 'Shadow Slave', 'Naruto', 'Elden Ring')")
    description: str = Field(default="", description="Additional description or specific focus")
    mc_version: str = Field(default="26.40", description="Target Minecraft version")
    edition: Edition = Field(default=Edition.BEDROCK, description="Target edition")
    style: str = Field(default="vanilla_plus", description="Visual style: faithful, vanilla_plus, rtx_pbr, anime_cel, medieval, modern, custom")
    texture_resolution: int = Field(default=64, description="Base texture resolution (16, 32, 64, 128, 256)")
    include_pbr: bool = Field(default=True, description="Include PBR texture maps")
    include_animations: bool = Field(default=True, description="Include animations")
    include_models: bool = Field(default=True, description="Include 3D models")
    include_sounds: bool = Field(default=False, description="Include custom sounds")
    include_scripts: bool = Field(default=True, description="Include behavior scripts")
    include_particles: bool = Field(default=True, description="Include particle effects")
    include_ui: bool = Field(default=True, description="Include custom UI")
    target_tiers: list[DeviceTier] = Field(default=[DeviceTier.LOW_32BIT_2GB, DeviceTier.MID_64BIT_4GB, DeviceTier.HIGH_64BIT_8GB])
    faithfulness: float = Field(default=0.8, ge=0.0, le=1.0, description="0=inspired, 1=faithful to canon")
    reference_images: list[str] = Field(default=[], description="Base64 reference images for custom style")


class GenerationRequest(ResearchRequest):
    """Full generation request (includes research)."""
    pass


class FeedbackRequest(BaseModel):
    version: str = Field(..., description="Version to provide feedback on")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    canon_reference: str = Field(default="", description="Canon reference (e.g., 'Chapter 234')")
    affected_assets: list[str] = Field(default=[], description="Asset names affected")
    suggested_fix: str = Field(default="", description="Suggested fix")
    priority: int = Field(default=3, ge=1, le=5, description="1=critical, 5=low")


class VersionRequest(BaseModel):
    version: str = Field(..., description="Version string (e.g., '0.0.2')")
    base_version: str = Field(default="", description="Base version to branch from")
    branch: str = Field(default="main", description="Branch name")
    changelog: str = Field(default="", description="Changelog for this version")


class RollbackRequest(BaseModel):
    version: str = Field(..., description="Version to rollback to")


class TagRequest(BaseModel):
    version: str = Field(..., description="Version to tag")
    tag_name: str = Field(..., description="Tag name (e.g., 'v1.0-release')")
    message: str = Field(default="", description="Tag message")


class ResearchResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: GenerationStatus
    progress: float
    current_step: str
    step_details: str
    error_message: Optional[str] = None
    logs: list[str] = Field(default_factory=list)
    current_version: Optional[str] = None
    version_history: list[dict] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    job_id: str
    status: GenerationStatus
    message: str


class VersionInfo(BaseModel):
    version: str
    status: str
    branch: str
    created_at: str
    created_by: str
    changelog: str
    has_preview: bool
    has_mcaddon: bool
    asset_count: int
    feedback_count: int
    tags: list[str] = Field(default_factory=list)


class DiffResponse(BaseModel):
    from_version: str
    to_version: str
    summary: str
    added: int
    modified: int
    removed: int
    performance_delta: dict
    added_assets: list[str]
    modified_assets: list[str]
    removed_assets: list[str]


class PerformanceProfileResponse(BaseModel):
    tier: str
    estimated_ram_mb: float
    estimated_texture_memory_mb: float
    target_fps: int
    texture_resolution: int
    use_pbr: bool
    use_lod_models: bool
    max_entities: int
    max_particles: int
    atlas_textures: bool
    simplify_models: bool
    reduced_animations: bool


class ProvidersResponse(BaseModel):
    available: list[str]
    details: dict


# =============================================================================
# API Endpoints - Research & Generation
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "providers": settings.available_providers,
        "features": [
            "deep_research", "version_control", "feedback_loops",
            "performance_optimization", "community_learning",
            "custom_ui", "pbr_textures", "3d_models"
        ],
    }


@app.post("/research", response_model=ResearchResponse)
async def research_theme(request: ResearchRequest):
    """
    Deep research a theme/universe lore (50+ virtual PDFs).
    Returns a job_id to track progress.
    """
    job_id = str(uuid.uuid4())[:8]

    # Create initial versioned state
    state = VersionedAddonState(
        theme=request.theme,
        description=request.description,
        mc_version=request.mc_version,
        edition=request.edition,
        style=request.style,
        texture_resolution=request.texture_resolution,
        include_pbr=request.include_pbr,
        include_animations=request.include_animations,
        include_models=request.include_models,
        include_sounds=request.include_sounds,
        include_scripts=request.include_scripts,
        include_particles=request.include_particles,
        include_ui=request.include_ui,
        target_tiers=request.target_tiers,
        generation_config={
            "faithfulness": request.faithfulness,
            "reference_images": request.reference_images,
        },
    )

    jobs[job_id] = state

    # Run research in background
    asyncio.create_task(_run_research(job_id, state))

    return ResearchResponse(
        job_id=job_id,
        status="started",
        message=f"Deep research started for '{request.theme}' (50+ domains)",
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate_addon(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Start full addon generation with version control.
    Returns a job_id to track progress.
    """
    job_id = str(uuid.uuid4())[:8]

    state = VersionedAddonState(
        theme=request.theme,
        description=request.description,
        mc_version=request.mc_version,
        edition=request.edition,
        style=request.style,
        texture_resolution=request.texture_resolution,
        include_pbr=request.include_pbr,
        include_animations=request.include_animations,
        include_models=request.include_models,
        include_sounds=request.include_sounds,
        include_scripts=request.include_scripts,
        include_particles=request.include_particles,
        include_ui=request.include_ui,
        target_tiers=request.target_tiers,
        generation_config={
            "faithfulness": request.faithfulness,
            "reference_images": request.reference_images,
        },
    )

    jobs[job_id] = state

    # Run full generation in background
    background_tasks.add_task(_run_generation, job_id, state)

    return GenerateResponse(
        job_id=job_id,
        status=GenerationStatus.PENDING,
        message=f"Full generation started for '{request.theme}'",
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Get generation job status with version info."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)

    return StatusResponse(
        job_id=job_id,
        status=state.status,
        progress=state.progress,
        current_step=state.current_step,
        step_details=state.step_details,
        error_message=state.error_message,
        logs=state.logs[-100:],
        current_version=state.current_version,
        version_history=manager.list_versions(),
    )


@app.get("/stream/{job_id}")
async def stream_status(job_id: str):
    """Stream real-time generation updates via Server-Sent Events."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]

    async def event_generator():
        # If already running, stream from graph
        if state.status not in [GenerationStatus.COMPLETED, GenerationStatus.FAILED]:
            async for chunk in run_generation_stream_v2(state, thread_id=job_id):
                yield f"data: {chunk.model_dump_json()}\n\n"
        else:
            # Already completed, send final state
            yield f"data: {state.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    """Get final generation result with all version info."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    current = state.get_current_version()

    if not current:
        raise HTTPException(status_code=400, detail="No version available")

    return {
        "job_id": job_id,
        "theme": state.theme,
        "current_version": state.current_version,
        "mc_version": state.mc_version,
        "edition": state.edition.value,
        "mcaddon_path": current.mcaddon_path,
        "zip_path": current.zip_path,
        "preview_image": current.preview_image_b64,
        "changelog": current.changelog,
        "assets_count": {
            "bp_assets": len(current.bp_assets),
            "rp_assets": len(current.rp_assets),
            "rp_textures": len(current.rp_textures),
        },
        "performance_profiles": {
            tier.value: {
                "ram_mb": p.estimated_ram_mb,
                "texture_mb": p.estimated_texture_memory_mb,
                "fps": p.target_fps,
                "resolution": p.texture_resolution,
                "pbr": p.use_pbr,
                "lod": p.use_lod_models,
            }
            for tier, p in current.performance_profiles.items()
        },
        "validation": {
            "errors": current.validation_errors,
            "warnings": current.validation_warnings,
        },
        "learned_patterns": state.learned_patterns,
    }


@app.get("/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str, version: str = None):
    """Download generated addon file for specific version."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    target_version = version or state.current_version
    ver = state.versions.get(target_version)

    if not ver:
        raise HTTPException(status_code=404, detail=f"Version {target_version} not found")

    file_map = {
        "mcaddon": ver.mcaddon_path,
        "zip": ver.zip_path,
        "bp": "",  # Would need separate BP zip
        "rp": "",  # Would need separate RP zip
    }

    if file_type not in file_map or not file_map[file_type]:
        raise HTTPException(status_code=404, detail=f"File type {file_type} not available for version {target_version}")

    file_path = Path(file_map[file_type])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/zip",
    )


# =============================================================================
# API Endpoints - Version Control
# =============================================================================

@app.get("/versions/{job_id}")
async def list_versions(job_id: str, branch: str = None):
    """List all versions for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)
    return {"versions": manager.list_versions(branch)}


@app.get("/versions/{job_id}/{version}")
async def get_version(job_id: str, version: str):
    """Get detailed info for a specific version."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    ver = state.versions.get(version)

    if not ver:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    return {
        "version": ver.version,
        "status": ver.status.value,
        "branch": ver.branch_name,
        "base_version": ver.base_version,
        "created_at": ver.created_at.isoformat(),
        "created_by": ver.created_by,
        "changelog": ver.changelog,
        "preview_image": ver.preview_image_b64,
        "mcaddon_path": ver.mcaddon_path,
        "zip_path": ver.zip_path,
        "asset_count": len(ver.bp_assets) + len(ver.rp_assets),
        "textures": len(ver.rp_textures),
        "feedback": [
            {
                "id": f.id,
                "type": f.feedback_type.value,
                "title": f.title,
                "description": f.description,
                "canon_reference": f.canon_reference,
                "status": f.status,
                "priority": f.priority,
            }
            for f in ver.feedback
        ],
        "resolved_feedback": ver.resolved_feedback_ids,
        "validation_errors": ver.validation_errors,
        "validation_warnings": ver.validation_warnings,
        "performance_profiles": {
            tier.value: {
                "ram_mb": p.estimated_ram_mb,
                "texture_mb": p.estimated_texture_memory_mb,
                "fps": p.target_fps,
                "resolution": p.texture_resolution,
                "pbr": p.use_pbr,
                "lod": p.use_lod_models,
            }
            for tier, p in ver.performance_profiles.items()
        },
    }


@app.post("/versions/{job_id}")
async def create_new_version(job_id: str, request: VersionRequest):
    """Create a new version (branch/iteration)."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)

    new_ver = manager.create_version(
        version=request.version,
        base_version=request.base_version,
        branch=request.branch,
        created_by="user",
        changelog=request.changelog,
    )

    return {
        "message": f"Version {new_ver.version} created",
        "version": new_ver.version,
        "base_version": new_ver.base_version,
        "branch": new_ver.branch_name,
    }


@app.post("/versions/{job_id}/rollback")
async def rollback(job_id: str, request: RollbackRequest):
    """Rollback to a previous version."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    success = await rollback_version(state, request.version)

    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")

    return {"message": f"Rolled back to {request.version} as new version"}


@app.get("/versions/{job_id}/diff")
async def get_diff(job_id: str, from_version: str, to_version: str):
    """Get diff between two versions."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    diff = await get_version_diff(state, from_version, to_version)
    return diff


@app.post("/versions/{job_id}/tag")
async def tag_version(job_id: str, request: TagRequest):
    """Tag a version (like git tag)."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)
    tag = manager.tag_version(request.version, request.tag_name, request.message)

    return {
        "message": f"Tagged {request.version} as {tag.name}",
        "tag": tag.name,
        "version": tag.version,
    }


@app.get("/versions/{job_id}/tree")
async def get_version_tree(job_id: str):
    """Get version tree for visualization."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)
    return manager.get_version_tree()


@app.post("/versions/{job_id}/export")
async def export_version(job_id: str, version: str):
    """Export a version as standalone addon files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)

    output_dir = Path(settings.OUTPUT_DIR) / "exports" / job_id / version
    success = manager.export_version(version, output_dir)

    if not success:
        raise HTTPException(status_code=400, detail="Export failed")

    return {"message": f"Version {version} exported to {output_dir}"}


@app.get("/versions/{job_id}/performance")
async def compare_performance(job_id: str, versions: list[str] = Query([])):
    """Compare performance across versions."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)

    if not versions:
        versions = state.version_history[-5:]  # Last 5 versions

    return manager.compare_performance(versions)


# =============================================================================
# API Endpoints - Feedback & Iteration
# =============================================================================

@app.post("/feedback/{job_id}")
async def add_feedback(job_id: str, request: FeedbackRequest):
    """Add user feedback for a version."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]

    # Validate version exists
    if request.version not in state.versions:
        raise HTTPException(status_code=404, detail=f"Version {request.version} not found")

    feedback = UserFeedback(
        version=request.version,
        feedback_type=request.feedback_type,
        title=request.title,
        description=request.description,
        canon_reference=request.canon_reference,
        affected_assets=request.affected_assets,
        suggested_fix=request.suggested_fix,
        priority=request.priority,
    )

    fb_id = state.add_feedback(feedback)

    # Auto-trigger iteration for high-priority canon corrections
    if request.feedback_type == FeedbackType.CANON_CORRECTION and request.priority <= 2:
        state.add_log(f"High-priority canon correction received, queuing iteration...")
        # In production, would trigger background regeneration

    return {
        "message": "Feedback added",
        "feedback_id": fb_id,
        "will_iterate": request.feedback_type == FeedbackType.CANON_CORRECTION and request.priority <= 2,
    }


@app.get("/feedback/{job_id}")
async def get_feedback(job_id: str, version: str = None, status: str = "open"):
    """Get feedback for a job/version."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]

    if version:
        ver = state.versions.get(version)
        if not ver:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
        feedback_list = ver.feedback
    else:
        feedback_list = state.all_feedback

    filtered = [f for f in feedback_list if f.status == status]
    return {
        "feedback": [
            {
                "id": f.id,
                "version": f.version,
                "type": f.feedback_type.value,
                "title": f.title,
                "description": f.description,
                "canon_reference": f.canon_reference,
                "affected_assets": f.affected_assets,
                "suggested_fix": f.suggested_fix,
                "priority": f.priority,
                "status": f.status,
                "created_at": f.created_at.isoformat(),
                "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
                "resolved_version": f.resolved_version,
            }
            for f in filtered
        ]
    }


@app.post("/feedback/{job_id}/resolve")
async def resolve_feedback(job_id: str, feedback_id: str, resolved_version: str = ""):
    """Mark feedback as resolved."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    success = state.resolve_feedback(feedback_id, resolved_version)

    if not success:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return {"message": "Feedback resolved", "feedback_id": feedback_id}


# =============================================================================
# API Endpoints - Performance & Optimization
# =============================================================================

@app.get("/performance/{job_id}")
async def get_performance(job_id: str, version: str = None):
    """Get performance profiles for a version."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    target = version or state.current_version
    ver = state.versions.get(target)

    if not ver:
        raise HTTPException(status_code=404, detail=f"Version {target} not found")

    return {
        "version": target,
        "profiles": {
            tier.value: {
                "ram_mb": p.estimated_ram_mb,
                "texture_mb": p.estimated_texture_memory_mb,
                "target_fps": p.target_fps,
                "texture_resolution": p.texture_resolution,
                "use_pbr": p.use_pbr,
                "use_lod_models": p.use_lod_models,
                "max_entities": p.max_entities,
                "max_particles": p.max_particles,
                "atlas_textures": p.atlas_textures,
                "simplify_models": p.simplify_models,
                "reduced_animations": p.reduced_animations,
            }
            for tier, p in ver.performance_profiles.items()
        },
    }


@app.post("/optimize/{job_id}")
async def optimize_version(job_id: str, target_tiers: list[DeviceTier] = None):
    """Re-optimize a version for specific device tiers."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    current = state.get_current_version()

    if not current:
        raise HTTPException(status_code=400, detail="No current version")

    # Create optimized variant
    from agents.performance_optimizer import get_performance_optimizer
    optimizer = get_performance_optimizer()

    tiers = target_tiers or [DeviceTier.LOW_32BIT_2GB, DeviceTier.MID_64BIT_4GB, DeviceTier.HIGH_64BIT_8GB]

    # This would create tier-specific optimized versions
    # For now, just re-run optimizer on current
    await optimizer.optimize(state, tiers)

    return {
        "message": "Optimization complete",
        "tiers_optimized": [t.value for t in tiers],
        "new_profiles": {
            tier.value: {
                "ram_mb": p.estimated_ram_mb,
                "texture_mb": p.estimated_texture_memory_mb,
                "fps": p.target_fps,
            }
            for tier, p in current.performance_profiles.items()
            if tier in tiers
        },
    }


# =============================================================================
# API Endpoints - Lore & Research
# =============================================================================

@app.get("/lore/{job_id}")
async def get_lore(job_id: str, domain: str = None):
    """Get researched lore data."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    current = state.get_current_version()

    if not current or not current.lore:
        raise HTTPException(status_code=404, detail="No lore data available")

    lore = current.lore

    if domain:
        # Return specific domain from references
        for ref in lore.references or []:
            if ref.get("domain") == domain:
                return ref
        raise HTTPException(status_code=404, detail=f"Domain {domain} not found")

    return {
        "universe_name": lore.universe_name,
        "source_type": lore.source_type,
        "summary": lore.summary,
        "entities": len(lore.entities),
        "items": len(lore.items),
        "blocks": len(lore.blocks),
        "biomes": len(lore.biomes),
        "mechanics": len(lore.mechanics),
        "domains": [
            {
                "domain": r.get("domain"),
                "name": r.get("name"),
                "confidence": r.get("confidence"),
                "canon_status": r.get("canon_status"),
                "source_count": r.get("source_count"),
            }
            for r in lore.references or []
            if "domain" in r
        ],
    }


@app.get("/lore/{job_id}/canon-validation")
async def get_canon_validation(job_id: str):
    """Get canon validation report."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    current = state.get_current_version()

    if not current or not current.lore:
        raise HTTPException(status_code=404, detail="No lore data available")

    for ref in current.lore.references or []:
        if ref.get("type") == "canon_validation":
            return ref.get("data", {})

    raise HTTPException(status_code=404, detail="Canon validation not performed")


@app.get("/lore/{job_id}/minecraft-mapping")
async def get_minecraft_mapping(job_id: str):
    """Get Minecraft translation mapping."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    current = state.get_current_version()

    if not current or not current.lore:
        raise HTTPException(status_code=404, detail="No lore data available")

    for ref in current.lore.references or []:
        if ref.get("type") == "minecraft_mapping":
            return ref.get("data", {})

    raise HTTPException(status_code=404, detail="Minecraft mapping not generated")


# =============================================================================
# API Endpoints - Community & Learning
# =============================================================================

@app.get("/community/patterns")
async def get_learned_patterns(job_id: str = None, pattern_type: str = None, context: str = None):
    """Get learned patterns from community addons."""
    if job_id and job_id in jobs:
        state = jobs[job_id]
        patterns = state.learned_patterns.get("patterns", [])
    else:
        # Global patterns
        from agents.community_learner import get_community_learner
        learner = get_community_learner()
        patterns = [
            {
                "type": p.pattern_type,
                "name": p.name,
                "description": p.description,
                "code": p.code_example,
                "contexts": p.applicable_contexts,
                "quality": p.quality_score,
                "sources": p.source_repos,
            }
            for p in learner.patterns
        ]

    # Filter
    if pattern_type:
        patterns = [p for p in patterns if p.get("type") == pattern_type]
    if context:
        patterns = [p for p in patterns if context in p.get("contexts", [])]

    return {"patterns": patterns, "count": len(patterns)}


@app.post("/community/sync")
async def sync_community(background_tasks: BackgroundTasks, job_id: str = None):
    """Trigger community learning sync."""
    if job_id and job_id in jobs:
        state = jobs[job_id]
    else:
        # Create temporary state for global sync
        state = VersionedAddonState(theme="global_sync")

    background_tasks.add_task(_sync_community, state)
    return {"message": "Community sync started"}


async def _sync_community(state: VersionedAddonState):
    """Background task for community sync."""
    from agents.community_learner import get_community_learner
    learner = get_community_learner()
    await learner.learn(state, force_refresh=True)


# =============================================================================
# API Endpoints - Providers & System
# =============================================================================

@app.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    """List available LLM providers and their status."""
    return ProvidersResponse(
        available=settings.available_providers,
        details={
            "openrouter": {"enabled": settings.has_openrouter, "model": settings.OPENROUTER_DEFAULT_MODEL},
            "groq": {"enabled": settings.has_groq, "model": settings.GROQ_DEFAULT_MODEL},
            "together": {"enabled": settings.has_together, "model": settings.TOGETHER_DEFAULT_MODEL},
            "google": {"enabled": settings.has_google, "model": settings.GOOGLE_DEFAULT_MODEL},
            "openai": {"enabled": settings.has_openai, "model": settings.OPENAI_DEFAULT_MODEL},
            "anthropic": {"enabled": settings.has_anthropic, "model": settings.ANTHROPIC_DEFAULT_MODEL},
            "deepseek": {"enabled": settings.has_deepseek, "model": settings.DEEPSEEK_DEFAULT_MODEL},
            "ollama": {"enabled": settings.has_ollama, "model": settings.OLLAMA_DEFAULT_MODEL},
        },
    )


@app.get("/schemas")
async def list_schemas():
    """List available Bedrock JSON schemas."""
    from agents.mc_schema_expert import get_mc_schema_expert
    expert = get_mc_schema_expert()
    await expert.sync_schemas()

    return {
        "schemas": list(expert.schemas.keys()),
        "count": len(expert.schemas),
    }


@app.post("/cleanup/{job_id}")
async def cleanup_job(job_id: str, keep_versions: int = 5):
    """Clean up old versions and files for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = jobs[job_id]
    manager = get_version_manager(state)
    removed = manager.cleanup_old_versions(keep_last=keep_versions)

    return {"message": f"Cleaned up {removed} old versions", "remaining": len(state.version_history)}


# =============================================================================
# Background Tasks
# =============================================================================

async def _run_research(job_id: str, state: VersionedAddonState):
    """Background task for deep research only."""
    try:
        from agents.lore_deep_researcher import get_lore_deep_researcher
        researcher = get_lore_deep_researcher()
        state = await researcher.research(state)
        jobs[job_id] = state
    except Exception as e:
        logger.error(f"Research job {job_id} failed: {e}")
        state.error_message = str(e)
        state.set_status(GenerationStatus.FAILED, "lore_deep_researcher", str(e))
        jobs[job_id] = state


async def _run_generation(job_id: str, state: VersionedAddonState):
    """Background task for full addon generation with dynamic graph."""
    try:
        final_state = await run_generation_v2(state, thread_id=job_id)
        jobs[job_id] = final_state
    except Exception as e:
        logger.error(f"Generation job {job_id} failed: {e}")
        state.error_message = str(e)
        state.set_status(GenerationStatus.FAILED, "orchestration", str(e))
        jobs[job_id] = state


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS,
    )
