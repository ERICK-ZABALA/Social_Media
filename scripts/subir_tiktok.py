#!/usr/bin/env python3
"""
subir_tiktok.py — Sube un video a los BORRADORES de TikTok (Opción A: video.upload).

No publica: la publicacion final y la eleccion de la musica las hace el titular desde
la app de TikTok en el celular. Es justo el flujo que se demuestra en el demo video
de review de la app "Rock Factory".

Requisitos (app "Rock Factory" en developers.tiktok.com):
    - Producto: Content Posting API, Direct Post: OFF (sube a borradores).
    - Scopes: user.info.basic, video.upload.
    - Token obtenido con scripts/oauth_helper.py (guardado en ~/.tiktok_rock_factory_token).
    - El video se sube por FILE_UPLOAD (bytes del servidor); no requiere verificacion de dominio.

Uso:
    python3 scripts/subir_tiktok.py --account retro-cartoon \
        --video channels/cuentos-caricaturas/media/dia_001.mp4 \
        --caption "El sendero de la cascada - Cuentos Caricaturas"

El caption admite hasta 2200 caracteres. La musica NO se incrusta: se elige en TikTok.

El token por cuenta se guarda en su propio archivo (ver scripts/accounts.py):
rock-factory -> ~/.tiktok_rock_factory_token, retro-cartoon -> ~/.tiktok_retro_cartoon_token,
insight-star -> ~/.tiktok_insight_star_token, ia-generativa-news -> ~/.tiktok_generative_ai_news_token.
"""

import argparse
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from accounts import token_path  # noqa: E402

TOKEN_HOST = "https://open.tiktokapis.com"


def _token(account):
    path = token_path(account)
    if not os.path.exists(path):
        raise SystemExit(
            f"No hay token para '{account}'. Ejecuta primero: "
            f"python3 scripts/oauth_helper.py --account {account}"
        )
    return json.load(open(path))["access_token"]


def _post_json(url, payload, token):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _post_file(url, fields, files, token):
    import email.utils
    import uuid

    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())
    for name, path in files.items():
        fn = os.path.basename(path)
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{fn}"\r\n'.encode()
        )
        parts.append(b"Content-Type: video/mp4\r\n\r\n")
        parts.append(open(path, "rb").read())
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def consultar_creador(token):
    """Obligatorio antes de cada post: muestra avatar/nombre de la cuenta destino."""
    resp = _post_json(
        f"{TOKEN_HOST}/v2/post/publish/creator_info/query/", {}, token
    )
    return resp


def subir_borrador(video_path, caption, token):
    if not os.path.exists(video_path):
        raise SystemExit(f"Video no encontrado: {video_path}")
    # Paso 0 (obligatorio): info del creador
    info = consultar_creador(token)
    print("Cuenta destino:", info.get("data", {}).get("creator_username", "?"))

    # Paso 1: FILE_UPLOAD del video a borradores
    resp = _post_file(
        f"{TOKEN_HOST}/v2/video/upload/",
        fields={"post_mode": "DIRECT_POST", "caption": caption[:2200]},
        files={"video": video_path},
        token=token,
    )
    return resp


def main():
    import argparse
    from accounts import known_slugs

    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="rock-factory", choices=known_slugs(),
                    help="Slug del canal/cuenta cuyo token se usa para subir.")
    ap.add_argument("--video", required=True, help="Ruta al mp4 a subir")
    ap.add_argument("--caption", default="", help="Texto del video (<=2200 chars)")
    a = ap.parse_args()

    token = _token(a.account)
    resp = subir_borrador(a.video, a.caption, token)
    print(json.dumps(resp, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
