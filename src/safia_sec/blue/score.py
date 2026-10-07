"""Scoring Blue against the gym's ground truth.

Pre-registered protocol (docs/EXPERIMENTS.md):
- strict hit    : CWE family matches and the line is within +-5 of the injected lines;
- function hit  : CWE family matches and the line is inside the function that contains the injected lines
                  (primary metric: a removed check, e.g. IDOR, has no injected line to point at);
- CWE-only hit  : CWE family matches anywhere in the file;
- false signal  : any finding on the clean app. Extra findings on vulnerable apps are reported, not punished
                  (the ground truth lists only the injected bug).
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass

from safia_sec.gym.injections import APPS, app_dir, build

from .scanner import cwe_number

TOL = 5
FAMILIES = {
    "CWE-89": {89, 564}, "CWE-639": {639, 284, 285, 862, 863, 566}, "CWE-22": {22, 23, 36, 73},
    "CWE-840": {840, 20, 1284, 190, 191, 837, 841, 1287}, "CWE-79": {79, 80, 83, 87},
    "CWE-915": {915, 269, 266, 284, 285, 862}, "CWE-330": {330, 331, 338, 340, 341, 640}, "CWE-601": {601},
}


@dataclass
class Case:
    id: str
    app: str
    cwe: str | None  # None = clean app
    source: str
    strict: tuple[int, int] | None
    function: tuple[int, int] | None


def lines_of(source: str, snippet: str) -> tuple[int, int]:
    start = source[: source.index(snippet)].count("\n") + 1
    return start, start + snippet.rstrip("\n").count("\n")


def enclosing_function(source: str, line: int) -> tuple[int, int]:
    best = None
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno <= line <= (node.end_lineno or node.lineno):
            if best is None or node.lineno > best[0]:
                best = (node.lineno, node.end_lineno or node.lineno)
    return best or (line, line)


def build_cases(apps: list[str] | None = None) -> list[Case]:
    cases = []
    for app, templates in APPS.items():
        if apps and app not in apps:
            continue
        clean = (app_dir(app) / "app.py").read_text()
        cases.append(Case(f"{app}/clean", app, None, clean, None, None))
        for cwe, t in templates.items():
            patched = build(cwe, app).patch["app.py"]
            if t.new:
                region = lines_of(patched, t.new)
            else:  # the bug is a removed check; it used to sit where the old snippet was
                s, _ = lines_of(clean, t.old)
                region = (s - 1, s + 1)
            cases.append(Case(f"{app}/{cwe}", app, cwe, patched, region, enclosing_function(patched, region[0])))
    return cases


def family_ok(case_cwe: str, found_cwe: str) -> bool:
    return cwe_number(found_cwe) in FAMILIES[case_cwe]


def score_case(case: Case, findings: list[dict]) -> dict:
    n = len(findings)
    if case.cwe is None:
        return {"n_findings": n, "false_signal": n > 0}
    fam = [f for f in findings if family_ok(case.cwe, f["cwe"])]
    s0, s1 = case.strict
    f0, f1 = case.function
    strict = [f for f in fam if s0 - TOL <= f["line"] <= s1 + TOL]
    func = [f for f in fam if f0 <= f["line"] <= f1]
    matched = {id(f) for f in strict} | {id(f) for f in func}
    located = any(f0 <= f["line"] <= f1 for f in findings)  # diagnostic: right function, any CWE
    return {"n_findings": n, "strict": bool(strict), "function": bool(func), "cwe_only": bool(fam),
            "located": located, "extras": n - len(matched)}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p, d = k / n, 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - a) / d, (c + a) / d
