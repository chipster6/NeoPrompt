# Engine API

The Engine API powers NeoPrompt's deterministic prompt engineering workflow. It is exposed via FastAPI under the `/engine/*` namespace and returns strict JSON payloads for easy validation in CI and automation.

> **Base URL**: `http://127.0.0.1:7070`

## POST `/engine/plan`

Resolve the packs and operator plan for a given seed without performing any transformations.

```bash
curl -fsS http://127.0.0.1:7070/engine/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "seed": "Draft acceptance criteria for a login flow",
    "model": "baseline",
    "category": "product",
    "overrides": {"llm_assist": false}
  }' | jq
```

Example response:

```json
{
  "packs_applied": ["core/product", "quality/base"],
  "operator_plan": ["clarify", "structure", "tighten_language"],
  "warnings": [],
  "errors": []
}
```

## POST `/engine/transform`

Generate a High-Level Engineered Prompt (HLEP) and full trace information.

```bash
curl -fsS http://127.0.0.1:7070/engine/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "seed": "Summarize the discussion points about observability.",
    "model": "baseline",
    "category": "science",
    "overrides": {"llm_assist": false}
  }' | jq
```

Example response:

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

When Hugging Face assist is enabled, the `operator_trace` entries include the model IDs, retry counts, and any backoff durations applied by the adapter.

## POST `/engine/score`

Run the quality scorer without returning a prompt.

```bash
curl -fsS http://127.0.0.1:7070/engine/score \
  -H 'Content-Type: application/json' \
  -d '{
    "seed": "Summarize the discussion points about observability.",
    "hlep": "You are an expert in science...",
    "category": "science"
  }' | jq
```

Example response:

```json
{
  "quality": {
    "score": 92,
    "components": {"structure": 30, "clarity": 20},
    "failed_checks": []
  }
}
```

## Interactive documentation

FastAPI automatically publishes interactive OpenAPI documentation:

- Swagger UI: <http://127.0.0.1:7070/api/docs>
- ReDoc: <http://127.0.0.1:7070/api/redoc>

These pages mirror the JSON contracts above and should be your first stop when the API surface changes.
