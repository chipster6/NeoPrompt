from __future__ import annotations
from typing import Callable, Dict
from backend.app.engine_ir.models.prompt_doc import PromptDoc


def apply_role_hdr(doc: PromptDoc) -> PromptDoc:
    # Deterministically prefix a role header to goal exactly once
    goal = doc.sections.goal or ""
    if not goal.startswith("[Role:"):
        doc.sections.goal = f"[Role: assistant]\n{goal}".strip()
    return doc


def apply_constraints(doc: PromptDoc) -> PromptDoc:
    # Deterministic unique, sorted for stability
    if doc.sections.constraints:
        uniq = sorted(set([c.strip() for c in doc.sections.constraints if c and c.strip()]))
        doc.sections.constraints = uniq
    return doc


def apply_io_format(doc: PromptDoc) -> PromptDoc:
    if not doc.sections.io_format:
        doc.sections.io_format = "Markdown"
    return doc


def apply_examples(doc: PromptDoc) -> PromptDoc:
    if not doc.sections.examples:
        # Add a minimal, deterministic placeholder example
        doc.sections.examples = [{"input": "Example input", "output": "Example output"}]
    return doc


def apply_quality_bar(doc: PromptDoc) -> PromptDoc:
    # Simple deterministic scorer based on present sections
    constraints = len(doc.sections.constraints or [])
    has_io = 1 if (doc.sections.io_format or "").strip() else 0
    has_examples = 1 if (doc.sections.examples or []) else 0
    score = min(1.0, 0.4 + 0.2 * has_io + 0.2 * has_examples + 0.05 * constraints)
    doc.meta.quality.signals["constraints_count"] = constraints
    doc.meta.quality.signals["has_io_format"] = bool(has_io)
    doc.meta.quality.signals["has_examples"] = bool(has_examples)
    doc.meta.quality.score = round(score, 3)
    return doc


OPERATOR_REGISTRY: Dict[str, Callable[[PromptDoc], PromptDoc]] = {
    "apply_role_hdr": apply_role_hdr,
    "apply_constraints": apply_constraints,
    "apply_io_format": apply_io_format,
    "apply_examples": apply_examples,
    "apply_quality_bar": apply_quality_bar,
}


def run_plan(doc: PromptDoc, operator_names: list[str]) -> PromptDoc:
    for name in operator_names:
        fn = OPERATOR_REGISTRY.get(name)
        if fn is None:
            continue
        doc = fn(doc)
    return doc
