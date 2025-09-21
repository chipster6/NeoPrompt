# Operating Modes

NeoPrompt supports multiple execution profiles so you can test specific capabilities without changing code. Each mode is activated by choosing the appropriate environment file or Docker Compose profile.

## Switching profiles

### Using environment files

1. Copy `.env.example` into the profile you want to use (e.g. `.env.local-hf`, `.env.local-only`).
2. Export the file with `set -a && source .env.<profile> && set +a` before launching services.
3. Restart the backend so the new configuration is picked up.

Swapping between profiles is just a matter of sourcing a different `.env.*` file—no Python code changes are required.

### Using Docker Compose

The provided `docker-compose.yml` exposes profiles that mirror the environment files:

- `docker compose --profile local-hf up` enables the Hugging Face adapter and assist operators.
- `docker compose --profile local-only up` disables outbound networking, forcing deterministic local execution.
- `docker compose --profile replay up` runs the API alongside the replay worker.

Stopping one stack and starting another with a new profile is sufficient to switch behavior. Compose injects the matching `.env.*` file automatically via the `env_file` entries.

## Mode reference

| Milestone | Mode name     | Activation                                  | Purpose |
|-----------|---------------|----------------------------------------------|---------|
| M0        | **Baseline**  | `NO_NET_MODE=true`, `LLM_ASSIST_ENABLED=false` | Core deterministic operators only |
| M1        | **Local**     | `.env.local-only` / `--profile local-only`     | Develop entirely offline without adapters |
| M3        | **Replay**    | `.env.replay` / `--profile replay`             | Re-run production decisions for regression tracking |
| M4        | **Stress**    | `.env.stress` / `--profile stress`             | Load-test operator throughput and guardrails |
| M5        | **Optimize**  | `.env.optimize` / `--profile optimize`         | Enable bandit optimizer for adaptive recipes |

These milestones align directly with the public roadmap so you can correlate documentation, changelog entries, and feature flags. When a milestone is complete the matching profile becomes part of CI, ensuring regression coverage for that capability.

## Tips

- Commit the `.env.*` files without secrets so new contributors inherit safe defaults per mode.
- Use `NO_NET_MODE=true` in CI to guarantee deterministic test runs.
- Combine `PROVIDER_ALLOWLIST` and `EGRESS_ALLOWLIST` when crafting custom enterprise profiles.
