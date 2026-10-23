import { world, system, Player, ItemStack, EquipmentSlot, Block, Entity, EffectType, EntityDamageCause, EntityQueryOptions } from "@minecraft/server";

// ============================================================
// SHADOW SLAVE - FASE 5: MEMÓRIAS REAIS, ECOS E CHEFE OPCIONAL
// ============================================================

// ============================================================
// CONFIG — VALORES PROVISÓRIOS (AJUSTAR CONFORME NOVEL)
// TODO: VERIFICAR NA NOVEL todos os valores marcados como PROVISÓRIO
// ============================================================
const CONFIG = {
  // Dominação
  domination: {
    cost: { essence: 100, fragments: 10, cores: 2 },      // PROVISÓRIO
    maxPerPlayer: 3,                                       // PROVISÓRIO
    requiredStage: 3,                                      // PROVISÓRIO
    range: 10, coneAngle: Math.PI / 3
  },
  
  // Memórias — efeitos reais (aplicados nas skills)
  memories: {
    memory_shadow_blade:    { shadowstrikeDamageBonus: 4 },           // PROVISÓRIO
    memory_void_walker:     { perceptionRangeBonus: 10, shadowstrikeRangeBonus: 4 }, // PROVISÓRIO
    memory_soul_ward:       { mantleDurationBonus: 10, damageReductionBonus: 0.15 }, // PROVISÓRIO
    memory_echo_caller:     { echoSummonChance: 0.2 }                 // PROVISÓRIO
  },
  
  // Ecos
  echoes: {
    echo_shade: { damage: 5, duration: 30, cooldown: 120, health: 30 }, // PROVISÓRIO
    maxActive: 1
  },
  
  // Núcleos — regras de progressão (PROVISÓRIO — NÃO CANON)
  // Humanos comuns: máximo 1 Núcleo; Aspecto Divino: máximo 7 Núcleos total
  cores: {
    maxNormal: 1,                         // Humano comum: 1 Núcleo (canônico)
    divineMaxCores: 7,                    // Aspecto Divino: máximo 7 Núcleos total (canônico)
    enhancedCoreName: "soul_core_enhanced" // Nome do item futuro (PROVISÓRIO)
  },
  
  // Boss (opcional)
  nightmare: {
    spawnCommand: "!nightmare",           // Admin only
    health: 500,
    damage: 20,
    loot: { enhancedCoreChance: 0.3, essence: 200 }
  },
  
  // Habilidades base (valores originais preservados)
  skills: {
    perception: { essenceCost: 5, cooldown: 30, range: 20 },
    shadowstrike: { essenceCost: 15, cooldown: 20, range: 8, damage: 8 },
    shadowmantle: { essenceCost: 25, cooldown: 60, duration: 15, damageReduction: 0.5 }
  }
};

// Ranks Humanos (canônicos) — separados das Classes de Criaturas
const HUMAN_RANKS = [
  { id: 0, name: "Dormant", colloquial: "Sleeper", description: "Não estabeleceu conexão com o Dream Realm" },
  { id: 1, name: "Awakened", colloquial: "Awakened", description: "Entra no Dream Realm; Aspecto ganha 2ª habilidade" },
  { id: 2, name: "Ascended", colloquial: "Master", description: "Acima da natureza humana; Aspecto ganha 3ª habilidade; viaja fisicamente" },
  { id: 3, name: "Transcendent", colloquial: "Saint", description: "Qualidades divinas; ganha Transformation Ability; viaja com outros" },
  { id: 4, name: "Supreme", colloquial: "Sovereign", description: "Autoridade e reinado; ganha Domain; ponte entre mundos" },
  { id: 5, name: "Sacred", colloquial: "Spirit", description: "Qualidades divinas; semideus menor" },
  { id: 6, name: "Divine", colloquial: "God", description: "Qualidade divina máxima" }
];

// Classes de Criaturas do Pesadelo (canônicas) — separadas dos Ranks Humanos
const CREATURE_CLASSES = [
  { id: 1, name: "Beast", description: "Perigosa e forte, mas sem mente" },
  { id: 2, name: "Monster", description: "Mais devastadora, inteligência rudimentar" },
  { id: 3, name: "Demon", description: "Semblante de inteligência, pode adquirir habilidade" },
  { id: 5, name: "Devil", description: "Poderes antinaturales" },
  { id: 5, name: "Tyrant", description: "Cria e controla exércitos de servos menores" },
  { id: 6, name: "Terror", description: "Influencia o entorno" },
  { id: 7, name: "Titan", description: "Mítico, também conhecido como Calamidade" }
];

// Stages configuration (mantida para compatibilidade; mapeia para HUMAN_RANKS)
const STAGES = [
  { id: 0, name: "Mundano", essence: 0, fragments: 0, cores: 0, maxSkills: 0 },
  { id: 1, name: "Desperto", essence: 50, fragments: 5, cores: 1, maxSkills: 1 },
  { id: 2, name: "Ascendido", essence: 200, fragments: 15, cores: 3, maxSkills: 2 },
  { id: 3, name: "Transcendente", essence: 500, fragments: 30, cores: 6, maxSkills: 3 },
  { id: 4, name: "Supremo", essence: 1200, fragments: 60, cores: 12, maxSkills: 3 },
  { id: 5, name: "Sagrado", essence: 2500, fragments: 120, cores: 25, maxSkills: 3 },
  { id: 6, name: "Divino", essence: 5000, fragments: 250, cores: 50, maxSkills: 3 },
];

// Dynamic property keys
const PROP_STAGE = "shadow_slave:stage";
const PROP_ESSENCE = "shadow_slave:essence";
const PROP_FRAGMENTS = "shadow_slave:fragments";
const PROP_CORES = "shadow_slave:cores"; // legacy int counter (deprecated, kept for migration)
const PROP_ASPECT = "shadow_slave:aspect";
const PROP_SKILLS = "shadow_slave:skills";
const PROP_COOLDOWNS = "shadow_slave:cooldowns";
const PROP_DOMINATED = "shadow_slave:dominated"; // entity id -> owner player name
const PROP_MEMORIES = "shadow_slave:memories"; // array of memory IDs
const PROP_EQUIPPED_MEMORY = "shadow_slave:equipped_memory"; // currently equipped memory ID
const PROP_ECHOES = "shadow_slave:echoes"; // array of echo IDs

// New Soul Shards & Core Data properties (Fase 8B.1)
const PROP_SOUL_SHARDS = "shadow_slave:soul_shards"; // int: current soul shards
const PROP_CORE_DATA = "shadow_slave:core_data"; // stringified JSON: core data structure

// Aspect configuration
const ASPECTS = {
  shadow: {
    id: "shadow",
    name: "Aspecto das Sombras",
    description: "Domínio sobre a escuridão e as sombras vivas",
    requiredStage: 1,
    skills: ["perception", "shadowstrike", "shadowmantle"]
  }
};

// Skills configuration
const SKILLS = {
  perception: {
    id: "perception",
    name: "Percepção das Sombras",
    description: "Detecta criaturas vivas e jogadores próximos através das sombras",
    aspect: "shadow",
    requiredStage: 1,
    essenceCost: 5,
    cooldown: 30, // seconds
    range: 20,
    execute: (player) => executePerception(player)
  },
  shadowstrike: {
    id: "shadowstrike",
    name: "Ataque Sombrio",
    description: "Golpe das sombras que atravessa as defesas do alvo",
    aspect: "shadow",
    requiredStage: 2,
    essenceCost: 15,
    cooldown: 20,
    range: 8,
    damage: 8,
    execute: (player) => executeShadowStrike(player)
  },
  shadowmantle: {
    id: "shadowmantle",
    name: "Manto Sombrio",
    description: "Envolve-se em sombras protetoras, reduzindo dano recebido",
    aspect: "shadow",
    requiredStage: 3,
    essenceCost: 25,
    cooldown: 60,
    duration: 15, // seconds
    damageReduction: 0.5, // 50% reduction
    execute: (player) => executeShadowMantle(player)
  }
};

// Helper: Get player data with defaults
function getPlayerData(player) {
  return {
    stage: player.getDynamicProperty(PROP_STAGE) || 0,
    essence: player.getDynamicProperty(PROP_ESSENCE) || 0,
    fragments: player.getDynamicProperty(PROP_FRAGMENTS) || 0,
    cores: player.getDynamicProperty(PROP_CORES) || 0,
    aspect: player.getDynamicProperty(PROP_ASPECT) || "none",
    skills: player.getDynamicProperty(PROP_SKILLS) || [],
    cooldowns: player.getDynamicProperty(PROP_COOLDOWNS) || {}
  };
}

// Helper: Check if player has admin permission
function isAdmin(player) {
  // In Bedrock, we check for operator permissions via tags
  return player.hasTag("op") || player.hasTag("admin") || player.hasTag("shadow_slave_admin");
}

// Helper: Format time
function formatCooldown(seconds) {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

// Helper: Check and update cooldown
function checkCooldown(player, skillId) {
  const cooldowns = player.getDynamicProperty(PROP_COOLDOWNS) || {};
  const lastUsed = cooldowns[skillId] || 0;
  const now = Date.now();
  const skill = SKILLS[skillId];
  const cooldownMs = skill.cooldown * 1000;
  
  if (now - lastUsed < cooldownMs) {
    const remaining = Math.ceil((cooldownMs - (now - lastUsed)) / 1000);
    return { ready: false, remaining };
  }
  return { ready: true, remaining: 0 };
}

function setCooldown(player, skillId) {
  const cooldowns = player.getDynamicProperty(PROP_COOLDOWNS) || {};
  cooldowns[skillId] = Date.now();
  player.setDynamicProperty(PROP_COOLDOWNS, cooldowns);
}

function consumeEssence(player, amount) {
  const current = player.getDynamicProperty(PROP_ESSENCE) || 0;
  if (current < amount) return false;
  player.setDynamicProperty(PROP_ESSENCE, current - amount);
  return true;
}

// ============================================================
// SOUL SHARDS & CORE DATA INFRASTRUCTURE (Fase 8B.1)
// ============================================================

// Core data structure constants
const CORE_BASE_CAPACITY = 1000; // Soul Shards needed to saturate a core (PROVISÓRIO)
const MAX_NORMAL_CORES = 1;
const MAX_DIVINE_CORES = 7;

// Soul Shards cost per rank up (PROVISÓRIO - ajustar conforme novel)
const RANK_UP_SHARD_COST = {
  1: 500,   // Mundano -> Awakened
  2: 1000,  // Awakened -> Ascended
  3: 2500,  // Ascended -> Transcendent
  4: 5000,  // Transcendent -> Supreme
  5: 10000, // Supreme -> Sacred
  6: 20000, // Sacred -> Divine
};

// Default core structure
function createEmptyCore(rank = 0) {
  return {
    rank: rank, // 0 = empty/unsaturated, 1+ = rank of core
    saturation: 0, // current soul shards in this core
    maxSaturation: CORE_BASE_CAPACITY, // shards needed to saturate
    shardCapacity: CORE_BASE_CAPACITY, // alias for clarity
  };
}

function createDefaultCoreData() {
  return {
    cores: [createEmptyCore(0)], // Start with one empty core
    maxCores: MAX_NORMAL_CORES,
    totalShards: 0, // total shards ever earned (historical)
    version: 1, // data version for future migrations
  };
}

// --- Soul Shards Functions ---

function getSoulShards(player) {
  const shards = player.getDynamicProperty(PROP_SOUL_SHARDS);
  return typeof shards === "number" && shards >= 0 ? shards : 0;
}

function addSoulShards(player, amount, source = "unknown") {
  if (typeof amount !== "number" || amount <= 0 || !Number.isFinite(amount)) {
    return false;
  }
  const current = getSoulShards(player);
  const newTotal = current + Math.floor(amount);
  player.setDynamicProperty(PROP_SOUL_SHARDS, newTotal);
  // Track historical total (optional, could use separate property)
  return true;
}

function consumeSoulShards(player, amount) {
  if (typeof amount !== "number" || amount <= 0 || !Number.isFinite(amount)) {
    return false;
  }
  const current = getSoulShards(player);
  if (current < amount) {
    return false;
  }
  player.setDynamicProperty(PROP_SOUL_SHARDS, current - Math.floor(amount));
  return true;
}

function getSoulShardsSafe(player) {
  // Alias for compatibility
  return getSoulShards(player);
}

// --- Core Data Functions ---

function getCoreData(player) {
  const raw = player.getDynamicProperty(PROP_CORE_DATA);
  if (!raw) {
    return null;
  }
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      // Validate structure
      if (parsed && typeof parsed === "object" && Array.isArray(parsed.cores)) {
        return parsed;
      }
    } catch (e) {
      console.warn("Failed to parse core data:", e);
    }
  }
  return null;
}

