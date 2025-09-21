# Changelog

All notable changes to NeoPrompt are documented here. The project follows semantic versioning aligned with roadmap milestones.

## [Unreleased]

- Placeholder for upcoming fixes and enhancements.

## [M1] - 2024-09-15

### Added
- Local-first engine with Hugging Face assist toggle
- `/engine/plan`, `/engine/transform`, `/engine/score` endpoints
- Prompt template hot-reload and diagnostics cache

### Fixed
- Hardened recipe validation to surface cross-file dependency issues

## [M0] - 2024-07-01

### Added
- Baseline prompt console with deterministic operator pipeline
- SQLite storage for decisions and feedback
- Initial Prometheus metrics (`neopr_recipes_*`, `neopr_bandit_*`)

### Notes
- Serves as the long-term support branch for air-gapped installations.

---

Milestone anchors (M0, M1, M2, …) align with the roadmap described in `docs/OPERATING_MODES.md`. Future releases (M2 replay, M3 stress, etc.) will extend this changelog so teams can map features to environment profiles quickly.
