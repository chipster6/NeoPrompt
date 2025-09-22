import importlib
import os


def test_get_llm_provider_uses_env_and_avoids_network(monkeypatch, tmp_path):
    env_file = tmp_path / ".env.local-hf"
    env_file.write_text(
        "\n".join(
            [
                "HF_BASE=https://example.test",
                "HF_TOKEN=fake-token",
                "EGRESS_ALLOWLIST=huggingface.co",
                "",
            ]
        ),
        encoding="utf-8",
    )

    for var in ("HF_BASE", "HF_TOKEN", "EGRESS_ALLOWLIST"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NEOPROMPT_ENV_FILE", str(env_file))

    deps = importlib.import_module("backend.app.deps")
    deps.reload_env_settings()

    hf_module = importlib.import_module("backend.app.adapters.providers.hf_serverless_adapter")

    def _no_network(*args, **kwargs):  # pragma: no cover - defensive
        raise AssertionError("network access attempted during provider construction")

    monkeypatch.setattr(hf_module.request, "urlopen", _no_network)

    provider = deps.get_llm_provider(model_id="mistralai/Mistral-7B-Instruct")

    assert isinstance(provider, hf_module.HFProvider)
    assert provider.base_url == "https://example.test"
    assert provider.token == "fake-token"
    assert os.getenv("EGRESS_ALLOWLIST") == "huggingface.co"
