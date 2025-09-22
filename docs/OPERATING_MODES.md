# Operating Modes

NeoPrompt is designed to run safely in constrained environments while still being able to tap into optional hosted helpers. The platform currently recognises two primary modes, both of which share the same code paths and deployment artefacts—only configuration changes.

## Local-Only

- **Audience**: Operators who must keep the stack entirely offline.
- **Behaviour**: All `/engine/*` functionality executes with the local Engine IR, rulepacks, and deterministic operators. No outbound network calls are performed and the egress policy blocks any attempt to reach the public internet.
- **How to enable**: Use the standard `.env` or `.env.local` file and the default Docker Compose profile. No Hugging Face credentials are required.

## Local + HF Assist

- **Audience**: Teams that want to remain offline by default but allow explicit access to Hugging Face's serverless inference endpoints when configured.
- **Behaviour**: The core pipeline continues to run locally. The Hugging Face provider adapter is available for opt-in calls when an operator supplies the required credentials. In Milestone 1 this path remains disabled by default but the configuration is ready for live exercises.
- **How to enable**:
  - Copy `.env.local-hf` to `.env` (or supply its values through environment management tooling) to set `HF_TOKEN`, `HF_BASE` (defaults to `https://api-inference.huggingface.co`), and the `EGRESS_ALLOWLIST` entries for Hugging Face domains.
  - Alternatively, select the `local-hf` Docker Compose profile to load the same variables without modifying the base configuration.
- **Operational notes**: Budgets (`HF_BUDGET_TOKENS`, `HF_MAX_TOKENS_PER_CALL`) and retry knobs (`HF_RETRIES`, `HF_BACKOFF_BASE`, `HF_BACKOFF_CAP`) reside in the same `.env.local-hf` template. Leaving the values unset keeps the hosted path dormant.

## Switching Between Modes

Moving from one mode to another never requires a code change or redeploy. Switch the active `.env.*` file (for example, rename `.env.local` ↔ `.env.local-hf`) or start the stack with the corresponding Compose profile. The application reads configuration on startup and activates the right providers automatically.

## Roadmap

Forthcoming milestones introduce additional runtime profiles so teams can plan ahead:

- **M3 – Replay Mode**: deterministic reprocessing of saved decisions for auditing.
- **M4 – Stress Mode**: high-concurrency load runs with synthetic traffic.

Documentation for new modes will land alongside those milestones, but the underlying principle remains: the same binaries run everywhere—configuration decides the behaviour.
