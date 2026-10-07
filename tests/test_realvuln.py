import json
from pathlib import Path

import pytest

from safia_sec import cli
from safia_sec.blue import realvuln
from safia_sec.blue.llm import FakeClient


def entry(id_, vulnerable=True, file="app/app.py", start=20, end=None, cwes=("CWE-89",), **kw):
    loc = {"start_line": start}
    if end is not None:
        loc["end_line"] = end
    return {"id": id_, "is_vulnerable": vulnerable, "file": file, "location": loc, "primary_cwe": cwes[0],
            "acceptable_cwes": list(cwes), "vulnerability_class": "x", **kw}


def f(line, cwe="CWE-89", file="app/app.py"):
    return {"file": file, "line": line, "cwe": cwe}


def test_tp_needs_file_cwe_and_line_within_ten():
    gt = {"findings": [entry("a", start=20, end=22)]}
    assert realvuln.match([f(32)], gt)["tp"] == 1          # end_line + 10
    assert realvuln.match([f(33)], gt)["fp"] == 1          # one line too far
    assert realvuln.match([f(20, "CWE-79")], gt)["fp"] == 1
    assert realvuln.match([f(20, file="app/other.py")], gt)["fp"] == 1


def test_each_entry_matches_once_and_duplicates_are_fp():
    m = realvuln.match([f(20), f(21)], {"findings": [entry("a")]})
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 0)


def test_trap_hit_is_fp_and_untouched_trap_is_tn():
    gt = {"findings": [entry("v", start=20), entry("t", vulnerable=False, start=80)]}
    m = realvuln.match([f(80)], gt)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (0, 1, 1, 0)
    assert realvuln.match([], gt)["tn"] == 1


def test_vulnerable_entry_preferred_over_colocated_trap():
    gt = {"findings": [entry("t", vulnerable=False, start=20), entry("v", start=22)]}
    assert realvuln.match([f(21)], gt)["tp"] == 1


def test_non_scoring_is_withheld_not_fp_and_not_fn():
    gt = {"findings": [entry("n", start=50, scoring="non_scoring")]}
    m = realvuln.match([f(50, "CWE-200")], gt)
    assert (m["fp"], m["fn"], m["ns"]) == (0, 0, 1)


def test_acceptable_locations_and_path_normalisation():
    gt = {"findings": [entry("a", acceptable_locations=[{"file": "./app/views.py", "start_line": 5}])]}
    assert realvuln.match([f(7, file="app/views.py")], gt)["tp"] == 1
    assert realvuln.match([f(20, file="./app/app.py")], gt)["tp"] == 1


def test_fn_in_non_python_files_is_counted_separately():
    gt = {"findings": [entry("a"), entry("b", file="templates/x.html")]}
    m = realvuln.match([], gt)
    assert m["fn"] == 2 and m["fn_py"] == 1


def test_f3_weights_recall():
    assert realvuln.prf(5, 5, 5)["f3"] == pytest.approx(0.5)
    assert realvuln.prf(1, 0, 9)["f3"] < realvuln.prf(9, 9, 1)["f3"]


def test_test_half_is_locked_without_final():
    with pytest.raises(realvuln.SplitLocked):
        realvuln.load_split("test")
    assert realvuln.load_split("test", final=True)["selected"]


def test_committed_split_follows_the_rule():
    s = json.loads(realvuln.SPLIT_FILE.read_text())
    for r in s["selected"]:
        assert realvuln.load_split(r["split"], final=True)["selected"]
        assert s["all_python_repos"][r["id"]] == r["split"]
    for split in ("dev", "test"):
        human = [r for r in s["selected"] if r["split"] == split and r["authorship"] == "human_authored"]
        llm = [r for r in s["selected"] if r["split"] == split and r["authorship"] == "llm_generated"]
        assert sum(r["loc"] for r in human) <= s["human_loc_cap"] and len(llm) == 1


def fake_dataset(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / "data"
    repo = data / "repos" / "demo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "app.py").write_text('import sqlite3\n\ndef q(db, name):\n    return db.execute("SELECT * FROM u WHERE n = \'%s\'" % name)\n')
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("PASSWORD = 'not-a-finding'\n")
    gt_dir = data / "benchmark" / "ground-truth" / "demo"
    gt_dir.mkdir(parents=True)
    (gt_dir / "ground-truth.json").write_text(json.dumps({"findings": [entry("demo-1", start=4)]}))
    split = tmp_path / "split.json"
    split.write_text(json.dumps({"benchmark_url": "x", "benchmark_commit": "0" * 40, "human_loc_cap": 500,
                                 "selected": [{"id": "demo", "split": "dev", "authorship": "human_authored", "loc": 4,
                                               "vulns": 1, "traps": 0, "repo_url": "x", "commit_sha": "y"}],
                                 "all_python_repos": {"demo": "dev"}}))
    return data, split


def test_cli_eval_realvuln_end_to_end_with_a_fake_model(tmp_path, monkeypatch):
    data, split = fake_dataset(tmp_path)
    monkeypatch.setattr(realvuln, "SPLIT_FILE", split)
    seen = []

    def respond(prompt):
        seen.append(prompt)
        if prompt.startswith("You are a skeptical"):
            return json.dumps({"verdict": "confirmed", "reason": "spliced", "fix": "bind it"})
        return json.dumps({"findings": [{"file": "app/app.py", "line": 4, "cwe": "CWE-89",
                                         "evidence": "SELECT * FROM u WHERE n", "explanation": "x"}]})
    out = tmp_path / "out"
    rc = cli.main(["eval-realvuln", "--split", "dev", "--model", "fake", "--data", str(data), "--out", str(out),
                   "--no-bandit"], client_factory=lambda args, seed: FakeClient(respond))
    res = json.loads((out / "result.json").read_text())
    assert rc == 0 and res["repos"][0]["scores"]["final"]["tp"] == 1 and res["settings"]["use_examples"]
    assert not any("not-a-finding" in p for p in seen)  # tests/ was skipped
    assert "| final | 1 | 0 | 0 |" in (out / "summary.md").read_text()


def test_cli_refuses_test_half_without_final(tmp_path):
    rc = cli.main(["eval-realvuln", "--split", "test", "--model", "fake", "--data", str(tmp_path)],
                  client_factory=lambda args, seed: FakeClient(lambda p: "{}"))
    assert rc == 2
