from __future__ import annotations
from typing import Any, Dict, Iterable, List, Tuple


def _dedup_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _parse_position_spec(spec: Any) -> Tuple[str, Any]:
    """
    Returns a tuple (kind, value):
      - ('start', None)
      - ('end', None)
      - ('before', 'op_name')
      - ('after', 'op_name')
      - ('index', int)
    """
    if spec is None:
        return ("end", None)
    if isinstance(spec, int):
        return ("index", spec)
    if isinstance(spec, str):
        s = spec.strip()
        if s == "start":
            return ("start", None)
        if s == "end":
            return ("end", None)
        if s.startswith("before:"):
            return ("before", s.split(":", 1)[1].strip())
        if s.startswith("after:"):
            return ("after", s.split(":", 1)[1].strip())
        if s.isdigit():
            return ("index", int(s))
    return ("end", None)


def _reposition(plan: List[str], op: str, spec: Any) -> None:
    kind, val = _parse_position_spec(spec)
    # If op not in plan, append to make position meaningful
    if op not in plan:
        plan.append(op)

    # Remove and compute target index
    plan[:] = [x for x in plan if x != op]
    idx = len(plan)
    if kind == "start":
        idx = 0
    elif kind == "end":
        idx = len(plan)
    elif kind == "before":
        if val in plan:
            idx = plan.index(val)
        else:
            idx = len(plan)
    elif kind == "after":
        if val in plan:
            idx = plan.index(val) + 1
        else:
            idx = len(plan)
    elif kind == "index":
        idx = max(0, min(int(val), len(plan)))
    plan.insert(idx, op)


def build_operator_plan(directives: Dict[str, Any], baseline_ops: List[str]) -> List[str]:
    """
    Combines baseline_ops with directives.operators include/exclude/insert_at.
    Guarantees deterministic ordering and idempotence (no duplicates).
    Directives shape:
      { "operators": {
           "include": [..],
           "exclude": [..],
           "insert_at": {"op":"start|end|before:OP|after:OP|<index>"},
         }}
    """
    ops_d = (directives or {}).get("operators", {}) or {}
    include = list(ops_d.get("include", []) or [])
    exclude = set(ops_d.get("exclude", []) or [])
    insert_at = dict(ops_d.get("insert_at", {}) or {})

    # Start with baseline ∪ include, unique and in that deterministic order
    plan = _dedup_preserve_order(list(baseline_ops or []) + include)

    # Exclude requested ops
    if exclude:
        plan = [op for op in plan if op not in exclude]

    # Apply insert_at with deterministic iteration order by op name
    for op_name in sorted(insert_at.keys()):
        if op_name in exclude:
            # If excluded, ignore insert_at for that op
            continue
        _reposition(plan, op_name, insert_at[op_name])

    # Final idempotence guarantee
    plan = _dedup_preserve_order(plan)
    return plan
