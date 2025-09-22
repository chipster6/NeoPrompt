#!/usr/bin/env python3
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    reports_path = Path("reports/rulepacks/junit.xml")
    if not reports_path.exists():
        print("RulePacks Gate B: junit.xml not found at reports/rulepacks/junit.xml")
        return 1

    try:
        root = ET.parse(str(reports_path)).getroot()
    except Exception as e:
        print(f"RulePacks Gate B: failed to parse junit.xml: {e}")
        return 1

    # Aggregate across all testsuite elements (root may be <testsuite> or <testsuites>)
    suites = []
    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = [n for n in root.iter() if n.tag == "testsuite"]

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    for s in suites:
        try:
            total_tests += int(s.attrib.get("tests", 0))
            total_failures += int(s.attrib.get("failures", 0))
            total_errors += int(s.attrib.get("errors", 0))
            total_skipped += int(s.attrib.get("skipped", 0))
        except Exception:
            # Defensive: ignore malformed attributes
            pass

    passed = max(0, total_tests - total_failures - total_errors)
    pass_rate = (passed / total_tests) if total_tests > 0 else 0.0

    print(
        f"RulePacks Gate B: tests={total_tests}, failures={total_failures}, errors={total_errors}, "
        f"skipped={total_skipped}, pass_rate={pass_rate:.2%}"
    )

    if total_tests <= 0:
        print("RulePacks Gate B: FAIL — zero tests in tests/rulepacks")
        return 1
    if pass_rate < 0.95:
        print("RulePacks Gate B: FAIL — pass rate below 95% threshold")
        return 1

    print("RulePacks Gate B: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
