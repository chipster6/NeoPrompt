# Prompt Engineering Console (NeoPrompt) — Technical Specification

**Profile:** Local-First (MVP) with **Hugging Face Assist** (Editor & Critic) as default

---

## 0) Purpose & Scope
- **Goal:** Convert a raw **seed prompt** into a **High-Level Engineered Prompt (HLEP)** that maximizes **precision, clarity, and actionability**, tailored by **Model** and **Category** via **RulePacks + Operators**.
- **Core capabilities:** Deterministic **Prompt Engineering Engine** (RulePacks + Operators) with **explainability**, **quality scoring**, **replay (M3)**, **stress-testing (M4)**, **explainable optimizer (M5)**.
- **LLM Assist (default MVP):** **Hugging Face Serverless Inference** for **Editor & Critic**; local-only and other providers remain optional via config.

---

## 1) Architecture (Hexagonal / Ports & Adapters)

- **Core (pure domain, testable):**
  - `engine/`: PromptDoc IR, RulePack resolver & merge, operator planner, operators (offline + LLM-assisted wrappers), scoring & validators.
- **Ports (interfaces):**
  - `LLMProvider` (Editor/Critic/Scorer), `Storage`, `Cache`, `SafetyClassifier`, `EventBus` (optional).
- **Adapters (plug-ins):**
  - Providers: `hf` (Serverless), `tgi` (OpenAI-compatible), `ollama` (local), `openai`, `anthropic`.
  - Storage: `sqlite`, `postgres`. Cache: `inmem`, `redis`. Safety: `llama_guard` (optional).
- **App shells:** `api/` (FastAPI), `cli/` (developer workflows), optional `ui/` (single screen).

> **Dependency rule:** App shells → Core + Ports. Adapters → Ports. No adapter↔adapter coupling.

---

## 2) Repository Layout

```
neoprompt/
  engine/
    models/        # PromptDoc IR, DTOs
    rulepacks/     # loaders, registries, merge rules
    planner/       # derives operator plan
    operators/     # offline + LLM-assisted (wrappers over LLMProvider)
    scoring/       # quality signals, checks
  ports/
    llm_provider.py
    storage.py
    cache.py
    safety.py
    events.py
  adapters/
    providers/     # hf_serverless_adapter.py, tgi_adapter.py, ollama_adapter.py, ...
    storage/       # sqlite_repo.py, postgres_repo.py
    cache/         # inmem_cache.py, redis_cache.py
    safety/        # llama_guard.py
  api/
    main.py
    routes/engine.py        # /engine/*
    routes/core.py          # /templates, /choose, /feedback, ...
    routes/advanced.py      # /replay, /stress-test, /optimize
    deps.py                 # DI wiring
  cli/
    __main__.py
    commands/*.py
  ui/                       # optional MVP screen
  configs/
    models.yaml
    categories.yaml
    rulepacks/*.yaml
    appsettings.*.yaml
  infra/
    compose/                # docker-compose profiles
    k8s/                    # kustomize base/overlays
```

---

## 3) Contracts (stable interfaces)

### 3.1 LLMProvider

```python
class ChatMessage(TypedDict):
    role: Literal["system","user","assistant"]
    content: str

class CompletionResult(TypedDict):
    text: str
    tokens_prompt: int
    tokens_completion: int
    duration_ms: int
    model_id: str
    cost_usd: float

class LLMProvider(Protocol):
    def chat(self, messages: list[ChatMessage], *,
             model: str, temperature: float = 0.2, max_tokens: int = 1024,
             stop: list[str] | None = None, json_mode: bool = False) -> CompletionResult: ...
```

### 3.2 Storage (CRUD summarized)

```python
class Storage(Protocol):
    def create_template(self, t: Template) -> Template: ...
    def get_template(self, id: str) -> Template | None: ...
    def list_templates(self, **filters) -> list[Template]: ...
    def save_engine_transform(self, e: EngineTransform) -> EngineTransform: ...
    # ...Runs, Feedback, Replay, Stress, Optimization CRUD...
```

### 3.3 SafetyClassifier

```python
class SafetyClassifier(Protocol):
    def check(self, text: str) -> dict[str, float]  # label -> score
```

---


## 4) Data Model (SQLModel/SQLAlchemy)

