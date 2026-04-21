# Python production-ready en 2025 : le guide complet

**L'écosystème Python a basculé en 2025 autour de trois piliers Astral** : `uv` pour les dépendances, `ruff` pour le lint/format, et `ty` qui s'apprête à concurrencer mypy. Les projets modernes consolident tout dans `pyproject.toml`, déploient via multi-stage Docker et sécurisent la supply chain avec Trusted Publishing OIDC. Ce guide couvre, section par section, la stack production-ready attendue en avril 2026 : structure, dépendances, qualité, tests, logging, erreurs, configuration, sécurité, performance, documentation, CI/CD, conteneurs, anti-patterns et bibliothèques incontournables. Chaque section donne les outils recommandés, des exemples concrets, les ✅/❌ et les configurations à adopter.

---

## 1. Structure de projet : `src/` layout et `pyproject.toml` unique

**En 2025, le `src/` layout s'est imposé comme standard PyPA/pyOpenSci**. Le code importable vit dans `src/mon_package/`, et l'import n'est possible **qu'après installation** (`uv sync` / `pip install -e .`). Cela force les tests à s'exécuter sur la version installée — exactement ce qui tournera en production — et empêche les imports accidentels depuis le répertoire courant. Le flat layout reste acceptable pour un prototype ou un notebook, mais tout code destiné à dépasser ce stade doit passer en `src/`.

**Les fichiers essentiels d'un projet 2025** sont : `pyproject.toml` (source unique de vérité, PEP 621), `uv.lock` (commité), `.python-version`, `.gitignore`, `.env` (gitignoré) + `.env.example` (commité), `README.md`, `LICENSE`, `CHANGELOG.md`, `Makefile`, `.pre-commit-config.yaml`. `setup.py` et `setup.cfg` sont **obsolètes** : la PEP 621 (métadonnées) et les PEP 517/518 (build backends) les ont rendus inutiles. Poetry 2.0 (janvier 2025) a lui-même adopté `[project]`. L'appel `python setup.py install` est officiellement banni depuis 2023.

### Arborescence type d'une application

```
my-app/
├── .github/workflows/ci.yml
├── docs/
├── src/
│   └── my_app/
│       ├── __init__.py
│       ├── __main__.py
│       ├── main.py               # FastAPI app
│       ├── config.py             # pydantic-settings
│       ├── api/  core/  services/  models/  db/
├── tests/
│   ├── conftest.py
│   ├── unit/   integration/   e2e/
├── .env.example  .gitignore  .pre-commit-config.yaml  .python-version
├── Dockerfile  compose.yaml  LICENSE  Makefile  README.md
├── pyproject.toml  uv.lock
```

Pour une **librairie distribuable**, ajouter un fichier vide `src/my_lib/py.typed` (PEP 561) qui signale que la librairie expose ses annotations de type — **indispensable en 2025**.

### `pyproject.toml` complet de référence

```toml
[build-system]
requires = ["uv_build>=0.9.15,<0.10.0"]
build-backend = "uv_build"
# Alternatives : hatchling (défaut PyPA), poetry-core, setuptools>=77, maturin (Rust)

[project]
name = "my-app"
version = "0.1.0"
description = "Application production-ready 2025."
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"                          # PEP 639 (SPDX string)
authors = [{ name = "Jean Dupont", email = "jean@example.com" }]
classifiers = [
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "httpx>=0.27",
    "sqlalchemy>=2.0",
    "structlog>=24.1",
]

[project.optional-dependencies]           # extras publiés (utilisateur final)
postgres = ["psycopg[binary]>=3.2"]
redis    = ["redis>=5.0"]

[project.scripts]
my-app = "my_app.__main__:main"

[dependency-groups]                       # PEP 735 — dev-only, non publié
test = ["pytest>=8.3", "pytest-cov>=5.0", "pytest-asyncio>=0.24", "hypothesis>=6.112"]
lint = ["ruff>=0.8", "mypy>=1.13", "pre-commit>=4.0"]
docs = ["mkdocs>=1.6", "mkdocs-material>=9.5", "mkdocstrings[python]>=0.27"]
dev  = [
    {include-group = "test"},
    {include-group = "lint"},
    {include-group = "docs"},
    "ipython>=8.30",
]

[tool.uv]
default-groups = ["dev"]
required-version = ">=0.5.0"
```

La distinction clé de la **PEP 735** (acceptée en 2024, supportée par uv, PDM, pip 25+) : `[project.optional-dependencies]` = extras **publiés** pour l'utilisateur, `[dependency-groups]` = groupes **locaux** pour le développement, jamais publiés.

---

## 2. Gestion des dépendances : la domination d'`uv`

**`uv` (Astral, écrit en Rust) s'est imposé comme le nouveau standard en 2025**. Il remplace à lui seul **pip + pip-tools + pipx + virtualenv + venv + pyenv + twine**. Les arguments sont décisifs : résolution + installation **10 à 100× plus rapides** que pip (un projet de 50 deps se résout en <1 s sur cache chaud), lockfile universel `uv.lock` qui capture **toutes les plateformes × toutes les versions Python** dans un seul fichier, gestion native de Python lui-même (`uv python install 3.13`), compatibilité `uv pip install`, support complet des PEP 621, 508, 517/518, 723 et 735, cache global avec hardlinks entre projets, et workspaces à la Cargo. Un seul binaire Rust installable sans Python.

### Paysage 2026

| Outil | Rôle | Vitesse | Lockfile universel | Gère Python | Verdict |
|---|---|---|---|---|---|
| **uv** | tout-en-un | ⚡⚡⚡ | ✅ `uv.lock` | ✅ | **Standard 2025** |
| Poetry 2.x | deps + build | 🐢 | ✅ `poetry.lock` | ❌ | Mature, stable |
| PDM | deps + build | ⚡ | ✅ `pdm.lock` | Partiel | Propre mais niche |
| Hatch | build + env matrix | moyen | ❌ | ✅ | Excellent pour libs |
| pip + venv + pip-tools | primitifs | 🐢 | via pip-tools | ❌ | Legacy |
| pipenv | deps | 🐢🐢 | Pipfile.lock | ❌ | Obsolète |

### Commandes `uv` essentielles

```bash
# Installation et Python
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12 3.13
uv python pin 3.13

# Projet
uv init --lib my-lib                    # src layout
uv add 'fastapi>=0.115' 'pydantic>=2.10'
uv add --dev pytest ruff mypy
uv add --group test pytest-cov          # PEP 735
uv remove fastapi

# Synchronisation
uv sync                                 # dev
uv sync --frozen --no-dev               # prod / CI
uv sync --locked                        # CI strict (échoue si lock désynchro)

# Exécution
uv run pytest
uv run uvicorn my_app.main:app --reload
uvx ruff check .                        # équivalent pipx

# Build & publish
uv build
uv publish                              # OIDC supporté
uv export --format pylock.toml          # PEP 751
```

### Pinning et lockfile

