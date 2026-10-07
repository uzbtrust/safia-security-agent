"""Blue: a read-only security reviewer built around a local model.

Pipeline per Python file:
  1. detect   - the model reads numbered code and reports findings (JSON-schema constrained);
  2. ground   - every finding must quote code that really exists in the file; the line number is snapped
                to where the quote occurs; findings without a real quote are dropped (anti-hallucination);
  3. bandit   - an independent static tool corroborates findings (and may add candidates);
  4. verify   - a second model call tries to REFUTE each candidate and proposes a fix.
`stages` keeps the list after every step so the value of each step can be measured.

Permissions: reads files below the scan root only (symlinks that leave the root are skipped); never executes
scanned code, never writes into the scanned tree, no shell. Bandit runs with a fixed argv, not model-chosen.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator

from . import fewshot
from .llm import ChatClient, LLMError

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", "build", "dist", "site-packages"}
TEST_DIRS = {"tests", "test", "migrations"}
MAX_FILE_BYTES = 200_000
# format guard: a verbose model must not run into the token cap and break the JSON; 12 leaves room for dense files
MAX_FINDINGS, MAX_TEXT = 12, 300

DETECT_SCHEMA = {"type": "object", "properties": {"findings": {"type": "array", "maxItems": MAX_FINDINGS, "items": {
    "type": "object",
    "properties": {"file": {"type": "string"}, "line": {"type": "integer"}, "cwe": {"type": "string"},
                   "evidence": {"type": "string", "maxLength": MAX_TEXT},
                   "explanation": {"type": "string", "maxLength": MAX_TEXT}},
    "required": ["file", "line", "cwe", "evidence", "explanation"]}}}, "required": ["findings"]}
VERIFY_SCHEMA = {"type": "object", "properties": {
    "verdict": {"type": "string", "enum": ["confirmed", "rejected"]},
    "reason": {"type": "string", "maxLength": MAX_TEXT}, "fix": {"type": "string", "maxLength": MAX_TEXT}},
    "required": ["verdict", "reason", "fix"]}

SEVERITY = {89: "high", 78: "high", 639: "high", 862: "high", 863: "high", 22: "high", 915: "high", 330: "high",
            798: "high", 502: "high", 918: "high", 79: "medium", 840: "medium", 601: "low", 327: "medium"}


@dataclass
class Finding:
    file: str
    line: int
    cwe: str
    evidence: str
    explanation: str
    severity: str = "medium"
    fix: str = ""
    sources: list[str] = field(default_factory=lambda: ["llm"])
    verdict: str = ""  # "", "confirmed" or "rejected"
    reason: str = ""

    def brief(self) -> dict:
        return {"file": self.file, "line": self.line, "cwe": self.cwe, "sources": self.sources,
                "verdict": self.verdict, "evidence": self.evidence[:120]}


@dataclass
class ScanResult:
    findings: list[Finding]
    dropped: list[dict]
    stages: dict[str, list[dict]]
    meta: dict


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text()


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def cwe_number(s: str) -> int | None:
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else None


def canonical_cwe(s: str) -> str:
    n = cwe_number(s)
    return f"CWE-{n}" if n else "CWE-unknown"


def severity_for(cwe: str) -> str:
    return SEVERITY.get(cwe_number(cwe) or -1, "medium")


# ----------------------------------------------------------------------------------------------- files
def is_test_path(rel: Path) -> bool:
    name = rel.name
    return (any(part in TEST_DIRS for part in rel.parts[:-1]) or name == "conftest.py"
            or name.startswith("test_") or name.endswith("_test.py"))


def iter_python_files(root: Path, include_tests: bool = False) -> Iterator[Path]:
    """Python files below root. Skips vendored/build dirs, tests and migrations (unless include_tests),
    huge files and symlinks that leave the root. A single file given as root is always scanned."""
    root = root.resolve()
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or (not include_tests and is_test_path(rel)):
            continue
        try:
            real = p.resolve()
            if root not in real.parents or not real.is_file() or real.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield real


def chunk_ranges(source: str, max_lines: int = 220) -> list[tuple[int, int]]:
    """1-based inclusive line ranges aligned on top-level statements; one chunk when the file is short."""
    n = len(source.splitlines())
    if n <= max_lines:
        return [(1, max(n, 1))]
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [(i, min(i + max_lines - 1, n)) for i in range(1, n + 1, max_lines)]
    ranges, start, end = [], 1, 0
    for node in tree.body:
        s, e = node.lineno, node.end_lineno or node.lineno
        if e - start + 1 > max_lines and end >= start:
            ranges.append((start, end))
            start = end + 1
        end = e
    ranges.append((start, n))
    return ranges


def numbered(source: str, start: int, end: int) -> str:
    lines = source.splitlines()
    return "\n".join(f"{i:3d}  {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1))


# ------------------------------------------------------------------------------------------- grounding
def parse_findings(text: str) -> list[dict]:
    data = json.loads(text)
    items = data["findings"]
    out = []
    for f in items if isinstance(items, list) else []:
        if (isinstance(f, dict) and isinstance(f.get("line"), int) and isinstance(f.get("cwe"), str)
                and isinstance(f.get("evidence"), str) and isinstance(f.get("explanation"), str)):
            out.append(f)
    return out


def snap_line(evidence: str, source: str, claimed: int) -> int | None:
    """Line where the quoted evidence really occurs (nearest to the claim), or None if it is not in the file."""
    lines = source.splitlines()
    quoted = [norm(x) for x in evidence.splitlines() if len(norm(x)) >= 6]
    if not quoted:
        return None
    key = max(quoted, key=len)
    hits = [i for i, ln in enumerate(lines, 1) if key in norm(ln)]
    if not hits:  # multi-line quote that does not fit a single line
        flat = norm(evidence)
        if len(flat) >= 12 and flat in norm(source):
            return min(max(claimed, 1), len(lines))
        return None
    return min(hits, key=lambda i: abs(i - claimed))


def ground(raw: list[dict], source: str, file: str) -> tuple[list[Finding], list[dict]]:
    kept, dropped = [], []
    for f in raw[:MAX_FINDINGS]:
        line = snap_line(f["evidence"], source, f["line"])
        if line is None:
            dropped.append({"file": file, "line": f["line"], "cwe": f["cwe"], "reason": "evidence_not_in_source"})
            continue
        cwe = canonical_cwe(f["cwe"])
        kept.append(Finding(file, line, cwe, f["evidence"].strip(), f["explanation"].strip(), severity_for(cwe)))
    return kept, dropped


def dedupe(findings: list[Finding]) -> list[Finding]:
    out: list[Finding] = []
    for f in findings:
        if any(g.file == f.file and g.cwe == f.cwe and abs(g.line - f.line) <= 3 for g in out):
            continue
        out.append(f)
    return out


# ----------------------------------------------------------------------------------------------- bandit
def run_bandit(root: Path) -> list[dict]:
    """Independent static findings (MEDIUM+ severity and confidence). Returns [] if Bandit is not installed."""
    root = root.resolve()
    target = str(root)
    cmd = [sys.executable, "-m", "bandit", "-q", "-f", "json", "-r", target, "-x", ",".join(f"*/{d}" for d in SKIP_DIRS)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        data = json.loads(res.stdout or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    out = []
    for r in data.get("results", []):
        if r.get("issue_severity") == "LOW" or r.get("issue_confidence") == "LOW":
            continue
        path = Path(r["filename"]).resolve()
        rel = path.name if root.is_file() else str(path.relative_to(root)) if root in path.parents else str(path)
        out.append({"file": rel, "line": r["line_number"], "cwe": (r.get("issue_cwe") or {}).get("id"),
                    "text": r["issue_text"], "code": (r.get("code") or "").strip()})
    return out


# ------------------------------------------------------------------------------------------------ scanner
class Scanner:
    def __init__(self, client: ChatClient, notes: str = "", verify: bool = True, use_bandit: bool = True,
                 max_lines: int = 220, use_examples: bool = True, include_tests: bool = False):
        self.client, self.notes, self.verify, self.use_bandit, self.max_lines = client, notes.strip(), verify, use_bandit, max_lines
        self.use_examples, self.include_tests = use_examples, include_tests
        self.detect_prompt, self.verify_prompt = load_prompt("detect"), load_prompt("verify")

    def _notes_block(self) -> str:
        return f"- Project notes (from the maintainers): {self.notes}\n" if self.notes else ""

    def _examples_block(self) -> str:
        return fewshot.block() if self.use_examples else ""

    def scan(self, root: Path) -> ScanResult:
        root = Path(root).resolve()
        base = root.parent if root.is_file() else root
        files = list(iter_python_files(root, self.include_tests))
        stages: dict[str, list[dict]] = {"raw": [], "grounded": [], "verified": [], "final": []}
        dropped: list[dict] = []
        meta = {"model": self.client.model, "files": len(files), "llm_calls": 0, "prompt_tokens": 0,
                "gen_tokens": 0, "wall_s": 0.0, "errors": [], "verify": self.verify, "bandit": self.use_bandit,
                "examples": self.use_examples, "include_tests": self.include_tests,
                "prompt_sha": hashlib.sha256((self.detect_prompt + self.verify_prompt).encode()).hexdigest()[:12]}
        bandit = run_bandit(root) if self.use_bandit else []
        results: list[Finding] = []

        for path in files:
            rel = str(path.relative_to(base))
            source = path.read_text(errors="replace")
            candidates: list[Finding] = []
            for start, end in chunk_ranges(source, self.max_lines):
                prompt = self.detect_prompt.format(file=rel, notes=self._notes_block(), examples=self._examples_block(),
                                                   numbered=numbered(source, start, end))
                try:
                    reply = self.client.chat(prompt, DETECT_SCHEMA)
                    self._account(meta, reply)
                    raw = parse_findings(reply.text)
                except (LLMError, ValueError, KeyError, TypeError) as exc:
                    meta["errors"].append(f"{rel}:{start}-{end}: {type(exc).__name__}: {exc}"[:200])
                    continue
                stages["raw"] += [{"file": rel, "line": f["line"], "cwe": f["cwe"], "evidence": f["evidence"][:120]} for f in raw]
                grounded, drop = ground(raw, source, rel)
                dropped += drop
                candidates += grounded
            candidates = dedupe(candidates)
            stages["grounded"] += [c.brief() for c in candidates]

            for b in (b for b in bandit if b["file"] == rel):  # corroborate, or add a Bandit-only candidate
                near = [c for c in candidates if abs(c.line - b["line"]) <= 3]
                if near:
                    for c in near:
                        if "bandit" not in c.sources:
                            c.sources.append("bandit")
                elif b["code"]:
                    cwe = canonical_cwe(str(b["cwe"])) if b["cwe"] else "CWE-unknown"
                    evid = next((x for x in b["code"].splitlines() if x.strip() and re.search(r"[A-Za-z]", x)), b["code"])
                    evid = re.sub(r"^\d+\s+", "", evid.strip())
                    line = snap_line(evid, source, b["line"]) or b["line"]
                    candidates.append(Finding(rel, line, cwe, evid, b["text"], severity_for(cwe), sources=["bandit"]))

            for c in candidates:
                if self.verify:
                    self._verify(c, rel, source, meta, dropped)
                else:
                    results.append(c)
                    continue
                if c.verdict == "confirmed":
                    results.append(c)
            stages["verified"] += [c.brief() for c in candidates if c.verdict != "rejected"]

        stages["final"] = [c.brief() for c in results]
        return ScanResult(results, dropped, stages, meta)

    def _verify(self, c: Finding, rel: str, source: str, meta: dict, dropped: list[dict]) -> None:
        start = max(1, c.line - 60)
        prompt = self.verify_prompt.format(cwe=c.cwe, line=c.line, evidence=c.evidence, explanation=c.explanation,
                                           file=rel, notes=self._notes_block(), examples=self._examples_block(),
                                           numbered=numbered(source, start, c.line + 60))
        try:
            reply = self.client.chat(prompt, VERIFY_SCHEMA)
            self._account(meta, reply)
            data = json.loads(reply.text)
            verdict = data["verdict"]
        except (LLMError, ValueError, KeyError, TypeError) as exc:
            meta["errors"].append(f"verify {rel}:{c.line}: {type(exc).__name__}: {exc}"[:200])
            c.verdict, c.reason = "confirmed", "verifier unavailable; kept unverified"
            return
        c.verdict, c.reason, c.fix = verdict, str(data.get("reason", ""))[:MAX_TEXT], str(data.get("fix", ""))[:MAX_TEXT]
        if verdict == "rejected":
            dropped.append({"file": rel, "line": c.line, "cwe": c.cwe, "reason": "refuted_by_verifier: " + c.reason})

    @staticmethod
    def _account(meta: dict, reply) -> None:
        meta["llm_calls"] += 1
        meta["prompt_tokens"] += reply.prompt_tokens or 0
        meta["gen_tokens"] += reply.gen_tokens or 0
        meta["wall_s"] = round(meta["wall_s"] + reply.wall_s, 1)
