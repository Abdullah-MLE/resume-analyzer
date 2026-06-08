import logging
import sys

# ============================================================
# Centralized Logger for the ATS System
# ============================================================
# Log File: system.log (contains DEBUG and above — everything)
# Console:  INFO and above (so you see important events live)
#
# Usage:
#   from app.core.logger import get_logger
#   logger = get_logger("embedding")   # named child logger
#   logger = get_logger()              # root system logger
# ============================================================

_ROOT_NAME = "ats_system"
_LOG_FILE = "system.log"
_is_configured = False


def _configure_root():
    """Configure the root logger once."""
    global _is_configured
    if _is_configured:
        return
    _is_configured = True

    root = logging.getLogger(_ROOT_NAME)
    root.setLevel(logging.DEBUG)

    # ---- Console Handler (INFO+) ----
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    ))

    # ---- File Handler (DEBUG+) ----
    file = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(name)s │ %(funcName)s:%(lineno)d │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root.addHandler(console)
    root.addHandler(file)


def get_logger(name: str = None):
    """Return a logger.

    - ``get_logger()``            → root ``ats_system`` logger
    - ``get_logger("embedding")`` → child ``ats_system.embedding`` logger
    """
    _configure_root()
    if name:
        return logging.getLogger(f"{_ROOT_NAME}.{name}")
    return logging.getLogger(_ROOT_NAME)
