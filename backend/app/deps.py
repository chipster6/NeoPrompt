from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml
from dotenv import load_dotenv

from backend.app.adapters.providers import get_llm_provider as _get_provider_by_name

# Module-level caches so we only parse files once per process
_CFG_CACHE: Optional[Dict[str, Any]] = None
_MODEL_TO_PROVIDER: Dict[str, str] = {}
_PROVIDER_ENV: Dict[str, Dict[str, str]] = {}
_DEFAULT_PROVIDER: str = "hf"
_ENV_LOADED: bool = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_env_if_needed() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    root = _repo_root()
    # Load base .env first, then allow local override for HF
    base_env = root / ".env"
    local_hf_env = root / ".env.local-hf"
    # Load base without override
    if base_env.exists():
        load_dotenv(dotenv_path=str(base_env), override=False)
    # Load local-hf as an override (commonly used for local dev)
    if local_hf_env.exists():
        load_dotenv(dotenv_path=str(local_hf_env), override=True)
    # Also allow environment to already be set externally
    _ENV_LOADED = True


def _load_models_cfg() -> Dict[str, Any]:
    global _CFG_CACHE
    if _CFG_CACHE is not None:
        return _CFG_CACHE
    cfg_path = _repo_root() / "configs" / "models.yaml"
    if not cfg_path.exists():
        # Minimal default configuration
        _CFG_CACHE = {"providers": {"default": "hf", "registry": {"hf": {"base_url_env": "HF_BASE", "token_env": "HF_TOKEN"}}}, "models": []}
        return _CFG_CACHE
    with open(cfg_path, "r", encoding="utf-8") as fh:
        _CFG_CACHE = yaml.safe_load(fh) or {}
    return _CFG_CACHE


def _build_registry_maps() -> Tuple[str, Dict[str, str], Dict[str, Dict[str, str]]]:
    cfg = _load_models_cfg()
    providers = (cfg.get("providers") or {})
    default_provider = str(providers.get("default", "hf"))
    reg_cfg = (providers.get("registry") or {})

    # Provider env var mapping (e.g., {"hf": {"base_url_env": "HF_BASE", "token_env": "HF_TOKEN"}})
    provider_env: Dict[str, Dict[str, str]] = {}
    for name, entry in reg_cfg.items():
        d = entry or {}
        provider_env[name] = {
            "base_url_env": str(d.get("base_url_env", "HF_BASE")),
            "token_env": str(d.get("token_env", "HF_TOKEN")),
        }

    # Model -> provider mapping
    model_to_provider: Dict[str, str] = {}
    for m in (cfg.get("models") or []):
        mid = m.get("id")
        prov = m.get("provider") or default_provider
        if isinstance(mid, str) and mid:
            model_to_provider[mid] = str(prov)

    return default_provider, model_to_provider, provider_env


# Initialize caches at import to avoid repeated YAML parsing in hot paths
_DEFAULT_PROVIDER, _MODEL_TO_PROVIDER, _PROVIDER_ENV = _build_registry_maps()


def get_llm_provider(model_id: Optional[str], **overrides: Any) -> Any:
    """Factory that returns a provider instance for the given model_id.

    - Selects provider via configs/models.yaml (falls back to providers.default)
    - Loads environment from .env and .env.local-hf (local-hf overrides)
    - Instantiates a provider without performing any network calls
    """
    _load_env_if_needed()

    # Resolve provider key
    key = _MODEL_TO_PROVIDER.get(model_id or "") or _DEFAULT_PROVIDER

    # Read env var names for this provider
    env_names = _PROVIDER_ENV.get(key, {"base_url_env": "HF_BASE", "token_env": "HF_TOKEN"})
    base_url_env = env_names.get("base_url_env", "HF_BASE")
    token_env = env_names.get("token_env", "HF_TOKEN")

    # Prepare kwargs (allow test-time overrides for explicit base_url/token)
    if "base_url" not in overrides:
        overrides["base_url"] = os.getenv(base_url_env, "https://api-inference.huggingface.co")
    if "token" not in overrides:
        overrides["token"] = os.getenv(token_env, "")

    # Instantiate via provider registry (no network calls in constructors)
    return _get_provider_by_name(key, **overrides)


    base_env = provider_settings.get("base_url_env")
    if "base_url" not in kwargs and base_env:
        env_value = os.getenv(base_env)
        if env_value:
            kwargs["base_url"] = env_value

    token_env = provider_settings.get("token_env")
    if "token" not in kwargs and token_env:
        kwargs["token"] = os.getenv(token_env, "")

    allow_env = provider_settings.get("allowlist_env")
    if allow_env:
        allow_value = os.getenv(allow_env, "")
        if allow_value:
            os.environ.setdefault("EGRESS_ALLOWLIST", allow_value)

    return provider_registry.get_llm_provider(resolved_provider, **kwargs)
