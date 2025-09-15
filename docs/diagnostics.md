# Diagnostics — NeoPrompt Recipe Validation

This document defines the diagnostics taxonomy and semantics used by the recipes loader/validator.

Fields
- file_path: absolute or project-relative path
- error: human-readable message
- line_number: 1-based line when available (YAML parsing)
- error_type: yaml_parse | schema_validation | semantic_validation | io_error
- severity: error | warning

Codes and guidance
- yaml_parse (error)
  - Meaning: YAML could not be parsed; file is ignored.
  - Typical causes: missing closing bracket, invalid indentation.
  - Action: Fix syntax. Line number provided when possible.
- schema_validation (error)
  - Meaning: YAML parsed but does not conform to the Recipe model (missing required fields, wrong types).
  - Action: Align with schema. See /recipe_schema or docs/recipe.schema.json for reference.
- semantic_validation (warning)
  - Meaning: Recipe violates domain guidance (e.g., law requires guards.max_temperature ≤ 0.3) or uses unknown enums.
  - Action: Adjust values or rename fields. In VALIDATION_STRICT mode, certain categories (e.g., law) are excluded on semantic violations.
- io_error (error)
  - Meaning: File access issue.
  - Action: Check permissions/path validity.

Severity policy
- yaml_parse, schema_validation, io_error → error
- semantic_validation → warning (except excluded from selection under VALIDATION_STRICT for critical categories)

Surface
- GET /recipes returns both recipes and diagnostics (errors array)
- GET /diagnostics returns diagnostics only
- CLI: backend/cli/recipes_validate.py prints diagnostics in text or JSON

Future extensions
- error codes per rule (e.g., NP1001: MISSING_FIELD, NP2003: MAX_TEMPERATURE_EXCEEDED)
- Related locations for cross-file rules (includes/extends)
