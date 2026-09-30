"""Baseline 'Blue': does Bandit flag the injected region? (No LLM needed.)

Writes eval/baselines/bandit.json. A hit on the clean app in the same region counts
as a false positive, so the baseline is not flattered by noisy rules.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from safia_sec.gym.injections import APP_DIR, TEMPLATES, build

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
    clean = (APP_DIR / "app.py").read_text()
    rows = []
    for cwe, t in TEMPLATES.items():
        patched = build(cwe).patch["app.py"]
        new_region = region(patched, t.new) if t.new else range(0)
        # IDOR removes code: the vulnerable spot is where the check used to be.
        if not t.new:
            start = clean[: clean.index(t.old)].count("\n") + 1
            new_region = range(start - 2, start + 2)
        hit = any(n in new_region for n in bandit_lines(patched))
        old_region = region(clean, t.old)
        false_pos = any(n in old_region for n in bandit_lines(clean))
        rows.append({"cwe": cwe, "title": t.title, "detected": hit, "false_positive_on_clean": false_pos})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"tool": "bandit", "target": "gym_apps/shop", "results": rows}, indent=2))
    for r in rows:
        print(f"{r['cwe']:8} detected={r['detected']!s:5} fp_on_clean={r['false_positive_on_clean']!s:5} {r['title']}")


if __name__ == "__main__":
    main()
