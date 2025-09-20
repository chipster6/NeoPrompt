# Personal Prompt Engineering Console — Technical Specification

**Status:** Draft v1 (personal, single-user)  
**Purpose:** A local app that rewrites and optimizes raw user requests into *engineered prompts* tailored to a chosen assistant (ChatGPT, Claude, Gemini, DeepSeek, etc.) and category (coding, science, psychology, law, politics). The app stores history, gathers feedback, and gradually learns which prompt “recipes” perform best for you.

---

## 0) Design Concept & Scope

### Concept
A middleware **prompt-engineering console** that sits between you and LLM assistants. You type a raw request into the console; it outputs a **clean, assistant-aware, domain-aware engineered prompt** you can paste (or send) to the assistant. It optionally uses a lightweight LLM to *enhance/clarify* your input before applying deterministic recipes.

### Scope (initial, personal-use)
- Single-user, local-first tool (no cloud accounts needed).
- Matrix-inspired UI/UX (terminal console aesthetic).
- Manual selection of **assistant** and **category** per prompt.
- **Recipe library** (YAML) defining assistant- and domain-specific best practices.
- **History** and **feedback** (👍/👎, copy events).
- **Lightweight optimizer** that prefers higher-scoring recipes over time.
- Optional **local enhancer model** (e.g., Flan‑T5) for paraphrase/clarification.
- Guardrails: JSON validation when requested; conservative settings for sensitive domains (law/medical).

### Out of scope (for now)
- Multi-user, accounts, billing, marketplace.
- Heavy analytics dashboards.
- Complex cloud telemetry or storing raw prompts by default (privacy-first).

---

## 1) User Workflow (Happy Path)

1. Choose **assistant** (e.g., Claude) and **category** (e.g., Coding).
2. Paste/type **raw input**.
3. (Optional) Enable **Enhance** → local/hosted LLM rewrites input for clarity (no change of intent).
4. Engine applies **operators** from a selected **recipe** (role header, constraints, formatting, examples, quality bar).
5. Console shows **engineered prompt** + **Copy** button.
6. You rate the result (👍/👎) and/or copy; feedback is stored.
7. Optimizer updates recipe preference for future runs (per assistant×category).

---

## 2) System Architecture (High Level)

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
  ├─ decisions(id, ts, assistant, category, context, recipe_id, hparams, propensity, [raw_input?], [engineered_prompt?])
  └─ feedback(decision_id, reward, components, safety_flags)

Recipes (YAML on disk)
  └─ assistant×category profiles, hot-reloadable
