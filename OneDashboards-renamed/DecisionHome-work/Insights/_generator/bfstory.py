"""Build 'OneDashboards - Bfusion Story': the BFusion custom-visual pack restructured as a story.

    python bfstory.py                    # writes ../../Story/Bfusion Story.pbip + .Report (the full story)
    python bfstory.py --role pmo         # one role report (roles.py): Story PPM / Modeller / PM / Resources / PMO
    python bfstory.py --check            # build + validate JSON schemas, model references, layout and links
    python story_all.py --check          # full story + the five role reports + Story Launcher, each in its own process

Same story grammar and navigation as the Insights pack (header AREA | QUESTION? -> orange headline -> ① pulse ->
② list to act on -> ③ / ④ the picture and the drivers -> Next chapter), but the pictures are the BFusion custom
visuals taken from 'OneDashboards - Bfusion' (bindings and Format-pane settings copied as they are), next to the
native KPI cards, registers and headlines of the Insights pack (same measures, so one definition per number).
The source pack is read only; it is never written.
"""
import copy
from dataclasses import dataclass
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402  (registers the Insights story measures)
import pbir  # noqa: E402
import pages  # noqa: E402
import layout  # noqa: E402
import a11y  # noqa: E402
import polish  # noqa: E402
import consistency  # noqa: E402
import chrome  # noqa: E402
import confidence  # noqa: E402
import story_measures  # noqa: E402
import entry  # noqa: E402
import roles  # noqa: E402
import app_links  # noqa: E402
from entry import (back_button, home_button, _crumb_w, _crumb_label, build_welcome, build_questions,  # noqa: E402
                   build_brief, BRIEF_TAKEAWAYS)
from pbir import (Page, P, M, C, s, b, uid, st, textbox, shape, nav_button, slicer, headline,  # noqa: E402
                  NAVY, NAVY_BTN, ORANGE, ORANGE_DK, ORANGE_SOFT, BORDER, MUTED)
from pbir import card, chart, table_style, cf_font  # noqa: E402
from story_measures import ACTIVE_STATE  # noqa: E402

# Short on purpose: Desktop cannot read files over 259 characters, and the longest custom visual file adds
# ~170 characters below the .Report folder (path_errors checks this).
NAME = "Bfusion Story"
OUT_DIR = build.ROOT.parent / "Story"
MAX_PATH = 259
OUT = OUT_DIR / f"{NAME}.Report"
SRC = build.REF                      # OneDashboards - Bfusion.Report (read only)

# 16:9 screens: 1800 x 1058 of content, 1880 x 1058 once chrome.py adds the 80 px chapter rail. A chapter or deep
# dive whose sections do not fit on one screen continues on hidden pages "(2/2)", reached with Continue / Previous.
W, H = 1800, 1058
BG = pages.BG_TALL                   # chrome.py swaps in the 16:9 footer band of the widened page
LIMIT = 958                          # top of the footer band of the 16:9 background (orange rule at ~963)
NAV_Y, NAV_H = 86, 30
Y_HEAD = 122                         # orange headline under the navigation row
Y_BODY = 226                         # first section label, under the filter-context bar
Y_BAR = 182                          # filter-context bar (chrome.py) between headline and body
Y_NEXT = LIMIT - 48                  # Next / Back row
BODY_END = Y_NEXT - 12
GAP = 14
SEC_H = 36                           # section label above every band

DP, DR = pages.DP, pages.DR
STD = pages.STD_SLICERS
PROJ = pages.PROJ_SLICERS
CAT = ("src", "Capacity & Utilization", "Category.Category")
GRAIN = ("src", "Capacity & Utilization", "Period Grain.Period Grain")
RES = [(DR("Department_Value"), "Department"), (DR("Role_Value"), "Role"), (C("DimDate", "Year"), "Year")]

PAGES = [  # (key, display) — story order; "Next" follows this list. "Nx" codes are deep-dives (hidden tabs).
    ("welcome", "Welcome"),
    ("home", "Home — Decision center"),
    ("questions", "Questions — where to start"),
    ("brief_exec", "Brief · Executive Summary"),
    ("exec", "1 · Executive Summary"),
    ("health", "1b · Portfolio 360 & Health"),
    ("roadmap", "1c · Roadmap & Delivery"),
    ("drift", "1d · Portfolio Drift"),
    ("kpigrid", "1e · Project KPI Grid"),
    ("brief_portfolio", "Brief · Portfolio"),
    ("portfolio", "2 · Portfolio"),
    ("selection", "2b · Selection & Funding Line"),
    ("scenarios", "2c · Scenarios & Trade-offs"),
    ("constraints", "2d · Constraints & Sequencing"),
    ("brief_finance", "Brief · Financials"),
    ("finance", "3 · Financials"),
    ("fintree", "3b · Variance Drivers"),
    ("budgetrisk", "3c · Budget Risk & Early Warning"),
    ("brief_resources", "Brief · Resources"),
    ("resources", "4 · Resources"),
    ("fte", "4b · FTE Decisions & Efficiency"),
    ("org", "4c · Organisation & Gaps"),
    ("timesheets", "4d · Timesheets vs Plan"),
    ("mywork", "4e · My Work"),
    ("brief_schedule", "Brief · Schedule"),
    ("schedule", "5 · Schedule"),
    ("critical", "5b · Critical Path & Chain"),
    ("psr", "5c · Project Status Report"),
    ("brief_risk", "Brief · Risk"),
    ("risk", "6 · Risk"),
    ("brief_benefits", "Brief · Benefits & Value"),
    ("benefits", "7 · Benefits & Value"),
    ("brief_governance", "Brief · Governance & Data Trust"),
    ("governance", "8 · Governance & Data Trust"),
    ("recon", "8b · Reconciliation"),
]
NAMES = dict(PAGES)
PID = {k: uid("bfstory-page", k) for k, _ in PAGES}
ORDER = [k for k, _ in PAGES]
CHAPTERS = [k for k, d in PAGES if layout._code(d) and not layout._code(d)[1]]
FULL_PAGES = list(PAGES)             # the full pack's pages; a role report renumbers a subset of them
ROLE = None                          # roles.Role while building a role report
HUB_KEY, HUB_LABEL = "home", "Decision center"   # where breadcrumbs and "Back" go; "questions" in most role reports


def apply_role(role):
    """Rebind the page globals to one role report. Call once, before build_pages(), in a fresh process."""
    global NAME, PAGES, NAMES, PID, ORDER, CHAPTERS, ROLE, HUB_KEY, HUB_LABEL
    ROLE = role
    NAME = role.report
    PAGES = roles.role_pages(role, dict(FULL_PAGES))
    NAMES = dict(PAGES)
    PID = {k: uid("bfstory-page", k) for k, _ in PAGES}
    ORDER = [k for k, _ in PAGES]
    CHAPTERS = [k for k, d in PAGES if layout._code(d) and not layout._code(d)[1]]
    HUB_KEY, HUB_LABEL = ("home", "Decision center") if role.home else ("questions", "Questions")


# ================================================================ source pack (custom visuals)
_SRC_PAGES = None


def _src_pages():
    global _SRC_PAGES
    if _SRC_PAGES is None:
        root = SRC / "definition" / "pages"
        order = json.loads((root / "pages.json").read_text(encoding="utf-8"))["pageOrder"]
        _SRC_PAGES = {}
        for pid in order:
            meta = json.loads((root / pid / "page.json").read_text(encoding="utf-8"))
            disp = meta["displayName"]
            assert disp not in _SRC_PAGES, f"duplicate source page name {disp!r}"
            vcs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((root / pid / "visuals").glob("*/visual.json"))]
            # page filters (not drill-through) travel with each copied visual as visual filters, because one story
            # page takes visuals from several source pages
            pflt = [f for f in meta.get("filterConfig", {}).get("filters", []) if f.get("howCreated") != "Drillthrough"]
            for vc in vcs:
                vc["_src_page"] = disp
                if pflt:
                    own = vc.setdefault("filterConfig", {"filters": []})["filters"]
                    names = {f["name"] for f in own}
                    own.extend(copy.deepcopy(f) for f in pflt if f["name"] not in names)
            _SRC_PAGES[disp] = sorted(vcs, key=lambda v: (v["position"]["y"], v["position"]["x"]))
            _SRC_INTERACTIONS[disp] = meta.get("visualInteractions", [])
    return _SRC_PAGES


_SRC_INTERACTIONS = {}
STALE = {"bfusionKpiTicker"}           # source visual filters pinned to one month (DimDate.Period 'Jul-26'): dropped


def src(page, vtype):
    """Deep copy of the one visual container of this type on a source page; vtype may be a prefix."""
    hits = [vc for vc in _src_pages()[page] if vc.get("visual", {}).get("visualType", "").startswith(vtype)]
    if len(hits) != 1:
        raise KeyError(f"{vtype}: {len(hits)} matches on source page {page!r} (need exactly 1)")
    vc = copy.deepcopy(hits[0])
    if any(vtype.startswith(p) for p in STALE):
        vc.pop("filterConfig", None)
    vc["visual"].get("objects", {}).pop("bookmarkState", None)   # saved Org-chart expansion: stale names
    return vc


def _slicer_field(vc):
    return vc["visual"]["query"]["queryState"]["Values"]["projections"][0]["field"]


def src_slicer(page, ref):
    for vc in _src_pages()[page]:
        v = vc.get("visual", {})
        if v.get("visualType") != "slicer":
            continue
        col = _slicer_field(vc).get("Column", {})
        if f'{col.get("Expression", {}).get("SourceRef", {}).get("Entity")}.{col.get("Property")}' == ref:
            vc = copy.deepcopy(vc)
            vc["visual"].setdefault("syncGroup", {"groupName": ref, "fieldChanges": True, "filterChanges": True})
            return vc
    raise KeyError(f"slicer {ref} not on source page {page!r}")


def _custom_name(vtype):
    import re
    base = re.sub(r"(_CustomVisual|_?[0-9A-Fa-f]{8,}.*|[A-Z0-9]{8,}.*)$", "", vtype.replace("bfusion", ""))
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base).strip()


# ================================================================ Insights pack (native story visuals)
_INS = {}


def insights(key):
    """The Insights chapter page with that key, laid out act-first as in the Insights pack (built once)."""
    if key not in _INS:
        if key == "timesheets":
            import ext_timesheets
            pg = ext_timesheets.build()[0]
        else:
            pg = getattr(pages, f"build_{key}")()
        layout.act_first(pg)
        _INS[key] = pg
    return _INS[key]


