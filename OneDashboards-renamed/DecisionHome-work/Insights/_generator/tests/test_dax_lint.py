"""Static DAX checks that build.py --check cannot do (it only verifies names exist).

Rule: a boolean filter argument of CALCULATE / CALCULATETABLE may not contain CALCULATE ("A function 'CALCULATE' has
been used in a True/False expression that is used as a table filter expression"). Put the value in a VAR first.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
from story_measures import MEASURES  # noqa: E402

TABLE_FILTERS = ("KEEPFILTERS", "REMOVEFILTERS", "FILTER", "ALL", "VALUES", "TREATAS", "USERELATIONSHIP",
                 "CROSSFILTER", "CALCULATETABLE", "DATESBETWEEN", "SUMMARIZE", "SELECTCOLUMNS", "ADDCOLUMNS")


def _args(s, open_idx):
    """Top-level comma-separated arguments of the call whose '(' is at open_idx (string literals respected)."""
    depth, cur, out, in_str = 0, "", [], False
    for c in s[open_idx:]:
        if c == '"':
            in_str = not in_str
        if not in_str:
            if c == "(":
                depth += 1
                if depth == 1:
                    continue
            elif c == ")":
                depth -= 1
                if depth == 0:
                    out.append(cur)
                    return out
            elif c == "," and depth == 1:
                out.append(cur)
                cur = ""
                continue
        cur += c
    return out


def calculate_in_boolean_filter(expr):
    """-> boolean filter arguments of CALCULATE(TABLE) that contain CALCULATE themselves."""
    e = re.sub(r"--[^\n]*", "", expr)
    bad = []
    for mt in re.finditer(r"\bCALCULATE(TABLE)?\s*\(", e):
        for f in _args(e, mt.end() - 1)[1:]:
            fs = f.strip()
            if (re.search(r"\bCALCULATE\b", fs) and re.search(r"[<>=]", fs)
                    and not fs.upper().startswith(TABLE_FILTERS)):
                bad.append(fs)
    return bad


def test_lint_catches_the_known_bad_form():
    bad = ('CALCULATE ( COUNTROWS ( T ), REMOVEFILTERS (), T[d] < EOMONTH ( MIN ( 1, CALCULATE ( MAX ( T[d] ), '
           'REMOVEFILTERS () ) ), -1 ) + 1 )')
    assert calculate_in_boolean_filter(bad)
    ok = "VAR _pe = CALCULATE ( MAX ( T[d] ) ) RETURN CALCULATE ( COUNTROWS ( T ), T[d] < _pe + 1 )"
    assert calculate_in_boolean_filter(ok) == []


def test_no_calculate_in_boolean_filters():
    offenders = {m["name"]: calculate_in_boolean_filter(m["expression"]) for m in MEASURES}
    assert {k: v for k, v in offenders.items() if v} == {}
