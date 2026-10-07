"""Write the pre-registered RealVuln dev/test split (targets/realvuln/split.json).

Rule (docs/EXPERIMENTS.md, fixed before any run on RealVuln):
  1. Universe: Python repos in RealVuln's ground truth at the pinned benchmark commit.
  2. Split by repo: sha256(repo_id) even -> dev, odd -> test. Mechanical, so nobody picks the test set.
  3. Selection per split (local runtime budget): human-authored repos with a known size (loc > 0) in
     ascending LOC while the cumulative LOC stays <= HUMAN_LOC_CAP, plus the single smallest
     LLM-generated repo. The same rule for dev and test.

Usage: python scripts/realvuln_split.py <path to a RealVuln checkout at BENCH_COMMIT>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BENCH_URL = "https://github.com/kolega-ai/Real-Vuln-Benchmark"
BENCH_COMMIT = "7a710251f55c17d32d3adcb13d37468e2e3b9e4a"
HUMAN_LOC_CAP = 500
OUT = Path(__file__).resolve().parents[1] / "targets" / "realvuln" / "split.json"


def split_of(repo_id: str) -> str:
    return "dev" if int(hashlib.sha256(repo_id.encode()).hexdigest(), 16) % 2 == 0 else "test"


def main() -> None:
    bench = Path(sys.argv[1])
    head = subprocess.run(["git", "-C", str(bench), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert head == BENCH_COMMIT, f"benchmark checkout is at {head}, expected {BENCH_COMMIT}"
    manifest = json.loads((bench / "benchmark-manifest.json").read_text())["repos"]
    repos = []
    for gt_path in sorted((bench / "ground-truth").glob("*/ground-truth.json")):
        gt = json.loads(gt_path.read_text())
        if gt.get("language") != "python":
            continue
        rid = gt_path.parent.name
        scored = [f for f in gt["findings"] if f.get("scoring", "scored") == "scored"]
        repos.append({"id": rid, "split": split_of(rid), "authorship": gt["authorship"], "loc": gt.get("loc") or 0,
                      "vulns": sum(f["is_vulnerable"] for f in scored),
                      "traps": sum(not f["is_vulnerable"] for f in scored),
                      "repo_url": manifest[rid]["repo_url"], "commit_sha": manifest[rid]["commit_sha"]})

    selected = []
    for split in ("dev", "test"):
        human = sorted((r for r in repos if r["split"] == split and r["authorship"] == "human_authored" and r["loc"] > 0),
                       key=lambda r: (r["loc"], r["id"]))
        total = 0
        for r in human:
            if total + r["loc"] > HUMAN_LOC_CAP:
                break
            total += r["loc"]
            selected.append(r)
        llm = sorted((r for r in repos if r["split"] == split and r["authorship"] == "llm_generated"),
                     key=lambda r: (r["loc"], r["id"]))
        selected.append(llm[0])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "benchmark_url": BENCH_URL, "benchmark_commit": BENCH_COMMIT, "human_loc_cap": HUMAN_LOC_CAP,
        "rule": "sha256(repo_id) even -> dev, odd -> test; per split: human-authored repos (loc > 0) in ascending LOC "
                "while cumulative LOC <= cap, plus the smallest LLM-generated repo",
        "selected": [{k: r[k] for k in ("id", "split", "authorship", "loc", "vulns", "traps", "repo_url", "commit_sha")}
                     for r in selected],
        "all_python_repos": {r["id"]: r["split"] for r in repos},
    }, indent=1) + "\n")
    for r in selected:
        print(f"{r['split']:5} {r['authorship']:15} {r['loc']:>5} LOC {r['vulns']:>3} vulns {r['traps']} traps  {r['id']}")
    print("written:", OUT)


if __name__ == "__main__":
    main()