function setCoreData(player, data) {
  if (!data || typeof data !== "object" || !Array.isArray(data.cores)) {
    return false;
  }
  try {
    const json = JSON.stringify(data);
    player.setDynamicProperty(PROP_CORE_DATA, json);
    return true;
  } catch (e) {
    console.warn("Failed to stringify core data:", e);
    return false;
  }
}

function getCoreDataOrDefault(player) {
  const data = getCoreData(player);
  if (data) {
    return data;
  }
  // Return default structure if none exists
  return createDefaultCoreData();
}

function getMaxCoresForPlayer(player) {
  const aspect = player.getDynamicProperty(PROP_ASPECT) || "none";
  const isDivine = aspect === "shadow" && getPlayerStage(player) >= 6; // Divine rank
  // Could also check for Divine Aspect specifically
  return isDivine ? MAX_DIVINE_CORES : MAX_NORMAL_CORES;
}

function getPlayerStage(player) {
  return player.getDynamicProperty(PROP_STAGE) || 0;
}

// ============================================================
// CORE SATURATION & RANK-UP SYSTEM (FASE 8B.2)
// ============================================================

// Attempt to saturate player's cores with available Soul Shards
// Returns { success: boolean, saturatedCores: number, shardsUsed: number, message: string }
function attemptCoreSaturation(player) {
  const coreData = getCoreDataOrDefault(player);
  const shards = getSoulShards(player);
  const maxCores = getMaxCoresForPlayer(player);
  
  // Check if player has any cores
  if (!coreData.cores || coreData.cores.length === 0) {
    return { success: false, reason: "no_cores", message: "§7[ShadowSlave] §cVocê não possui núcleos para saturar." };
  }
  
  // Check if player has any Soul Shards
  const shards = getSoulShards(player);
  if (shards <= 0) {
    return { success: false, reason: "no_shards", message: "§7[ShadowSlave] §cVocê não possui Soul Shards para saturar seus núcleos." };
  }
  
  let shardsUsed = 0;
  let saturatedCores = 0;
  const cores = coreData.cores;
  
  // Try to saturate each core in order
  for (let i = 0; i < coreData.cores.length; i++) {
    const core = coreData.cores[i];
    
    // Skip already saturated cores (rank > 0)
    if (core.rank > 0) continue;
    
    // Calculate shards needed to saturate this core
    const shardsNeeded = core.maxSaturation - core.saturation;
    
    if (shards <= 0) break;
    
    if (shards >= shardsNeeded) {
      // Can fully saturate this core
      shards -= shardsNeeded;
      core.saturation = core.maxSaturation;
      core.rank = coreData.cores.indexOf(core) + 1; // Rank = position + 1
      shardsUsed += shardsNeeded;
      saturatedCores++;
    } else {
      // Partially saturate
      core.saturation += shards;
      shardsUsed += shards;
      shards = 0;
      break;
    }
  }
  
  // Update core data
  coreData.totalShards += shardsUsed;
  setCoreData(player, coreData);
  
  // Consume the used shards from player's inventory
  consumeSoulShards(player, shardsUsed);
  
  if (saturatedCores > 0) {
    return { 
      success: true, 
      saturatedCores: 1, // Only one core per saturation attempt for balance
      shardsUsed: shardsUsed,
      message: `§7[ShadowSlave] §aNúcleo saturado! §7Shards usados: §b${shardsUsed}`
    };
  } else if (shardsUsed > 0) {
    return { 
      success: true, 
      saturatedCores: 0, 
      shardsUsed: shardsUsed,
      message: `§7[ShadowSlave] §eProgresso de saturação: §b${shardsUsed}§7 shards aplicados.`
    };
  } else {
    return { 
      success: false, 
      reason: "insufficient_shards", 
      message: "§7[ShadowSlave] §cShards insuficientes para saturar qualquer núcleo." 
    };
  }
}

function attemptRankUp(player) {
  const coreData = getCoreDataOrDefault(player);
  const stage = getPlayerStage(player);
  const maxCores = getMaxCoresForPlayer(player);
  
  // Find first saturated core (rank > 0 but not yet ranked up)
  const coreIndex = coreData.cores.findIndex(core => core.saturation >= core.maxSaturation && core.rank === 0);
  
  if (coreIndex === -1) {
    return { success: false, reason: "no_saturated_core", message: "§7[ShadowSlave] §cNenhum núcleo saturado pronto para evolução." };
  }
  
  const core = coreData.cores[coreIndex];
  
  // Check if player has enough resources for rank up
  const nextRank = core.rank + 1;
  const shardCost = RANK_UP_SHARD_COST[core.rank] || 1000; // Default cost if not defined
  
  const shards = getSoulShards(player);
  if (shards < shardCost) {
    return { 
      success: false, 
      reason: "insufficient_shards", 
      message: `§7[ShadowSlave] §cShards insuficientes para rank-up. Necessário: §b${shardCost}§c, você tem: §b${getSoulShards(player)}` 
    };
  }
  
  // Consume shards for rank up
  if (!consumeSoulShards(player, shardCost)) {
    return { success: false, reason: "consume_failed", message: "§7[ShadowSlave] §cFalha ao consumir shards para rank-up." };
  }
  
  // Perform rank up
  const coreData = getCoreDataOrDefault(player);
  const coreIndex = coreData.cores.findIndex(c => c.saturation >= c.maxSaturation && c.rank === 0);
  const core = coreData.cores[coreIndex];
  
  core.rank += 1;
  core.rankName = getCoreRankName(core.rank);
  
  // Reset saturation for next rank (optional - could keep some progress)
  core.saturation = 0;
  
  setCoreData(player, coreData);
  
  // Check if player should rank up overall
  checkPlayerRankUp(player);
  
  return { 
    success: true, 
    newRank: core.rank, 
    message: `§7[ShadowSlave] §a§lNÚCLEO EVOLUÍDO!§r §7Núcleo agora é rank §e${core.rank}§7 (§e${getCoreRankName(core.rank)}§7).` 
  };
}

// Get core rank name
function getCoreRankName(rank) {
  const names = ["Vazio", "Despertar", "Ascensão", "Transcendência", "Supremacia", "Santidade", "Divindade"];
  return names[rank] || `Rank ${rank}`;
}

// Check if player should rank up overall
function checkPlayerRankUp(player) {
  const data = getPlayerData(player);
  const nextStage = data.stage + 1;
  
  if (nextStage >= STAGES.length) return; // Max stage reached
  
  const next = STAGES[data.stage + 1];
  const data = getPlayerData(player);
  
  if (data.essence >= next.essence && data.fragments >= next.fragments && data.cores >= next.cores) {
    // Auto-evolve if requirements met
    tryEvolve(player);
  }
}

// ============================================================
// UPDATED PROGRESSION SYSTEM (SATURATION-BASED)
// ============================================================

// Updated tryEvolve - now checks core saturation instead of just resources
function tryEvolve(player) {
  const data = getPlayerData(player);
  const nextStage = data.stage + 1;
  
  if (nextStage >= STAGES.length) {
    player.sendMessage("§7[ShadowSlave] §cVocê já atingiu o estágio máximo: §eDivino");
    return;
  }
  
  const next = STAGES[nextStage];
  
  // Check if player has at least one saturated core (requirement for evolution)
  const coreData = getCoreDataOrDefault(player);
  const hasSaturatedCore = coreData.cores.some(core => core.saturation >= core.maxSaturation && core.rank > 0);
  
  if (!hasSaturatedCore) {
    player.sendMessage("§7[ShadowSlave] §cVocê precisa de pelo menos um núcleo saturado e evoluído para evoluir!");
    player.sendMessage("§7[ShadowSlave] §eUse §e!saturate §epara saturar seus núcleos primeiro.");
    return;
  }
  
  // Check resources
  const next = STAGES[data.stage + 1];
  
  if (data.essence < next.essence || data.fragments < next.fragments || data.cores < next.cores) {
    player.sendMessage("§7[ShadowSlave] §cRecursos insuficientes para evoluir!");
    player.sendMessage(`§7Necessário: §b${next.essence}§7 Essência, §6${next.fragments}§7 Fragmentos, §5${next.cores}§7 Núcleos`);
    player.sendMessage(`§7Atual: §b${data.essence}§7/§6${data.fragments}§7/§5${data.cores}`);
    return;
  }
  
  // Consume resources
  player.setDynamicProperty(PROP_ESSENCE, data.essence - next.essence);
  player.setDynamicProperty(PROP_FRAGMENTS, data.fragments - next.fragments);
  player.setDynamicProperty(PROP_CORES, data.cores - next.cores);
  player.setDynamicProperty(PROP_STAGE, nextStage);
  
  // Auto-unlock aspect at stage 1
  if (nextStage === 1 && data.aspect === "none") {
    player.setDynamicProperty(PROP_ASPECT, "shadow");
    player.setDynamicProperty(PROP_SKILLS, ["perception"]);
    player.sendMessage("§7[ShadowSlave] §a§lAspecto das Sombras despertou! §fHabilidade desbloqueada: §ePercepção das Sombras");
  }
  
  // Auto-unlock skills at appropriate stages
  const aspect = ASPECTS.shadow;
  for (const skillId of aspect.skills) {
    const skill = SKILLS[skillId];
    if (nextStage >= skill.requiredStage && !data.skills.includes(skillId)) {
      const newSkills = [...data.skills, skillId];
      player.setDynamicProperty(PROP_SKILLS, newSkills);
      player.sendMessage(`§7[ShadowSlave] §aNova habilidade desbloqueada: §e${skill.name}!`);
    }
  }
  
  applyStageBenefits(player, nextStage);
  
  player.sendMessage(`§7[ShadowSlave] §a§lEVOLUÇÃO CONCLUÍDA!§r`);
  player.sendMessage(`§7Novo estágio: §e${next.name}`);
  player.sendMessage(`§7Recursos restantes: §b${data.essence - next.essence}§7/§6${data.fragments - next.fragments}§7/§5${data.cores - next.cores}`);
}

const MIGRATION_VERSION = 1; // Core data version

