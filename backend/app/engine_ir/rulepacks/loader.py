from __future__ import annotations
import glob
import os
import re
from typing import Any, Dict, List, Tuple, Iterable, Hashable

import yaml

from backend.app.engine_ir.planner.plan import build_operator_plan


# Prefer project-root relative path for rulepacks
RULEPACKS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../configs/rulepacks")
)


# -------------------- Generic helpers --------------------

def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _freeze(x: Any) -> Hashable:
    if isinstance(x, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in x.items()))
    if isinstance(x, list):
        return tuple(_freeze(v) for v in x)
    return x  # assumes hashable scalars


def _append_unique(a: List[Any], b: List[Any]) -> List[Any]:
    seen = {_freeze(x) for x in a}
    out = list(a)
    for x in b:
        fx = _freeze(x)
        if fx not in seen:
            seen.add(fx)
            out.append(x)
    return out


def _is_override_wrapper(v: Any) -> bool:
    return isinstance(v, dict) and bool(v.get("override")) and "value" in v


def _unwrap_override(v: Any) -> Any:
    return v.get("value") if isinstance(v, dict) else v


def _merge_numbers_by_key(key: str, a: float | int | None, b: float | int | None) -> float | int | None:
    if a is None:
        return b
    if b is None:
        return a
    k = (key or "").lower()
    # Limits → take minimum; Richness → take maximum
    if k.startswith("max_") or k.endswith("_limit") or k.endswith("_limits") or k.endswith("_budget"):
        return min(a, b)
    if k.startswith("min_") or k.endswith("_count") or k.endswith("_richness") or k.endswith("_depth"):
        return max(a, b)
    try:
        return max(a, b)
    except Exception:
        return b


def _merge_values(a: Any, b: Any, key_path: Tuple[str, ...]) -> Any:
    # Normalize override wrappers on both sides for list contexts
    if _is_override_wrapper(a):
        a = _unwrap_override(a)
    if _is_override_wrapper(b):
        # Incoming override wins
        return _unwrap_override(b)

    # Dicts
    if isinstance(a, dict) and isinstance(b, dict):
        out: Dict[str, Any] = dict(a)
        # Deterministic traversal by key
        for k in sorted(b.keys()):
            if k in out:
                out[k] = _merge_values(out[k], b[k], key_path + (k,))
            else:
                out[k] = b[k]
        return out

    # Lists → append-unique
    if isinstance(a, list) and isinstance(b, list):
        return _append_unique(a, b)

    # Booleans → last-writer wins (must be checked before numbers since bool is int)
    if isinstance(a, bool) and isinstance(b, bool):
        return b

    # Numbers → key-based min/max, excluding bools
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        key = key_path[-1] if key_path else ""
        return _merge_numbers_by_key(key, a, b)

    # Fallback → incoming wins (last-writer)
    return b


# -------------------- Packs I/O --------------------

def load_packs(paths: List[str]) -> List[Dict[str, Any]]:
    """Load RulePacks from the given directories/files.

    - Accepts directories (non-recursive) and/or explicit files
    - Includes both .yaml and .yml
    - Deterministic ordering by (absdir, filename)
    - Adds _file basename to each loaded pack for traceability
    """
    files: List[str] = []
    for p in paths or []:
        try:
            if os.path.isdir(p):
                files.extend(glob.glob(os.path.join(p, "*.yaml")))
                files.extend(glob.glob(os.path.join(p, "*.yml")))
            elif os.path.isfile(p):
                files.append(p)
        except Exception:
            continue
    # Deduplicate and sort deterministically
    files = sorted(set(files), key=lambda f: (os.path.abspath(os.path.dirname(f)), os.path.basename(f)))

    packs: List[Dict[str, Any]] = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if not isinstance(data, dict):
                data = {}
            data["_file"] = os.path.basename(f)
            packs.append(data)
        except Exception:
            # Skip unreadable/invalid files to keep loader robust
            continue
    return packs


def load_rulepacks() -> List[Dict[str, Any]]:
    """Legacy wrapper that loads from the default RulePacks directory."""
    return load_packs([RULEPACKS_DIR])


# -------------------- Matching --------------------

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


# -------------------- Merge packs --------------------

def merge_packs(packs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge a sequence of RulePacks into a single config according to policy.

    - Lists: append-unique unless incoming uses {override: true, value: [...]}
    - Numbers: min for limits (max_*, *_limit/_limits/_budget), max for richness (min_*, *_count/_richness/_depth), fallback max
    - Booleans: last-writer wins
    - Dicts: deep-merge deterministically
    - Operators: (baseline ∪ include) − exclude with insert_at positioning (unknown anchors degrade deterministically)
    """
    merged_directives: Dict[str, Any] = {}
    baseline_ops: List[str] = []
    include_ops: List[str] = []
    exclude_ops: List[str] = []
    insert_at: Dict[str, Any] = {}

    # Merge directives and collect operator directives
    for p in packs or []:
        # directives
        d = p.get("directives", {}) or {}
        if isinstance(d, dict):
            merged_directives = _merge_values(merged_directives, d, ("directives",))
        # operators collection
        ops = p.get("operators", {}) or {}
        if not baseline_ops and isinstance(ops.get("baseline"), list):
            baseline_ops = list(ops.get("baseline") or [])
        include_ops = _append_unique(include_ops, _as_list(ops.get("include")))
        exclude_ops = _append_unique(exclude_ops, _as_list(ops.get("exclude")))
        ins = ops.get("insert_at", {}) or {}
        if isinstance(ins, dict):
            # last-writer wins per key (stable: apply in sorted key order when planning)
            for k in sorted(ins.keys()):
                insert_at[k] = ins[k]

    operator_directives = {
        "operators": {
            "include": include_ops,
            "exclude": exclude_ops,
            "insert_at": insert_at,
        }
    }
    operator_plan = build_operator_plan(operator_directives, baseline_ops)

    return {
        "directives": merged_directives,
        "operators": {
            "baseline": baseline_ops,
            "include": include_ops,
            "exclude": exclude_ops,
            "insert_at": insert_at,
            "plan": operator_plan,
        },
    }


# -------------------- Resolve API (back-compat) --------------------

def resolve(model: str | None, category: str | None) -> Dict[str, Any]:
    packs = load_rulepacks()

    # Filter by match rules, preserving deterministic order
    matched: List[Dict[str, Any]] = []
    packs_applied: List[str] = []
    for p in packs:
        match = p.get("match", {}) or {}
        m_ok = _match(model, _as_list(match.get("model"))) and _match(
            category, _as_list(match.get("category"))
        )
        if not m_ok:
            continue
        matched.append(p)
        packs_applied.append(p.get("name") or p.get("_file"))

    merged = merge_packs(matched)
    ops = merged.get("operators", {}) or {}

    # Preserve previous resolve() contract
    operator_directives = {
        "operators": {
            "include": list(ops.get("include", []) or []),
            "exclude": list(ops.get("exclude", []) or []),
            "insert_at": dict(ops.get("insert_at", {}) or {}),
        }
    }

    result = {
        "packs_applied": packs_applied,
        "directives": (merged.get("directives", {}) or {}) | operator_directives,
        "baseline_ops": list(ops.get("baseline", []) or []),
        "operator_plan": list(ops.get("plan", []) or []),
    }
    return result
