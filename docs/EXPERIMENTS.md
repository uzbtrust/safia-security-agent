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
- **Dev gym (shop + bank, 7 injected x 3 seeds + 2 clean x 3 seeds, verifier + Bandit on), 2026-10-07:**
  function recall at `final`: gemma4:12b **18/21**, qwen3.5:9b 1/21. Clean-app false signal: gemma4:12b 2/6,
  qwen3.5:9b 1/6. Model choice rule (pre-registered 2026-10-06) picked **gemma4:12b** on step 1 (recall gap
  of 17/21 runs, far past the 3-run threshold). [`eval/results/20261007-blue-gym-gemma4_12b/`,
  `20261007-blue-gym-qwen3.5_9b/`]

### Hypotheses: result against the dev gym
- **H1** (beats Bandit 2/11): confirmed for gemma4:12b (6 of 7 injected cases hit 3/3; Bandit only 2/7 of
  those same cases). Not confirmed for qwen3.5:9b at the `final` stage (1/21) — only at `raw` (11/21).
- **H2** (grounding lowers false signals, not recall): confirmed for gemma4:12b (clean false signal 3/6 ->
  2/6, function recall unchanged 18/21). Not confirmed for qwen3.5:9b (false signal unchanged 6/6, function
  recall fell 11/21 -> 9/21 — grounding dropped two correct hits, so the "deterministic, recall-neutral"
  assumption in H2 does not hold for every model).
- **H3** (verifier removes >=30% of false signals at <=10 points of recall): confirmed for gemma4:12b (false
  signal 3/12 extras+clean removed, 0/18 true hits rejected). The low-confidence self-verification-bias
  worry is **confirmed as a real failure mode for qwen3.5:9b**: its verifier rejected 9/10 true hits with
  factually wrong reasoning (called a SQL injection "parameterized", claimed `os.path.join` prevents
  traversal), collapsing function recall from 9/21 to 1/21 — a loss, not a >=30%-signal/<=10-point trade.
- **H4** (gemma4:12b higher recall, qwen3.5:9b ~2x faster): recall confirmed (18/21 vs 1/21, even more lopsided
  than expected). Speed not confirmed: qwen3.5:9b was only 1.4x faster per run (46.1s vs 64.7s), not ~2x —
  the probe's 2x decode-speed gap did not carry over to end-to-end run time.
- One case neither model found: **bank/CWE-840** (negative transfer amount) — 0/3 for both, even though
  `prompts/detect.md` names negative/oversized amounts explicitly. This is the clearest target for step 4.

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

## Step 4 protocol (pre-registered 2026-10-07, before any run of the round-1 changes)
**At most two improvement rounds, then a freeze.** Each round may only use dev evidence.
- **Round 1 (this commit).** Evidence used: the gemma4:12b dev gym run of 2026-10-07 (`result.json`), the
  class/CWE distribution of the RealVuln *dev* repos, and RealVuln's public scoring config
  (`config/cwe-families.json`, i.e. the rules, not the answers). From the RealVuln *test* half only repo-level
  counts (LOC, number of labels) were printed while designing the split; no test repo was cloned or scanned
  and no test label was read. Changes: a CWE menu in the detect prompt (the dev gym showed gemma4:12b
  pointing at the right function of bank/CWE-840 but labelling it CWE-606/603); a rule not to report code
  that is already guarded; a revised few-shot block (`blue/fewshot.py`, original snippets, never gym code)
  that is also given to the verifier; test files and migrations skipped by default (no RealVuln dev label
  sits in them; LOCAL's smoke scan flagged a test file); finding cap per chunk 8 -> 12 and generation cap
  1500 -> 2048 tokens (a RealVuln dev file has 14 labels in 161 lines; the largest dev chunk plus the prompt
  is about 16k characters, so prompt + answer still fit the 8192-token context). The gym's project notes now
  also name the toy apps' deliberate omissions that the new menu would otherwise invite (security headers,
  plaintext demo passwords in seed data): the gym's ground truth covers only the injected bug. Because the
  prompts changed, round-1 gym numbers are compared with the 2026-10-07 run as context, not as an ablation.