```
Template(id PK, name, version, body TEXT, tags JSONB, created_at, updated_at);
Run(id PK, template_id FK NULL, input JSONB, output JSONB, env JSONB, latency_ms INT, status TEXT, created_at);
Feedback(id PK, run_id FK, rating INT, notes TEXT, labels JSONB, created_at);

EngineTransform(id PK, seed_hash TEXT, model TEXT, category TEXT,
  packs_applied JSONB, operator_plan JSONB, hlep TEXT, quality JSONB, created_at);

RulePack(id PK, type TEXT, priority INT, blob JSONB, created_at);
GlossaryTerm(term TEXT PK, canonical TEXT, aliases JSONB);

ReplayRun(id PK, orig_run_id FK, new_run_id FK, drift_metrics JSONB, created_at);

StressProfile(id PK, template_id FK NULL, params JSONB, created_at);
StressResult(id PK, profile_id FK, run_id FK, case_type TEXT, pass_fail BOOL, error_msg TEXT, latency_ms INT, created_at);

OptimizationResult(id PK, template_id FK, targets JSONB, diffs JSONB, rationale TEXT, created_at);

Indexes: (Template.name, version), Run.created_at, EngineTransform.seed_hash, StressResult.case_type.
```

---

## 5) Prompt Engineering Engine

### 5.1 PromptDoc (IR)

```json
{
  "seed": "string",
  "model": "string",
  "category": "string",
  "context": { "project": "", "org": "", "user": "" },
  "packs_applied": ["pack.global.v1","pack.model.v1","pack.category.vN"],
  "sections": {
    "goal": "", "inputs": [], "constraints": [], "steps": [],
    "acceptance_criteria": [], "io_format": "markdown",
    "examples": [{"input":"","output":""}]
  },
  "meta": {
    "assumptions": [], "open_questions": [],
    "rationales": [{"operator":"clarify","why":""}],
    "quality": {"score":0,"signals":{"specificity":0,"structure":0,"ambiguity_inverse":0,"actionability":0,"consistency":0}}
  }
}
```

### 5.2 RulePacks (declarative)

- **Types:** global, model, category, org, project, user  
- **Merge:** lists append (unless `override: true`); numbers min for limits / max for richness; booleans last-writer; operators `(baseline ∪ include) − exclude`, with `insert_at`.

**Model pack example**

```yaml
id: pack.chatgpt.v1
type: model
priority: 40
applies_to: { models: ["gpt-4o","gpt-4.1","o4-mini","gpt-4o-mini"] }
directives:
  max_tokens_hint: 8000
  temperature_hint: 0.2
  style: { persona: "Domain expert; numbered steps", tone: "precise, neutral",
           formatting: ["section-headers","bullets","tables-when-appropriate"] }
  constraints:
    - "State assumptions explicitly"
    - "Ask for missing inputs unless STRICT_MODE=true"
    - "Include ≥1 I/O example when applicable"
  operators:
    include: ["clarify","disambiguate","structure","format_contract","tone_adjust",
              "example_inject","tighten_language","compress","safety_guard","verify_requirements"]
checklist:
  - { id: io-contract, test: "must include Goals, Inputs, Process, Output Format, Acceptance Criteria" }
  - { id: eval-precision, test: "hedging ≤ 2/500 tokens" }
```

**Category pack (precision)**

```yaml
id: pack.precision.v2
type: category
priority: 60
directives:
  style: { tone: "concise, unambiguous" }
  constraints: ["Acceptance criteria must be measurable (testable bullets)"]
  operators:
    insert_at: [{ name: "tighten_language", index: 6 }]
```

### 5.3 Operators (baseline order)

**Order:**  
`clarify → disambiguate → structure → format_contract → tone_adjust → example_inject → tighten_language → compress → safety_guard → verify_requirements`

- **clarify:** surface ambiguities; populate Assumptions/TODOs if unresolved.  
- **disambiguate:** canonicalize terms (Glossary).  
- **structure:** enforce required sections (+ “Risks & Mitigations” for strategic categories).  
- **format_contract:** Inputs, Process, Outputs, Acceptance, Output Format.  
- **tone_adjust:** persona/tone; avg sentence length ≤ 22.  
- **example_inject:** minimal I/O examples.  
- **tighten_language:** remove hedging; active voice.  
- **compress:** ≤15% tokens; preserve headings.  
- **safety_guard:** banned phrases/scope guard.  
- **verify_requirements:** error if required sections missing (and `STRICT_MODE=true`).

---

## 6) LLM-Assisted Enhancement (HF default)

### 6.1 Plan (two-model pattern)

When enabled by RulePack/overrides:

```
clarify → disambiguate → structure → format_contract → tone_adjust
→ llm_rewrite (N candidates, Editor via HF)
→ llm_critique (select/refine via HF)
→ example_inject → tighten_language → compress → safety_guard → verify_requirements → llm_score (optional)
```

