# NeoPrompt — Prompt Engineering Console (V2)

A local middleware tool that transforms raw user requests into optimized, assistant-aware prompts tailored for different LLM assistants (ChatGPT, Claude, Gemini, DeepSeek) and categories (coding, science, psychology, law, politics).

## Features (V2)

- Local-First engine with optional LLM Assist (HF Serverless) for Editor/Critic
- PromptDoc IR + RulePacks + Operator Planner with explainability and quality scoring
- Strict JSON I/O for assist ops; fallback to offline baseline when assist is not superior
- Observability: engine_quality_score, structured logs with operator trace
- Configurable providers via configs/models.yaml; environment profiles via .env.local-hf or .env.local-only

- **Matrix-inspired UI**: Terminal console aesthetic with dark theme
- **Smart Prompt Engineering**: Applies deterministic operators based on assistant and category
- **Recipe System**: YAML-based prompt templates with hot-reload
- **Learning Optimizer**: ε-greedy algorithm that learns from your feedback
- **Privacy-First**: Local SQLite storage, optional text persistence
- **Optional Enhancement**: Local LLM for input clarification

## Architecture (Hexagonal)

Core (pure domain)
- engine/models (PromptDoc), rulepacks/, planner/, operators/, scoring/

Ports
- llm_provider, storage, cache, safety, events

Adapters
- providers (hf, tgi, ollama, openai, anthropic), storage (sqlite/postgres), cache (inmem/redis)

App shells
- api (FastAPI), cli (developer workflows), ui (single screen, optional)

```
Frontend (React + Vite + Tailwind)
  ├─ Console Input (terminal-like)
  ├─ Toolbar (Assistant, Category, Enhance toggle)
  ├─ Output Panel (Engineered Prompt + Copy, feedback buttons)
  ├─ History Panel (filters/search)
  └─ Settings (prompt templates viewer/hot-reload)

API (FastAPI)
  ├─ POST /engine/plan        -> resolve RulePacks and operator plan
  ├─ POST /engine/transform   -> produce HLEP, quality score, operator trace
  ├─ POST /engine/score       -> quality scorer only
  ├─ GET  /templates, /choose, /feedback, /diagnostics (core)
  ├─ (M3+) /replay, (M4+) /stress-test, (M5+) /optimize

Storage (SQLite via SQLAlchemy)
  ├─ decisions table
  └─ feedback table
```

## Development Setup (Local-First)

Run the following once to install the pinned Python (3.12.10) and Node (22) versions:

```bash
mise install
# if you see an "untrusted" warning, run:
mise trust .mise.toml
```