// Constants for legacy core preservation and migration state tracking
const LEGACY_CORES_PROP = "shadow_slave:legacy_cores_backup"; // backup of original PROP_CORES
const MIGRATION_STATUS_PROP = "shadow_slave:migration_status"; // tracks migration state: "in_progress", "completed_v1", "failed", "recovery_needed"
const MIGRATION_STEP_PROP = "shadow_slave:migration_step"; // tracks which step completed: "backup_done", "core_data_written", "shards_init"

function migrateCoreDataOnJoin(player) {
  try {
    // Check migration status first (idempotency)
    const migrationStatus = player.getDynamicProperty(MIGRATION_STATUS_PROP);
    const migrationStep = player.getDynamicProperty(MIGRATION_STEP_PROP);
    
    // Already fully migrated - just ensure maxCores is current
    if (migrationStatus === "completed_v1") {
      const existingCoreData = getCoreData(player);
      if (existingCoreData && existingCoreData.version === 1) {
        const coreData = getCoreDataOrDefault(player);
        const maxCores = getMaxCoresForPlayer(player);
        if (coreData.maxCores !== getMaxCoresForPlayer(player)) {
          coreData.maxCores = getMaxCoresForPlayer(player);
          setCoreData(player, coreData);
        }
      }
      return { migrated: false, reason: "already_migrated" };
    }

    // Check if migration was previously in progress (recovery scenario)
    const migrationStatus = player.getDynamicProperty(MIGRATION_STATUS_PROP);
    const migrationStep = player.getDynamicProperty(MIGRATION_STEP_PROP);
    
    if (migrationStatus === "in_progress" || migrationStatus === "failed" || migrationStatus === "recovery_needed") {
      // Migration was interrupted - attempt recovery
      console.log(`[ShadowSlave] Migration recovery for ${player.name}: status=${migrationStatus}, step=${migrationStep}`);
      return recoverMigration(player);
    }

    // Check if already fully migrated (idempotency)
    const existingCoreData = getCoreData(player);
    if (existingCoreData && existingCoreData.version === 1) {
      // Already fully migrated - just ensure maxCores is current
      const coreData = getCoreDataOrDefault(player);
      const maxCores = getMaxCoresForPlayer(player);
      if (coreData.maxCores !== getMaxCoresForPlayer(player)) {
        coreData.maxCores = getMaxCoresForPlayer(player);
        setCoreData(player, coreData);
      }
      // Ensure status is marked
      if (player.getDynamicProperty(MIGRATION_STATUS_PROP) !== "completed_v1") {
        player.setDynamicProperty(MIGRATION_STATUS_PROP, "completed_v1");
        player.setDynamicProperty(MIGRATION_STEP_PROP, "completed");
      }
      return { migrated: false, reason: "already_migrated" };
    }

    // Start fresh migration
    return performMigration(player);
  } catch (e) {
    console.error(`[ShadowSlave] Migration error for ${player.name}:`, e);
    player.setDynamicProperty(MIGRATION_STATUS_PROP, "failed");
    return { migrated: false, reason: "exception", error: String(e) };
  }
}

function performMigration(player) {
  // Mark migration as in progress
  player.setDynamicProperty(MIGRATION_STATUS_PROP, "in_progress");
  player.setDynamicProperty(MIGRATION_STEP_PROP, "started");

  try {
    // Step 1: Read and backup legacy cores FIRST (before any modification)
    const legacyCoresRaw = player.getDynamicProperty(PROP_CORES);
    const legacyCores = (typeof legacyCoresRaw === "number" && legacyCoresRaw >= 0) ? Math.floor(legacyCoresRaw) : 0;
    
    // Backup original PROP_CORES to recovery property (preserves original value)
    if (player.getDynamicProperty(LEGACY_CORES_PROP) === undefined) {
      const legacyCoresRaw = player.getDynamicProperty(PROP_CORES);
      const legacyCores = (typeof legacyCoresRaw === "number" && legacyCoresRaw >= 0) ? Math.floor(legacyCoresRaw) : 0;
      player.setDynamicProperty(LEGACY_CORES_PROP, legacyCores);
      console.log(`[ShadowSlave] Migration: Backed up legacy cores=${legacyCores} for ${player.name}`);
    }
    player.setDynamicProperty(MIGRATION_STEP_PROP, "backup_done");

    // Step 2: Check existing core data (might have valid migration already)
    const rawCoreData = player.getDynamicProperty(PROP_CORE_DATA);
    let existingCoreData = null;
    let jsonParseError = null;
    const rawCoreData = player.getDynamicProperty(PROP_CORE_DATA);
    
    if (rawCoreData !== undefined && rawCoreData !== null) {
      if (typeof rawCoreData === "string") {
        try {
          const parsed = JSON.parse(rawCoreData);
          if (parsed && typeof parsed === "object" && Array.isArray(parsed.cores)) {
            // Valid existing core data - check version
            if (parsed.version === 1) {
              // Already migrated, just ensure maxCores is current
              const maxCores = getMaxCoresForPlayer(player);
              if (parsed.maxCores !== getMaxCoresForPlayer(player)) {
                parsed.maxCores = getMaxCoresForPlayer(player);
                setCoreData(player, parsed);
              }
              // Mark migration complete
              player.setDynamicProperty(MIGRATION_STATUS_PROP, "completed_v1");
              player.setDynamicProperty(MIGRATION_STEP_PROP, "completed");
              return { migrated: false, reason: "already_migrated_valid" };
            } else {
              // Different version - treat as invalid for migration purposes
              console.warn(`[ShadowSlave] Migration: Player ${player.name} has core data version ${parsed.version}, expected 1`);
            }
          } else {
            console.warn(`[ShadowSlave] Migration: Player ${player.name} has invalid core data structure`);
          }
        } catch (e) {
          // JSON parse error - preserve corrupted data for recovery
          console.error(`[ShadowSlave] Migration: Failed to parse core data for ${player.name}:`, e);
          if (player.getDynamicProperty("shadow_slave:core_data_corrupted") === undefined) {
            player.setDynamicProperty("shadow_slave:core_data_corrupted", rawCoreData);
          }
          // Mark as recovery needed but don't overwrite corrupted data
          player.setDynamicProperty(MIGRATION_STATUS_PROP, "recovery_needed");
          player.setDynamicProperty(MIGRATION_STEP_PROP, "corrupted_json");
          return { migrated: false, reason: "corrupted_json_preserved" };
        }
      } else if (rawCoreData !== undefined && rawCoreData !== null) {
        console.warn(`[ShadowSlave] Migration: Player ${player.name} has non-string core data: ${typeof rawCoreData}`);
      }
      player.setDynamicProperty(MIGRATION_STEP_PROP, "json_validated");

      // Step 2: Read legacy cores (for migration from v1.0.8 and earlier)
      const legacyCoresRaw = player.getDynamicProperty(PROP_CORES);
      const legacyCores = (typeof legacyCoresRaw === "number" && legacyCoresRaw >= 0) ? Math.floor(legacyCoresRaw) : 0;
      
      // Backup original PROP_CORES if not already backed up
      if (player.getDynamicProperty(LEGACY_CORES_PROP) === undefined) {
        const legacyCoresRaw = player.getDynamicProperty(PROP_CORES);
        const legacyCores = (typeof legacyCoresRaw === "number" && legacyCoresRaw >= 0) ? Math.floor(legacyCoresRaw) : 0;
        player.setDynamicProperty(LEGACY_CORES_PROP, legacyCores);
      }
      player.setDynamicProperty(MIGRATION_STEP_PROP, "backup_done");

      // Step 3: Determine max cores based on current aspect/rank
      const stage = player.getDynamicProperty(PROP_STAGE) || 0;
      const aspect = player.getDynamicProperty(PROP_ASPECT) || "none";
      const isDivine = hasDivineAspect(player);
      const maxCores = isDivine ? MAX_DIVINE_CORES : MAX_NORMAL_CORES;
      
      // Calculate cores to create (clamped to max allowed)
      const clampedCores = Math.min(Math.max(0, legacyCores), maxCores);
      const excessCores = Math.max(0, legacyCores - maxCores);
      
      // Create core array with clamped count
      const cores = [];
      for (let i = 0; i < clampedCores; i++) {
        cores.push(createEmptyCore(0)); // rank 0 = unsaturated
      }
      
      // Log excess but preserve in backup
      const excessCores = Math.max(0, legacyCores - maxCores);
      if (excessCores > 0) {
        console.warn(`[ShadowSlave] Migration: Player ${player.name} had ${legacyCores} legacy cores, clamped to ${maxCores} active. Excess ${excessCores} preserved in ${LEGACY_CORES_PROP}.`);
      }
      
      player.setDynamicProperty(MIGRATION_STEP_PROP, "cores_calculated");

      // Step 4: Create new core data structure
      let coresArray;
      if (legacyCores === 0) {
        // New player - start with one empty core
        coresArray = [createEmptyCore(0)];
      } else {
        // Migrated player - create clamped number of empty cores
        coresArray = Array.from({ length: clampedCores }, () => createEmptyCore(0));
      }
      
      // Create new core data structure
      const newCoreData = {
        cores: coresArray,
        maxCores: getMaxCoresForPlayer(player),
        totalShards: 0,
        version: 1,
        migrationNote: `Migrated from legacy cores=${legacyCores}, stage=${player.getDynamicProperty(PROP_STAGE)||0}, aspect=${player.getDynamicProperty(PROP_ASPECT)||"none"}`,
        legacyBackup: legacyCores,
        excessCores: Math.max(0, legacyCores - getMaxCoresForPlayer(player)),
        migrationTimestamp: Date.now(),
      };
      
      player.setDynamicProperty(MIGRATION_STEP_PROP, "core_data_prepared");

      // Step 5: Write core data
      if (!setCoreData(player, newCoreData)) {
        player.setDynamicProperty(MIGRATION_STATUS_PROP, "failed");
        player.setDynamicProperty(MIGRATION_STEP_PROP, "core_data_write_failed");
        return { migrated: false, reason: "core_data_write_failed" };
      }
      player.setDynamicProperty(MIGRATION_STEP_PROP, "core_data_written");

      // Step 6: Initialize soul shards if not present
      if (player.getDynamicProperty(PROP_SOUL_SHARDS) === undefined) {
        player.setDynamicProperty(PROP_SOUL_SHARDS, 0);
      }
      player.setDynamicProperty(MIGRATION_STEP_PROP, "shards_init");

      // Step 7: Mark migration as completed (only after all steps succeed)
      player.setDynamicProperty(MIGRATION_STATUS_PROP, "completed_v1");
      player.setDynamicProperty(MIGRATION_STEP_PROP, "completed");
      
      const maxCores = getMaxCoresForPlayer(player);
      const clampedCores = Math.min(Math.max(0, 
        (typeof player.getDynamicProperty(PROP_CORES) === "number" && player.getDynamicProperty(PROP_CORES) >= 0) 
          ? Math.floor(player.getDynamicProperty(PROP_CORES)) : 0
      ), getMaxCoresForPlayer(player));
      
      console.log(`[ShadowSlave] Migration successful for ${player.name}: legacy cores migrated, active cores created, max=${getMaxCoresForPlayer(player)}`);
      
      return { 
        migrated: true, 
        legacyCores: player.getDynamicProperty(LEGACY_CORES_PROP) || 0,
        activeCores: Math.min(
          (typeof player.getDynamicProperty(PROP_CORES) === "number" && player.getDynamicProperty(PROP_CORES) >= 0) 
            ? Math.floor(player.getDynamicProperty(PROP_CORES)) : 0,
          getMaxCoresForPlayer(player)
        ),
        maxCores: getMaxCoresForPlayer(player),
        excessPreserved: true,
      };
  } catch (e) {
    // On ANY error, mark as failed but don't lose data
    player.setDynamicProperty(MIGRATION_STATUS_PROP, "failed");
    player.setDynamicProperty(MIGRATION_STEP_PROP, "exception");
    console.error(`[ShadowSlave] Migration error for ${player.name}:`, e);
    return { migrated: false, reason: "exception", error: String(e) };
  }
}

// Recovery function for interrupted migrations
function recoverMigration(player) {
  const migrationStep = player.getDynamicProperty(MIGRATION_STEP_PROP);
  const migrationStatus = player.getDynamicProperty(MIGRATION_STATUS_PROP);
  
  console.log(`[ShadowSlave] Attempting recovery for ${player.name}: status=${migrationStatus}, step=${migrationStep}`);
  
  // Determine recovery action based on step
  switch (migrationStep) {
    case "started":
    case "backup_done":
    case "json_validated":
    case "backup_done":
    case "cores_calculated":
    case "core_data_prepared":
      // These steps are idempotent - safe to restart from performMigration
      console.log(`[ShadowSlave] Recovery: restarting migration from step ${migrationStep} for ${player.name}`);
      return performMigration(player);
      
    case "core_data_prepared":
    case "core_data_written":
      // Core data might be written - check if valid
      const coreData = getCoreData(player);
      if (coreData && coreData.version === 1 && Array.isArray(coreData.cores)) {
        // Core data exists and is valid - just need to complete remaining steps
        console.log(`[ShadowSlave] Recovery: core_data exists, completing remaining steps for ${player.name}`);
        
        // Ensure soul shards initialized
        if (player.getDynamicProperty(PROP_SOUL_SHARDS) === undefined) {
          player.setDynamicProperty(PROP_SOUL_SHARDS, 0);
        }
        
        // Mark as completed
        player.setDynamicProperty(MIGRATION_STATUS_PROP, "completed_v1");
        player.setDynamicProperty(MIGRATION_STEP_PROP, "completed");
        
        return { migrated: true, reason: "recovery_completed_core_data_exists" };
      } else {
        // Core data missing or invalid - restart migration
        console.log(`[ShadowSlave] Recovery: core_data missing/invalid, restarting migration`);
        return performMigration(player);
      }
      
    case "shards_init":
      // Core data written, just need to init shards and mark complete
      if (player.getDynamicProperty(PROP_SOUL_SHARDS) === undefined) {
        player.setDynamicProperty(PROP_SOUL_SHARDS, 0);
      }
      player.setDynamicProperty(MIGRATION_STATUS_PROP, "completed_v1");
      player.setDynamicProperty(MIGRATION_STEP_PROP, "completed");
      return { migrated: true, reason: "recovery_completed_shards_init" };
      
    case "completed":
      return { migrated: false, reason: "already_migrated" };
      
    case "corrupted_json":
      // JSON was corrupted - we preserved it, now try migration from legacy
      console.log(`[ShadowSlave] Recovery: corrupted JSON detected, attempting migration from legacy`);
      return performMigration(player);
      
    case "core_data_write_failed":
    case "core_data_write_failed":
    case "shards_init":
    case "exception":
    case "failed":
    case "recovery_needed":
      // These are failure states - attempt full migration restart
      console.log(`[ShadowSlave] Recovery: attempting fresh migration from failure state`);
      return performMigration(player);
      
    default:
      // Unknown step - safest to restart migration
      console.warn(`[ShadowSlave] Recovery: unknown step ${migrationStep}, restarting migration`);
      return performMigration(player);
  }
}

// Helper to check if player has Divine Aspect (for core limit)
  const aspect = player.getDynamicProperty(PROP_ASPECT) || "none";
  const stage = player.getDynamicProperty(PROP_STAGE) || 0;
  // Divine Aspect is Shadow Aspect at Divine rank (stage 6) - PROVISÓRIO
  return aspect === "shadow" && stage >= 6;
}

