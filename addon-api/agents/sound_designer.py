"""
Sound Designer Agent - Immersive audio for Minecraft Bedrock.

Creates sound definitions, events, and configurations:
- 3D positional audio
- Layered sound events
- Volume/distance curves
- Dynamic audio based on game state
- OGG Vorbis encoding specs
- Sound categorization and mixing
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
    LoreEntity,
    LoreItem,
    DeviceTier,
)
from core.versioned_state import VPPerformanceProfile
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class SoundSpec:
    """Specification for a sound effect."""
    name: str
    sound_type: str  # "entity", "item", "block", "ambient", "music", "ui", "mechanic"
    description: str
    category: str = "neutral"  # neutral, hostile, friendly, player, master, record, weather
    volume: float = 1.0
    pitch: float = 1.0
    pitch_variation: float = 0.1
    volume_variation: float = 0.1
    distance_filter: dict = field(default_factory=dict)  # min, max, curve
    streaming: bool = False
    preload: bool = True
    replace: bool = False
    sound_files: list[str] = field(default_factory=list)  # OGG file names
    weight: int = 1  # For random selection


@dataclass
class SoundEvent:
    """A sound event definition."""
    name: str
    sounds: list[dict] = field(default_factory=list)  # {name, volume, pitch, weight}
    min_distance: float = 1.0
    max_distance: float = 50.0
    volume_curve: list[tuple[float, float]] = field(default_factory=lambda: [(0, 1), (16, 0.5), (50, 0)])
    is_3d: bool = True


@dataclass
class SoundSystem:
    """Complete sound system for an addon."""
    name: str
    definitions: dict[str, dict] = field(default_factory=dict)  # sound_definitions.json
    events: dict[str, SoundEvent] = field(default_factory=dict)
    categories: dict[str, dict] = field(default_factory=dict)
    music: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class SoundDesigner:
    """
    Designs immersive audio systems for Bedrock addons.
    3D positional, layered, dynamic volume curves.
    """

    def __init__(self):
        self.router = get_router()

    async def design_sounds(
        self,
        state: VersionedAddonState,
        target_tier: DeviceTier = DeviceTier.MID_64BIT_4GB,
    ) -> VersionedAddonState:
        """Design sound system for the addon."""
        current = state.get_current_version()
        if not current or not current.lore:
            return state

        state.set_status(GenerationStatus.GENERATING_RP, "sound_designer",
                        f"Designing sounds for {target_tier.value}...")
        state.add_log("Creating immersive audio system...")

        profile = VPPerformanceProfile.for_tier(target_tier)
        sound_system = await self._design_sound_system(state, profile)

        # Create assets
        self._create_sound_assets(current, sound_system)

        state.set_status(GenerationStatus.GENERATING_RP, "sound_designer",
                        f"Created {len(sound_system.definitions)} sound definitions")
        return state

    async def _design_sound_system(
        self,
        state: VersionedAddonState,
        profile: VPPerformanceProfile,
    ) -> SoundSystem:
        """Design complete sound system."""
        current = state.get_current_version()
        lore = current.lore

        specs = []

        # Entity sounds
        for entity in lore.entities:
            specs.extend(self._entity_sounds(entity))

        # Item sounds
        for item in lore.items:
            specs.extend(self._item_sounds(item))

        # Block sounds
        for block in lore.blocks:
            specs.extend(self._block_sounds(block))

        # Biome ambience
        for biome in lore.biomes:
            specs.extend(self._biome_ambience(biome))

        # Mechanic sounds
        for mechanic in lore.mechanics:
            specs.extend(self._mechanic_sounds(mechanic))

        # UI sounds
        specs.extend(self._ui_sounds())

        # Music
        specs.extend(self._music_tracks(state.theme))

        # Generate sound definitions
        definitions = {}
        events = {}

        for spec in specs:
            defn, event = await self._generate_sound_definition(spec, profile)
            definitions[spec.name] = defn
            events[spec.name] = event

        return SoundSystem(
            name=f"{state.theme}_sounds",
            definitions=definitions,
            events=events,
            categories=self._create_categories(),
            music=self._create_music_config(state.theme),
            metadata={
                "total_sounds": len(definitions),
                "total_events": len(events),
                "tier": profile.tier.value if hasattr(profile, 'tier') else "unknown",
            }
        )

    def _entity_sounds(self, entity: LoreEntity) -> list[SoundSpec]:
        """Generate sound specs for entity."""
        specs = []
        base = entity.name

        # Living sounds
        specs.append(SoundSpec(
            name=f"{base}.living",
            sound_type="entity",
            description=f"Living/idle sounds for {entity.display_name}",
            category="hostile" if entity.entity_type in ["mob", "boss"] else "neutral",
            volume=0.8,
            pitch_variation=0.2,
            sound_files=[f"{base}_living1.ogg", f"{base}_living2.ogg", f"{base}_living3.ogg"],
            weight=1,
        ))

        # Hurt sounds
        specs.append(SoundSpec(
            name=f"{base}.hurt",
            sound_type="entity",
            description=f"Hurt sounds for {entity.display_name}",
            category="hostile",
            volume=1.0,
            pitch_variation=0.15,
            sound_files=[f"{base}_hurt1.ogg", f"{base}_hurt2.ogg"],
            weight=1,
        ))

        # Death sounds
        specs.append(SoundSpec(
            name=f"{base}.death",
            sound_type="entity",
            description=f"Death sounds for {entity.display_name}",
            category="hostile",
            volume=1.0,
            pitch_variation=0.1,
            sound_files=[f"{base}_death1.ogg", f"{base}_death2.ogg"],
            weight=1,
        ))

        # Step sounds
        specs.append(SoundSpec(
            name=f"{base}.step",
            sound_type="entity",
            description=f"Footstep sounds for {entity.display_name}",
            category="neutral",
            volume=0.6,
            pitch_variation=0.1,
            sound_files=[f"{base}_step1.ogg", f"{base}_step2.ogg", f"{base}_step3.ogg", f"{base}_step4.ogg"],
            weight=1,
        ))

        # Attack sounds
        specs.append(SoundSpec(
            name=f"{base}.attack",
            sound_type="entity",
            description=f"Attack sounds for {entity.display_name}",
            category="hostile",
            volume=1.0,
            pitch_variation=0.1,
            sound_files=[f"{base}_attack1.ogg", f"{base}_attack2.ogg"],
            weight=1,
        ))

        # Special ability sounds
        for ability in entity.abilities:
            specs.append(SoundSpec(
                name=f"{base}.{ability.lower().replace(' ', '_')}",
                sound_type="entity",
                description=f"{ability} sound effect",
                category="hostile",
                volume=1.0,
                pitch=1.0,
                sound_files=[f"{base}_{ability.lower().replace(' ', '_')}.ogg"],
                weight=1,
            ))

        return specs

    def _item_sounds(self, item: LoreItem) -> list[SoundSpec]:
        """Generate sound specs for item."""
        specs = []
        base = item.name

        # Use sound
        specs.append(SoundSpec(
            name=f"{base}.use",
            sound_type="item",
            description=f"Use sound for {item.display_name}",
            category="player",
            volume=1.0,
            pitch_variation=0.05,
            sound_files=[f"{base}_use.ogg"],
            weight=1,
        ))

        # Break sound (for tools/weapons)
        if item.item_type in ["sword", "pickaxe", "axe", "shovel", "hoe"]:
            specs.append(SoundSpec(
                name=f"{base}.break",
                sound_type="item",
                description=f"Break sound for {item.display_name}",
                category="player",
                volume=0.8,
                sound_files=[f"{base}_break.ogg"],
                weight=1,
            ))

        # Equip/unequip
        if item.item_type in ["sword", "armor", "tool"]:
            specs.append(SoundSpec(
                name=f"{base}.equip",
                sound_type="item",
                description=f"Equip sound for {item.display_name}",
                category="player",
                volume=0.7,
                sound_files=[f"{base}_equip.ogg"],
                weight=1,
            ))

        return specs

    def _block_sounds(self, block: Any) -> list[SoundSpec]:
        """Generate sound specs for block."""
        specs = []
        base = block.name if hasattr(block, 'name') else str(block)

        # Place
        specs.append(SoundSpec(
            name=f"{base}.place",
            sound_type="block",
            description=f"Place sound for {block.display_name if hasattr(block, 'display_name') else base}",
            category="neutral",
            volume=1.0,
            sound_files=[f"{base}_place.ogg"],
            weight=1,
        ))

        # Break
        specs.append(SoundSpec(
            name=f"{base}.break",
            sound_type="block",
            description=f"Break sound for {block.display_name if hasattr(block, 'display_name') else base}",
            category="neutral",
            volume=1.0,
            sound_files=[f"{base}_break.ogg"],
            weight=1,
        ))

        # Step
        specs.append(SoundSpec(
            name=f"{base}.step",
            sound_type="block",
            description=f"Step sound for {block.display_name if hasattr(block, 'display_name') else base}",
            category="neutral",
            volume=0.8,
            sound_files=[f"{base}_step1.ogg", f"{base}_step2.ogg", f"{base}_step3.ogg", f"{base}_step4.ogg"],
            weight=1,
        ))

        # Hit
        specs.append(SoundSpec(
            name=f"{base}.hit",
            sound_type="block",
            description=f"Hit sound for {block.display_name if hasattr(block, 'display_name') else base}",
            category="neutral",
            volume=0.6,
            sound_files=[f"{base}_hit1.ogg", f"{base}_hit2.ogg"],
            weight=1,
        ))

        # Fall
        specs.append(SoundSpec(
            name=f"{base}.fall",
            sound_type="block",
            description=f"Fall sound for {block.display_name if hasattr(block, 'display_name') else base}",
            category="neutral",
            volume=0.8,
            sound_files=[f"{base}_fall.ogg"],
            weight=1,
        ))

        return specs

    def _biome_ambience(self, biome: Any) -> list[SoundSpec]:
        """Generate ambient sounds for biome."""
        specs = []
        base = biome.name if hasattr(biome, 'name') else str(biome)

        # Mood/ambient
        specs.append(SoundSpec(
            name=f"{base}.ambient",
            sound_type="ambient",
            description=f"Ambient mood for {biome.display_name if hasattr(biome, 'display_name') else base}",
            category="weather",
            volume=0.3,
            streaming=True,
            sound_files=[f"{base}_ambient1.ogg", f"{base}_ambient2.ogg", f"{base}_ambient3.ogg"],
            weight=1,
        ))

        # Additions
        specs.append(SoundSpec(
            name=f"{base}.additions",
            sound_type="ambient",
            description=f"Ambient additions for {biome.display_name if hasattr(biome, 'display_name') else base}",
            category="weather",
            volume=0.2,
            sound_files=[f"{base}_addition1.ogg", f"{base}_addition2.ogg"],
            weight=1,
        ))

        return specs

    def _mechanic_sounds(self, mechanic: LoreMechanic) -> list[SoundSpec]:
        """Generate sound specs for mechanic."""
        specs = []
        base = mechanic.name

        specs.append(SoundSpec(
            name=f"{base}.activate",
            sound_type="mechanic",
            description=f"Activation sound for {mechanic.name}",
            category="neutral",
            volume=0.8,
            sound_files=[f"{base}_activate.ogg"],
            weight=1,
        ))

        specs.append(SoundSpec(
            name=f"{base}.loop",
            sound_type="mechanic",
            description=f"Looping sound for {mechanic.name}",
            category="neutral",
            volume=0.4,
            sound_files=[f"{base}_loop.ogg"],
            weight=1,
        ))

        return specs

    def _ui_sounds(self) -> list[SoundSpec]:
        """Generate UI sound specs."""
        return [
            SoundSpec(
                name="ui_button_click",
                sound_type="ui",
                description="Button click sound",
                category="master",
                volume=0.7,
                sound_files=["ui_click.ogg"],
                weight=1,
            ),
            SoundSpec(
                name="ui_button_hover",
                sound_type="ui",
                description="Button hover sound",
                category="master",
                volume=0.3,
                sound_files=["ui_hover.ogg"],
                weight=1,
            ),
            SoundSpec(
                name="ui_radial_open",
                sound_type="ui",
                description="Radial menu open",
                category="master",
                volume=0.8,
                sound_files=["ui_radial_open.ogg"],
                weight=1,
            ),
            SoundSpec(
                name="ui_radial_select",
                sound_type="ui",
                description="Radial menu segment select",
                category="master",
                volume=0.6,
                sound_files=["ui_radial_select.ogg"],
                weight=1,
            ),
            SoundSpec(
                name="ui_resource_gain",
                sound_type="ui",
                description="Resource gained",
                category="master",
                volume=0.7,
                sound_files=["ui_gain.ogg"],
                weight=1,
            ),
            SoundSpec(
                name="ui_resource_spend",
                sound_type="ui",
                description="Resource spent",
                category="master",
                volume=0.6,
                sound_files=["ui_spend.ogg"],
                weight=1,
            ),
            SoundSpec(
                name="ui_notification",
                sound_type="ui",
                description="Notification sound",
                category="master",
                volume=0.8,
                sound_files=["ui_notify.ogg"],
                weight=1,
            ),
            SoundSpec(
                name="ui_error",
                sound_type="ui",
                description="Error/invalid action",
                category="master",
                volume=0.7,
                sound_files=["ui_error.ogg"],
                weight=1,
            ),
        ]

    def _music_tracks(self, theme: str) -> list[SoundSpec]:
        """Generate music track specs."""
        return [
            SoundSpec(
                name=f"{theme.lower().replace(' ', '_')}_menu",
                sound_type="music",
                description="Main menu music",
                category="record",
                volume=0.6,
                streaming=True,
                sound_files=[f"{theme.lower().replace(' ', '_')}_menu.ogg"],
                weight=1,
            ),
            SoundSpec(
                name=f"{theme.lower().replace(' ', '_')}_exploration",
                sound_type="music",
                description="Exploration music",
                category="record",
                volume=0.4,
                streaming=True,
                sound_files=[f"{theme.lower().replace(' ', '_')}_explore1.ogg", f"{theme.lower().replace(' ', '_')}_explore2.ogg"],
                weight=1,
            ),
            SoundSpec(
                name=f"{theme.lower().replace(' ', '_')}_combat",
                sound_type="music",
                description="Combat music",
                category="record",
                volume=0.7,
                streaming=True,
                sound_files=[f"{theme.lower().replace(' ', '_')}_combat1.ogg", f"{theme.lower().replace(' ', '_')}_combat2.ogg"],
                weight=1,
            ),
            SoundSpec(
                name=f"{theme.lower().replace(' ', '_')}_boss",
                sound_type="music",
                description="Boss battle music",
                category="record",
                volume=0.8,
                streaming=True,
                sound_files=[f"{theme.lower().replace(' ', '_')}_boss.ogg"],
                weight=1,
            ),
        ]

    async def _generate_sound_definition(
        self,
        spec: SoundSpec,
        profile: VPPerformanceProfile,
    ) -> tuple[dict, SoundEvent]:
        """Generate sound definition and event."""
        # Adjust for tier
        volume = spec.volume
        if profile.tier == "low_32bit_2gb":
            volume *= 0.8

        # Sound definition (sound_definitions.json)
        definition = {
            "format_version": "1.14.0",
            "sound_definitions": {
                spec.name: {
                    "category": spec.category,
                    "sounds": [
                        {
                            "name": f"sounds/{sf}",
                            "volume": volume * (1 + spec.volume_variation * (0.5 - hash(sf) % 100 / 100)),
                            "pitch": spec.pitch * (1 + spec.pitch_variation * (0.5 - hash(sf) % 100 / 100)),
                            "weight": spec.weight,
                            "stream": spec.streaming,
                            "preload": spec.preload,
                        }
                        for sf in spec.sound_files
                    ],
                    "min_distance": 1.0,
                    "max_distance": 50.0,
                    "volume_curve": [[0, 1], [16, 0.5], [50, 0]],
                }
            }
        }

        # Sound event (for scripting)
        event = SoundEvent(
            name=spec.name,
            sounds=[
                {"name": sf, "volume": volume, "pitch": spec.pitch, "weight": spec.weight}
                for sf in spec.sound_files
            ],
            min_distance=1.0,
            max_distance=50.0,
            is_3d=spec.sound_type != "ui",
        )

        return definition, event

    def _create_categories(self) -> dict:
        """Create sound category mixing config."""
        return {
            "master": {"volume": 1.0},
            "music": {"volume": 0.7},
            "record": {"volume": 0.8},
            "weather": {"volume": 0.5},
            "block": {"volume": 1.0},
            "hostile": {"volume": 1.0},
            "neutral": {"volume": 0.8},
            "player": {"volume": 1.0},
            "ambient": {"volume": 0.6},
        }

    def _create_music_config(self, theme: str) -> dict:
        """Create music configuration."""
        return {
            "menu": {
                "track": f"{theme.lower().replace(' ', '_')}_menu",
                "delay": {"min": 0, "max": 0},
                "replace_current_music": True,
            },
            "game": {
                "track": f"{theme.lower().replace(' ', '_')}_exploration",
                "delay": {"min": 120, "max": 300},
                "replace_current_music": False,
            },
            "creative": {
                "track": f"{theme.lower().replace(' ', '_')}_exploration",
                "delay": {"min": 120, "max": 300},
            },
            "nether": {
                "track": f"{theme.lower().replace(' ', '_')}_combat",
                "delay": {"min": 60, "max": 180},
            },
            "end": {
                "track": f"{theme.lower().replace(' ', '_')}_boss",
                "delay": {"min": 30, "max": 120},
            },
        }

    def _create_sound_assets(self, version: 'AddonVersion', system: SoundSystem):
        """Create GeneratedAsset entries for sounds."""
        # Sound definitions
        version.rp_assets.append(GeneratedAsset(
            asset_type=AssetType.SOUND,
            content=system.definitions,
            metadata={"name": "sound_definitions"}
        ))

        # Music definitions
        if system.music:
            version.rp_assets.append(GeneratedAsset(
                asset_type=AssetType.SOUND,
                content={
                    "format_version": "1.14.0",
                    "music_definitions": system.music,
                },
                metadata={"name": "music_definitions"}
            ))

        # Note: Actual OGG files would be generated separately
        # Track needed files
        version.metadata = version.metadata or {}
        version.metadata["sound_files_needed"] = []
        for defn in system.definitions.values():
            for sd in defn.get("sound_definitions", {}).values():
                for s in sd.get("sounds", []):
                    version.metadata["sound_files_needed"].append(s["name"])


# Singleton
_sound_designer: SoundDesigner | None = None


def get_sound_designer() -> SoundDesigner:
    global _sound_designer
    if _sound_designer is None:
        _sound_designer = SoundDesigner()
    return _sound_designer
