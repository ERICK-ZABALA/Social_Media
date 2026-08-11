-- Social Media Factory — esquema base (Etapa 1)
-- SQLite. Fuente de verdad de todo el pipeline.
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Marcas / canales
CREATE TABLE IF NOT EXISTS brands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Cuentas por plataforma (una marca puede tener varias)
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id        INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    platform        TEXT NOT NULL CHECK (platform IN
                      ('tiktok','youtube','instagram','facebook','x','linkedin')),
    handle          TEXT,
    -- NUNCA guardamos tokens aqui: solo el nombre del secreto externo.
    secret_ref      TEXT,
    open_id         TEXT,
    is_sandbox      INTEGER NOT NULL DEFAULT 1,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (brand_id, platform, handle)
);

-- Temas ya cubiertos: memoria anti-repeticion
CREATE TABLE IF NOT EXISTS topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id    INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    topic_key   TEXT NOT NULL,          -- hash normalizado del tema
    label       TEXT NOT NULL,
    times_used  INTEGER NOT NULL DEFAULT 0,
    last_used   TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (brand_id, topic_key)
);

-- Piezas de contenido
CREATE TABLE IF NOT EXISTS content_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id        INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    topic_id        INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    kind            TEXT NOT NULL DEFAULT 'video'
                      CHECK (kind IN ('video','image','text')),
    title           TEXT,
    body            TEXT,
    media_path      TEXT,
    -- Maquina de estados explicita
    state           TEXT NOT NULL DEFAULT 'draft' CHECK (state IN
                      ('draft','pending_approval','approved','scheduled',
                       'publishing','published','failed','rejected','archived')),
    scheduled_at    TEXT,
    -- Licencia / copyright: obligatorio antes de aprobar
    rights_status   TEXT NOT NULL DEFAULT 'unknown' CHECK (rights_status IN
                      ('unknown','original','licensed','public_domain','risky')),
    rights_note     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ci_state ON content_items(state);
CREATE INDEX IF NOT EXISTS idx_ci_brand ON content_items(brand_id, state);

-- Auditoria de cambios de estado (append-only)
CREATE TABLE IF NOT EXISTS state_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id  INTEGER NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    from_state  TEXT,
    to_state    TEXT NOT NULL,
    actor       TEXT NOT NULL DEFAULT 'system',
    note        TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_se_content ON state_events(content_id);

-- Decisiones humanas (Telegram)
CREATE TABLE IF NOT EXISTS approvals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id  INTEGER NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    decision    TEXT NOT NULL CHECK (decision IN ('approve','edit','reject')),
    comment     TEXT,
    chat_id     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Intentos de publicacion: idempotencia + reintentos
CREATE TABLE IF NOT EXISTS publications (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id        INTEGER NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    account_id        INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    -- clave unica: impide publicar dos veces la misma pieza en la misma cuenta
    idempotency_key   TEXT NOT NULL UNIQUE,
    status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
                        ('queued','in_flight','done','error','abandoned')),
    attempts          INTEGER NOT NULL DEFAULT 0,
    max_attempts      INTEGER NOT NULL DEFAULT 5,
    next_attempt_at   TEXT,
    publish_id        TEXT,   -- publish_id que devuelve TikTok
    external_post_id  TEXT,   -- id final del post publicado
    privacy_level     TEXT,
    last_error        TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_pub_status ON publications(status, next_attempt_at);

-- Metricas
CREATE TABLE IF NOT EXISTS metrics (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_id    INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
    views             INTEGER DEFAULT 0,
    likes             INTEGER DEFAULT 0,
    comments          INTEGER DEFAULT 0,
    shares            INTEGER DEFAULT 0,
    captured_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_metrics_pub ON metrics(publication_id, captured_at);
