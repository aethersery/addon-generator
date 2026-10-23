"""
LangGraph Orchestration - Defines the addon generation workflow as a state graph.

Nodes = Agents (ThemeResearcher, ProjectArchitect, EntityDesigner, etc.)
Edges = Dependencies and data flow
State = AddonState (shared across all nodes)
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from core.state import AddonState, GenerationStatus
from agents.theme_researcher import get_theme_researcher
from agents.project_architect import get_project_architect

logger = logging.getLogger(__name__)


# =============================================================================
# Node Functions
# =============================================================================

async def theme_researcher_node(state: AddonState) -> AddonState:
    """Research the theme/universe lore."""
    researcher = get_theme_researcher()
    return await researcher.research(state)


async def project_architect_node(state: AddonState) -> AddonState:
    """Create the master generation plan."""
    architect = get_project_architect()
    return await architect.create_plan(state)


async def entity_designer_node(state: AddonState) -> AddonState:
    """Design entity JSON definitions (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "entity_designer", "Designing entities")
    state.add_log("Entity designer: TODO - implement entity JSON generation")
    # TODO: Implement entity designer agent
    return state


async def item_designer_node(state: AddonState) -> AddonState:
    """Design item JSON definitions (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "item_designer", "Designing items")
    state.add_log("Item designer: TODO - implement item JSON generation")
    return state


async def block_designer_node(state: AddonState) -> AddonState:
    """Design block JSON definitions (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "block_designer", "Designing blocks")
    state.add_log("Block designer: TODO - implement block JSON generation")
    return state


async def behavior_scripter_node(state: AddonState) -> AddonState:
    """Generate TypeScript/JS behavior scripts (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "behavior_scripter", "Writing behavior scripts")
    state.add_log("Behavior scripter: TODO - implement script generation")
    return state


async def loot_table_designer_node(state: AddonState) -> AddonState:
    """Generate loot tables (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "loot_table_designer", "Creating loot tables")
    state.add_log("Loot table designer: TODO - implement loot table generation")
    return state


async def spawn_rule_designer_node(state: AddonState) -> AddonState:
    """Generate spawn rules (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "spawn_rule_designer", "Creating spawn rules")
    state.add_log("Spawn rule designer: TODO - implement spawn rule generation")
    return state


async def recipe_designer_node(state: AddonState) -> AddonState:
    """Generate crafting recipes (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "recipe_designer", "Creating recipes")
    state.add_log("Recipe designer: TODO - implement recipe generation")
    return state


async def manifest_builder_bp_node(state: AddonState) -> AddonState:
    """Build Behavior Pack manifest (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_BP, "manifest_builder_bp", "Building BP manifest")
    state.add_log("BP Manifest builder: TODO - implement manifest generation")
    return state


async def modeler_node(state: AddonState) -> AddonState:
    """Generate 3D models via Hunyuan3D/Tripo3D (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_MODELS, "modeler", "Generating 3D models")
    state.add_log("3D Modeler: TODO - implement model generation via Hunyuan3D/Tripo3D")
    return state


async def animator_node(state: AddonState) -> AddonState:
    """Generate animations (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_RP, "animator", "Creating animations")
    state.add_log("Animator: TODO - implement animation generation")
    return state


async def anim_controller_node(state: AddonState) -> AddonState:
    """Generate animation controllers (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_RP, "anim_controller", "Creating animation controllers")
    state.add_log("Animation Controller: TODO - implement animation controller generation")
    return state


async def render_controller_node(state: AddonState) -> AddonState:
    """Generate render controllers (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_RP, "render_controller", "Creating render controllers")
    state.add_log("Render Controller: TODO - implement render controller generation")
    return state


async def texture_artist_node(state: AddonState) -> AddonState:
    """Generate textures via FLUX/SD (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_TEXTURES, "texture_artist", "Generating textures")
    state.add_log("Texture Artist: TODO - implement texture generation via Together AI FLUX")
    return state


async def particle_designer_node(state: AddonState) -> AddonState:
    """Generate particle effects (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_RP, "particle_designer", "Creating particles")
    state.add_log("Particle Designer: TODO - implement particle generation")
    return state


async def sound_designer_node(state: AddonState) -> AddonState:
    """Generate sound definitions (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_RP, "sound_designer", "Creating sounds")
    state.add_log("Sound Designer: TODO - implement sound generation")
    return state


