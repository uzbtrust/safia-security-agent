import json
from pathlib import Path

from safia_sec.blue.llm import FakeClient
from safia_sec.blue.scanner import DETECT_SCHEMA, MAX_TEXT, Scanner, load_prompt, snap_line
from safia_sec.blue import fewshot
from safia_sec.lora import data

SRC = '''import sqlite3


def find(db, name):
    q = "SELECT * FROM users WHERE name = '%s'" % name
    return db.execute(q).fetchall()


def safe(db, name):
    return db.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchall()
'''


def label(id_, line, vulnerable=True, file="app/models.py", end=None, cwe="CWE-89"):
    loc = {"start_line": line, **({"end_line": end} if end else {})}
    return {"id": id_, "is_vulnerable": vulnerable, "file": file, "location": loc, "primary_cwe": cwe,
            "acceptable_cwes": [cwe], "vulnerability_class": "sqli",
            "evidence": {"description": "User input is formatted into the SQL text. " * 12}}


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "app").mkdir(parents=True)
    (root / "app" / "models.py").write_text(SRC)
    (root / "tests").mkdir()
    (root / "tests" / "test_models.py").write_text("PASSWORD = 'x'\n")
    return root


def test_training_prompt_is_byte_identical_to_the_scanner_prompt(tmp_path):
    root = repo(tmp_path)
    exs, _ = data.repo_examples("r", root, {"findings": [label("a", 5)]}, load_prompt("detect"), fewshot.block())
    seen = []
    Scanner(FakeClient(lambda p: seen.append(p) or json.dumps({"findings": []})), verify=False,
            use_bandit=False).scan(root)
    assert [e.prompt for e in exs] == seen  # same files, chunks, numbering, prompt and examples; tests/ skipped


def test_answer_fits_the_schema_and_passes_grounding(tmp_path):
    root = repo(tmp_path)
    exs, stats = data.repo_examples("r", root, {"findings": [label("a", 5), label("t", 10, vulnerable=False)]},
                                    load_prompt("detect"), fewshot.block())
    ans = json.loads(exs[0].answer)
    f = ans["findings"][0]
    assert exs[0].kind == "positive" and len(ans["findings"]) == 1  # the trap is not a target
    assert set(f) == set(DETECT_SCHEMA["properties"]["findings"]["items"]["required"])
    assert len(f["explanation"]) <= MAX_TEXT and len(f["evidence"]) <= MAX_TEXT
    assert snap_line(f["evidence"], SRC, f["line"]) == f["line"] == 5
    assert stats["labels_used"] == 1


def test_label_on_a_blank_line_uses_the_next_quotable_line():
    lines = SRC.splitlines()
    assert data.evidence_line(lines, 3, None) == 4  # line 3 is blank -> "def find(db, name):"
    assert data.evidence_line(["", "", ""], 1, 3) is None


def test_seeding_hubs_are_excluded(tmp_path):
    root = repo(tmp_path)
    gt = {"findings": [label(f"h{i}", 5) for i in range(17)]}
    assert data.hub_files(gt) == {"app/models.py"}
    exs, stats = data.repo_examples("r", root, gt, load_prompt("detect"), fewshot.block())
    assert exs == [] and stats["hub_files"] == ["app/models.py"]


def test_labelled_chunk_without_a_quotable_line_is_never_a_negative(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "a.py").write_text("\n\n\nx = 1\n")
    exs, _ = data.repo_examples("r", root, {"findings": [label("a", 1, file="a.py", end=2)]},
                                load_prompt("detect"), fewshot.block())
    assert [e.kind for e in exs] == ["skip"]
    assert data.select(exs) == []


def test_select_keeps_positives_and_traps_and_balances_negatives():
    mk = lambda kind, i: data.Example("r", f"{kind}{i}.py", 1, 2, "p", "{}", 0, kind)
    exs = [mk("positive", i) for i in range(5)] + [mk("trap", i) for i in range(2)] + [mk("negative", i) for i in range(20)]
    kinds = [e.kind for e in data.select(exs)]
    assert kinds.count("positive") == 5 and kinds.count("trap") == 2 and kinds.count("negative") == 3


def test_long_explanations_are_cut_at_a_sentence():
    text = data.shorten("First sentence is here. " * 40)
    assert len(text) <= MAX_TEXT and text.endswith(".")