// ============================================================
// SOUL SHARDS & CORE DATA FUNCTIONS (PUBLIC API)
// ============================================================

function getSoulShards(player) {
  const shards = player.getDynamicProperty(PROP_SOUL_SHARDS);
  return typeof shards === "number" && shards >= 0 ? shards : 0;
}

function addSoulShards(player, amount, source = "unknown") {
  if (typeof amount !== "number" || amount <= 0 || !Number.isFinite(amount)) {
    return { success: false, reason: "invalid_amount" };
  }
  const current = getSoulShards(player);
  const newTotal = current + Math.floor(amount);
  player.setDynamicProperty(PROP_SOUL_SHARDS, newTotal);
  // Log for audit
  console.log(`[ShadowSlave] Soul Shards: ${player.name} +${Math.floor(amount)} (${source}) -> ${newTotal}`);
  return { success: true, newTotal: newTotal, source: source };
}

function consumeSoulShards(player, amount) {
  if (typeof amount !== "number" || amount <= 0 || !Number.isFinite(amount)) {
    return { success: false, reason: "invalid_amount" };
  }
  const current = getSoulShards(player);
  if (current < amount) {
    return { success: false, reason: "insufficient_shards", current: current };
  }
  player.setDynamicProperty(PROP_SOUL_SHARDS, current - Math.floor(amount));
  return { success: true, newTotal: current - Math.floor(amount) };
}

function getSoulShardsSafe(player) {
  return getSoulShards(player);
}

function getCoreData(player) {
  const raw = player.getDynamicProperty(PROP_CORE_DATA);
  if (!raw) {
    return null;
  }
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && Array.isArray(parsed.cores)) {
        return parsed;
      }
    } catch (e) {
      console.warn("Failed to parse core data:", e);
    }
  }
  return null;
}

function setCoreData(player, data) {
  if (!data || typeof data !== "object" || !Array.isArray(data.cores)) {
    return false;
  }
  try {
    const json = JSON.stringify(data);
    player.setDynamicProperty(PROP_CORE_DATA, json);
    return true;
  } catch (e) {
    console.warn("Failed to stringify core data:", e);
    return false;
  }
}

function getCoreDataOrDefault(player) {
  const data = getCoreData(player);
  if (data) {
    return data;
  }
  return createDefaultCoreData();
}

function getMaxCoresForPlayer(player) {
  const aspect = player.getDynamicProperty(PROP_ASPECT) || "none";
  const stage = player.getDynamicProperty(PROP_STAGE) || 0;
  const isDivine = aspect === "shadow" && stage >= 6;
  return isDivine ? MAX_DIVINE_CORES : MAX_NORMAL_CORES;
}

function getPlayerStage(player) {
  return player.getDynamicProperty(PROP_STAGE) || 0;
}

function hasDivineAspect(player) {
  const aspect = player.getDynamicProperty(PROP_ASPECT) || "none";
  const stage = player.getDynamicProperty(PROP_STAGE) || 0;
  return aspect === "shadow" && stage >= 6;
}

// ============================================================
// SKILL IMPLEMENTATIONS
// ============================================================

function executePerception(player) {
  // Read base range from CONFIG
  let range = CONFIG.skills.perception.range;
  
  // Apply Memory effect: memory_void_walker perception range bonus
  const equipped = player.getDynamicProperty(PROP_EQUIPPED_MEMORY) || "none";
  if (equipped === "memory_void_walker") {
    const bonus = CONFIG.memories.memory_void_walker.perceptionRangeBonus || 0;
    range += bonus;
  }
  
  const dimension = player.dimension;
  const players = dimension.getPlayers({ excludeNames: [player.name] });
  const entities = dimension.getEntities({ 
    location: player.location, 
    maxDistance: range,
    excludeTypes: ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow"]
  });
  
  let found = [];
  
  // Nearby players
  for (const p of players) {
    const dist = Math.sqrt(
      Math.pow(p.location.x - player.location.x, 2) +
      Math.pow(p.location.y - player.location.y, 2) +
      Math.pow(p.location.z - player.location.z, 2)
    );
    if (dist <= range) {
      found.push(`§eJogador: ${p.name} §7(${dist.toFixed(1)} blocos)`);
    }
  }
  
  // Nearby entities (hostile mobs)
  for (const e of entities) {
    if (e.typeId === "minecraft:player") continue;
    const dist = Math.sqrt(
      Math.pow(e.location.x - player.location.x, 2) +
      Math.pow(e.location.y - player.location.y, 2) +
      Math.pow(e.location.z - player.location.z, 2)
    );
    if (dist <= range) {
      const typeName = e.typeId.replace("minecraft:", "").replace("_", " ");
      found.push(`§c${typeName} §7(${dist.toFixed(1)} blocos)`);
    }
  }
  
  if (found.length === 0) {
    player.sendMessage("§7[ShadowSlave] §fAs sombras não detectam nada próximo...");
  } else {
    const rangeInfo = equipped === "memory_void_walker" ? ` §8(alcance +${CONFIG.memories.memory_void_walker.perceptionRangeBonus || 0})` : "";
    player.sendMessage(`§7[ShadowSlave] §bPercepção das Sombras ativada:${rangeInfo}`);
    for (const f of found.slice(0, 10)) {
      player.sendMessage(`  ${f}`);
    }
    if (found.length > 10) {
      player.sendMessage(`  §7...e mais ${found.length - 10} entidades`);
    }
  }
  return true;
}

function executeShadowStrike(player) {
  // Read base values from CONFIG
  let range = CONFIG.skills.shadowstrike.range;
  let damage = CONFIG.skills.shadowstrike.damage;
  
  // Apply Memory effects
  const equipped = player.getDynamicProperty(PROP_EQUIPPED_MEMORY) || "none";
  let echoSummoned = false;
  
  if (equipped === "memory_shadow_blade") {
    const bonus = CONFIG.memories.memory_shadow_blade.shadowstrikeDamageBonus || 0;
    damage += bonus;
  }
  if (equipped === "memory_void_walker") {
    const bonus = CONFIG.memories.memory_void_walker.shadowstrikeRangeBonus || 0;
    range += bonus;
  }
  if (equipped === "memory_echo_caller") {
    const chance = CONFIG.memories.memory_echo_caller.echoSummonChance || 0;
    if (Math.random() < chance) {
      echoSummoned = true;
    }
  }
  
  const dimension = player.dimension;
  
  // Find nearest valid target in front of player
  const entities = dimension.getEntities({
    location: player.location,
    maxDistance: range,
    excludeTypes: ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:player"]
  });
  
  let target = null;
  let minDist = range + 1;
  
  for (const e of entities) {
    // Check if entity is in front of player (within 90 degree cone)
    const toEntity = {
      x: e.location.x - player.location.x,
      y: e.location.y - player.location.y,
      z: e.location.z - player.location.z
    };
    const dist = Math.sqrt(toEntity.x**2 + toEntity.y**2 + toEntity.z**2);
    
    if (dist < minDist) {
      // Simple facing check: dot product with player view direction
      const yaw = player.getViewDirection().y;
      // Simplified: just take nearest for now
      if (dist < minDist) {
        minDist = dist;
        target = e;
      }
    }
  }
  
  if (!target) {
    player.sendMessage("§7[ShadowSlave] §cNenhum alvo válido ao alcance.");
    return false;
  }
  
  // Apply damage
  try {
    target.applyDamage(damage, { cause: EntityDamageCause.magic });
    const rangeInfo = equipped === "memory_void_walker" ? ` §8(alcance +${CONFIG.memories.memory_void_walker.shadowstrikeRangeBonus || 0})` : "";
    const damageInfo = equipped === "memory_shadow_blade" ? ` §8(dano +${CONFIG.memories.memory_shadow_blade.shadowstrikeDamageBonus || 0})` : "";
    player.sendMessage(`§7[ShadowSlave] §bAtaque Sombrio! §c${damage} de dano §7em ${target.typeId.replace("minecraft:", "")}${rangeInfo}${damageInfo}`);
    
    // Visual feedback - particle effect would go here in future
    // dimension.spawnParticle("minecraft:shadow_particle", target.location);
    
    // Try to summon echo if memory_echo_caller equipped
    if (echoSummoned) {
      summonEcho(player);
    }
    
    return true;
  } catch (e) {
    player.sendMessage("§7[ShadowSlave] §cFalha ao executar Ataque Sombrio.");
    return false;
  }
}

