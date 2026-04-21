# proxy-lm-studio

Serveur HTTPS mock qui intercepte les appels de LM Studio et Hugging Face pour renvoyer des réponses locales prédéfinies. Utile pour tester LM Studio hors-ligne ou mocker des modèles spécifiques.

---

## Architecture

```
proxy_lm-studio/
├── src/
│   └── proxy_lm_studio/
│       ├── config.py          # Configuration via variables d'environnement
│       ├── exceptions.py      # Hiérarchie d'exceptions
│       ├── logging_setup.py   # Logging structuré (structlog)
│       ├── routes.py          # Définition et matching des routes
│       ├── handlers.py        # Handler HTTP (RequestLogger)
│       └── main.py            # Point d'entrée : SSL + HTTPServer
├── responses/                 # Fichiers de réponses mock (JSON, Markdown, PNG)
│   ├── staff-picks.json
│   ├── artifacts/             # Réponses LM Studio
│   └── hf/                    # Réponses Hugging Face
├── certs/                     # Certificats SSL (CA + serveur)
├── tests/                     # 42 tests, 92% couverture
│   ├── unit/                  # Tests purs (routes, exceptions, main)
│   └── integration/           # Tests HTTPS sur port 18443
├── pyproject.toml             # Source unique de vérité (uv, ruff, mypy, pytest)
├── Dockerfile                 # Multi-stage builder/runtime
├── compose.yaml
└── .env.example
```

### Routes simulées

| Méthode | Chemin | Paramètre | Fichier servi |
|---|---|---|---|
| GET | `/api/v1/models` | `action=staff-picks` | `responses/staff-picks.json` |
| GET | `/api/v1/artifacts/{org}/{model}/revision/{rev}` | `manifest=true` | `responses/artifacts/{org}/{model}.json` |
| GET | `/api/v1/artifacts/{org}/{model}/revision/{rev}` | `action=readme` | `responses/artifacts/{org}/{model}.readme.md` |
| GET | `/api/v1/artifacts/{org}/{model}/revision/{rev}` | `action=thumbnail` | `responses/artifacts/{org}/{model}/thumbnail.png` |
| GET | `/api/models/{org}/{model}/tree/{rev}` | — | `responses/hf/{org}/{model}/{rev}.json` |
| GET | `/api/models/{org}/{model}/revision/{rev}` | — | `responses/hf/{org}/{model}/revision.json` |
| GET | `/api/models/{org}/{model}` | — | `responses/hf/{org}/{model}/info.json` |
| GET | `/{org}/{model}/resolve/{rev}/{filename}` | — | `responses/hf/{org}/{model}/files/{filename}` |

Si le fichier spécifique est absent, un fichier `_default.*` est utilisé en fallback. Si aucun fallback n'existe, le serveur répond 404.

---

## Installation

### Prérequis

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) (gestionnaire de dépendances)

```bash
# Installer uv si absent
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances du projet
uv sync
```

### Configuration

```bash
cp .env.example .env
# Éditer .env selon l'environnement
```

Variables disponibles (préfixe `PROXY_`) :

| Variable | Défaut | Description |
|---|---|---|
| `PROXY_HOST` | `0.0.0.0` | Interface d'écoute |
| `PROXY_PORT` | `443` | Port d'écoute |
| `PROXY_CERT_FILE` | `./certs/server.crt` | Chemin vers le certificat TLS |
| `PROXY_KEY_FILE` | `./certs/server.key` | Chemin vers la clé privée TLS |
| `PROXY_RESPONSES_DIR` | `./responses` | Répertoire des fichiers mock |
| `PROXY_LOG_LEVEL` | `INFO` | Niveau de log (`DEBUG`/`INFO`/`WARNING`/`ERROR`) |
| `PROXY_ENV` | `development` | Environnement (`development`/`production`/`test`) |

> **Note :** en production (`PROXY_ENV=production`) les logs sont émis en JSON (compatible Loki/Datadog). En développement, les logs sont colorés dans le terminal.

---

## Lancer le serveur

```bash
# Développement — port 8443, pas de sudo
PROXY_PORT=8443 uv run proxy-lm-studio

# Ou avec make
make run-dev

# Production — port 443 (nécessite sudo)
sudo uv run proxy-lm-studio

# Via make
make run
```

### Tester

```bash
# Avec la CA explicitement (sans avoir à l'installer)
curl --cacert ./certs/ca.crt "https://lmstudio.ai/api/v1/models?action=staff-picks"
curl --cacert ./certs/ca.crt https://huggingface.co/api/models/test/model

# Après installation de la CA sur le système
curl "https://lmstudio.ai/api/v1/models?action=staff-picks"
```

### Via Docker

