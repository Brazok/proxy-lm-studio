import ssl
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# --- Routes avec correspondance exacte (méthode, chemin, params requis) ---
MOCK_ROUTES = {
    ("GET", "/api/v1/models", (("action", "staff-picks"),)): {
        "file": "responses/staff-picks.json",
        "content_type": "application/json; charset=utf-8",
    },
}

# --- Routes avec pattern regex (pour les URL dynamiques) ---
MOCK_PATTERN_ROUTES = [
    # ===== LM Studio API =====
    # Manifest du modèle
    {
        "method": "GET",
        "pattern": re.compile(r"^/api/v1/artifacts/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"),
        "required_params": (("manifest", "true"),),
        "file_template": "responses/artifacts/{org}/{model}.json",
        "file_fallback": "responses/artifacts/_default.json",
        "content_type": "application/json; charset=utf-8",
    },
    # README LM Studio
    {
        "method": "GET",
        "pattern": re.compile(r"^/api/v1/artifacts/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"),
        "required_params": (("action", "readme"),),
        "file_template": "responses/artifacts/{org}/{model}.readme.md",
        "file_fallback": "responses/artifacts/_default.readme.md",
        "content_type": "text/markdown; charset=utf-8",
    },
        # thumbnail
    {
        "method": "GET",
        "pattern": re.compile(r"^/api/v1/artifacts/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"),
        "required_params": (("action", "thumbnail"),),
        "file_template": "responses/artifacts/{org}/{model}/thumbnail.png",
        "file_fallback": "responses/artifacts/_default.thumbnail.png",
        "content_type": "image/png; charset=utf-8",
    },

    # ===== Hugging Face API =====
    # Liste des fichiers d'un modèle : /api/models/{org}/{model}/tree/{revision}
    {
        "method": "GET",
        "pattern": re.compile(r"^/api/models/(?P<org>[^/]+)/(?P<model>[^/]+)/tree/(?P<revision>[^/]+)$"),
        "required_params": (),
        "file_template": "responses/hf/{org}/{model}/{revision}.json",
        "file_fallback": "responses/hf/_default.tree.json",
        "content_type": "application/json; charset=utf-8",
    },
    # Info d'une révision : /api/models/{org}/{model}/revision/{revision}
    {
        "method": "GET",
        "pattern": re.compile(r"^/api/models/(?P<org>[^/]+)/(?P<model>[^/]+)/revision/(?P<revision>[^/]+)$"),
        "required_params": (),
        "file_template": "responses/hf/{org}/{model}/revision.json",
        "file_fallback": "responses/hf/_default.revision.json",
        "content_type": "application/json; charset=utf-8",
    },
    # Métadonnées du modèle : /api/models/{org}/{model}
    {
        "method": "GET",
        "pattern": re.compile(r"^/api/models/(?P<org>[^/]+)/(?P<model>[^/]+)$"),
        "required_params": (),
        "file_template": "responses/hf/{org}/{model}/info.json",
        "file_fallback": "responses/hf/_default.info.json",
        "content_type": "application/json; charset=utf-8",
    },
    # Téléchargement : /{org}/{model}/resolve/{revision}/{filename}
    # Ces URL sont souvent redirigées vers un CDN. On renvoie un petit fichier mock ou un 302.
    {
        "method": "GET",
        "pattern": re.compile(r"^/(?P<org>[^/]+)/(?P<model>[^/]+)/resolve/(?P<revision>[^/]+)/(?P<filename>.+)$"),
        "required_params": (),
        "file_template": "responses/hf/{org}/{model}/files/{filename}",
        "file_fallback": "responses/hf/_default.file",
        "content_type": "application/octet-stream",
    },
]


