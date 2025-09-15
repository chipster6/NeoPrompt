from pathlib import Path
from backend.app.recipes import RecipesCache


def write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')


def test_security_limits(tmp_path, monkeypatch):
    recipes_dir = tmp_path / 'recipes'
    recipes_dir.mkdir()
    # Create a large fragment beyond per-file limit
    big = recipes_dir / '_fragments' / 'big.yaml'
    content = 'x: ' + 'a' * (300_000)  # > 256KiB default
    write(big, content)

    main = recipes_dir / 'chatgpt.coding.sec.yaml'
    write(main, 'id: chatgpt.coding.sec\nassistant: chatgpt\ncategory: coding\ninclude: ["_fragments/big.yaml"]\noperators: [role_hdr]\nhparams: {}\n')

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)
    # Expect a security_validation error
    assert any(e.error_type == 'security_validation' and 'file too large' in e.error for e in errors)


def test_env_policy(tmp_path, monkeypatch):
    recipes_dir = tmp_path / 'recipes'
    recipes_dir.mkdir()
# Only allow ENV prefix SAFE_
    monkeypatch.setenv('RECIPES_ENV_ALLOWLIST', 'SAFE_')
    write(recipes_dir / 'chatgpt.coding.env.yaml', 'id: chatgpt.coding.env\nassistant: chatgpt\ncategory: coding\noperators: [role_hdr]\nhparams: { note: "${ENV:UNSAFE_SECRET:-default}", other: "plain" }\n')

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)
    # Should report blocked by policy and keep default
    assert any(e.error_type == 'security_validation' and 'blocked by policy' in e.error for e in errors)