### 6.2 Strict JSON I/O

**Editor output (must be JSON)**

```json
{
  "diff":[
    {"op":"replace","path":"/sections/goal","value":"..."},
    {"op":"add","path":"/sections/acceptance_criteria","value":["...","..."]},
    {"op":"set","path":"/sections/io_format","value":"markdown"}
  ],
  "rationale":"Improved specificity; added measurable criteria.",
  "est_token_count": 1320
}
```

**Critic output**

```json
{
  "scores":[
    {"specificity":0.91,"structure":0.96,"ambiguity_inverse":0.90,"actionability":0.93,"consistency":0.95},
    {"specificity":0.88,"structure":0.92,"ambiguity_inverse":0.89,"actionability":0.90,"consistency":0.94}
  ],
  "winner_index":0,
  "feedback_per_section":{"goal":"Add KPIs","acceptance_criteria":"Make criteria measurable"}
}
```

**Validators:** required sections preserved; token bounds respected; diff applies cleanly → otherwise reject candidate.

### 6.3 Fallback rule

Compute offline baseline HLEP; accept Editor/Critic winner **only if** `winner_score ≥ baseline + 3`. Else return offline HLEP.

---

## 7) Configuration (Local-First + HF Assist)

### 7.1 Operating modes
- **Local + HF Assist (MVP default):** engine runs locally; LLM Assist uses **HF Serverless Inference** (free quota).
- **Local-Only (strict, optional):** no egress; offline operators only.
- **Team/Prod (optional later):** swap storage/cache/providers via config (Postgres/Redis, TGI/OpenAI/Anthropic).

### 7.2 Environment files

**`.env.local-hf` (MVP default)**

```env
APP_ENV=local
NO_NET_MODE=false
PROVIDER_ALLOWLIST=hf
EGRESS_ALLOWLIST=api-inference.huggingface.co,*.endpoints.huggingface.cloud

HF_TOKEN=***your_hf_api_token***
HF_BASE=https://api-inference.huggingface.co

LLM_ASSIST_ENABLED=true
LLM_CANDIDATES=2
LLM_MAX_TOKENS_PROMPT=3000
LLM_MAX_TOKENS_COMPLETION=1200
LLM_COST_BUDGET_USD=2.50
LLM_RATE_LIMIT_QPS=1

MODEL_DEFAULT=hf/mistralai/Mistral-7B-Instruct-v0.3
STRESS_FAIL_THRESHOLD=0.05
LOG_LEVEL=INFO
```

**`.env.local-only` (strict, optional)**

```env
APP_ENV=local
NO_NET_MODE=true
PROVIDER_ALLOWLIST=
EGRESS_ALLOWLIST=
LLM_ASSIST_ENABLED=false
MODEL_DEFAULT=
```

**Provider resolution & egress policy**
1. provider ∈ `PROVIDER_ALLOWLIST`  
2. if `NO_NET_MODE=true` and provider is remote → **EGRESS_BLOCKED**  
3. if provider domain ∉ `EGRESS_ALLOWLIST` → **EGRESS_BLOCKED**

**Error shape**

```json
{"error":{"code":"EGRESS_BLOCKED","message":"Remote provider disallowed by policy"}}
```

### 7.3 Provider registry (`configs/models.yaml`)

```yaml
providers:
  - { id: hf,  base_url: ${HF_BASE}, auth: bearer:${HF_TOKEN} }
  # optional adapters you can enable later:
  - { id: tgi, base_url: ${TGI_BASE} }                 # OpenAI-compatible
  - { id: ollama, base_url: http://localhost:11434 }   # local
  - { id: openai, base_url: https://api.openai.com/v1, auth: bearer:${OPENAI_API_KEY} }
  - { id: anthropic, base_url: https://api.anthropic.com, auth: bearer:${ANTHROPIC_API_KEY} }

models:
  - { id: "hf/mistralai/Mistral-7B-Instruct-v0.3", provider: hf,  token_limit: 8192 }   # Editor default
  - { id: "hf/Qwen/Qwen2.5-7B-Instruct",          provider: hf,  token_limit: 16384 }  # Critic default
  - { id: "hf/meta-llama/Llama-3.1-8B-Instruct",  provider: hf,  token_limit: 8192 }   # Alternate

  # Optional alternates
  - { id: "tgi:llama3.1-8b",        provider: tgi,    token_limit: 8192 }
  - { id: "ollama:llama3.1:8b",     provider: ollama, token_limit: 8192 }
  - { id: "ollama:qwen2.5:7b-instruct", provider: ollama, token_limit: 16384 }
```

