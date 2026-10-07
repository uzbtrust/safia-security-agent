"""Judge the Claude-authored Red variants with the same referee as everything else.

  .venv/bin/python scripts/claude_red_batch.py
Writes eval/results/<date>-red-claude-<model>/ (result.json + summary.md), same shape as API Red runs,
so judge_samples.py's downstream readers (and docs/EXPERIMENTS.md tables) treat it identically.
"""
import json
from collections import Counter
from datetime import date
from pathlib import Path

from safia_sec.gym.authored.claude_variants import VARIANTS, build
from safia_sec.gym.injections import APPS, app_dir
from safia_sec.gym.referee import judge

MODEL = "claude-sonnet-5"  # this session's configured model (docs/handoff/cloud.md records it exactly)


def main() -> None:
    samples = []
    for v in VARIANTS:
        golden = {cwe: t.exploit for cwe, t in APPS[v.app].items()}
        sub = build(v, golden, app_dir(v.app))
        verdict = judge(app_dir(v.app), sub)
        rec = {"app": v.app, "cwe": v.cwe, "title": v.title,
               "status": "accepted" if verdict.accepted else f"rejected:{verdict.reason}",
               "detail": verdict.detail[:300], "new": sub.patch["app.py"],
               "served_by": {"authored_by": "claude-assistant", "model": MODEL, "mode": "direct-authoring"}}
        samples.append(rec)
        print(v.app, v.cwe, rec["status"])

    reasons = Counter(s["status"] for s in samples if s["status"] != "accepted")
    out = Path("eval/results") / f"{date.today():%Y%m%d}-red-claude-{MODEL.replace('-', '_')}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(
        {"model": MODEL, "provider": "claude-direct-authoring", "samples": samples}, indent=2))
    lines = [f"# Claude-authored Red variants ({MODEL})", "",
             f"{sum(s['status'] == 'accepted' for s in samples)}/{len(samples)} accepted by the referee.",
             "Not API calls: written directly in the cloud session, at no extra token cost beyond this session.",
             "Used for gym diversity and Blue's few-shot memory only -- NOT for fine-tuning any model's weights.",
             "", "| app/CWE | title | status |", "|---|---|---|"]
    lines += [f"| {s['app']}/{s['cwe']} | {s['title']} | {s['status']} |" for s in samples]
    if reasons:
        lines += ["", "Rejections: " + ", ".join(f"{k} x{v}" for k, v in reasons.items())]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines)); print("written:", out)


if __name__ == "__main__":
    main()
