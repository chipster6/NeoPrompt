from __future__ import annotations
import os
import json
from fastapi.testclient import TestClient

# Ensure app imports find the backend package
from backend.app.main import app


def test_healthz_ok():
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_schema_endpoint_serves_json_schema(tmp_path, monkeypatch):
    # Force ENV to dev and ensure schema file exists
    # Endpoint already falls back to docs/recipe.schema.json; just call it
    client = TestClient(app)
    r = client.get("/prompt-templates/schema")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    # title may be Prompt Template or Recipe depending on file used
    assert "title" in data


def test_recipes_alias_logs_deprecation(caplog):
    caplog.set_level("WARNING")
    client = TestClient(app)
    r = client.get("/recipes")
    # endpoint should still return 200 even if no recipes loaded
    assert r.status_code == 200
    # Expect a deprecation warning in logs
    assert any("DEPRECATED: /recipes" in rec.message for rec in caplog.records)


def test_cors_env_policy(monkeypatch):
    # When ENV=dev and CORS_ALLOW_ORIGINS unset -> wildcard allowed (handled in middleware setup at import time)
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    # Recreate app to apply env policy
    from importlib import reload
    import backend.app.main as main_mod
    reload(main_mod)
    client = TestClient(main_mod.app)
    # Preflight OPTIONS request
    r = client.options("/healthz", headers={
        "Origin": "http://example.com",
        "Access-Control-Request-Method": "GET"
    })
    # CORS middleware should include AC-Allow-Origin header when wildcard
    assert r.headers.get("access-control-allow-origin") in ("*", "http://example.com")