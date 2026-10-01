"""Functional tests only: they must not assert security properties."""
from app import create_app


def client():
    return create_app().test_client()


def test_owner_reads_own_account():
    resp = client().get("/accounts/1", headers={"X-User": "1"})
    assert resp.status_code == 200 and resp.get_json()["balance"] == 100.0


def test_accounts_require_login():
    assert client().get("/accounts/1").status_code == 401


def test_unknown_account_is_404():
    assert client().get("/accounts/99", headers={"X-User": "1"}).status_code == 404


def test_transfer_moves_money():
    c = client()
    resp = c.post("/transfer", json={"from": 1, "to": 2, "amount": 30}, headers={"X-User": "1"})
    assert resp.status_code == 200
    assert c.get("/accounts/1", headers={"X-User": "1"}).get_json()["balance"] == 70.0
    assert c.get("/accounts/2", headers={"X-User": "2"}).get_json()["balance"] == 530.0


def test_transfer_over_balance_is_rejected():
    resp = client().post("/transfer", json={"from": 1, "to": 2, "amount": 1000}, headers={"X-User": "1"})
    assert resp.status_code == 400


def test_statement_search_finds_memo():
    resp = client().get("/statement", query_string={"account": "1", "q": "sal"}, headers={"X-User": "1"})
    assert [t["memo"] for t in resp.get_json()] == ["salary"]


def test_serves_a_receipt():
    resp = client().get("/receipt", query_string={"name": "r1.txt"})
    assert resp.status_code == 200 and "paid" in resp.get_data(as_text=True)


def test_missing_receipt_is_404():
    assert client().get("/receipt", query_string={"name": "nope.txt"}).status_code == 404
