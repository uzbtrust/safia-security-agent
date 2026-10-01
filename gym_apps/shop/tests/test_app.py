"""Functional tests only: they must not assert security properties."""
from app import create_app


def client():
    return create_app().test_client()


def test_search_returns_matching_visible_products():
    resp = client().get("/products", query_string={"q": "Napoleon"})
    assert [p["name"] for p in resp.get_json()] == ["Napoleon cake"]


def test_search_without_query_lists_visible_products():
    assert len(client().get("/products").get_json()) == 2


def test_owner_can_read_own_order():
    resp = client().get("/orders/1", headers={"X-User": "1"})
    assert resp.status_code == 200 and resp.get_json()["item"] == "Napoleon cake"


def test_orders_require_login():
    assert client().get("/orders/1").status_code == 401


def test_unknown_order_is_404():
    assert client().get("/orders/99", headers={"X-User": "1"}).status_code == 404


def test_serves_a_public_file():
    resp = client().get("/files", query_string={"name": "menu.txt"})
    assert resp.status_code == 200 and "napoleon" in resp.get_data(as_text=True)


def test_missing_file_is_404():
    assert client().get("/files", query_string={"name": "nope.txt"}).status_code == 404