- **Round 2** (once): its content must come from round-1 failures on the gym dev split and RealVuln dev only.
- **Freeze rule:** the frozen configuration is whichever of round 1 / round 2 has the higher RealVuln-dev F3
  (tie: higher gym-dev function recall). No change after the freeze.
- **Final, once, after the freeze:** gym test (`blog`) and RealVuln test, each with the frozen configuration
  and with the same configuration plus `--no-examples`. That pair is the H5/H6 comparison: it isolates the
  few-shot block; the CWE menu, the guard rule and the file filter are product changes kept in both arms.

### RealVuln (external benchmark)
- RealVuln 3.0.0 ground truth, benchmark commit `7a710251f55c` (Apache-2.0), Python repos only (the scanner
  reads Python). Each repo is pinned to the commit SHA in RealVuln's manifest.
- **Split by repo, mechanical:** sha256(repo_id) even -> dev, odd -> test (34 dev / 32 test Python repos).
- **Selection (runtime budget), same rule for both halves:** human-authored repos with a known size in
  ascending LOC while the cumulative LOC is <= 500, plus the single smallest LLM-generated repo.
  Result (`targets/realvuln/split.json`, written by `scripts/realvuln_split.py`): dev = 5 human-authored +
  1 LLM-generated repo (91 vulnerabilities, 16 false-positive traps); test = 3 + 1 (80 and 14).
- **Scoring = RealVuln's matcher semantics** (re-implemented, their code is not executed): a finding is a TP
  if file matches, its CWE is in the entry's `acceptable_cwes` and its line is within the entry's range
  +-10; every finding that matches no vulnerable entry is an FP (including a hit on a trap); unmatched
  vulnerable entries are FN; `non_scoring` entries are ignored. Primary metric: F3 = 10PR / (9P + R), the
  benchmark's own; precision and recall are always shown separately. Secondary: recall over entries in
  `.py` files only (the scanner's scope). Reported per stratum: human-authored (older community apps, likely
  seen in pre-training) and LLM-generated (2026, unlikely to be memorized).
- Run settings: same as the gym (T=0.7, ctx 8192, thinking off, verifier and Bandit on), seed 1 only (each
  repo has many labels), no project notes (the gym's notes would suppress classes RealVuln scores, such as
  missing rate limiting and CSRF).
- Adapter check (cloud, no model): feeding the dev ground truth itself as findings scores TP 91/91, FP 0; the
  test half is locked in code (`--final` required).

### Round 1 results (dev only)
- Gym dev (gemma4:12b, 3 seeds; `eval/results/20261007-blue-gym-gemma4_12b-step4r1/`): function recall 21/21
  (2026-10-07 prompts: 18/21), strict 18/21 (16/21), bank/CWE-840 3/3 (0/3), clean runs with a false signal
  0/6 (2/6). Caveats: the prompts were written after seeing the 2026-10-07 gaps, and the gym notes were
  widened, so this is a dev-set improvement, not evidence of generalization. The gym dev split is now at its
  ceiling and can no longer guide round 2.
- RealVuln dev (seed 1; `eval/results/20261008-realvuln-dev-gemma4_12b/`): final TP 40, FP 12, FN 51,
  precision 0.77, recall 0.44, **F3 0.46**; 0 of 16 traps flagged. Human-authored: P 0.93, R 0.48;
  LLM-generated Django repo: P 0.60, R 0.38. Raw F3 0.50 > final 0.46: grounding/dedupe cost 3 TP, the
  verifier 1 TP and removed 6 FP.
