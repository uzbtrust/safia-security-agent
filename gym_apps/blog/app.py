"""Tiny blog with accounts: third clean target for the Red-vs-Blue gym."""
import html
import secrets
import sqlite3

from flask import Flask, abort, jsonify, redirect, request


def create_app():
    app = Flask(__name__)
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, is_admin INTEGER);
        INSERT INTO users VALUES (1, 'alice', 'alice-pass', 0), (2, 'admin', 'admin-pass', 1);
        """
    )
    resets = {}  # username -> reset token (delivered out of band, never in a response)

    def current_user():
        raw = request.headers.get("X-User", "")
        row = db.execute("SELECT id, is_admin FROM users WHERE id = ?", (raw,)).fetchone() if raw.isdigit() else None
        if row is None:
            abort(401)
        return row

    @app.get("/search")
    def search():
        q = request.args.get("q", "")
        return f"<html><body><h1>Results for {html.escape(q)}</h1><p>No posts found.</p></body></html>"

    @app.post("/register")
    def register():
        data = request.get_json(silent=True) or {}
        username, password = data.get("username"), data.get("password")
        if not isinstance(username, str) or not isinstance(password, str) or not username:
            abort(400)
        try:
            cur = db.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 0)",
                (username, password),
            )
        except sqlite3.IntegrityError:
            abort(409)
        return jsonify({"id": cur.lastrowid, "username": username}), 201

    @app.get("/admin/stats")
    def admin_stats():
        user = current_user()
        if not user["is_admin"]:
            abort(403)
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return jsonify({"secret": "ADMIN-ONLY-DATA", "users": count})

    @app.post("/reset/request")
    def reset_request():
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        row = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row is not None:
            resets[username] = secrets.token_hex(16)
        return jsonify({"ok": True})

    @app.post("/reset/confirm")
    def reset_confirm():
        data = request.get_json(silent=True) or {}
        username, token, new = data.get("username"), data.get("token"), data.get("new_password")
        if not isinstance(token, str) or not isinstance(new, str) or resets.get(username) != token:
            abort(403)
        db.execute("UPDATE users SET password = ? WHERE username = ?", (new, username))
        resets.pop(username, None)
        return jsonify({"ok": True})

    @app.get("/go")
    def go():
        target = request.args.get("next", "/")
        if not target.startswith("/") or target.startswith("//"):
            target = "/"
        return redirect(target)

    return app
