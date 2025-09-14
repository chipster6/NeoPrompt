from fastapi.testclient import TestClient
from backend.app.main import app


def test_recipes_deps_endpoint():
    client = TestClient(app)
    r = client.get('/recipes?deps=true')
    assert r.status_code == 200
    data = r.json()
    assert 'deps' in data
    assert 'by_id' in data['deps'] and 'by_file' in data['deps']
    assert isinstance(data['deps']['by_id'], dict)
    assert isinstance(data['deps']['by_file'], dict)
