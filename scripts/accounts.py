#!/usr/bin/env python3
"""Mapa de cuentas TikTok para Social Media Factory.

Una SOLA app "Rock Factory" (client_key / client_secret compartidos) autoriza a
las 4 cuentas del proyecto mediante OAuth. Cada cuenta guarda su PROPIO token en
su archivo chmod 600 (fuera del repo). Este módulo centraliza el mapa para que
oauth_helper.py y subir_tiktok.py no lo dupliquen.

Uso:
    from accounts import token_path, account_email, known_slugs, resolve_account
"""
from __future__ import annotations

import os

# (slug del canal, email de la cuenta TikTok, path del archivo de token)
ACCOUNTS = [
    ("rock-factory",        "rock.factory@outlook.com",       "~/.tiktok_rock_factory_token"),
    ("cuentos-caricaturas", "retro.cartoon@outlook.com",      "~/.tiktok_retro_cartoon_token"),
    ("insight-star",        "insight.star@outlook.com",       "~/.tiktok_insight_star_token"),
    ("ia-generativa-news",  "generative.ai.news@outlook.com", "~/.tiktok_generative_ai_news_token"),
]

# Credenciales de la APP (compartidas entre todas las cuentas)
CLIENT_KEY_FILE = os.path.expanduser("~/.tiktok_rock_factory_key")
CLIENT_SECRET_FILE = os.path.expanduser("~/.tiktok_rock_factory_secret")

_VALID = {slug: (email, os.path.expanduser(path)) for slug, email, path in ACCOUNTS}


def known_slugs() -> list[str]:
    return list(_VALID)


def account_email(slug: str) -> str:
    if slug not in _VALID:
        raise KeyError(_unknown(slug))
    return _VALID[slug][0]


def token_path(slug: str) -> str:
    if slug not in _VALID:
        raise KeyError(_unknown(slug))
    return _VALID[slug][1]


def resolve_account(slug: str) -> tuple[str, str, str]:
    """Devuelve (slug, email, token_path) validado."""
    if slug not in _VALID:
        raise KeyError(_unknown(slug))
    email, path = _VALID[slug]
    return slug, email, path


def _unknown(slug: str) -> str:
    return (f"Cuenta desconocida: '{slug}'. "
            f"Opciones validas: {', '.join(known_slugs())}")
