import os
import itertools
from collections import Counter, defaultdict
from typing import Dict, List

from backend.app.main import app
from backend.app.recipes import RecipesCache, RecipeModel


def compute_coverage(recipes: List[RecipeModel]):
    assistants = sorted(set(r.assistant for r in recipes))
    categories = sorted(set(r.category for r in recipes))

    # Expected enums based on current design
    expected_assistants = ["chatgpt", "claude", "deepseek", "gemini"]
    expected_categories = ["coding", "law", "politics", "psychology", "science"]

    matrix_any: Dict[str, Dict[str, bool]] = defaultdict(dict)
    matrix_baseline: Dict[str, Dict[str, bool]] = defaultdict(dict)

    for a, c in itertools.product(expected_assistants, expected_categories):
        any_present = any(r.assistant == a and r.category == c for r in recipes)
        baseline_present = any(r.assistant == a and r.category == c and r.id.endswith('.baseline') for r in recipes)
        matrix_any[a][c] = any_present
        matrix_baseline[a][c] = baseline_present

    return expected_assistants, expected_categories, matrix_any, matrix_baseline


def render_bool(b: bool) -> str:
    return "✔️" if b else "—"


def generate_report() -> str:
    cache: RecipesCache = app.state.recipes_cache
    recs, errs = cache.ensure_loaded(force=True)

    total = len(recs)
    by_assistant = Counter(r.assistant for r in recs)
    by_category = Counter(r.category for r in recs)

    operators = Counter(op for r in recs for op in (r.operators or []))
    has_examples = sum(1 for r in recs if r.examples)

    exp_assts, exp_cats, any_matrix, base_matrix = compute_coverage(recs)

    lines: List[str] = []
    lines.append("# Recipe Library Coverage\n")
    lines.append(f"Total recipes: **{total}**\n")

    lines.append("## By Assistant\n")
    for a in exp_assts:
        lines.append(f"- {a}: {by_assistant.get(a, 0)}")
    lines.append("")

    lines.append("## By Category\n")
    for c in exp_cats:
        lines.append(f"- {c}: {by_category.get(c, 0)}")
    lines.append("")

    lines.append("## Operators Usage\n")
    for op, cnt in operators.most_common():
        lines.append(f"- {op}: {cnt}")
    if not operators:
        lines.append("- (none)")
    lines.append("")

    lines.append(f"Recipes with examples: {has_examples}\n")

    # Matrices
    lines.append("## Coverage Matrix — Any Recipe\n")
    header = "| assistant/category | " + " | ".join(exp_cats) + " |\n"
    sep = "|---|" + "|".join("---" for _ in exp_cats) + "|\n"
    lines.append(header + sep)
    for a in exp_assts:
        row = [render_bool(any_matrix[a][c]) for c in exp_cats]
        lines.append("| " + a + " | " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## Coverage Matrix — Baseline Recipe (.baseline)\n")
    lines.append(header + sep)
    for a in exp_assts:
        row = [render_bool(base_matrix[a][c]) for c in exp_cats]
        lines.append("| " + a + " | " + " | ".join(row) + " |")
    lines.append("")

    # Diagnostics summary
    lines.append("## Diagnostics Summary\n")
    if errs:
        err_types = Counter(getattr(e, 'error_type', 'unknown') for e in errs)
        for et, cnt in err_types.items():
            lines.append(f"- {et}: {cnt}")
    else:
        lines.append("- No diagnostics reported")

    return "\n".join(lines) + "\n"


def main():
    report = generate_report()
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/recipes_coverage.md"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote coverage report to {out_path}")


if __name__ == "__main__":
    main()
