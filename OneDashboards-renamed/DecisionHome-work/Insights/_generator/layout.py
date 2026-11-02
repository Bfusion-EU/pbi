"""Layout passes on the built pages (run by pages.build_all after the filter/tooltip passes, before a11y).

act_first(pg)        — standard chapter page: the list to act on (section ④) moves up to ②, the trend (②) to ③ and
                       the drivers (③) to ④, so the list is visible without scrolling. False = page left as it is.
nav_row(pg, key)     — 30 px row under the header: breadcrumb left, chapter strip right (chapters with deep-dives).
hide_deep_dives(...) — deep-dive pages ("5c · …") leave the tab bar; buttons and drill-through still reach them.
Spec: BFusion-Apps docs/superpowers/specs/2026-11-02-insights-navigation-design.md
"""
import math
import re

import pbir

NAV_Y, NAV_H, NAV_SHIFT = 86, 30, 36
FOOTER_FALLBACK_Y = 1500   # only used when a page has neither its own Next nor Back button
HEADER_BOTTOM = 80   # header chrome (title, subtitle, slicers) ends above 80; content starts at 82-84 (2d hero at 82)
CODE = re.compile(r"^(\d)([a-z]?) · (.+)$")    # "5c · What Changed" -> ("5", "c", "What Changed")


def _top(pg):
    return [v for v in pg.visuals if not v.get("parentGroupName")]


def _sec(pg, num):
    name = pbir.uid(pg.id, f"sec{num}", "textbox")
    return next((v for v in pg.visuals if v["name"] == name), None)


