"""
UI Designer Agent - Custom screen-space UI for Minecraft Bedrock.

Creates itzriyo157-style interfaces:
- Radial menus with animated segments
- Custom HUD overlays
- Screen-space buttons with animated states
- Gesture-based controls
- Themeable per work aesthetic
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
    DeviceTier,
)
from core.versioned_state import VPPerformanceProfile
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class UISpec:
    """Specification for a UI element."""
    name: str
    ui_type: str  # "radial_menu", "hud", "button", "panel", "screen", "gesture_zone"
    description: str
    theme: str = "default"
    position: dict = field(default_factory=dict)  # x, y, anchor
    size: dict = field(default_factory=dict)  # width, height
    states: list[str] = field(default_factory=lambda: ["default", "hover", "press", "disabled", "cooldown"])
    animations: list[str] = field(default_factory=list)
    bindings: list[str] = field(default_factory=list)  # Script variable bindings
    z_index: int = 0


@dataclass
class UISystem:
    """Complete UI system for an addon."""
    name: str
    elements: list[UISpec] = field(default_factory=list)
    scripts: dict = field(default_factory=dict)  # script_name -> content
    textures: list[str] = field(default_factory=list)  # Required texture names
    variables: list[dict] = field(default_factory=list)  # Dynamic properties
    events: list[dict] = field(default_factory=list)  # Event handlers


class UIDesigner:
    """
    Designs custom UI systems for Bedrock addons.
    Inspired by itzriyo157's custom button/HUD approach.
    """

    def __init__(self):
        self.router = get_router()

    async def design_ui(
        self,
        state: VersionedAddonState,
        target_tier: DeviceTier = DeviceTier.MID_64BIT_4GB,
    ) -> VersionedAddonState:
        """Design complete UI system for the addon."""
        current = state.get_current_version()
        if not current or not current.lore:
            return state

        state.set_status(GenerationStatus.GENERATING_RP, "ui_designer",
                        f"Designing custom UI for {target_tier.value}...")
        state.add_log("Creating itzriyo157-style custom UI system...")

        profile = VPPerformanceProfile.for_tier(target_tier)

        # Analyze what UI is needed based on lore
        ui_specs = await self._analyze_ui_needs(state, profile)

        # Generate UI system
        ui_system = await self._generate_ui_system(state, ui_specs, profile)

        # Create assets
        self._create_ui_assets(current, ui_system)

        state.set_status(GenerationStatus.GENERATING_RP, "ui_designer",
                        f"UI system created: {len(ui_system.elements)} elements, {len(ui_system.scripts)} scripts")
        return state

    async def _analyze_ui_needs(
        self,
        state: VersionedAddonState,
        profile: VPPerformanceProfile,
    ) -> list[UISpec]:
        """Analyze lore and determine needed UI elements."""
        current = state.get_current_version()
        lore = current.lore

        specs = []

        # Core UI always needed
        specs.append(UISpec(
            name="hud_main",
            ui_type="hud",
            description="Main HUD showing health, mana, core powers",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "bottom_center", "x": 0, "y": -50},
            size={"width": 300, "height": 80},
            states=["default", "combat", "low_health", "power_active"],
            bindings=["player.health", "player.mana", "shadow_slave:core_stage"],
        ))

        # Radial menu for power selection
        specs.append(UISpec(
            name="radial_memories",
            ui_type="radial_menu",
            description="Radial menu for selecting Shadow Memories",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "center", "x": 0, "y": 0},
            size={"radius": 120, "segments": 8},
            states=["default", "open", "selecting", "cooldown"],
            animations=["open", "close", "segment_hover", "segment_select"],
            bindings=["shadow_slave:memories", "shadow_slave:selected_memory"],
        ))

        # Quick action buttons
        specs.append(UISpec(
            name="btn_shadow_strike",
            ui_type="button",
            description="Shadow Strike ability button",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "bottom_right", "x": -80, "y": -80},
            size={"width": 64, "height": 64},
            states=["default", "hover", "press", "disabled", "cooldown", "charging"],
            animations=["press", "cooldown_sweep", "charge_glow"],
            bindings=["shadow_slave:shadowstrike_cooldown", "shadow_slave:essence"],
        ))

        specs.append(UISpec(
            name="btn_shadow_mantle",
            ui_type="button",
            description="Shadow Mantle defensive ability",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "bottom_right", "x": -160, "y": -80},
            size={"width": 64, "height": 64},
            states=["default", "hover", "press", "disabled", "cooldown", "active"],
            animations=["press", "cooldown_sweep", "activate_pulse"],
            bindings=["shadow_slave:mantle_cooldown", "shadow_slave:mantle_active"],
        ))

        # Dominate button
        specs.append(UISpec(
            name="btn_dominate",
            ui_type="button",
            description="Dominate shadow ability",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "bottom_right", "x": -240, "y": -80},
            size={"width": 64, "height": 64},
            states=["default", "hover", "press", "disabled", "cooldown", "targeting"],
            animations=["press", "cooldown_sweep", "targeting_pulse"],
            bindings=["shadow_slave:dominate_cooldown", "shadow_slave:dominated_count"],
        ))

        # Echo summon button
        specs.append(UISpec(
            name="btn_echo",
            ui_type="button",
            description="Summon Echo Shade",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "bottom_right", "x": -320, "y": -80},
            size={"width": 64, "height": 64},
            states=["default", "hover", "press", "disabled", "cooldown"],
            animations=["press", "cooldown_sweep", "summon_ripple"],
            bindings=["shadow_slave:echo_cooldown", "shadow_slave:active_echoes"],
        ))

        # Minion management panel
        specs.append(UISpec(
            name="panel_minions",
            ui_type="panel",
            description="Panel showing dominated minions with commands",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "top_right", "x": -20, "y": 20},
            size={"width": 200, "height": 300},
            states=["default", "expanded", "collapsed", "empty"],
            animations=["expand", "collapse", "minion_add", "minion_remove"],
            bindings=["shadow_slave:dominated_list"],
        ))

        # Essence/fragment counter
        specs.append(UISpec(
            name="hud_resources",
            ui_type="hud",
            description="Resource counters (Essence, Fragments, Cores)",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "top_left", "x": 20, "y": 20},
            size={"width": 250, "height": 100},
            states=["default", "gaining", "spending"],
            animations=["gain_pulse", "spend_flash"],
            bindings=["shadow_slave:essence", "shadow_slave:fragments", "shadow_slave:cores"],
        ))

        # Boss health bar (for major encounters)
        specs.append(UISpec(
            name="hud_boss",
            ui_type="hud",
            description="Boss health bar with phase indicators",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "top_center", "x": 0, "y": 20},
            size={"width": 400, "height": 60},
            states=["default", "phase_transition", "enraged", "vulnerable"],
            animations=["phase_flash", "enrage_glow", "vulnerable_pulse"],
            bindings=["shadow_slave:boss_health", "shadow_slave:boss_phase"],
        ))

        # Settings/Config screen
        specs.append(UISpec(
            name="screen_config",
            ui_type="screen",
            description="Addon configuration screen",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "center", "x": 0, "y": 0},
            size={"width": 400, "height": 500},
            states=["default", "general", "controls", "visuals", "performance"],
            animations=["tab_transition", "slider_drag", "toggle_flip"],
            bindings=["shadow_slave:config"],
        ))

        # Gesture zone for touch controls
        specs.append(UISpec(
            name="gesture_combat",
            ui_type="gesture_zone",
            description="Touch gesture zone for combat actions",
            theme=state.theme.lower().replace(" ", "_"),
            position={"anchor": "bottom_left", "x": 0, "y": 0},
            size={"width": "100%", "height": "50%"},
            states=["default", "swipe_up", "swipe_down", "swipe_left", "swipe_right", "tap", "long_press"],
            animations=["gesture_trail", "gesture_confirm"],
            bindings=["shadow_slave:gesture"],
        ))

        return specs

    async def _generate_ui_system(
        self,
        state: VersionedAddonState,
        specs: list[UISpec],
        profile: VPPerformanceProfile,
    ) -> UISystem:
        """Generate complete UI system with scripts and textures."""

        # Use LLM to generate sophisticated UI scripts
        prompt = f"""Create a complete custom UI system for **{state.theme}** Minecraft Bedrock addon.

