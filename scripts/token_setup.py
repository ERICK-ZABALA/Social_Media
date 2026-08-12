#!/usr/bin/env python3
"""token_setup.py — Inicializa los archivos de token de OAuth por cuenta.

La app "Rock Factory" (1 sola app en developers.tiktok.com) sirve para las 4
cuentas. Cada cuenta obtiene su PROPIO access_token + refresh_token vía el flujo
de OAuth, y se guarda en su propio archivo chmod 600 (fuera del repo, por eso
estos archivos NO se commitean).

Este script NO habla con TikTok: solo crea/limpia la estructura de archivos para
que el flujo quede documentado y los permisos correctos desde el inicio.

Uso:
    python3 scripts/token_setup.py            # crea los 4 archivos de token vacíos
    python3 scripts/token_setup.py --check    # lista qué tokens ya existen

Después de correrlo, para cada cuenta ejecutás (con el redirect URI del túnel):
    python3 scripts/oauth_helper.py --account retro-cartoon --redirect-uri https://.../callback

(La versión actual de oauth_helper.py guarda en ~/.tiktok_rock_factory_token;
 cuando se parametrice multi-cuenta, este mapa define los paths finales.)

Mapa de cuentas -> archivo de token (todos chmod 600):
    rock-factory       ~/.tiktok_rock_factory_token
    retro-cartoon      ~/.tiktok_retro_cartoon_token
    insight-star       ~/.tiktok_insight_star_token
    ia-generativa-news ~/.tiktok_generative_ai_news_token
"""
from __future__ import annotations

import argparse
import json
import os

# (slug del canal, email de la cuenta TikTok, path del archivo de token)
ACCOUNTS = [
    ("rock-factory",       "rock.factory@outlook.com",      "~/.tiktok_rock_factory_token"),
    ("retro-cartoon",      "retro.cartoon@outlook.com",     "~/.tiktok_retro_cartoon_token"),
    ("insight-star",       "insight.star@outlook.com",      "~/.tiktok_insight_star_token"),
    ("ia-generativa-news", "generative.ai.news@outlook.com","~/.tiktok_generative_ai_news_token"),
]

EMPTY = {
    "access_token": None,
    "refresh_token": None,
    "expires_in": None,
    "open_id": None,
    "scope": "user.info.basic,video.upload",
    "account": None,          # se rellena con el slug del canal
    "email": None,            # se rellena con el email de la cuenta
    "obtained_at": None,      # ISO timestamp, lo pone oauth_helper
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Solo lista qué tokens ya existen")
    a = ap.parse_args()

    print("Cuentas TikTok (1 app 'Rock Factory' -> 4 OAuth):\n")
    for slug, email, tok in ACCOUNTS:
        path = os.path.expanduser(tok)
        exists = os.path.exists(path)
        if a.check:
            status = "EXISTE" if exists else "  falta"
            size = os.path.getsize(path) if exists else 0
            print(f"  [{status}] {slug:18} {email:28} {path} ({size} B)")
            continue
        if exists:
            print(f"  [omitido] {slug:18} {path} ya existe")
            continue
        blob = dict(EMPTY)
        blob["account"] = slug
        blob["email"] = email
        with open(path, "w") as f:
            json.dump(blob, f, indent=2)
        os.chmod(path, 0o600)
        print(f"  [creado]  {slug:18} {path} (chmod 600)")

    if not a.check:
        print("\nListo. Para autorizar cada cuenta, cuando la app esté aprobada:")
        print("  python3 scripts/oauth_helper.py --account <slug> --redirect-uri https://TU-TUNEL/callback")


if __name__ == "__main__":
    main()
