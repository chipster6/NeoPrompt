import json
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_offline_plan_happy_path():
    payload = {"model": "mistralai/Mistral-7B-Instruct", "category": "precision"}
    r = client.post("/engine/plan", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "packs_applied" in data and data["packs_applied"]
    assert "operator_plan" in data and isinstance(data["operator_plan"], list)


def test_offline_score_happy_path():
    pd = {
        "sections": {
            "goal": "Do X",
            "constraints": ["A", "B"],
            "io_format": "Markdown",
            "examples": [{"input": "i", "output": "o"}],
        }
    }
    r = client.post("/engine/score", json={"prompt_doc": pd})
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["score"] <= 1.0
    assert "signals" in body


def test_offline_transform_happy_path_and_metrics():
    pd = {"sections": {"goal": "Do X", "constraints": ["B", "A"]}}
    r = client.post("/engine/transform", json={"model": "mistralai/Mistral-7B-Instruct", "category": "precision", "prompt_doc": pd})
    assert r.status_code == 200
    body = r.json()
    assert "hlep_text" in body and "Goal:" in body["hlep_text"]
    assert "operator_plan" in body and isinstance(body["operator_plan"], list)

    # Metrics must include engine counters/histograms
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "neopr_engine_requests_total" in text
    assert "neopr_engine_latency_seconds_bucket" in text
    # HF metrics should also be registered names
    assert "neopr_hf_backoffs_total" in text
    assert "neopr_hf_rate_limited_total" in text
