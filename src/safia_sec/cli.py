"""safia-sec: a local, read-only AI security reviewer.

  safia-sec scan <path> --model gemma4:12b --out report/
  safia-sec eval-gym --model gemma4:12b --seeds 1 2 3 --out eval/results/<run>/
  safia-sec eval-realvuln --model gemma4:12b --split dev
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .blue import evaluate, realvuln, report
from .blue.llm import CachedClient, OllamaClient
from .blue.scanner import Scanner


def default_client(args, seed: int):
    think = {"off": False, "on": True, "auto": None}[args.think]
    client = OllamaClient(args.model, host=args.host, num_ctx=args.num_ctx, temperature=args.temperature,
                          seed=seed, think=think)
    return client if args.no_cache else CachedClient(client, Path(args.cache))


def add_model_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--model", required=True)
    p.add_argument("--host", default="http://127.0.0.1:11434")
    p.add_argument("--num-ctx", type=int, default=8192)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--think", choices=["off", "on", "auto"], default="off")
    p.add_argument("--no-verify", action="store_true", help="skip the refutation step")
    p.add_argument("--no-bandit", action="store_true", help="do not use Bandit")
    p.add_argument("--no-examples", action="store_true",
                    help="do not add the few-shot examples to the prompts (for before/after comparison)")
    p.add_argument("--include-tests", action="store_true", help="also scan test files and migrations")
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--cache", default=".cache/llm")


def main(argv: list[str] | None = None, client_factory=None) -> int:
    ap = argparse.ArgumentParser(prog="safia-sec", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="review a Python file or folder (read-only)")
    sc.add_argument("path")
    sc.add_argument("--out", help="directory for report.json and report.md")
    sc.add_argument("--seed", type=int, default=1)
    sc.add_argument("--notes", default="", help="security-relevant facts about the project (auth model, conventions)")
    add_model_options(sc)
    ev = sub.add_parser("eval-gym", help="measure Blue on the gym apps")
    ev.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ev.add_argument("--apps", nargs="+", choices=["shop", "bank", "blog"])
    ev.add_argument("--out")
    add_model_options(ev)
    rv = sub.add_parser("eval-realvuln", help="measure Blue on the pre-registered RealVuln split")
    rv.add_argument("--split", choices=["dev", "test"], required=True)
    rv.add_argument("--final", action="store_true", help="required for the test half (run once, after the freeze)")
    rv.add_argument("--data", default=".cache/realvuln", help="output of scripts/realvuln_fetch.py")
    rv.add_argument("--seed", type=int, default=1)
    rv.add_argument("--out")
    add_model_options(rv)
    args = ap.parse_args(argv)
    factory = client_factory or default_client

    if args.cmd == "eval-realvuln":
        settings = realvuln.Settings(verify=not args.no_verify, use_bandit=not args.no_bandit,
                                     use_examples=not args.no_examples, include_tests=args.include_tests)
        try:
            result = realvuln.run(lambda seed: factory(args, seed), args.split, Path(args.data), args.seed,
                                  settings, final=args.final, progress=lambda s: print(s, flush=True))
        except realvuln.SplitLocked as exc:
            print(exc, file=sys.stderr)
            return 2
        tag = "" if settings.use_examples else "-noex"
        out = Path(args.out or f"eval/results/{date.today():%Y%m%d}-realvuln-{args.split}-"
                               f"{args.model.replace(':', '_').replace('/', '_')}{tag}")
        realvuln.write(result, args.model, out)
        print(realvuln.summarize(result, args.model))
        print("written:", out)
        return 0

    if args.cmd == "scan":
        target = Path(args.path)
        if not target.exists():
            print(f"no such path: {target}", file=sys.stderr)
            return 2
        scanner = Scanner(factory(args, args.seed), notes=args.notes, verify=not args.no_verify,
                          use_bandit=not args.no_bandit, use_examples=not args.no_examples,
                          include_tests=args.include_tests)
        result = scanner.scan(target)
        md = report.to_markdown(result, str(target))
        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / "report.json").write_text(json.dumps(report.to_dict(result), indent=1))
            (out / "report.md").write_text(md)
        print(md)
        return 1 if result.findings else 0

    tag = "-noex" if args.no_examples else ""
    out = Path(args.out or f"eval/results/{date.today():%Y%m%d}-blue-gym-{args.model.replace(':', '_').replace('/', '_')}{tag}")
    result = evaluate.run_eval(lambda seed: factory(args, seed), args.seeds, args.apps,
                               verify=not args.no_verify, use_bandit=not args.no_bandit,
                               use_examples=not args.no_examples, progress=lambda s: print(s, flush=True))
    evaluate.write(result, args.model, out)
    print(evaluate.summarize(result, args.model))
    print("written:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
