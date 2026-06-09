import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        request_id = request_id_var.get()
        prefix = f"[request_id={request_id}] " if request_id else ""
        record.msg = f"{prefix}{record.msg}"
        return super().format(record)


def configure_logging(log_level: str = "INFO", *, json_format: bool = True) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    log_dir = Path("data/runtime")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "server.log"

    formatter: logging.Formatter
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = PlainFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
