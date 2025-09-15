import os
import textwrap
from pathlib import Path

from backend.app.recipes import RecipesCache


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def test_extends_and_override(tmp_path):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    write(recipes_dir / "chatgpt.coding.base.yaml", """
    id: chatgpt.coding.base
    assistant: chatgpt
    category: coding
    operators: [role_hdr, constraints]
    hparams: { temperature: 0.2, top_p: 0.9 }
    guards: { max_temperature: 0.4 }
    """)

    write(recipes_dir / "chatgpt.coding.child.yaml", """
    id: chatgpt.coding.child
    assistant: chatgpt
    category: coding
    extends: chatgpt.coding.base
    operators: [io_format]
    hparams: { temperature: 0.25 }
    operators+: [quality_bar]
    """)

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)

    assert any(r.id == "chatgpt.coding.child" for r in recipes)
    child = next(r for r in recipes if r.id == "chatgpt.coding.child")

    # operators override entirely to [io_format], then operators+ appends quality_bar
    assert child.operators == ["io_format", "quality_bar"]
    # hparams are deep-merged: temperature overridden, top_p inherited
    # No direct access to merged dict, but we can rely on model.hparams
    assert float(child.hparams.get("temperature")) == 0.25
    assert float(child.hparams.get("top_p")) == 0.9
