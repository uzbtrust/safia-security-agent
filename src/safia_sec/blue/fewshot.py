"""Hand-written few-shot examples added to the detect prompt (step 4, docs/TASKS.md).

Not copied from any gym app: each snippet is small and original, illustrating a
VULNERABILITY PATTERN rather than a specific fixture, so the prompt coaches the
model to recognize the shape of a bug class instead of memorizing gym code (using
literal gym snippets here would leak ground truth into the dev/test eval and make
any recall gain meaningless).

Chosen to target the gap measured in the 2026-10-07 dev gym (docs/EXPERIMENTS.md):
both local models missed bank/CWE-840 (a weakened business-logic check) in 3 of 3
seeds, even though the detect prompt already names "negative or oversized amounts".
Two further examples (a removed ownership check, a different SQL-injection shape)
are included so the block teaches a pattern, not a single nudge toward one CWE.
"""
from __future__ import annotations

EXAMPLES: list[tuple[str, str, str, str]] = [
    ("CWE-840", "weakened business-logic check",
     'if abs(quantity) > stock[item]:\n'
     '    abort(400)\n'
     'stock[item] -= quantity\n',
     "abs() accepts a negative quantity as long as its size is in range, so a customer can send "
     "quantity=-5 and INCREASE stock instead of buying it. The check only validated the magnitude, "
     "not the sign; a correct version rejects quantity <= 0 outright. Watch for any arithmetic "
     "guard (abs(), range checks, type casts) that can let a negative or out-of-range value through."),
    ("CWE-639", "removed ownership check (IDOR)",
     'row = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()\n'
     'return jsonify(dict(row))\n',
     "the record is fetched by an id taken straight from the request, with no comparison against "
     "the caller's own id. Any logged-in user can read any other user's invoice by changing the id "
     "in the URL. There is no injected line to point at here; the bug is an absent check, so flag "
     "the function that does the lookup."),
    ("CWE-89", "SQL injection via string formatting",
     'rows = db.execute(\n'
     '    "SELECT * FROM logs WHERE user = \'{}\'".format(user)\n'
     ').fetchall()\n',
     "the value is spliced into the SQL text instead of passed as a bound parameter, so a user "
     "value like \"x' OR '1'='1\" changes the query's meaning. .format()/f-strings/+ on SQL text "
     "are the same bug as %-formatting; a parameterized query (\"...WHERE user = ?\", (user,)) is "
     "the fix. A query already using a bound parameter for one value is not this bug."),
]


def block(examples: list[tuple[str, str, str, str]] = EXAMPLES) -> str:
    """Formatted text for the detect prompt's {examples} slot, or '' when disabled."""
    if not examples:
        return ""
    lines = ["Examples of vulnerability PATTERNS (not from this codebase; learn the shape, not the exact code):"]
    for cwe, title, snippet, why in examples:
        indented = "\n".join("    " + ln for ln in snippet.rstrip("\n").splitlines())
        lines.append(f"- {cwe} ({title}):\n{indented}\n  Why: {why}")
    return "\n".join(lines) + "\n\n"
