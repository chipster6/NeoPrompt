"""Optional input enhancer: local HuggingFace model or hosted fallback.
The enhancer rewrites the user's raw input for clarity without changing intent.
"""
from __future__ import annotations
from typing import Optional

try:
    from transformers import pipeline
except Exception:  # transformers/torch may be optional
    pipeline = None


class Enhancer:
    def __init__(self, model_name: str = "google/flan-t5-base") -> None:
        self.model_name = model_name
        self._pipe = None

    def _ensure_pipe(self):
        if self._pipe is None and pipeline is not None:
            try:
                self._pipe = pipeline("text2text-generation", model=self.model_name)
            except Exception:
                self._pipe = None

    def enhance(self, text: str, assistant: str, category: str, max_new_tokens: int = 128) -> str:
        prompt = (
            f"Rewrite the user's request for {assistant}, category={category}. "
            "Clarify and structure the request without adding new content.\n\n" + text
        )
        self._ensure_pipe()
        if self._pipe is None:
            # Fallback: lightweight deterministic cleanup
            return text.strip()
        try:
            out = self._pipe(prompt, max_new_tokens=max_new_tokens, num_return_sequences=1)
            return out[0]["generated_text"].strip()
        except Exception:
            return text.strip()