def grab(ins_key, key):
    pg = insights(ins_key)
    for vc in pg.visuals:
        v = vc.get("visual", {})
        if vc["name"] == uid(pg.id, key, v.get("visualType")):
            return copy.deepcopy(vc)
    raise KeyError(f"{key} not on Insights page {ins_key}")


def kpis(ins_key):
    """The ① KPI cards of an Insights chapter (same measures, labels and colour rules)."""
    pg = insights(ins_key)
    out, k = [], 0
    while True:
        name = uid(pg.id, f"kpi{pages.Y1K}_{k}", "card")
        vc = next((v for v in pg.visuals if v["name"] == name), None)
        if vc is None:
            return out
        out.append(copy.deepcopy(vc))
        k += 1


# ================================================================ page frame
def put(pg, x, y, w, h, vc, key):
    """Place a copied visual container (source or Insights) on a page at a new position."""
    v = vc["visual"]
    flt = vc.get("filterConfig", {}).get("filters")
    out = pg.add(round(x, 2), round(y, 2), round(w, 2), round(h, 2), v, filters=copy.deepcopy(flt) if flt else None,
                 key=key)
    if "_src_page" in vc:                               # remember source name -> new name for visualInteractions
        pg.__dict__.setdefault("src_names", {})[(vc["_src_page"], vc["name"])] = out["name"]
    t = v.get("visualType", "")
    if t.startswith(("bfusion", "portfolioRoadmap")):
        gen = v.setdefault("visualContainerObjects", {}).setdefault("general", [{"properties": {}}])
        gen[0].setdefault("properties", {}).setdefault("altText", s(f"BFusion {_custom_name(t)} visual"))
    return out


def header(pg, key, area, question, subtitle, slicers):
    pg.add(0, 4, 60, 58, back_button(), key="go_back")       # not "back": next_back() uses that key at the foot
    home_button(pg, 64, 13)
    tsize = 24 if len(f"{area} | {question}") <= pages.TITLE_MAX else 20
    pg.add(116, 8, 906, 46, textbox([[(f"{area} | ", st("DIN", tsize, ORANGE, True)),
                                       (question, st("DIN", tsize, NAVY, True))]]), key="title")
    ssize = pages.subtitle_size(subtitle)
    pg.add(116, 52, 906, pages.SUBTITLE_H, textbox([[(subtitle, st("Segoe UI", ssize, MUTED))]]), key="subtitle")
    x = W - 16 - len(slicers) * 188 + 8
    assert x >= 1030, f"{pg.display}: too many slicers ({len(slicers)})"
    for k, sl in enumerate(slicers):
        if sl[0] == "src":
            vc = src_slicer(sl[1], sl[2])
            put(pg, x + k * 188, 10, 180, 62, vc, f"slicer{k}")
        else:
            pg.add(x + k * 188, 10, 180, 62, slicer(sl[0], sl[1]), key=f"slicer{k}")


def nav_row(pg, key):
    """Breadcrumb (Home › chapter › page) left, chapter strip right — same look as the Insights pack."""
    c = layout._code(NAMES[key])
    members = [k for k, d in PAGES if layout._code(d) and layout._code(d)[0] == c[0]]
    chap = members[0]
    x = 16
    pg.add(x, NAV_Y, _crumb_w(HUB_LABEL), NAV_H,
           layout._crumb(HUB_LABEL, PID[HUB_KEY], f"Open the {HUB_LABEL.lower()}"), key="nav_home")
    x += _crumb_w(HUB_LABEL)
    for k, link in ([(chap, True)] if chap != key else []) + [(key, False)]:
        pg.add(x, NAV_Y, 18, NAV_H, _crumb_label("›", MUTED, bold=False, size=12), key=f"nav_sep_{k}")
        x += 18
        text = layout._label(NAMES[k])
        if link:
            pg.add(x, NAV_Y, _crumb_w(text), NAV_H, layout._crumb(text, PID[k], "Open this chapter"), key=f"nav_crumb_{k}")
        else:
            pg.add(x, NAV_Y, _crumb_w(text), NAV_H, layout._alt(_crumb_label(text, NAVY), f"You are here: {text}"),
                   key=f"nav_here_{k}")
        x += _crumb_w(text)
    if len(members) > 1:
        size, widths, x = layout.strip_layout([layout._label(NAMES[m]) for m in members], x, W - 16)
        for m, w in zip(members, widths):
            cur = m == key
            btn = nav_button(layout._label(NAMES[m]), PID[m], "You are here" if cur else "Open this page",
                             fill=ORANGE if cur else "#FFFFFF", hover=ORANGE_DK if cur else ORANGE_SOFT,
                             press=ORANGE_DK if cur else ORANGE_SOFT, font="#FFFFFF" if cur else NAVY, size=size,
                             outline=None if cur else BORDER)
            if cur:
                layout._alt(btn, f"{layout._label(NAMES[m])} (current page)")
            pg.add(x, NAV_Y, w, NAV_H, btn, key=f"nav_strip_{m}")
            x += w + 6


def page_id(key, page):
    return PID[key] if page == 1 else uid("bfstory-page", key, f"p{page}")


KEY_OF = {}                          # page id -> story key, continuation pages included (chrome.py)


def next_back(pg, key, page=1, of=1):
    if of > 1:
        pg.add(W / 2 - 120, Y_NEXT, 240, 36, textbox([[(f"Page {page} of {of}", st("Segoe UI", 11, MUTED))]],
                                                     align="center"), key="pager")
    back = (page_id(key, page - 1), f"‹  Page {page - 1} of {of}", "Back to the previous screen of this page")         if page > 1 else (PID[HUB_KEY], f"‹  {HUB_LABEL}", "Back to the home page")
    pg.add(16, Y_NEXT, 220, 36, nav_button(back[1], back[0], back[2], fill="#FFFFFF", hover=ORANGE_SOFT, press=ORANGE,
                                           font=NAVY, outline=BORDER), key="back")
    if page < of:
        pg.add(W - 16 - 360, Y_NEXT, 360, 36, nav_button(f"Continue: page {page + 1} of {of}  ›", page_id(key, page + 1),
                                                         "Continue on the next screen"), key="next")
    else:
        _story_next(pg, key)


def _story_next(pg, key):
    idx = ORDER.index(key)
    if idx + 1 < len(ORDER):
        nxt = ORDER[idx + 1]
        label = NAMES[nxt].split("·", 1)[-1].strip()
        text = f"Next: {label}  ›"
        pg.add(W - 16 - 360, Y_NEXT, 360, 36,
               nav_button(text, PID[nxt], "Continue the story on the next page",
                          size=pbir.fit_size(text, 360, (11, 10, 9))), key="next")


QUESTIONS = {}                       # page key -> its header question, for the Questions page


def story_page(key, area, question, subtitle, slicers, headline_vc, page=1, of=1):
    QUESTIONS[key] = question
    pid = page_id(key, page)
    KEY_OF[pid] = key
    pg = Page(pid, NAMES[key] if page == 1 else f"{NAMES[key]} ({page}/{of})", W, H, background_image=BG)
    if page > 1:
        pg.page["visibility"] = "HiddenInViewMode"
    headline_vc = copy.deepcopy(headline_vc)
    header(pg, key, area, question, subtitle, slicers)
    nav_row(pg, key)
    put(pg, 16, Y_HEAD, 1768, 56, headline_vc, "headline")
    return pg


def head(measure):
    return {"visual": headline(measure)}


# ---------------------------------------------------------------- bands
# item: ("src", source page, visual type) | ("ins", insights page key, visual key) | callable(pg, x, y, w, h)
def band(pg, y, num, question, explain, h, items, weights=None):
    pages.section(pg, y, num, question, explain)
    weights = weights or [1] * len(items)
    gap = 12
    free = 1768 - gap * (len(items) - 1)
    x = 16
    for k, (it, wt) in enumerate(zip(items, weights)):
        w = free * wt / sum(weights)
        vy = y + SEC_H
        if callable(it):
            it(pg, x, vy, w, h)
        elif it[0] == "src":
            put(pg, x, vy, w, h, src(it[1], it[2]), f"b{num}_{k}")
        else:
            put(pg, x, vy, w, h, grab(it[1], it[2]), f"b{num}_{k}")
        x += w + gap
    return y + SEC_H + h + GAP


def pulse(pg, y, ins_key, question, explain):
    pages.section(pg, y, 1, question, explain)
    cards = kpis(ins_key)
    n = len(cards)
    w = (1768 - 10 * (n - 1)) / n
    for k, vc in enumerate(cards):
        put(pg, 16 + k * (w + 10), y + SEC_H, w, pages.KPI_H, vc, f"kpi_{k}")
    return y + SEC_H + pages.KPI_H + GAP


def bands(pg, y, spec, first=1):
    """spec: [(question, explain, height, items[, weights])]. Heights are relative: the bands are scaled so the
    page fills down to the Next row exactly."""
    free = BODY_END - y - len(spec) * (SEC_H + GAP) + GAP
    scale = free / sum(b_[2] for b_ in spec)
    for k, b_ in enumerate(spec):
        q, e, h, items = b_[:4]
        y = band(pg, y, first + k, q, e, int(h * scale), items, b_[4] if len(b_) > 4 else None)
    if y - GAP > BODY_END:
        raise ValueError(f"{pg.display}: content ends at {y - GAP}, below {BODY_END}")
    return y


SHRINK = 0.70                        # a band may drop to 70% of its designed height before it moves to the next screen
PULSE_H = SEC_H + pages.KPI_H + GAP     # the pulse row: pbir.kpi_h() tall cards (was 90 before the type bump)


def pack(spec, first_free):
    """Split the bands over 16:9 screens, in order: a band goes to the next screen once it would have to shrink below
    SHRINK. A band taller than a screen (the 1340 px single-visual deep dives) gets a screen to itself and is scaled to
    fill it, below SHRINK on purpose."""
    free = BODY_END - Y_BODY + GAP
    out, cur, used, cap = [], [], 0, first_free
    for b_ in spec:
        need = SEC_H + GAP + b_[2] * SHRINK
        if cur and used + need > cap:
            out.append(cur)
            cur, used, cap = [], 0, free
        cur.append(b_)
        used += need
    out.append(cur)
    return out


