> NOTE: LEGACY ADR — This ADR applies to v1 “recipes”. V2 uses PromptDoc + RulePacks and /engine/* endpoints. See NeoPrompt_TechSpecV2.md and docs/rulepacks_authoring.md.

# ADR 0001 — Schema and Validation Track for NeoPrompt Recipes

Status: Accepted
Date: 2025-09-14

Context
- Recipes are YAML files stored on disk that define assistant- and category-specific prompt engineering settings.
- We need a clear schema, structured validation, diagnostics, and tooling (API/CLI/editor integration) that are robust yet backward-compatible.

Decision
- Stack:
  - FastAPI for API
  - Pydantic v2 for schema modeling and JSON Schema generation
  - PyYAML (safe_load) for parsing YAML
  - mtime-based cache with last-known-good fallback (fs events as a later enhancement)
  - Prometheus client for basic metrics exposure at /metrics
- Schema evolution:
  - Keep current minimal fields (id, assistant, category, operators, hparams, guards, examples) and allow optional metadata (description, tags, version) without breaking existing recipes
  - Enforce assistant/category enums in validators (chatgpt|claude|gemini|deepseek; coding|science|psychology|law|politics)
- Validation:
  - Structural: Pydantic type/shape enforcement
  - Semantic: domain-specific checks (e.g., law requires guards.max_temperature ≤ 0.3)
  - Modes: VALIDATION_STRICT excludes semantic violations for critical categories (initially: law)
- Diagnostics:
  - Collect errors/warnings with error_type (yaml_parse|schema_validation|semantic_validation), file_path, line_number (when available), and severity (error|warning)
- Expose via /recipes and a dedicated /diagnostics endpoint (Legacy v1)
- V2: expose /engine/plan, /engine/transform, and /diagnostics for engine validations
- Tooling:
  - JSON Schema exposed via /recipe_schema for editor integration
  - Basic CLI for validate (single-shot; watch later)

Consequences
- Backward compatible with current recipes
- Editor integration possible today via JSON Schema
- Clear path to add includes/extends and cross-file rules later (dependency graph)

Alternatives Considered
- Adopting ruamel.yaml for stricter parsing/round-trip safety (deferred until needed)
- File watchers via watchdog/watchfiles (deferred in favor of simple polling)

Open Questions
- Exact includes/extends semantics (to be defined in a later ADR)
- Additional critical categories for STRICT mode (e.g., medical)