from loguru import logger

from .logging import setup_logging
from .network import find_free_port, is_port_in_use


def get_logger(name: str) -> logger:
    """Get a logger instance for the given name."""
    return logger.bind(name=name)


__all__ = ["setup_logging", "get_logger", "is_port_in_use", "find_free_port"]
