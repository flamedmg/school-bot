import socket

from loguru import logger


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use.

    Args:
        port: Port number to check

    Returns:
        bool: True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return False
        except OSError:
            logger.warning(f"Port {port} is already in use")
            return True


def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """Find a free port starting from the given port.

    Args:
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try

    Returns:
        int: First free port found

    Raises:
        RuntimeError: If no free port is found after max_attempts
    """
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            logger.info(f"Found free port: {port}")
            return port

    raise RuntimeError(
        f"No free ports found between {start_port} and {start_port + max_attempts}"
    )
