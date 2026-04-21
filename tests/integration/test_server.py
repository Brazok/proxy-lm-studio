"""Integration tests: spins up the HTTPS server on port 18443 and queries it with httpx."""

from __future__ import annotations

import ssl
import threading
from http.server import HTTPServer
from pathlib import Path

import httpx
import pytest

from proxy_lm_studio.config import Settings
from proxy_lm_studio.handlers import RequestLogger
from proxy_lm_studio.logging_setup import setup_logging

# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------

CERTS_DIR = Path(__file__).parent.parent.parent / "certs"
RESPONSES_DIR = Path(__file__).parent.parent.parent / "responses"

TEST_PORT = 18443
BASE_URL = f"https://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="module")
def https_server():
    """Start the HTTPS mock server in a daemon thread for the test module.

    Uses port 18443 (no sudo required) and the existing self-signed certificates.
    """
    if not CERTS_DIR.is_dir():
        pytest.skip("certs/ directory not found — skipping integration tests")

    # Configure structlog with test settings (no colours, no JSON, just quiet).
    settings = Settings(
        port=TEST_PORT,
        cert_file=CERTS_DIR / "server.crt",
        key_file=CERTS_DIR / "server.key",
        responses_dir=RESPONSES_DIR,
        env="test",
        log_level="WARNING",
    )
    setup_logging(settings)
    RequestLogger.responses_dir = settings.responses_dir

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(
        certfile=str(settings.cert_file),
        keyfile=str(settings.key_file),
    )
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2

    server = HTTPServer(("127.0.0.1", TEST_PORT), RequestLogger)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield BASE_URL

    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def client():
    """httpx client that trusts the local CA certificate."""
    ca_cert = CERTS_DIR / "ca.crt"
    if ca_cert.is_file():
        ssl_ctx = ssl.create_default_context(cafile=str(ca_cert))
    else:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
    with httpx.Client(verify=ssl_ctx, timeout=5.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Exact route tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_staff_picks_returns_200(https_server, client):
    response = client.get(f"{https_server}/api/v1/models?action=staff-picks")
    assert response.status_code == 200


@pytest.mark.integration
def test_staff_picks_returns_json(https_server, client):
    response = client.get(f"{https_server}/api/v1/models?action=staff-picks")
    assert "application/json" in response.headers["content-type"]
    data = response.json()
    assert isinstance(data, list | dict)


# ---------------------------------------------------------------------------
# Pattern route tests — LM Studio
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_lmstudio_manifest_known_model(https_server, client):
    """Known model returns the specific mock file (gemma-4-31b.json)."""
    url = (
        f"{https_server}/api/v1/artifacts/google/gemma-4-31b"
        "/revision/main?manifest=true"
    )
    response = client.get(url)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


@pytest.mark.integration
def test_lmstudio_manifest_unknown_model_uses_fallback(https_server, client):
    """Unknown model falls back to _default.json."""
    url = (
        f"{https_server}/api/v1/artifacts/unknownorg/unknownmodel"
        "/revision/main?manifest=true"
    )
    response = client.get(url)
    # Either 200 (fallback found) or 404 (fallback missing)
    assert response.status_code in {200, 404}


# ---------------------------------------------------------------------------
# Pattern route tests — Hugging Face
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_hf_tree_known_model(https_server, client):
    url = (
        f"{https_server}/api/models/lmstudio-community"
        "/gemma-4-31B-it-GGUF/tree/main"
    )
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.integration
def test_hf_tree_unknown_model_fallback_or_404(https_server, client):
    url = f"{https_server}/api/models/nobody/nomodel/tree/main"
    response = client.get(url)
    assert response.status_code in {200, 404}


@pytest.mark.integration
def test_hf_info_returns_json_or_404(https_server, client):
    url = f"{https_server}/api/models/google/gemma-2"
    response = client.get(url)
    assert response.status_code in {200, 404}


# ---------------------------------------------------------------------------
# Default response for unmatched routes
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_unmatched_route_returns_200(https_server, client):
    response = client.get(f"{https_server}/completely/unknown/path")
    assert response.status_code == 200
    assert b"no mock route matched" in response.content


# ---------------------------------------------------------------------------
# Method handling
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_post_method_handled(https_server, client):
    response = client.post(f"{https_server}/some/endpoint", content=b"payload")
    assert response.status_code == 200


@pytest.mark.integration
def test_options_method_handled(https_server, client):
    response = client.options(f"{https_server}/api/v1/models")
    assert response.status_code == 200
