# Setup complet de la CA et des certificats

Guide condensé pour créer ta CA, générer un certificat couvrant plusieurs domaines, et rediriger le trafic vers ton serveur local.

## 1. Créer la CA racine (une seule fois)

```bash
mkdir -p certs && cd certs

# Clé privée de la CA (protégée par mot de passe)
openssl genrsa -aes256 -out ca.key 4096

# Certificat auto-signé de la CA (valide 10 ans)
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/C=FR/ST=IleDeFrance/L=Paris/O=MonOrganisation/OU=MaCA/CN=Mon Autorite Racine"
```

**Résultat** : `ca.key` (à garder secrète) et `ca.crt` (à installer sur les machines clientes).

## 2. Créer le certificat serveur multi-domaines

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

## 3. Rediriger les domaines vers localhost

Édite `/etc/hosts` (Linux/macOS) ou `C:\Windows\System32\drivers\etc\hosts` (Windows) :

```
127.0.0.1   lmstudio.ai
127.0.0.1   api.lmstudio.ai
127.0.0.1   huggingface.co
```

Test : `ping lmstudio.ai` doit répondre depuis `127.0.0.1`.

## 4. Installer la CA sur le système

**Debian / Ubuntu** :
```bash
sudo cp ca.crt /usr/local/share/ca-certificates/certs.crt
sudo update-ca-certificates
```

**RHEL / Fedora / CentOS** :
```bash
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/certs.crt
sudo update-ca-trust
```

**Firefox** (n'utilise pas le magasin système) : *Paramètres → Vie privée → Certificats → Afficher les certificats → Autorités → Importer*.

## 5. Lancer le serveur Python

Dans le code Python, les chemins doivent pointer sur :
```python
CERT_FILE = "./certs/server.crt"
KEY_FILE  = "./certs/server.key"
```

Port 443 = privilégié → `sudo` requis :
```bash
sudo python3 server.py
```

## 6. Tester

```bash
# Avec la CA explicitement (sans avoir à l'installer)
curl --cacert ./certs/ca.crt https://lmstudio.ai/api/v1/models?action=staff-picks
curl --cacert ./certs/ca.crt https://huggingface.co/api/models/test/model

# Après installation de la CA sur le système, sans --cacert
curl https://lmstudio.ai/
```

Aucun warning TLS = ta CA est bien reconnue et le certificat couvre les domaines.

## Récapitulatif des fichiers

| Fichier | Rôle | À distribuer ? |
|---|---|---|
| `certs/ca.key` | Clé privée de la CA | ❌ Jamais |
| `certs/ca.crt` | Certificat public de la CA | ✅ Installer sur chaque client |
| `certs/server.key` | Clé privée du serveur | ❌ Reste sur le serveur |
| `certs/server.crt` | Certificat serveur multi-domaines | ✅ Chargé par le serveur |
| `certs/server.ext` | Fichier d'extensions (SAN) | ℹ️ Conserver pour régénérer |

## Pour ajouter un nouveau domaine plus tard

1. Ajouter une ligne `DNS.X = ...` dans `server.ext`
2. Régénérer le CSR et le certificat (étape 2, les 2 dernières commandes)
3. Ajouter l'entrée dans `/etc/hosts`
4. Redémarrer le serveur Python

La CA n'est **pas** à régénérer — elle reste valide tant que tu l'as installée sur tes clients.

## Points d'attention

**Port 443 déjà utilisé** : vérifie avec `sudo ss -tulpn | grep :443`. Arrête le service en conflit (nginx, apache…) ou utilise un port alternatif comme 8443.

**La clé serveur ne doit pas être chiffrée** — sinon Python demande un mot de passe au démarrage. Si elle l'est : `openssl rsa -in server.key -out server.key`.

**Certificate pinning** : si un client embarque en dur l'empreinte du vrai certificat (courant dans les apps desktop/mobile), ton certificat sera rejeté malgré tout. Diagnostic : tu vois la poignée de main TLS aboutir dans les logs mais aucune requête HTTP ne suit. Solution : patch du client ou outil type Frida pour désactiver le pinning.

**Ne jamais utiliser cette CA en production ni la partager** — quiconque possède `ca.key` peut émettre des certificats valides pour n'importe quel domaine sur les machines où ta CA est installée.