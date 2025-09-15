import textwrap
from pathlib import Path

from backend.app.recipes import RecipesCache


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def test_examples_file_references(tmp_path):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    # Make a valid example file
    (recipes_dir / "examples").mkdir()
    (recipes_dir / "examples" / "ok.txt").write_text("ok", encoding="utf-8")

    # Recipe referencing both existing and missing examples
    write(recipes_dir / "chatgpt.coding.refs.yaml", """
    id: chatgpt.coding.refs
    assistant: chatgpt
    category: coding
    operators: [role_hdr]
    examples: ["examples/ok.txt", "examples/missing.txt"]
    hparams: { temperature: 0.2 }
    guards: { max_temperature: 0.4 }
    """)

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)

    # Recipe exists (non-strict), but there should be a cross_file_validation error for the missing file
    assert any(r.id == "chatgpt.coding.refs" for r in recipes)
    assert any(e.error_type == "cross_file_validation" and "not found" in e.error for e in errors)
