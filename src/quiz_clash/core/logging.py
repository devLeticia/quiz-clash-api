import json
import logging
import os
from contextvars import ContextVar
from datetime import UTC, datetime

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

_RECORD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "color_message"}


def _extra_fields(record: logging.LogRecord) -> dict:
    return {k: v for k, v in vars(record).items() if k not in _RECORD_ATTRS}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id.get(),
            **_extra_fields(record),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


LEVEL_COLORS = {"DEBUG": "34", "INFO": "32", "WARNING": "33", "ERROR": "31", "CRITICAL": "1;31"}
REQUEST_COLORS = ["36", "35", "34", "33", "96", "95", "94", "93"]


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


_request_colors: dict[str, str] = {}


def _request_color(rid: str) -> str:
    if rid not in _request_colors:
        if len(_request_colors) >= 1000:
            _request_colors.clear()
        _request_colors[rid] = REQUEST_COLORS[len(_request_colors) % len(REQUEST_COLORS)]
    return _request_colors[rid]


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time = _color(datetime.fromtimestamp(record.created).strftime("%H:%M:%S"), "2")
        level = _color(f"{record.levelname:<7}", LEVEL_COLORS.get(record.levelname, "0"))
        rid = request_id.get()
        rid_text = f"[{rid or '-':<12}]"
        if rid:
            rid_text = _color(rid_text, _request_color(rid))
        message = _color(f"{record.getMessage():<22}", "1")
        fields = " ".join(f"{_color(k + '=', '2')}{v}" for k, v in _extra_fields(record).items())
        line = f"{time} {level} {rid_text} {message} {fields}".rstrip()
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging() -> None:
    handler = logging.StreamHandler()
    json_format = os.getenv("LOG_FORMAT", "text") == "json"
    handler.setFormatter(JsonFormatter() if json_format else TextFormatter())
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), handlers=[handler], force=True)

    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").disabled = True
