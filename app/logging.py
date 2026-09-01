from __future__ import annotations

import json
import logging
import os
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
_SECRET_PATTERN = re.compile(
    r"(?i)(fernet|license|token|secret|password|api[_-]?key|authorization)"
    + r"([\s:=]+)([^,\s;]+)"
)


def redact(value: object) -> str:
    text = str(value)
    text = _SECRET_PATTERN.sub(r"\1=***REDACTED***", text)
    return text[:2000]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "request_id": request_id_context.get(),
        }
        error_code = getattr(record, "error_code", None)
        if error_code is not None:
            event["error_code"] = redact(error_code)
        if record.exc_info:
            event["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(event, ensure_ascii=False)


def configure_logging(
    log_path: str | Path, max_bytes: int = 10_000_000, backup_count: int = 5
) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    root.handlers.clear()
    root.addHandler(handler)
    # Keep uvicorn access logs in the same persistent file.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