### Backend (API)
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optional dev tools
pip install -r requirements-dev.txt || true
python -c "from app.db import Base, engine; Base.metadata.create_all(engine); print('DB ready')"
uvicorn app.main:app --reload --port 7070
```

Logging
- Set LOG_LEVEL=DEBUG to increase verbosity.

Engine cache
- Caches packs/plan results; diagnostics available via /diagnostics.

Testing
```bash
# From repo root
pytest -q || python -m pytest -q
```

Scripts
- scripts/curl-examples.sh contains example curl commands (update to /engine/* as V2 endpoints come online).

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## Configuration (Profiles + Providers)

Environment variables and defaults

Profiles (choose one)
- .env.local-hf (MVP default)
  - APP_ENV=local
  - NO_NET_MODE=false
  - PROVIDER_ALLOWLIST=hf
  - EGRESS_ALLOWLIST=api-inference.huggingface.co,*.endpoints.huggingface.cloud
  - HF_TOKEN=***
  - LLM_ASSIST_ENABLED=true
  - MODEL_DEFAULT=hf/mistralai/Mistral-7B-Instruct-v0.3
- .env.local-only (strict)
  - APP_ENV=local
  - NO_NET_MODE=true
  - LLM_ASSIST_ENABLED=false

Providers (configs/models.yaml)
- Register provider base URLs and models (hf, tgi, ollama, openai, anthropic)

Core
- LOG_LEVEL, DATABASE_URL (sqlite by default), STORE_TEXT (default 0)
- Policy: provider/egress allowlists; violations return EGRESS_BLOCKED

## Diagnostics

- The backend maintains an in-memory cache of the last-known-good recipes (atomic snapshot).
- Default mode uses filesystem events to hot-reload recipe changes with debounce; it automatically falls back to mtime polling if events are unavailable.
- You can force a synchronous reload via the API.

Hot-reload modes and env vars
- RECIPES_RELOAD_MODE: events | poll | off (default: events)
- RECIPES_RELOAD_INTERVAL_SECONDS: polling interval in seconds (default: 5)
- RECIPES_DEBOUNCE_MS: debounce window for filesystem events in ms (default: 300)
- RECIPES_RECURSIVE: watch `recipes/**/*.yaml` recursively when set to 1 (default: 0)
- RECIPES_DIR: override prompt templates directory (default: repo prompt-templates/)

Force reload
```bash
curl -s 'http://127.0.0.1:7070/recipes?deps=true' | jq
```

You can also fetch diagnostics only:

```bash
curl -s 'http://127.0.0.1:7070/diagnostics' | jq
```

Diagnostics
- /engine/plan and /engine/transform return validation issues for schemas and JSON I/O
- Common error codes: ASSIST_JSON_INVALID, EGRESS_BLOCKED, ENGINE_VERIFY_FAILED (see NeoPrompt_TechSpecV2.md)

Observability
- Structured logs include operator trace and assist outcomes when enabled
- Prometheus metrics (exposed at `/metrics`):
  - `engine_quality_score{model,category}`
  - `http_requests_total{endpoint,status}`, `http_latency_seconds_bucket{endpoint}`

Manual test plan (quick)
- Events mode (macOS):
  - Edit a recipe in `recipes/*.yaml` and observe a single debounced reload in logs within ~500ms.
  - Introduce a YAML/schema error; last-known-good remains active; `/recipes` shows errors; fix and confirm recovery.
  - Use `curl -s 'http://127.0.0.1:7070/recipes?reload=true' | jq` for a manual reload.
- Poll mode:
  - Set `RECIPES_RELOAD_MODE=poll` and `RECIPES_RELOAD_INTERVAL_SECONDS=2`; edits are reflected within ~2s.

Notes
- Each process runs its own watcher; in multi-worker servers, each worker watches independently.
- For large recipe sets, keep `RECIPES_DEBOUNCE_MS` at a reasonable value to coalesce bursty edits.

## Editor Integration (VS Code)

- Generate a static JSON Schema file (docs/recipe.schema.json) or use the live endpoint.
- VS Code settings example (settings.json):

```json
{
  "yaml.schemas": {
    "./docs/recipe.schema.json": ["recipes/*.yaml"]
  }
}
```

## CLI Usage (will align with /engine/*)

Run a validation pass and print diagnostics:

```bash
PYTHONPATH=. .venv/bin/python -m backend.cli.recipes_validate --format json
```

Options:
- --format json|text (default text)
- --reload (force reload)
- --fail-on error|warning (exit non-zero if threshold met)

### Console CLI (neoprompt)

Interactive console-friendly wrapper around the API.

Examples:

```bash
# Help and health
scripts/neoprompt --help
scripts/neoprompt health

# Choose using stdin
echo "Write a haiku about the sea" | scripts/neoprompt choose --assistant chatgpt --category coding

# Choose with flags and interactive feedback prompt
scripts/neoprompt choose --assistant claude --category science --enhance --interactive

# Send feedback for a previous decision
scripts/neoprompt feedback --decision-id <ID> --reward 1
```

### SDKs

Python (editable install):

```bash
pip install -e sdk/python/neoprompt
python - <<'PY'
from neoprompt import Client
with Client() as c:
    print(c.health())
PY
```

TypeScript (build + use):

```bash
cd sdk/typescript
npm install
npm run build
node -e "import('./dist/index.js').then(async m => console.log(await new m.Client().health()))"
```

## What changed from v1 → v2

- Architecture: monolith → hexagonal (Core + Ports + Adapters)
- Recipes → PromptDoc + RulePacks
- Endpoints: /choose + /recipes → /engine/plan, /engine/transform, /engine/score
- LLM Assist default via HF Serverless; strict JSON I/O with fallback
- Security: provider/egress allowlists, NO_NET_MODE profile

## Milestones

- **M1 - Functional MVP**: Core prompt generation, copy functionality, basic feedback
- **M2 - Smart Enhancements**: Input enhancer, learning optimizer, JSON validation
- **M3 - Daily Comfort**: Hotkeys, history filters, desktop packaging (Tauri)

## Project Status

Note: Some V2 endpoints and infra (compose, configs/) may be introduced incrementally. Where references exist, they are marked as planned and will be added as the engine components land.

M0 complete baseline: two-container stack (api + nginx), env-driven CORS, health endpoints, schema endpoint, structured logging, rate-limit stub, CI updated.

## M0 Acceptance Checklist (run)

1) Bring up stack
- make build
- make up
- docker ps  # api and nginx should be healthy

2) Health & metrics
- curl -fsS http://localhost/healthz
- curl -fsS http://localhost/api/healthz
- curl -fsS http://localhost/api/metrics | head

3) Frontend (no dev server)
- open http://localhost/

4) API via Nginx proxy
- curl -fsS http://localhost/api/prompt-templates

5) Engine endpoints (as available)
- curl -fsS http://localhost/api/engine/plan -X POST -d '{"seed":"...","model":"...","category":"..."}'
- curl -fsS http://localhost/api/engine/transform -X POST -d '{"seed":"...","model":"...","category":"..."}'

6) CORS policy
- With CORS_ALLOW_ORIGINS=http://localhost, preflight from http://localhost succeeds
- In ENV=dev and empty CORS list, wildcard allowed

7) SQLite persistence (via volume)
- create decision via /choose, restart stack, verify in /history

8) Schema endpoint
- curl -fsS http://localhost/api/prompt-templates/schema | jq .title
