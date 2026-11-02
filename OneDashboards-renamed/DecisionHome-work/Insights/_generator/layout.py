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
HEADER_BOTTOM = 84
CODE = re.compile(r"^(\d)([a-z]?) · (.+)$")    # "5c · What Changed" -> ("5", "c", "What Changed")


def _top(pg):
    return [v for v in pg.visuals if not v.get("parentGroupName")]


def _sec(pg, num):
    name = pbir.uid(pg.id, f"sec{num}", "textbox")
    return next((v for v in pg.visuals if v["name"] == name), None)


def _renumber(vc, old, new):
    run = vc["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
    assert run["value"].startswith(old), run["value"]
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
