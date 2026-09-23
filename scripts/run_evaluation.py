"""
Developer CLI script to execute LLMOps baseline evaluation pipeline.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.seed_database import main as seed_main
from llmops.evaluations.eval_runner import baseline_evaluations
from llmops.regression.regression_suite import regression_gate
from backend.config.logging import logger


async def main():
    logger.info("=== Seeding database for evaluation ===")
    await seed_main()

    logger.info("=== Running Baseline Evaluation Suite ===")
    summary = await baseline_evaluations.run_suite()

    logger.info(f"Evaluation Summary: {summary}")

    logger.info("=== Running Quality Gate Check ===")
    gate_passed = await regression_gate.run_quality_gate()
    logger.info(f"Regression Quality Gate Status: {'PASSED' if gate_passed else 'FAILED'}")


if __name__ == "__main__":
    asyncio.run(main())
