# Addon Generator API v2 - Architecture Documentation

## Overview

The v2 architecture transforms the addon generator into a **self-evolving, multi-agent orchestration platform** with:

- **Deep Lore Research** (50+ virtual PDFs per work)
- **Git-like Version Control** for addon iterations
- **Feedback Loops** for canon correction and iteration
- **Device-Tier Optimization** (32-bit/2GB → 64-bit/8GB+)
- **Community Learning** from GitHub addons
- **Professional Assets**: PBR textures, 3D models, custom UI, particles, sound
- **Dynamic LangGraph** with parallel execution and human checkpoints

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ADDON GENERATOR API v2                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐  │
│  │   FRONTEND       │    │   API GATEWAY    │    │   JOB QUEUE          │  │
│  │   (Next.js PWA)  │◄──►│   (FastAPI)      │◄──►│   (BullMQ/Redis)     │  │
│  └──────────────────┘    └────────┬─────────┘    └──────────────────────┘  │
│                                   │                                         │
│         ┌─────────────────────────┼─────────────────────────┐              │
│         ▼                         ▼                         ▼              │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐       │
│  │  RESEARCH   │          │  GENERATION │          │  EVOLUTION  │       │
│  │  PHASE      │          │  PHASE      │          │  PHASE      │       │
│  ├─────────────┤          ├─────────────┤          ├─────────────┤       │
│  │ • DeepResearcher    │  │ • EntityDesigner   │  │ • VersionMgr   │       │
│  │ • CanonValidator    │  │ • ItemDesigner     │  │ • PerfOptimizer│       │
│  │ • MCSchemaExpert    │  │ • BlockDesigner    │  │ • FeedbackLoop │       │
│  │ • CommunityLearner  │  │ • ScriptEngineer   │  │ • Rollback/Tag │       │
│  └─────────────┘          │ • TextureSynth     │  └─────────────┘       │
│                           │ • ModelGenerator   │                         │
│                           │ • UIDesigner       │                         │
│                           │ • AnimationDesigner│                         │
│                           │ • ParticleDesigner │                         │
│                           │ • SoundDesigner    │                         │
│                           │ • AddonPackager    │                         │
│                           └─────────────┘          ┌─────────────┐       │
│                                                    │  PACKAGING  │       │
│                                                    │  .mcaddon   │       │
│                                                    │  .zip       │       │
│                                                    │  Preview    │       │
│                                                    │  Changelog  │       │
│                                                    └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8 Specialized Agents

| Agent | Responsibility | Key Features |
|-------|---------------|--------------|
| **LoreDeepResearcher** | 50+ source aggregation | Wiki, Fandom, Reddit, official sources → 50 structured JSON domains |
| **CanonValidator** | Fact-checking | Canon hierarchy, chapter citations, contradiction resolution |
| **MCSchemaExpert** | Schema authority | Auto-sync from GitHub, validation, migration, generation hints |
| **CommunityLearner** | Pattern extraction | Weekly GitHub scan of top 100 addons, pattern database |
| **ProjectArchitect** | Master planning | DAG creation, parallel groups, performance budgets |
| **PerformanceOptimizer** | Device-tier optimization | 3 profiles, texture atlasing, LOD, entity culling |
| **TextureSynthesizer** | PBR texture generation | 7 styles, full PBR maps, atlasing, itzriyo157-style UI |
| **ModelGenerator** | 3D model generation | Blockbench geo.json, LOD, bone merging, animation-ready |
| **UIDesigner** | Custom UI | Radial menus, HUDs, gesture zones, animated buttons |
| **AnimationDesigner** | Molang animations | Blend trees, procedural+keyframe, particle integration |
| **ParticleDesigner** | Custom particles | Shader effects, physics, molang-driven, performance budgets |
| **SoundDesigner** | Immersive audio | 3D positional, layered events, music system |
| **AddonPackager** | Final packaging | .mcaddon/.zip, manifests, preview, changelog, README |

---

## Version Control System

### Version Structure
```
AddonProject/
├── versions/
│   ├── v0.0.1/          # Initial generation
│   │   ├── manifest.json
│   │   ├── BP/, RP/
│   │   ├── preview.png
│   │   └── changelog.md
│   ├── v0.0.2/          # User feedback: "fix shadow blade damage"
│   └── v0.0.3/          # Auto-optimization: "reduced texture memory 40%"
├── lore/                # 50+ PDF research cache
└── learning/            # Community patterns
```

