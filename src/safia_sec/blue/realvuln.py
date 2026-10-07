"""RealVuln (external benchmark) adapter: fetch the pinned split, scan it with Blue, score it.

Scoring re-implements RealVuln's matcher semantics (their code is never executed here):
- a finding is a TP when its file equals the entry's file (or one of its acceptable_locations), its CWE is in
  the entry's acceptable_cwes and its line is within [start_line - 10, end_line + 10];
- each ground-truth entry can be matched once; a finding that matches no entry, or matches a false-positive
  trap, is an FP; unmatched vulnerable entries are FN, unmatched traps TN;
- entries marked "non_scoring" take no part: a finding on one is withheld (NS), never an FP;
- F3 = 10PR / (9P + R), RealVuln's primary metric. Precision and recall are always shown too.
The test half is only reachable with final=True (pre-registered: run once, after the freeze).
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .scanner import Scanner, canonical_cwe
from .score import wilson

SPLIT_FILE = Path(__file__).resolve().parents[3] / "targets" / "realvuln" / "split.json"
LINE_TOL = 10
STAGES = ["raw", "grounded", "verified", "final"]


class SplitLocked(Exception):
    pass


def load_split(split: str, final: bool = False, path: Path | None = None) -> dict:
    if split == "test" and not final:
        raise SplitLocked("the RealVuln test half runs once, after the freeze: pass final=True / --final")
    data = json.loads(Path(path or SPLIT_FILE).read_text())
    return {**data, "selected": [r for r in data["selected"] if r["split"] == split]}


# ------------------------------------------------------------------------------------------------ fetch
def _git(*args: str, cwd: Path | None = None) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()[:300]}")
    return res.stdout.strip()


def fetch(split: str, dest: Path, final: bool = False, log=print) -> None:
    """Pinned checkouts: ground truth of the selected repos (sparse) and each repo at its commit."""
    s = load_split(split, final)
    dest = Path(dest)
    bench = dest / "benchmark"
    if not (bench / ".git").exists():
        bench.mkdir(parents=True, exist_ok=True)
        _git("init", "-q", cwd=bench)
        _git("remote", "add", "origin", s["benchmark_url"], cwd=bench)
        _git("config", "core.sparseCheckout", "true", cwd=bench)
    (bench / ".git" / "info").mkdir(parents=True, exist_ok=True)
    wanted = sorted({f"ground-truth/{r['id']}/ground-truth.json" for r in s["selected"]}
                    | set((bench / ".git" / "info" / "sparse-checkout").read_text().split()
                          if (bench / ".git" / "info" / "sparse-checkout").exists() else []))
    (bench / ".git" / "info" / "sparse-checkout").write_text("\n".join(wanted) + "\n")
    _git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", s["benchmark_commit"], cwd=bench)
    _git("-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD", cwd=bench)
    assert _git("rev-parse", "HEAD", cwd=bench) == s["benchmark_commit"]
    log(f"benchmark ground truth at {s['benchmark_commit'][:12]}")
    for r in s["selected"]:
        repo = dest / "repos" / r["id"]
        if repo.exists() and _git("rev-parse", "HEAD", cwd=repo) == r["commit_sha"]:
            log(f"ok (cached) {r['id']}")
            continue
        repo.mkdir(parents=True, exist_ok=True)
        if not (repo / ".git").exists():
            _git("init", "-q", cwd=repo)
            _git("remote", "add", "origin", r["repo_url"], cwd=repo)
        _git("fetch", "-q", "--depth", "1", "origin", r["commit_sha"], cwd=repo)
        _git("-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD", cwd=repo)
        assert _git("rev-parse", "HEAD", cwd=repo) == r["commit_sha"]
        log(f"ok {r['id']} @ {r['commit_sha'][:12]}")


# ------------------------------------------------------------------------------------------------ score
def norm_path(p: str) -> str:
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _in_range(line: int | None, start: int | None, end: int | None) -> bool:
    if line is None or start is None:
        return True
    return start - LINE_TOL <= line <= (end if end is not None else start) + LINE_TOL


def _at_location(f: dict, entry: dict) -> bool:
    loc = entry.get("location", {})
    if f["file"] == norm_path(entry["file"]) and _in_range(f["line"], loc.get("start_line"), loc.get("end_line")):
        return True
    return any(f["file"] == norm_path(a.get("file", "")) and _in_range(f["line"], a.get("start_line"), a.get("end_line"))
               for a in entry.get("acceptable_locations", []))


def match(findings: list[dict], gt: dict) -> dict:
    """findings: [{file, line, cwe}]. Returns counts and per-item classifications."""
    scored = [e for e in gt["findings"] if e.get("scoring", "scored") == "scored"]
    non_scoring = [e for e in gt["findings"] if e.get("scoring", "scored") == "non_scoring"]
    used: set[str] = set()
    out = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "ns": 0, "fn_py": 0, "items": []}
    for f in findings:
        f = {**f, "file": norm_path(f["file"]), "cwe": canonical_cwe(f["cwe"])}
        cands = [e for e in scored if e["id"] not in used and f["cwe"] in e["acceptable_cwes"] and _at_location(f, e)]
        if cands:
            best = sorted(cands, key=lambda e: not e["is_vulnerable"])[0]
            used.add(best["id"])
            cls = "TP" if best["is_vulnerable"] else "FP"
            out["items"].append({"class": cls, "gt": best["id"], **f})
        elif f.get("line") is not None and any(_at_location(f, e) for e in non_scoring):
            out["items"].append({"class": "NS", "gt": None, **f})
        else:
            out["items"].append({"class": "FP", "gt": None, **f})
    for e in scored:
        if e["id"] in used:
            continue
        cls = "FN" if e["is_vulnerable"] else "TN"
        out["items"].append({"class": cls, "gt": e["id"], "file": e["file"], "line": e.get("location", {}).get("start_line"),
                             "cwe": e.get("primary_cwe"), "vclass": e.get("vulnerability_class")})
        if cls == "FN" and e["file"].endswith(".py"):
            out["fn_py"] += 1
    for it in out["items"]:
        out[it["class"].lower()] += 1
    return out


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f3 = 10 * p * r / (9 * p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f3": round(f3, 4)}


# -------------------------------------------------------------------------------------------------- run
@dataclass
class Settings:
    verify: bool = True
    use_bandit: bool = True
    use_examples: bool = True
    include_tests: bool = False


def run(make_client: Callable[[int], object], split: str, data: Path, seed: int = 1, settings: Settings = Settings(),
        final: bool = False, progress=print) -> dict:
    s = load_split(split, final)
    data = Path(data)
    repos = []
    for r in s["selected"]:
        root = data / "repos" / r["id"]
        gt = json.loads((data / "benchmark" / "ground-truth" / r["id"] / "ground-truth.json").read_text())
        res = Scanner(make_client(seed), notes="", verify=settings.verify, use_bandit=settings.use_bandit,
                      use_examples=settings.use_examples, include_tests=settings.include_tests).scan(root)
        scores = {st: match(res.stages[st], gt) for st in STAGES}
        repos.append({"id": r["id"], "authorship": r["authorship"], "loc": r["loc"], "commit_sha": r["commit_sha"],
                      "scores": {st: {k: v for k, v in sc.items() if k != "items"} for st, sc in scores.items()},
                      "items": scores["final"]["items"], "stages": res.stages, "dropped": res.dropped, "meta": res.meta})
        f = scores["final"]
        progress(f"{r['id']}: TP={f['tp']} FP={f['fp']} FN={f['fn']} calls={res.meta['llm_calls']} "
                 f"model_s={res.meta['wall_s']} errors={len(res.meta['errors'])}")
    return {"benchmark_commit": s["benchmark_commit"], "split": split, "seed": seed, "settings": settings.__dict__,
            "repos": repos}


def summarize(result: dict, model: str) -> str:
    rs = result["repos"]
    st = result["settings"]
    lines = [f"# RealVuln {result['split']}: {model}", "",
             f"{len(rs)} repos, benchmark {result['benchmark_commit'][:12]}, seed {result['seed']}, verify "
             f"{'on' if st['verify'] else 'off'}, bandit {'on' if st['use_bandit'] else 'off'}, examples "
             f"{'on' if st['use_examples'] else 'off'}. RealVuln matcher semantics (file + acceptable CWE + line +-10).", "",
             "| stage | TP | FP | FN | traps hit (FP) | precision | recall (95% CI) | F3 |", "|---|---|---|---|---|---|---|---|"]
    for stage in STAGES:
        tp, fp, fn = (sum(r["scores"][stage][k] for r in rs) for k in ("tp", "fp", "fn"))
        traps = sum(1 for r in rs for it in (r["items"] if stage == "final" else []) if it["class"] == "FP" and it["gt"])
        m = prf(tp, fp, fn)
        lo, hi = wilson(tp, tp + fn)
        lines.append(f"| {stage} | {tp} | {fp} | {fn} | {traps if stage == 'final' else '-'} | {m['precision']:.2f} | "
                     f"{m['recall']:.2f} ({lo:.2f}-{hi:.2f}) | {m['f3']:.2f} |")
    lines += ["", "Final stage per stratum and repo:", "",
              "| repo | authorship | LOC | TP | FP | FN | FN in .py | precision | recall | F3 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for group in ("human_authored", "llm_generated"):
        g = [r for r in rs if r["authorship"] == group]
        for r in g:
            sc = r["scores"]["final"]
            m = prf(sc["tp"], sc["fp"], sc["fn"])
            lines.append(f"| {r['id']} | {group} | {r['loc']} | {sc['tp']} | {sc['fp']} | {sc['fn']} | {sc['fn_py']} | "
                         f"{m['precision']:.2f} | {m['recall']:.2f} | {m['f3']:.2f} |")
        if g:
            tp, fp, fn, fnpy = (sum(r["scores"]["final"][k] for r in g) for k in ("tp", "fp", "fn", "fn_py"))
            m = prf(tp, fp, fn)
            lines.append(f"| **all {group}** | | {sum(r['loc'] for r in g)} | {tp} | {fp} | {fn} | {fnpy} | "
                         f"{m['precision']:.2f} | {m['recall']:.2f} | {m['f3']:.2f} |")
    tp, fn, fnpy = (sum(r["scores"]["final"][k] for r in rs) for k in ("tp", "fn", "fn_py"))
    py_recall = tp / (tp + fnpy) if tp + fnpy else 0.0
    calls = sum(r["meta"]["llm_calls"] for r in rs)
    secs = sum(r["meta"]["wall_s"] for r in rs)
    errs = sum(len(r["meta"]["errors"]) for r in rs)
    lines += ["", f"Recall over labels in .py files only (the scanner's scope): {py_recall:.2f}.",
              f"Cost: {calls} LLM calls, {secs:.0f} s model time, {errs} error(s)."]
    return "\n".join(lines) + "\n"


def write(result: dict, model: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps({"model": model, **result}, indent=1))
    (out / "summary.md").write_text(summarize(result, model))
