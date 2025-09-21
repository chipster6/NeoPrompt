# Optimizer v1 (ε-greedy) — Design and Operations (Legacy)

This file preserves the original v1 bandit optimizer documentation for reference. It has been superseded by the V2 roadmap in docs/optimizer.md.

Scope
- Applies per (assistant, category) group.
- Candidates: recipes loaded from recipes/ filtered by assistant and category; if none, fallback path picks a baseline or first available recipe.

Reward Signal
- Aggregate reward is a float in [0,1] provided via POST /feedback.
- Components (optional) are recorded and can include: user_like, copied, format_ok, etc.
- Current default: clients compute aggregate reward; server stores it as-is. Inputs are validated to [0,1].

Selection Policy (ε-greedy)
- Exploration with probability ε: choose a random eligible candidate.
- Exploitation with probability 1-ε: choose candidate with highest mean observed reward.
- Eligibility safety filter: temporarily exclude a recipe if its last 3 rewards are all < 0.2; if all are excluded, fall back to original candidates.
- Ties: current implementation picks the first encountered highest mean (note: can be improved to random tie-break).

State and Updates
- No separate stats table in v1. Mean rewards are computed on-the-fly from Decision+Feedback via SQL aggregation.
- Workflow:
  1) /choose selects recipe, returns decision_id, recipe_id, policy, propensity (selection confidence).
  2) /feedback records reward for that decision_id.
  3) Future selections incorporate the new reward in aggregated means.

Configuration
- EPSILON (env): default 0.10; can be updated at runtime via POST /stats { "epsilon": <value> }.
- BANDIT_ENABLED (env): default true. When false, selection falls back to first candidate; policy=disabled is noted.
- ENHANCER_ENABLED (env): optional rewriter; not required for optimizer.

API Endpoints
- POST /choose: inputs assistant, category, raw_input; returns decision details and policy notes.
- POST /feedback: inputs decision_id, reward in [0,1], optional components and safety_flags.
- GET /stats: returns current ε and mean reward per recipe by assistant/category.
- POST /stats: set ε and/or reset feedback rows (optionally filtered by assistant/category).
- GET /bandit_stats: returns persistent BanditStats snapshot (sample_count, reward_sum, avg_reward, explore_count, exploit_count, updated_at) with optional assistant/category filters.
- POST /bandit_config: update epsilon, min_initial_samples, optimistic_initial_value at runtime.
- POST /bandit_backfill: seed BanditStats from historical Decision+Feedback aggregates (optionally filtered).
- GET /metrics: Prometheus exposition endpoint (see Metrics section).

Success Metrics (initial)
- Rising mean reward per (assistant, category) over time.
- Observed exploration rate ~= ε over sufficient trials.
- Latency impact within budget (selection p95 < 5ms for in-memory stats; < 25ms when fetching stats).
- Safety: low-performing recipes (recently) excluded by safety filter.

Metrics (Prometheus)
- neopr_bandit_selected_total{assistant,category,recipe_id,policy,explored}
- neopr_bandit_feedback_total{assistant,category,recipe_id}
- neopr_bandit_reward_sum{assistant,category,recipe_id}
- neopr_bandit_reward_count{assistant,category,recipe_id}
- neopr_bandit_epsilon
- neopr_bandit_selection_latency_seconds (Histogram)
- neopr_bandit_feedback_latency_seconds (Histogram)

Rollout Plan (Feature-Flagged)
1) Phase 1 — Dark launch
   - Ensure BANDIT_ENABLED=0 (disabled). Deploy; verify no behavior changes.
   - Validate /metrics and /bandit_stats endpoints are up (bandit service may be uninitialized; endpoints guarded accordingly).
2) Phase 2 — Staging enablement
   - Enable BANDIT_ENABLED=1 in staging; exercise choose/feedback; verify metrics and stats growth.
   - Adjust epsilon live via POST /bandit_config if needed.
3) Phase 3 — Canary in production
   - Enable BANDIT_ENABLED=1 (global) for a canary slice of traffic/environment.
   - Monitor mean reward, explore rate≈ε, selection latency, error rates via Prometheus metrics.
4) Phase 4 — Gradual expansion
   - Increase coverage; rollback by setting BANDIT_ENABLED=0 and redeploying. Runtime adjustments via /bandit_config.

Runbook (Ops)
- To adjust exploration: POST /bandit_config {"epsilon": 0.2}.
- To clear learned averages: POST /stats {"reset": true, "assistant": "...", "category": "..."} (clears Feedback and recomputes from scratch).
- To seed stats from history: POST /bandit_backfill with optional assistant/category filters.
- To monitor health: watch selection and feedback latency histograms and reward trends.

Future Enhancements (out of v1 scope)
- Per-group overrides persisted in DB, contextual bandits, Thompson Sampling, stronger safeguards based on safety flags.
