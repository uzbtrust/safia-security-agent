#!/usr/bin/env python3
"""T0.3 smoke test for the local Ollama server. Standard library only; runs no model-written code.

Checks on the real model: cold load, prefill/decode speed, schema-constrained output through the
native `format` field (same request shape as scripts/red_generate.py) and through the
OpenAI-compatible `response_format`, what happens to prompts longer than the context window, and
determinism. Writes eval/results/<date>-smoke-ollama-<model>/{result.json,summary.md}.

  .venv/bin/python configs/local/smoke_test.py --model qwen2.5-coder:7b
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import red_generate  # noqa: E402  (imported for SCHEMA and PROMPT only)
from safia_sec.gym.injections import APP_DIR, TEMPLATES  # noqa: E402

NUM_CTX = 8192
V1_SCHEMA = {"type": "object",
             "properties": {"label": {"type": "string", "enum": ["alpha", "beta"]},
                            "reason": {"type": "string"}},
             "required": ["label", "reason"], "additionalProperties": False}


def post(host: str, path: str, body: dict, timeout: int = 900) -> tuple[dict, float]:
    req = urllib.request.Request(host + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp), time.time() - t0


def get(host: str, path: str) -> dict:
    with urllib.request.urlopen(host + path, timeout=30) as resp:
        return json.load(resp)


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as exc:  # tool missing or timeout
        return f"error: {exc!r}"


def chat(host: str, model: str, content: str, *, fmt: dict | None = None, **options) -> tuple[dict, float]:
    body = {"model": model, "stream": False, "messages": [{"role": "user", "content": content}],
            "options": {"num_ctx": NUM_CTX, **options}}
    if fmt is not None:
        body["format"] = fmt
    return post(host, "/api/chat", body)


def speed(d: dict) -> dict:
    pe, pd = d.get("prompt_eval_count", 0), d.get("prompt_eval_duration", 0)
    ge, gd = d.get("eval_count", 0), d.get("eval_duration", 0)
    return {"prompt_tokens": pe, "prefill_tok_s": round(pe / (pd / 1e9), 1) if pd else None,
            "gen_tokens": ge, "decode_tok_s": round(ge / (gd / 1e9), 1) if gd else None}


def check_red(host: str, model: str, n: int) -> list[dict]:
    t = TEMPLATES["CWE-89"]
    source = (APP_DIR / "app.py").read_text()
    prompt = red_generate.PROMPT.format(cwe=t.cwe, title=t.title, hint=t.hint, marker=t.marker, source=source)
    rows = []
    for i in range(n):
        d, wall = chat(host, model, prompt, fmt=red_generate.SCHEMA, temperature=0.8)
        content = d["message"]["content"]
        row = {"i": i, "wall_s": round(wall, 1), "done_reason": d.get("done_reason"), **speed(d)}
        try:
            data = json.loads(content)
            row["valid_json"] = True
            row["schema_ok"] = all(isinstance(data.get(k), str) for k in ("old", "new", "exploit_test"))
            if row["schema_ok"]:
                row["old_found_once"] = bool(data["old"].strip()) and source.count(data["old"]) == 1
                row["marker_in_exploit"] = t.marker in data["exploit_test"]
                row.update(old=data["old"], new=data["new"], exploit_test=data["exploit_test"])
        except json.JSONDecodeError as exc:
            row.update(valid_json=False, schema_ok=False, error=str(exc)[:120], raw_head=content[:200])
        rows.append(row)
        print("red", i, {k: row.get(k) for k in ("valid_json", "schema_ok", "old_found_once", "decode_tok_s")}, flush=True)
    return rows


def check_v1(host: str, model: str, n: int = 3) -> list[dict]:
    prompt = ("Is this Python line vulnerable to SQL injection? Reply as JSON.\n"
              "cursor.execute(f\"SELECT * FROM t WHERE id = {uid}\")")
    rows = []
    for i in range(n):
        body = {"model": model, "temperature": 0, "seed": i, "max_tokens": 120,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "verdict", "strict": True, "schema": V1_SCHEMA}}}
        d, wall = post(host, "/v1/chat/completions", body)
        content = d["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
            ok = set(data) == {"label", "reason"} and data["label"] in ("alpha", "beta")
        except (json.JSONDecodeError, TypeError):
            ok = False
        rows.append({"i": i, "wall_s": round(wall, 1), "conforms": ok, "usage": d.get("usage"), "head": content[:140]})
        print("v1", i, "conforms" if ok else "VIOLATES", flush=True)
    return rows


def build_long(n_lines: int, a: str, b: str) -> str:
    lines = [f"Line {k}: the quick brown fox jumps over the lazy dog {(k * 7919) % 10007}." for k in range(1, n_lines + 1)]
    half = n_lines // 2
    return (f"Secret A is {a}.\n" + "\n".join(lines[:half]) + f"\nSecret B is {b}.\n" + "\n".join(lines[half:])
            + "\n\nQuestion: what are secret A and secret B? Answer with both codes only.")


def check_long(host: str, model: str) -> dict:
    cal, _ = chat(host, model, build_long(100, "X1", "X2"), temperature=0, num_predict=1)
    per_line = cal["prompt_eval_count"] / 100
    n_lines = int(NUM_CTX * 1.3 / per_line)
    a, b = "ZEBRA-4417", "OTTER-9082"
    d, wall = chat(host, model, build_long(n_lines, a, b), temperature=0, num_predict=40)
    ans = d["message"]["content"]
    a1, b1 = "KIWI-2290", "HERON-6615"  # different head so the prefix cache cannot hide the token count
    v1, wall1 = post(host, "/v1/chat/completions", {"model": model, "temperature": 0, "max_tokens": 40,
                     "messages": [{"role": "user", "content": build_long(n_lines, a1, b1)}]})
    ans1 = v1["choices"][0]["message"]["content"]
    return {"calibration": speed(cal), "approx_prompt_tokens": round(per_line * n_lines), "num_ctx": NUM_CTX,
            "native": {**speed(d), "wall_s": round(wall, 1), "found_A": a in ans, "found_B": b in ans, "answer": ans[:120]},
            "v1": {"usage": v1.get("usage"), "wall_s": round(wall1, 1), "found_A": a1 in ans1, "found_B": b1 in ans1,
                   "answer": ans1[:120]}}


def check_determinism(host: str, model: str) -> dict:
    q = "List three common causes of SQL injection, one sentence each."

    def run(seed: int, temp: float) -> str:
        return chat(host, model, q, temperature=temp, seed=seed, num_predict=80)[0]["message"]["content"]

    t0 = [run(s, 0) for s in (1, 2, 3)]
    t8 = [run(s, 0.8) for s in (1, 2, 3)]
    return {"t0_identical_across_seeds": len(set(t0)) == 1, "t08_distinct_outputs_of_3_seeds": len(set(t8)),
            "t08_seed1_repeat_identical": run(1, 0.8) == t8[0]}


def yn(x) -> str:
    return "yes" if x else "no"


def write_outputs(res: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(res, indent=2))
    c, env, m = res["checks"], res["env"], res["model"]
    red, v1, lg, det, rs = c["red_native_format"], c["v1_response_format"], c["long_prompt"], c["determinism"], c["resident"]
    dec = [r["decode_tok_s"] for r in red if r.get("decode_tok_s")]
    dq, nat, via = m["details"] or {}, lg["native"], lg["v1"]
    lines = [
        f"# Smoke test: {m['tag']} on Ollama {env['ollama']}", "",
        f"- git `{env['git_sha']}`, num_ctx {NUM_CTX}, digest `{m['digest'][:12]}`, "
        f"{dq.get('parameter_size')} {dq.get('quantization_level')}, file {m['size_bytes'] / 1e9:.2f} GB",
        f"- power: {env['power']}; at start: {env['memory_pressure']}; swap {env['swap']}; free disk {env['free_disk']}", "",
        "| Check | Result |", "|---|---|",
        f"| Cold load | {c['cold_load']['load_s']} s |",
        f"| Decode speed (red samples) | {statistics.median(dec) if dec else '-'} tok/s median, "
        f"{min(dec) if dec else '-'}-{max(dec) if dec else '-'} |",
        f"| Prefill speed | {lg['calibration']['prefill_tok_s']} tok/s at {lg['calibration']['prompt_tokens']} tokens; "
        f"{nat['prefill_tok_s']} tok/s at {nat['prompt_tokens']} tokens |",
        "| Resident | " + "; ".join(f"{r['size_gb']} GB, {r['vram_gb']} GB on GPU, ctx {r['context_length']}" for r in rs) + " |",
        f"| Native `format` (red schema), n={len(red)} | valid JSON {sum(bool(r.get('valid_json')) for r in red)}, "
        f"schema ok {sum(bool(r.get('schema_ok')) for r in red)}, `old` found once {sum(bool(r.get('old_found_once')) for r in red)}, "
        f"marker present {sum(bool(r.get('marker_in_exploit')) for r in red)} |",
        f"| `/v1` `response_format` json_schema, n={len(v1)} | conforms {sum(r['conforms'] for r in v1)}; "
        f"usage present: {yn(all(r['usage'] for r in v1))} |",
        f"| Prompt longer than context (~{lg['approx_prompt_tokens']} tokens, ctx {NUM_CTX}) | native prompt_eval_count "
        f"{nat['prompt_tokens']}, found A/B: {yn(nat['found_A'])}/{yn(nat['found_B'])}; `/v1` usage "
        f"{via['usage']}, found A/B: {yn(via['found_A'])}/{yn(via['found_B'])} |",
        f"| Determinism T=0 | identical across seeds 1-3: {yn(det['t0_identical_across_seeds'])} |",
        f"| Determinism T=0.8 | {det['t08_distinct_outputs_of_3_seeds']} distinct outputs of 3 seeds; "
        f"seed 1 repeated identical: {yn(det['t08_seed1_repeat_identical'])} |", "",
        "Prefill is only meaningful for calls with a cold prompt prefix; repeated red prompts reuse the cache.",
        "Red samples are stored in result.json for inspection. They were never executed.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--n-red", type=int, default=3)
    a = ap.parse_args()
    host, model = a.host, a.model

    tags = {x["name"]: x for x in get(host, "/api/tags")["models"]}
    if model not in tags:
        sys.exit(f"model not pulled: {model} (present: {sorted(tags)})")
    show, _ = post(host, "/api/show", {"model": model})
    ctx_train = next((v for k, v in show.get("model_info", {}).items() if k.endswith(".context_length")), None)
    free = next((ln.split(":", 1)[1].split("(")[0].strip() for ln in sh(["diskutil", "info", "/"]).splitlines()
                 if "Container Free Space" in ln), "?")
    res = {"env": {"git_sha": sh(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"]),
                   "ollama": get(host, "/api/version")["version"], "num_ctx": NUM_CTX,
                   "power": (sh(["pmset", "-g", "batt"]).splitlines() or ["?"])[0],
                   "memory_pressure": (sh(["memory_pressure"]).splitlines() or ["?"])[-1],
                   "swap": sh(["sysctl", "-n", "vm.swapusage"]), "free_disk": free},
           "model": {"tag": model, "digest": tags[model]["digest"], "size_bytes": tags[model]["size"],
                     "details": show.get("details"), "context_length_trained": ctx_train},
           "checks": {}}
    c = res["checks"]
    d, wall = chat(host, model, "Reply with the single word OK.", temperature=0, num_predict=8)
    c["cold_load"] = {"load_s": round(d.get("load_duration", 0) / 1e9, 2), "wall_s": round(wall, 2)}
    print("cold load", c["cold_load"], flush=True)
    c["red_native_format"] = check_red(host, model, a.n_red)
    c["v1_response_format"] = check_v1(host, model)
    c["long_prompt"] = check_long(host, model)
    print("long prompt done", flush=True)
    c["determinism"] = check_determinism(host, model)
    c["resident"] = [{"name": r["name"], "size_gb": round(r["size"] / 1e9, 2), "vram_gb": round(r["size_vram"] / 1e9, 2),
                      "context_length": r.get("context_length")} for r in get(host, "/api/ps")["models"]]
    write_outputs(res, ROOT / "eval" / "results" / f"{date.today():%Y%m%d}-smoke-ollama-{model.replace(':', '_').replace('/', '_')}")


if __name__ == "__main__":
    main()
