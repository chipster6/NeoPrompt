"""Optional input enhancer: local HuggingFace model or hosted fallback.
The enhancer rewrites the user's raw input for clarity without changing intent.
"""
from __future__ import annotations
import json
import os
from typing import Optional

try:
    from transformers import pipeline
except Exception:  # transformers/torch may be optional
    pipeline = None

try:
    import urllib.request
except Exception:
    urllib = None  # type: ignore

from .guardrails import sanitize_text


class Enhancer:
    """Configurable enhancer with three modes: hosted, local, or fallback.

    Env vars:
    - ENHANCER_ENDPOINT: if set, POSTs to this URL with JSON {text, assistant, category, max_new_tokens}
      Optional ENHANCER_API_KEY used as Bearer token.
    - ENHANCER_MODEL: HF model name for local pipeline (default: google/flan-t5-base)
    - ENHANCER_MAX_NEW_TOKENS: default 128
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or os.getenv("ENHANCER_MODEL", "google/flan-t5-base")
        self._pipe = None
        self.last_mode: str = "fallback"

    def _ensure_pipe(self):
        if self._pipe is None and pipeline is not None:
            try:
                self._pipe = pipeline("text2text-generation", model=self.model_name)
            except Exception:
                self._pipe = None

    def _hosted_enhance(self, prompt: str, max_new_tokens: int) -> Optional[str]:
        endpoint = os.getenv("ENHANCER_ENDPOINT")
        if not endpoint or urllib is None:
            return None
        try:
            payload = json.dumps(
                {
                    "prompt": prompt,
                    "max_new_tokens": max_new_tokens,
                }
            ).encode("utf-8")
            req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
            api_key = os.getenv("ENHANCER_API_KEY")
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                body = resp.read().decode("utf-8")
                try:
                    data = json.loads(body)
                    # accept either {"text": "..."} or raw string
                    if isinstance(data, dict) and "text" in data:
                        return str(data["text"]).strip()
                    return str(data).strip()
                except Exception:
                    return body.strip()
        except Exception:
            return None

    def enhance(self, text: str, assistant: str, category: str, max_new_tokens: Optional[int] = None) -> str:
        max_new_tokens = max_new_tokens or int(os.getenv("ENHANCER_MAX_NEW_TOKENS", "128"))
        prompt = (
            f"Rewrite the user's request for {assistant}, category={category}. "
            "Clarify and structure the request without adding new content.\n\n" + text
        )
        # 1) Hosted first, if configured
        hosted = self._hosted_enhance(prompt, max_new_tokens)
        if hosted is not None:
            self.last_mode = "hosted"
            return sanitize_text(hosted).strip()

        # 2) Local pipeline
        self._ensure_pipe()
        if self._pipe is not None:
            try:
                out = self._pipe(prompt, max_new_tokens=max_new_tokens, num_return_sequences=1)
                self.last_mode = f"local:{self.model_name}"
                return sanitize_text(out[0]["generated_text"]).strip()
            except Exception:
                pass

        # 3) Fallback
        self.last_mode = "fallback"
        return sanitize_text(text).strip()

