import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "realtest: mark test to run only on real browser"
    )

@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables from .env.test file"""
    env_file = Path(__file__).parent.parent.parent / '.env.test'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        print(f"\nWarning: {env_file} not found. Create it from .env.test.example for real tests.")