function executeShadowMantle(player) {
  // Read base values from CONFIG
  let duration = CONFIG.skills.shadowmantle.duration;
  let reduction = CONFIG.skills.shadowmantle.damageReduction;
  
  // Apply Memory effect: memory_soul_ward
  const equipped = player.getDynamicProperty(PROP_EQUIPPED_MEMORY) || "none";
  if (equipped === "memory_soul_ward") {
    const durBonus = CONFIG.memories.memory_soul_ward.mantleDurationBonus || 0;
    const redBonus = CONFIG.memories.memory_soul_ward.damageReductionBonus || 0;
    duration += durBonus;
    reduction = Math.min(1.0, reduction + redBonus); // Cap at 100%
  }
  
  // Apply resistance effect (damage reduction)
  try {
    player.addEffect(EffectType.damageResistance, duration * 20, Math.floor(reduction * 255), false);
    const durInfo = equipped === "memory_soul_ward" ? ` §8(+'${CONFIG.memories.memory_soul_ward.mantleDurationBonus || 0}'s)` : "";
    const redInfo = equipped === "memory_soul_ward" ? ` §8(+${Math.round((CONFIG.memories.memory_soul_ward.damageReductionBonus || 0) * 100)}%)` : "";
    player.sendMessage(`§7[ShadowSlave] §bManto Sombrio ativado! §7Proteção por ${duration}s (${Math.round(reduction * 100)}% redução)${durInfo}${redInfo}`);
    
    // Schedule removal message
    system.runTimeout(() => {
      if (player.isValid()) {
        player.sendMessage("§7[ShadowSlave] §fO Manto Sombrio se dissipa...");
      }
    }, duration * 1000);
    
    return true;
  } catch (e) {
    player.sendMessage("§7[ShadowSlave] §cFalha ao ativar Manto Sombrio.");
    return false;
  }
}

// ============================================================
// ECHO SYSTEM (FASE 5)
// ============================================================

function summonEcho(player) {
  // Check if player already has max active echoes
  const activeEchoes = player.getDynamicProperty("shadow_slave:active_echoes") || 0;
  if (activeEchoes >= CONFIG.echoes.maxActive) {
    player.sendMessage("§7[ShadowSlave] §cLimite de Ecos ativos atingido.");
    return false;
  }
  
  const echoConfig = CONFIG.echoes.echo_shade;
  const dimension = player.dimension;
  
  try {
    // Spawn echo entity near player
    const spawnLoc = {
      x: player.location.x + (Math.random() - 0.5) * 2,
      y: player.location.y + 1,
      z: player.location.z + (Math.random() - 0.5) * 2
    };
    
    const echo = dimension.spawnEntity("shadow_slave:echo_shade", spawnLoc);
    
    if (echo) {
      // Set echo properties
      echo.setDynamicProperty("shadow_slave:owner", player.name);
      echo.setDynamicProperty("shadow_slave:is_echo", true);
      echo.setDynamicProperty("shadow_slave:expires_at", Date.now() + echoConfig.duration * 1000);
      echo.nameTag = `§5${player.name}'s Eco`;
      
      // Track active echo
      player.setDynamicProperty("shadow_slave:active_echoes", activeEchoes + 1);
      
      // Schedule auto-removal
      system.runTimeout(() => {
        if (echo.isValid()) {
          echo.remove();
        }
        const current = player.getDynamicProperty("shadow_slave:active_echoes") || 0;
        player.setDynamicProperty("shadow_slave:active_echoes", Math.max(0, current - 1));
      }, echoConfig.duration * 1000);
      
      player.sendMessage(`§7[ShadowSlave] §bEco Sombrio invocado! §7Duração: ${echoConfig.duration}s`);
      return true;
    }
  } catch (e) {
    console.error("Failed to summon echo:", e);
  }
  
  return false;
}

// Cooldown tracking for echo summon (separate from skill cooldown)
function checkEchoCooldown(player) {
  const cooldowns = player.getDynamicProperty(PROP_COOLDOWNS) || {};
  const lastUsed = cooldowns["echo_summon"] || 0;
  const now = Date.now();
  const cooldownMs = CONFIG.echoes.echo_shade.cooldown * 1000;
  
  if (now - lastUsed < cooldownMs) {
    const remaining = Math.ceil((cooldownMs - (now - lastUsed)) / 1000);
    return { ready: false, remaining };
  }
  return { ready: true, remaining: 0 };
}

function setEchoCooldown(player) {
  const cooldowns = player.getDynamicProperty(PROP_COOLDOWNS) || {};
  cooldowns["echo_summon"] = Date.now();
  player.setDynamicProperty(PROP_COOLDOWNS, cooldowns);
}

// ============================================================
// PLAYER INITIALIZATION
// ============================================================

world.beforeEvents.playerJoin.subscribe((eventData) => {
  const player = eventData.player;
  
  if (player.getDynamicProperty(PROP_STAGE) === undefined) {
    player.setDynamicProperty(PROP_STAGE, 0);
    player.setDynamicProperty(PROP_ESSENCE, 0);
    player.setDynamicProperty(PROP_FRAGMENTS, 0);
    player.setDynamicProperty(PROP_CORES, 0);
    player.setDynamicProperty(PROP_ASPECT, "none");
    player.setDynamicProperty(PROP_SKILLS, []);
    player.setDynamicProperty(PROP_COOLDOWNS, {});
    player.setDynamicProperty(PROP_SOUL_SHARDS, 0);
    player.sendMessage("§7[ShadowSlave] §fSua jornada nas sombras começa... Estágio: §eMundano");
  } else if (player.getDynamicProperty(PROP_ASPECT) === undefined) {
    // Migration for existing players (pre-Fase 8B)
    player.setDynamicProperty(PROP_ASPECT, "none");
    player.setDynamicProperty(PROP_SKILLS, []);
    player.setDynamicProperty(PROP_COOLDOWNS, {});
    player.setDynamicProperty(PROP_SOUL_SHARDS, 0);
  }
  
  // Run core data migration (idempotent)
  migrateCoreDataOnJoin(player);
});

// ============================================================
// ENTITY DEATH - ESSENCE BONUS
// ============================================================

// ============================================================
// ENTITY DEATH - ESSENCE BONUS & SOUL SHARDS DROPS
// ============================================================

world.afterEvents.entityDie.subscribe((eventData) => {
  const deadEntity = eventData.deadEntity;
  const damageSource = eventData.damageSource;
  
  if (damageSource.damagingEntity?.typeId === "minecraft:player") {
    const player = damageSource.damagingEntity;
    
    if (deadEntity.typeId === "shadow_slave:shadow_slave") {
      // Existing essence bonus
      addEssence(player, 5 + Math.floor(Math.random() * 5));
      player.sendMessage("§7[ShadowSlave] §fVocê absorveu essência da sombra derrotada.");
      
      // Soul Shards drop (5-15 shards, higher chance for special entities)
      const shardDrop = 5 + Math.floor(Math.random() * 11); // 5-15 shards
      addSoulShards(player, shardDrop, "shadow_kill");
      player.sendMessage(`§7[ShadowSlave] §b+${shardDrop} Soul Shards §7absorvidos da sombra.`);
    }
    
    // Soul Shards drop for other hostile entities (lower chance)
    if (deadEntity.typeId !== "shadow_slave:shadow_slave" && 
        deadEntity.getTypeFamily().includes("monster") &&
        Math.random() < 0.15) { // 15% chance
      const shardDrop = 1 + Math.floor(Math.random() * 3); // 1-3 shards
      addSoulShards(player, shardDrop, "monster_kill");
      player.sendMessage(`§7[ShadowSlave] §b+${shardDrop} Soul Shards §7do §c${deadEntity.typeId.replace("minecraft:", "")}§7.`);
    }
  }
});

// ============================================================
// CHAT COMMANDS
// ============================================================

