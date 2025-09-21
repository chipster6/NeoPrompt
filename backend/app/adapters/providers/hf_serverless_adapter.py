from __future__ import annotations
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
from urllib import request, error

from backend.app.metrics import (
    neopr_hf_backoffs_total,
    neopr_hf_rate_limited_total,
)


@dataclass
class CompletionResult:
    model: str
    text: str
    stop_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class HFError(Exception):
    def __init__(self, code: str, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class HFProvider:
    def __init__(
        self,
        base_url: str,
        token: str = "",
        max_retries: int = None,
        backoff_base: float = None,
        backoff_cap: float = None,
        jitter: str = "full",
        sleep_fn=time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token or ""
        self.max_retries = int(os.getenv("HF_RETRIES", max_retries if max_retries is not None else 3))
        self.backoff_base = float(os.getenv("HF_BACKOFF_BASE", backoff_base if backoff_base is not None else 0.6))
        self.backoff_cap = float(os.getenv("HF_BACKOFF_CAP", backoff_cap if backoff_cap is not None else 6.0))
        self.jitter = jitter
        self.sleep_fn = sleep_fn

    def _is_host_allowed(self, url: str) -> bool:
        allow = os.getenv("EGRESS_ALLOWLIST", "").strip()
        if not allow:
            return False
        host = urlparse(url).hostname or ""
        allowed = [h.strip() for h in allow.split(",") if h.strip()]
        for suffix in allowed:
            if host == suffix or host.endswith("." + suffix):
                return True
        return False

    def _check_budget(self, max_tokens: Optional[int]) -> None:
        if max_tokens is None:
            return
        per_call_cap = int(os.getenv("HF_MAX_TOKENS_PER_CALL", "0") or "0")
        if per_call_cap and max_tokens > per_call_cap:
            raise HFError("LLM_BUDGET_EXCEEDED", f"max_tokens {max_tokens} exceeds per-call cap {per_call_cap}")
        budget_total = int(os.getenv("HF_BUDGET_TOKENS", "0") or "0")
        if budget_total and max_tokens > budget_total:
            raise HFError("LLM_BUDGET_EXCEEDED", f"Requested tokens {max_tokens} exceed configured budget {budget_total}")

    def _jitter_sleep(self, attempt: int, retry_after: Optional[float]) -> None:
        if retry_after is not None:
            delay = float(retry_after)
        else:
            base = min(self.backoff_cap, self.backoff_base * (2 ** attempt))
            if self.jitter == "equal":
                delay = base / 2.0 + random.uniform(0, base / 2.0)
            else:
                delay = random.uniform(0, base)
        neopr_hf_backoffs_total.inc()
        self.sleep_fn(delay)

    def _send_request(self, url: str, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any], str]:
        data = json.dumps(body).encode("utf-8")
        req = request.Request(url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=60) as resp:
                status = getattr(resp, "status", 200)
                hdrs = {k: v for k, v in resp.headers.items()}
                text = resp.read().decode("utf-8")
                return status, hdrs, text
        except error.HTTPError as e:
            status = getattr(e, "code", 500)
            hdrs = dict(e.headers or {})
            text = e.read().decode("utf-8") if getattr(e, "fp", None) else ""
            return status, hdrs, text

    def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        json_mode: Optional[bool] = None,
    ) -> CompletionResult:
        path = f"{self.base_url}/models/{model}"
        if not self._is_host_allowed(path):
            raise HFError("EGRESS_BLOCKED", f"Egress to host not allowlisted: {path}")

        self._check_budget(max_tokens)

        headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
        }
        prompt = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])
        parameters: Dict[str, Any] = {}
        if temperature is not None:
            parameters["temperature"] = float(temperature)
        if max_tokens is not None:
            parameters["max_new_tokens"] = int(max_tokens)
        if stop:
            parameters["stop"] = stop
        if json_mode:
            parameters["return_full_text"] = False

        body = {"inputs": prompt, "parameters": parameters}

        last_err_text = ""
        for attempt in range(self.max_retries + 1):
            status, hdrs, text = self._send_request(path, headers, body)
            if status == 200:
                try:
                    data = json.loads(text)
                except Exception:
                    data = {"generated_text": text}
                generated = ""
                if isinstance(data, list) and data and "generated_text" in data[0]:
                    generated = data[0]["generated_text"]
                elif isinstance(data, dict) and "generated_text" in data:
                    generated = data["generated_text"]
                elif isinstance(data, dict) and "choices" in data and data["choices"]:
                    generated = data["choices"][0].get("text", "") or data["choices"][0].get("message", {}).get("content", "")
                else:
                    generated = text
                return CompletionResult(model=model, text=generated, stop_reason=None, usage=None)

            last_err_text = text or ""
            if status == 429:
                neopr_hf_rate_limited_total.inc()
                retry_after = hdrs.get("Retry-After")
                self._jitter_sleep(attempt, float(retry_after) if retry_after else None)
                continue
            if status == 503:
                retry_after = hdrs.get("Retry-After")
                self._jitter_sleep(attempt, float(retry_after) if retry_after else None)
                continue
            raise HFError("LLM_ERROR", f"HF error {status}: {last_err_text or 'unknown'}")

        if "loading" in (last_err_text or "").lower():
            raise HFError("LLM_COLD_START", f"Model cold start after retries: {last_err_text}")
        raise HFError("LLM_RATE_LIMITED", f"Rate limited after retries: {last_err_text}")