def chapter(key, area, question, subtitle, slicers, ins_key, pulse_q, spec, headline_measure=None):
    hv = head(headline_measure) if headline_measure else grab(ins_key, "headline")
    screens = pack(spec, BODY_END - Y_BODY + GAP - PULSE_H)
    out, num = [], 2
    for i, grp in enumerate(screens, 1):
        pg = story_page(key, area, question, subtitle, slicers, hv, i, len(screens))
        y = pulse(pg, Y_BODY, ins_key, *pulse_q) if i == 1 else Y_BODY
        bands(pg, y, grp, first=num)
        num += len(grp)
        next_back(pg, key, i, len(screens))
        out.append(pg)
    return out


def deep_dive(key, area, question, subtitle, slicers, headline_measure, spec):
    screens = pack(spec, BODY_END - Y_BODY + GAP)
    out, num = [], 1
    for i, grp in enumerate(screens, 1):
        pg = story_page(key, area, question, subtitle, slicers, head(headline_measure), i, len(screens))
        bands(pg, Y_BODY, grp, first=num)
        num += len(grp)
        next_back(pg, key, i, len(screens))
        pg.page["visibility"] = "HiddenInViewMode"
        out.append(pg)
    return out


# ================================================================ HOME
CARD_TEXT = {  # chapter -> (question, headline measure)
    "exec": ("Are we on course?", "Story | Exec Headline"),
    "portfolio": ("Are we funding the right work?", "Story | Portfolio Headline"),
    "finance": ("Are we spending as planned?", "Story | Finance Headline"),
    "resources": ("Do we have the people?", "Story | Resource Headline"),
    "schedule": ("Will we deliver on time?", "Story | Schedule Headline"),
    "risk": ("What could go wrong?", "Story | Risk Headline"),
    "benefits": ("Will it pay off?", "Story | Benefits Headline"),
    "governance": ("Can we trust the data?", "PMO | Governance Headline"),
    "selection": ("Which projects make the cut?", "Story | Portfolio Headline"),
    "scenarios": ("If we fund A instead of B, what do we gain?", "Story | Scenario · Headline"),
    "constraints": ("What holds the portfolio back?", "Story | Scenario · Headline"),
    "kpigrid": ("How does each project score?", "Story | Exec Headline"),
    "mywork": ("What is on my plate?", "Story | Schedule Headline"),
    "psr": ("Where does this project stand?", "Story | Status · Headline"),
    "timesheets": ("Are hours logged as planned?", "Story | Schedule Headline"),
}


# ---------------------------------------------------------------- KPI ticker = the command center's KPIs
# The ticker draws ▲/▼ from a "Compare to" measure paired by position with its value. Previous values come only
# from real history with the same definition as the current value:
#   plan-insight KPIs  -> latest SnapshotDate vs the snapshot before it (blank when only one snapshot exists)
#   budget / forecast  -> each project's latest status report as of this month end vs as of last month end,
#                         like-for-like (only projects that had a report last month), same rule as page 5c
#   timesheet hours    -> last full month vs the month before
# KPIs that are a current state with no history (late tasks, hours awaiting approval, unsubmitted status reports)
# go last, after the compared ones, so they show without an arrow.
TICKER = "Story\\Ticker"
_SNAP = "CALCULATE ( MAX ( FactPlanInsight[SnapshotDate] ) )"
_THIS_END = "[Story | Status · MoM This Month End]"


def _tk(name, expr, fmt, desc):
    full = f"Story | Ticker · {name}"
    story_measures.add(full, story_measures.D, expr, fmt, TICKER, desc)
    pbir.EXTENSION_MEASURES.add(full)
    return full


def _snapshot_pair(label, model_measure, fmt):
    now = _tk(f"{label} Now", f"VAR _s = {_SNAP}\nRETURN CALCULATE ( [{model_measure}], FactPlanInsight[SnapshotDate] = _s )",
              fmt, f"{model_measure} on the latest plan-insight snapshot.")
    prev = _tk(f"{label} Previous",
               f"VAR _s = {_SNAP}\n"
               "VAR _p = CALCULATE ( MAX ( FactPlanInsight[SnapshotDate] ), FactPlanInsight[SnapshotDate] < _s )\n"
               f"RETURN IF ( NOT ISBLANK ( _p ), CALCULATE ( [{model_measure}], FactPlanInsight[SnapshotDate] = _p ) )",
               fmt, f"{model_measure} on the plan-insight snapshot before the latest one; blank with one snapshot.")
    return now, prev


def _reported(col, months_back):
    """Sum over projects of FactStatusReport[col] in the latest report as of a month end, counting only projects
    that also had a report as of last month end (like-for-like, so new projects do not read as growth)."""
    return ("VAR _te = " + _THIS_END + "\n"
            "VAR _pe = EOMONTH ( _te, -1 )\n"
            f"VAR _at = EOMONTH ( _te, -{months_back} )\n"
            "RETURN SUMX (\n"
            "    FILTER ( VALUES ( DimProject[ProjectKey] ), NOT ISBLANK ( DimProject[ProjectKey] ) ),\n"
            "    VAR _p = CALCULATE ( MAX ( FactStatusReport[Report_ReportEnd] ), REMOVEFILTERS ( DimDate ), "
            "FactStatusReport[Report_ReportEnd] < _pe + 1, FactStatusReport[Report_ReportEnd] > DATE ( 1900, 1, 1 ) )\n"
            "    VAR _r = CALCULATE ( MAX ( FactStatusReport[Report_ReportEnd] ), REMOVEFILTERS ( DimDate ), "
            "FactStatusReport[Report_ReportEnd] < _at + 1, FactStatusReport[Report_ReportEnd] > DATE ( 1900, 1, 1 ) )\n"
            f"    RETURN IF ( NOT ISBLANK ( _p ), CALCULATE ( MAX ( FactStatusReport[{col}] ), REMOVEFILTERS ( DimDate ), "
            "FactStatusReport[Report_ReportEnd] = _r ) )\n)")


def _ts_hours(months_back):
    return (f"VAR _m = EOMONTH ( TODAY (), -{months_back} )\n"
            "RETURN CALCULATE ( [Timesheet | Hours], REMOVEFILTERS ( DimDate ), DimDate[Date] > EOMONTH ( _m, -1 ), "
            "DimDate[Date] <= _m )")


def _ticker_measures():
    """[(label, value measure, compare measure or None, polarity)] in ticker order."""
    gov = _snapshot_pair("Governance Score", "PMO | Governance Score", "0")
    comp = _snapshot_pair("Compliance %", "PMO | Compliance %", "0.0%")
    prob = _snapshot_pair("Problems", "PMO | Problems", "#,##0")
    warn = _snapshot_pair("Warnings", "PMO | Warnings", "#,##0")
    bud = (_tk("Reported Budget Now", _reported("Budget", 0), "#,##0", "Status-report budget, latest report as of "
               "this month end, like-for-like."),
           _tk("Reported Budget Previous", _reported("Budget", 1), "#,##0", "Same, as of last month end."))
    fc = (_tk("Reported Forecast Now", _reported("Forecast", 0), "#,##0", "Status-report forecast, latest report as of "
              "this month end, like-for-like."),
          _tk("Reported Forecast Previous", _reported("Forecast", 1), "#,##0", "Same, as of last month end."))
    ts = (_tk("Timesheet Hours Last Month", _ts_hours(1), "#,##0", "Timesheet hours in the last full month."),
          _tk("Timesheet Hours Month Before", _ts_hours(2), "#,##0", "Timesheet hours in the month before that."))
    return [("Governance score", *gov, "higherBetter"), ("Compliance", *comp, "higherBetter"),
            ("Problems", *prob, "lowerBetter"), ("Warnings", *warn, "lowerBetter"),
            ("Budget (reported)", *bud, "higherBetter"), ("Forecast (reported)", *fc, "lowerBetter"),
            ("Timesheet hours last month", *ts, "higherBetter"),
            ("Late tasks", "Task | Active Late Tasks", None, "lowerBetter"),
            ("Hours awaiting approval", "Timesheet | Awaiting Approval Hours", None, "lowerBetter"),
            # a count: PMO | Unsubmitted Status Reports is a text list of report dates and cannot be a KPI
            ("Plans with a status report not submitted", "Story | PMO · Plans With Open Status Report", None,
             "lowerBetter")]


_TICKER_ITEMS = None


def ticker():
    """The source KPI Ticker (look, license and settings kept), re-bound to the command center's KPIs."""
    global _TICKER_ITEMS
    if _TICKER_ITEMS is None:
        _TICKER_ITEMS = _ticker_measures()
    vc = src("Home — Decision View", "bfusionKpiTicker")
    v = vc["visual"]
    compared = [it for it in _TICKER_ITEMS if it[2]]
    v["query"] = {"queryState": {
        "values": {"projections": [P(M(it[1]), it[0]) for it in _TICKER_ITEMS]},
        "comparison": {"projections": [P(M(it[2]), f"{it[0]} (previous)") for it in compared]}}}
    v["objects"]["variance"] = ([{"properties": {"show": b(True), "polarity": s("higherBetter")}}]
                                + [{"properties": {"polarity": s(it[3])}, "selector": {"metadata": pbir.qref(M(it[1]))}}
                                   for it in _TICKER_ITEMS if it[3] != "higherBetter"])
    return vc


def _chip(text, target, tip):
    """Neutral chip: transparent, grey border, no orange (orange means a KPI state on Home)."""
    return nav_button(text, target, tip, fill="#FFFFFF", hover="#F3F4F6", press="#E5E7EB", font="#374151", size=10,
                      outline="#C9CED6")


WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}


