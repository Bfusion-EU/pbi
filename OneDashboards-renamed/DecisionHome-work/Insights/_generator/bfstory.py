"""Build 'OneDashboards - Bfusion Story': the BFusion custom-visual pack restructured as a story.

    python bfstory.py            # writes ../../Story/Bfusion Story.pbip + .Report
    python bfstory.py --check    # build + validate JSON schemas, model references and layout

Same story grammar and navigation as the Insights pack (header AREA | QUESTION? -> orange headline -> ① pulse ->
② list to act on -> ③ / ④ the picture and the drivers -> Next chapter), but the pictures are the BFusion custom
visuals taken from 'OneDashboards - Bfusion' (bindings and Format-pane settings copied as they are), next to the
native KPI cards, registers and headlines of the Insights pack (same measures, so one definition per number).
The source pack is read only; it is never written.
"""
import copy
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
import story_measures  # noqa: E402
import illustrations  # noqa: E402
from pbir import (Page, P, M, C, s, b, uid, st, textbox, shape, nav_button, home_icon_button, slicer, headline,  # noqa: E402
                  image, NAVY, NAVY_BTN, ORANGE, ORANGE_DK, ORANGE_SOFT, BORDER, MUTED)

# Short on purpose: Desktop cannot read files over 259 characters, and the longest custom visual file adds
# ~170 characters below the .Report folder (path_errors checks this).
NAME = "Bfusion Story"
OUT_DIR = build.ROOT.parent / "Story"
MAX_PATH = 259
OUT = OUT_DIR / f"{NAME}.Report"
SRC = build.REF                      # OneDashboards - Bfusion.Report (read only)
LOGO_FILE = Path(__file__).parent / "assets" / "bfusion_logo.png"   # 300x189, Branding/Logo/logo.jpg + rounded corners
LOGO_RES = "bfusion_logo.png"
ONEPLAN_RES = "OnePlan_logo_-_dark_background9901469509814106.png"   # 211x92 on #0E1C2D
INK = "#0E1C2D"                      # the OnePlan logo's own background: the welcome page uses it so the logo blends

W, H = 1800, 1800
BG = pages.BG_TALL
LIMIT = round(H * 0.928)             # top of the footer band
NAV_Y, NAV_H = 86, 30
Y_HEAD = 122                         # orange headline under the navigation row
Y_BODY = 188                         # first section label
Y_NEXT = 1612                        # Next / Back row
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
]
NAMES = dict(PAGES)
PID = {k: uid("bfstory-page", k) for k, _ in PAGES}
ORDER = [k for k, _ in PAGES]
CHAPTERS = [k for k, d in PAGES if layout._code(d) and not layout._code(d)[1]]


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
    if key != "home":
        pg.add(0, 4, 60, 58, home_icon_button(PID["home"]), key="home")
    tsize = 24 if len(f"{area} | {question}") <= pages.TITLE_MAX else 20
    pg.add(62, 8, 960, 46, textbox([[(f"{area} | ", st("DIN", tsize, ORANGE, True)),
                                      (question, st("DIN", tsize, NAVY, True))]]), key="title")
    ssize = 11 if len(subtitle) <= pages.SUBTITLE_MAX else 10
    pg.add(62, 52, 975, 26, textbox([[(subtitle, st("Segoe UI", ssize, MUTED))]]), key="subtitle")
    x = W - 16 - len(slicers) * 188 + 8
    assert x >= 1030, f"{pg.display}: too many slicers ({len(slicers)})"
    for k, sl in enumerate(slicers):
        if sl[0] == "src":
            vc = src_slicer(sl[1], sl[2])
            put(pg, x + k * 188, 10, 180, 62, vc, f"slicer{k}")
        else:
            pg.add(x + k * 188, 10, 180, 62, slicer(sl[0], sl[1]), key=f"slicer{k}")


def _crumb_w(text):
    return round(len(text) * 7.6 + 40)       # bold Segoe UI 10 pt + the button's own margins ("Home" fits whole)


def _crumb_label(text, colour, bold=True, size=10):
    """A button with no action: Desktop centres button text vertically, so every breadcrumb level (links,
    separators and the current page) sits on one line — textboxes put their text at the top instead."""
    btn = nav_button(text, "", "", fill="#FFFFFF", hover="#FFFFFF", press="#FFFFFF", font=colour, size=size, margin=0)
    btn["objects"]["text"][1]["properties"]["bold"] = b(bold)
    btn["visualContainerObjects"].pop("visualLink")
    return btn


def nav_row(pg, key):
    """Breadcrumb (Home › chapter › page) left, chapter strip right — same look as the Insights pack."""
    c = layout._code(NAMES[key])
    members = [k for k, d in PAGES if layout._code(d) and layout._code(d)[0] == c[0]]
    chap = members[0]
    x = 16
    pg.add(x, NAV_Y, _crumb_w("Home"), NAV_H, layout._crumb("Home", PID["home"], "Back to the decision center"),
           key="nav_home")
    x += _crumb_w("Home")
    for k, link in ([(chap, True)] if chap != key else []) + [(key, False)]:
        pg.add(x, NAV_Y, 18, NAV_H, layout._alt(_crumb_label("›", MUTED, bold=False, size=12), "then"), key=f"nav_sep_{k}")
        x += 18
        text = layout._label(NAMES[k])
        if link:
            pg.add(x, NAV_Y, _crumb_w(text), NAV_H, layout._crumb(text, PID[k], "Open this chapter"), key=f"nav_crumb_{k}")
        else:
            pg.add(x, NAV_Y, _crumb_w(text), NAV_H, layout._alt(_crumb_label(text, NAVY), f"You are here: {text}"),
                   key=f"nav_here_{k}")
        x += _crumb_w(text)
    if len(members) > 1:
        widths = [layout._w(layout._label(NAMES[m])) for m in members]
        x = W - 16 - sum(widths) - 6 * (len(members) - 1)
        for m, w in zip(members, widths):
            cur = m == key
            btn = nav_button(layout._label(NAMES[m]), PID[m], "You are here" if cur else "Open this page",
                             fill=ORANGE if cur else "#FFFFFF", hover=ORANGE_DK if cur else ORANGE_SOFT,
                             press=ORANGE_DK if cur else ORANGE_SOFT, font="#FFFFFF" if cur else NAVY, size=10,
                             outline=None if cur else BORDER)
            if cur:
                layout._alt(btn, f"{layout._label(NAMES[m])} (current page)")
            pg.add(x, NAV_Y, w, NAV_H, btn, key=f"nav_strip_{m}")
            x += w + 6


