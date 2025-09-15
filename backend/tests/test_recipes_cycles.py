import textwrap
from pathlib import Path

from backend.app.recipes import RecipesCache


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def test_extends_cycle_and_duplicates(tmp_path):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    # A -> B -> A cycle
    write(recipes_dir / "a.yaml", """
    id: chatgpt.coding.a
    assistant: chatgpt
    category: coding
    extends: chatgpt.coding.b
    operators: [role_hdr]
    hparams: { temperature: 0.2 }
    """)

    write(recipes_dir / "b.yaml", """
    id: chatgpt.coding.b
    assistant: chatgpt
    category: coding
    extends: chatgpt.coding.a
    operators: [role_hdr]
    hparams: { temperature: 0.2 }
    """)

    # Duplicate id in another file
    write(recipes_dir / "dup1.yaml", """
    id: chatgpt.coding.dup
    assistant: chatgpt
    category: coding
    operators: [role_hdr]
    hparams: { temperature: 0.2 }
    """)
    write(recipes_dir / "dup2.yaml", """
    id: chatgpt.coding.dup
    assistant: chatgpt
    category: coding
    operators: [role_hdr]
    hparams: { temperature: 0.2 }
    """)

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)

    # Duplicates: exclude both
    assert not any(r.id == "chatgpt.coding.dup" for r in recipes)
    assert any(e.error_type == "cross_file_validation" and "duplicate id" in e.error for e in errors)

    # Cycle reported
    assert any(e.error_type == "cross_file_validation" and "cycle" in e.error.lower() for e in errors)