**UI Elements ({len(specs)}):**
{json.dumps([{
    "name": s.name, "type": s.ui_type, "desc": s.description,
    "position": s.position, "size": s.size, "states": s.states,
    "animations": s.animations, "bindings": s.bindings
} for s in specs], indent=2)}

**Requirements:**
- itzriyo157-style screen-space buttons (not in-game UI)
- Animated states: default, hover, press, disabled, cooldown
- Radial menu with 8 segments, smooth open/close animation
- HUD with dynamic bindings to script variables
- Gesture support for touch devices
- Theme: {state.theme} aesthetic
- Performance tier: {profile.tier.value if hasattr(profile, 'tier') else 'mid'}

**Output JSON:**
```json
{{
  "name": "shadow_slave_ui",
  "elements": [...],
  "scripts": {{
    "ui_main.js": "Main UI controller - handles rendering, input, animations",
    "ui_radial.js": "Radial menu logic",
    "ui_hud.js": "HUD rendering and updates",
    "ui_buttons.js": "Button state machine and animations",
    "ui_gestures.js": "Touch gesture recognition",
  }},
  "textures": ["ui_button_primary", "ui_button_secondary", "ui_radial_menu", "ui_hud_bg", "ui_slot_empty", "ui_slot_filled"],
  "variables": [
    {{"name": "shadow_slave:ui_radial_open", "type": "bool", "default": false}},
    {{"name": "shadow_slave:selected_segment", "type": "int", "default": -1}},
    {{"name": "shadow_slave:button_cooldowns", "type": "map", "default": {{}}}}
  ],
  "events": [
    {{"event": "ui_button_press", "handler": "onButtonPress"}},
    {{"event": "ui_radial_select", "handler": "onRadialSelect"}},
    {{"event": "gesture_detected", "handler": "onGesture"}}
  ]
}}
```"""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                task_type=TaskType.CODE_GENERATION,
                temperature=0.3,
                max_tokens=12000,
            )
            ui_data = json.loads(self._extract_json(response.content))

            return UISystem(
                name=ui_data.get("name", f"{state.theme}_ui"),
                elements=specs,
                scripts=ui_data.get("scripts", {}),
                textures=ui_data.get("textures", []),
                variables=ui_data.get("variables", []),
                events=ui_data.get("events", []),
            )

        except Exception as e:
            logger.error(f"UI system generation failed: {e}")
            # Fallback: basic system
            return UISystem(
                name=f"{state.theme}_ui",
                elements=specs,
                scripts=self._get_fallback_scripts(),
                textures=["ui_button_primary", "ui_button_secondary", "ui_radial_menu", "ui_hud_bg"],
                variables=[
                    {"name": "shadow_slave:ui_radial_open", "type": "bool", "default": False},
                    {"name": "shadow_slave:selected_segment", "type": "int", "default": -1},
                ],
                events=[
                    {"event": "ui_button_press", "handler": "onButtonPress"},
                    {"event": "ui_radial_select", "handler": "onRadialSelect"},
                ],
            )

    def _get_fallback_scripts(self) -> dict:
        """Fallback UI scripts if LLM fails."""
        return {
            "ui_main.js": self._generate_main_ui_script(),
            "ui_radial.js": self._generate_radial_script(),
            "ui_hud.js": self._generate_hud_script(),
            "ui_buttons.js": self._generate_buttons_script(),
            "ui_gestures.js": self._generate_gestures_script(),
        }

    def _generate_main_ui_script(self) -> str:
        return """// Main UI Controller for Shadow Slave
