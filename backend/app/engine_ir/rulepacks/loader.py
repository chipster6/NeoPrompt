from __future__ import annotations
import glob
import os
import re
from typing import Any, Dict, List

import yaml

from backend.app.engine_ir.planner.plan import build_operator_plan


# Prefer project-root relative path for rulepacks
RULEPACKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../configs/rulepacks"))


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _append_unique(a: List[Any], b: List[Any]) -> List[Any]:
    seen = set(a)
    out = list(a)
    for x in b:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _merge_numbers(key: str, a: float | int | None, b: float | int | None) -> float | int | None:
    if a is None:
        return b
    if b is None:
        return a
    key_lower = key.lower()
    # min for limits, max for richness
    if key_lower.startswith("max_") or key_lower.endswith("_limit") or key_lower.endswith("_limits") or key_lower.endswith("_budget"):
        return min(a, b)
    if key_lower.startswith("min_") or key_lower.endswith("_count") or key_lower.endswith("_richness") or key_lower.endswith("_depth"):
        return max(a, b)
    try:
        return max(a, b)
    except Exception:
        return b


def _merge(a: Any, b: Any, key: str | None = None) -> Any:
    # List override form: {"override": true, "value": [...]}
    if isinstance(a, dict) and "override" in a and "value" in a and isinstance(b, (list, dict)):
        return b if isinstance(b, list) else b.get("value", [])
    if isinstance(b, dict) and "override" in b and "value" in b:
        return b.get("value", [])

    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            if k in out:
                out[k] = _merge(out[k], v, k)
            else:
                out[k] = v
        return out

    if isinstance(a, list) and isinstance(b, list):
        return _append_unique(a, b)

    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and key:
        return _merge_numbers(key, a, b)

    return b


def load_rulepacks() -> List[Dict[str, Any]]:
    files = sorted(glob.glob(os.path.join(RULEPACKS_DIR, "*.yaml")))
    packs: List[Dict[str, Any]] = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            data["_file"] = os.path.basename(f)
            packs.append(data)
    return packs


def _match(value: str | None, patterns: List[str] | None) -> bool:
    if not patterns:
        return True
    if not value:
        return False
    for p in patterns:
        if p == value:
            return True
        if "*" in p:
            regex = "^" + re.escape(p).replace("\\*", ".*") + "$"
            if re.match(regex, value):
                return True
        if p in value:
            return True
    return False


def resolve(model: str | None, category: str | None) -> Dict[str, Any]:
    packs = load_rulepacks()
    merged: Dict[str, Any] = {}
    packs_applied: List[str] = []
    op_include: List[str] = []
    op_exclude: List[str] = []
    op_insert_at: Dict[str, Any] = {}
    baseline_ops: List[str] = []

    for p in packs:
        match = p.get("match", {}) or {}
        m_ok = _match(model, _as_list(match.get("model"))) and _match(category, _as_list(match.get("category")))
        if not m_ok:
            continue
        packs_applied.append(p.get("name") or p.get("_file"))

        directives = p.get("directives", {}) or {}
        merged = _merge(merged, directives)

        ops = p.get("operators", {}) or {}
        if not baseline_ops:
            baseline_ops = list(ops.get("baseline", []) or [])
        op_include = _append_unique(op_include, _as_list(ops.get("include")))
        op_exclude = _append_unique(op_exclude, _as_list(ops.get("exclude")))
        ins = ops.get("insert_at", {}) or {}
        op_insert_at.update({k: ins[k] for k in sorted(ins.keys())})

    operator_directives = {
        "operators": {
            "include": op_include,
            "exclude": op_exclude,
            "insert_at": op_insert_at,
        }
    }
    operator_plan = build_operator_plan(operator_directives, baseline_ops)

    result = {
        "packs_applied": packs_applied,
        "directives": merged | operator_directives,
        "baseline_ops": baseline_ops,
        "operator_plan": operator_plan,
    }
    return result
