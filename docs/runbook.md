# Operations Runbook

This runbook covers feature toggles, rollout/rollback, and key diagnostics for NeoPrompt’s bandit optimizer and recipe reload/validation pipeline.

Bandit toggle and rollout
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

Recipe reload modes
- RECIPES_RELOAD_MODE: events|poll|off (default events)
  - events uses watchfiles; falls back to poll on failure
  - off recommended for immutable images or read-only filesystems
- RECIPES_RELOAD_INTERVAL_SECONDS: poll cadence (default 5)
- RECIPES_DEBOUNCE_MS: event debounce (default 300)

Validation strictness
- VALIDATION_STRICT: 0|1 (default 0). When 1, semantic-invalid recipes are excluded according to scope.
- VALIDATION_STRICT_SCOPE: all|critical (default all)
  - critical excludes for law/medical only

Troubleshooting
- No recipes available (503 on /choose):
  - GET /recipes?reload=true and GET /diagnostics for errors and severities
  - Confirm VALIDATION_STRICT and SCOPE aren’t overly aggressive
- Bandit not taking effect:
  - Check BANDIT_ENABLED=1 in environment and logs for "bandit.enabled true"
  - Verify /bandit_stats reflects selections; watch metrics counters
- High selection latency:
  - Inspect neopr_bandit_selection_latency_seconds histogram; check DB performance and TTL cache effectiveness
- Unexpected exploration rate:
  - Verify current ε via GET /bandit_stats (epsilon field) or the neopr_bandit_epsilon gauge; adjust with POST /bandit_config