def build_home():
    n = WORDS[len(CHAPTERS)]
    pg = Page(PID["home"], NAMES["home"], W, H, background_image=BG)
    KEY_OF[pg.id] = "home"
    header(pg, "home", "BFUSION", "DECISION CENTER",
           "Start with the pulse, act on the list, then open the chapter that answers your question.",
           [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"), (DP("State_Value"), "State")])
    put(pg, 16, 86, 1768, 72, ticker(), "ticker")
    put(pg, 16, 168, 1768, 56, grab("exec", "headline"), "headline")
    y = 236
    pages.section(pg, y, 1, "What needs attention now?",
                  "The PMO command center ranks projects by what needs a decision; click one to focus every page on it.")
    put(pg, 16, y + SEC_H, 1768, BODY_END - y - SEC_H, src("PMO | Command Center", "bfusionPMOCommandCenter"), "pmo")
    # 16:9: the eight question cards open over the command center (white backing), not below it
    # ② sits in a group that one toggle hides and shows (display-only bookmarks: slicer picks survive). The
    # "Hide" button lives inside the group, the "Show" button in its own group on the same spot, so exactly one
    # of the two is visible at any time.
    tw = max(190, *(pbir.button_w(t, 10) for t in (f"Show the {n} questions  ▼", "Hide the questions  ▲")))
    th = 30
    tx = 16 + 1768 - tw
    grp = pg.add_group(16, y, 1768, BODY_END - y, f"{n.capitalize()} questions", "questions", hidden=True)   # hidden by default
    grp_show = pg.add_group(tx, y + 2, tw, th, f"Show {n} questions", "questions_show")
    pg.add(16, y, 1768, BODY_END - y, shape("#FFFFFF"), key="q_backing", parent=grp)
    bm_hide = pbir.bookmark(f"Hide the {n} questions", "bfstory-questions-hide", pg.id, {grp: True, grp_show: False})
    bm_show = pbir.bookmark(f"Show the {n} questions", "bfstory-questions-show", pg.id, {grp: False, grp_show: True})
    pg.add(16, y, 1768 - tw - 12, SEC_H, textbox([[(f"{pages.CIRCLED[1]}  {n.capitalize()} questions, one answer each",
                                                     st("Segoe UI Semibold", 15, NAVY, True)),
                                                    ("   Each card is the headline of its chapter, written from the data "
                                                     "in the current filter.", st("Segoe UI", 11, MUTED))]]),
           key="sec2", parent=grp)
    toggle = dict(fill="#FFFFFF", hover="#F3F4F6", press="#E5E7EB", font="#374151", size=10, outline="#C9CED6")
    pg.add(tx, y + 2, tw, th, pbir.bookmark_button("Hide the questions  ▲", bm_hide, f"Hide the {n} chapter cards",
                                                   **toggle), key="q_hide", parent=grp)
    pg.add(tx, y + 2, tw, th, pbir.bookmark_button(f"Show the {n} questions  ▼", bm_show, f"Show the {n} chapter cards",
                                                   **toggle), key="q_show", parent=grp_show)
    y += SEC_H
    cols, gap = 4, 12
    cw = (1768 - gap * (cols - 1)) / cols
    ch = (BODY_END - y - gap) / 2
    for k, ck in enumerate(CHAPTERS):
        cx, cy = 16 + (k % cols) * (cw + gap), y + (k // cols) * (ch + gap)
        q, measure = CARD_TEXT[ck]
        pg.add(cx, cy, cw, ch, shape("#FFFFFF", radius=8, line=BORDER), key=f"card_bg{k}", parent=grp)
        code = layout._code(NAMES[ck])
        pg.add(cx + 12, cy + 10, cw - 24, 30, textbox([[(f"{code[0]} · {code[2].upper()}  ", st("DIN", 13, ORANGE, True)),
                                                         (q, st("Segoe UI Semibold", 12, NAVY, True))]]), key=f"card_t{k}",
               parent=grp)
        hl = headline(measure, bg="#FFFFFF", border="#FFFFFF", size=11)
        hl["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
        pg.add(cx + 8, cy + 44, cw - 16, ch - 44 - 50, hl, key=f"card_h{k}", parent=grp)
        deep = [m for m, d in PAGES if layout._code(d) and layout._code(d)[0] == code[0] and m != ck]
        bx, by = cx + 12, cy + ch - 44
        ow = max(120, pbir.button_w("Open chapter ›", 10))            # chips as wide as their text (type bump)
        pg.add(bx, by, ow, 32, _chip("Open chapter ›", PID[ck], f"Open {NAMES[ck]}"), key=f"card_open{k}", parent=grp)
        bx += ow + 8
        for m in deep:
            lbl = layout._code(NAMES[m])[0] + layout._code(NAMES[m])[1]
            dw = max(44, pbir.button_w(lbl, 10))
            if bx + dw > cx + cw - 8:
                break
            pg.add(bx, by, dw, 32, _chip(lbl, PID[m], NAMES[m]), key=f"card_deep{k}_{m}", parent=grp)
            bx += dw + 6
    return pg


# ================================================================ 1 EXECUTIVE
def _exec_where_next(pg, x, y, w, h):
    chaps = [k for k in CHAPTERS if k != "exec"]
    bw = (w - 10 * (len(chaps) - 1)) / len(chaps)
    size = pbir.fit_size([NAMES[ck] + "  ›" for ck in chaps], bw, (10, 9, 8))   # one size for the row
    for k, ck in enumerate(chaps):
        pg.add(round(x + k * (bw + 10), 2), y, round(bw, 2), 48,
               nav_button(NAMES[ck] + "  ›", PID[ck], "Open this chapter", fill=NAVY, hover=NAVY_BTN, press=ORANGE,
                          font="#FFFFFF", size=size), key=f"chap{k}")
    put(pg, x, y + 60, w, h - 60, grab("exec", "v_scorecard"), "v_scorecard")


def _exec_actions(pg, x, y, w, h):
    put(pg, x, y, w * 0.66, h, grab("exec", "v_attn"), "v_attn")
    ah = (h - 2 * 10) / 3
    for k in range(3):
        put(pg, x + w * 0.66 + 12, y + k * (ah + 10), w * 0.34 - 12, ah, grab("exec", f"act{k}"), f"act{k}")


def build_exec():
    return chapter("exec", "EXECUTIVE", "ARE WE ON COURSE?",
                   "Health, money, people and risk on one page — then the chapter that explains each number.",
                   STD, "exec", ("The pulse — one number per question",
                                 "Green is fine, amber needs a look, red needs a decision. Money is at completion."), [
        ("What needs a decision this month?", "Projects ranked by € overrun at completion, with the three actions the data points to.",
         340, [_exec_actions]),
        ("Where is the portfolio heading?", "Health of every project against its peers, and how status reports trend.",
         420, [("src", "Health Dashboard", "bfusionPortfolioHealthMatrix"),
               ("src", "Project Status Report (PSR)", "bfusionStatusTrendSparkline")], [2, 1]),
        ("Where should I look next?", "Each chapter answers one question in depth; the scorecard shows where to start.",
         380, [_exec_where_next]),
    ])


def build_health():
    return deep_dive("health", "PORTFOLIO 360", "HOW HEALTHY IS EACH PORTFOLIO?",
                     "Every dimension of health per portfolio, the summary KPIs behind it, and where health meets risk.",
                     [(DP("Portfolio Name"), "Portfolio"), (DP("BusinessUnit_Value"), "Business unit")],
                     "Story | Exec Headline", [
        ("Health on every dimension", "Schedule, cost, scope, resources and risk side by side.", 640,
         [("src", "360° Dashboard", "bfusionPortfolio360"), ("src", "Health Dashboard", "bfusionPortfolioSummaryKPI")],
         [1, 1.1]),
        ("Where do health and risk meet?", "Projects in the red corner of both are the board conversation.", 620,
         [("src", "Health Dashboard", "bfusionPortfolioHealthMatrix"), ("src", "Health Dashboard", "bfusionPortfolioRiskMatrix")],
         [1.5, 1]),
    ])


def build_roadmap():
    return deep_dive("roadmap", "ROADMAP", "WHAT LANDS WHEN, AND IS IT HEALTHY?",
                     "The portfolio roadmap by business unit and type, with delivery health and status-report trends.",
                     [(C("DimPortfolio", "BusinessUnit_Value"), "Business unit"),
                      (C("DimPortfolio", "ProjectType_Value"), "Project type")],
                     "Story | Schedule Headline", [
        ("What lands when?", "Bars are the planned window of each project; colour is health.", 720,
         [("src", "Roadmap", "portfolioRoadmap")]),
        ("Is delivery health improving?", "Health matrix of the delivery portfolio and the status-report trend.", 540,
         [("src", "Roadmap", "bfusionPortfolioHealthMatrix"), ("src", "PMO Delivery", "bfusionStatusTrendSparkline")],
         [1.6, 1]),
    ])


def build_drift():
    return deep_dive("drift", "TIME-LAPSE", "HOW HAS THE PORTFOLIO DRIFTED?",
                     "Replay the portfolio month by month: who moved, how far, and in which direction.",
                     [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program")],
                     "Story | Status · MoM Headline", [
        ("Drift over time", "Press play; trails show each project's path between status reports.", 1340,
         [("src", "TimeLaps", "bfusionPortfolioDrift")]),
    ])


def build_kpigrid():
    return deep_dive("kpigrid", "KPI GRID", "HOW DOES EACH PROJECT SCORE?",
                     "Every project KPI in one grid with conditional colouring; sort any column to find the outliers.",
                     [("src", "KPI Grid", "DimProject.PlanType"), (DP("Portfolio Name"), "Portfolio"),
                      ("src", "KPI Grid", "DimProject.EstimatedStart"), ("src", "KPI Grid", "DimProject.EstimatedEnd")],
                     "Story | Exec Headline", [
        ("Project scorecard", "One row per project; red cells need an answer from the project manager.", 1340,
         [("src", "KPI Grid", "bfusionKpiGrid")]),
    ])


# ================================================================ 2 PORTFOLIO
def build_portfolio():
    return chapter("portfolio", "PORTFOLIO", "ARE WE FUNDING THE RIGHT WORK?",
                   "Where the plan-field budget goes, how well it fits the strategy, and whether priority and value line up.",
                   PROJ, "portfolio", ("What is in the portfolio?",
                                       "Size, pipeline and strategic fit. Budget here = the lifetime Budget field on each plan."), [
        ("The portfolio register", "Portfolio › programme › project. Red variance = plan forecast more than 5% over plan budget.",
         350, [("ins", "portfolio", "v_register")]),
        ("Does the money follow the strategy?", "Budget by goal and alignment — the outer rings should be the strongly aligned work.",
         420, [("src", "Strategic Sunburst", "bfusionStrategicSunburst"), ("ins", "portfolio", "v_bud_align")]),
        ("Where does value concentrate?", "Pareto of value across projects, and priority against budget per project.",
         400, [("src", "Pareto Analysis", "bfusionParetoAnalysis"), ("ins", "portfolio", "v_scatter")]),
    ])


def build_selection():
    return deep_dive("selection", "SELECTION", "WHICH PROJECTS MAKE THE CUT?",
                     "Rank by value, draw the funding line, and check the selection against strategy and people.",
                     [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program")],
                     "Story | Portfolio Headline", [
        ("Where is the funding line?", "Projects above the waterline fit the budget; below it they wait or are cut.", 640,
         [("src", "Selection Waterfall", "bfusionSelectionWaterfall"),
          ("src", "Waterline Modeler & Resource Align", "bfusionWaterlineModeler")]),
        ("Does the selection fit strategy and people?", "Alignment of the funded set with goals and with available skills.", 620,
         [("src", "Waterline Modeler & Resource Align", "bfusionResourceAlignmentStrategy"),
          ("src", "Resource Alignment", "tableEx")], [1.3, 1]),
    ])


def build_scenarios():
    return deep_dive("scenarios", "SCENARIOS", "IF WE FUND A INSTEAD OF B, WHAT DO WE GAIN?",
                     "Pick scenario A and B: value against cost, the trade-off profile, and how sensitive the answer is.",
                     [(DP("Portfolio Name"), "Portfolio"), ("src", "Scenarios", "ModelerScenario_A.Name"),
                      ("src", "Scenarios", "ModelerScenario_B.Name")],
                     "Story | Scenario · Headline", [
        ("Value for money", "The efficient frontier: scenarios on the line give the most value per euro.", 600,
         [("src", "Scenarios", "bfusionEfficientFrontier"), ("src", "Scenarios", "bfusionScenarioRadar")], [1.1, 1]),
        ("How sensitive is the answer?", "Which assumption moves the outcome most, and the scenario KPIs side by side.", 640,
         [("src", "Sensitivity Tornado", "bfusionSensitivityTornado"), ("src", "Scenarios", "bfusionKpiGrid")]),
    ])


def build_constraints():
    return deep_dive("constraints", "CONSTRAINTS", "WHAT HOLDS THE PORTFOLIO BACK?",
                     "Where budget and capacity constraints cut projects out, and the start order that fits the people.",
                     [(DP("Portfolio Name"), "Portfolio"), ("src", "Resource Constraints & Sequencing", "ModelerScenario_A.Name"),
                      ("src", "Resource Constraints & Sequencing", "ModelerScenario_B.Name")],
                     "Story | Scenario · Headline", [
        ("Where do the constraints bite?", "Flow from demand to funded work; each drop-off is a constraint.", 560,
         [("src", "Constraint Sankey", "bfusionConstraintSankey")]),
        ("In what order can we start?", "Sequencing that respects resource capacity, per scenario.", 700,
         [("src", "Resource Constraints & Sequencing", "bfusionResourceConstraintSequencing")]),
    ])


# ================================================================ 3 FINANCIALS
def build_finance():
    return chapter("finance", "FINANCIALS", "ARE WE SPENDING AS PLANNED?",
                   "OnePlan financial plans. EAC and variance are at completion (all years); Year filters the to-date and trend views.",
                   STD, "finance", ("Where do we stand?",
                                    "EAC against budget at completion is the number the board asks for; budget to date checks the pace."), [
        ("Project financial register", "Sorted by overrun at completion. Red = EAC more than 5% over budget.", 350,
         [("ins", "finance", "v_fin_table")]),
        ("How is spend tracking over time?", "S-curve of budget, actual and forecast, and the financial story in words.", 420,
         [("src", "Project Financials Insights", "bfusionFinancialSCurve"),
          ("src", "Project Financials Insights", "bfusionFinancialKPINarrative")], [2, 1]),
        ("Where is the variance coming from?", "Financial overview per cost type, and the variance bridge by programme.", 400,
         [("src", "Project Financials Insights", "bfusionFinancialOverview"), ("ins", "finance", "v_waterfall")]),
    ])


def build_fintree():
    return deep_dive("fintree", "VARIANCE DRIVERS", "WHAT DRIVES THE VARIANCE?",
                     "Decompose the variance portfolio › programme › project › cost type and follow the biggest branch.",
                     [("src", "Financial Decomposition Tree", "DimProject.PlanType"), (DP("Portfolio Name"), "Portfolio")],
                     "Story | Finance Headline", [
        ("Variance driver tree", "Expand the widest branch first — that is where most of the gap sits.", 1340,
         [("src", "Financial Decomposition Tree", "bfusionVarianceDriverTree")]),
    ])


def build_budgetrisk():
    return deep_dive("budgetrisk", "BUDGET RISK", "WHERE WILL THE BUDGET LAND?",
                     "Forecast where each project's cost will end, and which projects to stop, rescue or continue.",
                     [(DP("Portfolio Name"), "Portfolio"), (DP("BusinessUnit_Value"), "Business unit"),
                      ("src", "Budget Risk Forecast", "DimProject.PlanType")],
                     "Story | Finance Headline", [
        ("Budget risk forecast", "Projected cost at completion with its confidence band against budget.", 760,
         [("src", "Budget Risk Forecast", "bfusionBudgetRiskForecast")]),
        ("Early warning: stop, rescue or continue?", "Sunk cost versus remaining value — the decision board for troubled projects.",
         500, [("src", "Project Early Warning Tracker", "bfusionSunkCostDecisionBoard")]),
    ])


# ================================================================ 4 RESOURCES
def build_resources():
    return chapter("resources", "RESOURCES", "DO WE HAVE THE PEOPLE?",
                   "Capacity from OnePlan resource calendars against scheduled and committed hours on project plans.",
                   [CAT] + RES, "resources", ("Supply and demand in one line",
                                              "Utilisation = scheduled hours on project plans ÷ capacity. Above 100% is overload."), [
        ("Who is over- or under-loaded?", "Bench and overload list (lowest utilisation first) and utilisation by role.", 350,
         [("ins", "resources", "v_bench"), ("ins", "resources", "v_role")], [2, 1]),
        ("Will supply cover demand?", "Capacity against demand per period; switch the grain and the grouping in the slicers.", 420,
         [("src", "Capacity & Allocation", "bfusionCapacityPlanning")]),
        ("Who, and when?", "Allocation heat map per person and period; hot cells are overload.", 380,
         [("src", "Capacity & Utilization", "bfusionResourceHeatmap")]),
    ])


def build_fte():
    return deep_dive("fte", "FTE DECISIONS", "WHERE DO WE ADD OR CUT PEOPLE?",
                     "Resource KPIs, the FTE decision board and how efficiently people are used.",
                     [CAT, (DR("Department_Value"), "Department"), (DR("Role_Value"), "Role"), (C("DimDate", "Year"), "Year")],
                     "Story | Resource Headline", [
        ("Resource KPIs", "Capacity, demand and utilisation by the grouping in the Category slicer.", 400,
         [("src", "Resource Decision Board", "bfusionResourceKPI")]),
        ("FTE decision board", "Hire, move or release: the gap per group in FTE.", 420,
         [("src", "Resource Decision Board", "bfusionFTEDecisionBoard")]),
        ("How efficiently are people used?", "Skills gaps and where hours go (productive, overhead, idle).", 400,
         [("src", "Efficiency Dashboard", "bfusionResourceGapAnalysis"),
          ("src", "Efficiency Dashboard", "bfusionResourceEfficiencyBreakdown")]),
    ])


def build_org():
    return deep_dive("org", "ORGANISATION", "WHO REPORTS WHERE, AND WHERE ARE THE GAPS?",
                     "The organisation chart next to the capacity gap of each team.",
                     [CAT, (DR("Department_Value"), "Department"), (DR("Role_Value"), "Role")],
                     "Story | Resource Headline", [
        ("Structure and gaps", "Click a team in the chart to see its gap on the right.", 1340,
         [("src", "Org Chart", "bfusionOrgStructure"), ("src", "Org Chart", "bfusionResourceGapAnalysis")], [1.2, 1]),
    ])


def build_timesheets():
    """Native body of the Insights 4b page (same measures), plus the BFusion KPI grid of timesheet detail."""
    ins = insights("timesheets")
    slicers = [(_slicer_field(v), _slicer_label(v)) for v in sorted(
        (v for v in ins.visuals if v.get("visual", {}).get("visualType") == "slicer" and v["position"]["y"] < 80),
        key=lambda v: v["position"]["x"])]
    title_runs = next(v for v in ins.visuals if v["name"] == uid(ins.id, "title", "textbox"))["visual"]["objects"]
    runs = title_runs["general"][0]["properties"]["paragraphs"][0]["textRuns"]
    area, question = runs[0]["value"].rstrip(" |"), runs[1]["value"]
    sub = next(v for v in ins.visuals if v["name"] == uid(ins.id, "subtitle", "textbox"))
    subtitle = sub["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"]
    skip = {uid(ins.id, k, t) for k in ("home", "title", "subtitle", "next", "back")
            for t in ("actionButton", "textbox")}
    body = sorted((v for v in ins.visuals if v["name"] not in skip and v["position"]["y"] >= 80
                   and not v.get("parentGroupName") and v.get("visual", {}).get("visualType") != "actionButton"),
                  key=lambda v: (v["position"]["y"], v["position"]["x"]))
    head_row = [v for v in body if v["position"]["y"] < 100]          # the Insights headline (y 84)
    # sections ① .. ④: from each section label down to the next one, moved as one block
    starts = sorted(v["position"]["y"] for v in body if v.get("visual", {}).get("visualType") == "textbox"
                    and any(c in json.dumps(v["visual"].get("objects", {}), ensure_ascii=False) for c in pages.CIRCLED))
    bottom = max(v["position"]["y"] + v["position"]["height"] for v in body)
    secs = []
    for k, y0 in enumerate(starts):
        y1 = starts[k + 1] if k + 1 < len(starts) else bottom + GAP
        secs.append((y0, y1 - y0, [v for v in body if y0 <= v["position"]["y"] < y1]))
    screens = pack([(None, None, h - SEC_H - GAP, y0) for y0, h, _ in secs], BODY_END - Y_BODY + GAP)
    by_start = {y0: (h, vs) for y0, h, vs in secs}
    out, k = [], 0
    for i, grp in enumerate(screens, 1):
        of = len(screens)
        pid = page_id("timesheets", i)
        KEY_OF[pid] = "timesheets"
        pg = Page(pid, NAMES["timesheets"] if i == 1 else f"{NAMES['timesheets']} ({i}/{of})", W, H, background_image=BG)
        QUESTIONS["timesheets"] = question
        header(pg, "timesheets", area, question, subtitle, slicers)
        nav_row(pg, "timesheets")
        for v in head_row:
            put(pg, v["position"]["x"], Y_HEAD, v["position"]["width"], v["position"]["height"], copy.deepcopy(v), "ts_head")
        # section labels keep their height; everything under them scales to fill the screen
        free = BODY_END - Y_BODY + GAP - SEC_H * len(grp)
        scale = free / sum(by_start[b_[3]][0] - SEC_H for b_ in grp)
        y = Y_BODY
        for b_ in grp:
            y0 = b_[3]
            h, vs = by_start[y0]
            for v in vs:
                p = v["position"]
                if p["y"] == y0:
                    ny, nh = y, p["height"]
                else:
                    ny = y + SEC_H + (p["y"] - y0 - SEC_H) * scale
                    nh = p["height"] * scale
                put(pg, p["x"], round(ny, 2), p["width"], round(min(nh, BODY_END - ny), 2), copy.deepcopy(v), f"ts{k}")
                k += 1
            y += SEC_H + (h - SEC_H) * scale
        next_back(pg, "timesheets", i, of)
        pg.page["visibility"] = "HiddenInViewMode"
        out.append(pg)
    return out


def _slicer_label(vc):
    pr = vc["visual"]["query"]["queryState"]["Values"]["projections"][0]
    return pr.get("displayName") or pr["field"]["Column"]["Property"]


def build_mywork():
    return deep_dive("mywork", "MY WORK", "WHAT IS ON MY PLATE?",
                     "Pick a project and a role: tasks by status, the load per person, the timeline and the board.",
                     [(DP("Name"), "Project"), (DR("Role_Value"), "Role"), (C("DimTask", "Status"), "Task status"),
                      (C("DimTask", "WorkType"), "Work type")],
                     "Story | Schedule Headline", [
        ("Tasks and load", "Task KPIs on the left; the heat map shows who carries the hours.", 500,
         [("src", "My Work", "bfusionTaskKPIBoard"), ("src", "My Work", "bfusionResourceHeatmap")]),
        ("When is it due?", "Hierarchical Gantt of the selected work.", 440,
         [("src", "My Work", "bfusionHierarchicalGantt")]),
        ("Where does it stand?", "Kanban board by status — drag nothing here, update in OnePlan.", 290,
         [("src", "My Work", "bfusionKanbanBoard")]),
    ])


# ================================================================ 5 SCHEDULE
def build_schedule():
    return chapter("schedule", "SCHEDULE", "WILL WE DELIVER ON TIME?",
                   "Schedule health reported by project managers, checked against baselines, milestones and late work.",
                   PROJ, "schedule", ("Delivery confidence",
                                      "Reported health of active projects first, then what the project work plans say."), [
        ("Late-work register", "Open project tasks past their baseline finish — longest slip first.", 350,
         [("ins", "schedule", "v_late")]),
        ("What runs when?", "Hierarchical Gantt with baselines; expand a project to see its late tasks.", 430,
         [("src", "Schedule Insights", "bfusionHierarchicalGantt")]),
        ("Where will finish dates land, and what is next?", "Forecast finish against plan, and open milestones soonest first.",
         390, [("src", "Scheduled Risk Forecast", "bfusionScheduleRiskForecast"), ("ins", "schedule", "v_miles")], [1.6, 1]),
    ])


def build_critical():
    return deep_dive("critical", "CRITICAL PATH", "WHICH TASKS SET THE FINISH DATE?",
                     "Pick a project: the critical path network and the critical-chain buffer it consumes.",
                     [(DP("PlanType"), "Plan type"), (DP("Name"), "Project")],
                     "Story | Schedule Headline", [
        ("Critical path", "Tasks with zero float; any slip here moves the finish date.", 640,
         [("src", "Critical Path & Chain", "bfusionCriticalPathDiagram")]),
        ("Critical chain and buffer", "Buffer burn against chain completion — red means the buffer is going faster than the work.",
         640, [("src", "Critical Path & Chain", "bfusionCriticalChain")]),
    ])


def build_psr():
    return deep_dive("psr", "STATUS REPORT", "WHERE DOES THIS PROJECT STAND?",
                     "Pick a project: status card, risks, trend, lifecycle, timeline and the people on it.",
                     [CAT, (DP("PlanType"), "Plan type"), (DP("Name"), "Project")],
                     "Story | Status · Headline", [
        ("Status, risks and trend", "The latest status report, the project's risk matrix and how its health trends.", 520,
         [("src", "Project Status Report (PSR)", "bfusionProjectStatusCard"),
          ("src", "Project Status Report (PSR)", "bfusionPortfolioRiskMatrix"),
          ("src", "Project Status Report (PSR)", "bfusionStatusTrendSparkline")], [0.9, 1.2, 1]),
        ("Lifecycle", "Where the project is in its gates.", 260,
         [("src", "Project Status Report (PSR)", "bfusionProjectLifecycle")]),
        ("Timeline and people", "Gantt of the project and the load of the people on it.", 440,
         [("src", "Project Status Report (PSR)", "bfusionHierarchicalGantt"),
          ("src", "Project Status Report (PSR)", "bfusionResourceHeatmap")], [1.5, 1]),
    ])


# ================================================================ 6 RISK / 7 BENEFITS / 8 GOVERNANCE
# ---------------------------------------------------------------- cross-report drill-through
# Hidden drill pages, each hosted by the role report that owns its topic. All Story reports live in one workspace /
# app and turn on settings.useCrossReportDrillthrough, so right-click a project, portfolio or person in ANY Story
# report › Drill through › "<page> [<host report>]" opens the host report on that one item; Back returns.
# Every page is one tall FitToWidth page, not a story page with "(2/2)" screens: a drill filter does not travel with a
# "Continue" click to a second screen. Only the bound field travels (Keep all filters off): the source page's year and
# slicers must not narrow a page that lives in another report.
@dataclass
class Drill:
    key: str          # page key; page id uid("bfstory-page", key) is stable across rebuilds
    name: str         # menu text: "<name> [<host report>]"
    host: str         # roles.ROLES key of the report that holds the page
    field: dict       # the drill-through field (table + column must match the source visual's field)
    chrome_key: str   # story page whose chapter rail / filter bar the page shows (must be in the host report)
    area: str
    question: str
    what: str         # "the project" / "the portfolio" / "the person", for the subtitle
    headline: str     # headline measure
    spec: list        # [(question, explain, relative height, items, weights | None)]


PSR = "Project Status Report (PSR)"
DRILLS = [
    Drill("psr_drill", "Project Status", "pm", DP("Name"), "psr", "STATUS REPORT", "WHERE DOES THIS PROJECT STAND?",
          "the project", "Story | Status · Headline", [
        ("Status, risks and trend", "The latest status report, the project's risk matrix and how its health trends.", 520,
         [("src", PSR, "bfusionProjectStatusCard"), ("src", PSR, "bfusionPortfolioRiskMatrix"),
          ("src", PSR, "bfusionStatusTrendSparkline")], [0.9, 1.2, 1]),
        ("Lifecycle", "Where the project is in its gates.", 260, [("src", PSR, "bfusionProjectLifecycle")], None),
        ("Timeline and people", "Gantt of the project and the load of the people on it.", 440,
         [("src", PSR, "bfusionHierarchicalGantt"), ("src", PSR, "bfusionResourceHeatmap")], [1.5, 1])]),
    Drill("sched_drill", "Project Schedule", "pm", DP("Name"), "critical", "SCHEDULE", "WHAT SETS THIS PROJECT'S FINISH?",
          "the project", "Story | Schedule Headline", [
        ("Critical path", "Tasks with zero float; any slip here moves the finish date.", 520,
         [("src", "Critical Path & Chain", "bfusionCriticalPathDiagram")], None),
        ("Critical chain and buffer", "Buffer burn against chain completion.", 400,
         [("src", "Critical Path & Chain", "bfusionCriticalChain")], None),
        ("Tasks and where they stand", "Task KPIs and the board by status.", 380,
         [("src", "My Work", "bfusionTaskKPIBoard"), ("src", "My Work", "bfusionKanbanBoard")], [1, 1.4])]),
    Drill("fin_drill", "Project Financials", "ppm", DP("Name"), "finance", "FINANCIALS", "IS THIS PROJECT ON BUDGET?",
          "the project", "Story | Finance Headline", [
        ("How is spend tracking over time?", "S-curve of budget, actual and forecast, and the financial story in words.", 420,
         [("src", "Project Financials Insights", "bfusionFinancialSCurve"),
          ("src", "Project Financials Insights", "bfusionFinancialKPINarrative")], [2, 1]),
        ("Where is the variance coming from?", "Financial overview per cost type.", 380,
         [("src", "Project Financials Insights", "bfusionFinancialOverview")], None),
        ("Where will the budget land?", "Cost at completion with its confidence band, and stop / rescue / continue.", 480,
         [("src", "Budget Risk Forecast", "bfusionBudgetRiskForecast"),
          ("src", "Project Early Warning Tracker", "bfusionSunkCostDecisionBoard")], [1.3, 1])]),
    Drill("pf_drill", "Portfolio Overview", "ppm", DP("Portfolio Name"), "health", "PORTFOLIO", "HOW IS THIS PORTFOLIO DOING?",
          "the portfolio", "Story | Exec Headline", [
        ("Health on every dimension", "Schedule, cost, scope, resources and risk side by side.", 520,
         [("src", "360° Dashboard", "bfusionPortfolio360"), ("src", "Health Dashboard", "bfusionPortfolioSummaryKPI")],
         [1, 1.1]),
        ("Where do health and risk meet?", "Projects in the red corner of both are the board conversation.", 440,
         [("src", "Health Dashboard", "bfusionPortfolioHealthMatrix"),
          ("src", "Health Dashboard", "bfusionPortfolioRiskMatrix")], [1.5, 1]),
        ("What lands when?", "Bars are the planned window of each project; colour is health.", 400,
         [("src", "Roadmap", "portfolioRoadmap")], None)]),
    Drill("person_drill", "Person Workload", "resources", DR("Name"), "resources", "PEOPLE", "WHAT IS ON THIS PERSON'S PLATE?",
          "the person", "Story | Resource Headline", [
        ("Who, and when?", "Allocation per period; hot cells are overload.", 420,
         [("src", "Capacity & Utilization", "bfusionResourceHeatmap")], None),
        ("Tasks and status", "Task KPIs and the board by status.", 400,
         [("src", "My Work", "bfusionTaskKPIBoard"), ("src", "My Work", "bfusionKanbanBoard")], [1, 1.4]),
        ("When is it due?", "Hierarchical Gantt of the assigned work.", 440, [("src", "My Work", "bfusionHierarchicalGantt")], None)]),
    Drill("gov_drill", "Project Data Quality", "pmo", DP("Name"), "recon", "DATA QUALITY", "CAN WE TRUST THIS PROJECT'S DATA?",
          "the project", CARD_TEXT["governance"][1], [
        ("Which sources does it have?", "One card per source the project reports through.", 300, [lambda *a: _recon_cards(*a)], None),
        ("Reconciliation", "The project's line in each source, side by side.", 900, [lambda *a: _recon_table(*a)], None)]),
]
DRILL_PIDS = {uid("bfstory-page", d.key) for d in DRILLS}
TALL_END = round(pages.TALL * 0.928) - 12   # footer band of the tall background


def build_drill(d):
    pid = uid("bfstory-page", d.key)
    KEY_OF[pid] = d.chrome_key
    pg = Page(pid, d.name, W, pages.TALL, display_option="FitToWidth", background_image=BG)
    header(pg, d.chrome_key, d.area, d.question,
           f"Drill-through: {d.what} you right-clicked, in any Story report. Back returns you there.", [])
    put(pg, 16, Y_HEAD, 1768, 56, head(d.headline), "headline")
    free = TALL_END - Y_BODY - len(d.spec) * (SEC_H + GAP) + GAP
    scale = free / sum(b_[2] for b_ in d.spec)
    y = Y_BODY
    for num, (q, e, h, items, wts) in enumerate(d.spec, 1):
        y = band(pg, y, num, q, e, int(h * scale), items, wts)
    ent, prop = d.field["Column"]["Expression"]["SourceRef"]["Entity"], d.field["Column"]["Property"]
    fname = uid("bind-filter", d.key, ent, prop)
    pg.page["filterConfig"] = {"filters": [{"name": fname, "field": d.field, "type": "Categorical",
                                            "howCreated": "Drillthrough"}]}
    pg.page["pageBinding"] = {"name": uid("bind", d.key), "type": "Drillthrough", "referenceScope": "CrossReport",
                              "acceptsFilterContext": "None",
                              "parameters": [{"name": uid("bind-param", d.key), "boundFilter": fname,
                                              "fieldExpr": d.field}]}
    pg.page["visibility"] = "HiddenInViewMode"
    return pg


def build_risk():
    return chapter("risk", "RISK", "WHAT COULD GO WRONG?",
                   "Risks and issues logged on the project work plans: how likely, how bad, where the exposure sits, what to escalate.",
                   PROJ, "risk", ("Risk position",
                                  "Active risks on project plans. Exposure is OnePlan's score (probability % × impact weight), not money."), [
        ("Top-risk register", "Highest exposure score first — every critical or high risk needs an owner and a mitigation.",
         350, [("ins", "risk", "v_risk_table")]),
        ("How likely, how bad?", "Risk matrix per risk, and per project across the portfolio.", 430,
         [("src", "Risk Matrix", "bfusionRiskMatrixExt"), ("src", "Risk Dashboard", "bfusionPortfolioRiskMatrix")]),
        ("What kind of risk, and where is it in the response cycle?", "Radar by category and the risk board by stage.", 390,
         [("src", "Risk Radar", "bfusionRiskRadarChart"), ("src", "Risk Radar", "bfusionKanbanBoard")]),
    ])


def build_benefits():
    return chapter("benefits", "BENEFITS", "WILL IT PAY OFF?",
                   "Planned benefits against EAC, when they land, and whether they are realised.",
                   PROJ, "benefits", ("The value case",
                                      "Planned benefits at completion, what is due to date and what is actually realised."), [
        ("Benefits register", "Every project with its benefit case, largest first.", 350,
         [("ins", "benefits", "v_ben_table")]),
        ("Is the value landing?", "Planned against realised benefits over time, per benefit type.", 430,
         [("src", "Realizations", "bfusionBenefitsRealization")]),
        ("When does it land, and where is the best return?", "Benefits per quarter and value for money per project.", 390,
         [("ins", "benefits", "v_ben_phasing"), ("ins", "benefits", "v_ratio")], [2, 1]),
    ])


def build_governance():
    return chapter("governance", "GOVERNANCE", "CAN WE TRUST THE DATA?",
                   "OnePlan Plan Insights rules: which plans fail which checks, and what to fix first.",
                   [(C("DimPortfolio", "Name"), "Portfolio"), (C("DimProgram", "Name"), "Program"),
                    (C("FactPlanInsight", "PlanType"), "Plan type"), (C("DimInsightRule", "Severity"), "Severity")],
                   "governance", ("Data trust score",
                                  "Share of assessed plans passing every rule; problems block decisions, warnings weaken them."), [
        ("Plan-by-plan action list", "The plans to fix, worst first, with the rule they fail.", 350,
         [("ins", "governance", "v_plans")]),
        ("Which rules fail most?", "Fix the rule that fails on most plans first — it moves the score fastest.", 400,
         [("ins", "governance", "v_rules"), ("ins", "governance", "v_area")], [1.5, 1]),
        ("Where does it concentrate?", "Pareto of failing plans and the drivers of the hygiene gap.", 400,
         [("src", "PMO Overview", "bfusionParetoAnalysis"), ("src", "PMO Hygiene", "bfusionVarianceDriverTree")]),
    ], headline_measure="PMO | Governance Headline")


def _recon_cards(pg, x, y, w, h):
    """One card per source: active projects that have it."""
    n = len(confidence.CHECKS)
    cw = (w - 10 * (n - 1)) / n
    for k, (key, label, _s, _c) in enumerate(confidence.CHECKS):
        pg.add(round(x + k * (cw + 10), 2), y, round(cw, 2), min(h, 90),
               card(confidence.ratio(key), label, colour_measure=confidence.ratio_colour(key), size=16), key=f"rc_card{k}")


def _recon_table(pg, x, y, w, h):
    gaps = M(confidence.GAPS)
    obj = table_style()
    obj["values"].append(cf_font(gaps, confidence.GAP_COLOUR))
    v = chart("tableEx", {"Values": [
        P(DP("Id"), "ID"), P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"),   # ID: one row per project
        P(M(confidence.GAP_COUNT), "Gaps"),
        P(gaps, "Missing sources"), P(M("Story | Budget At Completion"), "Budget"), P(M("Story | Finance EAC"), "EAC"),
        P(M(confidence.LIFETIME_ACTUAL), "Actual (all years)"), P(M("Story | Project Scheduled Hours"), "Scheduled h"),
        P(M("Timesheet | Actual Hours"), "Booked h"), P(M("Story | Baseline · Baseline Finish"), "Baseline finish"),
        P(M("Story | Status · Days Since Report"), "Days since report"),
        P(M("Story | Benefits At Completion"), "Planned benefits")]},
        "Project by project — most gaps first", obj, sort=[(M(confidence.GAP_COUNT), "Descending")])
    pg.add(x, y, w, h, v, filters=[pbir.f_in("DimProject", "State_Value", [ACTIVE_STATE])], key="v_recon")


def build_recon():
    return deep_dive("recon", "RECONCILIATION", "DO THE SOURCES AGREE?",
                     "Every active project against each OnePlan source. A number is only as complete as the source under it.",
                     [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program")],
                     confidence.HEADLINE, [
        ("How complete is each source?",
         "Active projects that have each piece of data; under 80% the pages built on it cover only part of the portfolio.",
         120, [_recon_cards]),
        ("Which projects have gaps?", "One row per active project, most gaps first — send each manager the missing sources.",
         720, [_recon_table]),
    ])


BUILDERS = {**{f"brief_{c}": (lambda c=c: build_brief(c)) for c in BRIEF_TAKEAWAYS},
            "welcome": build_welcome, "home": build_home, "questions": build_questions, "exec": build_exec, "health": build_health, "roadmap": build_roadmap,
            "drift": build_drift, "kpigrid": build_kpigrid, "portfolio": build_portfolio, "selection": build_selection,
            "scenarios": build_scenarios, "constraints": build_constraints, "finance": build_finance,
            "fintree": build_fintree, "budgetrisk": build_budgetrisk, "resources": build_resources, "fte": build_fte,
            "org": build_org, "timesheets": build_timesheets, "mywork": build_mywork, "schedule": build_schedule,
            "critical": build_critical, "psr": build_psr, "risk": build_risk, "benefits": build_benefits,
            "governance": build_governance, "recon": build_recon}


def copy_interactions(built):
    """Source visualInteractions (e.g. which scenario slicer filters which Scenarios visual) follow the copied
    visuals, when both ends of a link landed on the same story page."""
    for pg in built:
        names = pg.__dict__.get("src_names", {})
        out = []
        for (disp, _), _new in names.items():
            for it in _SRC_INTERACTIONS.get(disp, []):
                a, b_ = names.get((disp, it["source"])), names.get((disp, it["target"]))
                if a and b_ and not any(o["source"] == a and o["target"] == b_ for o in out):
                    out.append({"source": a, "target": b_, "type": it["type"]})
        if out:
            pg.page["visualInteractions"] = out
    # a link whose two ends landed on different 16:9 screens of the same page is lost: report it in --check
    DROPPED.clear()
    by_key = {}
    for pg in built:
        by_key.setdefault(KEY_OF.get(pg.id), []).append(pg)
    for key, screens in by_key.items():
        if len(screens) < 2:
            continue
        where = {}
        for pg in screens:
            for sk in pg.__dict__.get("src_names", {}):
                where.setdefault(sk, set()).add(pg.id)
        for (disp, _) in list(where):
            for it in _SRC_INTERACTIONS.get(disp, []):
                a, b_ = where.get((disp, it["source"])), where.get((disp, it["target"]))
                if a and b_ and not a & b_:
                    DROPPED.add(f"INTERACTION {NAMES[key]}: source link {it['source']} -> {it['target']} split over screens")


DROPPED = set()


STORY_BLURBS = {
    "exec": "Health, money, people and risk on one page", "health": "Health of every portfolio side by side",
    "roadmap": "What lands when, with its health", "drift": "How the portfolio changed over time",
    "kpigrid": "Every project scored on the same KPIs",
    "portfolio": "Value, cost and strategic fit of the pipeline", "selection": "Ranked projects against the funding line",
    "scenarios": "Compare funding choices before you decide", "constraints": "Dependencies and limits that block delivery",
    "finance": "Budget, actuals and forecast at completion", "fintree": "Which projects and cost lines cause the gap",
    "budgetrisk": "Early warnings before the money is spent",
    "resources": "Capacity against demand, month by month", "fte": "Where to add or reduce people",
    "org": "Reporting lines and unfilled roles", "timesheets": "Logged hours against the plan",
    "mywork": "Your tasks and hours in one place",
    "schedule": "Progress, slippage and upcoming milestones", "critical": "The tasks that set the finish date",
    "psr": "One project's status report, month by month",
    "risk": "Exposure, critical risks and open issues", "benefits": "Planned against realised benefits",
    "governance": "Data quality, compliance and reporting discipline",
    "recon": "Every project against every source, gaps first",
}


def context():
    common = dict(pid=PID, names=NAMES, pages=PAGES, chapters=CHAPTERS, questions=QUESTIONS,
                  headline={k: v[1] for k, v in CARD_TEXT.items()}, blurbs=STORY_BLURBS,
                  inside={"exec": ["KPI pulse", "Decisions this month", "Health matrix", "Status trend",
                                   "Chapter scorecard"]})
    if ROLE is None:
        return entry.Context(**common, title="Bfusion Decision Story", home_label="Decision Center")
    return entry.Context(**common, title=ROLE.title, home_label="Decision Center" if ROLE.home else "Questions",
                         art=roles.SCENE_OF, home_url=app_links.url("launcher", roles.LAUNCHER_PAGE_ID))


def build_pages():
    pbir.BOOKMARKS.clear()
    entry.use(context())
    # the questions and brief pages read every page's header question, so they are built last, in story order
    late = [k for k, _ in PAGES if k == "questions" or k.startswith("brief_")]
    done = {k: BUILDERS[k]() for k, _ in PAGES if k not in late}
    done.update({k: BUILDERS[k]() for k in late})
    built = [p for k, _ in PAGES for p in (done[k] if isinstance(done[k], list) else [done[k]])]
    if ROLE is not None:                         # outside PAGES: no Next link, no tab, reached by drill-through only
        built += [build_drill(d) for d in DRILLS if d.host == ROLE.key]
    for p in built:
        KEY_OF.setdefault(p.id, next((k for k, v in PID.items() if v == p.id), None))
    copy_interactions(built)
    pages.filter_real_projects(built)
    a11y.apply(built)
    chrome.apply(built, PID, KEY_OF, NAMES, CHAPTERS, Y_BAR,      # after a11y: the rail comes last in tab order
                 rail=roles.rail(ROLE) if ROLE else None, art=roles.SCENE_OF if ROLE else None)
    consistency.apply(built)
    polish.apply(built)
    if ROLE is not None:             # in a role report the tabs are Questions, Home and the role's chapters only:
        tabs = {PID[c] for c in CHAPTERS} | {PID[k] for k in ("questions", "home") if k in PID}
        for p in built:              # a deep dive promoted to a chapter shows, a chapter used as deep dive hides
            if p.id in tabs:
                p.page.pop("visibility", None)
            else:
                p.page["visibility"] = "HiddenInViewMode"
    return built


# ================================================================ write
def custom_types(built):
    return sorted({vc["visual"]["visualType"] for pg in built for vc in pg.visuals
                   if vc.get("visual", {}).get("visualType", "").startswith(("bfusion", "portfolioRoadmap"))})


# Test plans in the OnePlan demo tenant, by exact name (a substring match would also hide 'Latest...', 'Attestation...'):
# hidden until they are archived in OnePlan
TEST_PROJECTS = ["NIKO Test 2", "MSP Test", "Test PSR", "Test Timesheet", "Temlate Test"]
NO_TEST_PROJECTS = {**pbir.f_in("DimProject", "Name", TEST_PROJECTS, exclude=True), "ordinal": 9, "howCreated": "User"}


def write(built):
    out = build.write_report(NAME, built, pbir.BOOKMARKS, OUT_DIR, extra_filters=[NO_TEST_PROJECTS])
    # custom visual packages: report.json resource packages + the CustomVisuals folder, only those in use
    used = custom_types(built)
    ref = json.loads((SRC / "definition" / "report.json").read_text(encoding="utf-8"))
    pkgs = [p for p in ref["resourcePackages"] if p["type"] == "CustomVisual" and p["name"] in used]
    missing = set(used) - {p["name"] for p in pkgs}
    if missing:
        raise ValueError(f"no custom visual package in the source pack for {sorted(missing)}")
    rj = out / "definition" / "report.json"
    rep = json.loads(rj.read_text(encoding="utf-8"))
    rep["resourcePackages"] = pkgs + rep["resourcePackages"]
    # Report settings › "Allow visuals in this report to use drill-through targets from other reports"
    rep.setdefault("settings", {})["useCrossReportDrillthrough"] = True
    build.dump(rj, rep)
    entry.register_resources(out)
    chrome.register(out)
    for name in used:
        shutil.copytree(SRC / "CustomVisuals" / name, out / "CustomVisuals" / name)
    return out


def path_errors(out):
    """Power BI Desktop refuses files whose full path is longer than MAX_PATH characters."""
    return [f"PATH {len(str(f))} chars > {MAX_PATH}: {f}" for f in out.rglob("*") if len(str(f)) > MAX_PATH]


def layout_errors(built):
    errs = []
    for pg in built:
        names = [vc["name"] for vc in pg.visuals]
        errs += [f"LAYOUT {pg.display}: two visuals share the key of {n} (one overwrites the other)"
                 for n in sorted({n for n in names if names.count(n) > 1})]
        banded = "image" in pg.page["objects"].get("background", [{}])[0].get("properties", {})
        limit = (LIMIT if pg.page["height"] == H else round(pg.page["height"] * 0.928)) if banded else pg.page["height"]
        for vc in pg.visuals:
            p = vc["position"]
            if p["x"] < 0 or p["x"] + p["width"] > pg.page["width"] + 0.5 or p["y"] + p["height"] > limit:
                errs.append(f"LAYOUT {pg.display}: {vc['name']} at {p} outside page/footer")
        errs += nav_overlap_errors(pg)
    return errs


def nav_overlap_errors(pg):
    """The navigation row (breadcrumb left, chapter strip right) must not collide: no two top-level visuals that sit
    inside the row (NAV_Y .. NAV_Y + NAV_H) may overlap horizontally. The chapter rail (x < RAIL_W) is left out."""
    row = sorted((vc["position"] for vc in pg.visuals
                  if not vc.get("parentGroupName") and vc["position"]["x"] >= chrome.RAIL_W - 0.5
                  and NAV_Y <= vc["position"]["y"] and vc["position"]["y"] + vc["position"]["height"] <= NAV_Y + NAV_H + 0.5),
                 key=lambda p: p["x"])
    return [f"NAV {pg.display}: visual at x={b['x']} overlaps the one at x={a['x']} (ends {a['x'] + a['width']:.1f})"
            for k, a in enumerate(row) for b in row[k + 1:] if b["x"] < a["x"] + a["width"] - 0.5]


def reach_errors(built):
    """Every page must be reachable in one click from the landing page, Home, Questions, its chapter page or its
    chapter's brief (a role report without Home opens a chapter from its brief: Questions › Brief › chapter)."""
    links = {}
    for pg in built:
        for vc in pg.visuals:
            vl = vc.get("visual", {}).get("visualContainerObjects", {}).get("visualLink")
            if vl:
                tgt = vl[0]["properties"].get("navigationSection")
                if tgt:
                    links.setdefault(pg.id, set()).add(tgt["expr"]["Literal"]["Value"].strip("'"))
    roots = set().union(*(links.get(PID[r], set()) for r in ("welcome", "home", "questions") if r in PID))
    errs = []
    for k, _ in PAGES[1:]:                               # PAGES[0] is the page the report opens on
        c = layout._code(NAMES[k])
        chap = k if not c else next(m for m, d in PAGES if layout._code(d) and layout._code(d)[0] == c[0])
        if PID[k] not in roots | links.get(PID[chap], set()) | links.get(PID.get(f"brief_{chap}"), set()):
            errs.append(f"REACH {NAMES[k]}: no link from the landing page, Home, Questions, its chapter or its brief")
    return errs


def link_errors(built):
    """Every page-navigation button must open a page of this report (a role report holds a subset of the pages)."""
    ids = {pg.id for pg in built}
    errs = []
    for pg in built:
        for vc in pg.visuals:
            for vl in vc.get("visual", {}).get("visualContainerObjects", {}).get("visualLink", []):
                tgt = vl["properties"].get("navigationSection")
                v = tgt["expr"]["Literal"]["Value"].strip("'") if tgt else ""
                if v and v not in ids:
                    errs.append(f"LINK {pg.display}: {vc['name']} opens page {v}, which is not in this report")
    return errs


def inherited_measures():
    """Model measures the source pack itself references but the local .bim snapshot lacks (the published model is
    newer than the snapshot). Copied visuals keep them; the check reports them as warnings, not errors."""
    import re
    _, meas = build.load_model()
    used = set()
    for f in (SRC / "definition" / "pages").rglob("visual.json"):
        used |= set(re.findall(r'"Measure":\s*\{\s*"Expression":\s*\{\s*"SourceRef":\s*\{\s*"Entity":\s*"[^"]+"\s*\}\s*\},'
                               r'\s*"Property":\s*"([^"]+)"', f.read_text(encoding="utf-8")))
    return used - meas


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--out" in args:
        OUT_DIR = Path(args[args.index("--out") + 1])
    if "--role" in args:
        apply_role(roles.ROLES[args[args.index("--role") + 1]])
    pages_ = build_pages()
    out = write(pages_)
    print(f"built {len(pages_)} pages, {sum(len(p.visuals) for p in pages_)} visuals, "
          f"{len(custom_types(pages_))} custom visual types -> {out}")
    if "--check" in args:
        inh = inherited_measures()
        for m in sorted(inh):
            print(f"WARN inherited from the source pack, not in the local model snapshot: {m}")
        if ROLE is not None:
            for k in app_links.missing():
                print(f"WARN app_links.json: {k} not filled in (house button has no link yet)")
        _load = build.load_model
        build.load_model = lambda: (_load()[0], _load()[1] | inh)
        e = build.check(pages_, out) or 0
        more = (layout_errors(pages_) + reach_errors(pages_) + link_errors(pages_) + path_errors(out)
                + polish.errors(pages_) + consistency.errors(pages_) + sorted(DROPPED))
        for m in more:
            print(m)
        tot = e + len(more)
        print("OK" if tot == 0 else f"FAILED ({tot} problem(s))")
        sys.exit(1 if tot else 0)
