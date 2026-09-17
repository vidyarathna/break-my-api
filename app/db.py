"""Tiny SQLite layer for the ConfBadge demo API.

Note the lock: DB_LOCK protects each individual statement, which makes the code
*look* thread-safe. It does not protect a read-decide-write sequence. That is
BUG-B6 and it is the single most realistic bug in this repo.
"""

import os
import sqlite3
import threading

DB_PATH = os.environ.get("CONFBADGE_DB", "demo.db")

_conn: sqlite3.Connection | None = None
DB_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE users (
    id       INTEGER PRIMARY KEY,
    email    TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role     TEXT NOT NULL DEFAULT 'user',
    credits  REAL NOT NULL DEFAULT 0
);

CREATE TABLE tickets (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    price     REAL NOT NULL,
    stock     INTEGER NOT NULL,
    published INTEGER NOT NULL DEFAULT 1,
    audience  TEXT NOT NULL DEFAULT 'general'
);

CREATE TABLE orders (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    ticket_id INTEGER NOT NULL,
    quantity  INTEGER NOT NULL,
    coupon    TEXT,
    total     REAL NOT NULL,
    credits_earned REAL NOT NULL
);
"""

SEED = """
INSERT INTO users (id, email, password, role, credits) VALUES
    (1, 'alice@corp.example',        'alice123', 'user',  5000),
    (2, 'bob@corp.example',          'bob123',   'user',  5000),
    (9, 'root@confbadge.internal',   'r00t',     'admin', 0);

INSERT INTO tickets (id, name, price, stock, published, audience) VALUES
    (1, 'GENERAL-2026',  2000, 50, 1, 'general'),
    (2, 'STUDENT-2026',   500, 20, 1, 'student'),
    (3, 'WORKSHOP-AI',   3500,  5, 1, 'general'),
    (4, 'STAFF-COMP',       0, 10, 0, 'staff');
"""


def init_db() -> None:
    """Drop and rebuild the database. Called on startup and by POST /_reset
    so every demo run starts from identical state."""
    global _conn
    with DB_LOCK:
        if _conn is not None:
            _conn.close()
            _conn = None
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        _conn.executescript(SEED)
        _conn.commit()


def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with DB_LOCK:
        return _conn.execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    with DB_LOCK:
        return _conn.execute(sql, params).fetchone()


def execute(sql: str, params: tuple = ()) -> int:
    with DB_LOCK:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur.lastrowid
