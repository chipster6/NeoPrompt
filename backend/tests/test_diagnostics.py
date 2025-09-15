from fastapi.testclient import TestClient
from backend.app.main import app


def test_diagnostics_endpoint():
    client = TestClient(app)
    r = client.get('/diagnostics')
    assert r.status_code == 200
    data = r.json()
    assert 'count' in data and 'items' in data
    assert isinstance(data['items'], list)