### Version Operations
- **Create**: `POST /versions/{job_id}` - New iteration with changelog
- **Rollback**: `POST /versions/{job_id}/rollback` - Restore previous version
- **Diff**: `GET /versions/{job_id}/diff?from=v1&to=v2` - Asset/performance diff
- **Tag**: `POST /versions/{job_id}/tag` - Git-like tags (v1.0-release)
- **Branch**: `POST /versions/{job_id}/branch` - Experimental branches
- **Merge**: Auto-merge with conflict detection
- **Export**: `POST /versions/{job_id}/export` - Standalone addon files

---

## Device Tier Optimization

| Tier | Device | RAM Budget | Texture Res | PBR | LOD | Max Entities | Max Particles |
|------|--------|------------|-------------|-----|-----|--------------|---------------|
| **Low** | 32-bit, 2GB | 50 MB | 32px | ❌ | ✅ | 20 | 30 |
| **Mid** | 64-bit, 4GB | 150 MB | 64px | ✅ | ✅ | 50 | 100 |
| **High** | 64-bit, 8GB+ | 300 MB | 128px | ✅ | ❌ | 100 | 300 |

**Auto-optimization techniques:**
- Texture atlasing (combine multiple textures)
- Resolution scaling per tier
- PBR map removal for low tier
- Model simplification (polygon reduction, bone merging)
- LOD generation (3 levels)
- Entity culling (distance-based despawning)
- Particle budget limiting
- Script minification and object pooling

---

## Feedback & Iteration Loop

```mermaid
graph LR
    A[User plays v0.0.1] --> B{Issue found?}
    B -->|Canon error| C[POST /feedback - CANON_CORRECTION]
    B -->|Balance| C
    B -->|Bug| C
    B -->|Performance| C
    C --> D[FeedbackProcessor analyzes]
    D --> E[Creates v0.0.2 with fixes]
    E --> F[User tests v0.0.2]
    F --> G{Resolved?}
    G -->|Yes| H[Mark feedback resolved]
    G -->|No| C
```

### Feedback Types
- `CANON_CORRECTION` - "Novel says X, not Y" (auto-triggers iteration)
- `BALANCE_CHANGE` - "Too OP/weak"
- `BUG_REPORT` - "Crashes when..."
- `FEATURE_REQUEST` - "Add Z mechanic"
- `STYLE_ADJUSTMENT` - "Make it more anime"
- `PERFORMANCE_ISSUE` - "Lags on my phone"
- `UI_UX_ISSUE` - "Button hard to reach"

---

## API Endpoints Summary

### Research & Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research` | Deep research only (50+ domains) |
| POST | `/generate` | Full generation with versioning |
| GET | `/status/{job_id}` | Current status + version history |
| GET | `/stream/{job_id}` | SSE real-time updates |
| GET | `/result/{job_id}` | Final result with all versions |
| GET | `/download/{job_id}/{type}` | Download .mcaddon/.zip |

### Version Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/versions/{job_id}` | List all versions |
| GET | `/versions/{job_id}/{version}` | Version details |
| POST | `/versions/{job_id}` | Create new version |
| POST | `/versions/{job_id}/rollback` | Rollback to version |
| GET | `/versions/{job_id}/diff` | Diff between versions |
| POST | `/versions/{job_id}/tag` | Tag version |
| GET | `/versions/{job_id}/tree` | Version tree visualization |
| POST | `/versions/{job_id}/export` | Export standalone |

### Feedback & Iteration
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/feedback/{job_id}` | Add user feedback |
| GET | `/feedback/{job_id}` | List feedback |
| POST | `/feedback/{job_id}/resolve` | Mark resolved |

### Performance & Optimization
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/performance/{job_id}` | Performance profiles |
| POST | `/optimize/{job_id}` | Re-optimize for tiers |

