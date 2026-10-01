#!/usr/bin/env python3
"""Blue probe: can a local model find the vulnerabilities in the gym shop app? It reads code and never runs it.

Cases: the clean gym_apps/shop/app.py and its three vulnerable versions (injections.build). For every case the
model gets the numbered source and must return JSON findings {file, line, cwe, evidence, explanation}.
Scored: strict hit (CWE family and a line within +-5 of the injected region), location-only hit, evidence that
really occurs in the source, false signals on the clean app, JSON validity, speed and memory.

  .venv/bin/python configs/local/blue_probe.py --model qwen2.5-coder:7b [--runs 3] [--temperature 0.7]
Writes eval/results/<date>-blue-probe-<model>/{result.json,summary.md}.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
from safia_sec.gym.injections import APP_DIR, TEMPLATES, build  # noqa: E402

TOL = 5  # lines of slack around the injected region
FAMILY = {"CWE-89": {89}, "CWE-639": {639, 284, 285, 862, 863}, "CWE-22": {22, 23, 36, 73}}
SCHEMA = {"type": "object", "properties": {"findings": {"type": "array", "items": {
    "type": "object",
    "properties": {"file": {"type": "string"}, "line": {"type": "integer"}, "cwe": {"type": "string"},
                   "evidence": {"type": "string"}, "explanation": {"type": "string"}},
    "required": ["file", "line", "cwe", "evidence", "explanation"]}}}, "required": ["findings"]}
PROMPT = """You are a security reviewer. Read the Python/Flask file below and report real security vulnerabilities in it.

Rules:
- Report only vulnerabilities you can point to in this code. If there are none, return an empty list.
- For each finding give: "file" (app.py), "line" (the line number shown at the left), "cwe" (like "CWE-89"),
  "evidence" (the exact code copied from the file, without the line numbers) and "explanation" (one or two
  sentences on how it can be exploited).
- Users are identified by the X-User header in this toy app; do not report that as a finding.
- Do not report missing rate limiting, CSRF or logging.
Reply with JSON only: {{"findings": [...]}}

