"""Run Blue over the gym (clean + injected apps) and report each pipeline stage.

Stages show what every step buys: raw model output -> evidence-grounded -> verified (+Bandit) -> final.
Nothing in the scanned apps is executed. Results are meant for eval/results/<run>/ (result.json + summary.md).
"""
from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Callable

from .scanner import Scanner
from .score import build_cases, score_case, wilson

GYM_NOTES = ("Users are identified by the X-User header in this toy app; do not report that as a finding. "
             "Routes that never read X-User are public by design. "
             "This toy app omits rate limiting, CSRF protection, security headers and logging, and its seed data "
             "holds plaintext demo passwords, all by design: do not report those.")
STAGES = ["raw", "grounded", "verified", "final"]


def run_eval(make_client: Callable[[int], object], seeds: list[int], apps: list[str] | None = None,
             verify: bool = True, use_bandit: bool = True, use_examples: bool = True,
             notes: str = GYM_NOTES, progress=print) -> dict:
    cases = build_cases(apps)
    runs = []
    for case in cases:
        for seed in seeds:
            with tempfile.TemporaryDirectory(prefix="blue_eval_") as tmp:
                (Path(tmp) / "app.py").write_text(case.source)
                res = Scanner(make_client(seed), notes=notes, verify=verify, use_bandit=use_bandit,
                              use_examples=use_examples).scan(Path(tmp))
            scores = {st: score_case(case, res.stages[st]) for st in STAGES}
            runs.append({"case": case.id, "seed": seed, "scores": scores, "stages": res.stages,
                         "dropped": res.dropped, "meta": res.meta})
            progress(f"{case.id} seed={seed} final={scores['final']} calls={res.meta['llm_calls']}")
    return {"seeds": seeds, "verify": verify, "bandit": use_bandit, "examples": use_examples, "notes": notes,
            "cases": [c.id for c in cases], "runs": runs}


def summarize(result: dict, model: str) -> str:
    runs = result["runs"]
    clean = [r for r in runs if r["case"].endswith("/clean")]
    vuln = [r for r in runs if not r["case"].endswith("/clean")]
    lines = [f"# Blue gym evaluation: {model}", "",
             f"{len(result['cases'])} cases ({len(clean) // len(result['seeds'])} clean, "
             f"{len(vuln) // len(result['seeds'])} injected), seeds {result['seeds']}, verify "
             f"{'on' if result['verify'] else 'off'}, bandit {'on' if result['bandit'] else 'off'}, examples "
             f"{'on' if result.get('examples', True) else 'off'}. "
             "n is small: a direction, not proof.", "",
             "| stage | strict recall | function recall | CWE-only | located (any CWE) | clean runs with a false signal | findings per clean run | extras per injected run |",
             "|---|---|---|---|---|---|---|---|"]
    for st in STAGES:
        n = len(vuln)
        cell = lambda key: f"{(k := sum(r['scores'][st].get(key, 0) for r in vuln))}/{n} ({wilson(k, n)[0]:.2f}-{wilson(k, n)[1]:.2f})"
        loc = sum(r["scores"][st].get("located", 0) for r in vuln)
        fs = sum(r["scores"][st]["false_signal"] for r in clean)
        avg = sum(r["scores"][st]["n_findings"] for r in clean) / max(len(clean), 1)
        ex = sum(r["scores"][st]["extras"] for r in vuln) / max(n, 1)
        lines.append(f"| {st} | {cell('strict')} | {cell('function')} | {cell('cwe_only')} | {loc}/{n} | {fs}/{len(clean)} | {avg:.2f} | {ex:.2f} |")
    per = defaultdict(lambda: [0, 0, 0])
    for r in vuln:
        c = per[r["case"]]
        c[0] += r["scores"]["final"]["strict"]; c[1] += r["scores"]["final"]["function"]; c[2] += 1
    lines += ["", "Final stage per case (strict / function, of seeds):", "", "| case | strict | function |", "|---|---|---|"]
    lines += [f"| {k} | {v[0]}/{v[2]} | {v[1]}/{v[2]} |" for k, v in sorted(per.items())]
    tot = defaultdict(float)
    for r in runs:
        for k in ("llm_calls", "prompt_tokens", "gen_tokens", "wall_s"):
            tot[k] += r["meta"][k]
    errs = sum(len(r["meta"]["errors"]) for r in runs)
    lines += ["", f"Cost: {int(tot['llm_calls'])} LLM calls, {int(tot['prompt_tokens'])} prompt / {int(tot['gen_tokens'])} "
              f"generated tokens, {tot['wall_s']:.0f} s model time, {errs} error(s)."]
    return "\n".join(lines) + "\n"


def write(result: dict, model: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps({"model": model, **result}, indent=1))
    (out / "summary.md").write_text(summarize(result, model))
