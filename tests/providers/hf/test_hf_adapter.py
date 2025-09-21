import os
import json
import time
import types
import pytest
from prometheus_client import generate_latest

from backend.app.adapters.providers.hf_serverless_adapter import HFProvider, HFError
from backend.app.metrics import neopr_hf_backoffs_total, neopr_hf_rate_limited_total


def _no_sleep(_):
    return None


def test_egress_allowlist_blocks_when_not_allowed(monkeypatch):
    os.environ["EGRESS_ALLOWLIST"] = "example.com"
    provider = HFProvider(base_url="https://api-inference.huggingface.co", token="", sleep_fn=_no_sleep)
    with pytest.raises(HFError) as ei:
        provider.chat(messages=[{"role": "user", "content": "hi"}], model="mistralai/Mistral-7B-Instruct", max_tokens=10)
    assert ei.value.code == "EGRESS_BLOCKED"


def test_budget_exceeded_blocks_without_network(monkeypatch):
    os.environ["EGRESS_ALLOWLIST"] = "huggingface.co"
    os.environ["HF_BUDGET_TOKENS"] = "100"
    called = {"count": 0}

    provider = HFProvider(base_url="https://api-inference.huggingface.co", token="", sleep_fn=_no_sleep)

    def fake_send(url, headers, body):
        called["count"] += 1
        return (500, {}, "should not be called")

    monkeypatch.setattr(provider, "_send_request", fake_send)
    with pytest.raises(HFError) as ei:
        provider.chat(messages=[{"role": "user", "content": "hello"}], model="m", max_tokens=200)
    assert ei.value.code == "LLM_BUDGET_EXCEEDED"
    assert called["count"] == 0


def test_backoff_on_429_and_metrics_increment(monkeypatch):
    os.environ["EGRESS_ALLOWLIST"] = "huggingface.co"
    os.environ["HF_RETRIES"] = "2"
    provider = HFProvider(base_url="https://api-inference.huggingface.co", token="t", sleep_fn=_no_sleep)

    calls = {"n": 0}

    def fake_send(url, headers, body):
        # first two calls rate-limited, then success
        calls["n"] += 1
        if calls["n"] <= 2:
            return (429, {"Retry-After": "0.1"}, json.dumps({"error": "rate limit"}))
        return (200, {}, json.dumps([{"generated_text": "ok"}]))

    monkeypatch.setattr(provider, "_send_request", fake_send)

    result = provider.chat(messages=[{"role": "user", "content": "hi"}], model="m", max_tokens=10)
    assert result.text == "ok"

    # Metrics should include backoffs and rate-limited counters
    metrics_text = generate_latest().decode("utf-8")
    assert "neopr_hf_backoffs_total" in metrics_text
    assert "neopr_hf_rate_limited_total" in metrics_text


@pytest.mark.live
def test_live_hf_smoke_if_token_present(monkeypatch):
    """
    Optional smoke; not required in CI.
    """
    if not os.getenv("HF_TOKEN"):
        pytest.skip("HF token not set")
    os.environ["EGRESS_ALLOWLIST"] = "huggingface.co"
    provider = HFProvider(base_url=os.getenv("HF_BASE", "https://api-inference.huggingface.co"), token=os.getenv("HF_TOKEN", ""))
    try:
        provider.chat(messages=[{"role": "user", "content": "ping"}], model="mistralai/Mistral-7B-Instruct", max_tokens=5)
    except HFError as e:
        if e.code not in ("LLM_RATE_LIMITED", "LLM_COLD_START"):
            raise
