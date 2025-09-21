# Operating Modes (M1)

NeoPrompt M1 supports:
1) Local-only (offline): All /engine/* endpoints operate entirely offline using the Engine IR, Rulepacks, and deterministic Operators. No network calls are made.
2) Local + HF (optional): The Hugging Face Serverless adapter is included but ONLY used if explicitly invoked and allowed. M1 tests do not require any outbound calls.

## Environment
- .env.local-hf provides:
  - HF_TOKEN: HF API token (optional for live smoke)
  - HF_BASE: Base API URL (default https://api-inference.huggingface.co)
  - EGRESS_ALLOWLIST: host allowlist (e.g., huggingface.co) to prevent accidental egress
  - Optional budgets: HF_BUDGET_TOKENS, HF_MAX_TOKENS_PER_CALL
  - Optional retries/backoff: HF_RETRIES, HF_BACKOFF_BASE, HF_BACKOFF_CAP

## Provider Registry
- backend.app.adapters.providers.get_llm_provider("hf") returns an HFProvider instance.
- Provider constructors do not perform network calls.
- In M1, the HF adapter is exercised via mocked tests only; live smoke is optional and gated by an HF_TOKEN check.

## Metrics
- Engine metrics: neopr_engine_requests_total, neopr_engine_latency_seconds
- Provider metrics: neopr_hf_backoffs_total, neopr_hf_rate_limited_total
- All exposed on /metrics via Prometheus client.
