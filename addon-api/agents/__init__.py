"""
Addon Generator Agents Package.

Exports all specialized agents for the multi-agent orchestration system.
"""
from __future__ import annotations

# Research Agents
from .theme_researcher import get_theme_researcher, research_theme
from .lore_deep_researcher import get_lore_deep_researcher, research_theme_deep
from .canon_validator import get_canon_validator, validate_lore

# Schema & Validation
from .mc_schema_expert import get_mc_schema_expert

# Community Learning
from .community_learner import get_community_learner

# Planning & Architecture
from .project_architect import get_project_architect

# Generation Agents
from .texture_synthesizer import get_texture_synthesizer, TextureSynthesizer, TextureSpec, TextureStyle, TextureType
from .model_generator import get_model_generator, ModelGenerator, ModelSpec
from .ui_designer import get_ui_designer, UIDesigner, UISpec
from .animation_designer import get_animation_designer, AnimationDesigner, AnimationSpec
from .particle_designer import get_particle_designer, ParticleDesigner, ParticleSpec
from .sound_designer import get_sound_designer, SoundDesigner, SoundSpec

# Optimization & Quality
from .performance_optimizer import get_performance_optimizer
from .addon_packager import get_addon_packager, AddonPackager, PackagerConfig

# Version Control
from .version_manager import get_version_manager, VersionManager

__all__ = [
    # Research
    "get_theme_researcher",
    "research_theme",
    "get_lore_deep_researcher",
    "research_theme_deep",
    "get_canon_validator",
    "validate_lore",

    # Schema
    "get_mc_schema_expert",

    # Community
    "get_community_learner",

    # Planning
    "get_project_architect",

    # Generation
    "get_texture_synthesizer",
    "TextureSynthesizer",
    "TextureSpec",
    "TextureStyle",
    "TextureType",
    "get_model_generator",
    "ModelGenerator",
    "ModelSpec",
    "get_ui_designer",
    "UIDesigner",
    "UISpec",
    "get_animation_designer",
    "AnimationDesigner",
    "AnimationSpec",
    "get_particle_designer",
    "ParticleDesigner",
    "ParticleSpec",
    "get_sound_designer",
    "SoundDesigner",
    "SoundSpec",

    # Optimization
    "get_performance_optimizer",
    "get_addon_packager",
    "AddonPackager",
    "PackagerConfig",

    # Version Control
    "get_version_manager",
    "VersionManager",
]
