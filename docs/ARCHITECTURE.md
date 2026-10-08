# Architecture

```
                      safia-sec scan <path>                      (the product: Blue)
                               |
     files: *.py below the root, no symlinks out, no tests/migrations, <= 200 KB, chunks of <= 220 lines
                               |
  1 detect   local model (Ollama) reads numbered code + CWE menu + few-shot pairs -> JSON (schema-bound)
  2 ground   every finding must quote code that exists in the file; the line snaps to the quote
  3 bandit   independent static scan: corroborates findings, adds its own MEDIUM+ candidates
  4 verify   a second call tries to refute each candidate and proposes a fix
                               |
                report.json + report.md (escaped), exit code 1 if findings
```

## Components (`src/safia_sec/`)
| module | role |
|---|---|
| `cli.py` | `scan`, `eval-gym`, `eval-realvuln` |
| `blue/scanner.py` | the four-stage pipeline; keeps every stage's output so each stage can be measured |
| `blue/llm.py` | Ollama client (JSON-schema output, thinking off, explicit seed, context-truncation check), disk cache, fake client for tests |
| `blue/fewshot.py` | contrast pairs (flawed / guarded) for the detect and verify prompts |
| `prompts/detect.md`, `prompts/verify.md` | prompt templates; code is framed as data, never as instructions |
| `blue/report.py` | JSON and Markdown reports; quoted code gets a fence longer than any backtick run inside it |
| `blue/score.py`, `blue/evaluate.py` | gym scoring (strict, function, CWE-only, located; Wilson intervals) |
| `blue/realvuln.py` | RealVuln fetch (pinned SHAs), scan, scoring with the benchmark's matcher rules; test half locked |
| `gym/referee.py` | executes Red's exploit tests in a sandbox and accepts a bug only if it is proven |
| `gym/injections.py`, `gym/authored/` | golden vulnerability templates and hand-written variants |

## The gym (how ground truth is made)
```
clean app --Red: patch + exploit test--> referee (no LLM) --accepted--> labelled case for Blue
             (API model or template)      1. functional tests pass on the clean app
                                          2. exploit FAILS on the clean app
                                          3. functional tests still pass on the patched app
                                          4. exploit PASSES on the patched app
```
Apps: `gym_apps/shop`, `bank` (dev) and `blog` (test). The referee runs in a separate process with a scrubbed
environment, temp directories, CPU/memory/file limits, a timeout and an empty network namespace; untrusted
code is refused when the namespace is unavailable.

## Evaluation
- Gym: `safia-sec eval-gym` scores every stage against the injected bug (`eval/results/*-blue-gym-*`).
- External: RealVuln (`targets/realvuln/split.json`, mechanical dev/test split), `safia-sec eval-realvuln`.
- Baselines: Bandit on the gym (`eval/baselines/bandit.json`) and on RealVuln (`eval/baselines/realvuln_bandit.*`).
- Protocol and results: `docs/EXPERIMENTS.md`. The final GPU session: `scripts/vast_final.sh`.

## Two working environments
Code, tests and analysis were written in a cloud session without a GPU (mock model in tests); every model run
happened locally (MacBook Air M4) or on one rented GPU node. The hand-off logs are in `docs/handoff/`.
