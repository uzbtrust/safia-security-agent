# Decisions

The choices that shaped the project, why they were made, and what they cost.

1. **The product runs fully locally.** The reviewer reads proprietary code, so the model is an open-weight 12B
   model served by Ollama on 127.0.0.1. Cost: a 12B model is far weaker than frontier models, and needs about
   11 GB of accelerator memory.

2. **Model chosen by a rule written before the comparison.** gemma4:12b vs qwen3.5:9b on the gym dev split,
   decided by function-level recall (18/21 vs 1/21). The surprise was why: qwen's verifier rejected 9 of its
   own 10 true findings with wrong reasons (self-verification can destroy recall in a small model).

3. **Our own gym with proven ground truth.** Public benchmarks are scarce, partly in the models' training data,
   and their labels are hard to check. Red (a model or a template) injects a bug and writes an exploit; a
   referee that runs code, not an LLM, accepts it only if the exploit fails before and works after while
   functional tests stay green. Cost: synthetic, small apps; the referee proves exploitability, not realism.

4. **An external benchmark as the real test.** RealVuln (Apache-2.0, labelled Python repos with false-positive
   traps). Split by repo with a hash rule, test half locked in code, scored with the benchmark's own matcher
   rules. Cost: a small subset (runtime budget).

5. **A precision-minded pipeline.** Findings must quote real code (grounding), a second call tries to refute
   them, Bandit corroborates. On the gym dev split the verifier removed every clean-app false signal without
   losing a true hit; on the blog test split clean-app false signals survived (3/3), and on RealVuln test the
   filter stages cost F3 (0.45 raw -> 0.41). Kept, because a reviewer that cries wolf is ignored, but it is
   the first thing to revisit.

6. **Pre-registration and a dev/test discipline.** Hypotheses, metrics, the split, the number of improvement
   rounds (two), the freeze rule and the final protocol were committed before the runs they govern. This is
   why the project can report that its few-shot block did not help, and that dev numbers overstated test
   performance.

7. **Few-shot before fine-tuning.** Cheaper, reversible and measurable with an on/off switch. It turned out to
   add nothing measurable; the gains came from instructions (report every issue per handler, a CWE menu) and
   pipeline fixes found by error analysis. LoRA was left for after the freeze; it was prepared (data, scripts,
   pre-registration) and stopped at a two-attempt feasibility gate, and then dropped for time and budget rather
   than rushed: an unfinished fine-tune would add a claim the evidence cannot carry.

8. **Data rights.** Model output used to train weights must come from providers whose terms allow it
   (open-weight models with verified terms). Text written by the coding assistant (Claude) was used only as gym
   data, never as training data.

9. **Moving the last runs to a rented GPU without breaking comparability.** The Mac was needed for other work.
   Because backends differ even with the same weights and seed, round 1 was re-run on the GPU so that the
   freeze compared both rounds on one machine. Measured side effect: the noise floor (F3 0.459 Mac vs 0.428
   GPU for the same configuration). Cost of the whole GPU session: $0.36.

10. **Scope.** The case study also offered a live test of external applications as a bonus. It was not pursued:
    this project stays offline, reproducible and within systems we own.
