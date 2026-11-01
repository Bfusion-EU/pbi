"""Layout contract of the analytic (story) pages: sections never overlap and everything ends above the footer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402
import pbir  # noqa: E402
import extensions  # noqa: E402,F401

# Pages excluded on purpose (key -> reason). Empty = every analytic page obeys the contract.
EXCLUDED = {}
# Pages exempt from the "ends at or above YNEXT" rule only (their section rule is still checked).
EXCLUDED_YNEXT = {
    "onepager": "legacy: its chapter-button row (and the three cards above it) sit at y=1620, below YNEXT=1606; "
                "the page is 1800 high so nothing is cut",
}

FOOTER_KEYS = ("next", "back")      # chapter buttons sit AT pages.YNEXT by design


def _analytic_pages():
    hidden = {pages.PID[k] for k, _ in pages.HIDDEN_PAGES}
    key_of = {v: k for k, v in pages.PID.items()}
    return [(key_of[pg.id], pg) for pg in pages.build_all()
            if pg.id not in hidden and pg.height == pages.TALL and pg.id != pages.PID["home"]]


def _sections(pg):
    """-> [(number, y)] of the circled section headers (keys sec1..sec5), top to bottom."""
    out = []
    for n in range(1, 6):
        vc = next((v for v in pg.visuals if v["name"] == pbir.uid(pg.id, f"sec{n}", "textbox")), None)
        if vc:
            out.append((n, vc["position"]["y"]))
    return sorted(out, key=lambda t: t[1])


def test_sections_do_not_overlap_and_end_above_footer():
    problems = []
    checked = 0
    for key, pg in _analytic_pages():
        if key in EXCLUDED:
            continue
        secs = _sections(pg)
        assert secs, f"{key}: no section headers found"
        checked += 1
        foot = {pbir.uid(pg.id, k, "actionButton") for k in FOOTER_KEYS}
        for vc in pg.visuals:
            if vc["name"] in foot or "visualGroup" in vc:
                continue
            p = vc["position"]
            bottom = p["y"] + p["height"]
            if key not in EXCLUDED_YNEXT and bottom > pages.YNEXT + 0.01:
                problems.append(f"{key}: {vc['name']} ends at {bottom} > YNEXT {pages.YNEXT}")
            # the section a visual belongs to = the last header at or above its top
            mine = [(n, y) for n, y in secs if y <= p["y"] + 0.01]
            if not mine:
                continue
            nxt = [y for _n, y in secs if y > mine[-1][1]]
            if nxt and bottom > nxt[0] + 0.01:
                problems.append(f"{key}: section {mine[-1][0]} visual at y={p['y']} ends at {bottom}, "
                                f"past the next header at {nxt[0]}")
    assert checked >= 8
    assert problems == [], "\n".join(problems)