**Deux niveaux de spécification** : contraintes *abstract* dans `pyproject.toml` (ex. `fastapi>=0.115,<0.116`) et versions *concrete* avec hashes dans `uv.lock`. Règle d'or : **une application commit le lockfile** pour reproduire exactement l'environnement en prod ; **une librairie** commit le lockfile uniquement pour la CI, mais publie avec des `dependencies` larges. En CI, toujours `uv sync --frozen` pour échouer si le lock est désynchronisé.

**❌ Anti-patterns** : `pip install fastapi` sans pin, `pip freeze > requirements.txt` (capture les deps transitives sans structure), `pip install` sans virtualenv, `sudo pip`. **✅ Toujours** travailler en venv (`uv` le crée automatiquement dans `.venv/`), commiter le lockfile, et utiliser des groupes PEP 735 pour séparer runtime / test / docs / lint.

---

## 3. Qualité du code : l'ère Ruff

**Ruff a absorbé Black, Flake8, isort, pyupgrade, pydocstyle et une partie de Bandit**. Écrit en Rust, il est 10 à 100× plus rapide que la chaîne historique. En 2026, sur des projets Black-formatés comme Django ou Zulip, `ruff format` donne >99,9 % de lignes identiques à Black. **Recommandation** : un seul outil pour linter + formatter + trieur d'imports.

### Configuration Ruff recommandée

```toml
[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src", "tests"]
extend-exclude = ["migrations", "build", "dist"]

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true             # formatte aussi le code dans les docstrings

[tool.ruff.lint]
extend-select = [
    "F", "E", "W",   # pyflakes + pycodestyle
    "I",             # isort
    "N",             # pep8-naming
    "UP",            # pyupgrade
    "B",             # flake8-bugbear
    "C4",            # comprehensions
    "SIM",           # simplifications
    "TCH",           # TYPE_CHECKING imports
    "PTH",           # pathlib over os.path
    "RET", "ARG",
    "PL",            # Pylint (règles R/C/W)
    "RUF", "S",      # ruff + bandit (sécurité)
    "D",             # pydocstyle
    "ANN",           # annotations
    "ASYNC", "PERF", "FURB",
]
ignore = ["E501", "ISC001", "D203", "D212", "ANN401", "COM812"]
fixable = ["ALL"]
unfixable = ["F401"]                     # ne pas supprimer auto les imports inutilisés

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "D", "ANN", "ARG", "PLR2004"]
"__init__.py"   = ["F401", "D104"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"
```

### Type checkers : mypy reste la référence, `ty` arrive

**Mypy strict** reste le choix CI en 2026. Pyright/basedpyright (écrit en TypeScript) reste la référence côté éditeur via Pylance. Deux nouveaux venus Rust ont été mis en **beta fin 2025** : **`ty`** (Astral, ex-Red-Knot) et **`pyrefly`** (Meta). Sur Django 5.2, `ty` boucle un check en ~578 ms vs 16 s pour Pyright et un `DNF` pour mypy ; mais la conformance typing reste encore à ~15 % pour `ty` contre ~95 % pour Pyright. **Recommandation 2026** : mypy strict en CI comme référence, Pyright/Pylance pour le feedback éditeur, tester `ty` en parallèle. `ty` 1.0 est attendu courant 2026 — la trajectoire ressemble à celle de Ruff.

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
warn_unused_ignores = true
show_error_codes = true
pretty = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
```

### Type hints modernes (Python 3.12+)

```python
from __future__ import annotations
from typing import Literal, LiteralString, Self, Protocol, TypedDict, assert_never, override

# PEP 695 : syntaxe moderne de généricité
class Stack[T]:
    def __init__(self) -> None: self._items: list[T] = []
    def push(self, item: T) -> None: self._items.append(item)

# Type statement
type UserId = int
type JSON = None | bool | int | float | str | list[JSON] | dict[str, JSON]

# Self pour fluent API
class QueryBuilder:
    def where(self, expr: str) -> Self: ...

# @override (PEP 698)
class Child(Base):
    @override
    def greet(self) -> str: return "hello"

# Exhaustiveness checking
type Shape = Literal["circle", "square", "triangle"]
def area(s: Shape) -> float:
    match s:
        case "circle": return 3.14
        case "square": return 1.0
        case "triangle": return 0.5
        case _: assert_never(s)     # erreur statique si un cas manque
```

**✅ Bonnes pratiques** : `list[int]` au lieu de `List[int]` (PEP 585), `X | Y` au lieu de `Union[X, Y]` (PEP 604), `collections.abc.Iterable` au lieu de `typing.Iterable`, **annoter toutes les fonctions publiques**, `py.typed` dans les libs, imports lourds sous `if TYPE_CHECKING:`. **❌ À bannir** : `typing.Any` par défaut, `# type: ignore` sans code, `from typing import *`.

### PEP 8 et nommage

| Entité | Convention | Exemple |
|---|---|---|
| Module / package | `snake_case` | `user_service.py` |
| Classe / Exception | `PascalCase` | `UserService`, `NotFoundError` |
| Fonction / variable | `snake_case` | `get_user_by_id`, `total_amount` |
| Constante | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 5` |
| Privé | `_leading_underscore` | `self._cache` |
| Dunder | `__name__` | `__init__`, `__repr__` |

Longueur de ligne : **88 caractères** (défaut Black/Ruff). Les 79 strict PEP 8 sont acceptables, 120 tolérables selon les équipes, mais au-delà la lisibilité se dégrade.

---

## 4. Tests : pytest, pyramide et property-based

**pytest domine à >80 % des projets Python en 2025** (enquête JetBrains/PSF). Sa syntaxe `assert x == y` sans subclass, ses fixtures avec injection de dépendances, ses paramétrisations natives et son écosystème de plugins l'imposent face à `unittest`. Structure canonique : `tests/` **miroir** de `src/`, avec sous-dossiers `unit/`, `integration/`, `e2e/` et un `conftest.py` pour les fixtures partagées.

### Configuration pytest + coverage

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "-ra", "--strict-markers", "--strict-config", "--showlocals", "--tb=short",
    "--cov=mypackage", "--cov-branch",
    "--cov-report=term-missing", "--cov-report=xml",
    "--cov-fail-under=85",
]
markers = [
    "slow: tests lents",
    "integration: nécessite services externes",
    "e2e: tests end-to-end",
]
filterwarnings = ["error"]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["src"]
branch = true
parallel = true

[tool.coverage.report]
exclude_also = [
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "@(abc\\.)?abstractmethod",
    "\\.\\.\\.",
]
```

**Viser 85-95 % de couverture, pas 100 %** — la dernière fraction incite à tester du bruit. Activer `branch = true` pour tester les deux issues de chaque `if`. Exclure `if TYPE_CHECKING:` et les stubs Protocol vides.

### Fixtures et paramétrage

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    """Transaction rollback à chaque test pour isolation parfaite."""
    conn = db_engine.connect()
    tx = conn.begin()
    session = sessionmaker(bind=conn)()
    try:
        yield session
    finally:
        session.close(); tx.rollback(); conn.close()

