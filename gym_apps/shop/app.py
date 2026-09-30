"""Tiny bakery shop: the clean target for the Red-vs-Blue gym."""
import os
import sqlite3

from flask import Flask, abort, jsonify, request

BASE = os.path.dirname(os.path.realpath(__file__))
FILES = os.path.join(BASE, "files")


def create_app():
    app = Flask(__name__)
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, hidden INTEGER);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, item TEXT, total REAL);
        INSERT INTO products VALUES (1, 'Napoleon cake', 25.0, 0), (2, 'Honey cake', 20.0, 0),
                                    (3, 'INTERNAL-RECIPE-DRAFT', 0.0, 1);
        INSERT INTO orders VALUES (1, 1, 'Napoleon cake', 25.0), (2, 2, 'Honey cake', 20.0);
        """
    )

    def current_user():
        raw = request.headers.get("X-User", "")
        if not raw.isdigit():
            abort(401)
        return int(raw)

    @app.get("/products")
    def products():
        q = request.args.get("q", "")
        rows = db.execute(
            "SELECT id, name, price FROM products WHERE hidden = 0 AND name LIKE ?",
            (f"%{q}%",),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/orders/<int:order_id>")
    def order(order_id):
        user = current_user()
        row = db.execute(
            "SELECT id, user_id, item, total FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if row is None:
            abort(404)
        if row["user_id"] != user:
            abort(403)
        return jsonify(dict(row))

    @app.get("/files")
    def files():
        name = request.args.get("name", "")
        path = os.path.realpath(os.path.join(FILES, name))
        if os.path.commonpath([path, FILES]) != FILES or not os.path.isfile(path):
            abort(404)
        with open(path, encoding="utf-8") as fh:
            return fh.read(), 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app
