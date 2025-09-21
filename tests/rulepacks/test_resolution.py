import os
from backend.app.engine_ir.rulepacks.loader import resolve

def test_resolution_global_plus_precision_operator_order_and_merges():
    res = resolve(model="mistralai/Mistral-7B-Instruct", category="precision")
    packs = res["packs_applied"]
    assert "pack.global.v1" in packs[0]
    assert any("precision" in p for p in packs)
    directives = res["directives"]
    # List append-unique
    cons = directives["sections"]["constraints"]
    assert "Be clear and precise" in cons and "Avoid hallucinations" in cons
    assert len(cons) == len(set(cons))
    # Numbers: min for limits (max_tokens), max for richness (examples_count)
    assert directives["max_tokens"] == 2048
    assert directives["examples_count"] == 3
    # Booleans: last-writer wins (precision sets true)
    assert directives["json_mode"] is True
    # Operators: check order and exclude took effect
    plan = res["operator_plan"]
    assert plan[0] == "apply_role_hdr"
    assert plan[-1] == "apply_quality_bar"
    assert "apply_examples" not in plan
    assert plan.index("apply_io_format") < plan.index("apply_quality_bar")


def test_resolution_model_without_precision_uses_global_only():
    res = resolve(model="Qwen/Qwen2.5-7B-Instruct", category="general")
    packs = res["packs_applied"]
    # chatgpt pack should not match, precision pack not matched; only global
    assert any("global" in p for p in packs)
    assert not any("precision" in p for p in packs)
    directives = res["directives"]
    assert directives["max_tokens"] == 4096
    assert "Avoid hallucinations" not in directives.get("sections", {}).get("constraints", [])
