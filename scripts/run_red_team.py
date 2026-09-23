"""
Developer CLI script to execute AI Red Team Security Suite.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from security.red_team.red_team_suite import red_team_suite
from backend.config.logging import logger


async def main():
    logger.info("=== Starting AI Red Team Security Tests ===")
    results = await red_team_suite.run_red_team_tests()
    logger.info(f"Red Team Summary: {results}")


if __name__ == "__main__":
    asyncio.run(main())
