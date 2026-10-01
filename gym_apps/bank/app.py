"""Tiny bank: second clean target for the Red-vs-Blue gym."""
import os
import sqlite3

from flask import Flask, abort, jsonify, request

BASE = os.path.dirname(os.path.realpath(__file__))
RECEIPTS = os.path.join(BASE, "receipts")


def create_app():
    app = Flask(__name__)
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE accounts (id INTEGER PRIMARY KEY, user_id INTEGER, balance REAL);
        CREATE TABLE tx (id INTEGER PRIMARY KEY, account_id INTEGER, memo TEXT, amount REAL);
        INSERT INTO accounts VALUES (1, 1, 100.0), (2, 2, 500.0);
        INSERT INTO tx VALUES (1, 1, 'salary', 100.0), (2, 2, 'VIP-SECRET-MEMO', 500.0);
        """
    )

    def current_user():
        raw = request.headers.get("X-User", "")
        if not raw.isdigit():
            abort(401)
        return int(raw)

    @app.get("/accounts/<int:account_id>")
    def account(account_id):
        user = current_user()
        row = db.execute(
            "SELECT id, user_id, balance FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if row is None:
            abort(404)
        if row["user_id"] != user:
            abort(403)
        return jsonify(dict(row))

    @app.post("/transfer")
    def transfer():
        user = current_user()
        data = request.get_json(silent=True) or {}
        try:
            src, dst, amount = int(data["from"]), int(data["to"]), float(data["amount"])
        except (KeyError, TypeError, ValueError):
            abort(400)
        owner = db.execute("SELECT user_id, balance FROM accounts WHERE id = ?", (src,)).fetchone()
        target = db.execute("SELECT id FROM accounts WHERE id = ?", (dst,)).fetchone()
        if owner is None or target is None:
            abort(404)
        if owner["user_id"] != user:
            abort(403)
        if amount <= 0 or amount > owner["balance"]:
            abort(400)
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, src))
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, dst))
        return jsonify({"ok": True})

    @app.get("/statement")
    def statement():
        user = current_user()
        account_id = request.args.get("account", "")
        q = request.args.get("q", "")
        owner = db.execute("SELECT user_id FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if owner is None:
            abort(404)
        if owner["user_id"] != user:
            abort(403)
        rows = db.execute(
            "SELECT memo, amount FROM tx WHERE account_id = ? AND memo LIKE ?",
            (account_id, f"%{q}%"),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/receipt")
    def receipt():
        name = request.args.get("name", "")
        path = os.path.realpath(os.path.join(RECEIPTS, name))
        if os.path.commonpath([path, RECEIPTS]) != RECEIPTS or not os.path.isfile(path):
            abort(404)
        with open(path, encoding="utf-8") as fh:
            return fh.read(), 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app
