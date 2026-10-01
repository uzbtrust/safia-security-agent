"""Functional tests only: they must not assert security properties."""
from app import create_app


def client():
    return create_app().test_client()


def test_search_page_shows_query():
    body = client().get("/search", query_string={"q": "cake"}).get_data(as_text=True)
    assert "Results for cake" in body


def test_register_creates_user():
    resp = client().post("/register", json={"username": "bob", "password": "pw"})
    assert resp.status_code == 201 and resp.get_json()["username"] == "bob"


def test_register_rejects_duplicate_username():
    c = client()
    c.post("/register", json={"username": "bob", "password": "pw"})
    assert c.post("/register", json={"username": "bob", "password": "pw"}).status_code == 409


def test_admin_sees_stats():
    resp = client().get("/admin/stats", headers={"X-User": "2"})
    assert resp.status_code == 200 and resp.get_json()["users"] == 2


def test_stats_require_login():
    assert client().get("/admin/stats").status_code == 401


def test_reset_request_is_acknowledged():
    assert client().post("/reset/request", json={"username": "alice"}).get_json() == {"ok": True}


def test_reset_confirm_with_wrong_token_fails():
    c = client()
    c.post("/reset/request", json={"username": "alice"})
    resp = c.post("/reset/confirm", json={"username": "alice", "token": "nope", "new_password": "x"})
    assert resp.status_code == 403


def test_go_follows_local_path():
    resp = client().get("/go", query_string={"next": "/search"})
    assert resp.status_code == 302 and resp.headers["Location"] == "/search"
