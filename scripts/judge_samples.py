"""Judge samples written by `red_generate.py --no-judge` (run this on Linux).

Generation happens where the API keys / Ollama live (e.g. a Mac, without isolation);
judging executes model-written code, so it runs here, inside the referee sandbox.

  python scripts/judge_samples.py eval/results/<run>/        # -> eval/judged/<run>/
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from safia_sec.gym.injections import APPS, app_dir
from safia_sec.gym.referee import Submission, judge


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    data = json.loads((args.run_dir / "result.json").read_text())
    out = args.out or Path("eval/judged") / args.run_dir.resolve().name
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for rec in data["samples"]:
        rec = dict(rec)
        if rec["status"] == "old_found_unjudged":
            if "old" not in rec:
                rec["status"] = "missing_old"  # sample from an older script version
            else:
                app = rec.get("app", "shop")  # older runs only attacked the shop app
                source = (app_dir(app) / "app.py").read_text()
                t = APPS[app][rec["cwe"]]
                sub = Submission(rec["cwe"], {"app.py": source.replace(rec["old"], rec["new"])},
                                 rec["exploit_test"], t.marker)
                v = judge(app_dir(app), sub)
                if v.reason == "no_isolation":
                    sys.exit("referee sandbox unavailable here; run on Linux (unshare -rn) or Docker")
                rec["status"] = "accepted" if v.accepted else f"rejected:{v.reason}"
                rec["detail"] = v.detail[:300]
        rows.append(rec)

    per_cwe = {}
    for key in sorted({f"{r.get('app', 'shop')}/{r['cwe']}" for r in rows}):
        rs = [r for r in rows if f"{r.get('app', 'shop')}/{r['cwe']}" == key]
        ok = [r for r in rs if r["status"] == "accepted"]
        per_cwe[key] = {"generated": len(rs), "accepted": len(ok),
                        "distinct_accepted": len({re.sub(r"\s+", "", r["new"]) for r in ok}),
                        "reasons": dict(Counter(r["status"] for r in rs if r["status"] != "accepted"))}
    (out / "judged.json").write_text(json.dumps(
        {"source_run": str(args.run_dir), "model": data["model"], "provider": data.get("provider"),
         "per_cwe": per_cwe, "samples": rows}, indent=2))
    lines = [f"# Judged: {data['model']} ({data.get('provider', '?')})", "",
             "| app/CWE | generated | accepted | distinct | top rejection |", "|---|---|---|---|---|"]
    for key, r in per_cwe.items():
        top = max(r["reasons"], key=r["reasons"].get) if r["reasons"] else "-"
        lines.append(f"| {key} | {r['generated']} | {r['accepted']} | {r['distinct_accepted']} | {top} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines)); print("written:", out)


if __name__ == "__main__":
    main()