import { world, system, Player, ui } from "@minecraft/server";
import { RadialMenu } from "./ui_radial";
import { HUD } from "./ui_hud";
import { ButtonManager } from "./ui_buttons";
import { GestureRecognizer } from "./ui_gestures";

let radialMenu: RadialMenu;
let hud: HUD;
let buttons: ButtonManager;
let gestures: GestureRecognizer;

world.afterEvents.worldInitialize.subscribe(() => {
    radialMenu = new RadialMenu();
    hud = new HUD();
    buttons = new ButtonManager();
    gestures = new GestureRecognizer();
    registerUI();
});

function registerUI() {
    // Register custom UI screens
    ui.registerScreen("shadow_slave:radial", radialMenu);
    ui.registerScreen("shadow_slave:hud", hud);
    ui.registerScreen("shadow_slave:buttons", buttons);
}

system.runInterval(() => {
    const players = world.getPlayers();
    for (const player of players) {
        updateUI(player);
    }
}, 1); // Every tick for smooth animation

function updateUI(player: Player) {
    hud.update(player);
    buttons.update(player);
    radialMenu.update(player);
    gestures.update(player);
}

// Event handlers
world.beforeEvents.chatSend.subscribe((e) => {
    if (e.message.startsWith("!ui ")) {
        e.cancel = true;
        handleUICommand(e.sender, e.message.slice(4));
    }
});