# Parametrize avec ids et marks
@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (1, 2, 3), (0, 0, 0), (-1, 1, 0),
        pytest.param(10**9, 10**9, 2*10**9, id="very-large"),
        pytest.param("a", "b", None, marks=pytest.mark.xfail),
    ],
)
def test_add(a, b, expected):
    assert add(a, b) == expected
```

### Mocking : `pytest-mock` avec `spec=`

```python
def test_http_call(mocker):
    mock_get = mocker.patch("mypackage.client.requests.get")
    mock_get.return_value.json.return_value = {"id": 1}
    mock_get.return_value.status_code = 200
    assert fetch_user(1) == {"id": 1}
    mock_get.assert_called_once_with("https://api/users/1", timeout=5)

def test_spec(mocker):
    mock_user = mocker.MagicMock(spec=User)  # AttributeError si attribut inexistant
    mock_user.name = "A"

@pytest.mark.asyncio
async def test_async_call(mocker):
    mock = mocker.patch("pkg.api.fetch", new_callable=AsyncMock)
    mock.return_value = {"id": 1}
    assert await get_data() == {"id": 1}
```

**Règles d'or mocking** : mocker **là où l'objet est utilisé** (`mypackage.service.requests`, pas `requests`), toujours `spec=Class` pour bloquer les fautes de frappe silencieuses, `new_callable=AsyncMock` pour les coroutines, préférer l'inversion de dépendance au mock pour sa propre logique.

### TDD et property-based

**Cycle TDD** : Red (test qui échoue) → Green (code minimal) → Refactor (amélioration sans casse). **Hypothesis** complète idéalement les tests exemple-based : il génère des centaines d'inputs, trouve les edge cases que vous n'auriez pas imaginés, et **minimise** automatiquement le contre-exemple quand un test échoue.

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_idempotent(xs):
    assert sorted(sorted(xs)) == sorted(xs)

@given(a=st.integers(), b=st.integers())
def test_add_commutative(a, b):
    assert add(a, b) == add(b, a)
```

### Compléments incontournables

**`syrupy`** pour les snapshots (fail si snapshot manquant, matchers pour ignorer UUID/dates dynamiques). **`mutmut`** v3 pour la mutation testing (injecte des modifications dans le code et vérifie que les tests les détectent — complément essentiel du coverage qui ne mesure que l'exécution, pas l'assertion). **`factory-boy` + `Faker`** pour les factories d'objets. **`respx`** ou `pytest-httpx` pour mocker httpx. **`testcontainers-python`** pour lancer Postgres/Redis/Kafka dans Docker en intégration. **`time-machine`** pour geler le temps (plus rapide que `freezegun`). **`pytest-asyncio`** avec `asyncio_mode = "auto"` ou **`anyio`** pour supporter aussi trio.

---

## 5. Logging : `logging` stdlib + `structlog` en production

**Règle pragmatique 2025** : `logging` stdlib comme socle universel, **`structlog` par-dessus** pour enrichir en JSON avec contexte en production, **`loguru`** réservé aux scripts et outils internes.

### `logging` stdlib avec `dictConfig`

```python
import logging, logging.config, sys

LOGGING_CONFIG = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {
        "console": {"format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"},
        "json": {"()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                 "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s %(lineno)d"},
    },
    "handlers": {
        "stdout": {"class": "logging.StreamHandler", "stream": sys.stdout,
                   "formatter": "json", "level": "INFO"},
    },
    "loggers": {
        "": {"handlers": ["stdout"], "level": "INFO"},
        "uvicorn.access": {"level": "WARNING", "propagate": True},
    },
}
logging.config.dictConfig(LOGGING_CONFIG)

# Dans chaque module
logger = logging.getLogger(__name__)

def charge(user_id: int, amount: int) -> None:
    logger.debug("Charging user %s for %s cents", user_id, amount)   # ✅ lazy formatting
    try:
        ...
    except Exception:
        logger.exception("Charge failed for user_id=%s", user_id)   # ✅ traceback complet
        raise
```

### `structlog` : structured logging pour la prod

**Recommandé pour toute application distribuée** (microservices, ELK, Loki, Datadog, Honeycomb). Bind des variables contextuelles (request_id, trace_id), rendu JSON automatique, intégration OpenTelemetry.

```python
import logging, structlog
from structlog.contextvars import merge_contextvars

def setup_structlog(env: str = "production") -> None:
    shared = [
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer = (structlog.processors.JSONRenderer()
                if env == "production"
                else structlog.dev.ConsoleRenderer(colors=True))
    structlog.configure(
        processors=shared + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Middleware FastAPI : bind request_id + trace OTel
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        structlog.contextvars.clear_contextvars()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(
            request_id=request_id, method=request.method, path=request.url.path)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

# Usage
log = structlog.get_logger()
def process_order(order_id: int):
    bound = log.bind(order_id=order_id)
    bound.info("order.processing.start")
    bound.info("order.processing.success", amount_cents=4200)
```

Sortie JSON ingérée telle quelle par Loki/Datadog : `{"timestamp":"2026-04-20T10:15:22Z","level":"info","event":"order.processing.success","order_id":42,"amount_cents":4200,"request_id":"abc-123","trace_id":"5b8efff7..."}`.

### `loguru` pour scripts et CLI

Avantages : zéro-config, rotation intégrée (`rotation="100 MB"`, `retention="30 days"`), `logger.catch` comme décorateur, backtrace enrichi. **Pièges** : `diagnose=True` en prod peut fuiter des valeurs sensibles dans les tracebacks ; prévoir un `InterceptHandler` pour rediriger les logs `logging` vers loguru si des libs tierces utilisent `logging` directement.

**✅ Règles d'or** : un `logger = logging.getLogger(__name__)` par module, niveau via variable `LOG_LEVEL`, **JSON sur stdout en container** (la plateforme collecte), corrélation `request_id` + `trace_id` OTel, `logger.exception` (pas `logger.error(str(e))` qui perd la stack). **❌ À bannir** : `print()` en code métier, f-strings dans les logs chauds (pas de lazy eval), logger des secrets, logs multilignes non-JSON.

---

## 6. Gestion des erreurs et exceptions

**Chaque application production-ready définit une classe racine d'exception** qui permet aux appelants de tout rattraper tout en restant granulaire. Hiérarchie type :

```python
class AppError(Exception):
    default_message = "Application error"
    def __init__(self, message: str | None = None, *, context: dict | None = None):
        super().__init__(message or self.default_message)
        self.context = context or {}

class AuthError(AppError): ...
class InvalidCredentials(AuthError): default_message = "Invalid credentials"
class TokenExpired(AuthError): default_message = "Token expired"

class RepositoryError(AppError): ...
class NotFound(RepositoryError): default_message = "Resource not found"

class ExternalServiceError(AppError): ...
class PaymentGatewayTimeout(ExternalServiceError): ...
```

### Patterns corrects vs anti-patterns

**❌ À bannir absolument** : `except: pass` (avale même `KeyboardInterrupt`/`SystemExit`), `except Exception as e: logger.error(str(e))` (perd le traceback), try géant sur 50 lignes, retry sur `ValueError`/`PermissionError`, exception sans message, utiliser une exception pour le flow normal.

