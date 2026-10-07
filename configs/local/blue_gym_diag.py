#!/usr/bin/env python3
"""What a Blue gym run did beyond the headline table: where hits die, false signals, grounding, verifier, errors, speed.

  .venv/bin/python configs/local/blue_gym_diag.py [result.json ...]   # default: eval/results/*-blue-gym-*/result.json
  .venv/bin/python configs/local/blue_gym_diag.py --decide A/result.json B/result.json   # the model choice rule of docs/EXPERIMENTS.md
Prints markdown. Every number is computed from result.json and the project's own scoring code, so run it with the
project venv (it imports safia_sec). Nothing is executed from the scanned apps.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from safia_sec.blue.score import build_cases, family_ok, wilson

ROOT = Path(__file__).resolve().parents[2]
STAGES = ["raw", "grounded", "verified", "final"]
CASES = {c.id: c for c in build_cases()}


def kind(case_id: str, line: int, cwe: str) -> str:
    """hit = right CWE family inside the injected function; extra = anything else on an injected app; fp = any finding on a clean app."""
    case = CASES[case_id]
    if case.cwe is None:
        return "fp"
    f0, f1 = case.function
    return "hit" if family_ok(case.cwe, cwe) and f0 <= line <= f1 else "extra"


def candidates(run: dict) -> dict[tuple, str]:
    """(file, line, cwe) -> confirmed/rejected, for every candidate that reached the verifier (LLM or Bandit-only)."""
    out = {}
    for f in run["stages"]["grounded"] + run["stages"]["verified"]:
        out[(f["file"], f["line"], f["cwe"])] = "confirmed"
    for d in run["dropped"]:
        if d["reason"].startswith("refuted_by_verifier"):
            out[(d["file"], d["line"], d["cwe"])] = "rejected"
    return out


def where_hits_die(runs: list[dict]) -> list[str]:
    seeds = len({r["seed"] for r in runs})
    per = defaultdict(lambda: Counter())
    for r in runs:
        if CASES[r["case"]].cwe is None:
            continue
        for st in STAGES:
            per[r["case"]][st] += r["scores"][st]["function"]
    rows = ["| injected case | " + " | ".join(STAGES) + " |", "|---|" + "---|" * len(STAGES)]
    rows += [f"| {c} | " + " | ".join(f"{per[c][st]}/{seeds}" for st in STAGES) + " |" for c in sorted(per)]
    return rows


def false_signals(runs: list[dict]) -> list[str]:
    seen = Counter()
    for r in runs:
        if CASES[r["case"]].cwe is None:
            for f in r["stages"]["final"]:
                seen[(r["case"], f["cwe"], f["line"], f["evidence"][:70].replace("|", "/"), "+".join(f["sources"]))] += 1
    rows = ["| clean app | CWE | line | evidence | sources | runs |", "|---|---|---|---|---|---|"]
    rows += [f"| {c} | {cwe} | {ln} | `{ev}` | {src} | {n} |" for (c, cwe, ln, ev, src), n in sorted(seen.items())]
    return rows if seen else ["No finding survived on a clean app."]


def verifier(res: dict) -> list[str]:
    if not res["verify"]:
        return ["Verifier was off."]
    tally = Counter()
    refuted_hits = []
    for r in res["runs"]:
        for (_, line, cwe), verdict in candidates(r).items():
            tally[(kind(r["case"], line, cwe), verdict)] += 1
        for d in r["dropped"]:
            if d["reason"].startswith("refuted_by_verifier") and kind(r["case"], d["line"], d["cwe"]) == "hit":
                refuted_hits.append(f"{r['case']} seed {r['seed']} {d['cwe']} line {d['line']}: {d['reason'][21:150]}")
    rows = ["| candidate kind | reached the verifier | confirmed | rejected | rejected share |", "|---|---|---|---|---|"]
    for k, label in (("hit", "hit (injected bug)"), ("extra", "extra on injected app"), ("fp", "finding on clean app")):
        c, j = tally[(k, "confirmed")], tally[(k, "rejected")]
        rows.append(f"| {label} | {c + j} | {c} | {j} | {j / (c + j):.0%} |" if c + j else f"| {label} | 0 | 0 | 0 | - |")
    unavailable = sum(e.startswith("verify ") for r in res["runs"] for e in r["meta"]["errors"])
    rows += ["", f"Verifier calls that failed and were kept as confirmed (fail-open): {unavailable}."]
    if refuted_hits:
        rows += ["", "True findings the verifier rejected (first 4):"] + [f"- {x}" for x in refuted_hits[:4]]
    return rows


def grounding(runs: list[dict]) -> str:
    raw = sum(len(r["stages"]["raw"]) for r in runs)
    drops = Counter(d["reason"].split(":")[0] for r in runs for d in r["dropped"])
    return (f"{raw} raw findings; dropped before verification for evidence not in the source: "
            f"{drops.get('evidence_not_in_source', 0)}; refuted by the verifier: {drops.get('refuted_by_verifier', 0)}.")


def errors(runs: list[dict]) -> list[str]:
    errs = [e for r in runs for e in r["meta"]["errors"]]
    if not errs:
        return ["No error recorded in `meta.errors` (no invalid JSON, no truncated context, no unreachable server)."]
    kinds = Counter(e.split(": ", 1)[1].split(":")[0] if ": " in e else e for e in errs)
    rows = [f"{len(errs)} error(s) in {sum(bool(r['meta']['errors']) for r in runs)} of {len(runs)} runs: "
            + ", ".join(f"{k} x{n}" for k, n in kinds.most_common()), ""]
    return rows + [f"- {e}" for e in errs[:5]]


def speed(runs: list[dict]) -> list[str]:
    calls = sum(r["meta"]["llm_calls"] for r in runs)
    wall = sum(r["meta"]["wall_s"] for r in runs)
    prompt = sum(r["meta"]["prompt_tokens"] for r in runs)
    gen = sum(r["meta"]["gen_tokens"] for r in runs)
    rate = [r["meta"]["gen_tokens"] / r["meta"]["wall_s"] for r in runs if r["meta"]["wall_s"] > 0]
    rows = [f"{calls} calls, {wall:.0f} s model time ({wall / max(calls, 1):.1f} s per call), "
            f"{prompt / max(calls, 1):.0f} prompt and {gen / max(calls, 1):.0f} generated tokens per call "
            f"(context limit 8192)."]
    if len(rate) >= 3:
        third = len(rate) // 3
        rows.append(f"Generated tokens per model second, prefill included: first third of the runs "
                    f"{statistics.median(rate[:third]):.1f}, last third {statistics.median(rate[-third:]):.1f} "
                    f"(an indicator of thermal throttling only: the cases differ in size).")
    return rows


def decide(paths: list[Path]) -> str:
    """The model choice rule pre-registered in docs/EXPERIMENTS.md, applied to exactly two dev gym results."""
    res = [json.loads(p.read_text()) for p in paths]
    assert len(res) == 2, "give exactly two result.json files"
    same = all(res[0][k] == res[1][k] for k in ("seeds", "cases", "verify", "bandit", "notes"))
    rows = []
    for r in res:
        inj = [x for x in r["runs"] if CASES[x["case"]].cwe is not None]
        clean = [x for x in r["runs"] if CASES[x["case"]].cwe is None]
        rows.append({"model": r["model"], "n": len(inj), "k": sum(x["scores"]["final"]["function"] for x in inj),
                     "m": len(clean), "fs": sum(x["scores"]["final"]["false_signal"] for x in clean),
                     "per_clean": sum(x["scores"]["final"]["n_findings"] for x in clean) / max(len(clean), 1),
                     "wall": statistics.mean(x["meta"]["wall_s"] for x in r["runs"]),
                     "errors": sum(len(x["meta"]["errors"]) for x in r["runs"])})
    a, b = rows
    out = ["| | " + " | ".join(x["model"] for x in rows) + " |", "|---|---|---|"]
    ci = lambda x: f"{x['k']}/{x['n']} ({wilson(x['k'], x['n'])[0]:.2f}-{wilson(x['k'], x['n'])[1]:.2f})"
    out += [f"| function recall at final | {ci(a)} | {ci(b)} |",
            f"| clean runs with a false signal | {a['fs']}/{a['m']} | {b['fs']}/{b['m']} |",
            f"| findings per clean run | {a['per_clean']:.2f} | {b['per_clean']:.2f} |",
            f"| model seconds per run | {a['wall']:.1f} | {b['wall']:.1f} |",
            f"| errors in meta.errors | {a['errors']} | {b['errors']} |", ""]
    if not same:
        out.append("WARNING: the two runs differ in seeds, cases, verify, bandit or notes: not comparable.")
    gap = a["k"] - b["k"]
    pick = lambda better_is_a, step, why: f"Step {step} decides: {why} -> **{(a if better_is_a else b)['model']}**"
    if abs(gap) >= 3:
        out.append(pick(gap > 0, 1, f"recall gap {abs(gap)} of {a['n']} runs (3 or more)"))
    elif a["fs"] != b["fs"]:
        out.append(pick(a["fs"] < b["fs"], 2, f"recall gap {abs(gap)} (< 3), false signals on clean runs {a['fs']} against {b['fs']}"))
    elif a["per_clean"] != b["per_clean"]:
        out.append(pick(a["per_clean"] < b["per_clean"], 2, f"recall gap {abs(gap)} (< 3), same false-signal runs, findings per clean run {a['per_clean']:.2f} against {b['per_clean']:.2f}"))
    elif a["wall"] != b["wall"]:
        out.append(pick(a["wall"] < b["wall"], 3, f"everything else tied, model seconds per run {a['wall']:.1f} against {b['wall']:.1f}"))
    else:
        out.append("Complete tie on every step: no rule outcome.")
    return "\n".join(out)


def main() -> None:
    if sys.argv[1:2] == ["--decide"]:
        print(decide([Path(a) for a in sys.argv[2:]]))
        return
    paths = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "eval" / "results").glob("*-blue-gym-*/result.json"))
    for p in paths:
        res = json.loads(p.read_text())
        runs = res["runs"]
        print(f"# {res['model']}  ({p.parent.name}; seeds {res['seeds']}, {len(res['cases'])} cases)\n")
        print("## Function-level hits by stage (primary metric)\n", *where_hits_die(runs), sep="\n")
        print("\n## False signals that survived on clean apps\n", *false_signals(runs), sep="\n")
        print("\n## Verifier behaviour\n", *verifier(res), sep="\n")
        print("\n## Grounding\n\n" + grounding(runs))
        print("\n## Errors\n", *errors(runs), sep="\n")
        print("\n## Speed\n", *speed(runs), sep="\n")
        print()


if __name__ == "__main__":
    main()