```

**Packaging (optional later):** Tauri (preferred) or Electron for a desktop app icon.

---

## 3) Core Data Contracts (API)

### POST `/choose`
**Request**
```json
{
  "assistant": "chatgpt",
  "category": "coding",
  "raw_input": "Write a Python function to merge two sorted lists.",
  "options": { "enhance": true, "force_json": false },
  "context_features": { "input_tokens": 16, "lang": "en" }
}
```
**Response**
```json
{
  "decision_id": "uuid",
  "recipe_id": "chatgpt.coding.basic",
  "engineered_prompt": "You are an expert software engineer...",
  "operators": ["role_hdr","constraints","io_format","quality_bar"],
  "hparams": { "temperature": 0.2, "top_p": 0.9, "max_tokens": 1200 },
  "propensity": 0.9,
  "notes": ["enhanced=true","json_validation=false"]
}
```

### POST `/feedback`
**Request**
```json
{
  "decision_id": "uuid",
  "reward_components": { "user_like": 1, "copied": 1, "format_ok": 1 },
  "reward": 1.0,
  "safety_flags": []
}
```
**Response**: `{"ok": true}`

### GET `/history?limit=50&assistant=chatgpt&category=coding&with_text=false`
Returns list of past decisions (optionally include stored text).

### GET `/recipes`
Returns parsed recipes and validation errors.

---

## 4) Database Schema (SQLite)

**decisions**
- id TEXT PK
- ts DATETIME
- assistant TEXT
- category TEXT
- context JSON
- recipe_id TEXT
- hparams JSON
- propensity REAL
- raw_input TEXT *(optional; default off)*
- engineered_prompt TEXT *(optional; default off)*

**feedback**
- decision_id TEXT PK (FK decisions.id)
- ts DATETIME
- reward REAL [0..1]
- components JSON
- safety_flags JSON

Privacy-first: by default, do **not** store raw_input/engineered_prompt text; enable via settings if you want searchable history.

---

## 5) Recipe Library (YAML)

**Schema**
```yaml
id: "<assistant>.<category>.<name>"
assistant: "chatgpt|claude|gemini|deepseek"
category: "coding|science|psychology|law|politics"
operators: [role_hdr, constraints, io_format, quality_bar]  # order matters
hparams: { temperature: 0.2, top_p: 0.9, max_tokens: 1200 }
guards: { max_temperature: 0.4 }
examples: []   # optional few-shot blocks or file references
```

**Example – `recipes/chatgpt.coding.basic.yaml`**
```yaml
id: chatgpt.coding.basic
assistant: chatgpt
category: coding
operators: [role_hdr, constraints, io_format, quality_bar]
hparams: { temperature: 0.2, top_p: 0.9, max_tokens: 1200 }
guards: { max_temperature: 0.4 }
examples: []
```

### Baseline coverage (v1)
- Assistants: chatgpt, claude, gemini, deepseek
- Categories: coding, science, psychology, law, politics
- For every assistant×category pair, at least one baseline recipe exists (suffix `.baseline` where applicable) to prevent “No recipes available for the given assistant/category”.
- Safety defaults:
  - law: guards.max_temperature ≤ 0.3 (also capped at runtime by `apply_domain_caps`)
  - psychology, politics: guards.max_temperature ≤ 0.35
  - science, coding: guards.max_temperature ≤ 0.4

Existing examples include:
- `recipes/chatgpt.coding.basic.yaml`
- `recipes/claude.coding.strict.yaml`
- `recipes/chatgpt.science.explainer.yaml`
…plus baseline files for all other assistant×category pairs.

---

## 6) Operators (Deterministic Building Blocks)

1) **role_hdr**  
```
You are an expert in {category}. Provide precise, correct, concise answers.
```

2) **constraints**  
- No hidden chain-of-thought.  
- Prefer stepwise explanations for non-trivial tasks.  
- Cite sources if making factual claims.  
- If coding, include runnable examples when feasible.

3) **io_format**  
- If JSON requested → define minimal schema and require *valid JSON only*.  
- Else enforce Markdown sections: **TASK**, **ASSUMPTIONS**, **ANSWER** (or domain-appropriate headings).

4) **examples** *(optional)*  
- k=1–2 few-shot snippets from a per-category library.

5) **quality_bar**  
- “Answer must be correct, complete, minimal; address edge cases when relevant.”

---

## 7) Optimizer (Lightweight, Online)

- For each (assistant, category), maintain average **reward** per recipe.
- **Reward** = mean of available signals in [0,1], e.g.:
  - `user_like` (👍=1, 👎=0)
  - `copied` (1 if copied, else 0)
  - `format_ok` (1 if JSON/Markdown validates when requested, else 0)
- Selection policy = **ε-greedy**:
  - ε = 0.10 → 10% random exploration across eligible recipes.
  - 90% choose the **highest average reward** recipe.
- Safety: if last 3 rewards for a recipe < 0.2 → temporarily exclude (20 decisions).

*(Later upgrade to contextual bandit or LinTS if desired.)*

---

## 8) Enhancer (Optional LLM Rewriter)

**Purpose:** rewrite raw input for clarity/structure without changing intent.  
**Local model:** `flan-t5-base` via HuggingFace (CPU/GPU).  
**Hosted fallback:** small, inexpensive model (e.g., gpt‑4o‑mini) with system prompt:

```
Rewrite the user's request for {assistant}, category={category}. 
Clarify and structure the request without adding new content.
```

Latency fallback: if local model > threshold, skip or use hosted.

---

## 9) Guardrails

- **Domain caps:** for `law` and `medical`, enforce `temperature ≤ 0.3` and require citations when appropriate.
- **Schema validation:** if JSON requested, validate; attempt one auto-repair; only then mark `format_ok=1`.
- **Injection hygiene:** strip phrases like “ignore previous instructions” from enhancer output.

---

## 10) Frontend Specs (Minimum)

- **Console**: multiline textarea, token estimate, hotkeys (Ctrl/⌘+Enter to generate).
- **Toolbar**: assistant, category, enhance toggle.
- **OutputPanel**: engineered prompt (monospace); buttons: **Copy**, **👍**, **👎**; chips for recipe id/operators.
- **HistoryList**: time, assistant, category, recipe, reward; filters by assistant/category; optional text search if storing text.
- **Theme**: dark + green accents; simple “code rain” background via CSS.

---

## 11) Project Structure

```
project/
├─ recipes/
│  ├─ chatgpt.coding.basic.yaml
│  ├─ chatgpt.science.explainer.yaml
│  ├─ claude.coding.strict.yaml
│  └─ gemini.psychology.coach.yaml
├─ backend/
│  ├─ requirements.txt
│  └─ app/
│     ├─ main.py          # FastAPI routes (choose, feedback, history, recipes)
│     ├─ schemas.py       # Pydantic contracts
│     ├─ db.py            # SQLAlchemy models + init_db
│     ├─ recipes.py       # YAML loader + validator
│     ├─ engine.py        # operator implementations
│     ├─ optimizer.py     # ε-greedy selector
│     ├─ enhancer.py      # optional local/hosted rewriter
│     └─ guardrails.py    # validators, caps
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.ts
│  └─ src/
│     ├─ App.tsx
│     ├─ components/
│     │  ├─ Console.tsx
│     │  ├─ OutputPanel.tsx
│     │  └─ HistoryList.tsx
│     └─ lib/api.ts
└─ console.sqlite
```

---

## 12) Local Bring‑Up (Dev)

**Backend**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy pydantic pyyaml python-dotenv
python - <<'PY'
from backend.app.db import Base, engine
Base.metadata.create_all(engine)
print("DB ready")
PY
uvicorn backend.app.main:app --reload --port 7070
```

