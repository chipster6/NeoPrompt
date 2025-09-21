# Migration Guide — v1 Recipes → V2 PromptDoc + RulePacks

This document helps migrate from the v1 recipes/optimizer model to the V2 architecture (PromptDoc IR + RulePacks + Operator Planner, optional LLM Assist).

## Key changes (conceptual)
- Recipes → PromptDoc (IR) + RulePacks (policies). Operators are planned/ordered by the planner.
- Deterministic baseline with optional LLM Assist (Editor/Critic via HF Serverless by default).
- Strict JSON I/O for assist operators; fallback to offline baseline if JSON invalid or winner < baseline+3.
- Configuration via .env profiles (.env.local-hf, .env.local-only) and provider registry (configs/models.yaml).
- Security via provider/egress allowlists; NO_NET_MODE for strict local.

## Steps
1. Map a v1 recipe to PromptDoc fields:
   - id/name → meta; assistant/category → PromptDoc fields
   - operators list → planner inputs; examples → sections.examples
   - hparams/guards → meta and/or RulePacks directives
2. Create RulePacks (global/model/category) for shared policies (tone, constraints, operator inclusions).
3. Configure provider profiles:
   - .env.local-hf with HF_TOKEN and EGRESS_ALLOWLIST; or .env.local-only with NO_NET_MODE=true
   - configs/models.yaml: register default Editor/Critic models
4. Validate with /engine/plan (packs_applied, operator_plan) then /engine/transform (quality + trace).
5. If using assist, ensure strict JSON outputs; otherwise fallback will keep baseline offline.
6. Update integrations to use /engine/* endpoints; retire direct /recipes usage.