- Failure analysis (cloud, from that `result.json` and the dev ground truth): of 51 missed labels, 32 had a
  *different* final finding within 10 lines (one issue reported per handler, the absent controls next to it
  skipped), 5 were found in raw output only, 14 were nowhere near a finding. Most missed: CWE-307 (5),
  CWE-798 (4). Mislabels seen: SSTI as CWE-79, header injection as CWE-601, role bugs as CWE-639, a fixed
  default password as CWE-256. Pipeline faults: dedupe merged two different hardcoded secrets two lines
  apart (and an XSS/SSTI pair), the 12-finding cap was hit in one dense file, a Django `tests.py` was
  scanned, one verifier reply had trailing text after valid JSON.

### Round 2 (pre-registered 2026-10-08, before its run; commit "Round 2 of step 4")
Changes, each tied to the analysis above: the detect prompt asks for every distinct issue per function and
for what each handler is missing, says where absent controls are labelled (def line or route registration,
as the dev labels do), and sharpens the CWE choices that cost hits (639 vs 862/863, 798 vs 256, 1336 vs 79,
113, 209); one few-shot example shows a handler with three findings; dedupe merges only same line or same
quote; `tests.py` skipped; JSON with trailing text accepted; finding cap 16, answer cap 2560 tokens; gym notes
add "routes that never read X-User are public by design".
**Freeze procedure (applies the rule above mechanically):** LOCAL runs RealVuln dev with round 2 (same
settings). If its final F3 is higher than round 1's 0.459 (TP 40, FP 12, FN 51), round 2 is frozen; if lower,
the round-2 commit is reverted and round 1 is frozen; an exact tie goes to the gym-dev function recall. The frozen commit is tagged
`step4-freeze`. Then, once: gym test (`blog`, 3 seeds) and RealVuln test, each with and without
`--no-examples`.

### Hardware change for the freeze and the final runs (2026-10-08, before those runs)
The remaining runs move from the Mac (Apple Silicon, Ollama/Metal) to one rented NVIDIA machine, because the
Mac is needed for other work. The same model tag is pulled and its digest is compared with the Mac's
(`6114515d63c1`) and recorded. Because two backends can answer differently with the same seed, **round 1 is
re-run on the GPU** and the freeze rule compares round 1 and round 2 *on the same machine*
(`scripts/freeze_decide.py`; higher final F3 at 3 decimals; exact tie: stop). The Mac round-1 run (F3 0.459)
stays as a cross-hardware reproducibility reference. With two identical GPUs, r1/r2 run in parallel, then the
final arms run in parallel (with examples on GPU 0, `--no-examples` on GPU 1); with one GPU, sequentially.
Everything is one script (`scripts/vast_final.sh`); the final runs use only the tree the rule selected.

### Gym diagnostic added before round 1
- **Located** (diagnostic, not a hit): any finding inside the function of the injected bug, whatever its CWE.
  It separates "found the spot but mislabelled it" from "did not find it".

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

## Final results (frozen at tag `step4-freeze`, each test run once, 2026-10-08)
Machine: one rented node with 2x RTX 3090, Ollama 0.40.1, gemma4:12b digest `6114515d63c1` (same as the Mac
runs). Sources: `eval/results/20261008-*`, `eval/baselines/realvuln_bandit.*`.

**Freeze (RealVuln dev, same machine):** round 1 TP 37 / FP 9 / FN 54, F3 0.428; round 2 TP 53 / FP 11 / FN 38,
F3 0.600 -> round 2 frozen (`20261008-step4-freeze-gpu/decision.json`).

**RealVuln test** (4 repos, 80 vulnerabilities, 14 traps; seed 1):

| system | TP | FP | FN | precision | recall (95% CI) | F3 |
|---|---|---|---|---|---|---|
| Blue, frozen (with few-shot) | 31 | 9 | 49 | 0.78 | 0.39 (0.29-0.50) | **0.41** |
| Blue, frozen, `--no-examples` | 30 | 13 | 50 | 0.70 | 0.38 (0.28-0.48) | 0.39 |
| Bandit, MEDIUM+ | 10 | 8 | 70 | 0.56 | 0.12 | 0.14 |
| Bandit, all results | 12 | 11 | 68 | 0.52 | 0.15 | 0.16 |

