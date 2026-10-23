import { world, system, Player, ItemStack, EquipmentSlot, Block, Entity, EffectType, EntityDamageCause } from "@minecraft/server";

// ============================================================
// SHADOW SLAVE - FASE 3: ASPECTOS, HABILIDADES E COMBATE
// ============================================================

// Stages configuration
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
const PROP_CORES = "shadow_slave:cores";
const PROP_ASPECT = "shadow_slave:aspect";
const PROP_SKILLS = "shadow_slave:skills";
const PROP_COOLDOWNS = "shadow_slave:cooldowns";

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
// SKILL IMPLEMENTATIONS
// ============================================================

function executePerception(player) {
  const range = SKILLS.perception.range;
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
    player.sendMessage("§7[ShadowSlave] §bPercepção das Sombras ativada:");
    for (const f of found.slice(0, 10)) { // Limit to 10 entries
      player.sendMessage(`  ${f}`);
    }
    if (found.length > 10) {
      player.sendMessage(`  §7...e mais ${found.length - 10} entidades`);
    }
  }
  return true;
}

function executeShadowStrike(player) {
  const range = SKILLS.shadowstrike.range;
  const damage = SKILLS.shadowstrike.damage;
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
    player.sendMessage(`§7[ShadowSlave] §bAtaque Sombrio! §c${damage} de dano §7em ${target.typeId.replace("minecraft:", "")}`);
    
    // Visual feedback - particle effect would go here in future
    // dimension.spawnParticle("minecraft:shadow_particle", target.location);
    
    return true;
  } catch (e) {
    player.sendMessage("§7[ShadowSlave] §cFalha ao executar Ataque Sombrio.");
    return false;
  }
}

function executeShadowMantle(player) {
  const duration = SKILLS.shadowmantle.duration;
  const reduction = SKILLS.shadowmantle.damageReduction;
  
  // Apply resistance effect (damage reduction)
  try {
    player.addEffect(EffectType.damageResistance, duration * 20, Math.floor(reduction * 255), false);
    player.sendMessage(`§7[ShadowSlave] §bManto Sombrio ativado! §7Proteção por ${duration}s (${Math.round(reduction * 100)}% redução)`);
    
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
    player.sendMessage("§7[ShadowSlave] §fSua jornada nas sombras começa... Estágio: §eMundano");
  } else if (player.getDynamicProperty(PROP_ASPECT) === undefined) {
    // Migration for existing players
    player.setDynamicProperty(PROP_ASPECT, "none");
    player.setDynamicProperty(PROP_SKILLS, []);
    player.setDynamicProperty(PROP_COOLDOWNS, {});
  }
});

// ============================================================
// ENTITY DEATH - ESSENCE BONUS
// ============================================================

world.afterEvents.entityDie.subscribe((eventData) => {
  const deadEntity = eventData.deadEntity;
  const damageSource = eventData.damageSource;
  
  if (damageSource.damagingEntity?.typeId === "minecraft:player") {
    const player = damageSource.damagingEntity;
    
    if (deadEntity.typeId === "shadow_slave:shadow_slave") {
      addEssence(player, 5 + Math.floor(Math.random() * 5));
      player.sendMessage("§7[ShadowSlave] §fVocê absorveu essência da sombra derrotada.");
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
  
  if (next) {
    const canEvolve = data.essence >= next.essence && data.fragments >= next.fragments && data.cores >= next.cores;
    msg += `\n§7Próximo: §e${next.name} ${canEvolve ? "§a[DISPONÍVEL]" : "§c[BLOQUEADO]"}`;
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
  msg += `§cAdmin only:\n`;
  msg += `§e!giveessence <qtd> §7- Dar essência\n`;
  msg += `§e!givefragment <qtd> §7- Dar fragmentos\n`;
  msg += `§e!givecore <qtd> §7- Dar núcleos\n`;
  msg += `§e!setstage <0-6> §7- Forçar estágio\n`;
  msg += `\n§8§m------------------------§r`;
  player.sendMessage(msg);
}

// ============================================================
// EXPORTS
// ============================================================
export { STAGES, ASPECTS, SKILLS, addEssence, addFragment, addCore };
