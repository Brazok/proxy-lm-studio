"""Shared pytest fixtures for the proxy_lm_studio test suite."""

import pytest

from proxy_lm_studio.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache on Settings before and after each test.

    This ensures that environment variable patches applied via monkeypatch
    are picked up by get_settings() during the test.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