By stratum (Blue with few-shot): human-authored repos F3 0.27 (P 0.73, R 0.26), LLM-generated repo F3 0.56
(P 0.80, R 0.54). Without few-shot: 0.32 and 0.47. Stages (with few-shot): raw 34/8/46 F3 0.45 -> final
31/9/49 F3 0.41. The verified stage also adds Bandit-only candidates: with few-shot, the final list holds 2 of
them, both FP; the model's own findings are 31 TP / 7 FP.

**Gym test (`blog`, 4 injected cases x 3 seeds + clean x 3):**

| arm | function recall | strict recall | clean runs with a false signal |
|---|---|---|---|
| with few-shot | 6/12 (0.25-0.75) | 9/12 | 3/3 |
| `--no-examples` | 11/12 (0.65-0.99) | 11/12 | 3/3 |

Per case with few-shot: CWE-79 3/3, CWE-915 3/3, CWE-601 strict 3/3 but function 0/3 (all three point at the
`@app.get("/go")` decorator, one line above the function, as the round-2 prompt asked for endpoint-level
issues), CWE-330 0/3 (only CWE-307 reported for the reset handler). The clean-app false signals are CWE-307
(no brute-force protection) on the reset endpoints, which the gym notes declare out of scope; without
few-shot also CWE-601 on the guarded redirect and CWE-204.

### Verdicts on the pre-registered hypotheses (small n: directions, not proof)
- **H1 (beats Bandit): supported.** Gym dev 18/21 function recall vs Bandit 2/7 on the same cases; RealVuln
  test F3 0.41 vs 0.14-0.16, with higher precision (0.78 vs 0.52-0.56) and 2.6-3.3x the recall.
- **H2 (grounding lowers false signals without costing recall): partly.** Never removed a true hit on the gym
  (2026-10-07 run); on RealVuln it removed hallucinated quotes but also cost a few TP (test: 34 -> 33), and in
  round 1 a too-broad dedupe cost two more (fixed in round 2).
- **H3 (verifier removes >= 30% of false signals for <= 10 points of recall): supported on the gym, not on
  RealVuln.** Gym dev round 1: 5/5 clean findings and 3/3 extras removed, 21/21 true hits kept. RealVuln test:
  the verified stage lowered F3 (0.43 -> 0.41): the verifier rejected 2 TP and none of the 7 model FPs, and 2
  Bandit-only FPs were added. qwen3.5:9b showed the failure mode the hypothesis warned of
  (its own verifier rejected 9/10 true hits).
- **H4 (gemma4:12b higher recall, qwen3.5:9b about 2x faster): recall yes (18/21 vs 1/21); speed only 1.4x.**
- **H5 (few-shot improves recall on held-out apps): not supported.** Blog: 6/12 with vs 11/12 without.
- **H6 (gain transfers to the external benchmark): not supported.** RealVuln test F3 0.41 vs 0.39, recall 0.39
  vs 0.38: inside the noise (next item).
- **H7 (LoRA): not run.**

### What the numbers say beyond the hypotheses
- **Noise floor.** The same frozen-in-round-1 configuration scored F3 0.459 on the Mac and 0.428 on the GPU node
  (same weights, same seed; 4 of 6 repos gave identical counts). Differences of about 0.03 F3 on one seed are
  not meaningful.
- **Dev optimism.** Round 2 was written from the RealVuln dev misses: dev F3 0.600, test F3 0.41. The gym went
  from 21/21 (dev) to 6/12 (blog). The test numbers are the ones to quote.
- **Where the gain came from.** Round 1 -> round 2 on the same machine raised dev F3 from 0.428 to 0.600. Both
  test arms carry those prompt and pipeline changes; only the few-shot block differs between them, and it
  made no measurable difference. The improvement that holds up is the instruction-level change (report every
  issue per handler, CWE menu) plus pipeline fixes, not the examples.
