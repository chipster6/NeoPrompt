"""Deterministic prompt engineering operators and prompt builder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

__all__ = [
    "OperatorContext",
    "OperatorBuilder",
    "register_operator",
    "build_prompt",
    "op_role_hdr",
    "op_constraints",
    "op_io_format",
    "op_examples",
    "op_quality_bar",
]


@dataclass(frozen=True)
class OperatorContext:
    """Inputs shared by all operator builders."""

    category: str
    force_json: bool
    examples: Sequence[str]


OperatorBuilder = Callable[[OperatorContext], str | None]


def op_role_hdr(category: str) -> str:
    return f"You are an expert in {category}. Provide precise, correct, concise answers."


def op_constraints(category: str) -> str:
    lines = [
        "No hidden chain-of-thought.",
        "Prefer stepwise explanations for non-trivial tasks.",
        "Cite sources if making factual claims.",
    ]
    if category == "coding":
        lines.append("If coding, include runnable examples when feasible.")
    return "\n".join(lines)


def op_io_format(force_json: bool) -> str:
    if force_json:
        return (
            "If JSON is requested, respond with valid JSON only using the minimal required schema. "
            "Do not include any extra commentary outside JSON."
        )
    return (
        "Format your response with Markdown sections: \n"
        "**TASK**, **ASSUMPTIONS**, **ANSWER**."
    )


def op_examples(examples: Sequence[str]) -> str:
    if not examples:
        return ""
    header = "Examples:"
    return header + "\n\n" + "\n\n".join(examples)


def op_quality_bar() -> str:
    return (
        "Answer must be correct, complete, and minimal; address edge cases when relevant."
    )


def _build_role_hdr(ctx: OperatorContext) -> str:
    return op_role_hdr(ctx.category)


def _build_constraints(ctx: OperatorContext) -> str:
    return op_constraints(ctx.category)


def _build_io_format(ctx: OperatorContext) -> str:
    return op_io_format(ctx.force_json)


def _build_examples(ctx: OperatorContext) -> str | None:
    return op_examples(ctx.examples)


def _build_quality_bar(ctx: OperatorContext) -> str:
    return op_quality_bar()


_DEFAULT_OPERATORS: Dict[str, OperatorBuilder] = {
    "role_hdr": _build_role_hdr,
    "constraints": _build_constraints,
    "io_format": _build_io_format,
    "examples": _build_examples,
    "quality_bar": _build_quality_bar,
}


def register_operator(
    name: str,
    builder: OperatorBuilder,
    *,
    registry: MutableMapping[str, OperatorBuilder] | None = None,
    overwrite: bool = False,
) -> None:
    """Register or override a prompt operator builder."""

    registry = _DEFAULT_OPERATORS if registry is None else registry
    if not name:
        raise ValueError("Operator name must be a non-empty string")
    if not overwrite and name in registry:
        raise ValueError(f"Operator '{name}' is already registered")
    registry[name] = builder


def build_prompt(
    raw_input: str,
    category: str,
    operators: Iterable[str],
    *,
    force_json: bool = False,
    examples: Sequence[str] | None = None,
    registry: Mapping[str, OperatorBuilder] | None = None,
) -> Tuple[str, List[str]]:
    """Assemble the engineered prompt using the specified operators in order.
    Returns: (prompt_text, applied_ops)
    """

    applied: List[str] = []
    blocks: List[str] = []
    registry = registry or _DEFAULT_OPERATORS
    context = OperatorContext(
        category=category,
        force_json=force_json,
        examples=tuple(examples or ()),
    )

    for op in operators:
        builder = registry.get(op)
        if builder is None:
            # Unknown operator: skip silently for robustness
            continue
        block = builder(context)
        if not block:
            continue
        blocks.append(block)
        applied.append(op)

    # Raw task at the end
    blocks.append("TASK:\n" + raw_input.strip())

    prompt = "\n\n".join([b for b in blocks if b.strip()])
    return prompt, applied

