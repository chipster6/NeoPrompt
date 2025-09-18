"""Deterministic prompt engineering operators and prompt builder."""
from __future__ import annotations
from typing import List, Tuple


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


def op_examples(examples: List[str]) -> str:
    if not examples:
        return ""
    header = "Examples:"
    return header + "\n\n" + "\n\n".join(examples)


def op_quality_bar() -> str:
    return (
        "Answer must be correct, complete, and minimal; address edge cases when relevant."
    )


def build_prompt(
    raw_input: str,
    category: str,
    operators: List[str],
    *,
    force_json: bool = False,
    examples: List[str] | None = None,
) -> Tuple[str, List[str]]:
    """Assemble the engineered prompt using the specified operators in order.
    Returns: (prompt_text, applied_ops)
    """
    applied: List[str] = []
    blocks: List[str] = []
    examples = examples or []

    for op in operators:
        if op == "role_hdr":
            blocks.append(op_role_hdr(category))
            applied.append(op)
        elif op == "constraints":
            blocks.append(op_constraints(category))
            applied.append(op)
        elif op == "io_format":
            blocks.append(op_io_format(force_json))
            applied.append(op)
        elif op == "examples":
            ex = op_examples(examples)
            if ex:
                blocks.append(ex)
                applied.append(op)
        elif op == "quality_bar":
            blocks.append(op_quality_bar())
            applied.append(op)
        else:
            # Unknown operator: skip silently for robustness
            continue

    # Raw task at the end
    blocks.append("TASK:\n" + raw_input.strip())

    prompt = "\n\n".join([b for b in blocks if b.strip()])
    return prompt, applied