- **No sign of memorization.** The 2026 LLM-generated test repo (F3 0.56) scored higher than the older,
  public human-authored apps (0.27), the opposite of what memorized training data would produce.
- **Dense files stay hard.** `dsvw` (27 labels in one 93-line file): 8 raw findings, recall 0.19.

## LoRA experiment (H7, pre-registered 2026-10-08, before any training)
**Question.** Does a QLoRA adapter trained on RealVuln-dev labels improve the frozen scanner on held-out code,
compared with *the same base weights without the adapter, converted the same way*?
The shipped default stays the frozen Ollama `gemma4:12b` whatever the outcome; the LoRA model is an
experimental variant.

**Data** (`src/safia_sec/lora/data.py`, `scripts/lora_build_data.py`, list in `targets/realvuln/lora_train.json`):
- Repos: the RealVuln dev half minus the 6 dev-evaluation repos = 28 repos. Rule: also drop any repo whose
  distinctive code lines overlap the selected test repos by more than 10%; measured maximum 8.2%, none dropped.
- Seeding hubs excluded: a file with more than 16 labels (24 files; every LLM-generated repo has one, the
  test LLM repo too). Training on them would teach the benchmark's seeding template.
- One example per detect call, byte-identical to the frozen scanner's prompt (a unit test checks this);
  answer = the labels as the scanner's JSON (evidence = a quotable line of the label, so every target passes
  grounding; explanation = the label's description cut to 300 characters).
- All 201 labelled chunks, all 50 chunks holding a false-positive trap (answer: no findings), 151 sampled
  label-free chunks (seed 1): 402 examples, 442 target findings, about 1.16M tokens, sha256 `3055e51df897...`.
  The run stops if the rebuilt set has a different hash.

**Training** (`scripts/lora_train.py`, fixed): QLoRA (nf4, double quant, bf16 compute) on the official
instruction-tuned checkpoint that matches Ollama's `gemma4:12b` (repo id recorded); LoRA r 16, alpha 32,
dropout 0.05 on the language model's attention and MLP projections; lr 1e-4, cosine, 10 warm-up steps,
2 epochs, effective batch 8, max length 8192 tokens, seed 1; loss on answer tokens only. No tuning on results.

**Two phases** (`scripts/vast_lora.sh gate|train`, one 48 GB GPU, separate rentals):
- **gate** (feasibility, no training; any failure = stop and report "attempted, blocked"): (a) the base weights
  download; (b) 8 QLoRA steps on the 8 longest examples at the full 8192-token length (records peak GPU memory,
  tokens/s and the estimated full training time); (c) a merged smoke adapter imports into Ollama and the scanner
  gets valid JSON from it; (d) conversion check: the base model taken through the same import path
  (`safia-base-conv`) scores within 0.05 F3 of the official Ollama `gemma4:12b` on RealVuln dev, i.e. our
  conversion reproduces the product model. A detailed training plan (GPU, time, cost) is written from the gate
  report before the second phase.
- **train**: full training; `safia-base-conv` (base, no adapter) and `safia-lora` (adapter merged) both go
  HF -> `ollama create --quantize q4_K_M` with the official template and parameters; frozen pipeline (few-shot,
  verifier, Bandit), seed 1. RealVuln dev for both (same machine), then the test half once: RealVuln test and
  gym `blog` (3 seeds) for both.

**Reading the result.** Primary: RealVuln test F3, LoRA vs base-converted. A gain is claimed only if it is at
least 0.05 F3 (above the 0.03 noise floor). Also reported: precision, recall, strata, blog function and
strict recall, and the test LLM repo's seeding hub (`backend/app/loan_operations.py`) separately from the
rest of that repo, since hubs were left out of training.

**Known caveats.** Training and test labels come from one benchmark (its labelling style can be learned); the
LLM-generated training repos share generators with the test LLM repo; the merged adapter also changes the
verifier's behaviour. Budget: at most $5 for the GPU session.