def next_back(pg, key):
    idx = ORDER.index(key)
    if idx + 1 < len(ORDER):
        nxt = ORDER[idx + 1]
        label = NAMES[nxt].split("·", 1)[-1].strip()
        pg.add(W - 16 - 360, Y_NEXT, 360, 36,
               nav_button(f"Next: {label}  ›", PID[nxt], "Continue the story on the next page"), key="next")
    pg.add(16, Y_NEXT, 220, 36, nav_button("‹  Decision center", PID["home"], "Back to the home page", fill="#FFFFFF",
                                           hover=ORANGE_SOFT, press=ORANGE, font=NAVY, outline=BORDER), key="back")


QUESTIONS = {}                       # page key -> its header question, for the Questions page


def story_page(key, area, question, subtitle, slicers, headline_vc):
    QUESTIONS[key] = question
    pg = Page(PID[key], NAMES[key], W, H, background_image=BG)
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
        put(pg, 16 + k * (w + 10), y + SEC_H, w, 90, vc, f"kpi_{k}")
    return y + SEC_H + 90 + GAP


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


def chapter(key, area, question, subtitle, slicers, ins_key, pulse_q, spec, headline_measure=None):
    hv = head(headline_measure) if headline_measure else grab(ins_key, "headline")
    pg = story_page(key, area, question, subtitle, slicers, hv)
    y = pulse(pg, Y_BODY, ins_key, *pulse_q)
    bands(pg, y, spec, first=2)
    next_back(pg, key)
    return pg


def deep_dive(key, area, question, subtitle, slicers, headline_measure, spec):
    pg = story_page(key, area, question, subtitle, slicers, head(headline_measure))
    bands(pg, Y_BODY, spec)
    next_back(pg, key)
    pg.page["visibility"] = "HiddenInViewMode"
    return pg


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
            ("Status reports not submitted", "PMO | Unsubmitted Status Reports", None, "lowerBetter")]


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


