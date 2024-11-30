import warnings
import pytest


@pytest.fixture(autouse=True)
def ignore_resource_warnings():
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, module="fake_http_header"
    )
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, module="importlib.resources"
    )
    warnings.filterwarnings(
        "ignore", category=RuntimeWarning, message="coroutine.*was never awaited"
    )
