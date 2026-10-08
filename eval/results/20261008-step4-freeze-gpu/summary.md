# Step-4 freeze and final evaluation on a rented GPU (2026-10-08)

Machine: Vast.ai instance 54842885, 2x NVIDIA GeForce RTX 3090 (24 GB each, driver 580.159.03), Ollama 0.40.1 (the Mac runs used 0.35.0 on Metal). `gemma4:12b` digest 6114515d63c1, the same as on the Mac. Code: commit 0a3580c (round 2 included), tag `step4-freeze`. Rented 17:25, destroyed 18:11 (Tashkent time, 46 min) at $0.417/h with a 60 GB disk; credit used $0.357 of the $3.15 cap.
Run: `scripts/vast_final.sh`, unchanged. The first attempt stopped in setup (`vast_run_attempt1.log`): on that host github.com resolved to an unreachable address and the Ollama installer download failed. Infrastructure fixes on the instance only: github.com pinned in /etc/hosts to a verified GitHub address and `git config http.version HTTP/1.1`; the script then ran again from the start (no setting or prompt changed). `vast_run.log` is the cleaned log of that second run (download progress bars removed).

## Freeze decision (RealVuln dev, same machine, seed 1)
| round | TP | FP | FN | precision | recall | F3 |
|---|---|---|---|---|---|---|
| r1 (round 2 reverted) | 37 | 9 | 54 | 0.804 | 0.407 | 0.428 |
| r2 | 53 | 11 | 38 | 0.828 | 0.582 | 0.600 |
Rule (docs/EXPERIMENTS.md): the higher final F3 at 3 decimals is frozen, so **r2** (`decision.json`, re-run on the Mac with `scripts/freeze_decide.py`). Nothing was reverted.
Reproducibility: the Mac run of r1 had F3 0.459 (TP 40, FP 12, FN 51). On the GPU four of six repos gave identical TP/FP/FN; `realvuln-intentionally-vulnerable-python-application` changed from 5/0/2 to 2/1/5 and the Django repo kept 15 TP but fell from 10 to 6 FP. A different backend and Ollama version change some outputs even with the same seed.

## Final evaluation (once, frozen r2; the arms differ only by `--no-examples`)
| test | arm | headline |
|---|---|---|
| gym blog (12 injected runs, 3 clean runs) | examples | function recall 6/12, strict 9/12, located 6/12; clean runs with a false signal 3/3 (1.33 findings per clean run) |
| | no examples | function recall 11/12, strict 11/12, located 11/12; clean runs with a false signal 3/3 (2.00 per run) |
| RealVuln test (4 repos, 80 labels, 14 traps) | examples | TP 31, FP 9, FN 49, precision 0.78, recall 0.39, F3 0.41; traps hit 1 |
| | no examples | TP 30, FP 13, FN 50, precision 0.70, recall 0.38, F3 0.39; traps hit 2 |
RealVuln test by stratum, examples / no examples: human-authored F3 0.27 / 0.32 (precision 0.73 / 0.81, recall 0.26 / 0.30); LLM-generated F3 0.56 / 0.47 (precision 0.80 / 0.63, recall 0.54 / 0.46). 0 errors in every final run.

## Reading (direction, not proof)
- Dev to test with the same frozen prompts: RealVuln F3 0.600 on dev, 0.41 on test; gym function recall 21/21 on dev (round 1) and 6/12 on blog. The prompts were written from dev failures, so the dev numbers are optimistic and the test numbers are the honest ones.
- Few-shot examples: on blog they hurt (function 6/12 against 11/12; CWE-601 has 3/3 strict hits but 0/3 inside the function; CWE-330 0/3 against 2/3). On RealVuln test they add 0.02 F3, mostly precision with equal recall, and the effect splits by stratum. With 80 labels this is inside the noise.
- The grounding and verifier stages lowered RealVuln test F3 again (examples arm: raw 0.45, final 0.41).
