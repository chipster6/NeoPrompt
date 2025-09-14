# Personal Prompt Engineering Console

A local middleware tool that transforms raw user requests into optimized, assistant-aware prompts tailored for different LLM assistants (ChatGPT, Claude, Gemini, DeepSeek) and categories (coding, science, psychology, law, politics).

## Features

- **Matrix-inspired UI**: Terminal console aesthetic with dark theme
- **Smart Prompt Engineering**: Applies deterministic operators based on assistant and category
- **Recipe System**: YAML-based prompt templates with hot-reload
- **Learning Optimizer**: ε-greedy algorithm that learns from your feedback
- **Privacy-First**: Local SQLite storage, optional text persistence
- **Optional Enhancement**: Local LLM for input clarification

## Architecture

```
Frontend (React + Vite + Tailwind)
  ├─ Console Input (terminal-like)
  ├─ Toolbar (Assistant, Category, Enhance toggle)
  ├─ Output Panel (Engineered Prompt + Copy, feedback buttons)
  ├─ History Panel (filters/search)
  └─ Settings (recipes viewer/hot-reload)

Backend (FastAPI, Python 3.12)
  ├─ /choose      -> select recipe, (optional) enhance input, build engineered prompt
  ├─ /feedback    -> record reward components + aggregate reward
  ├─ /history     -> list recent decisions (with/without text)
  ├─ /recipes     -> list recipes and validation errors
  ├─ engine.py    -> deterministic operators
  ├─ optimizer.py -> ε-greedy scorer per assistant×category
  ├─ enhancer.py  -> optional local/hosted LLM rewriter
  └─ guardrails.py-> JSON/schema validation; domain caps (law/medical)

Storage (SQLite via SQLAlchemy)
  ├─ decisions table
  └─ feedback table
```

## Development Setup

Run the following once to install the pinned Python (3.12.10) and Node (22) versions:

```bash
mise install
# if you see an "untrusted" warning, run:
mise trust .mise.toml
```

### Backend
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

Recipes cache
- Cached in-memory; GET /recipes?reload=true forces a refresh.

Testing
```bash
# From repo root
pytest -q || python -m pytest -q
```

Scripts
- scripts/curl-examples.sh contains example curl commands for local verification.

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## Hot Reload and Recipe Diagnostics

- The backend maintains an in-memory cache of the last-known-good recipes (atomic snapshot).
- Default mode uses filesystem events to hot-reload recipe changes with debounce; it automatically falls back to mtime polling if events are unavailable.
- You can force a synchronous reload via the API.

Hot-reload modes and env vars
- RECIPES_RELOAD_MODE: events | poll | off (default: events)
- RECIPES_RELOAD_INTERVAL_SECONDS: polling interval in seconds (default: 5)
- RECIPES_DEBOUNCE_MS: debounce window for filesystem events in ms (default: 300)
- RECIPES_RECURSIVE: watch `recipes/**/*.yaml` recursively when set to 1 (default: 0)
- RECIPES_DIR: override recipes directory (default: repo recipes/)

Force reload
```bash
curl -s 'http://127.0.0.1:7070/recipes?reload=true' | jq
```

You can also fetch diagnostics only:

```bash
curl -s 'http://127.0.0.1:7070/diagnostics' | jq
```

Diagnostics
- The `/recipes` endpoint returns both parsed recipes and validation errors/warnings with fields:
  - `file_path`, `error`, `line_number` (when available), `error_type` (`yaml_parse`, `schema_validation`, `semantic_validation`), and `severity` (`error` or `warning`).
- It also returns a `meta` section:
  - `reload_mode`, `dir`, and other runtime details.
- If no valid recipes are available, `/choose` responds with a structured 503:

```json
{"detail": {"code": "recipes_unavailable", "message": "No valid recipes available, see /recipes for details"}}
```

Observability
- Logs include structured messages for reloads: outcome, reason, files scanned, valid/error counts, and duration.
- Prometheus metrics (exposed at `/metrics`):
  - `neopr_recipes_reload_total{outcome,reason}`
  - `neopr_recipes_reload_duration_seconds`
  - `neopr_recipes_valid_count`, `neopr_recipes_error_count`

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

## CLI Usage

Run a validation pass and print diagnostics:

```bash
PYTHONPATH=. .venv/bin/python -m backend.cli.recipes_validate --format json
```

Options:
- --format json|text (default text)
- --reload (force reload)
- --fail-on error|warning (exit non-zero if threshold met)

## Milestones

- **M1 - Functional MVP**: Core prompt generation, copy functionality, basic feedback
- **M2 - Smart Enhancements**: Input enhancer, learning optimizer, JSON validation
- **M3 - Daily Comfort**: Hotkeys, history filters, desktop packaging (Tauri)

## Project Status

🚧 **Under Development** - Currently building M1 MVP
