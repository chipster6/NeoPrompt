# Provider Policy

NeoPrompt enforces strict provider policies to keep inference calls predictable and auditable. The policy layer sits between the engine and individual adapters so the core code does not need to know about network limits, credentials, or cost ceilings.

## Allowlist model

Adapters are loaded only when both `PROVIDER_ALLOWLIST` and `EGRESS_ALLOWLIST` permit them. Each outbound request is checked for:

1. Provider slug (e.g. `hf`)
2. Hostname (e.g. `api-inference.huggingface.co`)
3. Active profile (`NO_NET_MODE`, `LLM_ASSIST_ENABLED`)

Requests that do not pass the allowlist are rejected before any HTTP call is made.

### Positive example

```json
{
  "provider": "hf",
  "endpoint": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
  "headers": {"Authorization": "Bearer <token>"},
  "body": {"inputs": "<prompt>", "parameters": {"max_new_tokens": 512, "temperature": 0.2}}
}
```

This request is allowed when:

- `PROVIDER_ALLOWLIST` includes `hf`
- `EGRESS_ALLOWLIST` includes `api-inference.huggingface.co`
- `LLM_ASSIST_ENABLED` is `true`
- The current spend remains below `LLM_COST_BUDGET_USD`

### Error examples

- `EGRESS_BLOCKED`: host is missing from the allowlist or `NO_NET_MODE=true`
- `PROVIDER_BLOCKED`: provider slug not in `PROVIDER_ALLOWLIST`
- `LLM_RATE_LIMITED`: upstream returned HTTP 429 after bounded retries
- `LLM_COLD_START`: upstream returned HTTP 503 after bounded retries
- `LLM_BUDGET_EXCEEDED`: the cost guard rejected the call before dispatch

## Cost budgets

Set `LLM_COST_BUDGET_USD` to cap total spend across all adapters. The value is tracked in the adapter layer itself, so even if the engine retries a call the budget check runs before every outbound request. When the threshold is hit the adapter returns `LLM_BUDGET_EXCEEDED` and no network call is attempted.

The adapter layer also records token estimates per request so teams can audit historical spend and tune budgets for each environment.
