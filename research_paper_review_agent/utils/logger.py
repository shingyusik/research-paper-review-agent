import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


_logger: Optional[logging.Logger] = None
_log_level: int = logging.INFO


def setup_logger(level: str = "INFO") -> logging.Logger:
    global _logger, _log_level

    _log_level = getattr(logging, level.upper(), logging.INFO)

    if _logger is not None:
        _logger.setLevel(_log_level)
        for handler in _logger.handlers:
            handler.setLevel(_log_level)
        return _logger

    _logger = logging.getLogger("research_paper_review_agent")
    _logger.setLevel(_log_level)
    _logger.propagate = False

    if _logger.handlers:
        _logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_log_level)
    console_format = "[%(asctime)s] %(levelname)s | %(name_short)-16s | %(message)s"
    console_handler.setFormatter(ColorFormatter(console_format, datefmt="%Y-%m-%d %H:%M:%S"))
    _logger.addHandler(console_handler)

    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(_log_level)
    file_format = "[%(asctime)s] %(levelname)-8s | %(name_short)-16s | %(message)s"
    file_handler.setFormatter(logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S"))
    _logger.addHandler(file_handler)

    return _logger


def get_logger(name: str) -> logging.LoggerAdapter:
    global _logger

    if _logger is None:
        setup_logger()

    return logging.LoggerAdapter(_logger, {"name_short": name})