function handleUICommand(player: Player, cmd: string) {
    if (cmd === "radial") radialMenu.toggle(player);
    if (cmd === "hud") hud.toggle(player);
    if (cmd === "config") ui.showScreen(player, "shadow_slave:config");
}
"""

    def _generate_radial_script(self) -> str:
        return """// Radial Menu System - itzriyo157 style
import { world, system, Player, ui } from "@minecraft/server";

export class RadialMenu {
    private isOpen = false;
    private selectedSegment = -1;
    private segments = 8;
    private animationProgress = 0;
    private targetProgress = 0;

    constructor() {
        this.setupSegments();
    }

    private setupSegments() {
        // Define 8 memory segments
        this.segmentData = [
            { id: "shadow_blade", name: "Shadow Blade", icon: "ui_sword", cost: { essence: 50 } },
            { id: "void_walker", name: "Void Walker", icon: "ui_boots", cost: { essence: 100 } },
            { id: "soul_ward", name: "Soul Ward", icon: "ui_shield", cost: { essence: 75 } },
            { id: "echo_caller", name: "Echo Caller", icon: "ui_summon", cost: { essence: 150 } },
            { id: "shadow_step", name: "Shadow Step", icon: "ui_dash", cost: { essence: 30 } },
            { id: "darkness_veil", name: "Darkness Veil", icon: "ui_cloak", cost: { essence: 80 } },
            { id: "soul_siphon", name: "Soul Siphon", icon: "ui_drain", cost: { essence: 60 } },
            { id: "void_blast", name: "Void Blast", icon: "ui_blast", cost: { essence: 120 } },
        ];
    }

    toggle(player: Player) {
        this.isOpen = !this.isOpen;
        this.targetProgress = this.isOpen ? 1 : 0;
        player.setDynamicProperty("shadow_slave:ui_radial_open", this.isOpen);
    }

    update(player: Player) {
        // Smooth animation
        const speed = 0.15;
        if (this.animationProgress < this.targetProgress) {
            this.animationProgress = Math.min(this.targetProgress, this.animationProgress + speed);
        } else if (this.animationProgress > this.targetProgress) {
            this.animationProgress = Math.max(this.targetProgress, this.animationProgress - speed);
        }

        // Handle input when open
        if (this.isOpen) {
            this.handleInput(player);
        }
    }

    private handleInput(player: Player) {
        // Get mouse/touch position relative to center
        // In practice, use ui.getCursorPosition or similar
        const angle = this.getCursorAngle(player);
        if (angle !== null) {
            this.selectedSegment = Math.floor((angle + Math.PI/8) / (Math.PI/4)) % 8;
            player.setDynamicProperty("shadow_slave:selected_segment", this.selectedSegment);
        }

        // Click/tap to select
        if (this.wasClicked(player)) {
            this.selectSegment(player);
        }
    }

    private getCursorAngle(player: Player): number | null {
        // Implementation depends on input API
        return null; // Placeholder
    }

    private wasClicked(player: Player): boolean {
        return false; // Placeholder
    }

    selectSegment(player: Player) {
        if (this.selectedSegment >= 0 && this.selectedSegment < this.segments) {
            const segment = this.segmentData[this.selectedSegment];
            // Trigger memory activation
            player.runCommand(`function shadow_slave/activate_memory ${segment.id}`);
            this.toggle(player);
        }
    }

    render(renderParams: any) {
        if (this.animationProgress <= 0) return;

        const centerX = renderParams.screenWidth / 2;
        const centerY = renderParams.screenHeight / 2;
        const radius = 120 * this.animationProgress;

        // Draw background ring
        // Draw segments with icons
        // Highlight selected segment
        // Draw center hub
    }
}
"""

    def _generate_hud_script(self) -> str:
        return """// HUD System
import { world, system, Player } from "@minecraft/server";

export class HUD {
    private visible = true;
    private elements = {
        health: { x: 50, y: -50, width: 200, height: 20 },
        mana: { x: 50, y: -25, width: 200, height: 15 },
        coreStage: { x: 50, y: -5, width: 100, height: 15 },
        resources: { x: 20, y: 20, width: 250, height: 80 },
        boss: { x: 0, y: 20, width: 400, height: 60 },
    };