def _renumber(vc, old, new):
    run = vc["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
    if not run["value"].startswith(old):
        raise ValueError(f"section label {run['value']!r} does not start with {old!r}")
    run["value"] = new + run["value"][len(old):]


def act_first(pg):
    import pages as P
    s2, s3, s4 = (_sec(pg, k) for k in (2, 3, 4))
    if not (s2 and s3 and s4 and s2["position"]["y"] == P.Y2 and s3["position"]["y"] == P.Y3
            and s4["position"]["y"] == P.Y4):
        return False
    gap = P.Y3 - (P.Y2V + P.H2)                                   # 16 px between a band and the next section label
    len2, len4 = P.Y2V + P.H2 - P.Y2, P.Y4V + P.H4 - P.Y4         # band heights including their section label
    new2 = P.Y2 + len4 + gap                                      # old ② starts after the moved register
    new3 = new2 + len2 + gap
    moves = [(P.Y4, P.YNEXT, P.Y2 - P.Y4), (P.Y2, P.Y3, new2 - P.Y2), (P.Y3, P.Y4, new3 - P.Y3)]
    for vc in _top(pg):
        y = vc["position"]["y"]
        for lo, hi, d in moves:
            if lo <= y < hi:
                vc["position"]["y"] = y + d
                break
    c = P.CIRCLED
    _renumber(s4, c[3], c[1])
    _renumber(s2, c[1], c[2])
    _renumber(s3, c[2], c[3])
    return True


def _code(display):
    m = CODE.match(display)
    return m.groups() if m else None


def chapter_of(key):
    """-> (chapter key, page keys of that chapter in story order); (None, []) for Home."""
    import pages as P
    c = _code(dict(P.PAGES)[key])
    if not c:
        return None, []
    members = [k for k, d in P.PAGES if _code(d) and _code(d)[0] == c[0]]
    return members[0], members


def _label(display):
    num, letter, name = _code(display)
    return f"{num}{letter} {name}"


# Bold Segoe UI 10 pt (13.33 px) glyph widths in px, measured from segoeuib.ttf. A per-character average (the old
# 7.3 px) made short labels too narrow: "Home" wrapped inside its 61 px button and pushed the trail out of line.
BOLD10_PX = {'a': 7.17, 'b': 8.27, 'c': 6.40, 'd': 8.25, 'e': 7.21, 'f': 5.11, 'g': 8.25, 'h': 8.03, 'i': 3.79,
             'j': 3.79, 'k': 7.45, 'l': 3.79, 'm': 12.21, 'n': 8.07, 'o': 8.15, 'p': 8.27, 'q': 8.25, 'r': 5.31,
             's': 5.87, 't': 5.19, 'u': 8.07, 'v': 7.23, 'w': 10.63, 'x': 7.36, 'y': 7.17, 'z': 6.39, 'A': 9.37,
             'B': 8.55, 'C': 8.32, 'D': 9.83, 'E': 7.09, 'F': 6.93, 'G': 9.48, 'H': 10.21, 'I': 4.23, 'J': 5.93,
             'K': 8.65, 'L': 6.81, 'M': 12.76, 'N': 10.53, 'O': 10.11, 'P': 8.19, 'Q': 10.11, 'R': 8.71, 'S': 7.48,
             'T': 7.81, 'U': 9.64, 'V': 8.89, 'W': 13.40, 'X': 8.73, 'Y': 8.09, 'Z': 8.09, ' ': 3.68, '&': 11.33,
             ',': 3.61, '-': 5.39, "'": 3.91, **{d: 7.67 for d in "0123456789"}}
WIDE_PX = 13.4       # a glyph not in the table counts as the widest one ("W"), so a new label never wraps
PAD_X = 12           # text margin on each side of every nav button (crumbs and chapter strip)
SLACK = 10           # Desktop renders a little wider than the font metrics: never let a label wrap
SEP_W = 16           # the "›" between crumbs


def _w(text):
    """Nav button width: the measured text, PAD_X on both sides and SLACK."""
    return math.ceil(sum(BOLD10_PX.get(c, WIDE_PX) for c in text)) + 2 * PAD_X + SLACK


def _alt(btn, text):
    """Alt text on a button (a11y.apply keeps an existing altText)."""
    btn["visualContainerObjects"].setdefault("general", [{"properties": {}}])[0]["properties"]["altText"] = pbir.s(text)
    return btn


def _pad(btn, pad=PAD_X):
    """Same text margin left and right, so a centred label sits in the middle of its button."""
    btn["objects"]["text"][1]["properties"].update(leftMargin=pbir.n(pad), rightMargin=pbir.n(pad))
    return btn


def _crumb(text, target, tip):
    return _alt(_pad(pbir.nav_button(text, target, tip, fill="#FFFFFF", hover=pbir.ORANGE_SOFT,
                                     press=pbir.ORANGE_SOFT, font=pbir.NAVY, size=10)), f"Breadcrumb: {text}")


def _still(text, colour, size, bold=True, pad=PAD_X):
    """A button without an action or fill. The separator and the current page use it instead of a text box: a button
    centres its text vertically, a text box puts it at the top, so the trail would not line up."""
    btn = _pad(pbir.nav_button(text, "", fill="#FFFFFF", font=colour, size=size), pad)
    del btn["visualContainerObjects"]["visualLink"]
    btn["objects"]["fill"] = [{"properties": {"show": pbir.b(False)}}]
    btn["objects"]["text"][1]["properties"]["bold"] = pbir.b(bold)
    return btn


def nav_row(pg, key):
    import pages as P
    if pbir.uid(pg.id, "nav_home", "actionButton") in {v["name"] for v in pg.visuals}:
        return
    own = {pbir.uid(pg.id, k, "actionButton") for k in ("next", "back")}
    foot = min((v["position"]["y"] for v in _top(pg) if v["name"] in own), default=None)
    if foot is None:                                 # no Next/Back row: fall back to "buttons low on the page"
        foot = min((v["position"]["y"] for v in _top(pg) if v["visual"]["visualType"] == "actionButton"
                    and v["position"]["y"] >= FOOTER_FALLBACK_Y), default=P.YNEXT)
    for vc in _top(pg):                              # room for the row: everything between header and Next/Back
        y = vc["position"]["y"]
        if HEADER_BOTTOM <= y < foot:
            vc["position"]["y"] = y + NAV_SHIFT
    limit = foot - 8
    for vc in _top(pg):                              # nothing may run into this page's Next/Back row
        p = vc["position"]
        if p["y"] < foot and p["y"] + p["height"] > limit:
            new_h = limit - p["y"]
            if new_h < 0.6 * p["height"]:
                raise ValueError(f"{pg.display}: {vc['name']} would lose more than 40% of its height")
            p["height"] = new_h
    names = dict(P.PAGES)
    chap, members = chapter_of(key)
    x = 16
    pg.add(x, NAV_Y, _w("Home"), NAV_H, _crumb("Home", P.PID["home"], "Back to the command center"), key="nav_home")
    x += _w("Home")
    trail = ([(chap, True)] if chap != key else []) + [(key, False)]
    for k, link in trail:
        pg.add(x, NAV_Y, SEP_W, NAV_H, _still("›", pbir.MUTED, 11, bold=False, pad=0), key=f"nav_sep_{k}")
        x += SEP_W
        text = _label(names[k])
        if link:
            pg.add(x, NAV_Y, _w(text), NAV_H, _crumb(text, P.PID[k], "Open this chapter"), key=f"nav_crumb_{k}")
        else:
            pg.add(x, NAV_Y, _w(text), NAV_H, _alt(_still(text, pbir.NAVY, 10), f"You are here: {text}"),
                   key=f"nav_here_{k}")
        x += _w(text)
    if len(members) > 1:
        widths = [_w(_label(names[m])) for m in members]
        x = P.W - 16 - sum(widths) - 6 * (len(members) - 1)
        for m, w in zip(members, widths):
            cur = m == key
            btn = pbir.nav_button(_label(names[m]), P.PID[m], "You are here" if cur else "Open this page",
                                  fill=pbir.ORANGE if cur else "#FFFFFF",
                                  hover=pbir.ORANGE_DK if cur else pbir.ORANGE_SOFT,
                                  press=pbir.ORANGE_DK if cur else pbir.ORANGE_SOFT,
                                  font="#FFFFFF" if cur else pbir.NAVY, size=10,
                                  outline=None if cur else pbir.BORDER)
            _pad(btn)
            if cur:
                _alt(btn, f"{_label(names[m])} (current page)")
            pg.add(x, NAV_Y, w, NAV_H, btn, key=f"nav_strip_{m}")
            x += w + 6


def hide_deep_dives(built):
    import pages as P
    for k, d in P.PAGES:
        c = _code(d)
        if c and c[1] and k in built:
            built[k].page["visibility"] = "HiddenInViewMode"