def build_home():
    pg = Page(PID["home"], NAMES["home"], W, H, background_image=BG)
    header(pg, "home", "BFUSION", "DECISION CENTER",
           "Start with the pulse, act on the list, then open the chapter that answers your question.",
           [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"), (DP("State_Value"), "State")])
    back = home_icon_button(PID["welcome"])
    back["visualContainerObjects"]["visualLink"][0]["properties"]["tooltip"] = s("Back to the welcome page")
    pg.add(0, 4, 60, 58, back, key="welcome")
    put(pg, 16, 86, 1768, 72, ticker(), "ticker")
    put(pg, 16, 168, 1768, 56, grab("exec", "headline"), "headline")
    y = 236
    pages.section(pg, y, 1, "What needs attention now?",
                  "The PMO command center ranks projects by what needs a decision; click one to focus every page on it.")
    put(pg, 16, y + SEC_H, 1768, 560, src("PMO | Command Center", "bfusionPMOCommandCenter"), "pmo")
    y += SEC_H + 560 + GAP
    # ② sits in a group that one toggle hides and shows (display-only bookmarks: slicer picks survive). The
    # "Hide" button lives inside the group, the "Show" button in its own group on the same spot, so exactly one
    # of the two is visible at any time.
    tw, th = 190, 30
    tx = 16 + 1768 - tw
    grp = pg.add_group(16, y, 1768, BODY_END - y, "Eight questions", "questions", hidden=True)   # hidden by default
    grp_show = pg.add_group(tx, y + 2, tw, th, "Show eight questions", "questions_show")
    bm_hide = pbir.bookmark("Hide the eight questions", "bfstory-questions-hide", pg.id, {grp: True, grp_show: False})
    bm_show = pbir.bookmark("Show the eight questions", "bfstory-questions-show", pg.id, {grp: False, grp_show: True})
    pg.add(16, y, 1768 - tw - 12, SEC_H, textbox([[(f"{pages.CIRCLED[1]}  Eight questions, one answer each",
                                                     st("Segoe UI Semibold", 15, NAVY, True)),
                                                    ("   Each card is the headline of its chapter, written from the data "
                                                     "in the current filter.", st("Segoe UI", 11, MUTED))]]),
           key="sec2", parent=grp)
    toggle = dict(fill="#FFFFFF", hover="#F3F4F6", press="#E5E7EB", font="#374151", size=10, outline="#C9CED6")
    pg.add(tx, y + 2, tw, th, pbir.bookmark_button("Hide the questions  ▲", bm_hide, "Hide the eight chapter cards",
                                                   **toggle), key="q_hide", parent=grp)
    pg.add(tx, y + 2, tw, th, pbir.bookmark_button("Show the eight questions  ▼", bm_show, "Show the eight chapter cards",
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
        pg.add(bx, by, 120, 32, _chip("Open chapter ›", PID[ck], f"Open {NAMES[ck]}"), key=f"card_open{k}", parent=grp)
        bx += 128
        for m in deep:
            lbl = layout._code(NAMES[m])[0] + layout._code(NAMES[m])[1]
            if bx + 44 > cx + cw - 8:
                break
            pg.add(bx, by, 44, 32, _chip(lbl, PID[m], NAMES[m]), key=f"card_deep{k}_{m}", parent=grp)
            bx += 50
    return pg


# ================================================================ WELCOME + QUESTIONS
# Both are one screen (1800x1000, FitToPage): the welcome page is the cover, the questions page the menu.
SH = 1000


def _logo(res, name):
    vc = image(res, name)
    vc["objects"]["image"][0]["properties"]["sourceFile"]["image"]["scaling"] = s("Fit")
    return vc


def build_welcome():
    pg = Page(PID["welcome"], NAMES["welcome"], W, SH, background_colour=INK, display_option="FitToPage")
    pg.page["objects"]["outspace"] = [{"properties": {"color": pbir.col_solid(INK), "transparency": pbir.n(0)}}]
    pg.add(0, 0, W, 8, shape(ORANGE), key="top_bar")
    x = 120
    pg.add(x, 110, 190, 120, _logo(LOGO_RES, "BFusion logo"), key="bfusion_logo")
    pg.add(x, 270, 860, 34, textbox([[("PMO DECISION PACK", st("DIN", 15, ORANGE, True))]]), key="eyebrow")
    pg.add(x, 306, 900, 96, textbox([[("Bfusion Decision Story", st("DIN", 50, "#FFFFFF", True))]]), key="title")
    pg.add(x, 410, 860, 80, textbox([[("Eight questions, one answer each: from the portfolio pulse to the decision "
                                       "you need to take today.", st("Segoe UI", 18, "#C9D2E0"))]]), key="subtitle")
    pg.add(x, 530, 380, 64, nav_button("Open the Decision Center  ›", PID["home"], "Open the decision center",
                                       size=16), key="go_home")
    pg.add(x + 400, 530, 380, 64, nav_button("Browse the questions  ›", PID["questions"],
                                             "Pick a question and open the dashboard that answers it",
                                             fill=INK, hover="#1B2C42", press="#22344D", font="#FFFFFF", size=16,
                                             outline="#FFFFFF"), key="go_questions")
    pg.add(x, 680, 400, 26, textbox([[("DATA SOURCE", st("Segoe UI Semibold", 11, "#8A97AB", True))]]), key="src_label")
    pg.add(x, 710, 211, 92, _logo(ONEPLAN_RES, "OnePlan logo"), key="oneplan_logo")
    pg.add(x + 230, 724, 560, 70, textbox([[("Portfolio, project, resource, cost and status data, read from OnePlan.",
                                             st("Segoe UI", 13, "#C9D2E0"))]]), key="src_text")
    # right: how every page reads
    px, py, pw, ph = 1080, 110, 600, 700
    pg.add(px, py, pw, ph, shape("#15263B", radius=12, line="#22344D"), key="how_bg")
    pg.add(px + 36, py + 32, pw - 72, 40, textbox([[("How every page reads", st("DIN", 22, "#FFFFFF", True))]]),
           key="how_title")
    steps = [("Pulse", "KPIs against last period, with an up or down arrow."),
             ("Act", "The list of projects that need a decision now."),
             ("Explain", "Charts and deep dives that show why."),
             ("Next", "Every page ends with the next question in the story.")]
    for k, (head_, body) in enumerate(steps):
        sy = py + 100 + k * 140
        pg.add(px + 36, sy, 56, 56, shape(ORANGE, radius=28), key=f"how_dot{k}")
        pg.add(px + 36, sy + 8, 56, 40, textbox([[(str(k + 1), st("DIN", 20, "#FFFFFF", True))]], align="center"),
               key=f"how_num{k}")
        pg.add(px + 112, sy, pw - 148, 110, textbox([[(head_, st("Segoe UI Semibold", 16, "#FFFFFF", True))],
                                                     [(body, st("Segoe UI", 13, "#C9D2E0"))]]), key=f"how_step{k}")
    pg.add(0, 860, W, 1, shape("#22344D"), key="foot_rule")
    pg.add(x, 872, 600, 30, textbox([[("bfusion.eu", st("Segoe UI", 11, "#8A97AB"))]]), key="foot_left")
    pg.add(W - 120 - 600, 872, 600, 30, textbox([[("BFUSION · Data from OnePlan · Power BI",
                                                   st("Segoe UI", 11, "#8A97AB"))]], align="right"), key="foot_right")
    return pg


def _sentence(q):
    return (q[0] + q[1:].lower()).replace(" a instead of b", " A instead of B")


# ---------------------------------------------------------------- questions page: dark bento grid
# Executive summary is the tall orange "start here" tile; the chapters with deep dives are tiles that list them;
# risk / benefits / governance (no deep dives) are wide bars. Every tile is one click to its chapter: a transparent
# button lies over the tile's text, and the deep-dive row buttons lie over that.
TILE, TILE_LINE, ROW, BADGE = "#15263B", "#22344D", "#1B2E46", "#2A3F5C"
SOFT_INK, MUTED_INK = "#AEB8C7", "#8A97AB"
ICON = {"exec": "exec", "portfolio": "portfolio", "finance": "finance", "resources": "resources",
        "schedule": "schedule", "risk": "risk", "benefits": "benefits", "governance": "governance"}
INSIDE = {"exec": ["KPI pulse", "Decisions this month", "Health matrix", "Status trend", "Chapter scorecard"]}


def _ghost(text, target, tip, font="#FFFFFF", size=10, margin=12, hover="#FFFFFF"):
    """Button with no fill of its own: the tile or row drawn under it shows through; hover lightens it."""
    btn = nav_button(text, target, tip, fill=INK, hover=hover, press=hover, font=font, size=size, align="left",
                     margin=margin)
    fills = btn["objects"]["fill"]
    fills[1]["properties"]["transparency"] = pbir.n(100)
    fills[2]["properties"]["transparency"] = pbir.n(90)
    fills[3]["properties"]["transparency"] = pbir.n(80)
    return btn


def _text(pg, x, y, w, h, text, style, key, align=None):
    pg.add(x, y, w, h, textbox([[(text, style)]], align=align), key=key)


def _icon(pg, x, y, ck, fill, key):
    pg.add(x, y, 44, 44, shape(fill, radius=10), key=f"{key}_icobg")
    pg.add(x + 9, y + 9, 26, 26, image(f"rail-{ICON[ck]}-white.png", f"{ck} icon"), key=f"{key}_ico")


def _arrow(pg, x, y, fill, ink, key):
    pg.add(x, y, 40, 40, shape(fill, radius=20), key=f"{key}_arrow")
    _text(pg, x, y + 4, 40, 32, "→", st("Segoe UI", 14, ink, True), f"{key}_arrow_t", align="center")


def _headline(pg, x, y, w, h, ck, bg, ink, key):
    hl = headline(CARD_TEXT[ck][1], bg=bg, border=bg, size=10, colour=ink)
    hl["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    pg.add(x, y, w, h, hl, key=key)


def _deep_row(pg, x, y, w, m, row, badge, badge_ink, ink, key):
    c = layout._code(NAMES[m])
    pg.add(x, y, w, 30, shape(row, radius=8), key=f"{key}_bg")
    pg.add(x + 8, y + 5, 30, 20, shape(badge, radius=6), key=f"{key}_badge")
    _text(pg, x + 8, y + 3, 30, 22, f"{c[0]}{c[1]}", st("Segoe UI", 8, badge_ink, True), f"{key}_code", align="center")
    pg.add(x, y, w, 30, layout._alt(_ghost(_sentence(QUESTIONS[m]), PID[m], f"Open {NAMES[m]}", font=ink, size=10,
                                           margin=46), f"Open {NAMES[m]}"), key=f"{key}_btn")


def _deep(ck):
    code = layout._code(NAMES[ck])[0]
    return [m for m, d in PAGES if layout._code(d) and layout._code(d)[0] == code and m != ck]


def _tile(pg, x, y, w, h, k, ck):
    code = layout._code(NAMES[ck])
    key = f"t{k}"
    pg.add(x, y, w, h, shape(TILE, radius=14, line=TILE_LINE), key=f"{key}_bg")
    _icon(pg, x + 24, y + 20, ck, TILE_LINE, key)
    _arrow(pg, x + w - 64, y + 20, ORANGE, "#FFFFFF", key)
    _text(pg, x + 20, y + 76, w - 40, 24, f"{code[0]} · {code[2].upper()}", st("Segoe UI Semibold", 9, MUTED_INK, True),
          f"{key}_lbl")
    _text(pg, x + 20, y + 98, w - 40, 44, _sentence(QUESTIONS[ck]), st("DIN", 17, "#FFFFFF", True), f"{key}_q")
    _headline(pg, x + 14, y + 140, w - 28, 46, ck, TILE, SOFT_INK, f"{key}_hl")
    _brief_link(pg, x, y, w, h, ck, key)
    for j, m in enumerate(_deep(ck)):
        _deep_row(pg, x + 20, y + 196 + j * 38, w - 40, m, ROW, BADGE, ORANGE, "#E5EAF1", f"{key}_d{j}")


def _brief_link(pg, x, y, w, h, ck, key):
    """The whole tile opens the chapter brief, which leads on to the chapter and its deep dives."""
    tip = f"Open the {layout._code(NAMES[ck])[2]} brief"
    pg.add(x, y, w, h, layout._alt(_ghost("", PID[f"brief_{ck}"], tip), tip), key=f"{key}_go")


def _start_tile(pg, x, y, w, h, ck):
    code = layout._code(NAMES[ck])
    key = "t0"
    pg.add(x, y, w, h, shape(ORANGE, radius=14), key=f"{key}_bg")
    _text(pg, x + 20, y + 22, 220, 26, "START HERE", st("Segoe UI Semibold", 10, "#FFFFFF", True), f"{key}_start")
    _arrow(pg, x + w - 64, y + 20, "#FFFFFF", ORANGE, key)
    _icon(pg, x + 24, y + 60, ck, "#EE8455", key)
    _text(pg, x + 20, y + 118, w - 40, 24, f"{code[0]} · {code[2].upper()}", st("Segoe UI Semibold", 9, "#FFFFFF", True),
          f"{key}_lbl")
    _text(pg, x + 20, y + 142, w - 40, 60, _sentence(QUESTIONS[ck]), st("DIN", 28, "#FFFFFF", True), f"{key}_q")
    _headline(pg, x + 14, y + 204, w - 28, 50, ck, ORANGE, "#FFFFFF", f"{key}_hl")
    _brief_link(pg, x, y, w, h, ck, key)
    for j, m in enumerate(_deep(ck)):
        _deep_row(pg, x + 20, y + 268 + j * 40, w - 40, m, "#EC7A4A", "#F3A27C", "#FFFFFF", "#FFFFFF", f"{key}_d{j}")
    # what the chapter holds, as chips at the foot of the tile
    cy = y + h - 150
    _text(pg, x + 20, cy, w - 40, 24, "INSIDE THIS CHAPTER", st("Segoe UI Semibold", 9, "#FFFFFF", True), f"{key}_in")
    cx, cy = x + 24, cy + 32
    for j, chip in enumerate(INSIDE[ck]):
        cw_ = round(len(chip) * 7.2 + 30)
        if cx + cw_ > x + w - 20:
            cx, cy = x + 24, cy + 36
        pg.add(cx, cy, cw_, 28, shape(ORANGE, radius=14, line="#F6B79A"), key=f"{key}_chip{j}")
        _text(pg, cx, cy + 2, cw_, 24, chip, st("Segoe UI", 9, "#FFFFFF"), f"{key}_chip{j}_t", align="center")
        cx += cw_ + 8


def _bar(pg, x, y, w, h, k, ck):
    code = layout._code(NAMES[ck])
    key = f"t{k}"
    pg.add(x, y, w, h, shape(TILE, radius=14, line=TILE_LINE), key=f"{key}_bg")
    _icon(pg, x + 20, y + (h - 44) / 2, ck, TILE_LINE, key)
    _text(pg, x + 80, y + 18, 420, 24, f"{code[0]} · {code[2].upper()}", st("Segoe UI Semibold", 9, MUTED_INK, True),
          f"{key}_lbl")
    _text(pg, x + 80, y + 42, 440, 44, _sentence(QUESTIONS[ck]), st("DIN", 17, "#FFFFFF", True), f"{key}_q")
    _headline(pg, x + 520, y + 16, w - 520 - 84, h - 32, ck, TILE, SOFT_INK, f"{key}_hl")
    _arrow(pg, x + w - 64, y + (h - 40) / 2, ORANGE, "#FFFFFF", key)
    _brief_link(pg, x, y, w, h, ck, key)


def build_questions():
    pg = Page(PID["questions"], NAMES["questions"], W, SH, background_colour=INK, display_option="FitToPage")
    pg.page["objects"]["outspace"] = [{"properties": {"color": pbir.col_solid(INK), "transparency": pbir.n(0)}}]
    pg.add(0, 0, W, 6, shape(ORANGE), key="top_bar")
    back = home_icon_button(PID["home"])
    back["visualContainerObjects"]["visualLink"][0]["properties"]["tooltip"] = s("Back to the decision center")
    pg.add(10, 26, 60, 58, back, key="home")
    _text(pg, 80, 26, 600, 26, "START HERE", st("Segoe UI Semibold", 11, ORANGE, True), "eyebrow")
    _text(pg, 80, 50, 1100, 56, "Which question do you have?", st("DIN", 30, "#FFFFFF", True), "title")
    n_q = len(CHAPTERS) + sum(len(_deep(ck)) for ck in CHAPTERS)
    _text(pg, 80, 104, 1100, 28, f"{len(CHAPTERS)} chapters, {n_q} questions. Click a tile to open its chapter, "
                                 "a row to go one level deeper.", st("Segoe UI", 11, SOFT_INK), "subtitle")
    pg.add(W - 32 - 186 - 14 - 180, 52, 180, 46,
           nav_button("‹  Welcome", PID["welcome"], "Back to the welcome page", fill=INK, hover="#1B2C42",
                      press="#22344D", font="#FFFFFF", size=11, outline="#FFFFFF", radius=23), key="back_welcome")
    pg.add(W - 32 - 186, 52, 186, 46, nav_button("Decision Center  ›", PID["home"], "Open the decision center",
                                                 size=11, radius=23), key="go_home")
    G, top, bottom = 14, 150, 900
    cw = (1768 - 3 * G) / 4
    rh = (bottom - top - G) / 2
    col = [16 + c * (cw + G) for c in range(4)]
    chap = dict(zip([layout._code(NAMES[k])[0] for k in CHAPTERS], CHAPTERS))
    _start_tile(pg, col[0], top, cw, bottom - top, chap["1"])
    for k, (num, cx, cy) in enumerate([("2", col[1], top), ("3", col[2], top), ("4", col[3], top),
                                       ("5", col[1], top + rh + G)], start=1):
        _tile(pg, cx, cy, cw, rh, k, chap[num])
    bh = (rh - 2 * G) / 3
    for j, num in enumerate("678"):
        _bar(pg, col[2], top + rh + G + j * (bh + G), 2 * cw + G, bh, 5 + j, chap[num])
    pg.add(16, 930, 1768, 1, shape(TILE_LINE), key="foot_rule")
    pg.add(16, 944, 64, 40, _logo(LOGO_RES, "BFusion logo"), key="foot_logo")
    _text(pg, W - 16 - 600, 952, 600, 26, "BFUSION · Data from OnePlan", st("Segoe UI", 9, MUTED_INK), "foot_right",
          align="right")
    return pg


# ---------------------------------------------------------------- chapter brief pages (navy navigation pages)
# One per chapter, between the Questions page and the chapter: the question, a verdict, three takeaways and one
# tile per page of the chapter. The picture top-right and the drawings in the tiles are faint line art
# (illustrations.py), so they stay behind the text.
RED, AMBER, GREEN, GREY = "#D64545", "#E0A100", "#2E9E6A", "#8A97AB"
BRIEF_FOLDER = "Story\\Brief"
# chapter -> [(value measure, label, rule)]; rule: None (no judgement) | ("hi", amber, red): higher is better,
# below red is red | ("lo", amber, red): lower is better, at or above red is red | "band": utilisation, red above
# 100%, amber below 50%. The thresholds are defaults for the PMO to confirm.
BRIEF_TAKEAWAYS = {
    "exec": [("Story | Active Projects", "active projects", None),
             ("Story | On Track %", "of active projects on track", ("hi", 0.8, 0.6)),
             ("Story | Late Active Projects", "projects running late", ("lo", 1, 5))],
    "portfolio": [("Story | Proposed Projects", "proposals in the pipeline", None),
                  ("Story | Aligned Budget %", "of budget on strongly aligned work", ("hi", 0.7, 0.5)),
                  ("Story | Plan Variance %", "plan forecast against plan budget", ("lo", 0.0001, 0.05))],
    "finance": [("Story | EAC Variance %", "forecast against budget at completion", ("lo", 0.0001, 0.05)),
                ("Story | Projects Over Budget", "projects over budget", ("lo", 1, 5)),
                ("Story | Burn %", "of the budget spent", None)],
    "resources": [("Story | Utilisation %", "utilisation of capacity", "band"),
                  ("Story | Over-allocated People", "people over-allocated", ("lo", 1, 5)),
                  ("Story | Free Capacity (h)", "hours of free capacity", None)],
    "schedule": [("Story | On Schedule %", "of active projects on schedule", ("hi", 0.8, 0.6)),
                 ("Story | Overdue Tasks", "overdue tasks", ("lo", 1, 20)),
                 ("Story | Milestones Next 30d", "milestones in the next 30 days", None)],
    "risk": [("Story | Critical High Risks", "critical or high risks", ("lo", 1, 5)),
             ("Story | Unmitigated Risk %", "of risks without mitigation", ("lo", 0.2, 0.4)),
             ("Story | Open Issues", "open issues", ("lo", 1, 10))],
    "benefits": [("Story | Benefits Realised %", "of benefits due realised", ("hi", 0.9, 0.7)),
                 ("Story | Value Ratio", "value per euro of forecast cost", ("hi", 2, 1)),
                 ("Story | Benefits At Completion", "benefits planned at completion", None)],
    "governance": [("PMO | Governance Score", "governance score", ("hi", 80, 60)),
                   ("PMO | Compliance %", "compliance", ("hi", 0.9, 0.75)),
                   ("PMO | Unsubmitted Status Reports", "status reports not submitted", ("lo", 1, 10))],
}
BRIEF_BLURB = {
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
}
_BRIEF_MEASURES = None


def _colour_dax(m, rule):
    if rule is None:
        return f'"{ORANGE}"'
    v = f"VAR _v = [{m}]\nRETURN IF ( ISBLANK ( _v ), \"{GREY}\", "
    if rule == "band":
        return v + f'IF ( _v > 1, "{RED}", IF ( _v < 0.5, "{AMBER}", "{GREEN}" ) ) )'
    kind, amber, red = rule
    if kind == "hi":
        return v + f'IF ( _v < {red}, "{RED}", IF ( _v < {amber}, "{AMBER}", "{GREEN}" ) ) )'
    return v + f'IF ( _v >= {red}, "{RED}", IF ( _v >= {amber}, "{AMBER}", "{GREEN}" ) ) )'


_MODEL_FORMATS = {"PMO | Governance Score": "0", "PMO | Compliance %": "0.0%", "PMO | Unsubmitted Status Reports": "#,##0"}


def _value_dax(m):
    fmt = _MODEL_FORMATS.get(m) or next(x["formatString"] for x in story_measures.MEASURES if x["name"] == m)
    head = f'VAR _v = [{m}]\nRETURN IF ( ISBLANK ( _v ), "–", '
    if "%" in fmt or "." in fmt:
        return head + f'FORMAT ( _v, "{fmt}" ) )'
    return head + ('IF ( ABS ( _v ) >= 1000000, FORMAT ( _v / 1000000, "#,##0.0" ) & "M", '
                   'IF ( ABS ( _v ) >= 10000, FORMAT ( _v / 1000, "#,##0" ) & "K", FORMAT ( _v, "#,##0" ) ) ) )')


def _brief_measure(name, expr, fmt, desc):
    full = f"Story | Brief · {name}"
    story_measures.add(full, story_measures.D if fmt else story_measures.T, expr, fmt, BRIEF_FOLDER, desc)
    pbir.EXTENSION_MEASURES.add(full)
    return full


def brief_measures():
    """{chapter: ([takeaway colour measures], verdict, verdict colour, [takeaway value texts])}; registered once."""
    global _BRIEF_MEASURES
    if _BRIEF_MEASURES is None:
        _BRIEF_MEASURES = {}
        for ch, items in BRIEF_TAKEAWAYS.items():
            label = layout._code(NAMES[ch])[2]
            cols = [_brief_measure(f"{label} {k + 1} Colour", _colour_dax(m, rule), None,
                                   f"Dot colour for the takeaway '{lbl}': {rule or 'no judgement'}.")
                    for k, (m, lbl, rule) in enumerate(items)]
            judged = [c for c, (_, _, rule) in zip(cols, items) if rule]
            count = lambda colour: " + ".join(f'INT ( [{c}] = "{colour}" )' for c in judged)  # noqa: E731
            head = f"VAR _r = {count(RED)}\nVAR _a = {count(AMBER)}\nVAR _g = {count(GREEN)}\nRETURN "
            verdict = _brief_measure(f"{label} Verdict", head + 'IF ( _r > 0, "ACT", IF ( _a > 0, "WATCH", '
                                     'IF ( _g > 0, "ON TRACK", "NO DATA" ) ) )', None,
                                     "ACT when a takeaway is red, WATCH when one is amber, else ON TRACK.")
            vcol = _brief_measure(f"{label} Verdict Colour", head + f'IF ( _r > 0, "{RED}", IF ( _a > 0, "{AMBER}", '
                                  f'IF ( _g > 0, "{GREEN}", "{GREY}" ) ) )', None, "Colour of the verdict pill.")
            texts = [_brief_measure(f"{label} {k + 1} Value", _value_dax(m), None,
                                    f"[{m}] as text for the brief: a dash when blank, M / K for large numbers.")
                     for k, (m, _, _) in enumerate(items)]
            _BRIEF_MEASURES[ch] = (cols, verdict, vcol, texts)
    return _BRIEF_MEASURES


def _fx(measure):
    return {"solid": {"color": {"expr": M(measure)}}}


def _value_card(measure, size, colour, bg=None):
    vc = headline(measure, bg=bg or INK, border=bg or INK, size=size, colour=colour)
    vc["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    if bg is None:
        vc["visualContainerObjects"]["background"] = [{"properties": {"show": b(False)}}]
    vc["objects"]["labels"][0]["properties"]["fontFamily"] = s("DIN")
    return vc


def _dot(pg, x, y, d, measure, key):
    vc = shape(GREY, radius=d // 2)
    vc["objects"]["fill"][0]["properties"]["fillColor"] = _fx(measure)
    pg.add(x, y, d, d, vc, key=key)


def _crumb(pg, x, text, target, tip, key, colour=SOFT_INK, bold=False, size=10, w=None, align="center"):
    """One breadcrumb level. Every level, separators and the current page included, is a button: Desktop centres
    button text vertically, so all levels sit on one line (a text box puts its text at the top instead)."""
    w = w or _crumb_w(text) - 16
    btn = nav_button(text, target, tip, fill=INK, hover="#1B2C42" if target else INK, press="#22344D" if target else INK,
                     font=colour, size=size, margin=4, align=align)
    btn["objects"]["text"][1]["properties"]["bold"] = b(bold)
    if not target:
        btn["visualContainerObjects"].pop("visualLink")
    pg.add(x, 26, w, 32, layout._alt(btn, tip), key=key)
    return x + w


def _tile_text(m):
    """(eyebrow, question, blurb) of a navigation tile on a brief page."""
    if m.startswith("brief_"):
        nxt = m[len("brief_"):]
        return f"NEXT QUESTION · {layout._code(NAMES[nxt])[2].upper()}", _sentence(QUESTIONS[nxt]), BRIEF_BLURB[nxt]
    if m == "home":
        return "THE DECISION CENTER", "What needs a decision now?", "The pulse, the list to act on, every chapter"
    if m == "questions":
        return "ALL QUESTIONS", "Which question do you have?", "Every chapter and deep dive on one page"
    c = layout._code(NAMES[m])
    return ("START WITH THE CHAPTER" if not c[1] else f"DEEP DIVE {c[0]}{c[1]}"), _sentence(QUESTIONS[m]), BRIEF_BLURB[m]


def _tile_art(m):
    if m.startswith("brief_"):
        return illustrations.spot_file(m[len("brief_"):])
    return illustrations.spot_file({"home": "exec", "questions": "kpigrid"}.get(m, m))


def build_brief(ch):
    key = f"brief_{ch}"
    code = layout._code(NAMES[ch])
    cols, verdict, vcol, texts = brief_measures()[ch]
    pg = Page(PID[key], NAMES[key], W, SH, background_colour=INK, display_option="FitToPage")
    pg.page["objects"]["outspace"] = [{"properties": {"color": pbir.col_solid(INK), "transparency": pbir.n(0)}}]
    pg.page["visibility"] = "HiddenInViewMode"
    pg.add(0, 0, W, 6, shape(ORANGE), key="top_bar")
    pg.add(1000, 70, illustrations.SCENE_W, illustrations.SCENE_H,
           _logo(illustrations.scene_file(ch), f"{code[2]} illustration"), key="scene")
    # home (welcome page) + breadcrumb + all questions
    pg.add(24, 22, 44, 44, shape(ORANGE, radius=12), key="home_bg")
    pg.add(34, 32, 24, 24, _logo(illustrations.HOME_FILE, "Home icon"), key="home_ico")
    pg.add(24, 22, 44, 44, layout._alt(_ghost("", PID["welcome"], "Back to the welcome page", hover=INK),
                                       "Back to the welcome page"), key="home")
    x = _crumb(pg, 80, "Welcome", PID["welcome"], "Back to the welcome page", "crumb_welcome")
    x = _crumb(pg, x, "›", "", "then", "crumb_sep1", size=12, w=18)
    x = _crumb(pg, x, "Questions", PID["questions"], "All questions", "crumb_questions")
    x = _crumb(pg, x, "›", "", "then", "crumb_sep2", size=12, w=18)
    here = f"{code[0]} · {code[2]}"
    _crumb(pg, x, here, "", f"You are here: {here}", "crumb_here", colour="#FFFFFF", bold=True, w=_crumb_w(here),
           align="left")
    pg.add(W - 32 - 190, 22, 190, 44, nav_button("‹  All questions", PID["questions"], "Back to all questions",
                                                 fill=INK, hover="#1B2C42", press="#22344D", font="#FFFFFF", size=11,
                                                 outline="#FFFFFF", radius=22), key="all_questions")
    # question, verdict, headline
    q = _sentence(QUESTIONS[ch])
    dy = 40 if len(q) * 29 <= 760 else 0               # one line of 44 pt DIN: centre it in the two-line slot
    _text(pg, 80, 128 + dy, 900, 28, f"CHAPTER {code[0]} · {code[2].upper()}",
          st("Segoe UI Semibold", 11, ORANGE, True), "eyebrow")
    _text(pg, 80, 158 + dy, 780, 150, q, st("DIN", 44, "#FFFFFF", True), "question")
    pg.add(84, 310, 900, 68, shape("#15263B", radius=34, line=TILE_LINE), key="verdict_bg")
    pill = _value_card(verdict, 10, "#FFFFFF", bg=GREY)
    pill["visualContainerObjects"]["background"] = [{"properties": {"show": b(True), "color": _fx(vcol)}}]
    pill["visualContainerObjects"]["border"] = [{"properties": {"show": b(True), "color": _fx(vcol), "radius": pbir.n(16)}}]
    pill["objects"]["labels"][0]["properties"]["fontFamily"] = s("Segoe UI Semibold")
    pg.add(96, 320, 140, 48, pill, key="verdict")
    pg.add(246, 314, 728, 60, _value_card(CARD_TEXT[ch][1], 11, "#E5EAF1"), key="headline")
    # three takeaways
    tw = (900 - 2 * 12) / 3
    for k, (m, lbl, _rule) in enumerate(BRIEF_TAKEAWAYS[ch]):
        tx, ty = 84 + k * (tw + 12), 392
        pg.add(tx, ty, tw, 136, shape("#15263B", radius=14, line=TILE_LINE), key=f"take{k}_bg")
        _dot(pg, tx + 18, ty + 20, 14, cols[k], f"take{k}_dot")
        pg.add(tx + 36, ty + 10, tw - 72, 72, _value_card(texts[k], 24, "#FFFFFF"), key=f"take{k}_val")
        _text(pg, tx + 12, ty + 86, tw - 24, 40, lbl, st("Segoe UI", 11, SOFT_INK), f"take{k}_lbl", align="center")
    # one tile per page of the chapter: the chapter first, then its deep dives
    keys = [ch] + _deep(ch)
    if len(keys) == 1:                                  # one-page chapter: offer the next question and the list too
        nxt = CHAPTERS[CHAPTERS.index(ch) + 1] if ch != CHAPTERS[-1] else None
        keys += [f"brief_{nxt}" if nxt else "home", "questions"]
    n = len(keys)
    gap, ty, th = 18, 560, 340
    tw = (W - 48 - gap * (n - 1)) / n
    qsize = {1: 30, 2: 26, 3: 22, 4: 19, 5: 17}[n]
    for k, m in enumerate(keys):
        tx = 24 + k * (tw + gap)
        main = m == ch
        pg.add(tx, ty, tw, th, shape(ORANGE if main else "#15263B", radius=20, line=None if main else TILE_LINE),
               key=f"tile{k}_bg")
        pg.add(tx + tw - 176, ty + 8, 168, 168, _logo(_tile_art(m), "Tile drawing"), key=f"tile{k}_art")
        eyebrow, question, blurb = _tile_text(m)
        _text(pg, tx + 26, ty + 24, tw - 52, 26, eyebrow, st("Segoe UI Semibold", 10, "#FFFFFF" if main else ORANGE, True),
              f"tile{k}_eyebrow")
        _text(pg, tx + 24, ty + th - 172, tw - 48, 96, question, st("DIN", qsize, "#FFFFFF", True), f"tile{k}_q")
        _text(pg, tx + 24, ty + th - 76, tw - 120, 56, blurb,
              st("Segoe UI", 10, "#FFE6D8" if main else SOFT_INK), f"tile{k}_blurb")
        pg.add(tx + tw - 80, ty + th - 80, 52, 52, shape("#FFFFFF" if main else ORANGE, radius=26), key=f"tile{k}_arrow")
        _text(pg, tx + tw - 80, ty + th - 74, 52, 40, "→", st("Segoe UI", 16, ORANGE if main else "#FFFFFF", True),
              f"tile{k}_arrow_t", align="center")
        tip = f"Open {NAMES[m]}"
        pg.add(tx, ty, tw, th, layout._alt(_ghost("", PID[m], tip), tip), key=f"tile{k}_go")
    pg.add(16, 930, 1768, 1, shape(TILE_LINE), key="foot_rule")
    pg.add(16, 944, 64, 40, _logo(LOGO_RES, "BFusion logo"), key="foot_logo")
    _text(pg, W - 16 - 600, 952, 600, 26, "BFUSION · Data from OnePlan", st("Segoe UI", 9, MUTED_INK), "foot_right",
          align="right")
    return pg


# ================================================================ 1 EXECUTIVE
def _exec_where_next(pg, x, y, w, h):
    chaps = [k for k in CHAPTERS if k != "exec"]
    bw = (w - 10 * (len(chaps) - 1)) / len(chaps)
    for k, ck in enumerate(chaps):
        pg.add(round(x + k * (bw + 10), 2), y, round(bw, 2), 48,
               nav_button(NAMES[ck] + "  ›", PID[ck], "Open this chapter", fill=NAVY, hover=NAVY_BTN, press=ORANGE,
                          font="#FFFFFF", size=10), key=f"chap{k}")
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
    pg = Page(PID["timesheets"], NAMES["timesheets"], W, H, background_image=BG)
    QUESTIONS["timesheets"] = question
    header(pg, "timesheets", area, question, subtitle, slicers)
    nav_row(pg, "timesheets")
    skip = {uid(ins.id, k, t) for k in ("home", "title", "subtitle", "next", "back")
            for t in ("actionButton", "textbox")}
    body = [v for v in ins.visuals if v["name"] not in skip and v["position"]["y"] >= 80 and not v.get("parentGroupName")
            and v.get("visual", {}).get("visualType") != "actionButton"]
    for k, vc in enumerate(sorted(body, key=lambda v: (v["position"]["y"], v["position"]["x"]))):
        p = vc["position"]
        y = p["y"] + (Y_HEAD - 84)
        h = min(p["height"], BODY_END - y)
        if h < 0.6 * p["height"]:
            raise ValueError(f"timesheets: {vc['name']} loses too much height")
        put(pg, p["x"], y, p["width"], h, vc, f"ts{k}")
    next_back(pg, "timesheets")
    pg.page["visibility"] = "HiddenInViewMode"
    return pg


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


BUILDERS = {**{f"brief_{c}": (lambda c=c: build_brief(c)) for c in BRIEF_TAKEAWAYS},
            "welcome": build_welcome, "home": build_home, "questions": build_questions, "exec": build_exec, "health": build_health, "roadmap": build_roadmap,
            "drift": build_drift, "kpigrid": build_kpigrid, "portfolio": build_portfolio, "selection": build_selection,
            "scenarios": build_scenarios, "constraints": build_constraints, "finance": build_finance,
            "fintree": build_fintree, "budgetrisk": build_budgetrisk, "resources": build_resources, "fte": build_fte,
            "org": build_org, "timesheets": build_timesheets, "mywork": build_mywork, "schedule": build_schedule,
            "critical": build_critical, "psr": build_psr, "risk": build_risk, "benefits": build_benefits,
            "governance": build_governance}


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


def build_pages():
    pbir.BOOKMARKS.clear()
    # the questions and brief pages read every page's header question, so they are built last, in story order
    late = [k for k, _ in PAGES if k == "questions" or k.startswith("brief_")]
    done = {k: BUILDERS[k]() for k, _ in PAGES if k not in late}
    done.update({k: BUILDERS[k]() for k in late})
    built = [done[k] for k, _ in PAGES]
    copy_interactions(built)
    pages.filter_real_projects(built)
    a11y.apply(built)
    return built


# ================================================================ write
def custom_types(built):
    return sorted({vc["visual"]["visualType"] for pg in built for vc in pg.visuals
                   if vc.get("visual", {}).get("visualType", "").startswith(("bfusion", "portfolioRoadmap"))})


def write(built):
    out = build.write_report(NAME, built, pbir.BOOKMARKS, OUT_DIR)
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
    reg = next(p for p in rep["resourcePackages"] if p["type"] == "RegisteredResources")
    reg["items"].append({"name": LOGO_RES, "path": LOGO_RES, "type": "Image"})
    shutil.copy(LOGO_FILE, out / "StaticResources" / "RegisteredResources" / LOGO_RES)
    for f in illustrations.files():
        reg["items"].append({"name": f, "path": f, "type": "Image"})
        shutil.copy(illustrations.OUT / f, out / "StaticResources" / "RegisteredResources" / f)
    build.dump(rj, rep)
    for name in used:
        shutil.copytree(SRC / "CustomVisuals" / name, out / "CustomVisuals" / name)
    return out


def path_errors(out):
    """Power BI Desktop refuses files whose full path is longer than MAX_PATH characters."""
    return [f"PATH {len(str(f))} chars > {MAX_PATH}: {f}" for f in out.rglob("*") if len(str(f)) > MAX_PATH]


def layout_errors(built):
    errs = []
    for pg in built:
        banded = "image" in pg.page["objects"].get("background", [{}])[0].get("properties", {})
        limit = round(pg.page["height"] * (0.928 if banded else 1))   # top of the footer band, if the page has one
        for vc in pg.visuals:
            p = vc["position"]
            if p["x"] < 0 or p["x"] + p["width"] > W + 0.5 or p["y"] + p["height"] > limit:
                errs.append(f"LAYOUT {pg.display}: {vc['name']} at {p} outside page/footer")
    return errs


def reach_errors(built):
    """Every page must be reachable in one click from Home or from its chapter page."""
    links = {}
    for pg in built:
        for vc in pg.visuals:
            vl = vc.get("visual", {}).get("visualContainerObjects", {}).get("visualLink")
            if vl:
                tgt = vl[0]["properties"].get("navigationSection")
                if tgt:
                    links.setdefault(pg.id, set()).add(tgt["expr"]["Literal"]["Value"].strip("'"))
    errs = []
    for k, _ in PAGES:
        chap = k if not layout._code(NAMES[k]) else [m for m, d in PAGES if layout._code(d)
                                                     and layout._code(d)[0] == layout._code(NAMES[k])[0]][0]
        hubs = (links.get(PID["home"], set()) | links.get(PID["welcome"], set()) | links.get(PID["questions"], set())
                | links.get(PID[chap], set()))
        if k != "welcome" and PID[k] not in hubs:
            errs.append(f"REACH {NAMES[k]}: no link from Welcome, Home or its chapter")
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
    pages_ = build_pages()
    out = write(pages_)
    print(f"built {len(pages_)} pages, {sum(len(p.visuals) for p in pages_)} visuals, "
          f"{len(custom_types(pages_))} custom visual types -> {out}")
    if "--check" in sys.argv:
        inh = inherited_measures()
        for m in sorted(inh):
            print(f"WARN inherited from the source pack, not in the local model snapshot: {m}")
        _load = build.load_model
        build.load_model = lambda: (_load()[0], _load()[1] | inh)
        e = build.check(pages_, out) or 0
        more = layout_errors(pages_) + reach_errors(pages_) + path_errors(out)
        for m in more:
            print(m)
        tot = e + len(more)
        print("OK" if tot == 0 else f"FAILED ({tot} problem(s))")
        sys.exit(1 if tot else 0)
