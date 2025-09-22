import os
from typing import Any
from urllib import request

from backend.app.deps import get_llm_provider
from backend.app.adapters.providers.hf_serverless_adapter import HFProvider


def test_get_llm_provider_returns_provider_without_network(monkeypatch):
    # Ensure environment is set (mirrors .env.local-hf defaults)
    os.environ.setdefault("HF_BASE", "https://api-inference.huggingface.co")
    os.environ.setdefault("HF_TOKEN", "")

    # Fail if any network attempt is made during provider construction
    called = {"n": 0}

    def fake_urlopen(*args: Any, **kwargs: Any):  # pragma: no cover - should not be hit
        called["n"] += 1
        raise AssertionError("Network should not be called during provider factory")

    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    p = get_llm_provider("mistralai/Mistral-7B-Instruct")
    assert p is not None
    assert isinstance(p, HFProvider)
    assert hasattr(p, "chat")
    # No network should have occurred
    assert called["n"] == 0


def test_unknown_model_falls_back_to_default_provider():
    p = get_llm_provider("some/unknown-model")
    assert isinstance(p, HFProvider)


def test_overrides_are_applied_to_provider_instance():
    # Provide custom base_url and token; provider constructor should receive them
    p = get_llm_provider(
        "mistralai/Mistral-7B-Instruct",
        base_url="https://example.org",
        token="abc123",
    )
    assert isinstance(p, HFProvider)
    assert getattr(p, "base_url", "").startswith("https://example.org")
    assert getattr(p, "token", "") == "abc123"