class RequestLogger(BaseHTTPRequestHandler):
    def log_request_details(self, body=None):
        print("\n" + "=" * 70)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Nouvelle requête")
        print("=" * 70)
        print(f"Méthode    : {self.command}")
        print(f"Chemin     : {self.path}")
        print(f"Client     : {self.client_address[0]}:{self.client_address[1]}")

        print("\n--- Headers ---")
        for header, value in self.headers.items():
            print(f"  {header}: {value}")

        if body:
            print("\n--- Body ---")
            try:
                print(body.decode('utf-8'))
            except UnicodeDecodeError:
                print(f"(binaire, {len(body)} octets)")

        print("=" * 70)

    def match_exact_route(self, method, path, query):
        """Cherche dans MOCK_ROUTES (correspondance exacte du chemin)."""
        query_tuple = tuple(sorted((k, v[0]) for k, v in query.items()))

        key = (method, path, query_tuple)
        if key in MOCK_ROUTES:
            return MOCK_ROUTES[key], {}

        for (m, p, required_params), route in MOCK_ROUTES.items():
            if m != method or p != path:
                continue
            if all(param in query_tuple for param in required_params):
                return route, {}

        return None, None

    def match_pattern_route(self, method, path, query):
        """Cherche dans MOCK_PATTERN_ROUTES (correspondance regex)."""
        query_tuple = tuple(sorted((k, v[0]) for k, v in query.items()))

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

    def match_route(self, method, path, query):
        """Essaie d'abord les routes exactes, puis les patterns."""
        route, vars_captured = self.match_exact_route(method, path, query)
        if route:
            return route, vars_captured

        return self.match_pattern_route(method, path, query)

    def resolve_file_path(self, route, captured_vars):
        """Détermine quel fichier lire en fonction du template et des variables."""
        if "file_template" in route:
            try:
                candidate = route["file_template"].format(**captured_vars)
            except KeyError as e:
                print(f"  ⚠️  Variable manquante dans le template : {e}")
                candidate = None

            if candidate and os.path.isfile(candidate):
                return candidate, False

            fallback = route.get("file_fallback")
            if fallback and os.path.isfile(fallback):
                print(f"  ℹ️  Fichier spécifique absent, fallback : {fallback}")
                return fallback, True
            return None, False

        return route.get("file"), False

    def send_file_response(self, route, captured_vars=None):
        """Envoie le contenu du fichier résolu."""
        captured_vars = captured_vars or {}
        content_type = route.get("content_type", "application/octet-stream")

        file_path, is_fallback = self.resolve_file_path(route, captured_vars)

        if not file_path or not os.path.isfile(file_path):
            print(f"  ⚠️  Aucun fichier disponible pour cette requête")
            self.send_error(404, "Mock file not found")
            return

        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except OSError as e:
            self.send_error(500, f"Cannot read mock file: {e}")
            return

        if captured_vars:
            try:
                text = content.decode("utf-8")
                for key, value in captured_vars.items():
                    text = text.replace(f"{{{{{key}}}}}", value)
                content = text.encode("utf-8")
            except UnicodeDecodeError:
                pass

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

        tag = " (fallback)" if is_fallback else ""
        print(f"  ✅ Réponse envoyée depuis : {file_path}{tag} ({len(content)} octets)")
        if captured_vars:
            print(f"  📋 Variables capturées : {captured_vars}")

    def send_default_response(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Requete recue (aucune route simulee), voir la console.\n")

    def handle_request(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        self.log_request_details(body=body)
        if query:
            print(f"\n--- Query params parsés ---")
            for k, v in query.items():
                print(f"  {k} = {v}")

        route, captured_vars = self.match_route(self.command, path, query)
        if route:
            print(f"\n→ Route simulée trouvée : {self.command} {path}")
            self.send_file_response(route, captured_vars)
        else:
            print(f"\n→ Aucune route simulée pour {self.command} {path}")
            self.send_default_response()

    def do_GET(self):     self.handle_request()
    def do_POST(self):    self.handle_request()
    def do_PUT(self):     self.handle_request()
    def do_DELETE(self):  self.handle_request()
    def do_PATCH(self):   self.handle_request()
    def do_HEAD(self):    self.handle_request()
    def do_OPTIONS(self): self.handle_request()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 443
    CERT_FILE = "./certs/server.crt"
    KEY_FILE  = "./certs/server.key"

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    server = HTTPServer((HOST, PORT), RequestLogger)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print(f"Serveur HTTPS démarré sur https://{HOST}:{PORT}")
    print(f"\nRoutes exactes :")
    for (method, path, params), route in MOCK_ROUTES.items():
        params_str = "&".join(f"{k}={v}" for k, v in params)
        full = f"{path}?{params_str}" if params_str else path
        print(f"  {method:6} {full}  →  {route['file']}")

    print(f"\nRoutes dynamiques (regex) :")
    for route in MOCK_PATTERN_ROUTES:
        params_str = "&".join(f"{k}={v}" for k, v in route.get("required_params", ()))
        pattern_str = route["pattern"].pattern
        full = f"{pattern_str}?{params_str}" if params_str else pattern_str
        template = route.get("file_template") or route.get("file", "?")
        print(f"  {route['method']:6} {full}  →  {template}")

    print("\nEn attente de requêtes... (Ctrl+C pour arrêter)\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
        server.server_close()