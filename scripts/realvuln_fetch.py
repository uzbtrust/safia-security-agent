"""Download the pre-registered RealVuln split at its pinned commits (ground truth + target repos).

Read-only: repos are checked out, never installed or executed. The test half needs --final (run once, after the
freeze; see docs/EXPERIMENTS.md).
  python scripts/realvuln_fetch.py --split dev
"""
import argparse
from pathlib import Path

from safia_sec.blue.realvuln import fetch


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--dest", default=".cache/realvuln")
    ap.add_argument("--final", action="store_true", help="required for the test half")
    args = ap.parse_args()
    fetch(args.split, Path(args.dest), final=args.final)


if __name__ == "__main__":
    main()
