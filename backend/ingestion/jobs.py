"""
In-process background ingestion queue.

Redis/Celery are intentionally not used. Jobs run on an asyncio worker so the
API can return 202 Accepted for large documents.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from backend.config.logging import logger


@dataclass
class IngestionJob:
    id: str
    path: str
    status: str = "queued"
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class IngestionJobQueue:
    def __init__(self):
        self._jobs: Dict[str, IngestionJob] = {}
        self._queue: Optional[asyncio.Queue] = None
        self._worker_started = False

    def _ensure_queue(self) -> asyncio.Queue:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    async def _worker(self) -> None:
        from backend.ingestion.pipeline import ingestion_pipeline

        while True:
            job_id = await self._queue.get()
            job = self._jobs[job_id]
            job.status = "processing"
            try:
                document = await ingestion_pipeline.ingest_file(job.path)
                job.status = "completed" if document else "failed"
                job.message = document.title if document else "ingestion returned no document"
            except Exception as exc:
                job.status = "failed"
                job.message = str(exc)
                logger.error("[INGEST JOB] %s failed: %s", job_id, exc)
            finally:
                self._queue.task_done()

    def start(self) -> None:
        if self._worker_started:
            return
        self._ensure_queue()
        asyncio.create_task(self._worker())
        self._worker_started = True

    async def enqueue(self, path: str) -> IngestionJob:
        self.start()
        job = IngestionJob(id=str(uuid.uuid4()), path=path)
        self._jobs[job.id] = job
        await self._ensure_queue().put(job.id)
        return job

    def get(self, job_id: str) -> Optional[IngestionJob]:
        return self._jobs.get(job_id)


ingestion_jobs = IngestionJobQueue()
