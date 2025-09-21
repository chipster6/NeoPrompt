# Provider Policy (M1)

## Egress Control
- Outbound HTTP(S) calls are blocked unless the target host matches EGRESS_ALLOWLIST.
- Error code: EGRESS_BLOCKED (HTTP 403 recommended).

## Budgets and Cost Controls
- Token/call budgets enforced pre-flight:
  - HF_MAX_TOKENS_PER_CALL: per-call cap
  - HF_BUDGET_TOKENS: coarse budget threshold
- Exceeded budget error: LLM_BUDGET_EXCEEDED (HTTP 402 recommended).

## Rate Limiting and Cold Starts
- 429 Rate limits: Retries with exponential backoff and jitter; honors Retry-After if present.
  - Error code on exhaustion: LLM_RATE_LIMITED (HTTP 429).
- 503 Cold starts: Retries similarly; if exhausted with loading signals, map to LLM_COLD_START (HTTP 503).
- neopr_hf_backoffs_total increments per backoff; neopr_hf_rate_limited_total increments on 429.

## General Errors
- Non-retryable errors: LLM_ERROR (HTTP 502/500).
- M1 offline path never triggers provider calls; API remains deterministic and side-effect free.