async def ui_designer_node(state: AddonState) -> AddonState:
    """Generate UI definitions (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_RP, "ui_designer", "Creating UI")
    state.add_log("UI Designer: TODO - implement UI generation")
    return state


async def manifest_builder_rp_node(state: AddonState) -> AddonState:
    """Build Resource Pack manifest (placeholder for now)."""
    state.set_status(GenerationStatus.GENERATING_RP, "manifest_builder_rp", "Building RP manifest")
    state.add_log("RP Manifest builder: TODO - implement manifest generation")
    return state


async def schema_validator_node(state: AddonState) -> AddonState:
    """Validate all generated JSON against Bedrock schemas (placeholder for now)."""
    state.set_status(GenerationStatus.VALIDATING, "schema_validator", "Validating schemas")
    state.add_log("Schema Validator: TODO - implement validation against bedrock-json-schemas")
    state.validation_passed = True  # Placeholder
    return state


async def packager_node(state: AddonState) -> AddonState:
    """Package into .mcaddon/.mcpack (placeholder for now)."""
    state.set_status(GenerationStatus.PACKAGING, "packager", "Packaging addon")
    state.add_log("Packager: TODO - implement ZIP packaging")
    return state


async def automated_tester_node(state: AddonState) -> AddonState:
    """Test addon in Bedrock Dedicated Server (placeholder for now)."""
    state.set_status(GenerationStatus.TESTING, "automated_tester", "Testing in BDS")
    state.add_log("Automated Tester: TODO - implement BDS headless testing")
    state.tests_passed = True  # Placeholder
    return state


async def doc_generator_node(state: AddonState) -> AddonState:
    """Generate documentation (placeholder for now)."""
    state.set_status(GenerationStatus.COMPLETED, "doc_generator", "Generating documentation")
    state.add_log("Doc Generator: TODO - implement documentation generation")
    return state


# =============================================================================
# Conditional Edges
# =============================================================================

def check_research_complete(state: AddonState) -> str:
    """Check if research completed successfully."""
    if state.research_complete and state.lore:
        return "continue"
    return "failed"


def check_plan_complete(state: AddonState) -> str:
    """Check if planning completed successfully."""
    if state.plan_complete and state.plan:
        return "continue"
    return "failed"


def check_bp_complete(state: AddonState) -> str:
    """Check if BP generation completed."""
    # In real implementation, check if all planned BP assets are generated
    return "continue"


def check_rp_complete(state: AddonState) -> str:
    """Check if RP generation completed."""
    return "continue"


def check_validation_passed(state: AddonState) -> str:
    """Check if validation passed."""
    if state.validation_passed:
        return "passed"
    return "failed"


# =============================================================================
# Graph Builder
# =============================================================================

def create_addon_generation_graph() -> StateGraph:
    """Create the LangGraph state graph for addon generation."""

    # Define the graph with AddonState as the state schema
    workflow = StateGraph(AddonState)

    # Add nodes (agents)
    workflow.add_node("theme_researcher", theme_researcher_node)
    workflow.add_node("project_architect", project_architect_node)

    # BP Generation nodes (parallel group 1)
    workflow.add_node("entity_designer", entity_designer_node)
    workflow.add_node("item_designer", item_designer_node)
    workflow.add_node("block_designer", block_designer_node)

    # BP Generation nodes (parallel group 2 - depend on group 1)
    workflow.add_node("behavior_scripter", behavior_scripter_node)
    workflow.add_node("loot_table_designer", loot_table_designer_node)
    workflow.add_node("spawn_rule_designer", spawn_rule_designer_node)
    workflow.add_node("recipe_designer", recipe_designer_node)

    # BP Manifest (depends on all BP assets)
    workflow.add_node("manifest_builder_bp", manifest_builder_bp_node)

    # RP Generation nodes (parallel group 1)
    workflow.add_node("modeler", modeler_node)
    workflow.add_node("texture_artist", texture_artist_node)

    # RP Generation nodes (parallel group 2 - depend on models/textures)
    workflow.add_node("animator", animator_node)
    workflow.add_node("anim_controller", anim_controller_node)
    workflow.add_node("render_controller", render_controller_node)
    workflow.add_node("particle_designer", particle_designer_node)
    workflow.add_node("sound_designer", sound_designer_node)
    workflow.add_node("ui_designer", ui_designer_node)

    # RP Manifest
    workflow.add_node("manifest_builder_rp", manifest_builder_rp_node)

    # Finalization nodes
    workflow.add_node("schema_validator", schema_validator_node)
    workflow.add_node("packager", packager_node)
    workflow.add_node("automated_tester", automated_tester_node)
    workflow.add_node("doc_generator", doc_generator_node)

    # Define edges (sequential flow with parallel branches)

    # Start -> Research -> Plan
    workflow.add_edge(START, "theme_researcher")
    workflow.add_conditional_edges(
        "theme_researcher",
        check_research_complete,
        {"continue": "project_architect", "failed": END}
    )
    workflow.add_conditional_edges(
        "project_architect",
        check_plan_complete,
        {"continue": "entity_designer", "failed": END}  # Will fan out from entity_designer
    )

    # Parallel Group 1: Entity, Item, Block designers (independent)
    workflow.add_edge("entity_designer", "item_designer")
    workflow.add_edge("item_designer", "block_designer")

    # After block_designer, fan out to parallel group 2
    workflow.add_edge("block_designer", "behavior_scripter")
    workflow.add_edge("block_designer", "loot_table_designer")
    workflow.add_edge("block_designer", "spawn_rule_designer")
    workflow.add_edge("block_designer", "recipe_designer")

    # All BP designers converge to manifest builder
    workflow.add_edge("behavior_scripter", "manifest_builder_bp")
    workflow.add_edge("loot_table_designer", "manifest_builder_bp")
    workflow.add_edge("spawn_rule_designer", "manifest_builder_bp")
    workflow.add_edge("recipe_designer", "manifest_builder_bp")

    # BP Manifest -> RP Generation (Modeler + Texture Artist in parallel)
    workflow.add_edge("manifest_builder_bp", "modeler")
    workflow.add_edge("manifest_builder_bp", "texture_artist")

    # Modeler -> Animator, AnimController, RenderController
    workflow.add_edge("modeler", "animator")
    workflow.add_edge("animator", "anim_controller")
    workflow.add_edge("anim_controller", "render_controller")

    # Texture Artist -> Particle, Sound, UI (can run parallel with animation chain)
    workflow.add_edge("texture_artist", "particle_designer")
    workflow.add_edge("texture_artist", "sound_designer")
    workflow.add_edge("texture_artist", "ui_designer")

    # All RP generators converge to RP manifest
    workflow.add_edge("render_controller", "manifest_builder_rp")
    workflow.add_edge("particle_designer", "manifest_builder_rp")
    workflow.add_edge("sound_designer", "manifest_builder_rp")
    workflow.add_edge("ui_designer", "manifest_builder_rp")

    # RP Manifest -> Validation -> Packaging -> Testing -> Docs
    workflow.add_edge("manifest_builder_rp", "schema_validator")
    workflow.add_conditional_edges(
        "schema_validator",
        check_validation_passed,
        {"passed": "packager", "failed": END}
    )
    workflow.add_edge("packager", "automated_tester")
    workflow.add_edge("automated_tester", "doc_generator")
    workflow.add_edge("doc_generator", END)

    # Compile with memory checkpointing
    return workflow.compile(checkpointer=MemorySaver())


# =============================================================================
# Execution Helper
# =============================================================================

async def run_generation(state: AddonState, thread_id: str = "default") -> AddonState:
    """
    Run the complete addon generation workflow.

    Args:
        state: Initial AddonState with theme, preferences, etc.
        thread_id: Unique identifier for this generation run (for checkpointing)

    Returns:
        Final AddonState with all generated assets
    """
    graph = create_addon_generation_graph()

    # Configuration for the run
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,  # Prevent infinite loops
    }

    logger.info(f"Starting addon generation for theme: {state.theme} (thread: {thread_id})")

    try:
        # Run the graph
        final_state = await graph.ainvoke(state, config=config)
        logger.info(f"Generation completed with status: {final_state.status}")
        return final_state
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        state.error_message = f"Graph execution failed: {str(e)}"
        state.set_status(GenerationStatus.FAILED, "orchestration", str(e))
        return state


async def run_generation_stream(state: AddonState, thread_id: str = "default"):
    """
    Run generation with streaming updates.

    Yields:
        AddonState at each step for real-time UI updates.
    """
    graph = create_addon_generation_graph()

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }

    async for chunk in graph.astream(state, config=config, stream_mode="values"):
        yield chunk


# =============================================================================
# Visualization (for debugging)
# =============================================================================

def visualize_graph() -> str:
    """Generate Mermaid diagram of the graph."""
    graph = create_addon_generation_graph()
    return graph.get_graph().draw_mermaid()
