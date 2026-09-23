"""
Structured JSON logging module with request trace context formatting.
"""

import logging
import json
import sys
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom formatter producing JSON structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = getattr(record, "trace_id")
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Initialize structured logging across the application."""
    logger = logging.getLogger("employee_rag")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger


logger = setup_logging()
