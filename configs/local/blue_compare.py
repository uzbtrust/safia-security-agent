#!/usr/bin/env python3
"""One comparison table from the Blue probe results of several models. Nothing in it is typed by hand.

  .venv/bin/python configs/local/blue_compare.py [result.json ...]   # default: eval/results/*-blue-probe-*/result.json
Writes eval/results/<date>-blue-probe-comparison/summary.md. Run it with the project venv (it imports blue_probe).
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "configs" / "local"))
from blue_probe import wilson  # noqa: E402


def num(v, nd: int = 1) -> str:
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) and v else "-"


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "eval" / "results").glob("*-blue-probe-*/result.json"))
    paths = [p for p in paths if "comparison" not in str(p)]
    res = sorted((json.loads(p.read_text()) for p in paths), key=lambda r: r["model"]["tag"])
    bandit = json.loads((ROOT / "eval" / "baselines" / "bandit.json").read_text())["results"]
    b_hit = sum(bool(r["detected"]) for r in bandit)
    b_fp = sum(bool(r["false_positive_on_clean"]) for r in bandit)

    q = ["| Model | strict recall (95% CI) | location only | CWE only | strict per CWE 89/639/22 | false signal on clean | JSON valid | evidence in source |",
         "|---|---|---|---|---|---|---|---|"]
    c = ["| Model | Ollama | decode tok/s | prefill tok/s | first load s | s per generation | resident | power | thinking |", "|---|---|---|---|---|---|---|---|---|"]
    for r in res:
        a, runs = r["aggregate"], r["runs"]
        lo, hi = wilson(a["recall_strict"], a["vuln_runs"])
        per = "/".join(f"{sum(x['strict'] for x in runs if x['case'] == k)}" for k in ("CWE-89", "CWE-639", "CWE-22"))
        ev = f"{a['evidence_ok']}/{a['findings_total']}"
        q.append(f"| {r['model']['tag']} | {a['recall_strict']}/{a['vuln_runs']} ({lo:.2f}-{hi:.2f}) | {a['recall_loc_only']}/{a['vuln_runs']} | "
                 f"{a['recall_cwe_only']}/{a['vuln_runs']} | {per} of 3 each | {a['fp_clean_runs']}/{a['clean_runs']} runs ({a['findings_on_clean_mean']} findings) | "
                 f"{a['json_valid']}/{a['generations']} | {ev} |")
        res_mem = a.get("resident") or {}
        power = (r["env"]["power"] or "?").replace("Now drawing from ", "").strip("'")
        c.append(f"| {r['model']['tag']} | {r['env'].get('ollama', '-')} | {num(a['decode_tok_s_median'])} | {num(a.get('prefill_tok_s_median'))} | {num(a.get('load_s_first'))} | "
                 f"{num(a['wall_s_median'])} | {num(res_mem.get('size_gb'), 2)} GB | {power} | {r['config']['think']} |")
    q.append(f"| Bandit (baseline) | {b_hit}/3 | - | - | - | {b_fp}/3 | - | - |")

    best = max(res, key=lambda r: r["aggregate"]["recall_strict"])
    calm = min(res, key=lambda r: (r["aggregate"]["fp_clean_runs"], r["aggregate"]["findings_on_clean_mean"]))
    cfg = res[0]["config"]
    lines = [f"# Blue probe comparison ({len(res)} local models)", "",
             f"Same prompts and scoring for every model: T={cfg['temperature']}, seeds {cfg['seeds']}, num_ctx {cfg['num_ctx']}, "
             f"+-{cfg['tolerance_lines']} lines, 4 cases (clean + 3 injected), nothing executed. Bandit is the static baseline (strict recall = CWE found at the region).",
             "Rows for runs made before load/prefill timing was added show '-' there. Quality columns are comparable.", "",
             *q, "", *c, "",
             f"- Highest strict recall: {best['model']['tag']} ({best['aggregate']['recall_strict']}/{best['aggregate']['vuln_runs']}).",
             f"- Fewest false signals on the clean app: {calm['model']['tag']} ({calm['aggregate']['fp_clean_runs']}/{calm['aggregate']['clean_runs']} runs).",
             f"- Samples are tiny ({res[0]['aggregate']['vuln_runs']} injected runs per model): a direction, not proof. The injected region is the only ground truth,",
             "  so extra findings are not necessarily wrong. Recommendation is written by hand below the table when the numbers are in."]
    out = ROOT / "eval" / "results" / f"{date.today():%Y%m%d}-blue-probe-comparison"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
