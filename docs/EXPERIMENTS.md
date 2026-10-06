# Experiments

Pre-registration log. Hypotheses and the scoring protocol are committed **before** the runs they govern, so the
git history shows what was decided before the numbers were known. Every number below comes from a file under
`eval/`; nothing is estimated.

## Setup in one paragraph
Three clean toy apps (`shop`, `bank`, `blog`) are attacked by a *Red* model that injects one vulnerability and
writes an exploit test. A referee (real code execution, no LLM) accepts it only if the exploit fails on the
clean app, passes on the patched one and the functional tests stay green. *Blue* is the local scanner
(`safia-sec scan`): it reads code, never executes it, and is scored against that ground truth.

## Measured so far (sources in brackets)
- Bandit baseline: 2 of 11 injected vulnerabilities found (both SQL injection), 0 false signals on the clean
  apps. [`eval/baselines/bandit.json`]
- Red via API, 30 samples each, judged in the Linux sandbox: GLM 5.3 Flash 13/30 accepted (10 distinct),
  DeepSeek V4.1 Flash 11/30 (3 distinct). Diversity is bounded by the app size; hence three apps and eleven
  templates. [`eval/judged/`]
- Local model probe on the `shop` app only (3 injected + clean, 3 seeds): gemma4:12b strict recall 6/9,
  qwen3.5:9b 5/9, qwen2.5-coder:7b 3/9; all three raise a false signal on the clean app in 3/3 runs.
  [`eval/results/20261001-blue-probe-comparison/`]

## Scoring protocol v3 (fixed before any Blue gym run)
- **Strict hit**: CWE family matches and the line is within +-5 of the injected lines.
- **Function hit** (primary): CWE family matches and the line is inside the function containing the injected
  lines. Reason: a removed check (IDOR, open redirect) has no injected line to point at; the probe showed the
  strict window misses a correct finding on the `def` line by one line. This rule was chosen after seeing the
  probe, and is therefore applied only to runs made after this commit; strict is always reported next to it.
- **CWE-only**: family matches anywhere in the file.
- **False signal**: any finding on a clean app. Extra findings on injected apps are reported, not punished
  (the ground truth lists only the injected bug).
- Stages reported separately: `raw` (model output), `grounded` (quote must exist in the file), `verified`
  (refutation step, plus Bandit candidates), `final`.
- 95% Wilson intervals; with n this small the result is a direction, not proof.

## Dev / test split
- **dev**: `shop` + `bank` (7 injected, 2 clean). Prompts and code may be tuned here.
- **test**: `blog` (4 injected, 1 clean) and one external benchmark. Run **once**, after the code freeze.
- Caveat: the generic checklist in `prompts/detect.md` names vulnerability classes that also occur in the gym.
  The test split therefore measures whether the model applies the checklist to unseen code, not whether it
  discovers unknown classes.

## Hypotheses (before the Blue gym runs)
- **H1** The model-based detector finds more injected vulnerabilities (function-level) than Bandit's 2/11.
- **H2** Evidence grounding lowers false signals on clean apps without lowering recall (it is deterministic).
- **H3** The verifier removes >= 30% of false signals at <= 10 points of recall. Low confidence: a small model
  may rubber-stamp its own mistakes (self-verification bias).
- **H4** gemma4:12b has higher recall than qwen3.5:9b; qwen3.5:9b is about twice as fast.
- **H5** Few-shot memory built from Blue's missed cases improves recall on held-out apps.
- **H6** Any gain from H5 persists on an external benchmark (transfer).
- **H7** (optional, only if time allows) a small LoRA triage model beats the same base model few-shot.

## Model choice rule (fixed on 2026-10-06, before the dev gym runs of the two local models)
The only evidence so far is the shop-only probe (9 injected runs per model: strict recall 6/9 for gemma4:12b against 5/9 for qwen3.5:9b, overlapping 95% intervals). The choice therefore waits for the dev gym with identical settings (T=0.7, seeds 1-3, ctx 8192, thinking off, verifier and Bandit on): 7 injected cases x 3 seeds = 21 runs and 2 clean apps x 3 seeds = 6 runs per model.
1. Function-level recall at the `final` stage over the 21 injected runs. A gap of 3 runs (14 points) or more decides.
2. Inside that gap: fewer clean runs that keep a false signal at the `final` stage, then fewer findings per clean run.
3. Still tied: faster end to end (model seconds per run, `meta.wall_s`).
The winner becomes the default model of `safia-sec`; the other is removed from the machine and stays in this log as the H4 comparison. Memory (+10.8 GB wired for gemma4:12b, +6.8 GB for qwen3.5:9b) is not a criterion; it goes to LIMITATIONS. With n this small the outcome is a direction, not proof.