    toggle(player: Player) {
        this.visible = !this.visible;
    }

    update(player: Player) {
        if (!this.visible) return;

        // Update dynamic properties
        const health = player.getDynamicProperty("shadow_slave:health") || 20;
        const maxHealth = player.getDynamicProperty("shadow_slave:max_health") || 20;
        const mana = player.getDynamicProperty("shadow_slave:mana") || 100;
        const coreStage = player.getDynamicProperty("shadow_slave:core_stage") || 0;
        const essence = player.getDynamicProperty("shadow_slave:essence") || 0;
        const fragments = player.getDynamicProperty("shadow_slave:fragments") || 0;
        const cores = player.getDynamicProperty("shadow_slave:cores") || 0;

        // Update HUD elements via dynamic properties for rendering
        player.setDynamicProperty("shadow_slave:hud_health_pct", health / maxHealth);
        player.setDynamicProperty("shadow_slave:hud_mana_pct", mana / 100);
        player.setDynamicProperty("shadow_slave:hud_core_stage", coreStage);
        player.setDynamicProperty("shadow_slave:hud_essence", essence);
        player.setDynamicProperty("shadow_slave:hud_fragments", fragments);
        player.setDynamicProperty("shadow_slave:hud_cores", cores);

        // Boss health
        const bossHealth = player.getDynamicProperty("shadow_slave:boss_health");
        if (bossHealth !== undefined) {
            player.setDynamicProperty("shadow_slave:hud_boss_visible", true);
            player.setDynamicProperty("shadow_slave:hud_boss_pct", bossHealth / 100);
        } else {
            player.setDynamicProperty("shadow_slave:hud_boss_visible", false);
        }
    }
}
"""

    def _generate_buttons_script(self) -> str:
        return """// Button State Machine - itzriyo157 style animated buttons
import { world, system, Player } from "@minecraft/server";

export class ButtonManager {
    private buttons = new Map<string, ButtonState>();

    constructor() {
        this.initButtons();
    }

    private initButtons() {
        const buttonConfigs = [
            { id: "shadow_strike", cooldown: 5, essenceCost: 10 },
            { id: "shadow_mantle", cooldown: 15, essenceCost: 20 },
            { id: "dominate", cooldown: 30, essenceCost: 50 },
            { id: "echo", cooldown: 120, essenceCost: 100 },
        ];

        for (const config of buttonConfigs) {
            this.buttons.set(config.id, {
                id: config.id,
                state: "default",
                cooldown: config.cooldown,
                cooldownRemaining: 0,
                essenceCost: config.essenceCost,
                chargeProgress: 0,
                isCharging: false,
            });
        }
    }

    update(player: Player) {
        const essence = player.getDynamicProperty("shadow_slave:essence") || 0;

        for (const [id, btn] of this.buttons) {
            // Update cooldown
            if (btn.cooldownRemaining > 0) {
                btn.cooldownRemaining -= 1/20; // Per tick
                btn.state = "cooldown";
            } else if (btn.state === "cooldown") {
                btn.state = essence >= btn.essenceCost ? "default" : "disabled";
            }

            // Check affordability
            if (btn.state === "default" && essence < btn.essenceCost) {
                btn.state = "disabled";
            }

            // Sync to dynamic properties for rendering
            player.setDynamicProperty(`shadow_slave:btn_${id}_state`, btn.state);
            player.setDynamicProperty(`shadow_slave:btn_${id}_cooldown`, btn.cooldownRemaining / btn.cooldown);
            player.setDynamicProperty(`shadow_slave:btn_${id}_charging`, btn.isCharging ? 1 : 0);
        }
    }

    press(player: Player, buttonId: string) {
        const btn = this.buttons.get(buttonId);
        if (!btn || btn.state === "disabled" || btn.state === "cooldown") return;

        btn.state = "press";
        btn.isCharging = true;
        btn.chargeProgress = 0;

        // Execute ability after short charge
        system.runTimeout(() => {
            if (btn.isCharging) {
                this.executeAbility(player, buttonId);
                btn.cooldownRemaining = btn.cooldown;
                btn.state = "cooldown";
                btn.isCharging = false;
            }
        }, 0.15 * 20); // 150ms charge time
    }