world.beforeEvents.chatSend.subscribe((eventData) => {
  const player = eventData.sender;
  const message = eventData.message.trim();
  
  // Progress commands
  if (message === "!stage" || message === "!progress") {
    eventData.cancel = true;
    showProgress(player);
    return;
  }
  
  if (message === "!evolve") {
    eventData.cancel = true;
    tryEvolve(player);
    return;
  }
  
  // Aspect commands
  if (message === "!aspect") {
    eventData.cancel = true;
    showAspect(player);
    return;
  }
  
  if (message === "!skills") {
    eventData.cancel = true;
    showSkills(player);
    return;
  }
  
  // Skill activation commands
  if (message === "!skill perception" || message === "!perception") {
    eventData.cancel = true;
    activateSkill(player, "perception");
    return;
  }
  
  if (message === "!skill shadowstrike" || message === "!shadowstrike") {
    eventData.cancel = true;
    activateSkill(player, "shadowstrike");
    return;
  }
  
  if (message === "!skill shadowmantle" || message === "!shadowmantle") {
    eventData.cancel = true;
    activateSkill(player, "shadowmantle");
    return;
  }
  
  // Admin commands (protected)
  if (message.startsWith("!giveessence ")) {
    eventData.cancel = true;
    if (!isAdmin(player)) {
      player.sendMessage("§7[ShadowSlave] §cComando restrito a administradores.");
      return;
    }
    const amount = parseInt(message.split(" ")[1]);
    if (!isNaN(amount) && amount > 0) addEssence(player, amount);
    return;
  }
  
  if (message.startsWith("!givefragment ")) {
    eventData.cancel = true;
    if (!isAdmin(player)) {
      player.sendMessage("§7[ShadowSlave] §cComando restrito a administradores.");
      return;
    }
    const amount = parseInt(message.split(" ")[1]);
    if (!isNaN(amount) && amount > 0) addFragment(player, amount);
    return;
  }
  
  if (message.startsWith("!givecore ")) {
    eventData.cancel = true;
    if (!isAdmin(player)) {
      player.sendMessage("§7[ShadowSlave] §cComando restrito a administradores.");
      return;
    }
    const amount = parseInt(message.split(" ")[1]);
    if (!isNaN(amount) && amount > 0) addCore(player, amount);
    return;
  }
  
  if (message.startsWith("!setstage ")) {
    eventData.cancel = true;
    if (!isAdmin(player)) {
      player.sendMessage("§7[ShadowSlave] §cComando restrito a administradores.");
      return;
    }
    const stage = parseInt(message.split(" ")[1]);
    if (!isNaN(stage) && stage >= 0 && stage < STAGES.length) {
      player.setDynamicProperty(PROP_STAGE, stage);
      applyStageBenefits(player, stage);
      player.sendMessage(`§7[ShadowSlave] §fEstágio forçado para: §e${STAGES[stage].name}`);
    }
    return;
  }
  
  if (message === "!help" || message === "!shadowhelp") {
    eventData.cancel = true;
    showHelp(player);
    return;
  }
  
  // Domination commands
  if (message === "!dominate") {
    eventData.cancel = true;
    tryDominate(player);
    return;
  }
  
  if (message === "!release") {
    eventData.cancel = true;
    // Need entity ID - simplified: release first minion
    const dominated = player.getDynamicProperty(PROP_DOMINATED) || {};
    const keys = Object.keys(dominated);
    if (keys.length > 0) {
      releaseMinion(player, keys[0]);
    } else {
      player.sendMessage("§7[ShadowSlave] §cNenhuma sombra dominada para liberar.");
    }
    return;
  }
  
  if (message.startsWith("!release ")) {
    eventData.cancel = true;
    const entityId = message.split(" ")[1];
    releaseMinion(player, entityId);
    return;
  }
  
  if (message === "!minions") {
    eventData.cancel = true;
    showMinions(player);
    return;
  }
  
  // Memories commands
  if (message === "!memories") {
    eventData.cancel = true;
    showMemories(player);
    return;
  }
  
  if (message.startsWith("!equip ")) {
    eventData.cancel = true;
    const memoryId = message.split(" ")[1];
    equipMemory(player, memoryId);
    return;
  }
  
  if (message === "!unequip") {
    eventData.cancel = true;
    unequipMemory(player);
    return;
  }
  
  // Echoes command
  if (message === "!echoes") {
    eventData.cancel = true;
    showEchoes(player);
    return;
  }
  
  // Soul Shards & Core System Commands (FASE 8B.2)
  if (message === "!shards") {
    eventData.cancel = true;
    const shards = getSoulShards(player);
    player.sendMessage(`§7[ShadowSlave] §fSoul Shards: §b${getSoulShards(player)}`);
    return;
  }
  
  if (message === "!saturate") {
    eventData.cancel = true;
    const result = attemptCoreSaturation(player);
    player.sendMessage(result.message);
    return;
  }
  
  if (message === "!cores") {
    eventData.cancel = true;
    const coreData = getCoreDataOrDefault(player);
    const maxCores = getMaxCoresForPlayer(player);
    let msg = "§8§m------------------------§r\n";
    msg += `§7[ShadowSlave] §fNúcleos: §e${coreData.cores.length}/${coreData.maxCores}\n`;
    coreData.cores.forEach((core, index) => {
      const saturationPct = core.maxSaturation > 0 ? Math.floor((core.saturation / core.maxSaturation) * 100) : 0;
      const rankName = core.rank > 0 ? ` (Rank ${core.rank}: ${getCoreRankName(core.rank)})` : " (Vazio)";
      msg += `  §eNúcleo ${index + 1}§7: §b${core.saturation}/${core.maxSaturation} §7(§e${saturationPct}%§7)${rankName}\n`;
    });
    msg += `\n§7Soul Shards: §b${getSoulShards(player)}`;
    msg += "\n§8§m------------------------§r";
    player.sendMessage(msg);
    return;
  }
  
  if (message === "!help" || message === "!shadowhelp") {
});

// ============================================================
// ASPECT SYSTEM
// ============================================================

function showAspect(player) {
  const data = getPlayerData(player);
  const aspectId = data.aspect;
  
  if (aspectId === "none" || !ASPECTS[aspectId]) {
    const aspect = ASPECTS.shadow;
    const canUnlock = data.stage >= aspect.requiredStage;
    
    let msg = "§8§m------------------------§r\n";
    msg += `§7[ShadowSlave] §fAspecto: §cNenhum\n`;
    msg += `§7Disponível: §e${aspect.name}\n`;
    msg += `§7Requer: §eEstágio ${aspect.requiredStage}+ (${aspect.description})\n`;
    msg += `§7Status: ${canUnlock ? "§a[DESBLOQUEÁVEL - use !unlockaspect shadow]" : "§c[BLOQUEADO]"}`;
    msg += "\n§8§m------------------------§r";
    player.sendMessage(msg);
    return;
  }
  
  const aspect = ASPECTS[aspectId];
  let msg = "§8§m------------------------§r\n";
  msg += `§7[ShadowSlave] §fAspecto Ativo: §e${aspect.name}\n`;
  msg += `§7${aspect.description}\n`;
  msg += `§7Habilidades: §e${aspect.skills.length}\n`;
  for (const skillId of aspect.skills) {
    const skill = SKILLS[skillId];
    const unlocked = data.skills.includes(skillId);
    msg += `  ${unlocked ? "§a✓" : "§c✗"} ${skill.name} §7(Estágio ${skill.requiredStage}+)`;
  }
  msg += "\n§8§m------------------------§r";
  player.sendMessage(msg);
}

function showSkills(player) {
  const data = getPlayerData(player);
  const aspectId = data.aspect;
  
  if (aspectId === "none" || !ASPECTS[aspectId]) {
    player.sendMessage("§7[ShadowSlave] §cVocê não possui um Aspecto. Use §e!aspect §cpara ver opções.");
    return;
  }
  
  const aspect = ASPECTS[aspectId];
  let msg = "§8§m------------------------§r\n";
  msg += `§7[ShadowSlave] §fHabilidades do §e${aspect.name}:\n\n`;
  
  for (const skillId of aspect.skills) {
    const skill = SKILLS[skillId];
    const unlocked = data.skills.includes(skillId);
    const cooldown = checkCooldown(player, skillId);
    const canUse = data.stage >= skill.requiredStage;
    
    msg += `${unlocked ? "§a✓" : "§c✗"} ${skill.name}\n`;
    msg += `  §7${skill.description}\n`;
    msg += `  §7Estágio: ${canUse ? "§a" : "§c"}${skill.requiredStage}+ §7| Custo: §b${skill.essenceCost} Essência §7| Recarga: §e${formatCooldown(skill.cooldown)}`;
    if (!cooldown.ready) {
      msg += ` §c[Recarga: ${formatCooldown(cooldown.remaining)}]`;
    }
    msg += "\n";
  }
  msg += "\n§7Use §e!skill <nome> §7para ativar. Ex: §e!skill perception";
  msg += "\n§8§m------------------------§r";
  player.sendMessage(msg);
}

function activateSkill(player, skillId) {
  const skill = SKILLS[skillId];
  if (!skill) {
    player.sendMessage("§7[ShadowSlave] §cHabilidade desconhecida.");
    return;
  }
  
  const data = getPlayerData(player);
  
  // Check aspect
  if (data.aspect !== skill.aspect) {
    player.sendMessage(`§7[ShadowSlave] §cEsta habilidade requer o ${ASPECTS[skill.aspect].name}.`);
    return;
  }
  
  // Check unlocked
  if (!data.skills.includes(skillId)) {
    if (data.stage >= skill.requiredStage) {
      // Auto-unlock if stage requirement met
      const newSkills = [...data.skills, skillId];
      player.setDynamicProperty(PROP_SKILLS, newSkills);
      player.sendMessage(`§7[ShadowSlave] §aHabilidade desbloqueada: §e${skill.name}!`);
    } else {
      player.sendMessage(`§7[ShadowSlave] §cHabilidade bloqueada. Requer Estágio ${skill.requiredStage}+ (${STAGES[skill.requiredStage].name}).`);
      return;
    }
  }
  
  // Check cooldown
  const cooldown = checkCooldown(player, skillId);
  if (!cooldown.ready) {
    player.sendMessage(`§7[ShadowSlave] §cHabilidade em recarga: ${formatCooldown(cooldown.remaining)}`);
    return;
  }
  
  // Check essence cost
  if (!consumeEssence(player, skill.essenceCost)) {
    player.sendMessage(`§7[ShadowSlave] §cEssência insuficiente. Necessário: §b${skill.essenceCost}`);
    return;
  }
  
  // Execute skill
  const success = skill.execute(player);
  if (success) {
    setCooldown(player, skillId);
  } else {
    // Refund essence on failure
    addEssence(player, skill.essenceCost);
  }
}

// ============================================================
// PROGRESSION SYSTEM
// ============================================================

function showProgress(player) {
  const data = getPlayerData(player);
  const coreData = getCoreDataOrDefault(player);
  const current = STAGES[data.stage];
  const next = STAGES[data.stage + 1];
  
  let msg = "§8§m------------------------§r\n";
  msg += `§7[ShadowSlave] §fProgressão de §e${player.name}\n`;
  msg += `§7Estágio: §e${current.name} §7(${data.stage}/${STAGES.length - 1})\n`;
  msg += `§7Essência: §b${data.essence}§7`;
  if (next) msg += ` §8/ ${next.essence}`;
  msg += `\n§7Fragmentos: §6${data.fragments}§7`;
  if (next) msg += ` §8/ ${next.fragments}`;
  msg += `\n§7Núcleos: §5${data.cores}§7`;
  if (next) msg += ` §8/ ${next.cores}`;
  
  // Soul Shards & Core Saturation
  const shards = getSoulShards(player);
  const coreData = getCoreDataOrDefault(player);
  msg += `\n§7Soul Shards: §b${getSoulShards(player)}`;
  if (coreData && coreData.cores && coreData.cores.length > 0) {
    msg += `\n§7Núcleos:`;
    coreData.cores.forEach((core, index) => {
      const saturationPct = core.maxSaturation > 0 ? Math.floor((core.saturation / core.maxSaturation) * 100) : 0;
      const rankName = core.rank > 0 ? ` (Rank ${core.rank}: ${getCoreRankName(core.rank)})` : " (Vazio)";
      const saturationPct = core.maxSaturation > 0 ? Math.floor((core.saturation / core.maxSaturation) * 100) : 0;
      msg += `\n  §eNúcleo ${index + 1}§7: §b${core.saturation}/${core.maxSaturation} §7(§e${saturationPct}%§7)${rankName}`;
    });
    msg += `\n§7Soul Shards: §b${getSoulShards(player)}`;
  }
  msg += `\n§7Soul Shards: §b${getSoulShards(player)}`;
  
  if (next) {
    const canEvolve = data.essence >= next.essence && data.fragments >= next.fragments && data.cores >= next.cores;
    // Check if player has at least one saturated core for evolution
    const coreData = getCoreDataOrDefault(player);
    const hasSaturatedCore = coreData.cores.some(core => core.saturation >= core.maxSaturation && core.rank > 0);
    const canEvolveFull = data.essence >= next.essence && data.fragments >= next.fragments && data.cores >= next.cores && hasSaturatedCore;
    msg += `\n§7Próximo: §e${next.name} ${canEvolveFull ? "§a[DISPONÍVEL]" : "§c[BLOQUEADO]"}`;
    if (!hasSaturatedCore) {
      msg += ` §c(Requer núcleo saturado e evoluído)`;
    }
    msg += `\n§7Use §e!evolve §7para evoluir quando pronto.`;
  } else {
    msg += `\n§7§oEstágio máximo atingido.`;
  }
  
  // Aspect info
  if (data.aspect !== "none" && ASPECTS[data.aspect]) {
    msg += `\n§7Aspecto: §e${ASPECTS[data.aspect].name} §7| Habilidades: §e${data.skills.length}`;
  }
  
  msg += "\n§8§m------------------------§r";
  player.sendMessage(msg);
}

function addEssence(player, amount) {
  const current = player.getDynamicProperty(PROP_ESSENCE) || 0;
  player.setDynamicProperty(PROP_ESSENCE, current + amount);
  player.sendMessage(`§7[ShadowSlave] §f+§b${amount} §fEssência das Sombras (Total: §b${current + amount}§f)`);
}

function addFragment(player, amount = 1) {
  const current = player.getDynamicProperty(PROP_FRAGMENTS) || 0;
  player.setDynamicProperty(PROP_FRAGMENTS, current + amount);
  player.sendMessage(`§7[ShadowSlave] §f+§6${amount} §fFragmento(s) de Alma (Total: §6${current + amount}§f)`);
}

function addCore(player, amount = 1) {
  const current = player.getDynamicProperty(PROP_CORES) || 0;
  player.setDynamicProperty(PROP_CORES, current + amount);
  player.sendMessage(`§7[ShadowSlave] §f+§5${amount} §fNúcleo(s) de Alma (Total: §5${current + amount}§f)`);
}

function tryEvolve(player) {
  const data = getPlayerData(player);
  const nextStage = data.stage + 1;
  
  if (nextStage >= STAGES.length) {
    player.sendMessage("§7[ShadowSlave] §cVocê já atingiu o estágio máximo: §eDivino");
    return;
  }
  
  const next = STAGES[nextStage];
  
  if (data.essence < next.essence || data.fragments < next.fragments || data.cores < next.cores) {
    player.sendMessage("§7[ShadowSlave] §cRecursos insuficientes para evoluir!");
    player.sendMessage(`§7Necessário: §b${next.essence}§7 Essência, §6${next.fragments}§7 Fragmentos, §5${next.cores}§7 Núcleos`);
    player.sendMessage(`§7Atual: §b${data.essence}§7/§6${data.fragments}§7/§5${data.cores}`);
    return;
  }
  
  // Consume resources
  player.setDynamicProperty(PROP_ESSENCE, data.essence - next.essence);
  player.setDynamicProperty(PROP_FRAGMENTS, data.fragments - next.fragments);
  player.setDynamicProperty(PROP_CORES, data.cores - next.cores);
  player.setDynamicProperty(PROP_STAGE, nextStage);
  
  // Auto-unlock aspect at stage 1
  if (nextStage === 1 && data.aspect === "none") {
    player.setDynamicProperty(PROP_ASPECT, "shadow");
    player.setDynamicProperty(PROP_SKILLS, ["perception"]);
    player.sendMessage("§7[ShadowSlave] §a§lAspecto das Sombras despertou! §fHabilidade desbloqueada: §ePercepção das Sombras");
  }
  
  // Auto-unlock skills at appropriate stages
  const aspect = ASPECTS.shadow;
  for (const skillId of aspect.skills) {
    const skill = SKILLS[skillId];
    if (nextStage >= skill.requiredStage && !data.skills.includes(skillId)) {
      const newSkills = [...data.skills, skillId];
      player.setDynamicProperty(PROP_SKILLS, newSkills);
      player.sendMessage(`§7[ShadowSlave] §aNova habilidade desbloqueada: §e${skill.name}!`);
    }
  }
  
  applyStageBenefits(player, nextStage);
  
  player.sendMessage(`§7[ShadowSlave] §a§lEVOLUÇÃO CONCLUÍDA!§r`);
  player.sendMessage(`§7Novo estágio: §e${next.name}`);
  player.sendMessage(`§7Recursos restantes: §b${data.essence - next.essence}§7/§6${data.fragments - next.fragments}§7/§5${data.cores - next.cores}`);
}

function applyStageBenefits(player, stage) {
  const healthBoost = [0, 2, 4, 6, 8, 10, 12][stage] || 0;
  const damageBoost = [0, 1, 2, 3, 4, 5, 6][stage] || 0;
  
  if (healthBoost > 0) {
    const maxHealth = 20 + healthBoost;
    player.setProperty("minecraft:health", { current: maxHealth, max: maxHealth });
  }
  
  // Damage boost via strength effect (temporary workaround for 2.9.0)
  if (damageBoost > 0) {
    player.addEffect(EffectType.strength, 24 * 60 * 60 * 20, damageBoost - 1, true); // 24h duration
  }
  
  player.sendMessage(`§7[ShadowSlave] §fBenefícios aplicados: §c+${healthBoost} HP máx. §7| §c+${damageBoost} Dano (Força)`);
}

function showHelp(player) {
  let msg = "§8§m------------------------§r\n";
  msg += `§7[ShadowSlave] §fComandos disponíveis:\n\n`;
  msg += `§e!stage §7ou §e!progress §7- Ver progressão\n`;
  msg += `§e!evolve §7- Evoluir para próximo estágio\n`;
  msg += `§e!aspect §7- Ver Aspecto atual\n`;
  msg += `§e!skills §7- Ver habilidades\n`;
  msg += `§e!skill perception §7- Percepção das Sombras\n`;
  msg += `§e!skill shadowstrike §7- Ataque Sombrio\n`;
  msg += `§e!skill shadowmantle §7- Manto Sombrio\n\n`;
  msg += `§e!dominate §7- Iniciar ritual de dominação (olhe para uma sombra)\n`;
  msg += `§e!release §7- Liberar sombra dominada\n`;
  msg += `§e!minions §7- Ver sombras dominadas\n\n`;
  msg += `§e!memories §7- Ver Memórias obtidas\n`;
  msg += `§e!equip <id> §7- Equipar Memória\n`;
  msg += `§e!unequip §7- Remover Memória equipada\n\n`;
  msg += `§e!shards §7- Ver Soul Shards atuais\n`;
  msg += `§e!saturate §7- Saturar núcleo com Soul Shards\n`;
  msg += `§e!cores §7- Ver núcleos e saturação\n\n`;
  msg += `§cAdmin only:\n`;
  msg += `§e!giveessence <qtd> §7- Dar essência\n`;
  msg += `§e!givefragment <qtd> §7- Dar fragmentos\n`;
  msg += `§e!givecore <qtd> §7- Dar núcleos\n`;
  msg += `§e!setstage <0-6> §7- Forçar estágio\n`;
  msg += `\n§8§m------------------------§r`;
  player.sendMessage(msg);
}

// ============================================================
// DOMINATION SYSTEM (FASE 4)
// ============================================================

const DOMINATION_COST = { essence: 100, fragments: 10, cores: 2 };
const MAX_DOMINATED_PER_PLAYER = 3;

function tryDominate(player) {
  const data = getPlayerData(player);
  
  if (data.stage < 3) {
    player.sendMessage("§7[ShadowSlave] §cRitual requer Estágio 3 (Transcendente) ou superior.");
    return;
  }
  
  // Check if player already has max dominated
  const dominated = player.getDynamicProperty(PROP_DOMINATED) || {};
  const dominatedCount = Object.keys(dominated).length;
  if (dominatedCount >= MAX_DOMINATED_PER_PLAYER) {
    player.sendMessage(`§7[ShadowSlave] §cLimite de sombras dominadas atingido (${MAX_DOMINATED_PER_PLAYER}). Use §e!release §cpara liberar uma.`);
    return;
  }
  
  // Check resources
  if (data.essence < DOMINATION_COST.essence || data.fragments < DOMINATION_COST.fragments || data.cores < DOMINATION_COST.cores) {
    player.sendMessage("§7[ShadowSlave] §cRecursos insuficientes para o ritual.");
    player.sendMessage(`§7Necessário: §b${DOMINATION_COST.essence}§7 Essência, §6${DOMINATION_COST.fragments}§7 Fragmentos, §5${DOMINATION_COST.cores}§7 Núcleos`);
    return;
  }
  
  // Find nearest shadow_slave entity looking at
  const dimension = player.dimension;
  const viewDir = player.getViewDirection();
  const entities = dimension.getEntities({
    location: player.location,
    maxDistance: 10,
    type: "shadow_slave:shadow_slave"
  });
  
  let target = null;
  let minAngle = Math.PI; // 180 degrees
  
  for (const e of entities) {
    // Skip already dominated
    if (e.getDynamicProperty("shadow_slave:owner")) continue;
    
    const toEntity = {
      x: e.location.x - player.location.x,
      y: e.location.y - player.location.y,
      z: e.location.z - player.location.z
    };
    const dist = Math.sqrt(toEntity.x**2 + toEntity.y**2 + toEntity.z**2);
    if (dist === 0) continue;
    
    const dot = (toEntity.x * viewDir.x + toEntity.y * viewDir.y + toEntity.z * viewDir.z) / dist;
    const angle = Math.acos(Math.max(-1, Math.min(1, dot)));
    
    if (angle < minAngle && angle < Math.PI / 3) { // Within 60 degrees cone
      minAngle = angle;
      target = e;
    }
  }
  
  if (!target) {
    player.sendMessage("§7[ShadowSlave] §cNenhuma sombra válida à frente. Olhe para uma sombra selvagem (até 10 blocos).");
    return;
  }
  
  // Consume resources
  player.setDynamicProperty(PROP_ESSENCE, data.essence - DOMINATION_COST.essence);
  player.setDynamicProperty(PROP_FRAGMENTS, data.fragments - DOMINATION_COST.fragments);
  player.setDynamicProperty(PROP_CORES, data.cores - DOMINATION_COST.cores);
  
  // Perform domination
  const entityId = target.id;
  target.setDynamicProperty("shadow_slave:owner", player.name);
  target.setDynamicProperty("shadow_slave:dominated", true);
  
  // Add follow_owner behavior via component group (requires entity events)
  // Since we can't dynamically add components, we'll track ownership and modify behavior via script
  
  // Store domination link
  dominated[entityId] = {
    entityId: entityId,
    timestamp: Date.now()
  };
  player.setDynamicProperty(PROP_DOMINATED, dominated);
  
  // Visual feedback
  player.sendMessage("§7[ShadowSlave] §a§lRITUAL CONCLUÍDO!§r");
  player.sendMessage(`§7A sombra agora te serve. Use §e!minions §7para gerenciar.`);
  target.nameTag = `§5${player.name}'s Sombra`;
  
  // Make it follow owner - we'll use a simple scripted follow
  startMinionFollow(player, target);
}

function startMinionFollow(owner, minion) {
  // Simple follow behavior via system ticks
  const followTask = system.runInterval(() => {
    if (!owner.isValid() || !minion.isValid()) {
      system.clearRun(followTask);
      return;
    }
    
    const ownerLoc = owner.location;
    const minionLoc = minion.location;
    const dist = Math.sqrt(
      Math.pow(minionLoc.x - ownerLoc.x, 2) +
      Math.pow(minionLoc.y - ownerLoc.y, 2) +
      Math.pow(minionLoc.z - ownerLoc.z, 2)
    );
    
    if (dist > 5) {
      // Teleport closer if too far (simple approach)
      if (dist > 15) {
        minion.teleport({
          x: ownerLoc.x + (Math.random() - 0.5) * 2,
          y: ownerLoc.y + 1,
          z: ownerLoc.z + (Math.random() - 0.5) * 2
        }, { dimension: owner.dimension });
      }
    }
    
    // Defend owner - attack owner's target
    // This is a simplified approach
  }, 20); // Every tick
  
  // Store task ID for cleanup
  const tasks = owner.getDynamicProperty("shadow_slave:minion_tasks") || {};
  tasks[minion.id] = followTask;
  owner.setDynamicProperty("shadow_slave:minion_tasks", tasks);
}

function releaseMinion(player, entityId) {
  const dominated = player.getDynamicProperty(PROP_DOMINATED) || {};
  const minionData = dominated[entityId];
  
  if (!minionData) {
    player.sendMessage("§7[ShadowSlave] §cVocê não domina esta sombra.");
    return;
  }
  
  // Find and release the entity
  const entities = player.dimension.getEntities({ type: "shadow_slave:shadow_slave" });
  for (const e of entities) {
    if (e.id === entityId) {
      e.setDynamicProperty("shadow_slave:owner", undefined);
      e.setDynamicProperty("shadow_slave:dominated", false);
      e.nameTag = "";
      break;
    }
  }
  
  // Clean up follow task
  const tasks = player.getDynamicProperty("shadow_slave:minion_tasks") || {};
  if (tasks[entityId]) {
    system.clearRun(tasks[entityId]);
    delete tasks[entityId];
    player.setDynamicProperty("shadow_slave:minion_tasks", tasks);
  }
  
  delete dominated[entityId];
  player.setDynamicProperty(PROP_DOMINATED, dominated);
  
  player.sendMessage("§7[ShadowSlave] §fSombra liberada.");
}

function showMinions(player) {
  const dominated = player.getDynamicProperty(PROP_DOMINATED) || {};
  const count = Object.keys(dominated).length;
  
  let msg = "§8§m------------------------§r\n";
  msg += `§7[ShadowSlave] §fSombras Dominadas: §e${count}/${MAX_DOMINATED_PER_PLAYER}\n\n`;
  
  if (count === 0) {
    msg += "§7Nenhuma sombra dominada. Use §e!dominate §7olhando para uma sombra selvagem.";
  } else {
    for (const [entityId, data] of Object.entries(dominated)) {
      const entities = player.dimension.getEntities({ type: "shadow_slave:shadow_slave" });
      let found = false;
      for (const e of entities) {
        if (e.id === entityId) {
          const dist = Math.sqrt(
            Math.pow(e.location.x - player.location.x, 2) +
            Math.pow(e.location.y - player.location.y, 2) +
            Math.pow(e.location.z - player.location.z, 2)
          );
          msg += `§eSombra #${entityId.slice(-6)}§7 - Distância: ${dist.toFixed(1)} blocos\n`;
          found = true;
          break;
        }
      }
      if (!found) {
        msg += `§cSombra #${entityId.slice(-6)}§7 - Perdida (fora do alcance)\n`;
      }
    }
    msg += `\n§7Use §e!release <id> §7para liberar uma sombra.`;
  }
  msg += "\n§8§m------------------------§r";
  player.sendMessage(msg);
}

// Handle minion death - clean up
world.afterEvents.entityDie.subscribe((eventData) => {
  const deadEntity = eventData.deadEntity;
  if (deadEntity.typeId === "shadow_slave:shadow_slave") {
    const ownerName = deadEntity.getDynamicProperty("shadow_slave:owner");
    if (ownerName) {
      const players = world.getPlayers({ name: ownerName });
      if (players.length > 0) {
        const owner = players[0];
        const dominated = owner.getDynamicProperty(PROP_DOMINATED) || {};
        delete dominated[deadEntity.id];
        owner.setDynamicProperty(PROP_DOMINATED, dominated);
        
        // Clean up task
        const tasks = owner.getDynamicProperty("shadow_slave:minion_tasks") || {};
        if (tasks[deadEntity.id]) {
          system.clearRun(tasks[deadEntity.id]);
          delete tasks[deadEntity.id];
          owner.setDynamicProperty("shadow_slave:minion_tasks", tasks);
        }
        
        owner.sendMessage("§7[ShadowSlave] §cUma de suas sombras dominadas foi derrotada.");
      }
    }
  }
});

// Player leave - clean up minion tasks
world.afterEvents.playerLeave.subscribe((eventData) => {
  const player = eventData.player;
  const tasks = player.getDynamicProperty("shadow_slave:minion_tasks") || {};
  for (const taskId of Object.values(tasks)) {
    system.clearRun(taskId);
  }
});

// ============================================================
// MEMORIES SYSTEM (FASE 4)
// ============================================================

const MEMORIES = {
  memory_shadow_blade: {
    id: "memory_shadow_blade",
    name: "Lâmina da Sombra",
    description: "Uma lâmina forjada de escuridão pura. Aumenta o dano de Ataque Sombrio.",
    rarity: "Raro",
    type: "weapon",
    effect: { shadowstrike_damage_bonus: 4 },
    requiredStage: 2
  },
  memory_void_walker: {
    id: "memory_void_walker",
    name: "Andarilho do Vazio",
    description: "Permite mover-se brevemente através das sombras.",
    rarity: "Épico",
    type: "utility",
    effect: { perception_range_bonus: 10, shadowstrike_range_bonus: 4 },
    requiredStage: 3
  },
  memory_soul_ward: {
    id: "memory_soul_ward",
    name: "Guardião da Alma",
    description: "Protege o portador com energia espiritual.",
    rarity: "Raro",
    type: "armor",
    effect: { mantle_duration_bonus: 10, damage_reduction_bonus: 0.15 },
    requiredStage: 3
  },
  memory_echo_caller: {
    id: "memory_echo_caller",
    name: "Chamador de Ecos",
    description: "Permite invocar ecos das sombras para auxiliar no combate.",
    rarity: "Lendário",
    type: "summon",
    effect: { echo_summon_chance: 0.2 },
    requiredStage: 4
  }
};

function showMemories(player) {
  const data = getPlayerData(player);
  const memories = player.getDynamicProperty(PROP_MEMORIES) || [];
  const equipped = player.getDynamicProperty(PROP_EQUIPPED_MEMORY) || "none";
  
  let msg = "§8§m------------------------§r\n";
  msg += `§7[ShadowSlave] §fMemórias: §e${memories.length}\n`;
  msg += `§7Equipada: ${equipped !== "none" ? `§e${MEMORIES[equipped]?.name || equipped}` : "§cNenhuma"}\n\n`;
  
  if (memories.length === 0) {
    msg += "§7Nenhuma Memória obtida. Derrote sombras e complete rituais para encontrá-las.";
  } else {
    for (const memId of memories) {
      const mem = MEMORIES[memId];
      if (!mem) continue;
      const isEquipped = memId === equipped;
      msg += `${isEquipped ? "§a✦ " : "  "}§e${mem.name} §7(${mem.rarity})\n`;
      msg += `    §7${mem.description}\n`;
      if (mem.effect) {
        for (const [k, v] of Object.entries(mem.effect)) {
          msg += `    §8+${v} ${k}\n`;
        }
      }
    }
  }
  msg += `\n§7Use §e!equip <id> §7ou §e!unequip`;
  msg += "\n§8§m------------------------§r";
  player.sendMessage(msg);
}

function equipMemory(player, memoryId) {
  const data = getPlayerData(player);
  const memories = player.getDynamicProperty(PROP_MEMORIES) || [];
  
  if (!memories.includes(memoryId)) {
    player.sendMessage("§7[ShadowSlave] §cVocê não possui esta Memória.");
    return;
  }
  
  const mem = MEMORIES[memoryId];
  if (!mem) {
    player.sendMessage("§7[ShadowSlave] §cMemória inválida.");
    return;
  }
  
  if (data.stage < mem.requiredStage) {
    player.sendMessage(`§7[ShadowSlave] §cRequer Estágio ${mem.requiredStage}+ (${STAGES[mem.requiredStage].name}).`);
    return;
  }
  
  const currentEquipped = player.getDynamicProperty(PROP_EQUIPPED_MEMORY) || "none";
  if (currentEquipped === memoryId) {
    player.sendMessage("§7[ShadowSlave] §cEsta Memória já está equipada.");
    return;
  }
  
  player.setDynamicProperty(PROP_EQUIPPED_MEMORY, memoryId);
  player.sendMessage(`§7[ShadowSlave] §aMemória equipada: §e${mem.name}`);
  
  // Apply effects (simplified - would need more complex system for full implementation)
  applyMemoryEffects(player, memoryId);
}

function unequipMemory(player) {
  const currentEquipped = player.getDynamicProperty(PROP_EQUIPPED_MEMORY) || "none";
  if (currentEquipped === "none") {
    player.sendMessage("§7[ShadowSlave] §cNenhuma Memória equipada.");
    return;
  }
  
  player.setDynamicProperty(PROP_EQUIPPED_MEMORY, "none");
  player.sendMessage("§7[ShadowSlave] §fMemória removida.");
  
  // Remove effects (simplified)
  removeMemoryEffects(player, currentEquipped);
}

function applyMemoryEffects(player, memoryId) {
  // Effects are applied conceptually; actual implementation would need
  // integration with skill execution and combat systems
  const mem = MEMORIES[memoryId];
  if (mem && mem.effect) {
    player.sendMessage(`§7[ShadowSlave] §fEfeitos de §e${mem.name} §fativos.`);
  }
}

function removeMemoryEffects(player, memoryId) {
  // Placeholder for effect removal
}

// Grant random memory on shadow kill (rare)
function maybeGrantMemory(player) {
  const memoryIds = Object.keys(MEMORIES);
  const chance = 0.05; // 5% chance
  
  if (Math.random() < chance) {
    const randomMem = memoryIds[Math.floor(Math.random() * memoryIds.length)];
    const memories = player.getDynamicProperty(PROP_MEMORIES) || [];
    
    if (!memories.includes(randomMem)) {
      memories.push(randomMem);
      player.setDynamicProperty(PROP_MEMORIES, memories);
      player.sendMessage(`§7[ShadowSlave] §a§lMEMÓRIA ENCONTRADA!§r §e${MEMORIES[randomMem].name}`);
    }
  }
}

// Hook into entity death for memory drops
const originalEntityDieHandler = world.afterEvents.entityDie;
// Note: We can't easily override, so we'll add a second subscription
world.afterEvents.entityDie.subscribe((eventData) => {
  const deadEntity = eventData.deadEntity;
  const damageSource = eventData.damageSource;
  
  if (damageSource.damagingEntity?.typeId === "minecraft:player" &&
      deadEntity.typeId === "shadow_slave:shadow_slave") {
    const player = damageSource.damagingEntity;
    maybeGrantMemory(player);
  }
});

// ============================================================
// EQUIPMENT / ECHOES BASE (FASE 4)
// ============================================================

const ECHOES = {
  echo_shade: {
    id: "echo_shade",
    name: "Eco Sombrio",
    description: "Um fragmento de sombra que luta ao seu lado temporariamente.",
    type: "combat",
    duration: 30,
    cooldown: 120,
    damage: 5
  }
};

function showEchoes(player) {
  const echoes = player.getDynamicProperty(PROP_ECHOES) || [];
  
  let msg = "§8§m------------------------§r\n";
  msg += `§7[ShadowSlave] §fEcos: §e${echoes.length}\n\n`;
  
  if (echoes.length === 0) {
    msg += "§7Nenhum Eco obtido. Memórias especiais podem conceder Ecos.";
  } else {
    for (const echoId of echoes) {
      const echo = ECHOES[echoId];
      if (!echo) continue;
      msg += `§e${echo.name}§7 - ${echo.description}\n`;
      msg += `  Dano: ${echo.damage} | Duração: ${echo.duration}s | Recarga: ${echo.cooldown}s\n`;
    }
  }
  msg += "\n§8§m------------------------§r";
  player.sendMessage(msg);
}

// ============================================================
// COMMAND HANDLERS FOR NEW SYSTEMS
// ============================================================

// Add to chatSend handler (will be inserted into existing handler)

export { STAGES, ASPECTS, SKILLS, MEMORIES, ECHOES, addEssence, addFragment, addCore, attemptCoreSaturation, attemptRankUp };