### 7.4 RulePack defaults (HF Assist)

```yaml
id: pack.precision.v2
type: category
priority: 60
directives:
  llm_assist_enabled: true
  editor_model: "hf/mistralai/Mistral-7B-Instruct-v0.3"
  critic_model: "hf/Qwen/Qwen2.5-7B-Instruct"
  candidate_count: 2
  rubric:
    required_sections: ["goal","inputs","constraints","steps","acceptance_criteria","io_format"]
    penalties: { missing_section: 20, hedging_per_500_tokens: 2, passive_voice_ratio: 0.15 }
    preferences: { tone: "precise, neutral", persona: "domain expert; numbered steps" }
operators:
  include: ["clarify","disambiguate","structure","format_contract","tone_adjust",
            "llm_rewrite","llm_critique","example_inject",
            "tighten_language","compress","safety_guard","verify_requirements"]
```

---

## 8) HF Serverless Adapter (behavior)

- **Endpoint:** `POST ${HF_BASE}/models/{repo-id}`
- **Body:**
  ```json
  { "inputs": "<prompt>", "parameters": { "max_new_tokens": 512, "temperature": 0.2, "return_full_text": false } }
  ```
- **Retries/backoff:** on `429/503` (bounded).
- **Guards:** token & cost budgets; strict JSON parsing for `llm_rewrite/llm_critique`; cache by `(seed, packs, models, candidate_count)`.

**Errors**
```json
{"error":{"code":"LLM_RATE_LIMITED","message":"HF 429; retried/backoff exhausted"}}
{"error":{"code":"LLM_COLD_START","message":"HF 503; retried/backoff exhausted"}}
{"error":{"code":"LLM_BUDGET_EXCEEDED","message":"Cost or token budget exceeded"}}
{"error":{"code":"ASSIST_JSON_INVALID","message":"LLM Assist returned non-JSON/invalid JSON"}}
```

---

## 9) APIs (REST)

- **POST `/engine/transform`**  
  **Req:**  
  ```json
  { "seed": "...", "model": "...", "category": "...",
    "overrides": { "llm_assist": true, "editor_model": "...",
                   "critic_model": "...", "candidate_count": 2,
                   "style": {}, "operators": [] } }
  ```
  **Resp (excerpt):**
  ```json
  {
    "hlep":"...", "quality":{"score":92,"components":{...},"failed_checks":[]},
    "packs_applied":[...],
    "operator_plan":[...],
    "diff":{"added_sections":["acceptance_criteria"],"removed_hedging":7},
    "rationales":[{"operator":"clarify","why":"..."}],
    "token_estimate":{"prompt":980,"margin_to_limit":199020},
    "operator_trace":[
      {"op":"llm_rewrite","models":["hf/mistralai/Mistral-7B-Instruct-v0.3"],"candidates":2},
      {"op":"llm_critique","model":"hf/Qwen/Qwen2.5-7B-Instruct","winner":0}
    ]
  }
  ```

- **POST `/engine/plan`** (packs + operator plan only)  
- **POST `/engine/score`** (quality scorer)  
- **GET `/engine/packs/models`**, **GET `/engine/packs/categories`**

**Core:** `/templates` CRUD, `/choose`, `/feedback`, `/metrics`, `/diagnostics`, `/healthz`  
**M3:** `/replay`, `/replay-results`  
**M4:** `/stress-test`, `/stress-results`  
**M5:** `/optimize`, `/optimize/accept`

---

## 10) UI (single screen)

- **Inputs:** Seed, Model, Category.  
- **Advanced:** strict mode, examples count, tone, output format, **LLM Assist toggle** (`OFF | HF (default) | Local`).  
- **Outputs:** Engineered prompt (editable), quality meter, packs chips, operator trace (incl. Editor/Critic), diff viewer.

---

## 11) Observability

- **Logs:** structlog JSON (`request_id`, `run_id`, `operator`, `model`, `cost`, `error_code`).  
- **Metrics (Prometheus):**
  - `http_requests_total{endpoint,status}`
  - `http_latency_seconds_bucket{endpoint}`
  - `engine_quality_score{model,category}`
  - `replay_drift_score_avg{model_from,model_to}`
  - `stress_failures_total{case_type}`
  - `optimize_accept_ratio`
- **Tracing (optional):** OpenTelemetry around provider calls & operators.

---

## 12) Security & Safety

- Pydantic validation; required section checks.  
- M4 stress profiles for injection/leakage; “no hidden prompts returned”.  
- Secrets via ENV; pre-commit secret scan.  
- Logs redact seed by default (enable with DEBUG).  
- Optional `SafetyClassifier` stage before accepting Editor diffs.

