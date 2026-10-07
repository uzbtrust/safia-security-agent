"""Few-shot block for the detect and verify prompts (step 4, docs/EXPERIMENTS.md "Step 4 protocol").

Each example is a short, original contrast pair (the flawed line and its guarded form), never code copied
from a gym app or a benchmark repo: literal evaluation code in the prompt would leak ground truth and make
any gain meaningless. Round 1 targets what the dev evidence showed:
- gemma4:12b flagged the right function of bank/CWE-840 but under CWE-606/603, and missed the class
  itself in 3 of 3 seeds -> a business-rule example in a new shape (a percentage, not a transfer);
- the only clean-app false signal that survived verification was a bound LIKE parameter built with an
  f-string -> a contrast pair separating SQL text from bound values;
- removed ownership checks have no line of their own -> where to point;
- RealVuln dev labels many configuration-level issues (hardcoded keys, debug mode) -> one config example.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    cwe: str
    title: str
    flawed: str
    guarded: str
    why: str


EXAMPLES: list[Example] = [
    Example(
        "CWE-840", "business rule not enforced",
        'pct = float(request.json["discount_pct"])\norder.total = order.total * (1 - pct / 100)',
        'if not 0 <= pct <= MAX_DISCOUNT_PCT:\n    abort(400)',
        "a percentage, amount or quantity from the request must be checked against the business rule on both "
        "sides: pct=150 makes the total negative. A check of one side only (an upper limit, or abs()) is the "
        "same bug. Report it at the line that uses the value.",
    ),
    Example(
        "CWE-639", "object fetched by id without an ownership check",
        'doc = Document.query.get_or_404(doc_id)\nreturn jsonify(doc.to_dict())',
        'if doc.owner_id != current_user.id:\n    abort(403)',
        "any logged-in user can read another user's document by changing the id. The bug is an absent check, "
        "so point at the lookup line.",
    ),
    Example(
        "CWE-89", "SQL text built from request data",
        'db.execute("SELECT * FROM notes WHERE owner = ? AND title = \'%s\'" % term, (uid,))',
        'db.execute("SELECT * FROM notes WHERE owner = ? AND title LIKE ?", (uid, f"%{term}%"))',
        "only SQL text assembled from request data is injectable (f-string, .format, % or + on the query "
        "string). The guarded line is NOT a finding: building a bound VALUE with an f-string is safe. A bound "
        "parameter elsewhere in the same query does not make spliced text safe.",
    ),
    Example(
        "CWE-798", "hardcoded secret (configuration is code too)",
        'app.config["SECRET_KEY"] = "dev-secret-123"',
        'app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]',
        "anyone with the source can forge sessions. Configuration lines are findings too: a debug mode left on "
        "(CWE-489) or a cookie without Secure/HttpOnly (CWE-614) is reported at its own line.",
    ),
]


def _indent(code: str) -> str:
    return "\n".join("      " + ln for ln in code.splitlines())


def block(examples: list[Example] = EXAMPLES) -> str:
    """Text for the {examples} slot of the detect and verify prompts, or '' when disabled."""
    if not examples:
        return ""
    lines = ["Examples (not from this codebase; learn the pattern, not the code):"]
    for e in examples:
        lines.append(f"- {e.cwe} ({e.title}).\n    Flawed:\n{_indent(e.flawed)}\n    Guarded:\n{_indent(e.guarded)}\n"
                     f"    Why: {e.why}")
    return "\n".join(lines) + "\n\n"
