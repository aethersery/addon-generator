# Shadow Slave Addon (Minecraft Bedrock 1.26.40)

An experimental "Shadow Slave" follower addon for Minecraft Bedrock Edition 1.26.40. The shadow slave is a custom entity that follows its owner and can assist in combat.

## Features
- Custom entity: `shadow_slave:shadow_slave`
- Follows the nearest player by default
- Basic melee combat behavior
- Minimal RP/BP setup for testing

## Project Structure
- `ShadowSlave_BP/` - Behavior Pack (entity logic, loot, spawn rules)
- `ShadowSlave_RP/` - Resource Pack (models, textures, animations, render controllers)
- `pack_icon.png` (optional) - add your own icon

## Installation (Windows/Android)
1. Copy `ShadowSlave_BP` and `ShadowSlave_RP` folders to:
   - Windows: `%LOCALAPPDATA%\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang\behavior_packs\` and `resource_packs\`
   - Android: `/storage/emulated/0/Android/data/com.mojang.minecraftpe/files/games/com.mojang/behavior_packs/` and `resource_packs\`
2. Create a world, enable both packs (BP + RP), and load it.

## How to test
- Spawn the entity via `/summon shadow_slave:shadow_slave`
- Or add a spawn egg/recipe later

## Notes for 1.26.40
This uses stable entity components available in 1.26.40. If you see validation errors, check `format_version` fields.

## License
MIT
