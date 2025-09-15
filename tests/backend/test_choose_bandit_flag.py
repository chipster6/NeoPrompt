import importlib
from typing import List

import pytest
from fastapi.testclient import TestClient


def write_recipe(tmp_path, rid: str = "chatgpt.coding.baseline"):
    p = tmp_path / "sample.yaml"
    p.write_text(
        "\n".join(
            [
                f"id: {rid}",
                "assistant: chatgpt",
                "category: coding",
                "operators: [role_hdr, constraints, io_format, quality_bar]",
                "hparams: { temperature: 0.2, top_p: 0.9, max_tokens: 100 }",
                "guards: { max_temperature: 0.4 }",
                "examples: []",
            ]
        ),
        encoding="utf-8",
    )
    return p


def setup_app_with_tmp_recipes(monkeypatch, tmp_path, bandit_enabled: str):
    # Configure flag before import
    monkeypatch.setenv("BANDIT_ENABLED", bandit_enabled)
    # Ensure default epsilon
    monkeypatch.setenv("EPSILON", "0.10")
    # Import and reload main to apply env
    import backend.app.main as main_mod
    import backend.app.recipes as rmod
    importlib.reload(rmod)
    importlib.reload(main_mod)

    # Point recipes cache at tmp dir with one valid recipe
    write_recipe(tmp_path)
    main_mod.app.state.recipes_cache = rmod.RecipesCache(str(tmp_path))
    return main_mod


def test_choose_uses_optimizer_when_bandit_disabled(monkeypatch, tmp_path):
    main_mod = setup_app_with_tmp_recipes(monkeypatch, tmp_path, bandit_enabled="0")
    with TestClient(main_mod.app) as client:
        # Warm cache
        rr = client.get("/recipes?reload=true")
        assert rr.status_code == 200

        r = client.post(
        "/choose",
        json={
            "assistant": "chatgpt",
            "category": "coding",
            "raw_input": "test",
            "options": {},
            "context_features": {},
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    notes: List[str] = data.get("notes", [])
    # Should not have bandit explored note
    assert any(n.startswith("policy=") for n in notes)
    assert not any(n.startswith("explored=") for n in notes)
    # Bandit service should not be initialized
    assert not hasattr(main_mod.app.state, "bandit_service")


def test_choose_uses_bandit_when_enabled(monkeypatch, tmp_path):
    main_mod = setup_app_with_tmp_recipes(monkeypatch, tmp_path, bandit_enabled="1")
    with TestClient(main_mod.app) as client:
        rr = client.get("/recipes?reload=true")
        assert rr.status_code == 200

        r = client.post(
        "/choose",
        json={
            "assistant": "chatgpt",
            "category": "coding",
            "raw_input": "test",
            "options": {},
            "context_features": {},
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    notes: List[str] = data.get("notes", [])
    # Coldstart path is expected with a fresh DB; at minimum policy should be present
    assert any(n == "policy=coldstart" for n in notes) or any(n.startswith("policy=") for n in notes)
    # Bandit service should be initialized on app.state
    assert hasattr(main_mod.app.state, "bandit_service") and main_mod.app.state.bandit_service is not None
