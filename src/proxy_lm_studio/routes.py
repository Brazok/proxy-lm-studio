"""Route definitions and matching logic for the mock server."""

from __future__ import annotations

import re
from typing import TypedDict

# ---------------------------------------------------------------------------
# Typed route definitions
# ---------------------------------------------------------------------------


class ExactRoute(TypedDict):
    """A route matched by exact HTTP method, path, and required query parameters."""

    file: str
    content_type: str


class _PatternRouteRequired(TypedDict):
    """Required fields for a pattern-based route."""

    method: str
    pattern: re.Pattern[str]
    required_params: tuple[tuple[str, str], ...]
    file_template: str
    content_type: str


class PatternRoute(_PatternRouteRequired, total=False):
    """A route matched by regex pattern, with an optional fallback file."""

    file_fallback: str


# ---------------------------------------------------------------------------
# Route tables (identical logic to original server.py)
# ---------------------------------------------------------------------------

# Key: (method, path, required_params_tuple)
MOCK_ROUTES: dict[tuple[str, str, tuple[tuple[str, str], ...]], ExactRoute] = {
    ("GET", "/api/v1/models", (("action", "staff-picks"),)): {
        "file": "staff-picks.json",
        "content_type": "application/json; charset=utf-8",
    },
}

MOCK_PATTERN_ROUTES: list[PatternRoute] = [
    # ===== LM Studio API =====
    # Manifest du modèle
    {
        "method": "GET",
        "pattern": re.compile(
            r"^/api/v1/artifacts/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"
        ),
        "required_params": (("manifest", "true"),),
        "file_template": "artifacts/{org}/{model}.json",
        "file_fallback": "artifacts/_default.json",
        "content_type": "application/json; charset=utf-8",
    },
    # README LM Studio
    {
        "method": "GET",
        "pattern": re.compile(
            r"^/api/v1/artifacts/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"
        ),
        "required_params": (("action", "readme"),),
        "file_template": "artifacts/{org}/{model}.readme.md",
        "file_fallback": "artifacts/_default.readme.md",
        "content_type": "text/markdown; charset=utf-8",
    },
    # Thumbnail LM Studio
    {
        "method": "GET",
        "pattern": re.compile(
            r"^/api/v1/artifacts/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"
        ),
        "required_params": (("action", "thumbnail"),),
        "file_template": "artifacts/{org}/{model}/thumbnail.png",
        "file_fallback": "artifacts/_default.thumbnail.png",
        "content_type": "image/png",
    },
    # ===== Hugging Face API =====
    # Liste des fichiers d'un modèle : /api/models/{org}/{model}/tree/{revision}
    {
        "method": "GET",
        "pattern": re.compile(
            r"^/api/models/(?P<org>[^/]+)/(?P<model>[^/]+)/tree/(?P<revision>[^/]+)$"
        ),
        "required_params": (),
        "file_template": "hf/{org}/{model}/{revision}.json",
        "file_fallback": "hf/_default.tree.json",
        "content_type": "application/json; charset=utf-8",
    },
    # Info d'une révision : /api/models/{org}/{model}/revision/{revision}
    {
        "method": "GET",
        "pattern": re.compile(
            r"^/api/models/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"
        ),
        "required_params": (),
        "file_template": "hf/{org}/{model}/revision.json",
        "file_fallback": "hf/_default.revision.json",
        "content_type": "application/json; charset=utf-8",
    },
    # Métadonnées du modèle : /api/models/{org}/{model}
    {
        "method": "GET",
        "pattern": re.compile(r"^/api/models/(?P<org>[^/]+)/(?P<model>[^/]+)$"),
        "required_params": (),
        "file_template": "hf/{org}/{model}/info.json",
        "file_fallback": "hf/_default.info.json",
        "content_type": "application/json; charset=utf-8",
    },
    # Téléchargement : /{org}/{model}/resolve/{revision}/{filename}
    {
        "method": "GET",
        "pattern": re.compile(
            r"^/(?P<org>[^/]+)/(?P<model>[^/]+)/resolve/(?P<revision>[^/]+)/(?P<filename>.+)$"
        ),
        "required_params": (),
        "file_template": "hf/{org}/{model}/files/{filename}",
        "file_fallback": "hf/_default.file",
        "content_type": "application/octet-stream",
    },
]


# ---------------------------------------------------------------------------
# Matching functions (module-level, pure — no I/O)
# ---------------------------------------------------------------------------


def match_exact_route(
    method: str,
    path: str,
    query_tuple: tuple[tuple[str, str], ...],
) -> tuple[ExactRoute, dict[str, str]] | tuple[None, None]:
    """Search MOCK_ROUTES for an exact method/path/params match.

    Args:
        method: HTTP method string (e.g. "GET").
        path: URL path (e.g. "/api/v1/models").
        query_tuple: Sorted tuple of (key, value) query parameter pairs.

    Returns:
        A (route, empty_vars) tuple on match, or (None, None) on miss.
    """
    key = (method, path, query_tuple)
    if key in MOCK_ROUTES:
        return MOCK_ROUTES[key], {}

    for (m, p, required_params), route in MOCK_ROUTES.items():
        if m != method or p != path:
            continue
        if all(param in query_tuple for param in required_params):
            return route, {}

    return None, None


def match_pattern_route(
    method: str,
    path: str,
    query_tuple: tuple[tuple[str, str], ...],
) -> tuple[PatternRoute, dict[str, str]] | tuple[None, None]:
    """Search MOCK_PATTERN_ROUTES for a regex match.

    Args:
        method: HTTP method string.
        path: URL path to match against compiled patterns.
        query_tuple: Sorted tuple of (key, value) query parameter pairs.

    Returns:
        A (route, captured_vars) tuple on match, or (None, None) on miss.
    """
    for route in MOCK_PATTERN_ROUTES:
        if route["method"] != method:
            continue
        match = route["pattern"].match(path)
        if not match:
            continue
        required = route.get("required_params", ())
        if not all(param in query_tuple for param in required):
            continue
        return route, match.groupdict()

    return None, None


def match_route(
    method: str,
    path: str,
    query_tuple: tuple[tuple[str, str], ...],
) -> tuple[ExactRoute | PatternRoute, dict[str, str]] | tuple[None, None]:
    """Try exact routes first, then pattern routes.

    Args:
        method: HTTP method string.
        path: URL path.
        query_tuple: Sorted tuple of (key, value) query parameter pairs.

    Returns:
        A (route, captured_vars) tuple, or (None, None) if no route matches.
    """
    route, captured = match_exact_route(method, path, query_tuple)
    if route is not None and captured is not None:
        return route, captured
    return match_pattern_route(method, path, query_tuple)
