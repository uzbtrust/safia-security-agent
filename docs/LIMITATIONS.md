# Limitations

What the results do and do not show, and where the agent falls short. Numbers come from `eval/`; see
`EXPERIMENTS.md` for sources.

## Measurement
- **Small samples, one seed on RealVuln.** The external test is 4 repositories with 80 labelled vulnerabilities,
  run once with seed 1. The same configuration gave F3 0.459 on the Mac and 0.428 on the GPU node, so
  differences of about 0.03 F3 are noise. The gym uses 3 seeds but only 4-7 cases per split.
- **Small, easy-to-run repositories.** The RealVuln subset was chosen by a runtime budget (the smallest repos
  of each half, by a mechanical rule). It says nothing about large codebases.
- **Dev numbers are optimistic.** Round 2 was written from the RealVuln dev misses (dev F3 0.600); the frozen
  configuration scores 0.41 on the test half. Quote the test numbers.
- **Gym ground truth covers only the injected bug.** A "false signal" on a clean gym app can be a real issue
  that the gym declares out of scope (the toy apps have no rate limiting by design; the frozen prompt flags it
  on the blog reset endpoints in 3/3 clean runs).
- **Metric artefact.** The gym's function-level hit uses the Python AST, where a function starts at `def`, not
  at its decorator. Three blog runs pointed at `@app.get("/go")` and count as strict hits but function misses.
- **Benchmark judgement.** RealVuln labels, acceptable CWE lists and the +-10 line tolerance are the benchmark
  authors' choices. Findings in non-Python files (templates, configs) are out of the scanner's scope.
- **Hardware change.** The freeze and the final runs moved from the Mac (Ollama/Metal) to 2x RTX 3090 (CUDA).
  Round 1 was re-run there so that the freeze compared like with like; Mac and GPU numbers are not
  interchangeable.

## The scanner
- **Python only, one file at a time.** No cross-file data flow; the verifier sees about 120 lines around a
  finding. Middleware, settings or decorators defined elsewhere are invisible, which causes both misses and
  false alarms for "missing control" issues (authentication, CSRF, rate limiting).
- **Under-reporting in dense code.** `dsvw` (27 labels in one 93-line file): 8 findings, recall 0.19.
- **The few-shot block did not help** on the held-out sets (blog 6/12 vs 11/12 without it; RealVuln test F3
  0.41 vs 0.39). It stays in the frozen configuration because the freeze rule selected the round that
  contains it; `--no-examples` turns it off.
- **Precision-first filters vs a recall-weighted metric.** Grounding and the verifier protect against
  hallucinated and weak findings, but on RealVuln test they lowered F3 from 0.45 (raw) to 0.41 (final).
- **The verifier fails open:** if it errors, the finding is kept and marked unverified.
- **Model size and speed.** gemma4:12b needs about 11 GB of accelerator memory. On a 16 GB MacBook Air
  RealVuln dev (1,759 LOC) took 73 minutes (98 calls, 44.8 s per call); a 24 GB GPU is far faster.
- **No SARIF output yet**; reports are JSON and Markdown.

## The gym (training and evaluation harness)
- Three small synthetic Flask apps with one injected bug per case; synthetic bugs are cleaner than real ones.
- Red diversity is low: API models had 13/30 (GLM) and 11/30 (DeepSeek) samples accepted, many of them
  near-duplicates, because each app has few injection points.
- The referee proves that a bug is exploitable, not that it is realistic.
- The referee sandbox is a Linux network namespace plus resource limits and AST checks, not a VM. On macOS it
  refuses to run model-written code.

## Not done
LoRA fine-tuning (H7), cross-file analysis, other languages, several seeds on RealVuln, SARIF.
