"""Bandit baseline on the RealVuln split, scored with the same matcher as Blue (eval/baselines/realvuln_bandit.*).

Bandit is a classical rule-based scanner; nothing is tuned here. Two variants: MEDIUM+ severity and confidence (the
filter Blue's pipeline uses for its Bandit candidates) and every result. Same file filter as Blue (tests and
migrations skipped). The test half needs --final.
  python scripts/bandit_realvuln.py --data .cache/realvuln [--final]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from safia_sec.blue import realvuln
from safia_sec.blue.scanner import SKIP_DIRS, canonical_cwe, is_test_path

OUT = Path(__file__).resolve().parents[1] / "eval" / "baselines"


def bandit(root: Path) -> list[dict]:
    cmd = [sys.executable, "-m", "bandit", "-q", "-f", "json", "-r", str(root), "-x", ",".join(f"*/{d}" for d in SKIP_DIRS)]
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=300).stdout or "{}")
    out = []
    for r in data.get("results", []):
        rel = Path(r["filename"]).resolve().relative_to(root.resolve())
        if is_test_path(rel) or not (r.get("issue_cwe") or {}).get("id"):
            continue
        out.append({"file": str(rel), "line": r["line_number"], "cwe": canonical_cwe(str(r["issue_cwe"]["id"])),
                    "medium_plus": r["issue_severity"] != "LOW" and r["issue_confidence"] != "LOW"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".cache/realvuln")
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args()
    data, report, lines = Path(args.data), {}, ["# Bandit baseline on RealVuln (same matcher as Blue)", "",
                                                  "| split | variant | TP | FP | FN | precision | recall | F3 |", "|---|---|---|---|---|---|---|---|"]
    for split in ("dev", "test") if args.final else ("dev",):
        repos = realvuln.load_split(split, final=args.final)["selected"]
        for variant in ("medium_plus", "all"):
            tot = {"tp": 0, "fp": 0, "fn": 0}
            per = {}
            for r in repos:
                gt = json.loads((data / "benchmark" / "ground-truth" / r["id"] / "ground-truth.json").read_text())
                found = [f for f in bandit(data / "repos" / r["id"]) if variant == "all" or f["medium_plus"]]
                m = realvuln.match(found, gt)
                per[r["id"]] = {k: m[k] for k in ("tp", "fp", "fn")}
                for k in tot:
                    tot[k] += m[k]
            report[f"{split}/{variant}"] = {"total": {**tot, **realvuln.prf(tot["tp"], tot["fp"], tot["fn"])}, "repos": per}
            p = realvuln.prf(tot["tp"], tot["fp"], tot["fn"])
            lines.append(f"| {split} | {variant} | {tot['tp']} | {tot['fp']} | {tot['fn']} | {p['precision']:.2f} | "
                         f"{p['recall']:.2f} | {p['f3']:.2f} |")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "realvuln_bandit.json").write_text(json.dumps(report, indent=1) + "\n")
    (OUT / "realvuln_bandit.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
