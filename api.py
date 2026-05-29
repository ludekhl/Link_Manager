"""REST API for the Link Manager database.

Runs alongside the Streamlit app (app.py) and shares the same SQLite file,
so links created/edited here show up in the UI and vice versa. Intended to be
consumed by the linkmanager MCP server (Claude on M3 + the Briefing Dashboard
"Rob" on M2).

Auth: every /api/* route requires the X-API-Key header to match the
LINKMANAGER_API_KEY environment variable. /health is open.

Schema (unchanged, defined by app.py):
    groups(id, name UNIQUE)
    links(id, name, url, group_name -> groups.name)

No created_at column; "category" in the user's words maps to group_name.
"""
from __future__ import annotations

import os
import sqlite3
from functools import wraps

from flask import Flask, g, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("LINKMANAGER_DB", os.path.join(BASE_DIR, "links_db.sqlite"))
API_KEY = os.environ.get("LINKMANAGER_API_KEY", "")

app = Flask(__name__)


# ── DB helpers ────────────────────────────────────────────────────────────────


def _db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def _close_db(_exc: object) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _ensure_schema() -> None:
    """Match app.py's init_db so the API can run standalone (fresh DB)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS groups "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS links "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, url TEXT, group_name TEXT, "
        "FOREIGN KEY(group_name) REFERENCES groups(name))"
    )
    c.execute("INSERT OR IGNORE INTO groups (name) VALUES ('General')")
    conn.commit()
    conn.close()


# ── Auth ────────────────────────────────────────────────────────────────────


def require_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not API_KEY:
            return jsonify(error="Server missing LINKMANAGER_API_KEY"), 500
        if request.headers.get("X-API-Key") != API_KEY:
            return jsonify(error="Unauthorized"), 401
        return fn(*args, **kwargs)

    return wrapper


def _link_row(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "name": r["name"], "url": r["url"], "group": r["group_name"]}


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> object:
    db = _db()
    n = db.execute("SELECT COUNT(*) AS n FROM links").fetchone()["n"]
    return jsonify(status="ok", links=n)


# ── Links ─────────────────────────────────────────────────────────────────────


@app.get("/api/links")
@require_key
def list_links() -> object:
    """List or search links.

    Query params:
      q      — case-insensitive substring match on name OR url
      group  — exact group filter
      limit  — max rows (default 200)
    """
    q = (request.args.get("q") or "").strip()
    group = (request.args.get("group") or "").strip()
    try:
        limit = min(int(request.args.get("limit", 200)), 1000)
    except ValueError:
        limit = 200

    sql = "SELECT id, name, url, group_name FROM links"
    where, params = [], []
    if q:
        where.append("(name LIKE ? COLLATE NOCASE OR url LIKE ? COLLATE NOCASE)")
        params += [f"%{q}%", f"%{q}%"]
    if group:
        where.append("group_name = ?")
        params.append(group)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = _db().execute(sql, params).fetchall()
    return jsonify(count=len(rows), links=[_link_row(r) for r in rows])


@app.get("/api/links/<int:link_id>")
@require_key
def get_link(link_id: int) -> object:
    r = _db().execute(
        "SELECT id, name, url, group_name FROM links WHERE id = ?", (link_id,)
    ).fetchone()
    if not r:
        return jsonify(error="Not found"), 404
    return jsonify(link=_link_row(r))


@app.post("/api/links")
@require_key
def create_link() -> object:
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    url = (data.get("url") or "").strip()
    group = (data.get("group") or "General").strip() or "General"
    if not name or not url:
        return jsonify(error="name and url are required"), 400

    db = _db()
    # Auto-create the group so a new category never silently lands in General.
    db.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (group,))
    cur = db.execute(
        "INSERT INTO links (name, url, group_name) VALUES (?, ?, ?)",
        (name, url, group),
    )
    db.commit()
    r = db.execute(
        "SELECT id, name, url, group_name FROM links WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(link=_link_row(r)), 201


@app.patch("/api/links/<int:link_id>")
@require_key
def update_link(link_id: int) -> object:
    data = request.get_json(silent=True) or {}
    db = _db()
    existing = db.execute(
        "SELECT id, name, url, group_name FROM links WHERE id = ?", (link_id,)
    ).fetchone()
    if not existing:
        return jsonify(error="Not found"), 404

    name = (data.get("name") if data.get("name") is not None else existing["name"])
    url = (data.get("url") if data.get("url") is not None else existing["url"])
    group = (data.get("group") if data.get("group") is not None else existing["group_name"])
    name = (name or "").strip()
    url = (url or "").strip()
    group = (group or "General").strip() or "General"
    if not name or not url:
        return jsonify(error="name and url cannot be empty"), 400

    db.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (group,))
    db.execute(
        "UPDATE links SET name = ?, url = ?, group_name = ? WHERE id = ?",
        (name, url, group, link_id),
    )
    db.commit()
    r = db.execute(
        "SELECT id, name, url, group_name FROM links WHERE id = ?", (link_id,)
    ).fetchone()
    return jsonify(link=_link_row(r))


@app.delete("/api/links/<int:link_id>")
@require_key
def delete_link(link_id: int) -> object:
    db = _db()
    r = db.execute("SELECT id FROM links WHERE id = ?", (link_id,)).fetchone()
    if not r:
        return jsonify(error="Not found"), 404
    db.execute("DELETE FROM links WHERE id = ?", (link_id,))
    db.commit()
    return jsonify(deleted=link_id)


# ── Groups ──────────────────────────────────────────────────────────────────


@app.get("/api/groups")
@require_key
def list_groups() -> object:
    rows = _db().execute(
        "SELECT g.name AS name, COUNT(l.id) AS count "
        "FROM groups g LEFT JOIN links l ON l.group_name = g.name "
        "GROUP BY g.name ORDER BY g.name"
    ).fetchall()
    return jsonify(groups=[{"name": r["name"], "count": r["count"]} for r in rows])


@app.post("/api/groups")
@require_key
def create_group() -> object:
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400
    db = _db()
    db.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (name,))
    db.commit()
    return jsonify(group=name), 201


@app.patch("/api/groups/<path:old_name>")
@require_key
def rename_group(old_name: str) -> object:
    data = request.get_json(silent=True) or {}
    new_name = (data.get("name") or "").strip()
    if old_name == "General":
        return jsonify(error="Cannot rename the General group"), 400
    if not new_name:
        return jsonify(error="new name is required"), 400
    db = _db()
    exists = db.execute("SELECT 1 FROM groups WHERE name = ?", (old_name,)).fetchone()
    if not exists:
        return jsonify(error="Group not found"), 404
    db.execute("UPDATE groups SET name = ? WHERE name = ?", (new_name, old_name))
    db.execute(
        "UPDATE links SET group_name = ? WHERE group_name = ?", (new_name, old_name)
    )
    db.commit()
    return jsonify(group=new_name)


@app.delete("/api/groups/<path:name>")
@require_key
def delete_group(name: str) -> object:
    if name == "General":
        return jsonify(error="Cannot delete the General group"), 400
    db = _db()
    exists = db.execute("SELECT 1 FROM groups WHERE name = ?", (name,)).fetchone()
    if not exists:
        return jsonify(error="Group not found"), 404
    # Mirror app.py: links of a deleted group fall back to General.
    db.execute("UPDATE links SET group_name = 'General' WHERE group_name = ?", (name,))
    db.execute("DELETE FROM groups WHERE name = ?", (name,))
    db.commit()
    return jsonify(deleted=name)


_ensure_schema()


if __name__ == "__main__":
    port = int(os.environ.get("LINKMANAGER_API_PORT", 7001))
    app.run(host="0.0.0.0", port=port)
