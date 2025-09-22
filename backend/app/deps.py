from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import dotenv_values

from backend.app.adapters import providers as provider_registry

# Default location relative to repo root; override via MODELS_CONFIG_PATH.
_DEFAULT_MODELS_PATH = Path(__file__).resolve().parents[2] / "configs" / "models.yaml"


def _models_config_path() -> Path:
    override = os.getenv("MODELS_CONFIG_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_MODELS_PATH


@lru_cache(maxsize=1)
def _load_models_config(path: str | None = None) -> Dict[str, Any]:
    cfg_path = Path(path) if path else _models_config_path()
    with cfg_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    data["_path"] = str(cfg_path)
    return data


def reload_models_config() -> None:
    _load_models_config.cache_clear()


def get_models_config() -> Dict[str, Any]:
    return copy.deepcopy(_load_models_config())


@lru_cache(maxsize=1)
def _load_env_settings() -> Dict[str, str]:
    """Load environment values from supported .env files."""

    candidates: list[Path] = []
    override = os.getenv("NEOPROMPT_ENV_FILE")
    if override:
        for part in override.split(os.pathsep):
            if not part:
                continue
            candidate = Path(part).expanduser()
            if candidate.is_dir():
                candidate = candidate / ".env"
            candidates.append(candidate)
    else:
        repo_root = Path(__file__).resolve().parents[2]
        candidates = [
            repo_root / ".env",
            repo_root / ".env.local",
            repo_root / ".env.local-hf",
        ]

    settings: Dict[str, str] = {}
    for path in candidates:
        try:
            if not path.exists():
                continue
            values = dotenv_values(str(path))
            for key, value in values.items():
                if isinstance(value, (str, int, float)):
                    settings[str(key)] = str(value)
        except Exception:
            continue
    return settings


def reload_env_settings() -> None:
    _load_env_settings.cache_clear()


def get_model_entry(model_id: str) -> Dict[str, Any]:
    config = _load_models_config()
    for entry in config.get("models", []) or []:
        if entry.get("id") == model_id:
            return copy.deepcopy(entry)
    raise ValueError(f"Unknown model id: {model_id}")



def get_model_params(model_id: str) -> Dict[str, Any]:
    """Return a copy of model-specific params from the models registry."""
    entry = get_model_entry(model_id)
    return copy.deepcopy(entry.get("params", {}) or {})

def get_provider_settings(provider_name: str) -> Dict[str, Any]:
    config = _load_models_config()
    providers = config.get("providers", {}) or {}
    registry = providers.get("registry", {}) or {}
    settings = registry.get(provider_name)
    if settings is None:
        raise ValueError(f"Unknown provider name: {provider_name}")
    return copy.deepcopy(settings)


def get_llm_provider(
    model_id: str | None = None,
    provider_name: str | None = None,
    **overrides: Any,
) -> Any:
    """Instantiate the configured provider using the static models registry."""
    config = _load_models_config()
    providers_block = config.get("providers", {}) or {}
    env_settings = _load_env_settings()
    resolved_provider = (provider_name or "").strip()
    if model_id:
        try:
            model_entry = get_model_entry(model_id)
            if not resolved_provider:
                resolved_provider = (model_entry.get("provider") or "").strip()
        except ValueError:
            pass

    if not resolved_provider:
        resolved_provider = (providers_block.get("default") or "").strip()

    if not resolved_provider:
        raise ValueError("No provider could be resolved for get_llm_provider")

    provider_settings = (providers_block.get("registry", {}) or {}).get(resolved_provider, {}) or {}

    kwargs: Dict[str, Any] = {k: v for k, v in overrides.items() if v is not None}

    def resolve_env(var_name: str | None) -> str | None:
        if not var_name:
            return None
        existing = os.getenv(var_name)
        if existing is not None:
            return existing
        value = env_settings.get(var_name)
        if value is not None:
            os.environ.setdefault(var_name, value)
            return value
        return None

    base_env = provider_settings.get("base_url_env")
    if "base_url" not in kwargs and base_env:
        env_value = resolve_env(base_env)
        if env_value:
            kwargs["base_url"] = env_value

    token_env = provider_settings.get("token_env")
    if "token" not in kwargs and token_env:
        token_value = resolve_env(token_env)
        if token_value is not None:
            kwargs["token"] = token_value

    allow_env = provider_settings.get("allowlist_env")
    if allow_env:
        allow_value = resolve_env(allow_env)
        if allow_value:
            os.environ.setdefault("EGRESS_ALLOWLIST", allow_value)

    return provider_registry.get_llm_provider(resolved_provider, **kwargs)
