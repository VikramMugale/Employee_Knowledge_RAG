"""
Developer CLI script to seed the database and vector indexes from data/seed/policies/.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion.pipeline import ingestion_pipeline
from backend.config.logging import logger


async def main():
    logger.info("=== Starting Seed Ingestion ===")
    seed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "seed", "policies"))
    ingested = await ingestion_pipeline.ingest_directory(seed_dir)
    for document in ingested:
        chunk_count = len(ingestion_pipeline.chunks_registry.get(document.id, []))
        logger.info(f"Indexed {chunk_count} chunks for {document.title}")
    logger.info("=== Seed Ingestion Completed Successfully ===")


if __name__ == "__main__":
    asyncio.run(main())
