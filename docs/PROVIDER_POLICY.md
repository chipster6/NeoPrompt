# Provider Policy

The provider adapter layer is the single gateway for any external LLM call. It is responsible for enforcing egress, budget, and rate controls before a request ever leaves the host.

## Allowed Providers

| Provider key | Description            | Allowlisted domains                      |
|--------------|------------------------|-------------------------------------------|
| `hf`         | Hugging Face Inference | `api-inference.huggingface.co` (default) |

Additional providers join the table as they are onboarded. Operators may extend the allowlist through configuration, but the adapter validates that every outbound hostname matches an approved entry. Violations return `EGRESS_BLOCKED` (HTTP 403 recommended).

## Example HF Invocation

```http
POST /models/bigscience/bloomz-560m HTTP/1.1
Host: api-inference.huggingface.co
Authorization: Bearer <HF_TOKEN>
Content-Type: application/json

{"inputs": "Summarise: NeoPrompt keeps prompts local by default."}
```

The adapter injects retry and timeout guards, serialises payloads, and collects request/response metadata for observability.

## Error Codes

- `EGRESS_BLOCKED`: Attempted call to a host outside the configured allowlist.
- `LLM_RATE_LIMITED`: The upstream service returned 429 after the adapter exhausted backoff retries.
- `LLM_COLD_START`: Upstream indicated a loading/cold start condition (e.g., 503 with retry hints) and the retry budget expired.
- `LLM_BUDGET_EXCEEDED`: The request would exceed `LLM_COST_BUDGET_USD`, `HF_BUDGET_TOKENS`, or `HF_MAX_TOKENS_PER_CALL` constraints.
- `LLM_ERROR`: All other non-retryable failures (HTTP 5xx/4xx).

## Budgets and Rate Limits

Budgeting and throttling occur inside the provider adapter. Each outbound call is checked against:

- `LLM_COST_BUDGET_USD`: Aggregate spend ceiling shared across providers.
- Token-oriented limits such as `HF_BUDGET_TOKENS` (rolling window) and `HF_MAX_TOKENS_PER_CALL` (per request).
- Client-side rate guards that cap concurrent calls and respect provider guidance.

If a limit trips, the adapter short-circuits the call locally and surfaces the appropriate error code. Successful calls update the trackers so subsequent requests see the latest spend/tokens state.

## Rate Limiting and Cold Starts

The adapter automatically retries when upstream returns `429` or temporary `5xx` codes, using exponential backoff with jitter. When retry attempts are depleted, it surfaces `LLM_RATE_LIMITED` or `LLM_COLD_START` as appropriate. Metrics such as `neopr_hf_backoffs_total` and `neopr_hf_rate_limited_total` provide visibility into these events.

## Offline Guarantee

In Local-Only mode the provider registry remains dormant, meaning the Hugging Face adapter is never invoked. The application continues to produce deterministic results with zero egress while still benefiting from the policy protections documented above should a hosted mode be enabled later.
