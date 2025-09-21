import json
import copy
import pytest

from backend.app.engine_ir.models.prompt_doc import PromptDoc
from backend.app.engine_ir.planner.plan import build_operator_plan
from backend.app.engine_ir.operators import (
    OPERATOR_REGISTRY,
    apply_role_hdr,
    apply_constraints,
    apply_io_format,
    apply_examples,
    apply_quality_bar,
    run_plan,
)


def test_promptdoc_round_trip_schema_and_serialization():
    pd = PromptDoc(
        seed=123,
        model="mistralai/Mistral-7B-Instruct",
        category="precision",
        context={"task": "summarize"},
        sections={
            "goal": "Summarize document X.",
            "inputs": ["doc_x"],
            "constraints": ["Be concise", "No hallucinations"],
            "steps": ["Read", "Summarize"],
            "acceptance_criteria": ["<= 200 words"],
            "io_format": "Markdown",
            "examples": [{"input": "i", "output": "o"}],
        },
        meta={"assumptions": ["text is English"], "open_questions": [], "rationales": []},
    )

    s = pd.model_dump_json()
    pd2 = PromptDoc.model_validate_json(s)
    assert pd2.sections.goal == "Summarize document X."
    assert pd2.sections.io_format == "Markdown"
    assert pd2.meta.assumptions == ["text is English"]
    assert json.loads(s)["sections"]["goal"] == "Summarize document X."


def test_planner_include_exclude_insert_at_and_idempotence():
    baseline = ["apply_role_hdr", "apply_constraints", "apply_io_format", "apply_examples", "apply_quality_bar"]
    directives = {
        "operators": {
            "include": ["apply_examples", "apply_quality_bar", "apply_io_format"],
            "exclude": ["apply_examples"],
            "insert_at": {
                "apply_role_hdr": "start",
                "apply_io_format": "before:apply_quality_bar",
                "apply_quality_bar": "end",
                "apply_constraints": 1,
                "nonexistent": "before:apply_io_format",
            },
        }
    }
    plan = build_operator_plan(directives, baseline)
    assert len(plan) == len(set(plan))
    assert plan[0] == "apply_role_hdr"
    assert plan[-1] == "apply_quality_bar"
    assert plan.index("apply_io_format") < plan.index("apply_quality_bar")
    assert "apply_examples" not in plan


def test_operators_are_deterministic_and_pure_on_promptdoc():
    pd = PromptDoc(sections={"goal": "Do X", "constraints": ["B", "A"]})
    before_copy = pd.model_copy(deep=True)
    out1 = apply_role_hdr(pd.model_copy(deep=True))
    out1 = apply_constraints(out1)
    out1 = apply_io_format(out1)
    out1 = apply_examples(out1)
    out1 = apply_quality_bar(out1)

    out2 = apply_role_hdr(pd.model_copy(deep=True))
    out2 = apply_constraints(out2)
    out2 = apply_io_format(out2)
    out2 = apply_examples(out2)
    out2 = apply_quality_bar(out2)

    assert out1.model_dump() == out2.model_dump()
    assert before_copy.model_dump() == pd.model_dump()


def test_run_plan_applies_registry_in_order():
    pd = PromptDoc(sections={"goal": "G"})
    plan = ["apply_role_hdr", "apply_io_format", "apply_quality_bar"]
    out = run_plan(pd, plan)
    assert out.sections.io_format == "Markdown"
    assert out.meta.quality.score is not None
