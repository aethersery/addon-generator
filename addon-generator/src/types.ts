// Type definitions for the Addon Generator frontend

export type Edition = 'bedrock' | 'java' | 'both';
export type GenerationStatus = 
  | 'pending'
  | 'researching'
  | 'planning'
  | 'generating_bp'
  | 'generating_rp'
  | 'generating_textures'
  | 'generating_models'
  | 'validating'
  | 'packaging'
  | 'testing'
  | 'completed'
  | 'failed';

export interface ResearchRequest {
  theme: string;
  description: string;
  mc_version: string;
  edition: Edition;
  style_preference: string;
  texture_resolution: number;
  include_pbr: boolean;
  include_animations: boolean;
  include_sounds: boolean;
  include_scripts: boolean;
}

export interface ResearchResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface GenerationRequest extends ResearchRequest {}

export interface GenerateResponse {
  job_id: string;
  status: GenerationStatus;
  message: string;
}

export interface StatusResponse {
  job_id: string;
  status: GenerationStatus;
  progress: number;
  current_step: string;
  step_details: string;
  error_message: string | null;
  logs: string[];
}

export interface ResultResponse {
  job_id: string;
  theme: string;
  mc_version: string;
  edition: string;
  bp_zip_path: string | null;
  rp_zip_path: string | null;
  mcaddon_path: string | null;
  mcpack_paths: string[];
  assets_count: {
    bp_entities: number;
    bp_items: number;
    bp_blocks: number;
    bp_scripts: number;
    rp_models: number;
    rp_textures: number;
    rp_animations: number;
  };
  generation_time_seconds: number;
  tokens_used: number;
  api_calls: number;
  estimated_cost_usd: number;
}

export interface ProvidersResponse {
  available: string[];
  details: Record<string, {
    enabled: boolean;
    model: string;
  }>;
}

export interface LoreEntity {
  name: string;
  display_name: string;
  description: string;
  role: string;
  abilities: string[];
  visual_description: string;
  size_category: string;
  biome_tags: string[];
  loot_drops: string[];
  health: number;
  damage: number;
  speed: number;
  is_tameable: boolean;
  is_rideable: boolean;
}

export interface LoreItem {
  name: string;
  display_name: string;
  description: string;
  item_type: string;
  rarity: string;
  abilities: string[];
  visual_description: string;
  durability: number;
  damage: number;
  cooldown: number;
  stack_size: number;
  crafting_materials: string[];
}

export interface LoreBlock {
  name: string;
  display_name: string;
  description: string;
  block_type: string;
  hardness: number;
  resistance: number;
  harvest_tool: string;
  harvest_level: number;
  light_level: number;
  visual_description: string;
  drops: string[];
}

export interface LoreBiome {
  name: string;
  display_name: string;
  description: string;
  temperature: number;
  humidity: number;
  features: string[];
  entities: string[];
  blocks: string[];
  is_dimension: boolean;
}

export interface LoreMechanic {
  name: string;
  description: string;
  implementation_hints: string[];
  related_entities: string[];
  related_items: string[];
}

export interface LoreData {
  universe_name: string;
  source_type: string;
  summary: string;
  entities: LoreEntity[];
  items: LoreItem[];
  blocks: LoreBlock[];
  biomes: LoreBiome[];
  mechanics: LoreMechanic[];
  references: string[];
  researched_at: string;
}