**✅ Pattern correct** :
```python
try:
    charge_card(...)
except PaymentGatewayTimeout:
    raise                                     # retry-safe, on propage
except ExternalServiceError as e:
    logger.exception("payment.external_error")
    raise AppError("Payment unavailable") from e    # exception chaining

# EAFP (style pythonique) plutôt que LBYL
try:
    value = d["key"]["sub"]
except (KeyError, TypeError):
    value = default
```

### `ExceptionGroup` et `except*` (Python 3.11+)

Nouveauté essentielle pour `asyncio.TaskGroup` et tout code concurrent. `except*` filtre par type et laisse passer les autres sous-exceptions.

```python
async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fetch("https://api.a/"))
            tg.create_task(fetch("https://api.b/"))
            tg.create_task(fetch("https://api.c/"))
    except* httpx.TimeoutException as eg:
        for exc in eg.exceptions:
            logger.warning("timeout", url=str(exc.request.url))
    except* httpx.HTTPStatusError as eg:
        for exc in eg.exceptions:
            logger.error("http_error", status=exc.response.status_code)
```

### Retry avec `tenacity`

```python
from tenacity import (retry, stop_after_attempt, wait_exponential_jitter,
                      retry_if_exception_type, before_sleep_log)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, max=30),        # backoff + jitter
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_invoice(invoice_id: str) -> dict:
    r = httpx.get(f"https://api.billing/{invoice_id}", timeout=3)
    r.raise_for_status()
    return r.json()
```

**Règles retry** : retry uniquement les erreurs transitoires (timeouts, 5xx, réseau, 429 avec respect du `Retry-After`), **jamais** les 4xx sauf 408/425/429, jamais les `ValidationError`, toujours un `stop_after_attempt` fini avec jitter pour éviter les *thundering herds*.

### Context managers pour le cleanup

```python
from contextlib import contextmanager, ExitStack

@contextmanager
def transaction(conn):
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

# Stack dynamique de ressources
with ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]
    process(files)                              # tous fermés auto
```

---

## 7. Configuration et variables d'environnement : `pydantic-settings` v2

**Hiérarchie de configuration 12-Factor** : defaults codés → fichier config (TOML/YAML) → `.env` → variables d'environnement → arguments CLI → overrides constructeur (tests). `pydantic-settings` v2 (2.14.0 en avril 2026) implémente précisément cette hiérarchie via `settings_customise_sources()`, avec validation stricte, type-safety, `SecretStr` qui masque les valeurs sensibles à `repr()`, et lecture automatique des secrets Docker dans `/run/secrets`.

### Exemple complet

```python
from enum import StrEnum
from functools import lru_cache
from typing import Literal
from pydantic import Field, PostgresDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Environment(StrEnum):
    DEV = "development"; STAGING = "staging"; PROD = "production"; TEST = "test"

class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: SecretStr = SecretStr("")
    name: str = "app"
    pool_size: int = Field(default=5, ge=1, le=100)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.defaults", ".env"),
        env_nested_delimiter="__",              # DB__HOST, DB__PORT
        env_ignore_empty=True,
        extra="forbid",                         # bloque les typos
        secrets_dir="/run/secrets",             # Docker secrets
    )

    app_name: str = "my-app"
    environment: Environment = Environment.DEV
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    secret_key: SecretStr
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @model_validator(mode="after")
    def _prod_invariants(self) -> "Settings":
        if self.environment is Environment.PROD:
            if self.debug:
                raise ValueError("DEBUG interdit en production")
            if len(self.secret_key.get_secret_value()) < 32:
                raise ValueError("SECRET_KEY >= 32 caractères requis")
        return self

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

### `.env.example` commité

```dotenv
# Copier en .env : `cp .env.example .env` — NE JAMAIS commiter .env !
APP_NAME=my-app
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=change-me-use-at-least-32-chars-xxxxxxxxxx
DB__HOST=localhost
DB__PORT=5432
DB__PASSWORD=postgres
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Environnements multiples

**En dev** : `.env` + `direnv` (optionnel, charge/décharge automatiquement à l'entrée du dossier, peut s'intégrer à 1Password/sops). **En prod, ne JAMAIS utiliser de `.env`** : injecter les variables via Kubernetes `Secret` + `envFrom`, Docker secrets (`/run/secrets/<name>`), systemd `EnvironmentFile=`, ou un cloud secret manager.

### Gestion des secrets

| Outil | Cas d'usage |
|---|---|
| **HashiCorp Vault** | Grandes orgs, secrets dynamiques (credentials DB rotés), multi-cloud |
| **AWS Secrets Manager / GCP Secret Manager / Azure Key Vault** | Cloud-natif, rotation auto |
| **Doppler / Infisical** | SaaS developer-first, DX rapide |
| **1Password Secrets Automation** | Équipes 1Password, CLI `op` puissante |
| **SOPS (Mozilla)** | GitOps, chiffre YAML/JSON avec KMS/age/PGP |
| **Sealed Secrets (Bitnami)** | Kubernetes, commiter des secrets chiffrés dans Git |
| **direnv** | Shell dev local |

**❌ À bannir** : hardcoder un secret (`API_KEY = "sk-proj-abc..."`), commiter `.env` même "juste pour dev", logger un secret en clair (`logger.info(f"Using key: {settings.api_key}")`), `os.environ.get("KEY", "hardcoded-fallback")`, secrets en paramètre CLI (visible dans `ps aux`) ou dans l'URL (logs de proxies). **Statistique Verizon DBIR 2025** : 10 millions de credentials ont fuité depuis GitHub en 2025, l'erreur initiale étant quasi toujours un `.env` commité ou une clé hardcodée.

---

## 8. Sécurité : Ruff S-rules, pip-audit, Argon2

**Ruff intègre nativement les règles `flake8-bandit` (préfixe `S`)** — 10 à 100× plus rapide que Bandit seul, exécuté à chaque save. Règles S notables : `S102` (exec), `S301` (pickle), `S307` (eval), `S324` (MD5/SHA1), `S501` (requests verify=False), `S602/S605` (subprocess shell=True), `S608` (SQL string concat), `S506` (yaml.load unsafe).

### Audit des dépendances

**`pip-audit` (maintenu par le PyPA, source OSV.dev + PyPI advisory DB)** a remplacé `safety` dont la DB communautaire est devenue payante pour usage commercial. Les attaques de 2024-2025 — **Ultralytics (PyPI, compromission GitHub Actions)**, **Shai-Hulud worm (nov. 2025, npm → PyPI via monorepos)** — ont rendu la supply chain prioritaire. PyPI a traité 2000+ signalements de malware en 2025 avec 66 % résolus en <4h et introduit un système de quarantaine.

**Bonnes pratiques supply chain 2025** : lockfile avec hashes (`uv lock` ou `pip-compile --generate-hashes`), `uv sync --frozen` en installation reproductible, **Trusted Publishing OIDC** pour PyPI (tokens éphémères 15 min, attestations Sigstore auto — plus aucun secret long-lived), SBOM CycloneDX généré à la build, détection de secrets en pre-commit (`gitleaks`, `detect-secrets`), Renovate/Dependabot avec auto-merge des patch CVEs.

