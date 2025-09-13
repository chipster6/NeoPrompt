"""Guardrails: domain caps, JSON validation, and text hygiene."""
from __future__ import annotations
import json
import re
from typing import Dict, Any, Tuple


def apply_domain_caps(category: str, hparams: Dict[str, Any]) -> Dict[str, Any]:
    """For law/medical, cap temperature <= 0.3."""
    capped = dict(hparams)
    if category in {"law", "medical"}:
        temp = float(capped.get("temperature", 0.0))
        if temp > 0.3:
            capped["temperature"] = 0.3
    return capped


_INJECTION_PATTERNS = [
    r"(?i)ignore (all|any|previous|earlier) instructions",
    r"(?i)disregard (all|any|previous|earlier) instructions",
    r"(?i)you are (now )?a (?:different|new) (?:assistant|model|persona)",
    r"(?i)system prompt",
    r"(?i)developer mode",
    r"(?i)prompt injection",
    r"(?i)jailbreak",
    r"(?i)\bDAN\b",
]


def sanitize_text(text: str) -> str:
    """Strip common prompt-injection phrases and obfuscations from text.
    This is a conservative hygiene step; it does not attempt to fully neutralize attacks.
    """
    cleaned = text
    for pat in _INJECTION_PATTERNS:
        cleaned = re.sub(pat, "", cleaned)
    # Remove stray control fence attempts
    cleaned = re.sub(r"```[a-zA-Z0-9_-]*\n?", "", cleaned)
    # Collapse excessive whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def validate_json_if_required(force_json: bool, content: str) -> Tuple[bool, str]:
    """Validate JSON if requested. Returns (ok, maybe_repaired_content)."""
    if not force_json:
        return True, content
    try:
        json.loads(content)
        return True, content
    except Exception:
        # Attempt a naive auto-repair by trimming to first/last braces
        try:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = content[start : end + 1]
                json.loads(candidate)
                return True, candidate
        except Exception:
            pass
        return False, content
