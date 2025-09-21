# Operations Runbook (V2)

This runbook covers environment profiles, provider/egress policies, diagnostics, and planned endpoints for replay/stress/optimize. Legacy bandit ops are preserved below.


Environment profiles
- .env.local-hf (default MVP): HF_TOKEN, PROVIDER_ALLOWLIST=hf, EGRESS_ALLOWLIST
- .env.local-only (strict): NO_NET_MODE=true; no remote providers

Provider & egress policy
- Requests to remote providers are allowed only if provider ∈ PROVIDER_ALLOWLIST AND domain ∈ EGRESS_ALLOWLIST
- Violations return {"error":{"code":"EGRESS_BLOCKED", ...}}

Diagnostics
- Use /engine/plan to inspect packs_applied and operator_plan
- Use /engine/transform for full trace, quality score, and assist operator outcomes
- /diagnostics aggregates recent validation and runtime issues

Planned endpoints (post-MVP)
- /replay, /stress-test, /optimize — align with NeoPrompt_TechSpecV2.md roadmap

Legacy: Bandit toggle and rollout
- Toggle: BANDIT_ENABLED=0|1 (env). Default is 0.
- Rollout plan:
  1) Dark launch: ensure BANDIT_ENABLED=0 in prod; verify no behavior changes and metrics endpoint up.
  2) Staging enablement: set BANDIT_ENABLED=1 in staging; exercise /choose and /feedback.
  3) Canary: set BANDIT_ENABLED=1 for a canary environment; observe key metrics (below).
  4) Gradual expansion: enable more environments; rollback by setting BANDIT_ENABLED=0 and redeploying.

Runtime tuning
- Exploration rate ε: POST /bandit_config { "epsilon": 0.2 }
- Cold start/priors: POST /bandit_config { "min_initial_samples": N, "optimistic_initial_value": 0.5 }
- Backfill stats from history: POST /bandit_backfill { "assistant": "chatgpt", "category": "coding" }

Monitoring (Prometheus)
- Endpoint: GET /metrics (content-type text/plain)
- Key series:
  - neopr_bandit_selected_total{assistant,category,recipe_id,policy,explored}
  - neopr_bandit_feedback_total{assistant,category,recipe_id}
  - neopr_bandit_reward_sum{assistant,category,recipe_id}
  - neopr_bandit_reward_count{assistant,category,recipe_id}
  - neopr_bandit_epsilon
  - neopr_bandit_selection_latency_seconds (Histogram)
  - neopr_bandit_feedback_latency_seconds (Histogram)
- Health checks:
  - Explore rate tracks ε over time (ratio of explored=true to total selections)
  - Mean rewards trending upward; latency within budget

Legacy (v1) recipe reload modes (if applicable)
- RECIPES_RELOAD_MODE: events|poll|off (default events)
- RECIPES_RELOAD_INTERVAL_SECONDS: poll cadence (default 5)
- RECIPES_DEBOUNCE_MS: event debounce (default 300)

Legacy (v1) validation strictness (recipes)
- VALIDATION_STRICT: 0|1 (default 0)
- VALIDATION_STRICT_SCOPE: all|critical (default all)

Troubleshooting
- Engine diagnostics unclear for a seed:
  - POST /engine/plan and /engine/transform; check returned warnings/errors and operator_trace
  - Check provider/egress policy (EGRESS_BLOCKED) and assist JSON (ASSIST_JSON_INVALID)
- Bandit not taking effect:
  - Check BANDIT_ENABLED=1 in environment and logs for "bandit.enabled true"
  - Verify /bandit_stats reflects selections; watch metrics counters
- High selection latency:
  - Inspect neopr_bandit_selection_latency_seconds histogram; check DB performance and TTL cache effectiveness
- Unexpected exploration rate:
  - Verify current ε via GET /bandit_stats (epsilon field) or the neopr_bandit_epsilon gauge; adjust with POST /bandit_config