### Code vulnérable vs sécurisé

```python
# ❌ Injection SQL
cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
# ✅
cur.execute("SELECT * FROM users WHERE name = %s", (name,))

# ❌ Command injection
subprocess.run(f"convert {user_file} out.png", shell=True)
# ✅
subprocess.run(["convert", user_file, "out.png"], check=True)

# ❌ Désérialisation catastrophique (RCE)
obj = pickle.loads(untrusted_bytes)
cfg = yaml.load(untrusted_yaml)
# ✅
obj = json.loads(untrusted_bytes)
cfg = yaml.safe_load(untrusted_yaml)

# ❌ TLS
requests.get(url, verify=False)
# ✅
requests.get(url, timeout=10)            # verify=True par défaut

# ❌ Random pour secrets
token = random.random()
# ✅
token = secrets.token_urlsafe(32)
```

### Hachage de mot de passe : Argon2id

**OWASP 2025** recommande **Argon2id** par défaut, sinon bcrypt. **À BANNIR** : `hashlib.sha256(password)`, `hashlib.md5`, `crypt`.

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Paramètres OWASP 2025 : m=64 MiB, t=3, p=4
ph = PasswordHasher(time_cost=3, memory_cost=64*1024, parallelism=4,
                    hash_len=32, salt_len=16)

hash_str = ph.hash("correct horse battery staple")

def verify(stored_hash: str, candidate: str) -> bool:
    try:
        ph.verify(stored_hash, candidate)
    except (VerifyMismatchError, InvalidHashError):
        return False
    if ph.check_needs_rehash(stored_hash):       # rehash si params ont évolué
        save_new_hash(ph.hash(candidate))
    return True
```

Pour la cryptographie générale : **`cryptography`** (PyCA, bindings OpenSSL) — **pas** `pycrypto`. AEAD moderne : `AESGCM` ou `ChaCha20Poly1305` depuis `cryptography.hazmat`. Pour chiffrement simple symétrique : `Fernet`.

### Checklist sécurité rapide

| ❌ À éviter | ✅ À la place |
|---|---|
| `eval` / `exec` sur input | `ast.literal_eval` si structure simple |
| `pickle.loads` sur data externe | `json`, `msgpack`, protobuf |
| `yaml.load` | `yaml.safe_load` |
| `shell=True` avec input utilisateur | liste d'args, `shlex.quote` |
| `tempfile.mktemp()` | `tempfile.NamedTemporaryFile` |
| `random` pour cryptographie | `secrets` |
| `hashlib.sha256` pour mot de passe | `argon2-cffi` / `bcrypt` |
| Secret dans le code / Git | Vault / Secrets Manager |
| `assert` pour sécurité runtime | `if not ...: raise` (asserts OFF avec `-O`) |
| `requests` sans `timeout` | `timeout=(connect, read)` toujours |

---

## 9. Performance : profiler d'abord, optimiser ensuite

**Règle #1 : mesurer avant d'optimiser**. Algorithmes et structures de données d'abord — un passage de `O(n²)` à `O(n log n)` bat toute micro-optimisation.

### Arsenal de profiling 2025

| Outil | Type | Overhead | Cas d'usage |
|---|---|---|---|
| **`py-spy`** | Sampling Rust hors-process | Très faible | **Production**, attach à PID |
| **`scalene`** | CPU + mémoire + GPU, distingue Python vs C | Faible | **Dev moderne**, notebooks |
| `pyinstrument` | Sampling, call-stack | Faible | Web apps, rapports HTML |
| `cProfile` (stdlib) | Deterministic | Moyen/haut | Baseline locale, `.prof` |
| `line_profiler` | Ligne par ligne | Élevé | Focus sur une fonction |
| `memray` (Bloomberg) | Mémoire, flamegraph | Moyen | Fuites mémoire |
| `austin` | Frame stack sampler | Très faible | Prod-like |

**py-spy** est le champion pour la production : aucune modification de code, écrit en Rust, safe en prod :
```bash
sudo py-spy top --pid 12345                          # top interactif
sudo py-spy record -o flame.svg --pid 12345 --duration 30
sudo py-spy dump --pid 12345                         # stacks (deadlock ?)
```

**Scalene** distingue temps Python vs temps natif et les copies mémoire — inestimable pour comprendre *"pourquoi ce code numpy est lent"*.

### Optimisations courantes

```python
# Structures de données : O(n) → O(1)
if item in my_list: ...                  # ❌ O(n)
if item in set(my_list): ...             # ✅ O(1)

# collections spécialisées
from collections import Counter, deque, defaultdict
counts = Counter(words)
q = deque(maxlen=100)                    # O(1) append/popleft

# Générateurs pour mémoire constante
def read_large(path):
    with open(path) as f:
        for line in f:
            yield process(line)

# Caching mémoïsation
from functools import cache, lru_cache
@cache
def factorial(n): return 1 if n <= 1 else n * factorial(n-1)

# Binding local dans hot loops
def fast(xs, _sqrt=math.sqrt):
    return [_sqrt(x) for x in xs]
```

### Data : polars, duckdb, pyarrow

**Polars** (Rust, lazy, multi-thread, Arrow) s'impose en 2025 pour les pipelines analytiques, souvent **10-100× plus rapide** que pandas grâce au query planner qui optimise la chaîne avant exécution.

```python
import polars as pl
df = (pl.scan_csv("events.csv")                    # lazy
        .filter(pl.col("status") == "ok")
        .group_by("user_id")
        .agg(pl.col("amount").sum().alias("total"))
        .sort("total", descending=True)
        .collect())                                # exécution ici, pushdown + parallélisation
