"""Fetch the LoRA training repos (pinned) and write the training set (pre-registered; see src/safia_sec/lora/data.py).

  python scripts/lora_build_data.py --dest .cache/lora            # -> .cache/lora/train.jsonl + summary.json
Read-only: repos are checked out, never installed or executed.
"""
import argparse
import json
from pathlib import Path

from safia_sec.blue.realvuln import _git
from safia_sec.lora.data import TRAIN_FILE, build


def fetch(dest: Path) -> tuple[Path, Path]:
    spec = json.loads(TRAIN_FILE.read_text())
    bench, repos = dest / "benchmark", dest / "repos"
    if not (bench / ".git").exists():
        bench.mkdir(parents=True, exist_ok=True)
        _git("init", "-q", cwd=bench)
        _git("remote", "add", "origin", "https://github.com/kolega-ai/Real-Vuln-Benchmark", cwd=bench)
        _git("config", "core.sparseCheckout", "true", cwd=bench)
    patterns = ["/benchmark-manifest.json"] + [f"/ground-truth/{r}/ground-truth.json" for r in spec["train_repos"]]
    (bench / ".git" / "info").mkdir(parents=True, exist_ok=True)
    (bench / ".git" / "info" / "sparse-checkout").write_text("\n".join(patterns) + "\n")
    _git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", spec["benchmark_commit"], cwd=bench)
    _git("-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD", cwd=bench)
    assert _git("rev-parse", "HEAD", cwd=bench) == spec["benchmark_commit"]
    manifest = json.loads((bench / "benchmark-manifest.json").read_text())["repos"]
    for rid in spec["train_repos"]:
        repo, want = repos / rid, manifest[rid]["commit_sha"]
        if repo.exists() and _git("rev-parse", "HEAD", cwd=repo) == want:
            continue
        repo.mkdir(parents=True, exist_ok=True)
        if not (repo / ".git").exists():
            _git("init", "-q", cwd=repo)
            _git("remote", "add", "origin", manifest[rid]["repo_url"], cwd=repo)
        _git("fetch", "-q", "--depth", "1", "origin", want, cwd=repo)
        _git("-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD", cwd=repo)
        assert _git("rev-parse", "HEAD", cwd=repo) == want
    return bench, repos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=".cache/lora")
    args = ap.parse_args()
    dest = Path(args.dest)
    bench, repos = fetch(dest)
    s = build(bench, repos, dest / "train.jsonl")
    print(f"{s['examples']} examples ({s['positive']} positive, {s['trap']} trap, {s['negative']} negative), "
          f"{s['findings']} target findings, ~{s['chars'] / 3.9 / 1e6:.2f}M tokens, sha256 {s['sha256'][:12]}")


if __name__ == "__main__":
    main()
