import textwrap
from pathlib import Path

from backend.app.recipes import RecipesCache


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def test_include_and_fragment_schema(tmp_path, monkeypatch):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    # Valid fragment
    write(recipes_dir / "_fragments" / "coding.yaml", """
    operators: [role_hdr, io_format]
    hparams: { temperature: 0.2 }
    guards: { max_temperature: 0.4 }
    examples: []
    """)

    # Illegal fragment keys
    write(recipes_dir / "_fragments" / "bad.yaml", """
    id: bad
    operators: [constraints]
    """)

    # Recipe including fragments
    write(recipes_dir / "chatgpt.coding.demo.yaml", """
    id: chatgpt.coding.demo
    assistant: chatgpt
    category: coding
    include: ["_fragments/coding.yaml", "_fragments/bad.yaml"]
    operators+: [quality_bar]
    hparams: { top_p: 0.9 }
    """)

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)

    # One valid recipe should be present even with fragment error (non-strict mode)
    assert any(r.id == "chatgpt.coding.demo" for r in recipes)
    # Expect schema_validation error for illegal fragment keys
    assert any(e.error_type == "schema_validation" and "fragment" in e.error for e in errors)

    # Final operators should include the fragment operators plus appended quality_bar.
    # Because lists override entirely unless using operators+, the base operators in the recipe are not set,
    # so we rely on the fragment's operators with operators+ appended.
    demo = next(r for r in recipes if r.id == "chatgpt.coding.demo")
    assert demo.operators == ["role_hdr", "io_format", "quality_bar"]
