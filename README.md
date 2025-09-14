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
python -c "from app.db import Base, engine; Base.metadata.create_all(engine); print('DB ready')"
uvicorn app.main:app --reload --port 7070
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## Hot Reload and Recipe Diagnostics

- The backend maintains an in-memory cache of the last-known-good recipes.
- Editing YAML files under `recipes/` is picked up automatically via mtime checks.
- You can force a synchronous reload with:

```bash
curl -s 'http://127.0.0.1:7070/recipes?reload=true' | jq
```

- The `/recipes` endpoint returns both parsed recipes and validation errors/warnings with fields:
  - `file_path`, `error`, `line_number` (when available), and `error_type` (`yaml_parse`, `schema_validation`, `semantic_validation`).
- If no valid recipes are available, `/choose` responds with a structured 503:

```json
{"detail": {"code": "recipes_unavailable", "message": "No valid recipes available, see /recipes for details"}}
```

## Milestones

- **M1 - Functional MVP**: Core prompt generation, copy functionality, basic feedback
- **M2 - Smart Enhancements**: Input enhancer, learning optimizer, JSON validation
- **M3 - Daily Comfort**: Hotkeys, history filters, desktop packaging (Tauri)

## Project Status

🚧 **Under Development** - Currently building M1 MVP