```

### Code critique : Numba, PyO3, Cython

| Outil | Idéal pour |
|---|---|
| **Numba** | Boucles numériques, `@njit`, intégration numpy |
| **Cython** | Modules C-like typés |
| **mypyc** | Compiler du Python typé mypy en C (2-5×) |
| **PyO3 + maturin** | Extensions **Rust** natives — **choix 2025** pour perf + sécurité mémoire |

### GIL : l'état des lieux en 2025

**Python 3.13 (oct. 2024)** : premier build **free-threaded** officiel (dit "3.13t"), GIL optionnel via `--disable-gil`. **Python 3.14 (oct. 2025)** : overhead single-thread passé de ~40 % à ~9 %, speedup mesuré sur 4 threads CPU-bound à **~3.1×** vs GIL (2.2× en 3.13t). JIT expérimental (copy-and-patch) activable via `PYTHON_JIT=1`, encore modeste. Subinterpreters (PEP 684/734) : chaque sub-interpreter a son GIL depuis 3.12, API `concurrent.interpreters` en 3.14.

**Recommandation prod 2025** : service web I/O bound → CPython 3.13/3.14 standard, asyncio suffit. Pipeline CPU bound multi-cœurs où fork/pickle coûte cher → tester **3.14t** (free-threaded). **Ne pas activer le JIT en prod** tant qu'il est marqué expérimental.

### Concurrence : règle de choix

- **I/O bound** (HTTP, DB, disque) → **`asyncio`** (httpx, asyncpg, aiofiles)
- **CPU bound** → **`multiprocessing`** ou free-threaded 3.13t ou libs natives (numpy/numba/Rust)
- **Mixte** → `asyncio.to_thread(...)` pour isoler le blocant

**❌ Règles à connaître** : pas de threading pour CPU-bound en CPython GIL-enabled (inutile), jamais `time.sleep()` dans du async (`await asyncio.sleep`), jamais `result += chunk` dans une boucle (O(n²) — utiliser `"".join()`), pas de `len()` dans une condition `while` serrée.

---

## 10. Documentation : docstrings Google + MkDocs Material

**Google style est le choix par défaut 2026** — plus lisible, compacte, adoptée par FastAPI, Google, mkdocstrings. NumPy style reste le standard scientifique (pandas, scikit-learn, NumPy). Sphinx/reST est verbeux et à réserver aux projets historiques.

```python
def fetch_user(user_id: int, include_orders: bool = False) -> User:
    """Récupère un utilisateur par son ID.

    Example:
        >>> fetch_user(1)
        User(id=1, name='Alice')

    Args:
        user_id: L'identifiant unique de l'utilisateur.
        include_orders: Si True, charge les commandes associées.

    Returns:
        L'instance User correspondante.

    Raises:
        UserNotFoundError: Si aucun utilisateur n'existe avec cet ID.
        ConnectionError: Si la base de données est injoignable.
    """
```

**✅ Bonnes pratiques** : première ligne = phrase impérative courte (<72 car) avec point final, ligne vide avant le corps détaillé, documenter **toutes** les exceptions dans `Raises:`, inclure des exemples `>>>` testables avec `doctest`, ne pas dupliquer les types si PEP 484 présent. **❌ À bannir** : mélanger deux styles, `# comment` au lieu de docstring, redondance (`"""Gets the user."""` pour `def get_user()`).

### MkDocs Material : recommandation moderne 2026

Utilisée par FastAPI, Pydantic, Typer, Textual, HTTPX, Starlette. Markdown natif, thème Material ultra-moderne out-of-the-box, live reload instantané, recherche client-side native, déploiement trivial sur GitHub Pages. **`mkdocstrings[python]`** génère automatiquement la référence API à partir des docstrings Google.

```yaml
# mkdocs.yml
site_name: "mypackage"
theme:
  name: material
  features: [navigation.instant, navigation.tabs, content.code.copy, content.code.annotate]
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
    - media: "(prefers-color-scheme: dark)"
      scheme: slate

plugins:
  - search
  - autorefs
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
            show_source: true
            show_signature_annotations: true
            separate_signature: true
            members_order: source
          inventories:
            - https://docs.python.org/3/objects.inv

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.highlight
  - pymdownx.tabbed
```

Dans `docs/reference/core.md` : `::: mypackage.core` suffit à générer toute la référence.

### Sphinx : quand le choisir

Sphinx reste le choix pour les projets scientifiques (support reST mature, intersphinx riche, versioning natif avec ReadTheDocs, PDF/ePub natifs). Stack moderne Sphinx : `sphinx.ext.autodoc` + `napoleon` (styles Google/NumPy) + `myst-parser` (Markdown) + thème `furo` ou `sphinx-book-theme` + `sphinx-copybutton`.

### Documents projet

**README.md** avec badges (PyPI, CI, coverage, license), installation, quick start, lien docs. **CHANGELOG.md** au format [Keep-a-Changelog](https://keepachangelog.com/) avec sections `Added/Changed/Deprecated/Removed/Fixed/Security`. **CONTRIBUTING.md** pour l'onboarding contributeur. Automatiser le changelog avec `towncrier`, `scriv`, `git-cliff` ou `python-semantic-release` à partir de commits Conventional Commits.

---

## 11. CI/CD : GitHub Actions + uv + OIDC

### Workflow GitHub Actions complet (2026)

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      - run: uv python install 3.13
      - run: uv sync --locked --all-extras --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with: { enable-cache: true }
      - run: uv sync --locked --dev
      - run: uv run mypy src/

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          python-version: ${{ matrix.python-version }}
      - run: uv sync --locked --all-extras --dev
      - run: uv run pytest --cov=src --cov-report=xml -n auto
      - uses: codecov/codecov-action@v4
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.13'

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
      - run: uv sync --locked --dev
      - run: uv run bandit -r src/
      - run: uv run pip-audit
      - uses: aquasecurity/trivy-action@master
        with: { scan-type: fs, severity: HIGH,CRITICAL }

  publish:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: [lint, typecheck, test, security]
    runs-on: ubuntu-latest
    environment: { name: pypi, url: https://pypi.org/p/myproject }
    permissions:
      id-token: write                            # requis OIDC
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
        # Aucun token : OIDC + attestations Sigstore auto
```

### Trusted Publishing (OIDC) : la fin des tokens PyPI

`twine` est en déclin ; **`pypa/gh-action-pypi-publish@release/v1`** (OIDC) ou **`uv publish`** sont les voies 2026. Tokens éphémères 15 minutes, attestations Sigstore automatiques depuis nov. 2024, pas de rotation manuelle, audit côté PyPI (quel commit/workflow a publié). **Ne jamais** stocker `PYPI_API_TOKEN` en secret long-lived (cf. attaque supply chain `litellm` du 24 mars 2025).

### `.pre-commit-config.yaml` moderne

```yaml
default_language_version:
  python: python3.13
default_stages: [pre-commit, pre-push]

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ["--maxkb=1000"]
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.11
    hooks:
      - id: ruff-check
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.19.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0, types-requests]
        args: [--strict, --ignore-missing-imports]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.11.7
    hooks:
      - id: uv-lock
      - id: uv-export
        args: ["--frozen", "--output-file=requirements.txt"]

  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.1.0
    hooks:
      - id: commitizen
        stages: [commit-msg]
```

**Ordre crucial** : `ruff-check --fix` **avant** `ruff-format` pour que le format corrige le code fixé.

### Versioning et changelog

**python-semantic-release** : tout-en-un — parse Conventional Commits → bump version + changelog + tag + release GitHub + publish. **git-cliff** (Rust) : générateur de changelog rapide et configurable. **release-please** (Google) : GitHub Action qui crée des PR de release automatisées. **nox** avec `venv_backend="uv"` remplace avantageusement tox pour les matrices multi-Python locales.

---

## 12. Containerisation : multi-stage `uv` + `slim`

### Dockerfile multi-stage complet

```dockerfile
# syntax=docker/dockerfile:1.9
# ============ STAGE 1 : BUILDER ============
FROM python:3.13-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 1) Deps UNIQUEMENT (layer cachable)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --no-editable

# 2) Code source et projet
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ============ STAGE 2 : RUNTIME ============
FROM python:3.13-slim-trixie AS runtime

