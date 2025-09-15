import argparse
import json
import sys
from backend.app.main import app
from backend.app.recipes import RecipesCache


def main():
    parser = argparse.ArgumentParser(description="Validate NeoPrompt recipes and print diagnostics.")
    parser.add_argument("--reload", action="store_true", help="Force reload before validating")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--fail-on", choices=["none", "warning", "error"], default="none", help="Exit non-zero if threshold met")
    args = parser.parse_args()

    cache: RecipesCache = app.state.recipes_cache
    _, errors = cache.ensure_loaded(force=args.reload)

    items = []
    for err in errors:
        severity = "warning" if getattr(err, "error_type", None) == "semantic_validation" else "error"
        items.append({
            "file_path": err.file_path,
            "error": err.error,
            "line_number": err.line_number,
            "error_type": getattr(err, "error_type", None),
            "severity": severity,
        })

    if args.format == "json":
        print(json.dumps({"count": len(items), "items": items}, indent=2))
    else:
        if not items:
            print("No diagnostics found.")
        else:
            for it in items:
                ln = f":{it['line_number']}" if it.get("line_number") else ""
                print(f"[{it['severity']}] {it['error_type'] or 'unknown'} {it['file_path']}{ln}: {it['error']}")

    exit_code = 0
    if args["fail-on"] if isinstance(args, dict) else getattr(args, 'fail_on', 'none'):
        threshold = getattr(args, 'fail_on', 'none')
        if threshold == 'error' and any(i['severity'] == 'error' for i in items):
            exit_code = 2
        elif threshold == 'warning' and any(i['severity'] in ('warning', 'error') for i in items):
            exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
