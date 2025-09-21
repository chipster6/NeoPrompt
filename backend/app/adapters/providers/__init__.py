from __future__ import annotations
import os
from typing import Any, Dict

# No heavy imports at module import time; avoid network usage.
_PROVIDER_REGISTRY: Dict[str, Any] = {}


def register_provider(name: str, provider_cls: Any) -> None:
    _PROVIDER_REGISTRY[name] = provider_cls


def get_llm_provider(name: str, **kwargs) -> Any:
    name = (name or "").lower()
    if name not in _PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {name}")
    Provider = _PROVIDER_REGISTRY[name]
    # Do not call network in constructor; only set up config/env
    if not kwargs:
        base_url = os.getenv("HF_BASE", "https://api-inference.huggingface.co")
        token = os.getenv("HF_TOKEN", "")
        return Provider(base_url=base_url, token=token)
    return Provider(**kwargs)


# Late registration to avoid circular import issues
try:
    from .hf_serverless_adapter import HFProvider  # noqa: F401
    register_provider("hf", HFProvider)
except Exception:
    # Registry still importable for Gate D2; specific provider import errors will surface in Track C tests.
    pass