    release(player: Player, buttonId: string) {
        const btn = this.buttons.get(buttonId);
        if (btn && btn.isCharging) {
            btn.isCharging = false;
            btn.state = btn.cooldownRemaining > 0 ? "cooldown" : "default";
        }
    }

    private executeAbility(player: Player, buttonId: string) {
        const commands = {
            "shadow_strike": "function shadow_slave/shadow_strike",
            "shadow_mantle": "function shadow_slave/shadow_mantle",
            "dominate": "function shadow_slave/dominate",
            "echo": "function shadow_slave/summon_echo",
        };
        if (commands[buttonId]) {
            player.runCommand(commands[buttonId]);
        }
    }
}
"""

    def _generate_gestures_script(self) -> str:
        return """// Touch Gesture Recognition
import { world, system, Player } from "@minecraft/server";

export class GestureRecognizer {
    private touchStart = new Map<string, {x: number, y: number, time: number}>();
    private gestureThreshold = 50; // pixels
    private timeThreshold = 300; // ms

    update(player: Player) {
        // In practice, hook into touch events via ui system
        // This is a conceptual implementation
    }

    private onTouchStart(player: Player, touchId: string, x: number, y: number) {
        this.touchStart.set(touchId, { x, y, time: Date.now() });
    }

    private onTouchEnd(player: Player, touchId: string, x: number, y: number) {
        const start = this.touchStart.get(touchId);
        if (!start) return;

        const dx = x - start.x;
        const dy = y - start.y;
        const dt = Date.now() - start.time;
        const dist = Math.sqrt(dx*dx + dy*dy);

        this.touchStart.delete(touchId);

        if (dt < this.timeThreshold && dist < this.gestureThreshold) {
            // Tap
            this.triggerGesture(player, "tap", { x, y });
        } else if (dist >= this.gestureThreshold) {
            // Swipe
            const angle = Math.atan2(dy, dx);
            let direction = "right";
            if (angle > Math.PI/4 && angle < 3*Math.PI/4) direction = "down";
            else if (angle < -Math.PI/4 && angle > -3*Math.PI/4) direction = "up";
            else if (Math.abs(angle) > 3*Math.PI/4) direction = "left";

            this.triggerGesture(player, `swipe_${direction}`, { x, y, angle, dist });
        } else if (dt >= this.timeThreshold) {
            // Long press
            this.triggerGesture(player, "long_press", { x, y });
        }
    }

    private triggerGesture(player: Player, gesture: string, data: any) {
        player.setDynamicProperty("shadow_slave:gesture", gesture);
        player.setDynamicProperty("shadow_slave:gesture_data", JSON.stringify(data));
        // Reset after 1 tick
        system.runTimeout(() => {
            player.setDynamicProperty("shadow_slave:gesture", "");
        }, 1);
    }
}
"""

    def _create_ui_assets(self, version: 'AddonVersion', ui_system: UISystem):
        """Create GeneratedAsset entries for UI system."""
        # UI definition files
        for script_name, script_content in ui_system.scripts.items():
            version.bp_assets.append(GeneratedAsset(
                asset_type=AssetType.SCRIPT,
                content=script_content,
                metadata={"name": script_name.replace(".js", ""), "path": f"scripts/ui/{script_name}"}
            ))

        # UI JSON definitions
        ui_def = {
            "format_version": "1.21.0",
            "ui_screens": [
                {
                    "screen_name": f"shadow_slave:{spec.name}",
                    "screen_type": spec.ui_type,
                    "position": spec.position,
                    "size": spec.size,
                    "states": spec.states,
                    "animations": spec.animations,
                    "bindings": spec.bindings,
                    "z_index": spec.z_index,
                }
                for spec in ui_system.elements
            ],
        }

        version.rp_assets.append(GeneratedAsset(
            asset_type=AssetType.UI,
            content=ui_def,
            metadata={"name": "ui_definitions"}
        ))

        # Dynamic property definitions
        props_def = {
            "format_version": "1.21.0",
            "dynamic_properties": ui_system.variables,
        }

        version.bp_assets.append(GeneratedAsset(
            asset_type=AssetType.SCRIPT,
            content="// Dynamic properties registered via script",
            metadata={"name": "dynamic_props", "path": "scripts/dynamic_props.js"}
        ))

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
_ui_designer: UIDesigner | None = None


def get_ui_designer() -> UIDesigner:
    global _ui_designer
    if _ui_designer is None:
        _ui_designer = UIDesigner()
    return _ui_designer
