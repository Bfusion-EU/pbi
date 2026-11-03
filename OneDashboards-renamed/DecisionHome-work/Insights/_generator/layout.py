"""Layout passes on the built pages (run by pages.build_all after the filter/tooltip passes, before a11y).

act_first(pg)        — standard chapter page: the list to act on (section ④) moves up to ②, the trend (②) to ③ and
                       the drivers (③) to ④, so the list is visible without scrolling. False = page left as it is.
nav_row(pg, key)     — 30 px row under the header: breadcrumb left, chapter strip right (chapters with deep-dives).
hide_deep_dives(...) — deep-dive pages ("5c · …") leave the tab bar; buttons and drill-through still reach them.
Spec: BFusion-Apps docs/superpowers/specs/2026-11-02-insights-navigation-design.md
"""
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


def _w(text):
    return round(len(text) * 7.3 + 32)               # bold Segoe UI 10 pt button: ~7.3 px per character + margins


def _crumb_text(text, colour, bold=True, size=10):
    """A breadcrumb level with no action (separator, current page): a button, so it lines up with the links."""
    btn = pbir.nav_button(text, "", "", fill="#FFFFFF", hover="#FFFFFF", press="#FFFFFF", font=colour, size=size,
                          margin=0)
    btn["objects"]["text"][1]["properties"]["bold"] = pbir.b(bold)
    btn["visualContainerObjects"].pop("visualLink")
    return btn


def _alt(btn, text):
    """Alt text on a button (a11y.apply keeps an existing altText)."""
    btn["visualContainerObjects"].setdefault("general", [{"properties": {}}])[0]["properties"]["altText"] = pbir.s(text)
    return btn


def _crumb(text, target, tip):
    return _alt(pbir.nav_button(text, target, tip, fill="#FFFFFF", hover=pbir.ORANGE_SOFT, press=pbir.ORANGE_SOFT,
                                font=pbir.NAVY, size=10), f"Breadcrumb: {text}")


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
    pg.add(x, NAV_Y, _w("Command center"), NAV_H, _crumb("Command center", P.PID["home"], "Open the command center"),
           key="nav_home")
    x += _w("Command center")
    trail = ([(chap, True)] if chap != key else []) + [(key, False)]
    for k, link in trail:
        # every level is a button: Desktop centres button text, so the levels sit on one line (a text box would not)
        pg.add(x, NAV_Y, 18, NAV_H, _crumb_text("›", pbir.MUTED, bold=False, size=12), key=f"nav_sep_{k}")
        x += 18
        text = _label(names[k])
        if link:
            pg.add(x, NAV_Y, _w(text), NAV_H, _crumb(text, P.PID[k], "Open this chapter"), key=f"nav_crumb_{k}")
        else:
            pg.add(x, NAV_Y, _w(text), NAV_H, _alt(_crumb_text(text, pbir.NAVY), f"You are here: {text}"),
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
