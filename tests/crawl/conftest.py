import logging
from pathlib import Path

import pytest
from dotenv import load_dotenv


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "realtest: mark test to run only on real browser"
    )


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables from .env.test file"""
    env_file = Path(__file__).parent.parent.parent / ".env.test"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        print(
            f"\nWarning: {env_file} not found. "
            "Create it from .env.test.example for real tests."
        )


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for test execution"""
    # Set up logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # This ensures our configuration takes precedence
    )

    # Ensure crawler logs are visible
    crawler_logger = logging.getLogger("src.schedule.crawler")
    crawler_logger.setLevel(logging.INFO)

    # Create a console handler if none exists
    if not crawler_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        crawler_logger.addHandler(console_handler)
