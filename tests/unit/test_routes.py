"""Unit tests for the route matching functions (pure, no I/O)."""

from proxy_lm_studio.routes import match_exact_route, match_pattern_route, match_route

# ---------------------------------------------------------------------------
# Exact route matching
# ---------------------------------------------------------------------------


def test_match_exact_route_hit():
    route, captured = match_exact_route(
        "GET", "/api/v1/models", (("action", "staff-picks"),)
    )
    assert route is not None
    assert route["file"] == "staff-picks.json"
    assert captured == {}


def test_match_exact_route_miss_wrong_method():
    route, captured = match_exact_route(
        "POST", "/api/v1/models", (("action", "staff-picks"),)
    )
    assert route is None
    assert captured is None


def test_match_exact_route_miss_wrong_path():
    route, captured = match_exact_route(
        "GET", "/api/v2/models", (("action", "staff-picks"),)
    )
    assert route is None
    assert captured is None


def test_match_exact_route_miss_wrong_params():
    route, captured = match_exact_route(
        "GET", "/api/v1/models", (("action", "unknown"),)
    )
    assert route is None
    assert captured is None


def test_match_exact_route_empty_params_miss():
    route, captured = match_exact_route("GET", "/api/v1/models", ())
    assert route is None
    assert captured is None


# ---------------------------------------------------------------------------
# Pattern route matching — LM Studio
# ---------------------------------------------------------------------------


def test_match_pattern_route_lmstudio_manifest():
    path = "/api/v1/artifacts/google/gemma-3/revision/main"
    route, captured = match_pattern_route("GET", path, (("manifest", "true"),))
    assert route is not None
    assert "artifacts" in route["file_template"]
    assert captured == {"org": "google", "model": "gemma-3", "revision": "main"}


def test_match_pattern_route_lmstudio_manifest_wrong_param():
    path = "/api/v1/artifacts/google/gemma-3/revision/main"
    route, _captured = match_pattern_route("GET", path, ())
    # No required_params match for manifest route — falls through to readme, thumbnail, etc.
    # All LM Studio routes share the same path pattern but differ on required_params.
    # With no params, none of the manifest/readme/thumbnail routes match — but the HF
    # routes don't match either (different path prefix). So result is None.
    assert route is None


def test_match_pattern_route_lmstudio_readme():
    path = "/api/v1/artifacts/google/gemma-3/revision/main"
    route, captured = match_pattern_route("GET", path, (("action", "readme"),))
    assert route is not None
    assert route["content_type"] == "text/markdown; charset=utf-8"
    assert captured["org"] == "google"


def test_match_pattern_route_lmstudio_thumbnail():
    path = "/api/v1/artifacts/nvidia/nemotron/revision/v1"
    route, captured = match_pattern_route("GET", path, (("action", "thumbnail"),))
    assert route is not None
    assert route["content_type"] == "image/png"
    assert captured["model"] == "nemotron"


# ---------------------------------------------------------------------------
# Pattern route matching — Hugging Face
# ---------------------------------------------------------------------------


def test_match_pattern_route_hf_tree():
    path = "/api/models/lmstudio-community/gemma-3-12b/tree/main"
    route, captured = match_pattern_route("GET", path, ())
    assert route is not None
    assert route["file_template"] == "hf/{org}/{model}/{revision}.json"
    assert captured == {
        "org": "lmstudio-community",
        "model": "gemma-3-12b",
        "revision": "main",
    }


def test_match_pattern_route_hf_revision():
    path = "/api/models/mistralai/Mistral-7B-v0.1/revision/refs%2Fpr%2F1"
    route, captured = match_pattern_route("GET", path, ())
    assert route is not None
    assert "revision.json" in route["file_template"]
    assert captured["org"] == "mistralai"


def test_match_pattern_route_hf_info():
    path = "/api/models/google/gemma-2"
    route, captured = match_pattern_route("GET", path, ())
    assert route is not None
    assert "info.json" in route["file_template"]
    assert captured == {"org": "google", "model": "gemma-2"}


def test_match_pattern_route_hf_resolve():
    path = "/lmstudio-community/gemma-3-12b/resolve/main/config.json"
    route, captured = match_pattern_route("GET", path, ())
    assert route is not None
    assert "files/{filename}" in route["file_template"]
    assert captured["filename"] == "config.json"


def test_match_pattern_route_miss():
    route, captured = match_pattern_route("GET", "/completely/unknown/path", ())
    assert route is None
    assert captured is None


def test_match_pattern_route_wrong_method():
    path = "/api/models/google/gemma-2"
    route, captured = match_pattern_route("DELETE", path, ())
    assert route is None
    assert captured is None


# ---------------------------------------------------------------------------
# Combined match_route (exact takes precedence)
# ---------------------------------------------------------------------------


def test_match_route_exact_takes_precedence():
    # This path+params matches both the exact table (first) and potentially
    # nothing in pattern (exact wins before we even try patterns).
    route, captured = match_route(
        "GET", "/api/v1/models", (("action", "staff-picks"),)
    )
    assert route is not None
    assert route.get("file") == "staff-picks.json"
    assert captured == {}


def test_match_route_falls_back_to_pattern():
    path = "/api/models/google/gemma-2"
    route, captured = match_route("GET", path, ())
    assert route is not None
    assert captured is not None
    assert "google" in captured["org"]


def test_match_route_miss():
    route, captured = match_route("GET", "/no/such/route", ())
    assert route is None
    assert captured is None


# ---------------------------------------------------------------------------
# Captured variable correctness
# ---------------------------------------------------------------------------


def test_captured_vars_org_model_revision():
    path = "/api/v1/artifacts/meta-llama/llama-3/revision/v2"
    _, captured = match_pattern_route("GET", path, (("manifest", "true"),))
    assert captured is not None
    assert captured["org"] == "meta-llama"
    assert captured["model"] == "llama-3"
    assert captured["revision"] == "v2"


def test_captured_vars_hf_resolve_with_subpath():
    path = "/myorg/mymodel/resolve/abc123/subfolder/weights.bin"
    _, captured = match_pattern_route("GET", path, ())
    assert captured is not None
    assert captured["filename"] == "subfolder/weights.bin"
