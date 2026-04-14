from __future__ import annotations

import unittest

from utils.research_regression import run_all_research_regressions


class ResearchParserRegressionTests(unittest.TestCase):
    def test_regression_cases(self) -> None:
        results = run_all_research_regressions()
        failures: list[str] = []
        for result in results:
            for assertion in result["assertions"]:
                if not assertion["passed"]:
                    failures.append(f"{result['case_id']}::{assertion['name']} -> {assertion['detail']}")
        if failures:
            self.fail("\n".join(failures))


if __name__ == "__main__":
    unittest.main()
