from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

import httpx


class NeoPromptError(Exception):
    pass


@dataclass
class Client:
    base_url: str = os.environ.get("NEOPROMPT_API_BASE", "http://localhost/api")
    timeout: float = 15.0
    _client: Optional[httpx.Client] = None

    def _ensure(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "Client":
        self._ensure()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            return self._ensure().request(method, url, **kwargs)
        except httpx.HTTPError as e:  # pragma: no cover - passthrough
            raise NeoPromptError(str(e)) from e

    # --- API methods ---
    def health(self) -> Dict[str, Any]:
        r = self._request("GET", "/healthz")
        r.raise_for_status()
        return r.json()

    def choose(
        self,
        assistant: str,
        category: str,
        raw: str,
        *,
        enhance: bool = False,
        force_json: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "assistant": assistant,
            "category": category,
            "raw_input": raw,
            "options": {
                "enhance": bool(enhance),
                "force_json": bool(force_json),
            },
        }
        if kwargs:
            payload.update(kwargs)
        r = self._request("POST", "/choose", json=payload)
        r.raise_for_status()
        return r.json()

    def feedback(
        self,
        decision_id: Union[str, int],
        *,
        reward: Union[int, float],
        components: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"decision_id": decision_id, "reward": float(reward)}
        if components:
            payload["reward_components"] = components
        r = self._request("POST", "/feedback", json=payload)
        r.raise_for_status()
        return r.json()

    def history(
        self,
        *,
        limit: Optional[int] = None,
        assistant: Optional[str] = None,
        category: Optional[str] = None,
        with_text: bool = False,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = int(limit)
        if assistant:
            params["assistant"] = assistant
        if category:
            params["category"] = category
        if with_text:
            params["with_text"] = True
        r = self._request("GET", "/history", params=params)
        r.raise_for_status()
        return r.json()

    def prompt_templates(self) -> Dict[str, Any]:
        r = self._request("GET", "/prompt-templates")
        r.raise_for_status()
        return r.json()

    def prompt_templates_schema(self) -> Dict[str, Any]:
        r = self._request("GET", "/prompt-templates/schema")
        r.raise_for_status()
        return r.json()
