from backend.app.engine import build_prompt, register_operator

def test_build_prompt_force_json_instructions():
    prompt, applied = build_prompt(
        raw_input="Return an object",
        category="coding",
        operators=["role_hdr", "io_format", "quality_bar"],
        force_json=True,
        examples=[],
    )
    assert "valid JSON only" in prompt
    assert applied == ["role_hdr", "io_format", "quality_bar"]


def test_build_prompt_operator_order_deterministic():
    ops = ["constraints", "role_hdr", "io_format", "examples", "quality_bar"]
    prompt, applied = build_prompt(
        raw_input="Do X",
        category="science",
        operators=ops,
        force_json=False,
        examples=["Ex1", "Ex2"],
    )
    # Applied should keep input order, including optional examples
    assert applied == ops
    # Ensure raw task appended at end
    assert prompt.strip().endswith("TASK:\nDo X")


def test_build_prompt_custom_operator_registry():
    register_operator("custom_block", lambda ctx: "Custom block", overwrite=True)
    prompt, applied = build_prompt(
        raw_input="Investigate",
        category="science",
        operators=["custom_block", "role_hdr"],
    )
    assert prompt.startswith("Custom block")
    assert applied == ["custom_block", "role_hdr"]
