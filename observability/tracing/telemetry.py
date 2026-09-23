"""
Langfuse tracing when keys are present; otherwise structured logs only.
"""

import uuid
from typing import Dict, Any, Optional
from backend.config.logging import logger
from backend.config.settings import settings


class TelemetryTracer:
    """Records traces locally and mirrors them to Langfuse when configured."""

    def __init__(self):
        self._langfuse = None
        self._traces: Dict[str, Any] = {}
        self.ready = False

    def connect(self) -> bool:
        if not settings.uses_langfuse():
            logger.info("[LANGFUSE] Keys not set; using local logs only.")
            return False
        try:
            from langfuse import Langfuse

            host = settings.langfuse_host or settings.langfuse_base_url
            self._langfuse = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=host,
            )
            self.ready = True
            logger.info("[LANGFUSE] Connected to %s", host)
            return True
        except Exception as exc:
            self._langfuse = None
            self.ready = False
            logger.error("[LANGFUSE] Unavailable, using local logs: %s", exc)
            return False

    def start_trace(self, name: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        logger.info("[TELEMETRY TRACE START] trace_id=%s name='%s' user_id=%s", trace_id, name, user_id)
        if self._langfuse is not None:
            try:
                if hasattr(self._langfuse, "trace"):
                    handle = self._langfuse.trace(id=trace_id, name=name, user_id=user_id, metadata=metadata or {})
                    self._traces[trace_id] = handle
                elif hasattr(self._langfuse, "start_span"):
                    handle = self._langfuse.start_span(name=name)
                    self._traces[trace_id] = handle
            except Exception as exc:
                logger.error("[LANGFUSE] start_trace failed: %s", exc)
        return trace_id

    def log_span(
        self,
        trace_id: str,
        span_name: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        scores: Optional[Dict[str, float]] = None,
    ):
        score_str = f" scores={scores}" if scores else ""
        logger.info("[TELEMETRY SPAN] trace_id=%s span='%s'%s", trace_id, span_name, score_str)
        handle = self._traces.get(trace_id)
        if handle is None:
            return
        try:
            if hasattr(handle, "span"):
                handle.span(name=span_name, input=inputs, output=outputs)
            if scores and hasattr(handle, "score"):
                for key, value in scores.items():
                    handle.score(name=key, value=value)
        except Exception as exc:
            logger.error("[LANGFUSE] log_span failed: %s", exc)


telemetry_tracer = TelemetryTracer()
