# syntax=docker/dockerfile:1.9

# ============================================================
# STAGE 1 : BUILDER — installe les dépendances avec uv
# ============================================================
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Couche 1 : dépendances uniquement (invalidée uniquement si uv.lock change)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --no-editable

# Couche 2 : code source + installation du projet
COPY src/ /app/src/
COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ============================================================
# STAGE 2 : RUNTIME — image minimale sans uv
# ============================================================
FROM python:3.12-slim-bookworm AS runtime

ARG APP_UID=10001
RUN groupadd --system --gid ${APP_UID} app \
 && useradd --system --uid ${APP_UID} --gid app \
      --home-dir /app --shell /usr/sbin/nologin app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    # Valeurs par défaut — surchargées par les secrets Docker en prod
    PROXY_HOST=0.0.0.0 \
    PROXY_PORT=443 \
    PROXY_ENV=production \
    PROXY_LOG_LEVEL=INFO \
    PROXY_CERT_FILE=/run/secrets/server_crt \
    PROXY_KEY_FILE=/run/secrets/server_key \
    PROXY_RESPONSES_DIR=/app/responses

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app responses/ /app/responses/

# Les certificats sont montés via Docker secrets (/run/secrets/)
# Port 443 nécessite NET_BIND_SERVICE (voir compose.yaml)
EXPOSE 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "\
import ssl, urllib.request; \
ctx = ssl.create_default_context(); \
ctx.check_hostname = False; \
ctx.verify_mode = ssl.CERT_NONE; \
urllib.request.urlopen('https://localhost:443/', context=ctx, timeout=3)" \
  || exit 1

USER app

ENTRYPOINT ["proxy-lm-studio"]
