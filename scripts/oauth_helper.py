#!/usr/bin/env python3
"""
oauth_helper.py — Genera un access token de TikTok (Login Kit) para Rock Factory.

Uso:
    1. Poné tu client_key en el archivo ~/.tiktok_rock_factory_key  (una sola línea).
       O pasalo con --client-key.
    2. El client_secret va en ~/.tiktok_rock_factory_secret (chmod 600).
    3. Ejecutá:  python3 scripts/oauth_helper.py
    4. Se abre el navegador en la pantalla de autorización de TikTok (usá la cuenta
       del canal, la de Francia). Autorizá la app.
    5. El script captura el 'code' en http://localhost:8080/callback, hace el token
       exchange y guarda el token en ~/.tiktok_rock_factory_token (chmod 600).

Requisitos en el portal (developers.tiktok.com), app "Rock Factory":
    - Login Kit agregado.
    - Redirect URI configurada exactamente en: http://localhost:8080/callback
    - Scopes pedidos: user.info.basic,video.upload

Solo usa la biblioteca estándar de Python (sin pip).
"""

import base64
import http.server
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

TOKEN_HOST = "https://open.tiktokapis.com"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
# El Redirect URI DEBE empezar con https:// (TikTok lo exige). Se usa un tunel
# HTTPS independiente (ngrok / cloudflared) que apunte a http://localhost:8080.
# Configuralo con --redirect-uri o la env TIKTOK_REDIRECT_URI.
# Ejemplo con cloudflared:  cloudflared tunnel --url http://localhost:8080
# Ejemplo con ngrok:        ngrok http 8080   -> te da https://xxxx.ngrok.io
REDIRECT_URI = os.environ.get(
    "TIKTOK_REDIRECT_URI", "https://TU-TUNEL.example.com/callback"
)
SCOPES = "user.info.basic,video.upload"
TOKEN_FILE = os.path.expanduser("~/.tiktok_rock_factory_token")
KEY_FILE = os.path.expanduser("~/.tiktok_rock_factory_key")
SECRET_FILE = os.path.expanduser("~/.tiktok_rock_factory_secret")

_auth_code = None


def _load_secret():
    if os.path.exists(SECRET_FILE):
        return open(SECRET_FILE).read().strip()
    return os.environ.get("TIKTOK_CLIENT_SECRET", "")


def _load_key(cli):
    if cli:
        return cli
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE).read().strip()
    return os.environ.get("TIKTOK_CLIENT_KEY", "")


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        q = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(q)
        if "code" in params:
            _auth_code = params["code"][0]
            body = "<html><body><h2>OK</h2>Autorizacion capturada. Podés cerrar esta pestaña.</body></html>".encode("utf-8")
            self.send_response(200)
        else:
            err = params.get("error", ["desconocido"])[0]
            body = f"<html><body><h2>Error</h2>{err}</body></html>".encode()
            self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def _exchange(client_key, client_secret, code):
    data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    req = urllib.request.Request(
        f"{TOKEN_HOST}/v2/oauth/token/",
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def run(client_key=None, redirect_uri=None):
    global REDIRECT_URI
    if redirect_uri:
        REDIRECT_URI = redirect_uri
    client_key = _load_key(client_key)
    client_secret = _load_secret()
    if not client_key:
        raise SystemExit("Falta client_key. Ponelo en ~/.tiktok_rock_factory_key o usá --client-key.")
    if not client_secret:
        raise SystemExit("Falta client_secret. Ponelo en ~/.tiktok_rock_factory_secret (chmod 600).")

    state = secrets.token_urlsafe(16)
    params = {
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)
    print("Abrindo navegador en:")
    print(url)
    webbrowser.open(url)

    srv = http.server.HTTPServer(("127.0.0.1", 8080), _Handler)
    t = threading.Thread(target=srv.handle_request)
    t.start()
    print("Esperando autorizacion en http://localhost:8080/callback ...")
    t.join(timeout=300)
    srv.server_close()

    if not _auth_code:
        raise SystemExit("No se recibio el code. Revisa que el redirect URI sea exactamente http://localhost:8080/callback")

    resp = _exchange(client_key, client_secret, _auth_code)
    if resp.get("error"):
        raise SystemExit(f"Error en token exchange: {resp}")

    tok = resp["data"]
    with open(TOKEN_FILE, "w") as f:
        json.dump(tok, f)
    os.chmod(TOKEN_FILE, 0o600)
    print(f"Token guardado en {TOKEN_FILE}")
    print("access_token:", tok.get("access_token", "")[:12], "...")
    print("expires_in:", tok.get("expires_in"), "segundos")
    print("refresh_token presente:", "refresh_token" in tok)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-key", default=None)
    ap.add_argument("--redirect-uri", default=None,
                    help="Redirect URI https (debe coincidir con el portal de TikTok). "
                         "Ej: https://xxxx.ngrok.io/callback o el de cloudflared.")
    a = ap.parse_args()
    run(a.client_key, a.redirect_uri)
