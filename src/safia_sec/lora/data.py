"""LoRA training data from RealVuln dev labels (pre-registered in docs/EXPERIMENTS.md, "LoRA experiment").

Each example is one detect call exactly as the frozen scanner makes it (same chunking, numbering, prompt and
few-shot block) paired with the answer the labels imply: {"findings": [...]} in the scanner's JSON schema.
- Repos: the RealVuln dev half minus the 6 repos used for dev evaluation (fixed list in
  targets/realvuln/lora_train.json, with the measured code overlap against the test repos).
- Seeding hubs are excluded: a file with more than MAX_FINDINGS labels is the benchmark's seeding template
  (every LLM-generated repo has one, the test repo too); training on them would teach the template, and they
  do not fit the scanner's finding cap anyway.
- Positives: every remaining chunk with a label. Negatives (answer: no findings): every chunk holding a
  false-positive trap, then a seeded random sample of label-free chunks up to the number of positives.
- Evidence is a line copied from the file (the label's first line with at least 6 non-space characters), so
  every target passes the scanner's grounding step; explanations are the labels' descriptions, cut to the
  schema's 300 characters.
Nothing here executes repository code.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

from ..blue import fewshot
from ..blue.scanner import MAX_FINDINGS, MAX_TEXT, chunk_ranges, iter_python_files, load_prompt, numbered

TRAIN_FILE = Path(__file__).resolve().parents[3] / "targets" / "realvuln" / "lora_train.json"


@dataclass
class Example:
    repo: str
    file: str
    start: int
    end: int
    prompt: str
    answer: str
    n_findings: int
    kind: str  # positive | trap | negative | skip

    def record(self) -> dict:
        return {"repo": self.repo, "file": self.file, "chunk": [self.start, self.end], "kind": self.kind,
                "n_findings": self.n_findings,
                "messages": [{"role": "user", "content": self.prompt}, {"role": "assistant", "content": self.answer}]}


def scored(gt: dict) -> list[dict]:
    return [e for e in gt["findings"] if e.get("scoring", "scored") == "scored"]


def hub_files(gt: dict) -> set[str]:
    counts: dict[str, int] = {}
    for e in scored(gt):
        if e["is_vulnerable"]:
            counts[e["file"]] = counts.get(e["file"], 0) + 1
    return {f for f, n in counts.items() if n > MAX_FINDINGS}


def evidence_line(lines: list[str], start: int, end: int | None) -> int | None:
    """First line of the label's range with >= 6 non-space characters (1-based), or None."""
    last = start + 3 if end is None else max(end, start)
    for i in range(start, min(last, len(lines)) + 1):
        if 1 <= i <= len(lines) and len(re.sub(r"\s+", "", lines[i - 1])) >= 6:
            return i
    return None


def shorten(text: str, limit: int = MAX_TEXT) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[: stop + 1] if stop > limit // 2 else cut[: limit - 1].rstrip() + ".")


def answer_for(entries: list[dict], rel: str, lines: list[str]) -> tuple[str, int, int]:
    """JSON answer for one chunk; returns (answer, n_findings, n_labels_without_a_quotable_line)."""
    out, skipped = [], 0
    for e in sorted(entries, key=lambda e: (e["location"].get("start_line") or 0, e["id"])):
        loc = e["location"]
        line = evidence_line(lines, loc.get("start_line") or 0, loc.get("end_line"))
        if line is None:
            skipped += 1
            continue
        desc = (e.get("evidence") or {}).get("description") or e.get("vulnerability_class", "")
        out.append({"file": rel, "line": line, "cwe": e["primary_cwe"], "evidence": lines[line - 1].strip()[:MAX_TEXT],
                    "explanation": shorten(desc)})
    return json.dumps({"findings": out}, ensure_ascii=False), len(out), skipped


def repo_examples(repo_id: str, root: Path, gt: dict, prompt: str, examples_block: str) -> tuple[list[Example], dict]:
    hubs = hub_files(gt)
    entries = scored(gt)
    exs, stats = [], {"hub_files": sorted(hubs), "labels_used": 0, "labels_unquotable": 0, "chunks": 0}
    for path in iter_python_files(root):
        rel = str(path.relative_to(root.resolve()))
        if rel in hubs:
            continue
        source = path.read_text(errors="replace")
        lines = source.splitlines()
        for start, end in chunk_ranges(source):
            stats["chunks"] += 1
            inside = [e for e in entries if e["file"] == rel and start <= (e["location"].get("start_line") or 0) <= end]
            vul = [e for e in inside if e["is_vulnerable"]]
            traps = [e for e in inside if not e["is_vulnerable"]]
            text = prompt.format(file=rel, notes="", examples=examples_block, numbered=numbered(source, start, end))
            if vul:
                answer, n, skipped = answer_for(vul, rel, lines)
                stats["labels_used"] += n
                stats["labels_unquotable"] += skipped
                kind = "positive" if n else "skip"  # never teach "nothing here" on a labelled chunk
            else:
                answer, n, kind = json.dumps({"findings": []}), 0, "trap" if traps else "negative"
            exs.append(Example(repo_id, rel, start, end, text, answer, n, kind))
    return exs, stats


def select(examples: list[Example], seed: int = 1) -> list[Example]:
    """All positives and trap chunks; label-free chunks sampled up to the number of positives."""
    pos = [e for e in examples if e.kind == "positive"]
    traps = [e for e in examples if e.kind == "trap"]
    neg = [e for e in examples if e.kind == "negative"]
    rng = random.Random(seed)
    rng.shuffle(neg)
    picked = pos + traps + neg[: max(0, len(pos) - len(traps))]
    rng.shuffle(picked)
    return picked


def build(bench: Path, repos_dir: Path, out: Path, train_file: Path | None = None, seed: int = 1) -> dict:
    spec = json.loads(Path(train_file or TRAIN_FILE).read_text())
    prompt, block = load_prompt("detect"), fewshot.block()
    every, per_repo = [], {}
    for rid in spec["train_repos"]:
        gt = json.loads((bench / "ground-truth" / rid / "ground-truth.json").read_text())
        exs, stats = repo_examples(rid, repos_dir / rid, gt, prompt, block)
        every += exs
        per_repo[rid] = stats
    chosen = select(every, seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for e in chosen:
            fh.write(json.dumps(e.record(), ensure_ascii=False) + "\n")
    summary = {"examples": len(chosen), "positive": sum(e.kind == "positive" for e in chosen),
               "trap": sum(e.kind == "trap" for e in chosen), "negative": sum(e.kind == "negative" for e in chosen),
               "findings": sum(e.n_findings for e in chosen), "chars": sum(len(e.prompt) + len(e.answer) for e in chosen),
               "candidate_chunks": len(every), "seed": seed,
               "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "per_repo": per_repo}
    (out.parent / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary
