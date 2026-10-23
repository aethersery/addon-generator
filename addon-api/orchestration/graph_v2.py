"""
Dynamic LangGraph v2 - Enhanced orchestration with feedback loops, parallel groups, and version control.

Features:
- Dynamic DAG construction based on generation plan
- Parallel execution groups for independent agents
- Feedback loops for iteration and correction
- Human-in-the-loop checkpoints
- Checkpointing and resume capability
- Version-aware state management
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from enum import Enum

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send

from core.state import (
    VersionedAddonState,
    GenerationStatus,
    AssetType,
)
from core.versioned_state import (
    VersionedAddonState as VState,
    UserFeedback,
    FeedbackType,
    DeviceTier,
)
from agents.theme_researcher import get_theme_researcher
from agents.project_architect import get_project_architect
from agents.lore_deep_researcher import get_lore_deep_researcher
from agents.canon_validator import get_canon_validator
from agents.mc_schema_expert import get_mc_schema_expert
from agents.community_learner import get_community_learner
from agents.performance_optimizer import get_performance_optimizer
from agents.texture_synthesizer import get_texture_synthesizer
from agents.model_generator import get_model_generator
from agents.ui_designer import get_ui_designer
from agents.animation_designer import get_animation_designer
from agents.particle_designer import get_particle_designer
from agents.sound_designer import get_sound_designer
from agents.addon_packager import get_addon_packager

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of nodes in the graph."""
    RESEARCH = "research"
    GENERATION = "generation"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    PACKAGING = "packaging"
    HUMAN_LOOP = "human_loop"
    FEEDBACK = "feedback"


@dataclass
class GraphNode:
    """Graph node configuration."""
    name: str
    agent: str
    node_type: NodeType
    func: Callable
    dependencies: list[str] = field(default_factory=list)
    parallel_group: str = ""
    retry_count: int = 2
    timeout_seconds: int = 300
    human_checkpoint: bool = False
    feedback_loop: bool = False


@dataclass
class ExecutionPlan:
    """Dynamic execution plan."""
    nodes: list[GraphNode]
    parallel_groups: dict[str, list[str]] = field(default_factory=dict)
    feedback_edges: list[tuple[str, str]] = field(default_factory=list)  # from, to
    human_checkpoints: list[str] = field(default_factory=list)
    estimated_duration: int = 0


class DynamicAddonGraph:
    """
    Dynamic LangGraph for addon generation.
    Builds execution graph from ProjectArchitect's plan.
    Supports parallel execution, feedback loops, and human checkpoints.
    """

    def __init__(self):
        self.graph: Optional[StateGraph] = None
        self.nodes: dict[str, GraphNode] = {}
        self.checkpointer = MemorySaver()
        self._register_agents()

    def _register_agents(self):
        """Register all available agents."""
        self.agent_registry = {
            "lore_deep_researcher": get_lore_deep_researcher(),
            "canon_validator": get_canon_validator(),
            "mc_schema_expert": get_mc_schema_expert(),
            "community_learner": get_community_learner(),
            "project_architect": get_project_architect(),
            "performance_optimizer": get_performance_optimizer(),
            "texture_synthesizer": get_texture_synthesizer(),
            "model_generator": get_model_generator(),
            "ui_designer": get_ui_designer(),
            "animation_designer": get_animation_designer(),
            "particle_designer": get_particle_designer(),
            "sound_designer": get_sound_designer(),
            "addon_packager": get_addon_packager(),
        }

        # Node functions mapping
        self.node_functions = {
            "lore_deep_researcher": self._node_lore_deep_researcher,
            "canon_validator": self._node_canon_validator,
            "mc_schema_expert": self._node_mc_schema_expert,
            "community_learner": self._node_community_learner,
            "project_architect": self._node_project_architect,
            "performance_optimizer": self._node_performance_optimizer,
            "texture_synthesizer": self._node_texture_synthesizer,
            "model_generator": self._node_model_generator,
            "ui_designer": self._node_ui_designer,
            "animation_designer": self._node_animation_designer,
            "particle_designer": self._node_particle_designer,
            "sound_designer": self._node_sound_designer,
            "addon_packager": self._node_addon_packager,
            "human_feedback": self._node_human_feedback,
            "feedback_processor": self._node_feedback_processor,
        }

    def build_graph(self, state: VersionedAddonState) -> StateGraph:
        """Build dynamic graph from generation plan."""
        plan = state.generation_plan
        if not plan:
            # Default linear graph
            return self._build_default_graph()

        # Extract execution plan from architect's output
        exec_plan = self._create_execution_plan(plan, state)

        # Build StateGraph
        workflow = StateGraph(VersionedAddonState)

        # Add all nodes
        for node in exec_plan.nodes:
            workflow.add_node(node.name, node.func)
            self.nodes[node.name] = node

        # Add edges based on dependencies and parallel groups
        self._add_edges(workflow, exec_plan)

        # Add feedback edges
        for from_node, to_node in exec_plan.feedback_edges:
            workflow.add_edge(from_node, to_node)

        # Compile
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        return self.graph

    def _create_execution_plan(self, plan: dict, state: VersionedAddonState) -> ExecutionPlan:
        """Create execution plan from architect's plan."""
        nodes = []
        parallel_groups = {}
        feedback_edges = []
        human_checkpoints = []

        # Phase 1: Research (parallel)
        research_nodes = [
            GraphNode("lore_deep_researcher", "lore_deep_researcher", NodeType.RESEARCH,
                     self.node_functions["lore_deep_researcher"],
                     parallel_group="research"),
            GraphNode("community_learner", "community_learner", NodeType.RESEARCH,
                     self.node_functions["community_learner"],
                     parallel_group="research"),
        ]
        nodes.extend(research_nodes)
        parallel_groups["research"] = ["lore_deep_researcher", "community_learner"]

        # Phase 2: Validation (depends on research)
        validation_nodes = [
            GraphNode("canon_validator", "canon_validator", NodeType.VALIDATION,
                     self.node_functions["canon_validator"],
                     dependencies=["lore_deep_researcher", "community_learner"]),
            GraphNode("mc_schema_expert", "mc_schema_expert", NodeType.VALIDATION,
                     self.node_functions["mc_schema_expert"],
                     dependencies=["lore_deep_researcher", "community_learner"]),
        ]
        nodes.extend(validation_nodes)

        # Phase 3: Architecture (depends on validation)
        nodes.append(GraphNode("project_architect", "project_architect", NodeType.GENERATION,
                              self.node_functions["project_architect"],
                              dependencies=["canon_validator", "mc_schema_expert"]))

        # Phase 4: BP Generation (parallel groups)
        bp_groups = plan.get("parallel_groups", {}).get("behavior_pack", [])
        if bp_groups:
            for i, group in enumerate(bp_groups):
                group_name = f"bp_group_{i}"
                parallel_groups[group_name] = group
                # These would be entity_designer, item_designer, etc.
        else:
            # Default BP generation
            bp_nodes = ["entity_designer", "item_designer", "block_designer", "script_engineer"]
            for n in bp_nodes:
                nodes.append(GraphNode(n, n, NodeType.GENERATION,
                                     self.node_functions.get(n, self._node_placeholder),
                                     dependencies=["project_architect"],
                                     parallel_group="bp_generation"))
            parallel_groups["bp_generation"] = bp_nodes

        # Phase 5: RP Generation (parallel)
        rp_nodes = [
            GraphNode("texture_synthesizer", "texture_synthesizer", NodeType.GENERATION,
                     self.node_functions["texture_synthesizer"],
                     dependencies=["project_architect"],
                     parallel_group="rp_generation"),
            GraphNode("model_generator", "model_generator", NodeType.GENERATION,
                     self.node_functions["model_generator"],
                     dependencies=["project_architect"],
                     parallel_group="rp_generation"),
            GraphNode("ui_designer", "ui_designer", NodeType.GENERATION,
                     self.node_functions["ui_designer"],
                     dependencies=["project_architect"],
                     parallel_group="rp_generation"),
            GraphNode("animation_designer", "animation_designer", NodeType.GENERATION,
                     self.node_functions["animation_designer"],
                     dependencies=["model_generator"],
                     parallel_group="rp_generation"),
            GraphNode("particle_designer", "particle_designer", NodeType.GENERATION,
                     self.node_functions["particle_designer"],
                     dependencies=["project_architect"],
                     parallel_group="rp_generation"),
            GraphNode("sound_designer", "sound_designer", NodeType.GENERATION,
                     self.node_functions["sound_designer"],
                     dependencies=["project_architect"],
                     parallel_group="rp_generation"),
        ]
        nodes.extend(rp_nodes)
        parallel_groups["rp_generation"] = [n.name for n in rp_nodes]

        # Phase 6: Optimization (depends on all generation)
        all_gen_nodes = [n.name for n in nodes if n.node_type == NodeType.GENERATION and n.name != "project_architect"]
        nodes.append(GraphNode("performance_optimizer", "performance_optimizer", NodeType.OPTIMIZATION,
                              self.node_functions["performance_optimizer"],
                              dependencies=all_gen_nodes))

        # Phase 7: Validation (depends on optimization)
        nodes.append(GraphNode("final_validation", "mc_schema_expert", NodeType.VALIDATION,
                              self.node_functions["mc_schema_expert"],
                              dependencies=["performance_optimizer"],
                              human_checkpoint=True))
        human_checkpoints.append("final_validation")

        # Phase 8: Packaging
        nodes.append(GraphNode("addon_packager", "addon_packager", NodeType.PACKAGING,
                              self.node_functions["addon_packager"],
                              dependencies=["final_validation"]))

        # Feedback loops
        # If validation fails, go back to relevant generator
        feedback_edges.append(("final_validation", "feedback_processor"))
        nodes.append(GraphNode("feedback_processor", "feedback_processor", NodeType.FEEDBACK,
                              self.node_functions["feedback_processor"],
                              dependencies=["final_validation"]))

        # Human feedback loop
        nodes.append(GraphNode("human_feedback", "human_feedback", NodeType.HUMAN_LOOP,
                              self.node_functions["human_feedback"],
                              dependencies=["feedback_processor"],
                              human_checkpoint=True))
        human_checkpoints.append("human_feedback")
        feedback_edges.append(("human_feedback", "project_architect"))  # Re-plan

        return ExecutionPlan(
            nodes=nodes,
            parallel_groups=parallel_groups,
            feedback_edges=feedback_edges,
            human_checkpoints=human_checkpoints,
        )

    def _add_edges(self, workflow: StateGraph, plan: ExecutionPlan):
        """Add edges to workflow based on plan."""
        # Add sequential edges for dependencies
        for node in plan.nodes:
            for dep in node.dependencies:
                workflow.add_edge(dep, node.name)

        # Handle parallel groups - they run concurrently via LangGraph's Send
        # The parallel execution is handled by the node functions returning Send() commands

        # Connect START to first nodes (no dependencies)
        start_nodes = [n.name for n in plan.nodes if not n.dependencies]
        for n in start_nodes:
            workflow.add_edge(START, n)

        # Connect END from last nodes (no dependents)
        all_deps = set()
        for node in plan.nodes:
            all_deps.update(node.dependencies)
        end_nodes = [n.name for n in plan.nodes if n.name not in all_deps]
        for n in end_nodes:
            workflow.add_edge(n, END)

    def _build_default_graph(self) -> StateGraph:
        """Build default linear graph for backwards compatibility."""
        workflow = StateGraph(VersionedAddonState)

        # Research phase
        workflow.add_node("lore_deep_researcher", self._node_lore_deep_researcher)
        workflow.add_node("community_learner", self._node_community_learner)

        # Validation
        workflow.add_node("canon_validator", self._node_canon_validator)
        workflow.add_node("mc_schema_expert", self._node_mc_schema_expert)

        # Architecture
        workflow.add_node("project_architect", self._node_project_architect)

        # Generation (parallel simulated)
        workflow.add_node("texture_synthesizer", self._node_texture_synthesizer)
        workflow.add_node("model_generator", self._node_model_generator)
        workflow.add_node("ui_designer", self._node_ui_designer)
        workflow.add_node("animation_designer", self._node_animation_designer)
        workflow.add_node("particle_designer", self._node_particle_designer)
        workflow.add_node("sound_designer", self._node_sound_designer)

        # Optimization
        workflow.add_node("performance_optimizer", self._node_performance_optimizer)

        # Validation
        workflow.add_node("final_validation", self._node_mc_schema_expert)

        # Packaging
        workflow.add_node("addon_packager", self._node_addon_packager)

        # Edges
        workflow.add_edge(START, "lore_deep_researcher")
        workflow.add_edge(START, "community_learner")
        workflow.add_edge("lore_deep_researcher", "canon_validator")
        workflow.add_edge("community_learner", "canon_validator")
        workflow.add_edge("lore_deep_researcher", "mc_schema_expert")
        workflow.add_edge("community_learner", "mc_schema_expert")
        workflow.add_edge("canon_validator", "project_architect")
        workflow.add_edge("mc_schema_expert", "project_architect")
        workflow.add_edge("project_architect", "texture_synthesizer")
        workflow.add_edge("project_architect", "model_generator")
        workflow.add_edge("project_architect", "ui_designer")
        workflow.add_edge("project_architect", "particle_designer")
        workflow.add_edge("project_architect", "sound_designer")
        workflow.add_edge("model_generator", "animation_designer")
        workflow.add_edge("texture_synthesizer", "performance_optimizer")
        workflow.add_edge("model_generator", "performance_optimizer")
        workflow.add_edge("ui_designer", "performance_optimizer")
        workflow.add_edge("animation_designer", "performance_optimizer")
        workflow.add_edge("particle_designer", "performance_optimizer")
        workflow.add_edge("sound_designer", "performance_optimizer")
        workflow.add_edge("performance_optimizer", "final_validation")
        workflow.add_edge("final_validation", "addon_packager")
        workflow.add_edge("addon_packager", END)

        self.graph = workflow.compile(checkpointer=self.checkpointer)
        return self.graph

    # =========================================================================
    # Node Functions
    # =========================================================================

    async def _node_lore_deep_researcher(self, state: VersionedAddonState) -> VersionedAddonState:
        researcher = get_lore_deep_researcher()
        return await researcher.research(state)

    async def _node_canon_validator(self, state: VersionedAddonState) -> VersionedAddonState:
        validator = get_canon_validator()
        return await validator.validate(state)

    async def _node_mc_schema_expert(self, state: VersionedAddonState) -> VersionedAddonState:
        expert = get_mc_schema_expert()
        return await expert.validate_all_assets(state)

    async def _node_community_learner(self, state: VersionedAddonState) -> VersionedAddonState:
        learner = get_community_learner()
        return await learner.learn(state)

    async def _node_project_architect(self, state: VersionedAddonState) -> VersionedAddonState:
        architect = get_project_architect()
        return await architect.create_plan(state)

    async def _node_performance_optimizer(self, state: VersionedAddonState) -> VersionedAddonState:
        optimizer = get_performance_optimizer()
        return await optimizer.optimize(state)

    async def _node_texture_synthesizer(self, state: VersionedAddonState) -> VersionedAddonState:
        synthesizer = get_texture_synthesizer()
        # Generate texture specs from plan
        specs = self._create_texture_specs(state)
        return await synthesizer.generate_textures(state, specs)

    async def _node_model_generator(self, state: VersionedAddonState) -> VersionedAddonState:
        generator = get_model_generator()
        specs = self._create_model_specs(state)
        return await generator.generate_models(state, specs)

    async def _node_ui_designer(self, state: VersionedAddonState) -> VersionedAddonState:
        designer = get_ui_designer()
        return await designer.design_ui(state)

    async def _node_animation_designer(self, state: VersionedAddonState) -> VersionedAddonState:
        designer = get_animation_designer()
        return await designer.design_animations(state)

    async def _node_particle_designer(self, state: VersionedAddonState) -> VersionedAddonState:
        designer = get_particle_designer()
        return await designer.design_particles(state)

    async def _node_sound_designer(self, state: VersionedAddonState) -> VersionedAddonState:
        designer = get_sound_designer()
        return await designer.design_sounds(state)

    async def _node_addon_packager(self, state: VersionedAddonState) -> VersionedAddonState:
        packager = get_addon_packager()
        return await packager.package(state)

    async def _node_human_feedback(self, state: VersionedAddonState) -> VersionedAddonState:
        """Checkpoint for human feedback - pauses execution."""
        state.set_status(GenerationStatus.VALIDATING, "human_feedback",
                        "Waiting for human feedback...")
        state.add_log("Human feedback checkpoint reached")
        # In real implementation, this would pause and wait for external input
        # For now, just continue
        return state

    async def _node_feedback_processor(self, state: VersionedAddonState) -> VersionedAddonState:
        """Process validation errors and human feedback to create corrections."""
        current = state.get_current_version()
        if not current:
            return state

        errors = current.validation_errors
        warnings = current.validation_warnings
        feedback = current.feedback

        if not errors and not any(f.status == "open" for f in feedback):
            state.add_log("No errors or feedback to process")
            return state

        state.add_log(f"Processing {len(errors)} errors and {len([f for f in feedback if f.status == 'open'])} open feedback")

        # Create correction plan
        corrections = await self._generate_corrections(state, errors, feedback)

        # Apply corrections by creating new version
        if corrections:
            new_version = f"{current.version}.{len(current.feedback) + 1}"
            state.create_version(
                version=new_version,
                base_version=current.version,
                branch="corrections",
                created_by="agent:feedback_processor",
                changelog=f"Auto-corrections: {len(corrections)} fixes applied",
            )
            state.add_log(f"Created correction version {new_version}")

        return state

    async def _generate_corrections(
        self,
        state: VersionedAddonState,
        errors: list[str],
        feedback: list[UserFeedback],
    ) -> list[dict]:
        """Generate correction plan from errors and feedback."""
        # This would use LLM to create specific fixes
        # For now, return empty - real implementation would be more complex
        return []

    def _create_texture_specs(self, state: VersionedAddonState) -> list:
        """Create texture specs from generation plan."""
        # Import here to avoid circular
        from agents.texture_synthesizer import TextureSpec, TextureType, TextureStyle

        specs = []
        current = state.get_current_version()
        if not current or not current.lore:
            return specs

        # Entity textures
        for entity in current.lore.entities:
            specs.append(TextureSpec(
                name=f"entity_{entity.name}",
                texture_type=TextureType.ENTITY,
                style=TextureStyle(state.style),
                resolution=state.texture_resolution,
                description=entity.description,
            ))

        # Item textures
        for item in current.lore.items:
            specs.append(TextureSpec(
                name=f"item_{item.name}",
                texture_type=TextureType.ITEM,
                style=TextureStyle(state.style),
                resolution=state.texture_resolution,
                description=item.description,
            ))

        # Block textures
        for block in current.lore.blocks:
            specs.append(TextureSpec(
                name=f"block_{block.name}",
                texture_type=TextureType.BLOCK,
                style=TextureStyle(state.style),
                resolution=state.texture_resolution,
                description=block.description,
            ))

        return specs

    def _create_model_specs(self, state: VersionedAddonState) -> list:
        """Create model specs from generation plan."""
        from agents.model_generator import ModelSpec

        specs = []
        current = state.get_current_version()
        if not current or not current.lore:
            return specs

        # Entity models
        for entity in current.lore.entities:
            spec = get_model_generator().create_entity_model_spec(entity)
            specs.append(spec)

        return specs

    async def _node_placeholder(self, state: VersionedAddonState) -> VersionedAddonState:
        """Placeholder for unimplemented nodes."""
        state.add_log("Placeholder node executed")
        return state


# Global instance
_graph_instance: DynamicAddonGraph | None = None


def get_dynamic_graph() -> DynamicAddonGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = DynamicAddonGraph()
    return _graph_instance


async def run_generation_v2(state: VersionedAddonState, thread_id: str = "default") -> VersionedAddonState:
    """Run generation with dynamic graph."""
    graph = get_dynamic_graph()
    compiled = graph.build_graph(state)

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 200,
    }

    logger.info(f"Starting v2 generation for {state.theme} (thread: {thread_id})")

    try:
        final_state = await compiled.ainvoke(state, config=config)
        logger.info(f"Generation completed: {final_state.status}")
        return final_state
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        state.error_message = f"Graph execution failed: {str(e)}"
        state.set_status(GenerationStatus.FAILED, "orchestration", str(e))
        return state


async def run_generation_stream_v2(state: VersionedAddonState, thread_id: str = "default"):
    """Run generation with streaming updates."""
    graph = get_dynamic_graph()
    compiled = graph.build_graph(state)

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 200,
    }

    async for chunk in compiled.astream(state, config=config, stream_mode="values"):
        yield chunk
