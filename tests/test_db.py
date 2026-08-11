"""Tests de la Etapa 1: esquema, maquina de estados, idempotencia, reintentos."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smf import db as D  # noqa: E402


@pytest.fixture()
def conn(tmp_path):
    c = D.connect(tmp_path / "test.db")
    D.init_db(c)
    yield c
    c.close()


@pytest.fixture()
def brand(conn):
    return D.add_brand(conn, "music_rock", "Music Rock")


def test_schema_creates_all_tables(conn):
    names = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("brands", "accounts", "topics", "content_items",
              "state_events", "approvals", "publications", "metrics"):
        assert t in names


def test_topic_key_normaliza_acentos_y_orden(conn, brand):
    t1, existed1 = D.ensure_topic(conn, brand, "Historia del Rock Progresivo")
    t2, existed2 = D.ensure_topic(conn, brand, "rock progresivo, la historia")
    assert existed1 is False
    assert existed2 is True, "debe detectar el mismo tema pese a orden/acentos"
    assert t1 == t2


def test_topic_distinto_no_colisiona(conn, brand):
    a, _ = D.ensure_topic(conn, brand, "Historia del Rock Progresivo")
    b, existed = D.ensure_topic(conn, brand, "Bateristas de heavy metal")
    assert a != b and existed is False


def test_no_se_puede_aprobar_con_derechos_desconocidos(conn, brand):
    cid = D.create_content(conn, brand, "Cover de una cancion comercial")
    D.transition(conn, cid, "pending_approval")
    with pytest.raises(D.InvalidTransition, match="derechos"):
        D.transition(conn, cid, "approved")


def test_aprueba_cuando_los_derechos_estan_resueltos(conn, brand):
    cid = D.create_content(conn, brand, "Tema original", rights_status="original")
    D.transition(conn, cid, "pending_approval")
    D.transition(conn, cid, "approved")
    assert D.get_content(conn, cid)["state"] == "approved"


def test_transicion_ilegal_se_rechaza(conn, brand):
    cid = D.create_content(conn, brand, "x", rights_status="original")
    with pytest.raises(D.InvalidTransition):
        D.transition(conn, cid, "published")  # draft -> published prohibido


def test_state_events_registra_auditoria(conn, brand):
    cid = D.create_content(conn, brand, "x", rights_status="original")
    D.transition(conn, cid, "pending_approval")
    D.transition(conn, cid, "approved")
    ev = conn.execute(
        "SELECT to_state FROM state_events WHERE content_id=? ORDER BY id", (cid,)).fetchall()
    assert [e["to_state"] for e in ev] == ["draft", "pending_approval", "approved"]


def test_approval_reject_y_edit(conn, brand):
    cid = D.create_content(conn, brand, "x", rights_status="original")
    D.transition(conn, cid, "pending_approval")
    D.record_approval(conn, cid, "edit", "hacelo mas corto", chat_id="123")
    assert D.get_content(conn, cid)["state"] == "draft"
    D.transition(conn, cid, "pending_approval")
    D.record_approval(conn, cid, "reject", "no va", chat_id="123")
    assert D.get_content(conn, cid)["state"] == "rejected"


def test_enqueue_es_idempotente(conn, brand):
    acc = D.add_account(conn, brand, "tiktok", "@musicrock")
    cid = D.create_content(conn, brand, "x", rights_status="original")
    p1 = D.enqueue_publication(conn, cid, acc)
    p2 = D.enqueue_publication(conn, cid, acc)
    p3 = D.enqueue_publication(conn, cid, acc)
    assert p1 == p2 == p3
    n = conn.execute("SELECT COUNT(*) n FROM publications").fetchone()["n"]
    assert n == 1, "no debe duplicar publicaciones: evita postear dos veces"


def test_claim_marca_in_flight_y_no_se_reclama_dos_veces(conn, brand):
    acc = D.add_account(conn, brand, "tiktok", "@musicrock")
    cid = D.create_content(conn, brand, "x", rights_status="original")
    D.enqueue_publication(conn, cid, acc)
    first = D.claim_due_publications(conn)
    assert len(first) == 1 and first[0]["status"] == "in_flight"
    second = D.claim_due_publications(conn)
    assert second == [], "un job in_flight no debe reclamarse de nuevo"


def test_flujo_completo_hasta_published(conn, brand):
    acc = D.add_account(conn, brand, "tiktok", "@musicrock")
    cid = D.create_content(conn, brand, "Tema original", rights_status="original")
    D.transition(conn, cid, "pending_approval")
    D.record_approval(conn, cid, "approve", chat_id="123")
    D.transition(conn, cid, "scheduled")
    pid = D.enqueue_publication(conn, cid, acc)
    D.claim_due_publications(conn)
    D.mark_published(conn, pid, external_post_id="v12345",
                     publish_id="p1", privacy_level="SELF_ONLY")
    assert D.get_content(conn, cid)["state"] == "published"
    row = conn.execute("SELECT * FROM publications WHERE id=?", (pid,)).fetchone()
    assert row["status"] == "done" and row["external_post_id"] == "v12345"


def test_fallo_aplica_backoff_creciente(conn, brand):
    acc = D.add_account(conn, brand, "tiktok", "@musicrock")
    cid = D.create_content(conn, brand, "x", rights_status="original")
    pid = D.enqueue_publication(conn, cid, acc)
    D.claim_due_publications(conn)
    D.mark_failed(conn, pid, "timeout")
    r = conn.execute("SELECT * FROM publications WHERE id=?", (pid,)).fetchone()
    assert r["status"] == "error" and r["attempts"] == 1
    assert r["next_attempt_at"] is not None


def test_se_abandona_tras_agotar_intentos(conn, brand):
    acc = D.add_account(conn, brand, "tiktok", "@musicrock")
    cid = D.create_content(conn, brand, "x", rights_status="original")
    pid = D.enqueue_publication(conn, cid, acc)
    conn.execute("UPDATE publications SET max_attempts=2 WHERE id=?", (pid,))
    for _ in range(2):
        conn.execute("UPDATE publications SET next_attempt_at=NULL WHERE id=?", (pid,))
        D.claim_due_publications(conn)
        D.mark_failed(conn, pid, "boom")
    r = conn.execute("SELECT * FROM publications WHERE id=?", (pid,)).fetchone()
    assert r["status"] == "abandoned"


def test_accounts_no_guardan_tokens(conn, brand):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(accounts)")}
    assert "secret_ref" in cols
    assert not {"access_token", "refresh_token", "token"} & cols, \
        "los tokens jamas deben vivir en la DB"
