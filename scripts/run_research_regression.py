from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.research_regression import run_all_research_regressions


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Research Track parser regression checks.")
    parser.add_argument("--case", action="append", dest="case_ids", help="Run only the specified regression case id. Repeatable.")
    args = parser.parse_args()

    results = run_all_research_regressions(case_ids=args.case_ids)
    any_failures = False
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n[{status}] {result['case_id']} - {result['label']}")
        print(f"URL: {result['url']}")
        print(
            "Summary: "
            f"page_type={result['parser_report'].get('page_type', 'unknown')} | "
            f"language={result['parser_report'].get('page_language', 'unknown')} | "
            f"candidates={len(result.get('candidate_names', []))} | "
            f"selected={result.get('selected_name', 'None') or 'None'} | "
            f"email={result.get('selected_email', 'None') or 'None'}"
        )
        if result["parser_report"].get("failure_categories") or result["parser_report"].get("warning_categories"):
            categories = result["parser_report"].get("failure_categories", []) + result["parser_report"].get("warning_categories", [])
            print("Categories:", ", ".join(categories))
        for assertion in result["assertions"]:
            marker = "PASS" if assertion["passed"] else "FAIL"
            print(f"  - [{marker}] {assertion['name']}: {assertion['detail']}")
            if not assertion["passed"]:
                any_failures = True

    return 1 if any_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
