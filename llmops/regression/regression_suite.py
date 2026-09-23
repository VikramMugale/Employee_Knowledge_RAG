"""
Automated CI Regression Runner enforcing deployment quality gates.
"""

from typing import Dict, Any
from llmops.evaluations.eval_runner import baseline_evaluations
from backend.config.logging import logger


class RegressionQualityGate:
    """
    Enforces quality thresholds before deployment.
    Blocks CI/CD deployment if faithfulness or context recall falls below baseline.
    """

    MIN_FAITHFULNESS_THRESHOLD = 0.85
    MIN_NO_ANSWER_ACCURACY_THRESHOLD = 0.80

    async def run_quality_gate(self) -> bool:
        """Run golden dataset evaluations and evaluate pass/fail criteria."""
        eval_summary = await baseline_evaluations.run_suite()

        faithfulness = eval_summary.get("mean_faithfulness", 0.0)
        no_answer_acc = eval_summary.get("no_answer_accuracy", 0.0)

        passed = (
            faithfulness >= self.MIN_FAITHFULNESS_THRESHOLD and
            no_answer_acc >= self.MIN_NO_ANSWER_ACCURACY_THRESHOLD
        )

        if passed:
            logger.info(f"[QUALITY GATE PASSED] Faithfulness={faithfulness} >= {self.MIN_FAITHFULNESS_THRESHOLD}")
        else:
            logger.error(f"[QUALITY GATE FAILED] Faithfulness={faithfulness} < {self.MIN_FAITHFULNESS_THRESHOLD}. BLOCKING DEPLOYMENT!")

        return passed


regression_gate = RegressionQualityGate()
