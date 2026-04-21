"""Unit tests for main.py: SSL context creation and startup validation."""

from __future__ import annotations

import ssl
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from proxy_lm_studio.config import Settings
from proxy_lm_studio.exceptions import ConfigurationError
from proxy_lm_studio.main import _build_ssl_context, main

CERTS_DIR = Path(__file__).parent.parent.parent / "certs"


@pytest.fixture
def valid_settings():
    return Settings(
        cert_file=CERTS_DIR / "server.crt",
        key_file=CERTS_DIR / "server.key",
        responses_dir=Path("./responses"),
        env="test",
        log_level="WARNING",
    )


def test_build_ssl_context_valid(valid_settings):
    """Valid cert+key should produce an SSL context without error."""
    if not CERTS_DIR.is_dir():
        pytest.skip("certs/ directory not found")
    ctx = _build_ssl_context(valid_settings)
    assert isinstance(ctx, ssl.SSLContext)


def test_build_ssl_context_missing_cert(tmp_path):
    """Missing cert_file should raise ConfigurationError."""
    settings = Settings(
        cert_file=tmp_path / "nonexistent.crt",
        key_file=tmp_path / "nonexistent.key",
        responses_dir=Path("./responses"),
        env="test",
    )
    with pytest.raises(ConfigurationError, match="Certificate file not found"):
        _build_ssl_context(settings)


def test_build_ssl_context_missing_key(tmp_path):
    """Missing key_file should raise ConfigurationError (when cert exists)."""
    if not CERTS_DIR.is_dir():
        pytest.skip("certs/ directory not found")
    settings = Settings(
        cert_file=CERTS_DIR / "server.crt",
        key_file=tmp_path / "nonexistent.key",
        responses_dir=Path("./responses"),
        env="test",
    )
    with pytest.raises(ConfigurationError, match="Key file not found"):
        _build_ssl_context(settings)


def test_main_runs_and_shuts_down_on_keyboard_interrupt(monkeypatch, tmp_path):
    """main() should start and handle KeyboardInterrupt gracefully."""
    if not CERTS_DIR.is_dir():
        pytest.skip("certs/ directory not found")

    mock_server = MagicMock()
    mock_server.socket = MagicMock()
    mock_server.serve_forever.side_effect = KeyboardInterrupt

    mock_ssl_ctx = MagicMock()
    mock_ssl_ctx.wrap_socket.return_value = MagicMock()

    monkeypatch.setenv("PROXY_PORT", "19444")
    monkeypatch.setenv("PROXY_CERT_FILE", str(CERTS_DIR / "server.crt"))
    monkeypatch.setenv("PROXY_KEY_FILE", str(CERTS_DIR / "server.key"))
    monkeypatch.setenv("PROXY_RESPONSES_DIR", str(tmp_path))
    monkeypatch.setenv("PROXY_ENV", "test")
    monkeypatch.setenv("PROXY_LOG_LEVEL", "WARNING")

    with (
        patch("proxy_lm_studio.main.HTTPServer", return_value=mock_server),
        patch("proxy_lm_studio.main._build_ssl_context", return_value=mock_ssl_ctx),
    ):
        main()

    mock_server.serve_forever.assert_called_once()
    mock_server.server_close.assert_called_once()
