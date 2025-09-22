import os
from backend.app.engine_ir.rulepacks.loader import resolve, merge_packs

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


def test_list_override_wrapper_in_memory():
    p1 = {
        "name": "p1",
        "directives": {
            "sections": {"constraints": ["A", "B"]},
            "tags": ["t1", "t2"],
        },
    }
    p2 = {
        "name": "p2",
        "directives": {
            "sections": {"constraints": {"override": True, "value": ["X"]}},
            "tags": {"override": True, "value": ["t3"]},
        },
    }
    out = merge_packs([p1, p2])
    cons = out["directives"]["sections"]["constraints"]
    tags = out["directives"]["tags"]
    assert cons == ["X"]
    assert tags == ["t3"]


def test_numeric_min_max_and_bool_last_writer():
    p1 = {
        "name": "p1",
        "directives": {"max_tokens": 512, "min_depth": 2, "temperature": 0.3, "enabled": True},
    }
    p2 = {
        "name": "p2",
        "directives": {"max_tokens": 2048, "min_depth": 1, "temperature": 0.7, "enabled": False},
    }
    out = merge_packs([p1, p2])
    d = out["directives"]
    assert d["max_tokens"] == 512  # min for max_*
    assert d["min_depth"] == 2     # max for min_*
    assert d["temperature"] == 0.7 # fallback max
    assert d["enabled"] is False   # last-writer


def test_operator_plan_include_exclude_and_insert_at_unknown_anchor():
    a = {"name": "A", "operators": {"baseline": ["alpha", "beta", "gamma"]}}
    b = {
        "name": "B",
        "operators": {
            "include": ["x", "y"],
            "exclude": ["beta"],
            "insert_at": {"x": "before:alpha", "y": "before:nonexistent"},
        },
    }
    out = merge_packs([a, b])
    plan = out["operators"]["plan"]
    assert plan == ["x", "alpha", "gamma", "y"]
    assert "beta" not in plan
