from pathlib import Path
from backend.app.recipes import RecipesCache


def write(p: Path, s: str):
    p.write_text(s, encoding='utf-8')


def test_schema_and_semantic_validation(tmp_path, monkeypatch):
    # Create schema-invalid (missing required fields) and semantic-invalid (law with high max_temperature)
    bad_schema = tmp_path / 'bad_schema.yaml'
    write(bad_schema, 'assistant: chatgpt\ncategory: coding\n')

    sem_invalid = tmp_path / 'sem_invalid.yaml'
    write(sem_invalid, 'id: test.law.baseline\nassistant: chatgpt\ncategory: law\noperators: [role_hdr]\nhparams: {temperature: 0.2}\nguards: {max_temperature: 0.9}\n')

    good = tmp_path / 'good.yaml'
    write(good, 'id: ok.coding.baseline\nassistant: chatgpt\ncategory: coding\noperators: [role_hdr]\nhparams: {temperature: 0.2}\nguards: {max_temperature: 0.4}\n')

    cache = RecipesCache(str(tmp_path))
    recipes, errors = cache.ensure_loaded(force=True)

    # Schema-invalid excluded
    assert any(getattr(e, 'error_type', None) == 'schema_validation' for e in errors)

    # Semantic issues are warnings and still included by default (VALIDATION_STRICT off)
    assert any(getattr(e, 'error_type', None) == 'semantic_validation' for e in errors)
    assert any(r.id == 'test.law.baseline' for r in recipes)


def test_validation_strict_excludes_semantic(tmp_path, monkeypatch):
    # Turn on strict mode
    monkeypatch.setenv('VALIDATION_STRICT', '1')
    from importlib import reload
    import backend.app.recipes as rmod
    reload(rmod)

    sem_invalid = tmp_path / 'sem_invalid.yaml'
    write(sem_invalid, 'id: test.law.baseline\nassistant: chatgpt\ncategory: law\noperators: [role_hdr]\nhparams: {temperature: 0.2}\nguards: {max_temperature: 0.9}\n')

    cache = rmod.RecipesCache(str(tmp_path))
    recipes, errors = cache.ensure_loaded(force=True)

    # Semantic issues present but recipe excluded
    assert any(getattr(e, 'error_type', None) == 'semantic_validation' for e in errors)
    assert all(r.id != 'test.law.baseline' for r in recipes)
