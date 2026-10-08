"""Apply the pre-registered step-4 freeze rule to two RealVuln-dev results from the same machine.

Rule (docs/EXPERIMENTS.md): the round with the higher final F3 is frozen; an exact tie (3 decimals) is not decided
here (exit code 3) because its tie-break needs a gym-dev run.
  python scripts/freeze_decide.py <r1 result dir> <r2 result dir> <out dir>
Prints r1 or r2 on the last line; exit 0 when decided.
"""
import json
import sys
from pathlib import Path


def totals(result_dir: Path) -> dict:
    data = json.loads((Path(result_dir) / "result.json").read_text())
    tp, fp, fn = (sum(r["scores"]["final"][k] for r in data["repos"]) for k in ("tp", "fp", "fn"))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f3 = 10 * p * r / (9 * p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 4), "recall": round(r, 4), "f3": round(f3, 4),
            "split": data["split"], "examples": data["settings"]["use_examples"]}


def decide(r1: dict, r2: dict) -> str:
    a, b = round(r1["f3"], 3), round(r2["f3"], 3)
    return "r2" if b > a else "r1" if b < a else "tie"


def main() -> int:
    r1_dir, r2_dir, out = (Path(a) for a in sys.argv[1:4])
    r1, r2 = totals(r1_dir), totals(r2_dir)
    assert r1["split"] == r2["split"] == "dev" and r1["examples"] and r2["examples"]
    winner = decide(r1, r2)
    out.mkdir(parents=True, exist_ok=True)
    (out / "decision.json").write_text(json.dumps({"rule": "higher RealVuln-dev final F3 (3 decimals); tie undecided",
                                                   "r1": r1, "r2": r2, "winner": winner}, indent=1) + "\n")
    print(f"r1 F3 {r1['f3']:.3f} (TP {r1['tp']} FP {r1['fp']} FN {r1['fn']}) | "
          f"r2 F3 {r2['f3']:.3f} (TP {r2['tp']} FP {r2['fp']} FN {r2['fn']})")
    print(winner)
    return 3 if winner == "tie" else 0


if __name__ == "__main__":
    raise SystemExit(main())