ARG APP_UID=10001
RUN groupadd --system --gid ${APP_UID} app \
 && useradd --system --uid ${APP_UID} --gid app \
      --home-dir /app --shell /usr/sbin/nologin app

# tini pour SIGTERM propre
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", \
     "--port", "8000", "--workers", "4", "myapp.main:app"]
```

### Choix de l'image de base

| Image | Taille | Pour qui |
|---|---|---|
| **`python:3.13-slim-trixie`** (Debian, glibc) | ~45 MB | **Défaut recommandé** — compatible toutes wheels PyPI |
| `python:3.13-alpine` (musl) | ~25 MB | Uniquement si pas de deps C/Rust — rebuild souvent obligatoire |
| `gcr.io/distroless/python3-debian12` | ~50 MB | Durcissement (pas de shell) — usage avancé |
| `cgr.dev/chainguard/python` | ~40 MB | CVE minimal, SBOM inclus, sécurité renforcée |
| `ghcr.io/astral-sh/uv:python3.13-bookworm-slim` | ~80 MB | Comme **builder** uniquement |

**❌ Anti-pattern `alpine` par réflexe** : musl vs glibc casse les wheels binaires (numpy, pandas, cryptography, pydantic-core). Rebuild très lent. Préférer `slim` qui est à peine plus gros (~20 MB).

### Principes à respecter

**✅ Toujours** : multi-stage (séparer builder avec compilateurs / runtime minimal), layer caching (copier `pyproject.toml` + `uv.lock` **avant** le code source), user non-root (`USER app` avec UID ≥ 10000), image pinnée par digest SHA256 en prod, `UV_COMPILE_BYTECODE=1` pour compiler à la build, `.dockerignore` strict, healthcheck natif, `tini`/`dumb-init` pour que `SIGTERM` arrive bien à Python, scan de sécurité (Trivy, Grype, docker scout) + génération de SBOM (CycloneDX ou SPDX), tags immuables via Git SHA.

**❌ Jamais** : `FROM python:latest`, `COPY . .` avant les deps (invalide le cache), tourner en root, mettre `uv` dans l'image runtime si non nécessaire (surface d'attaque).

### `.dockerignore` essentiel

```gitignore
.git .github .gitignore
__pycache__ *.pyc .pytest_cache .mypy_cache .ruff_cache
.coverage htmlcov .tox .nox
.venv venv env
.vscode .idea
dist build *.egg-info
Dockerfile* docker-compose*.yml
.env .env.* .secrets.baseline *.pem *.key
docs/ tests/
```

### Sécurité : scan et SBOM

```bash
trivy image myapp:latest --severity HIGH,CRITICAL --exit-code 1
docker scout cves myapp:latest
syft myapp:latest -o cyclonedx-json > sbom.json
cosign sign --yes myapp:latest
```

---

## 13. Anti-patterns à éviter absolument

| ❌ Anti-pattern | ✅ Correction |
|---|---|
| `def f(x=[])` — mutable default | `def f(x=None): x = x or []` |
| `except: pass` ou `except Exception: pass` | Attraper précisément + `logger.exception` |
| Modifier liste en itérant (`items.remove(x)`) | Compréhension : `items = [x for x in items if ...]` |
| `from foo import *` | Imports explicites + `__all__` |
| `if x is 1000` / `if s is "a"` | `==` (sauf `None`, `True`, `False`) |
| État global mutable, Singleton métaclasse | DI (FastAPI `Depends`), un module = singleton |
| `class StringUtils: @staticmethod` partout | Module `string_utils.py` avec fonctions |
| `def f(a,b,c,d,e,f,g,h,i)` | `dataclass` ou `BaseModel` + `*` keyword-only |
| Pas de type hints sur API publique | Annoter tout + `py.typed` |
| `pip install` hors venv / `sudo pip` | `uv` (venv auto) / `uv tool install` |
| `setup.py` | `pyproject.toml` + hatchling/uv_build |
| `print()` en code métier | `logging`/`structlog` |
| `os.path.join(...)` | `Path(__file__).parent / "data"` |
| `f = open(...); f.read()` sans `with` | `with Path(...).open() as f:` |
| `result += chunk` dans boucle | `"".join(chunks)` ou `StringIO` |
| Classes partout quand une fonction suffit | Fonction pure, classe uniquement si état/polymorphisme |
| Monkey-patching en prod | Sous-classer/composer ; monkey-patch réservé aux tests |
| `time.sleep(5)` dans async | `await asyncio.sleep(5)` |
| `datetime.utcnow()` (déprécié 3.12) | `datetime.now(UTC)` |
| `requirements.txt` seul | Lockfile (`uv.lock`) commit |
| `assert user.is_admin` pour sécurité | `if not user.is_admin: raise PermissionError` (asserts OFF avec `-O`) |
| `eval(user_input)` | `ast.literal_eval` ou parser dédié |
| `yaml.load(data)` | `yaml.safe_load(data)` |
| `hashlib.md5(password)` | `argon2-cffi` |
| `subprocess.call(cmd, shell=True)` | `subprocess.run([...])` sans shell |
| `random.random()` pour secret | `secrets.token_urlsafe(32)` |
| Dict comme enum | `enum.StrEnum` |
| `requests.get(url)` sans timeout | `httpx.get(url, timeout=10)` |

Chacun de ces anti-patterns est soit une bombe à retardement (race condition, RCE, fuite de sécurité), soit un piège de performance (O(n²), event loop bloquée), soit un obstacle durable à la maintenance (type opacity, couplage global). Les bannir de manière automatisée via Ruff + Bandit + mypy + pre-commit est non-négociable en 2026.

---

## 14. Bibliothèques incontournables 2026 par catégorie

### HTTP clients
- **httpx** — *recommandé par défaut*. API sync/async identique, HTTP/2, timeouts par défaut, test transport ASGI.
- **requests** — Legacy encore massif, pas d'async.
- **aiohttp** — Client + serveur async historique.
- **niquests** — Fork moderne de `requests` avec HTTP/2, HTTP/3, async.

### Frameworks web
- **FastAPI** — *Gagnant 2024-2026*, 38 % d'adoption (+9pt JetBrains Survey 2024). Async, OpenAPI auto, Pydantic v2.
- **Litestar** — Alternative FastAPI : DI plus structurée, plugins intégrés.
- **Django 5.x** — Full-stack mature. **Django Ninja** pour DX FastAPI-like.
- **Flask 3.x** / **Quart** (async) — Micro-frameworks.
- **Starlette** — ASGI bas niveau, base de FastAPI.
- **Robyn** — Framework Rust ASGI ultra-rapide, en croissance.

### Serveurs ASGI/WSGI
- **uvicorn** — Standard ASGI (uvloop + httptools).
- **granian** — Serveur Rust (ASGI/WSGI/RSGI), support free-threaded 3.13t, métriques Prometheus natives.
- **hypercorn** — HTTP/3 + QUIC, multi-loop.
- **gunicorn** — Standard WSGI (Django, Flask), tend à être remplacé par granian.

### Validation / parsing
- **pydantic v2** — Core Rust, 5-50× plus rapide que v1. Standard API, config, LLMs structurés.
- **msgspec** — *Ultra-rapide*, 5-10× plus rapide que pydantic sur du pur parsing JSON/MsgPack/YAML/TOML.
- **attrs** — Déclaratif, mature, par Hynek.
- **dataclasses** (stdlib) — `slots=True, frozen=True, kw_only=True`.

### Data science
- **polars** — DataFrame Rust lazy, 10-100× plus rapide que pandas, streaming.
- **pandas 2.x** — Toujours #1 adoption, backend PyArrow en option.
- **numpy** v2.x — Socle de tout.
- **duckdb** — OLAP embarqué, SQL sur Parquet/CSV/Arrow/pandas/polars sans serveur.
- **pyarrow** — Format colonne standard.
- **narwhals** — Adaptateur DataFrame-agnostique pour auteurs de libs.

### ML / IA
- **scikit-learn**, **PyTorch**, **transformers** (HuggingFace) — les classiques.
- **langchain / LangGraph** — Dominant mais controversé pour sa complexité.
- **llama-index** — Spécialisé RAG.
- **instructor** — Outputs structurés LLM via Pydantic, >3M downloads/mois.
- **pydantic-ai** — *Nouveau 2024-2025*, framework d'agents officiel Pydantic, DX FastAPI-like. Candidat solide à remplacer LangChain pour les agents simples/moyens.
- **dspy** — Programmer les LLMs, compilation de prompts avec optimizers.
- **vllm / sglang** — Serving LLM haute performance.

### Async
- **asyncio** (stdlib), **anyio** (abstraction portable asyncio/trio, task groups structurés), **trio** (concurrence structurée by design), **aiofiles**, **asyncer** (sync ↔ async, auteur FastAPI), **aiocache**.

### Bases de données / ORM
- **SQLAlchemy 2.x** — Standard, API 2.0 typée avec `Mapped[]`, async natif.
- **SQLModel** — Pydantic + SQLAlchemy (auteur FastAPI).
- **psycopg 3** — Driver Postgres moderne sync + async.
- **asyncpg** — Driver Postgres async le plus rapide.
- **Django ORM** — Complet, async natif (`aget`, `aall`).
- **tortoise-orm**, **piccolo** — ORM async.
- **alembic** — Migrations SQLAlchemy.

### Task queues
- **Celery** — Classique, très déployé.
- **dramatiq** — Plus simple, plus rapide.
- **arq** — Celery-like async (Redis).
- **taskiq** — Distributed async, intégré FastAPI, brokers variés (Redis, NATS, Kafka, RabbitMQ).
- **procrastinate** — Queue sur PostgreSQL (pas de Redis nécessaire).
- **Temporal** — Workflows durables, production-grade.
- **Prefect 3** / **Dagster** / **Airflow** — Orchestration pipelines data/ML.

### CLI
- **Typer** — Typé, auteur FastAPI, construit sur Click.
- **Click** — Mature, flexible.
- **rich** — Affichage terminal (couleur, tables, progress bars, tracebacks).
- **textual** — TUI complètes (auteur rich).
- **questionary** — Prompts interactifs.

### Dates / temps
- **whenever** (*nouveau 2024*) — Types séparés `Instant` / `ZonedDateTime` / `PlainDateTime`, DST-safe, noyau Rust, 10-100× plus rapide que pendulum/arrow. **Recommandé** pour tout nouveau projet.
- **pendulum** — Historique, maintenance ralentie.
- **arrow** — API friendly mais un seul type (perd l'info de typage).
- **stdlib `datetime` + `zoneinfo`** — Verbeux et piégeux.

### Configuration
- **pydantic-settings** — Type-safe, validation Pydantic.
- **python-dotenv** — Chargement `.env` (inutile si pydantic-settings).
- **dynaconf** — Multi-sources (TOML, YAML, env, Vault), profils multi-env.
- **tomllib** (stdlib ≥ 3.11).

### Sérialisation
- **orjson** — JSON Rust, 3-10× plus rapide que stdlib, sérialise nativement `datetime`/`UUID`/`dataclass`/numpy/pydantic.
- **msgspec** — JSON/MsgPack/YAML/TOML unifié avec validation zéro-coût.
- **pyyaml** — Toujours `yaml.safe_load`.
- **tomllib** / **tomli_w** — Lecture/écriture TOML.

### Testing
- **pytest**, **pytest-xdist** (parallélisation), **pytest-cov**, **hypothesis** (property-based), **faker**, **factory-boy**, **respx** / **pytest-httpx**, **time-machine**, **testcontainers-python**, **tenacity**.

### Observabilité
- **opentelemetry-python** — Standard cloud-native, auto-instrumentation FastAPI/Django/Flask/SQLAlchemy/httpx.
- **sentry-sdk** — Error tracking + performance.
- **structlog** — Logging structuré JSON.
- **prometheus-client** — Métriques format Prom.
- **logfire** (Pydantic team, 2024) — Observabilité Python-native, bâtie sur OpenTelemetry.
- **loguru** — Logging simplifié pour scripts.

---

## Conclusion : la stack convergée 2025-2026

Trois convergences structurent Python production-ready en 2025. **L'écosystème Astral (uv + ruff + ty) a consolidé l'outillage** autour de binaires Rust ultra-rapides, remplaçant 7 à 10 outils historiques par quelques commandes unifiées — un gain de productivité mesurable à chaque commit. **Le typage strict s'est généralisé** : pydantic v2 (core Rust), mypy strict en CI, Pyright côté éditeur, PEP 695 pour les génériques modernes, `@override` et `assert_never` pour l'exhaustivité. **La sécurité supply chain est passée de bonne pratique à norme** : Trusted Publishing OIDC (fin des tokens PyPI long-lived), SBOM CycloneDX systématique, attestations Sigstore, pip-audit + detect-secrets en pre-commit.

Trois insights valent d'être retenus. **La vitesse change les workflows** : quand `uv sync` prend moins d'une seconde et `ruff check` scanne 100 000 lignes en quelques millisecondes, les outils redeviennent invisibles et le développeur relance les contrôles à chaque save — la friction disparaît. **Les anti-patterns "classiques" restent dangereux** : `datetime.utcnow()` déprécié, `time.sleep()` dans du async, mutable defaults, `except: pass` continuent de produire des bugs en 2026 ; seule une automation pre-commit + CI les élimine durablement. **L'observabilité structured-by-default** (structlog + OTel + logfire/Sentry) est devenue le prérequis pour opérer des microservices — le logging en chaînes de caractères libres ne passe plus à l'échelle.

Le `pyproject.toml` de référence tient en 60 lignes et porte toute la configuration ; un `.pre-commit-config.yaml` de 30 lignes empêche le code non-conforme d'atteindre `main` ; un Dockerfile multi-stage de 40 lignes produit une image distroless-like signée Sigstore. Cette **simplicité est le vrai livrable de 2025** : la production-readiness ne demande plus d'ingénierie héroïque, juste l'application disciplinée d'une stack désormais bien définie.