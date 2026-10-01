"""Baseline 'Blue': does Bandit flag the injected region? (No LLM needed.)

Writes eval/baselines/bandit.json. A hit on the clean app in the same region counts
as a false positive, so the baseline is not flattered by noisy rules.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from safia_sec.gym.injections import all_templates, app_dir, APPS, build

OUT = Path(__file__).resolve().parents[1] / "eval" / "baselines" / "bandit.json"


def bandit_lines(source: str) -> list[int]:
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "app.py"
        f.write_text(source)
        res = subprocess.run([sys.executable, "-m", "bandit", "-q", "-f", "json", str(f)],
                             capture_output=True, text=True)
        return [r["line_number"] for r in json.loads(res.stdout)["results"]]


def region(source: str, snippet: str) -> range:
    start = source[: source.index(snippet)].count("\n") + 1
    return range(start - 1, start + snippet.count("\n") + 1)


def main() -> None:
    rows = []
    for app, cwe in all_templates():
        t = APPS[app][cwe]
        clean = (app_dir(app) / "app.py").read_text()
        patched = build(cwe, app).patch["app.py"]
        if t.new:
            region_new = region(patched, t.new)
        else:  # code was removed: the weak spot is where the removed lines used to be
            start = clean[: clean.index(t.old)].count("\n") + 1
            region_new = range(start - 2, start + 2)
        hit = any(n in region_new for n in bandit_lines(patched))
        false_pos = any(n in region(clean, t.old) for n in bandit_lines(clean))
        rows.append({"app": app, "cwe": cwe, "title": t.title, "detected": hit,
                     "false_positive_on_clean": false_pos})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"tool": "bandit", "target": "gym_apps/*", "results": rows}, indent=2))
    for r in rows:
        print(f"{r['app']:5} {r['cwe']:8} detected={r['detected']!s:5} fp_on_clean={r['false_positive_on_clean']!s:5} {r['title']}")
    print(f"detected {sum(r['detected'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()
