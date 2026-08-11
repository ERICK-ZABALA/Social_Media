"""Capa de acceso a datos + maquina de estados. Sin dependencias externas."""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "smf.db"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"

# Transiciones permitidas. Cualquier otra lanza InvalidTransition.
TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_approval", "rejected", "archived"},
    "pending_approval": {"approved", "rejected", "draft"},
    "approved": {"scheduled", "publishing", "rejected"},
    "scheduled": {"publishing", "approved", "rejected"},
    "publishing": {"published", "failed"},
    "failed": {"scheduled", "publishing", "archived", "rejected"},
    "published": {"archived"},
    "rejected": {"archived", "draft"},
    "archived": set(),
}


class InvalidTransition(Exception):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def connect(db_path: str | os.PathLike | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- helpers

def topic_key(label: str) -> str:
    """Normaliza un tema para detectar repeticiones (acentos, orden, ruido)."""
    txt = unicodedata.normalize("NFKD", label.lower())
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    words = sorted(set(re.findall(r"[a-z0-9]+", txt)))
    stop = {"el", "la", "los", "las", "de", "del", "y", "en", "un", "una", "the", "a", "of"}
    words = [w for w in words if w not in stop]
    return hashlib.sha256(" ".join(words).encode()).hexdigest()[:32]


def idempotency_key(content_id: int, account_id: int) -> str:
    return hashlib.sha256(f"{content_id}:{account_id}".encode()).hexdigest()[:40]


# ---------------------------------------------------------------- brands

def add_brand(conn, slug: str, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO brands(slug,name) VALUES(?,?) ON CONFLICT(slug) DO UPDATE SET name=excluded.name",
        (slug, name),
    )
    if cur.lastrowid:
        return cur.lastrowid
    return conn.execute("SELECT id FROM brands WHERE slug=?", (slug,)).fetchone()["id"]


def add_account(conn, brand_id: int, platform: str, handle: str,
                secret_ref: str | None = None, is_sandbox: int = 1) -> int:
    conn.execute(
        """INSERT INTO accounts(brand_id,platform,handle,secret_ref,is_sandbox)
           VALUES(?,?,?,?,?) ON CONFLICT(brand_id,platform,handle) DO NOTHING""",
        (brand_id, platform, handle, secret_ref, is_sandbox),
    )
    return conn.execute(
        "SELECT id FROM accounts WHERE brand_id=? AND platform=? AND handle=?",
        (brand_id, platform, handle),
    ).fetchone()["id"]


# ---------------------------------------------------------------- topics

def ensure_topic(conn, brand_id: int, label: str) -> tuple[int, bool]:
    """Devuelve (topic_id, ya_existia). Base de la memoria anti-repeticion."""
    key = topic_key(label)
    row = conn.execute(
        "SELECT id FROM topics WHERE brand_id=? AND topic_key=?", (brand_id, key)
    ).fetchone()
    if row:
        return row["id"], True
    cur = conn.execute(
        "INSERT INTO topics(brand_id,topic_key,label) VALUES(?,?,?)",
        (brand_id, key, label),
    )
    return cur.lastrowid, False


def mark_topic_used(conn, topic_id: int) -> None:
    conn.execute(
        "UPDATE topics SET times_used=times_used+1, last_used=? WHERE id=?",
        (utcnow(), topic_id),
    )


# ---------------------------------------------------------------- content

def create_content(conn, brand_id: int, title: str, body: str = "",
                   kind: str = "video", topic_id: int | None = None,
                   media_path: str | None = None,
                   rights_status: str = "unknown",
                   rights_note: str | None = None) -> int:
    cur = conn.execute(
        """INSERT INTO content_items(brand_id,topic_id,kind,title,body,media_path,
                                     rights_status,rights_note)
           VALUES(?,?,?,?,?,?,?,?)""",
        (brand_id, topic_id, kind, title, body, media_path, rights_status, rights_note),
    )
    cid = cur.lastrowid
    conn.execute(
        "INSERT INTO state_events(content_id,from_state,to_state,actor,note) VALUES(?,?,?,?,?)",
        (cid, None, "draft", "system", "created"),
    )
    return cid


def get_content(conn, content_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM content_items WHERE id=?", (content_id,)).fetchone()


def transition(conn, content_id: int, to_state: str,
               actor: str = "system", note: str | None = None) -> None:
    row = get_content(conn, content_id)
    if row is None:
        raise InvalidTransition(f"content {content_id} no existe")
    frm = row["state"]
    if to_state not in TRANSITIONS.get(frm, set()):
        raise InvalidTransition(f"{frm} -> {to_state} no permitido (content {content_id})")
    # Regla dura de negocio: nada se aprueba con derechos sin resolver.
    if to_state == "approved" and row["rights_status"] in ("unknown", "risky"):
        raise InvalidTransition(
            f"content {content_id}: rights_status='{row['rights_status']}', "
            "no se puede aprobar hasta resolver derechos"
        )
    conn.execute(
        "UPDATE content_items SET state=?, updated_at=? WHERE id=?",
        (to_state, utcnow(), content_id),
    )
    conn.execute(
        "INSERT INTO state_events(content_id,from_state,to_state,actor,note) VALUES(?,?,?,?,?)",
        (content_id, frm, to_state, actor, note),
    )


def record_approval(conn, content_id: int, decision: str,
                    comment: str | None = None, chat_id: str | None = None) -> None:
    conn.execute(
        "INSERT INTO approvals(content_id,decision,comment,chat_id) VALUES(?,?,?,?)",
        (content_id, decision, comment, chat_id),
    )
    if decision == "approve":
        transition(conn, content_id, "approved", actor=f"tg:{chat_id}", note=comment)
    elif decision == "reject":
        transition(conn, content_id, "rejected", actor=f"tg:{chat_id}", note=comment)
    else:  # edit -> vuelve a draft para regenerar
        transition(conn, content_id, "draft", actor=f"tg:{chat_id}", note=comment)


# ---------------------------------------------------------------- publish

def enqueue_publication(conn, content_id: int, account_id: int) -> int:
    """Idempotente: llamarlo N veces crea UNA sola fila."""
    key = idempotency_key(content_id, account_id)
    conn.execute(
        """INSERT INTO publications(content_id,account_id,idempotency_key,next_attempt_at)
           VALUES(?,?,?,?) ON CONFLICT(idempotency_key) DO NOTHING""",
        (content_id, account_id, key, utcnow()),
    )
    return conn.execute(
        "SELECT id FROM publications WHERE idempotency_key=?", (key,)
    ).fetchone()["id"]


def claim_due_publications(conn, limit: int = 5) -> list[sqlite3.Row]:
    """Toma trabajos vencidos y los marca in_flight (evita doble worker)."""
    rows = conn.execute(
        """SELECT * FROM publications
           WHERE status IN ('queued','error')
             AND attempts < max_attempts
             AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
           ORDER BY next_attempt_at LIMIT ?""",
        (utcnow(), limit),
    ).fetchall()
    claimed = []
    for r in rows:
        cur = conn.execute(
            """UPDATE publications SET status='in_flight', attempts=attempts+1, updated_at=?
               WHERE id=? AND status IN ('queued','error')""",
            (utcnow(), r["id"]),
        )
        if cur.rowcount == 1:
            claimed.append(conn.execute(
                "SELECT * FROM publications WHERE id=?", (r["id"],)).fetchone())
    return claimed


def mark_published(conn, pub_id: int, external_post_id: str,
                   publish_id: str | None = None, privacy_level: str | None = None) -> None:
    conn.execute(
        """UPDATE publications SET status='done', external_post_id=?, publish_id=?,
               privacy_level=?, last_error=NULL, updated_at=? WHERE id=?""",
        (external_post_id, publish_id, privacy_level, utcnow(), pub_id),
    )
    row = conn.execute("SELECT content_id FROM publications WHERE id=?", (pub_id,)).fetchone()
    cur_state = get_content(conn, row["content_id"])["state"]
    if cur_state != "published":
        if cur_state != "publishing":
            transition(conn, row["content_id"], "publishing", note="auto")
        transition(conn, row["content_id"], "published", note=f"pub {pub_id}")


def mark_failed(conn, pub_id: int, error: str, backoff_base_sec: int = 60) -> None:
    """Backoff exponencial; agota intentos -> abandoned + content failed."""
    row = conn.execute("SELECT * FROM publications WHERE id=?", (pub_id,)).fetchone()
    if row["attempts"] >= row["max_attempts"]:
        conn.execute(
            "UPDATE publications SET status='abandoned', last_error=?, updated_at=? WHERE id=?",
            (error, utcnow(), pub_id),
        )
        content = get_content(conn, row["content_id"])
        if content["state"] == "publishing":
            transition(conn, row["content_id"], "failed", note=error[:200])
        return
    delay = backoff_base_sec * (2 ** (row["attempts"] - 1))
    nxt = (datetime.now(timezone.utc) + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """UPDATE publications SET status='error', last_error=?, next_attempt_at=?,
               updated_at=? WHERE id=?""",
        (error, nxt, utcnow(), pub_id),
    )
