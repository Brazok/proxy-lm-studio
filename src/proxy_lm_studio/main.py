"""Server startup: SSL context, HTTPServer configuration, and graceful shutdown."""

from __future__ import annotations

import ssl
from http.server import HTTPServer

import structlog

from proxy_lm_studio.config import Settings, get_settings
from proxy_lm_studio.exceptions import ConfigurationError
from proxy_lm_studio.handlers import RequestLogger
from proxy_lm_studio.logging_setup import setup_logging
from proxy_lm_studio.routes import MOCK_PATTERN_ROUTES, MOCK_ROUTES

log = structlog.get_logger(__name__)


def _build_ssl_context(settings: Settings) -> ssl.SSLContext:
    """Create and configure the SSL context from certificate files in Settings.

    Args:
        settings: Application settings providing cert_file and key_file paths.

    Returns:
        A configured SSLContext ready to wrap the server socket.

    Raises:
        ConfigurationError: If cert_file or key_file do not exist.
    """
    if not settings.cert_file.is_file():
        raise ConfigurationError(
            f"Certificate file not found: {settings.cert_file}",
            context={"cert_file": str(settings.cert_file)},
        )
    if not settings.key_file.is_file():
        raise ConfigurationError(
            f"Key file not found: {settings.key_file}",
            context={"key_file": str(settings.key_file)},
        )

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=settings.cert_file, keyfile=settings.key_file)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def main() -> None:
    """Configure logging, build the SSL context, and start the HTTPS server."""
    settings = get_settings()
    setup_logging(settings)

    # Inject responses_dir into the handler class (stdlib HTTPServer pattern).
    RequestLogger.responses_dir = settings.responses_dir

    log.info(
        "server.starting",
        host=settings.host,
        port=settings.port,
        responses_dir=str(settings.responses_dir),
        env=settings.env,
    )

    # Log registered routes at startup.
    for (method, path, params), exact_route in MOCK_ROUTES.items():
        params_str = "&".join(f"{k}={v}" for k, v in params)
        full = f"{path}?{params_str}" if params_str else path
        log.debug(
            "route.exact.registered",
            method=method,
            path=full,
            file=exact_route["file"],
        )

    for pattern_route in MOCK_PATTERN_ROUTES:
        params_str = "&".join(
            f"{k}={v}" for k, v in pattern_route.get("required_params", ())
        )
        pattern_str = pattern_route["pattern"].pattern
        full = f"{pattern_str}?{params_str}" if params_str else pattern_str
        log.debug(
            "route.pattern.registered",
            method=pattern_route["method"],
            pattern=full,
            template=pattern_route["file_template"],
        )

    ssl_context = _build_ssl_context(settings)
    server = HTTPServer((settings.host, settings.port), RequestLogger)
    server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

    log.info("server.ready", url=f"https://{settings.host}:{settings.port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("server.shutdown")
    finally:
        server.server_close()