app.py:
```
{numbered}
```"""


def post(host: str, path: str, body: dict, timeout: int = 900) -> tuple[dict, float]:
    req = urllib.request.Request(host + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp), time.time() - t0


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as exc:
        return f"error: {exc!r}"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def cwe_num(s: str) -> int | None:
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else None


def lines_of(source: str, snippet: str) -> tuple[int, int]:
    start = source[: source.index(snippet)].count("\n") + 1
    return start, start + snippet.rstrip("\n").count("\n")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - a) / d, (c + a) / d


def build_cases() -> tuple[dict, dict]:
    clean = (APP_DIR / "app.py").read_text()
    cases = {"clean": {"source": clean, "region": None}}
    for cwe, t in TEMPLATES.items():
        patched = build(cwe).patch["app.py"]
        if t.new:
            region = lines_of(patched, t.new)
        else:  # the vulnerability is a removed check: it was here in the clean file
            s, _ = lines_of(clean, t.old)
            region = (s - 1, s + 1)
        cases[cwe] = {"source": patched, "region": region}
    clean_regions = {cwe: lines_of(clean, t.old) for cwe, t in TEMPLATES.items()}
    return cases, clean_regions


def near(line: int, region: tuple[int, int]) -> bool:
    return region[0] - TOL <= line <= region[1] + TOL


def evidence_ok(evidence: str, source: str) -> bool:
    e = norm(evidence)
    if e and e in norm(source):
        return True
    return any(len(x.strip()) >= 12 and norm(x) in norm(source) for x in (evidence or "").splitlines())


def run_one(host, model, source, seed, temperature, think, num_ctx, num_predict) -> dict:
    numbered = "\n".join(f"{i:3d}  {ln}" for i, ln in enumerate(source.splitlines(), 1))
    body = {"model": model, "stream": False, "format": SCHEMA,
            "messages": [{"role": "user", "content": PROMPT.format(numbered=numbered)}],
            "options": {"temperature": temperature, "seed": seed, "num_ctx": num_ctx, "num_predict": num_predict}}
    if think is not None:
        body["think"] = think
    d, wall = post(host, "/api/chat", body)
    content = d["message"]["content"]
    ge, gd = d.get("eval_count", 0), d.get("eval_duration", 0)
    rec = {"wall_s": round(wall, 1), "prompt_tokens": d.get("prompt_eval_count"), "gen_tokens": ge,
           "decode_tok_s": round(ge / (gd / 1e9), 1) if gd else None, "done_reason": d.get("done_reason")}
    try:
        data = json.loads(content)
        findings = data["findings"]
        ok = isinstance(findings, list) and all(
            isinstance(f, dict) and isinstance(f.get("line"), int) and isinstance(f.get("cwe"), str) and
            isinstance(f.get("evidence"), str) for f in findings)
        rec["valid_json"] = bool(ok)
        rec["findings"] = [dict(f, explanation=str(f.get("explanation", ""))[:300]) for f in findings] if ok else []
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        rec.update(valid_json=False, findings=[], error=str(exc)[:120], raw_head=content[:160])
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--num-predict", type=int, default=1500)
    ap.add_argument("--think", choices=["off", "on"], default="off", help="thinking mode, for models that support it")
    a = ap.parse_args()

    tags = {x["name"]: x for x in json.load(urllib.request.urlopen(a.host + "/api/tags"))["models"]}
    if a.model not in tags:
        sys.exit(f"model not pulled: {a.model}")
    show, _ = post(a.host, "/api/show", {"model": a.model})
    caps = show.get("capabilities") or []
    think = (a.think == "on") if "thinking" in caps else None
    cases, clean_regions = build_cases()

    runs = []
    for name, c in cases.items():
        for r in range(a.runs):
            rec = {"case": name, "run": r, "seed": r + 1,
                   **run_one(a.host, a.model, c["source"], r + 1, a.temperature, think, a.num_ctx, a.num_predict)}
            fs = rec["findings"]
            rec["evidence_ok"] = sum(evidence_ok(f["evidence"], c["source"]) for f in fs)
            if name == "clean":
                rec["fp_regions"] = sorted({cw for cw, reg in clean_regions.items() for f in fs
                                            if cwe_num(f["cwe"]) in FAMILY[cw] and near(f["line"], reg)})
            else:
                fam, reg = FAMILY[name], c["region"]
                rec["strict"] = any(cwe_num(f["cwe"]) in fam and near(f["line"], reg) for f in fs)
                rec["loc_only"] = any(near(f["line"], reg) for f in fs)
                rec["cwe_only"] = any(cwe_num(f["cwe"]) in fam for f in fs)
            runs.append(rec)
            print(name, r, {k: rec.get(k) for k in ("valid_json", "strict", "fp_regions", "decode_tok_s")},
                  len(fs), "findings", flush=True)

    ps = [m for m in json.load(urllib.request.urlopen(a.host + "/api/ps"))["models"] if m["name"] == a.model]
    resident = {"size_gb": round(ps[0]["size"] / 1e9, 2), "vram_gb": round(ps[0]["size_vram"] / 1e9, 2)} if ps else None
    vuln = [r for r in runs if r["case"] != "clean"]
    clean_runs = [r for r in runs if r["case"] == "clean"]
    n_find = sum(len(r["findings"]) for r in runs)
    agg = {"recall_strict": sum(r["strict"] for r in vuln), "recall_loc_only": sum(r["loc_only"] for r in vuln),
           "recall_cwe_only": sum(r["cwe_only"] for r in vuln), "vuln_runs": len(vuln),
           "fp_clean_runs": sum(bool(r["fp_regions"]) for r in clean_runs), "clean_runs": len(clean_runs),
           "findings_on_clean_mean": round(statistics.mean(len(r["findings"]) for r in clean_runs), 2),
           "json_valid": sum(r["valid_json"] for r in runs), "generations": len(runs),
           "evidence_ok": sum(r["evidence_ok"] for r in runs), "findings_total": n_find,
           "decode_tok_s_median": statistics.median([r["decode_tok_s"] for r in runs if r["decode_tok_s"]] or [0]),
           "wall_s_median": statistics.median(r["wall_s"] for r in runs), "resident": resident}
    res = {"model": {"tag": a.model, "digest": tags[a.model]["digest"], "size_bytes": tags[a.model]["size"],
                     "details": show.get("details"), "capabilities": caps},
           "config": {"temperature": a.temperature, "seeds": list(range(1, a.runs + 1)), "num_ctx": a.num_ctx,
                      "num_predict": a.num_predict, "think": think, "tolerance_lines": TOL},
           "env": {"git_sha": sh(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"]),
                   "power": (sh(["pmset", "-g", "batt"]).splitlines() or ["?"])[0],
                   "memory_pressure": (sh(["memory_pressure"]).splitlines() or ["?"])[-1],
                   "swap": sh(["sysctl", "-n", "vm.swapusage"])},
           "aggregate": agg, "runs": runs}
    out = ROOT / "eval" / "results" / f"{date.today():%Y%m%d}-blue-probe-{a.model.replace(':', '_').replace('/', '_')}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(res, indent=2))

    lo, hi = wilson(agg["recall_strict"], agg["vuln_runs"])
    lines = [f"# Blue probe: {a.model}", "",
             f"- git `{res['env']['git_sha']}`, digest `{tags[a.model]['digest'][:12]}`, {res['model']['details'].get('parameter_size')} "
             f"{res['model']['details'].get('quantization_level')}; T={a.temperature}, seeds 1-{a.runs}, num_ctx {a.num_ctx}, "
             f"thinking={think}",
             f"- {res['env']['power']}; at the end: {res['env']['memory_pressure']}",
             "- Bandit baseline (eval/baselines/bandit.json): 1 of 3 found (CWE-89 only), no false signal on the clean app.", "",
             "| Case | strict hit | location only | CWE only | findings (mean) | JSON valid |", "|---|---|---|---|---|---|"]
    for name in cases:
        rs = [r for r in runs if r["case"] == name]
        mean_f = round(statistics.mean(len(r["findings"]) for r in rs), 1)
        if name == "clean":
            lines.append(f"| clean (false signal in an injected region) | {sum(bool(r['fp_regions']) for r in rs)}/{len(rs)} | - | - | "
                         f"{mean_f} | {sum(r['valid_json'] for r in rs)}/{len(rs)} |")
        else:
            lines.append(f"| {name} | {sum(r['strict'] for r in rs)}/{len(rs)} | {sum(r['loc_only'] for r in rs)}/{len(rs)} | "
                         f"{sum(r['cwe_only'] for r in rs)}/{len(rs)} | {mean_f} | {sum(r['valid_json'] for r in rs)}/{len(rs)} |")
    lines += ["", f"- Recall strict {agg['recall_strict']}/{agg['vuln_runs']} (Wilson 95% {lo:.2f}-{hi:.2f}); location only "
              f"{agg['recall_loc_only']}/{agg['vuln_runs']}; CWE only {agg['recall_cwe_only']}/{agg['vuln_runs']}",
              f"- False signal on the clean app: {agg['fp_clean_runs']}/{agg['clean_runs']} runs; {agg['findings_on_clean_mean']} findings per clean run",
              f"- JSON valid {agg['json_valid']}/{agg['generations']}; evidence found in the source {agg['evidence_ok']}/{agg['findings_total']} findings",
              f"- Speed {agg['decode_tok_s_median']} tok/s decode (median), {agg['wall_s_median']} s per generation (median); resident {resident}",
              "", "Examples to look at (case, run in result.json):"]
    misses = [f"miss {r['case']}#{r['run']}" for r in vuln if not r["strict"]][:3]
    fps = [f"false signal clean#{r['run']} {r['fp_regions']}" for r in clean_runs if r["fp_regions"]][:2]
    lines += [f"- {x}" for x in (misses + fps)] or ["- none"]
    lines += ["", f"Small sample ({a.runs} runs x 4 cases): a direction, not proof. The injected region is the only ground truth,",
              "so extra findings are not necessarily wrong. Generated text only; nothing was executed."]
    (out / "summary.md").write_text("\n".join(lines[:60]) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
