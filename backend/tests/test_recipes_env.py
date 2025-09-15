import os
import textwrap
from pathlib import Path

from backend.app.recipes import RecipesCache


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def test_env_substitution_with_whitelist(tmp_path, monkeypatch):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    # .env at repo root precedence (tmp/.env), but we will use process env here
    (tmp_path / ".env").write_text("ORG_NAME=FromEnvFile\n", encoding="utf-8")

    # Whitelist
    monkeypatch.setenv("ENV_WHITELIST", "ORG_NAME")
    monkeypatch.setenv("ORG_NAME", "NeoPrompt")

    write(recipes_dir / "chatgpt.coding.env.yaml", """
    id: chatgpt.coding.env
    assistant: chatgpt
    category: coding
    operators: [role_hdr]
    hparams:
      model_note: "Org=${ORG_NAME}"
    """)

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)

    r = next(r for r in recipes if r.id == "chatgpt.coding.env")
    assert r.hparams.get("model_note") == "Org=NeoPrompt"


def test_env_missing_var_warns(tmp_path, monkeypatch):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    monkeypatch.setenv("ENV_WHITELIST", "MISSING_VAR")
    # Do not set MISSING_VAR

    write(recipes_dir / "chatgpt.coding.missing.yaml", """
    id: chatgpt.coding.missing
    assistant: chatgpt
    category: coding
    operators: [role_hdr]
    hparams:
      model_note: "${MISSING_VAR}"
    """)

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)

    # Should still compile in non-strict mode but produce a semantic_validation warning
    assert any(r.id == "chatgpt.coding.missing" for r in recipes)
    assert any(e.error_type == "semantic_validation" and "MISSING_VAR" in e.error for e in errors)