**Frontend**
```bash
cd frontend
npm i
npm run dev
# open http://localhost:5173
```

*(Optional) One-command launcher:* create a small shell script that runs both servers, or later wrap with **Tauri** for a desktop icon/app.

---

## 13) Hosting Paths (if you go web‑based)

**Option A — Vercel (frontend) + Render (backend)**  
- Frontend: Vercel (static).  
- Backend: Render Web Service (Docker).  
- Set `VITE_API_BASE` to the backend URL (e.g., `https://api.yourdomain.com`).

**Option B — VPS (Docker Compose + Caddy)**  
- One VM, run Caddy reverse proxy for TLS + static.  
- Containers: `frontend` (static build) and `backend` (Uvicorn).  
- Domain: `https://prompt.yourdomain.com` with `/api` → backend.

*(Fly.io is another managed single‑app alternative.)*

---

## 14) Milestones & Definitions of Done

**M1 — Functional MVP**
- Generate engineered prompts from YAML recipes.
- Copy button works; p95 latency < 1s without enhancer.
- Feedback posts to `/feedback`; average reward computed.
- Recipes hot‑reload with validation; invalid files don’t crash app.

**M2 — Smart Enhancements**
- Enhancer toggle works (local or hosted).
- Optimizer shifts preference after ~10–20 interactions.
- JSON validation and simple auto‑repair in place.

**M3 — Daily Comfort**
- Hotkeys, history filters, token estimate.
- Optional text storage for searchable history.
- Ready for packaging (Tauri) if you want a desktop icon.

---

## Milestones M3–M5 (Advanced Features)

### Milestone M3 — Control-Layer Simulation & Replay
- Extend `Run` records to capture full environment context (model version, flags, operator chain, user state).
- API Endpoints:
  - `POST /replay {run_ids[], target_model}` → re-executes runs against new model, linking results to originals.
  - `GET /replay-results?orig_run_id=` → shows diffs and drift metrics.
- Diff Engine: sentence-level, character-level, and Jaccard/cosine similarity scores.
- CLI: `replay` option to select past runs, target model, and display side-by-side results.
- Metrics: drift percentages, replay counts, regression indicators.

### Milestone M4 — Dynamic Prompt Stress-Testing Engine
- Generate adversarial, malformed, and edge-case inputs automatically.
- API Endpoints:
  - `POST /stress-test {template_id, profile}` → runs a set of adversarial cases.
  - `GET /stress-results?profile_id=` → retrieves summary of pass/fail rates by case type.
- Schema:
  - `StressProfile(id, template_id, params(json), created_at)`
  - `StressResult(profile_id, run_id, case_type, pass_fail, error_msg, latency_ms)`
- CLI: `stress` option to run predefined profiles and print a fail matrix.
- CI/CD: Hook into pipelines (pytest/gh actions) to block merges on failures.
- Metrics: injection resistance scores, SLA violations, robustness indexes.

### Milestone M5 — Automated Prompt Optimizer with Explainable Operators
- Each operator tagged with: intent, rationale, deterministic flag, expected effect.
- API Endpoints:
  - `POST /optimize {template_id, targets:[clarity, bias, compression]}` → suggests improved prompts with explanations and diffs.
  - `POST /optimize/accept {opt_result_id}` → saves approved optimization as a new version with provenance.
- Schema:
  - `OptimizationResult(id, template_id, targets[], diffs[], rationale, created_at)`
- CLI: `optimize` command to preview, accept, or reject operator suggestions.
- Governance: Enterprise mode can enforce required operators before publishing.

---