---

## 13) Performance & SLOs

- Non-LLM endpoints p95 < **350ms**.  
- `/engine/transform` (offline path) avg ≤ **120ms**; with LLM Assist bounded by provider latency and `candidate_count`.  
- Cache identical (seed, packs, models, N) requests.

---

## 14) Testing

- **Unit:** operators, RulePack merge, JSON diff application.  
- **Property:** `compress` never removes required sections.  
- **Golden:** stable HLEP snapshots per model×category (regex-tolerant).  
- **Integration:** `/engine/*` via httpx; migrations (Alembic).  
- **Stress (CI):** light profile on touched templates; fail if `fail_rate > STRESS_FAIL_THRESHOLD`.  
- **LLM Assist:** Editor preserves sections & emits valid JSON; Critic enforces rubric; fallback triggers when winner < baseline+3; token/cost budgets enforced.

---

## 15) CI/CD

1. Lint (ruff) → Types (mypy `--strict`) → Tests (pytest, ≥85% coverage)  
2. Migrations check (Alembic)  
3. Stress (light)  
4. Build (Docker) → Scan (secrets/licenses)  
5. Release (conventional commits) → Deploy (compose/K8s)

---

## 16) Deployment Profiles (config-only switches)

- **Local Dev (MVP):** Docker Compose; SQLite + in-mem cache; HF Serverless enabled by `.env.local-hf`.  
- **Single VM (staging):** Compose with Postgres + Redis + API (+ optional TGI).  
- **Kubernetes (prod):** services for `api`, optional `engine-worker`, `postgres`, `redis`, `tgi`, Prom/Grafana. HPA on RPS/CPU; cert-manager for TLS.  
- **Serverless (alt):** API on Cloud Run/App Service; HF Inference Endpoints for Editor/Critic.

**Scale-out levers:** async queue for assist, idempotency keys, request coalescing by seed hash, Redis cache TTL, per-key rate limits, feature flags (`LLM_ASSIST_ENABLED`, `CANDIDATE_COUNT`, `FALLBACK_DELTA`, `SAFETY_STRICT`).

---

## 17) Error Model

```json
{ "error": { "code":"ENGINE_VERIFY_FAILED", "message":"Missing sections: acceptance_criteria",
             "hint":"Disable STRICT_MODE or provide fields" } }
```

Common: `BAD_REQUEST`, `MODEL_NOT_SUPPORTED`, `PACK_RESOLUTION_FAILED`, `ENGINE_VERIFY_FAILED`, `EGRESS_BLOCKED`, `LLM_BUDGET_EXCEEDED`, `LLM_RATE_LIMITED`, `LLM_COLD_START`, `STRESS_ASSERTION_FAILED`, `REPLAY_TARGET_UNAVAILABLE`, `ASSIST_JSON_INVALID`.

---

## 18) Quickstart (MVP)

1. Create `.env.local-hf` (above) with `HF_TOKEN`.  
2. Launch:  
   ```bash
   docker compose -f infra/compose/docker-compose.local-hf.yml up --build
   ```
3. Put a seed in `seed.txt`, then:  
   ```bash
   neoprompt transform \
     --model "hf/mistralai/Mistral-7B-Instruct-v0.3" \
     --category precision_clarity \
     --in seed.txt --out out.md --explain
   ```
4. Confirm HLEP + quality + operator trace shows `llm_rewrite` & `llm_critique`.  
5. If HF throttles: bounded retry; otherwise `LLM_RATE_LIMITED`. Fallback to offline if winner < baseline+3.

---

## 19) “Do This Now” (build order)

1. RulePack resolver + registries (`models.yaml`, `categories.yaml`).  
2. Offline operators + PromptDoc + scoring.  
3. `/engine/transform|plan|score`.  
4. HF Serverless adapter (budget, retry, cache).  
5. `llm_rewrite` / `llm_critique` / `llm_score` (strict JSON) + fallback logic.  
6. UI single screen + CLI.  
7. Replay (M3) → Stress (M4) → Optimizer (M5).  
8. CI + metrics + dashboards.

---

## 20) Definition of Done

- Engine endpoints implemented with schemas herein.  
- Local-First with HF Assist operational by config (no code change for other modes).  
- Quality uplift vs baseline verified (+3 default).  
- Tests ≥85%; stress CI active; non-LLM p95 < 350ms.  
- Docs shipped: “How the Engine Builds Your Prompt” & “LLM Assist & Providers.”
