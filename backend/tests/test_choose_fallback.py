from fastapi.testclient import TestClient
from backend.app.main import app


def test_choose_tier_fallbacks():
    client = TestClient(app)
    # Warm cache
    client.get('/recipes')

    # Use an unknown category to force fallback to assistant baseline
    r = client.post('/choose', json={
        'assistant': 'chatgpt',
        'category': 'unknown_category_xyz',
        'raw_input': 'test'
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['recipe_id'].endswith('.baseline')
    assert any(n.startswith('tier=assistant+baseline') for n in data.get('notes', [])), data.get('notes')


def test_choose_returns_503_when_all_invalid(tmp_path, monkeypatch):
    from backend.app.main import app
    from backend.app.recipes import RecipesCache

    # Create a temp recipes dir with a broken YAML
    p = tmp_path / 'bad.yaml'
    p.write_text('id: bad\nassistant: chatgpt\ncategory: coding\noperators: [role_hdr\n', encoding='utf-8')

    # Swap cache to point at this directory
    app.state.recipes_cache = RecipesCache(str(tmp_path))

    client = TestClient(app)
    # Force reload to capture the broken file
    client.get('/recipes?reload=true')

    r = client.post('/choose', json={
        'assistant': 'chatgpt',
        'category': 'coding',
        'raw_input': 'test'
    })
    assert r.status_code == 503, r.text
    body = r.json()
    assert body['detail']['code'] == 'recipes_unavailable'
