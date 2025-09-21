# NeoPrompt Quickstart

NeoPrompt ships with a local-first workflow so you can experiment with prompt engineering before wiring up any external LLMs. This guide walks through the minimum steps to get a developer instance online.

## Prerequisites

- Python 3.12 (use `mise install` from the repo root to install the pinned toolchain)
- Node.js 22 for the optional frontend (`mise install` covers this as well)
- Docker (optional) if you prefer Compose profiles over local virtual environments
- A Hugging Face Inference token **only** if you plan to exercise the assist operators

## 1. Clone and bootstrap

```bash
git clone https://github.com/NeodigmLabs/NeoPrompt.git
cd NeoPrompt
mise install
```

## 2. Pick an environment profile

NeoPrompt ships with two developer-focused profiles. Copy the template environment file and adjust whichever profile you need.

### Assisted profile (`.env.local-hf`)

```bash
cp .env.example .env.local-hf
```

Set the following keys for Hugging Face Serverless assist:

- `NO_NET_MODE=false`
- `LLM_ASSIST_ENABLED=true`
- `HF_TOKEN=your-hf-token`
- `MODEL_DEFAULT=hf/mistralai/Mistral-7B-Instruct-v0.3`

You can then export the profile before running services:

```bash
set -a && source .env.local-hf && set +a
```

### Local-Only mode (`.env.local-only`)

Developers without network access or HF tokens can still run NeoPrompt entirely offline. Copy the template and flip the strict flags:

```bash
cp .env.example .env.local-only
```

Recommended settings:

- `NO_NET_MODE=true` to prevent all outbound calls
- `LLM_ASSIST_ENABLED=false` to disable assist operators entirely
- `PROVIDER_ALLOWLIST=` (empty) to guarantee no adapters are loaded

Apply the profile with:

```bash
set -a && source .env.local-only && set +a
```

The engine will fall back to deterministic operators and local caches only. Compose users can achieve the same effect with `docker compose --profile local-only up` (see [docs/OPERATING_MODES.md](OPERATING_MODES.md)).

## 3. Start the stack

### Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.db  # initializes the SQLite database
uvicorn app.main:app --reload --port 7070
```

### Frontend (optional console)

```bash
cd frontend
npm install
npm run dev
```

The console will be available at <http://localhost:5173> and the API at <http://127.0.0.1:7070>.

## 4. Verify `/engine/transform`

With the API online, issue a request to the engine transformation endpoint. The command below uses the offline profile by default:

```bash
curl -fsS http://127.0.0.1:7070/engine/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "seed":"Summarize the discussion points about observability.",
    "model":"baseline",
    "category":"science",
    "overrides":{"llm_assist":false}
  }' | jq
```

You should see a response similar to:

```json
{
  "hlep": "You are an expert in science...",
  "quality": {"score": 92, "components": {"structure": 30, "clarity": 20}, "failed_checks": []},
  "packs_applied": ["core/science", "quality/base"],
  "operator_plan": ["clarify", "structure", "tighten_language"],
  "operator_trace": [
    {"op": "clarify", "status": "ok"},
    {"op": "tighten_language", "status": "ok"}
  ],
  "token_estimate": {"prompt": 640, "margin_to_limit": 199360}
}
```

If you enabled Hugging Face assist, the `operator_trace` will include the selected models and any retries. Offline mode omits external model references entirely.

## 5. Next steps

- Read [docs/OPERATING_MODES.md](OPERATING_MODES.md) for profile switching tips
- Explore [docs/ENGINE_API.md](ENGINE_API.md) for full request/response contracts
- Inspect [docs/RULEPACKS.md](RULEPACKS.md) to customize prompt rules
