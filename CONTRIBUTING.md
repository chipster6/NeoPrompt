# Contributing to NeoPrompt

Thanks for your interest in improving NeoPrompt! This guide explains how to set up your environment, propose changes, and validate your work before opening a pull request.

## Getting started

1. Fork the repository and clone your fork locally.
2. Install the pinned toolchain with `mise install`.
3. Create a virtual environment in `backend/` (`python3 -m venv .venv && source .venv/bin/activate`).
4. Install backend dependencies with `pip install -r backend/requirements.txt` (and `requirements-dev.txt` when linting locally).
5. Install frontend dependencies with `npm install` from the `frontend/` directory if you are touching the UI.

## Branching & commits

- Work off the latest `main` branch.
- Keep commits focused—each commit should introduce a logical unit of work.
- Run the full test suite before pushing (`pytest -q`).
- Follow the conventional PR template when submitting changes.

## Testing strategy

NeoPrompt relies on a few complementary testing styles:

- **Golden tests (snapshots):** Located alongside the engine tests (see `tests/backend/`), these capture canonical outputs from the planner and transformer. Update them with care and include reasoning in your PR description when a snapshot changes.
- **Property tests:** Check invariants such as operator ordering or schema validation. Use `hypothesis`-style patterns to generate input variations whenever feasible.
- **Stress profile (CI):** The `local-only` Compose profile is exercised in CI to ensure deterministic behavior without network access. Run `docker compose --profile stress up --build` locally if you are modifying performance-sensitive code or adapters.

Document new tests in your PR description so reviewers understand coverage improvements.

## Code style

- Python code should follow `black`/`isort` formatting (run `pytest` or `make lint` to trigger hooks).
- Type hints are required for new Python modules.
- Frontend code should adhere to the ESLint + Prettier configuration defined in `frontend/`.

## Security and responsible disclosure

Please review [docs/SECURITY.md](docs/SECURITY.md) before reporting vulnerabilities. It covers supported versions, disclosure timelines, and secure contact details.

## Community

- File issues for bugs or feature requests.
- Join discussions in the GitHub repository for roadmap updates.
- Respect the code of conduct and be excellent to each other.
