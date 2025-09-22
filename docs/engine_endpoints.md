# Engine Offline API (Gate D1)

This document describes the offline Engine endpoints exposed under the /engine prefix. These endpoints are deterministic and make no network or LLM calls.

Base path: /engine

Endpoints

1) POST /engine/plan
- Purpose: Resolve RulePacks for a given model/category and return the final operator plan and merged directives.
- Request
```json path=null start=null
{
  "model": "mistralai/Mistral-7B-Instruct",
  "category": "precision",
  "overrides": {}
}
```
- Response
```json path=null start=null
{
  "packs_applied": ["pack.global.v1", "pack.precision.v2"],
  "directives": {"sections": {"constraints": ["…"]}, "max_tokens": 2048, "operators": {"include": ["…"], "exclude": ["…"], "insert_at": {"apply_role_hdr": "start"}}},
  "operator_plan": ["apply_role_hdr", "apply_constraints", "apply_io_format", "apply_quality_bar"]
}
```

2) POST /engine/score
- Purpose: Compute an offline, deterministic quality score for a PromptDoc (stub for M1).
- Request
```json path=null start=null
{
  "prompt_doc": {
    "sections": {
      "goal": "Summarize document X",
      "constraints": ["Be concise", "No hallucinations"],
      "io_format": "Markdown",
      "examples": [{"input": "i", "output": "o"}]
    }
  }
}
```
- Response
```json path=null start=null
{
  "signals": {
    "constraints_count": 2,
    "has_io_format": true,
    "has_examples": true
  },
  "score": 0.9
}
```

3) POST /engine/transform
- Purpose: Resolve RulePacks and apply deterministic operators to a PromptDoc; return transformed PromptDoc and HLEP text.
- Request
```json path=null start=null
{
  "model": "mistralai/Mistral-7B-Instruct",
  "category": "precision",
  "prompt_doc": {
    "sections": {
      "goal": "Do X",
      "constraints": ["B", "A"]
    }
  }
}
```
- Response
```json path=null start=null
{
  "packs_applied": ["pack.global.v1", "pack.precision.v2"],
  "operator_plan": ["apply_role_hdr", "apply_constraints", "apply_io_format", "apply_quality_bar"],
  "prompt_doc": {"sections": {"goal": "[Role: assistant]\nDo X", "constraints": ["A", "B"], "io_format": "Markdown"}, "meta": {"quality": {"score": 0.6, "signals": {"constraints_count": 2, "has_io_format": true, "has_examples": false}}}},
  "hlep_text": "Goal:\n[Role: assistant]\nDo X\n\nConstraints:\n- A\n- B\n\nIO Format:\nMarkdown"
}
```

Notes
- PromptDoc schema: backend/app/engine_ir/models/prompt_doc.py
- Operator plan builder: backend/app/engine_ir/planner/plan.py
- Deterministic operators: backend/app/engine_ir/operators/__init__.py
- RulePacks resolver: backend/app/engine_ir/rulepacks/loader.py

Metrics
- The following Prometheus metrics are emitted for these endpoints and visible at GET /metrics:
  - neopr_engine_requests_total{endpoint="plan|score|transform"}
  - neopr_engine_latency_seconds_bucket (and _count/_sum)
- HF provider counters are pre-registered and will appear even in offline mode:
  - neopr_hf_backoffs_total
  - neopr_hf_rate_limited_total

Example curl
```bash path=null start=null
# Plan
curl -s localhost:7070/engine/plan \
  -H 'content-type: application/json' \
  -d '{"model":"mistralai/Mistral-7B-Instruct","category":"precision"}' | jq

# Score
curl -s localhost:7070/engine/score \
  -H 'content-type: application/json' \
  -d '{"prompt_doc":{"sections":{"goal":"Do X","constraints":["A","B"],"io_format":"Markdown"}}}' | jq

# Transform
curl -s localhost:7070/engine/transform \
  -H 'content-type: application/json' \
  -d '{"model":"mistralai/Mistral-7B-Instruct","category":"precision","prompt_doc":{"sections":{"goal":"Do X","constraints":["B","A"]}}}' | jq
```