```bash
docker compose up --build
```

Le `compose.yaml` monte les certificats via Docker secrets et lie le port 443.

---

## Développement

```bash
make lint        # ruff check
make format      # ruff format
make typecheck   # mypy strict
make test        # pytest + coverage (seuil 85%)
make test-cov    # rapport HTML dans htmlcov/
```

Lancer tous les hooks pre-commit avant de committer :

```bash
uv run pre-commit install   # à faire une seule fois
make pre-commit             # vérification complète
```

### Ajouter une réponse mock

1. Créer le fichier JSON (ou MD/PNG) dans `responses/`
2. Si nécessaire, ajouter une route dans `src/proxy_lm_studio/routes.py`
3. Ajouter un test dans `tests/unit/test_routes.py` ou `tests/integration/test_server.py`

---

## Setup des certificats

### 1. Créer la CA racine (une seule fois)

```bash
mkdir -p certs && cd certs

# Clé privée de la CA (protégée par mot de passe)
openssl genrsa -aes256 -out ca.key 4096

# Certificat auto-signé de la CA (valide 10 ans)
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/C=FR/ST=IleDeFrance/L=Paris/O=MonOrganisation/OU=MaCA/CN=Mon Autorite Racine"
```

**Résultat** : `ca.key` (à garder secrète) et `ca.crt` (à installer sur les machines clientes).

### 2. Créer le certificat serveur multi-domaines

```bash
# Clé privée du serveur (sans mot de passe)
openssl genrsa -out server.key 2048

# CSR
openssl req -new -key server.key -out server.csr \
  -subj "/C=FR/ST=IleDeFrance/L=Paris/O=MockServer/OU=IT/CN=lmstudio.ai"

# Fichier d'extensions avec TOUS les domaines à couvrir
cat > server.ext <<'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1  = lmstudio.ai
DNS.2  = *.lmstudio.ai
DNS.3  = api.lmstudio.ai
DNS.4  = huggingface.co
DNS.5  = *.huggingface.co
DNS.10 = localhost
IP.1   = 127.0.0.1
EOF

# Signature du certificat par la CA (valide 825 jours max pour navigateurs)
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -extfile server.ext
```

**Vérification** :
```bash
openssl x509 -in server.crt -text -noout | grep -A 2 "Subject Alternative Name"
openssl verify -CAfile ca.crt server.crt    # doit afficher : OK
```

### 3. Rediriger les domaines vers localhost

Édite `/etc/hosts` (Linux/macOS) ou `C:\Windows\System32\drivers\etc\hosts` (Windows) :

```
127.0.0.1   lmstudio.ai
127.0.0.1   api.lmstudio.ai
127.0.0.1   huggingface.co
```

Test : `ping lmstudio.ai` doit répondre depuis `127.0.0.1`.

### 4. Installer la CA sur le système

**Debian / Ubuntu** :
```bash
sudo cp certs/ca.crt /usr/local/share/ca-certificates/certs.crt
sudo update-ca-certificates
```

**RHEL / Fedora / CentOS** :
```bash
sudo cp certs/ca.crt /etc/pki/ca-trust/source/anchors/certs.crt
sudo update-ca-trust
```

**Firefox** (n'utilise pas le magasin système) : *Paramètres → Vie privée → Certificats → Afficher les certificats → Autorités → Importer*.

### Récapitulatif des fichiers de certificats

| Fichier | Rôle | À distribuer ? |
|---|---|---|
| `certs/ca.key` | Clé privée de la CA | ❌ Jamais |
| `certs/ca.crt` | Certificat public de la CA | ✅ Installer sur chaque client |
| `certs/server.key` | Clé privée du serveur | ❌ Reste sur le serveur |
| `certs/server.crt` | Certificat serveur multi-domaines | ✅ Chargé par le serveur |
| `certs/server.ext` | Fichier d'extensions (SAN) | ℹ️ Conserver pour régénérer |

### Pour ajouter un nouveau domaine plus tard

1. Ajouter une ligne `DNS.X = ...` dans `server.ext`
2. Régénérer le CSR et le certificat (étape 2, les 2 dernières commandes)
3. Ajouter l'entrée dans `/etc/hosts`
4. Redémarrer le serveur

La CA n'est **pas** à régénérer — elle reste valide tant qu'elle est installée sur les clients.

---

## Points d'attention

**Port 443 déjà utilisé** : vérifie avec `sudo ss -tulpn | grep :443`. Arrête le service en conflit (nginx, apache…) ou utilise un port alternatif (`PROXY_PORT=8443`).

**La clé serveur ne doit pas être chiffrée** — sinon Python demande un mot de passe au démarrage. Si elle l'est : `openssl rsa -in server.key -out server.key`.
