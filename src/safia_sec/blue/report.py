"""Reports: JSON for machines, Markdown for people. Code and model text are untrusted, so they are escaped."""
from __future__ import annotations

import html
from collections import Counter
from dataclasses import asdict

from .scanner import ScanResult

ORDER = {"high": 0, "medium": 1, "low": 2}


def to_dict(result: ScanResult) -> dict:
    return {"meta": result.meta, "findings": [asdict(f) for f in result.findings],
            "dropped": result.dropped, "stages": result.stages}


def fence_for(text: str) -> str:
    """A code fence longer than any backtick run inside the text, so quoted code cannot break out of it."""
    run = best = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        best = max(best, run)
    return "`" * max(3, best + 1)


def esc(text: str) -> str:
    return html.escape(text, quote=False).replace("\n", " ")


def to_markdown(result: ScanResult, target: str = "") -> str:
    m = result.meta
    out = [f"# Security scan: {esc(target)}", "",
           f"Model `{esc(str(m['model']))}` · files {m['files']} · LLM calls {m['llm_calls']} · "
           f"verify {'on' if m['verify'] else 'off'} · bandit {'on' if m['bandit'] else 'off'}", ""]
    fs = sorted(result.findings, key=lambda f: (ORDER.get(f.severity, 3), f.file, f.line))
    out.append(f"**{len(fs)} finding(s)**; {len(result.dropped)} candidate(s) dropped "
               f"({', '.join(f'{k}: {v}' for k, v in Counter(d['reason'].split(':')[0] for d in result.dropped).items()) or 'none'}).")
    for i, f in enumerate(fs, 1):
        fence = fence_for(f.evidence)
        out += ["", f"## {i}. [{f.severity.upper()}] {f.cwe} at `{esc(f.file)}:{f.line}`", "",
                f"Found by: {', '.join(f.sources)}" + (f" · verifier: {f.verdict}" if f.verdict else ""), "",
                "Evidence:", "", fence, f.evidence, fence, "", f"Why: {esc(f.explanation)}"]
        if f.reason:
            out += ["", f"Verifier: {esc(f.reason)}"]
        if f.fix:
            out += ["", f"Suggested fix: {esc(f.fix)}"]
    if m["errors"]:
        out += ["", "## Errors", ""] + [f"- {esc(e)}" for e in m["errors"]]
    return "\n".join(out) + "\n"
