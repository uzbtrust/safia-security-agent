# safia-sec: a local AI security reviewer

`safia-sec` reads a Python codebase with an open-weight model running on your own machine and reports
security vulnerabilities and risky decisions, each with file:line, the quoted code as evidence, a CWE, an
explanation and a suggested fix. It only reads: it never runs the scanned code, has no shell, and no code
leaves the machine.

Built as the Safia (AI Team) ML Engineer case study. The interesting part is not only the agent but how it was
measured: a self-built "Red vs Blue" gym with exploit-proven ground truth, an external benchmark split and
locked in advance, and pre-registered hypotheses, including the ones that failed.

## Results (held-out, run once after a code freeze)

RealVuln test half (4 labelled Python repositories, 80 vulnerabilities, 14 false-positive traps), scored with
the benchmark's own matcher rules (file + accepted CWE + line +-10):

| system | precision | recall | F3 (benchmark's metric) |
|---|---|---|---|
| **safia-sec (gemma4:12b, local)** | **0.78** | **0.39** | **0.41** |
| Bandit (classical scanner), MEDIUM+ / all | 0.56 / 0.52 | 0.12 / 0.15 | 0.14 / 0.16 |

- 2.6-3.3x Bandit's recall at higher precision; 1 of 14 traps flagged.
- On the newest repository (LLM-generated in 2026, unlikely to be in the model's training data) F3 0.56; on
  older public "vulnerable app" repos 0.27, so the score is not explained by memorization.
- Honest caveats: one seed (same configuration on another machine moved F3 by 0.03); a small test set chosen
  by a runtime budget; the development split scored much higher (F3 0.60), because the prompts were tuned on
  it. Full numbers, sources and the failures: [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md),
  [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

### What did not work, measured
- **Few-shot examples gave no measurable gain** on held-out code (RealVuln test F3 0.41 with vs 0.39
  without, inside the noise; gym test 6/12 with vs 11/12 without). The improvement that held up came from error
  analysis turned into instructions ("report every issue in a handler, including missing controls", a CWE menu)
  and from fixing pipeline bugs that silently dropped true findings.
- **Self-verification can destroy recall:** qwen3.5:9b's verifier rejected 9 of its own 10 true findings with
  wrong reasons, which decided the model choice (gemma4:12b: 18/21 vs 1/21 on the gym dev split).

## Quick start
```bash
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
ollama pull gemma4:12b                      # ~8 GB; about 11 GB of GPU / unified memory while running
safia-sec scan path/to/project --model gemma4:12b --out report/
```
`report/report.md` lists findings by severity with evidence, explanation, the verifier's reason and a fix;
`report.json` holds the same plus every pipeline stage and the dropped candidates. Exit code 1 means findings.
Useful flags: `--notes "facts about the project"` (e.g. how auth works), `--include-tests`, `--no-verify`,
`--no-bandit`, `--no-examples`.

## How it works
1. **Detect:** the local model reads numbered code with a CWE menu and short "flawed / guarded" examples;
   output is JSON constrained by a schema. Code is framed as data, never as instructions.
2. **Ground:** every finding must quote code that really exists in the file; otherwise it is dropped. The line
   number is snapped to the quote. This removes hallucinated findings.
3. **Corroborate:** Bandit runs independently; agreement is recorded, Bandit-only candidates are added.
4. **Verify:** a second call tries to refute each candidate (looks for a guard) and proposes a fix.

Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Security of the tool itself:
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## How it was evaluated
- **Gym (`gym_apps/`):** three small Flask apps (`shop`, `bank` = dev; `blog` = test). A Red model or template
  injects a vulnerability and writes an exploit test; a referee that executes code (not an LLM) accepts it only
  if the exploit fails on the clean app, works on the patched one, and functional tests still pass. Model-written
  code runs only in a sandbox with an empty network namespace.
- **External benchmark:** [RealVuln](https://github.com/kolega-ai/Real-Vuln-Benchmark) 3.0.0, Python repos,
  split by repo with a hash rule ([`targets/realvuln/split.json`](targets/realvuln/split.json)); the test half
  is locked in code.
- **Discipline:** hypotheses, metrics, the split, at most two improvement rounds and the freeze rule were
  committed before the runs they govern ([`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md)). Why each choice was
  made: [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Reproduce
```bash
pytest -q                                                      # 78 tests, mock model
safia-sec eval-gym --model gemma4:12b --apps shop bank --seeds 1 2 3
python scripts/realvuln_fetch.py --split dev && safia-sec eval-realvuln --model gemma4:12b --split dev
bash scripts/vast_final.sh       # freeze decision + once-only final runs on one NVIDIA machine (see the script)
python scripts/bandit_realvuln.py --final                      # Bandit baseline
```
LLM answers are cached by (model, options, prompt), so re-running an evaluation replays it.

## Cost
Model runs: a MacBook Air M4 (16 GB) and one rented node with 2x RTX 3090 for 46 minutes ($0.36). Red data
from API models cost cents (for example $0.022 on the day of the two 30-sample runs).

## Repository map
`src/safia_sec/` agent, gym, evaluation · `src/safia_sec/prompts/` prompts · `gym_apps/` target apps ·
`eval/results/` every run (`result.json` + `summary.md`) · `eval/baselines/` Bandit · `targets/realvuln/` split
· `scripts/` runners · `docs/` plan, experiments, decisions, limitations, architecture, threat model, hand-off logs.

## How this was built
Code, tests and analysis were written with Claude Code (Anthropic) in a cloud session without a GPU; every
model run happened on the local machine or the rented GPU node, and every number above comes from a committed
result file. Red data came from GLM 5.3 Flash and DeepSeek V4.1 Flash (via OpenRouter) and from templates;
five extra gym variants were written by the coding assistant and are marked as such.
