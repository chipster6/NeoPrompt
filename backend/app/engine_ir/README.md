# Engine IR & Planner

This package provides:
- IR: PromptDoc (Pydantic v2) with Sections and Meta models
- Planner: deterministic operator plan composition
- Operators: pure-ish deterministic transforms and a registry with run_plan

Contents
- models/prompt_doc.py: PromptDoc, Sections, Meta, Quality + to_hlep()
- planner/plan.py: build_operator_plan(directives, baseline_ops)
- operators/__init__.py: OPERATOR_REGISTRY and run_plan()
- rulepacks/loader.py: load/merge rulepacks and resolve() helper

PromptDoc IR
- Pydantic v2; model_config uses extra="allow" and populate_by_name=True
- JSON-pointer friendly keys (examples):
  - /seed, /model, /category, /context, /packs_applied
  - /sections/goal, /sections/inputs, /sections/constraints,
    /sections/steps, /sections/acceptance_criteria, /sections/io_format,
    /sections/examples
  - /meta/assumptions, /meta/open_questions, /meta/rationales,
    /meta/quality/score, /meta/quality/signals
- to_hlep(): renders a stable, human-legible summary of the document

Planner
- API: build_operator_plan(directives, baseline_ops) -> list[str]
- Directives schema (subset):
  operators:
    include: [str, ...]
    exclude: [str, ...]
    insert_at: { op_name: "start|end|before:OP|after:OP|<index>" }
- Semantics:
  1) plan := unique_preserving(baseline_ops + include)
  2) remove exclude
  3) apply insert_at in deterministic iteration order
  4) deduplicate again for idempotence
- Missing anchors or out-of-range indices degrade gracefully; duplicates are never produced.

Operators
- Registry: OPERATOR_REGISTRY maps name -> fn(PromptDoc) -> PromptDoc
- run_plan(doc, operator_names): applies known operators in order
- Default operators included:
  - apply_role_hdr: prefix a role header once to sections.goal
  - apply_constraints: normalize/deduplicate constraints deterministically
  - apply_io_format: default io_format if missing
  - apply_examples: inject a deterministic placeholder example if missing
  - apply_quality_bar: compute simple deterministic signals + score

Tests
- Engine tests live in tests/engine/test_ir_and_planner.py
- Run locally:
  - pytest -q tests/engine --maxfail=1
  - pytest -q tests/engine --junitxml=reports/engine.junit.xml
- Gate A (CI): requires >0 tests and pass-rate ≥ 0.95 (JUnit)

Notes
- No external network calls or side effects in core logic
- Deterministic ordering and idempotence are prioritized in planner and operators
