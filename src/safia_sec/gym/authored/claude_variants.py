"""Additional Red samples authored directly by Claude in this session (no API call, no extra cost).

Each entry is a genuinely different code pattern for the SAME vulnerability class the gym already has
a golden template for (see injections.py), to address the diversity gap found earlier (Red API runs kept
rediscovering near-identical variants of one injection point per CWE). Every sample is still judged by the
SAME deterministic referee as any other Red output: nothing here is trusted because Claude wrote it.

Provenance: authored_by="claude-assistant" (not an API call), model id as reported by this session
(docs/handoff/cloud.md records the exact session). These are NOT used to fine-tune any model weights —
see CLAUDE.md "Qoidalar" for why (Claude output -> LoRA training data is kept to open-weight-model output
only). They may be used for prompt few-shot examples and gym diversity, same as the hand-written templates.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..referee import Submission


@dataclass(frozen=True)
class Variant:
    app: str
    cwe: str
    title: str
    old: str
    new: str
    marker: str
    exploit: str  # if "", reuse the golden template's exploit (same vulnerable behavior, new code shape)


VARIANTS: list[Variant] = [
    Variant(
        "shop", "CWE-89", "SQLi via .format() instead of an f-string",
        '''        rows = db.execute(
            "SELECT id, name, price FROM products WHERE hidden = 0 AND name LIKE ?",
            (f"%{q}%",),
        ).fetchall()
''',
        '''        query = "SELECT id, name, price FROM products WHERE hidden = 0 AND name LIKE '%{}%'".format(q)
        rows = db.execute(query).fetchall()
''',
        "INTERNAL-RECIPE-DRAFT", "",
    ),
    Variant(
        "shop", "CWE-22", "Path traversal via an absolute-path bypass of a naive '..' filter",
        '''        path = os.path.realpath(os.path.join(FILES, name))
        if os.path.commonpath([path, FILES]) != FILES or not os.path.isfile(path):
            abort(404)
''',
        '''        path = os.path.join(FILES, name)
        if ".." in name:
            abort(404)
        if not os.path.isfile(path):
            abort(404)
''',
        "CANARY-5f3a9c",
        '''from app import create_app, BASE


def test_exploit_path_traversal_via_absolute_path():
    client = create_app().test_client()
    resp = client.get("/files", query_string={"name": BASE + "/secret.txt"})
    assert "CANARY-5f3a9c" in resp.get_data(as_text=True)
''',
    ),
    Variant(
        "bank", "CWE-89", "SQLi in statement search via string concatenation",
        '''        rows = db.execute(
            "SELECT memo, amount FROM tx WHERE account_id = ? AND memo LIKE ?",
            (account_id, f"%{q}%"),
        ).fetchall()
''',
        '''        rows = db.execute(
            "SELECT memo, amount FROM tx WHERE account_id = ? AND memo LIKE '%" + q + "%'",
            (account_id,),
        ).fetchall()
''',
        "VIP-SECRET-MEMO", "",
    ),
    Variant(
        "bank", "CWE-840", "Negative-transfer check 'fixed' with abs(), still exploitable",
        "        if amount <= 0 or amount > owner[\"balance\"]:\n",
        "        if abs(amount) > owner[\"balance\"]:\n",
        "balance", "",
    ),
    Variant(
        "blog", "CWE-79", "Reflected XSS via string concatenation instead of an f-string",
        '''        return f"<html><body><h1>Results for {html.escape(q)}</h1><p>No posts found.</p></body></html>"
''',
        '''        return "<html><body><h1>Results for " + q + "</h1><p>No posts found.</p></body></html>"
''',
        "XSS-CANARY-7", "",
    ),
]


def build(v: Variant, golden_exploit_by_cwe: dict[str, str], app_dir) -> Submission:
    source = (app_dir / "app.py").read_text()
    assert source.count(v.old) == 1, f"{v.app}/{v.cwe}: snippet not found exactly once"
    exploit = v.exploit or golden_exploit_by_cwe[v.cwe]
    return Submission(v.cwe, {"app.py": source.replace(v.old, v.new)}, exploit, v.marker)
