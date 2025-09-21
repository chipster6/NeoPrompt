# Diagnostics — Engine Validation (V2)

This document describes diagnostics for the V2 engine: PromptDoc IR, RulePacks resolution/merge, and template/runtime validations.

Fields
- file_path: absolute or project-relative path
- error: human-readable message
- line_number: 1-based when available
- error_type: json_parse | schema_validation | semantic_validation | io_error | assist_json_invalid | egress_blocked
- severity: error | warning

Codes and guidance
- json_parse (error)
  - Meaning: JSON (or JSON-in-Markdown) could not be parsed; payload or config ignored.
  - Action: Fix syntax. Line number provided when possible.
- schema_validation (error)
  - Meaning: Payload/config parsed but does not conform to the PromptDoc or RulePack schema.
  - Action: Align with schemas (see docs/promptdoc.schema.json, docs/rulepack.schema.json).
- semantic_validation (warning)
  - Meaning: Violates domain guidance or unknown enums.
  - Action: Adjust values or rename fields. In STRICT mode, certain violations may be rejected.
- assist_json_invalid (error)
  - Meaning: LLM Assist (Editor/Critic) returned non‑JSON or invalid JSON for strict JSON I/O operators.
  - Action: Inspect operator trace; retry or disable assist; ensure models are configured.
- egress_blocked (error)
  - Meaning: Remote call blocked by NO_NET_MODE or provider/egress allowlist.
  - Action: Verify .env profile and EGRESS/PROVIDER allowlists.
- io_error (error)
  - Meaning: File/network access issue.
  - Action: Check permissions/path/policy.

Severity policy
- json_parse, schema_validation, assist_json_invalid, egress_blocked, io_error → error
- semantic_validation → warning (unless STRICT mode enforces rejection)

Surfaces
- GET /engine/plan returns packs_applied and operator_plan (+ warnings)
- POST /engine/transform returns quality, operator_trace, and errors array on failures
- GET /diagnostics returns aggregated diagnostics

See also: NeoPrompt_TechSpecV2.md (Sections: Configuration, Error Model).

