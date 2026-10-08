"""Write targets/realvuln/lora_train.json: the repos LoRA may train on (pre-registered rule).

Rule: the RealVuln dev half, minus the 6 dev-evaluation repos, minus any repo whose distinctive code lines
(>= 25 non-space characters) overlap the selected test repos by more than OVERLAP_CAP. Reads the test repos'
code only to measure that overlap; no label of the test half is read.
  python scripts/lora_split.py <benchmark checkout> <dir with dev repos> <dir with the selected test repos>
"""
import json
import re
import sys
from pathlib import Path

from safia_sec.blue.realvuln import SPLIT_FILE, _git
from safia_sec.blue.scanner import iter_python_files
from safia_sec.lora.data import TRAIN_FILE

OVERLAP_CAP = 0.10


def code_lines(root: Path) -> set[str]:
    out = set()
    for f in iter_python_files(root):
        for ln in f.read_text(errors="replace").splitlines():
            t = re.sub(r"\s+", "", ln)
            if len(t) >= 25:
                out.add(t)
    return out


def main() -> None:
    bench, dev_dir, test_dir = (Path(a) for a in sys.argv[1:4])
    split = json.loads(SPLIT_FILE.read_text())
    assert _git("rev-parse", "HEAD", cwd=bench) == split["benchmark_commit"], "benchmark checkout at the wrong commit"
    eval_dev = {r["id"] for r in split["selected"] if r["split"] == "dev"}
    test_sel = [r["id"] for r in split["selected"] if r["split"] == "test"]
    test_code = set().union(*(code_lines(test_dir / r) for r in test_sel))
    train, excluded, overlap = [], {}, {}
    for rid, half in sorted(split["all_python_repos"].items()):
        if half != "dev":
            continue
        if rid in eval_dev:
            excluded[rid] = "dev evaluation repo"
            continue
        lines = code_lines(dev_dir / rid)
        overlap[rid] = round(len(lines & test_code) / max(len(lines), 1), 4)
        if overlap[rid] > OVERLAP_CAP:
            excluded[rid] = f"code overlap with test repos {overlap[rid]:.1%}"
        else:
            train.append(rid)
    TRAIN_FILE.write_text(json.dumps({"benchmark_commit": split["benchmark_commit"], "overlap_cap": OVERLAP_CAP,
                                      "rule": "dev half - dev-evaluation repos - repos with code overlap > cap",
                                      "train_repos": train, "excluded": excluded, "overlap": overlap}, indent=1) + "\n")
    print(f"{len(train)} training repos, {len(excluded)} excluded; max overlap {max(overlap.values()):.1%}")


if __name__ == "__main__":
    main()
