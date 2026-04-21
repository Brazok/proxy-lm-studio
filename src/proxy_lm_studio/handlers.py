"""HTTP request handler with structured logging and typed route dispatch."""

from __future__ import annotations

from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import structlog

from proxy_lm_studio.exceptions import FileServeError
from proxy_lm_studio.logging_setup import bind_request_context
from proxy_lm_studio.routes import ExactRoute, PatternRoute, match_route

log = structlog.get_logger(__name__)


class RequestLogger(BaseHTTPRequestHandler):
    """HTTP request handler that matches routes and serves mock response files.

    The class attribute ``responses_dir`` must be set before the server starts
    (typically in ``main()``). This is the standard pattern for injecting
    configuration into stdlib HTTPServer handlers.
    """

    responses_dir: Path = Path("./responses")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _log_request(self, body: bytes | None = None) -> None:
        """Emit a structured log event with request metadata.

        Args:
            body: Raw request body bytes, if any.
        """
        bind_request_context(
            method=self.command,
            path=self.path,
            client_ip=self.client_address[0],
        )
        log.info(
            "request.received",
            client_port=self.client_address[1],
            headers=dict(self.headers),
            body_bytes=len(body) if body else 0,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def _resolve_file_path(
        self,
        route: ExactRoute | PatternRoute,
        captured_vars: dict[str, str],
    ) -> tuple[Path | None, bool]:
        """Determine which mock file to serve given a matched route and captured vars.

        Args:
            route: The matched route definition (exact or pattern).
            captured_vars: Variables captured from the regex match (empty for exact routes).

        Returns:
            A (path, is_fallback) tuple. Path is None if no file is available.
        """
        if "file_template" in route:
            template: str = route["file_template"]  # type: ignore[typeddict-item]
            try:
                relative = template.format(**captured_vars)
            except KeyError as exc:
                log.warning("route.template.missing_var", key=str(exc))
                relative = ""

            if relative:
                candidate = self.responses_dir / relative
                if candidate.is_file():
                    return candidate, False

            fallback_rel: str | None = route.get("file_fallback")  # type: ignore[assignment]
            if fallback_rel:
                fallback = self.responses_dir / fallback_rel
                if fallback.is_file():
                    log.info("route.fallback.used", fallback=str(fallback))
                    return fallback, True

            return None, False

        file_rel: str | None = route.get("file")
        if file_rel:
            return self.responses_dir / file_rel, False
        return None, False

    def _send_file_response(
        self,
        route: ExactRoute | PatternRoute,
        captured_vars: dict[str, str] | None = None,
    ) -> None:
        """Read the resolved mock file and write it as the HTTP response.

        Args:
            route: The matched route definition.
            captured_vars: Variables for template substitution and response body replacement.

        Raises:
            FileServeError: If the file exists but cannot be read due to an OS error.
        """
        vars_ = captured_vars or {}
        content_type: str = route.get("content_type", "application/octet-stream")

        file_path, is_fallback = self._resolve_file_path(route, vars_)

        if file_path is None or not file_path.is_file():
            log.warning("route.file.not_found", route_keys=list(route.keys()))
            self.send_error(404, "Mock file not found")
            return

        try:
            content = file_path.read_bytes()
        except OSError as exc:
            log.exception("route.file.read_error", path=str(file_path))
            raise FileServeError(
                f"Cannot read mock file: {exc}",
                context={"path": str(file_path)},
            ) from exc

        if vars_:
            try:
                text = content.decode("utf-8")
                for key, value in vars_.items():
                    text = text.replace(f"{{{{{key}}}}}", value)
                content = text.encode("utf-8")
            except UnicodeDecodeError:
                pass  # binary file — skip template substitution

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

        log.info(
            "response.sent",
            file=str(file_path),
            is_fallback=is_fallback,
            size_bytes=len(content),
            captured_vars=vars_,
        )

    def _send_default_response(self) -> None:
        """Send a plain-text 200 for requests with no matching mock route."""
        body = b"Request received (no mock route matched).\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------
    # Request dispatch
    # ------------------------------------------------------------------

    def handle_request(self) -> None:
        """Parse the request URL, match a route, and dispatch the response."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        query_tuple = tuple(sorted((k, v[0]) for k, v in query.items()))

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        self._log_request(body=body)

        route, captured_vars = match_route(self.command, path, query_tuple)
        if route is not None:
            log.info("route.matched", command=self.command, path=path)
            self._send_file_response(route, captured_vars)
        else:
            log.info("route.unmatched", command=self.command, path=path)
            self._send_default_response()

    def do_GET(self) -> None:
        """Handle GET requests."""
        self.handle_request()

    def do_POST(self) -> None:
        """Handle POST requests."""
        self.handle_request()

    def do_PUT(self) -> None:
        """Handle PUT requests."""
        self.handle_request()

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        self.handle_request()

    def do_PATCH(self) -> None:
        """Handle PATCH requests."""
        self.handle_request()

    def do_HEAD(self) -> None:
        """Handle HEAD requests."""
        self.handle_request()

    def do_OPTIONS(self) -> None:
        """Handle OPTIONS requests."""
        self.handle_request()

    def log_message(self, format: str, *args: object) -> None:
        """Suppress the default BaseHTTPRequestHandler access log."""