### Lore & Research
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lore/{job_id}` | Researched lore data |
| GET | `/lore/{job_id}/canon-validation` | Canon validation report |
| GET | `/lore/{job_id}/minecraft-mapping` | MC translation map |

### Community & Learning
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/community/patterns` | Learned patterns |
| POST | `/community/sync` | Trigger GitHub sync |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/providers` | LLM provider status |
| GET | `/schemas` | Bedrock schemas |
| POST | `/cleanup/{job_id}` | Cleanup old versions |

---

## Data Models

### ResearchRequest (v2)
```json
{
  "theme": "Shadow Slave",
  "description": "Focus on Shadow Cores and Memories",
  "mc_version": "26.40",
  "edition": "bedrock",
  "style": "vanilla_plus",
  "texture_resolution": 64,
  "include_pbr": true,
  "include_animations": true,
  "include_models": true,
  "include_sounds": false,
  "include_scripts": true,
  "include_particles": true,
  "include_ui": true,
  "target_tiers": ["low_32bit_2gb", "mid_64bit_4gb", "high_64bit_8gb"],
  "faithfulness": 0.85,
  "reference_images": []
}
```

### VersionedAddonState (Key Fields)
```python
class VersionedAddonState(AddonState):
    versions: dict[str, AddonVersion]      # All versions
    current_version: str                   # Active version
    version_history: list[str]             # Ordered history
    branches: dict[str, str]               # branch -> head version
    all_feedback: list[UserFeedback]       # Global feedback
    learned_patterns: dict                 # Community patterns
    target_tiers: list[DeviceTier]         # Optimization targets
    generation_config: dict                # Faithfulness, refs, etc.
```

---

## Deployment

### Environment Variables
```env
# LLM Providers (at least one required)
OPENROUTER_API_KEY=sk-...
GROQ_API_KEY=gsk_...
TOGETHER_API_KEY=...
GOOGLE_API_KEY=...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
DEEPSEEK_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434

# Database (PlanetScale recommended)
DATABASE_URL=mysql://user:pass@host/db

# Redis (BullMQ queue)
REDIS_URL=redis://localhost:6379/0

# GitHub (for community learner)
GITHUB_TOKEN=ghp_...

# Storage (S3/R2 for .mcaddon files)
S3_ENDPOINT=https://...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=addon-packages
```

### Deploy Commands
```bash
# Backend (Railway/Render/Fly.io)
cd addon-api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (Vercel)
cd addon-generator
npm install
npm run build
vercel deploy
```

---

## Frontend Integration (Next.js)

### Key Components to Add
```tsx
// Version Timeline
<VersionTimeline 
  versions={job.versionHistory} 
  currentVersion={job.currentVersion}
  onVersionClick={loadVersion}
  onDiffClick={showDiff}
/>

// Feedback Panel
<FeedbackPanel
  feedback={version.feedback}
  onAddFeedback={addFeedback}
  onResolve={resolveFeedback}
/>

// Performance Dashboard
<PerformanceDashboard
  profiles={version.performanceProfiles}
  targetTier={selectedTier}
/>

// Lore Explorer (50 domains)
<LoreExplorer
  domains={lore.references}
  onDomainClick={showDomainDetails}
/>

// Real-time Generation Stream
<GenerationStream
  jobId={jobId}
  onUpdate={setStatus}
/>
```

---

## Extending the System

### Adding New Agents
1. Create `addon-api/agents/new_agent.py` with async `process(state)` method
2. Register in `addon-api/agents/__init__.py`
3. Add node to `orchestration/graph_v2.py` in `_register_agents()`
4. Add to execution plan in `_create_execution_plan()`

### Custom Texture Styles
```python
# In TextureSynthesizer._load_style_prompts()
TextureStyle.CUSTOM_STYLE: "Your custom style description...",
```

### Custom UI Themes
```python
# In UIDesigner._analyze_ui_needs()
specs.append(UISpec(
    name="custom_theme_button",
    ui_type="button",
    theme="my_custom_theme",
    color_palette=["#hex1", "#hex2"],
))
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No LLM providers available" | Set at least one API key in env |
| "Schema validation failed" | Run `GET /schemas` to sync latest |
| "Generation timeout" | Increase `timeout_seconds` in node config |
| "Out of memory" | Reduce texture resolution or enable atlasing |
| "GitHub rate limited" | Add `GITHUB_TOKEN` for higher limits |

### Debug Endpoints
- `GET /health` - System status
- `GET /providers` - LLM connectivity
- `GET /schemas` - Schema sync status
- Job logs in `/status/{job_id}` response

---

## Roadmap

### Phase 2 (Next)
- [ ] WebSocket real-time collaboration
- [ ] Multi-user workspaces
- [ ] Marketplace integration
- [ ] Automated testing on device farm
- [ ] Visual diff viewer in UI

### Phase 3 (Future)
- [ ] AI-generated music/sound
- [ ] Natural language addon editing
- [ ] Cross-edition sync (Bedrock ↔ Java)
- [ ] Modpack generation
- [ ] Server-side addon hosting

---

## License

MIT - Use freely for personal or commercial projects.
