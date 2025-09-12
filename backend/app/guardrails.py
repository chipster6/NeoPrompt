"""Guardrails: domain caps, JSON validation, and text hygiene."""
from __future__ import annotations
import json
from typing import Dict, Any, Tuple


def apply_domain_caps(category: str, hparams: Dict[str, Any]) -> Dict[str, Any]:
    """For law/medical, cap temperature <= 0.3."""
    capped = dict(hparams)
    if category in {"law", "medical"}:
        temp = float(capped.get("temperature", 0.0))
        if temp > 0.3:
            capped["temperature"] = 0.3
    return capped


def sanitize_text(text: str) -> str:
    """Strip common prompt-injection phrases from enhancer output."""
    banned = [
        "ignore previous instructions",
        "disregard earlier instructions",
    ]
    lowered = text
    for b in banned:
        lowered = lowered.replace(b, "")
        lowered = lowered.replace(b.title(), "")
    return lowered


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

