"""Page layouts for the BFusion Insights pack — one story per subject area.

Every analytic page follows the same narrative grammar (copied from the
Timesheet Dashboard in OneDashboards - Bfusion):
  header (AREA | QUESTION?) -> orange headline sentence (measure) ->
  ① the pulse (KPI cards) -> ② trend / composition -> ③ drivers -> ④ the list to act on
  -> "Next chapter" button.
"""
from pbir import *  # noqa: F401,F403
import pbir

W = 1800
TALL = 1800
BG_TALL = "bfv5_footer_band_1800x1800.png"

PAGES = [  # (key, display name) — the story order; "Next chapter" follows this list
    ("home", "Home — Story Navigator"),
    ("exec", "1 · Executive Summary"),
    ("portfolio", "2 · Portfolio"),
    ("lifecycle", "2b · Pipeline, Gates & Dependencies"),
    ("scenarios", "2c · Scenario Comparison"),
    ("onepager", "2d · Project One-Pager"),
    ("finance", "3 · Financials"),
    ("finance2", "3b · Pareto & Portfolio P&L"),
    ("resources", "4 · Resource Management"),
    ("timesheets", "4b · Timesheets vs Plan"),
    ("tsstatus", "4c · Timesheet Status"),
    ("resource", "4d · Resource Detail"),
    ("schedule", "5 · Planning & Scheduling"),
    ("gantt", "5b · Gantt View"),
    ("status", "5c · Status-Report Trend"),
    ("baseline", "5d · Plan vs Baseline"),
    ("risk", "6 · Risk Management"),
    ("benefits", "7 · Benefits & Value"),
    ("governance", "8 · Governance & Data Trust"),
]
# Pages outside the story flow: drill-through and report-page tooltips (hidden in view mode)
HIDDEN_PAGES = [
    ("project", "Project One-Pager (drill-through)"),
    ("tip_project", "Tooltip · Project"),
    ("tip_resource", "Tooltip · Resource"),
    ("resource_dt", "Resource Detail (drill-through)"),
]
PID = {k: uid("insights-page", k) for k, _ in PAGES + HIDDEN_PAGES}
# Home tiles: chapters with follow-on pages, and the short button labels used on the tile
SUBPAGES = {"portfolio": ["lifecycle", "scenarios", "onepager"], "finance": ["finance2"], "resources": ["timesheets", "tsstatus", "resource"],
            "schedule": ["gantt", "status", "baseline"]}
SHORT = {"portfolio": "Portfolio", "lifecycle": "Gates", "scenarios": "Scenarios", "finance": "Spend",
         "finance2": "Pareto & P&L", "resources": "People", "timesheets": "Time", "tsstatus": "TS status", "resource": "Person", "gantt": "Gantt", "schedule": "Schedule",
         "status": "Status trend", "onepager": "Project", "baseline": "Baseline"}
ORDER = [k for k, _ in PAGES]

# ---------------------------------------------------------------- common bits
DP = lambda p: C("DimProject", p)  # noqa: E731
DT = lambda p: C("DimTask", p)  # noqa: E731
DR = lambda p: C("DimResource", p)  # noqa: E731
MONTH = C("DimDate", "MonthStart")
CIRCLED = "①②③④⑤"


TITLE_MAX = 45      # "AREA | QUESTION?" in DIN 24 fits the 960px title box up to ~45 characters
SUBTITLE_MAX = 130  # Segoe UI 11 on one line in the 975px subtitle box


def header(pg, area, question, subtitle, slicers):
    pg.add(0, 4, 60, 58, home_icon_button(PID["home"]), key="home")
    tsize = 24 if len(f"{area} | {question}") <= TITLE_MAX else 20
    pg.add(62, 8, 960, 46, textbox([[(f"{area} | ", st("DIN", tsize, ORANGE, True)),
                                      (question, st("DIN", tsize, NAVY, True))]]), key="title")
    ssize = 11 if len(subtitle) <= SUBTITLE_MAX else 10
    pg.add(62, 52, 975, 26, textbox([[(subtitle, st("Segoe UI", ssize, MUTED))]]), key="subtitle")
    x = W - 16 - len(slicers) * 188 + 8
    for k, sl in enumerate(slicers):
        # (field, label) or (field, label, sync group name) for a slicer outside the report-wide sync
        field, label = sl[0], sl[1]
        group = sl[2] if len(sl) > 2 else None
        pg.add(x + k * 188, 10, 180, 62, slicer(field, label, group=group), key=f"slicer{k}")


def section(pg, y, num, question, explain, width=1768, x=16):
    pg.add(x, y, width, 34, textbox([[(f"{CIRCLED[num - 1]}  {question}", st("Segoe UI Semibold", 15, NAVY, True)),
                                      (f"   {explain}", st("Segoe UI", 11, MUTED))]]), key=f"sec{num}")


def kpi_row(pg, y, items, h=90, x0=16, width=1768, gap=10):
    w = (width - gap * (len(items) - 1)) / len(items)
    for k, it in enumerate(items):
        measure, label = it[0], it[1]
        opts = it[2] if len(it) > 2 else {}
        pg.add(round(x0 + k * (w + gap), 2), y, round(w, 2), h, card(measure, label, **opts), key=f"kpi{y}_{k}")


def next_chapter(pg, key, y):
    idx = ORDER.index(key)
    if idx + 1 < len(ORDER):
        nxt = ORDER[idx + 1]
        label = dict(PAGES)[nxt].split("·", 1)[-1].strip()
        pg.add(W - 16 - 340, y, 340, 36, nav_button((f"Next chapter: {label}  ›" if len(label) <= 26 else f"Next: {label}  ›"), PID[nxt],
                                                     "Continue the story on the next page"), key="next")
    pg.add(16, y, 220, 36, nav_button("‹  Story navigator", PID["home"], "Back to the home page",
                                      fill="#FFFFFF", hover=ORANGE_SOFT, press=ORANGE, font=NAVY, outline=BORDER),
           key="back")


def legend_note(pg, x, y, w, items, key):
    runs = []
    for k, (label, colour) in enumerate(items):
        runs.append(("■ " if k == 0 else "     ■ ", st("Segoe UI", 12, colour)))
        runs.append((label, st("Segoe UI", 10, colour, True)))
    pg.add(x, y, w, 28, textbox([runs], align="right"), key=key)


def analytic_page(key, area, question, subtitle, slicers, headline_measure):
    pg = Page(PID[key], dict(PAGES)[key], W, TALL, background_image=BG_TALL)
    header(pg, area, question, subtitle, slicers)
    pg.add(16, 84, 1768, 56, headline(headline_measure), key="headline")
    return pg


# Money / people pages: Year filters FactCost and FactCapacity/FactResourcePlan.
STD_SLICERS = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (DP("ProjectType_Value"), "Project type"), (C("DimDate", "Year"), "Year")]
# Project-attribute pages (portfolio, schedule, risk, benefits): DimDate filters nothing there, so no Year.
PROJ_SLICERS = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
                (DP("ProjectType_Value"), "Project type"), (DP("State_Value"), "State")]
PROJECT_TASKS = f_not_blank("DimTask", "ProjectKey")  # D-04: project plans only
# Per-project rankings: hide the blank DimProject row that collects FactCost of non-project plans.
REAL_PROJECTS = f_not_blank("DimProject", "Id")
# FactPlanInsight: non-project plans carry ProjectKey -1, so project plans = ProjectKey > 0.
PROJECT_INSIGHTS = f_cmp("FactPlanInsight", "ProjectKey", 1, 0, int64=True)
FILL_ALL = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}


def one_axis():
    """Combo charts comparing like with like (hours vs hours) share one value axis."""
    return [{"properties": {"secShow": b(False)}}]

Y1, Y1K = 150, 188           # ① section + KPI row
Y2, Y2V, H2 = 294, 334, 340  # ② section + visuals
Y3, Y3V, H3 = 690, 730, 400  # ③
Y4, Y4V, H4 = 1146, 1186, 400  # ④
YNEXT = 1606


# ================================================================= HOME
def build_home():
    pg = Page(PID["home"], dict(PAGES)["home"], W, 1000, background_colour=NAVY_BG, display_option="FitToPage")
    # brand mark (equaliser bars like the Pulse home page)
    for k, (x, h) in enumerate([(40, 10), (48, 17), (56, 13), (64, 20), (72, 9)]):
        pg.add(x, 30 - h / 2 + 5, 5, h, shape(ORANGE), key=f"bar{k}")
    pg.add(87, 16, 240, 41, textbox([[("BFUSION", st("DIN", 18, "#FFFFFF", True))]]), key="brand")
    pg.add(1648, 12, 125, 55, image("OnePlan_logo_-_dark_background9901469509814106.png", "OnePlan logo"), key="logo")
    pg.add(40, 52, 1100, 60, textbox([[("PPM Insights 360°", st("DIN", 28, "#FFFFFF", True)),
                                       ("   native story pack", st("DIN", 16, PEACH, False))]]), key="title")
    pg.add(40, 108, 1300, 32, textbox([[("Eight chapters, one question each. Read the orange headline first, "
                                         "then follow ① → ④ down the page to the list you act on.",
                                         st("Segoe UI", 12, SLATE))]]), key="sub")
    pg.add(40, 146, 1720, 1, shape(NAVY_LINE), key="rule1")
    # pulse strip
    pulse = [("Story | Active Projects", "Active projects", {}),
             ("Story | On Track %", "Active projects on track", {}),
             ("Story | EAC Variance %", "EAC vs budget", {"colour_measure": "Story | Variance Colour"}),
             ("Story | Utilisation %", "Utilisation (org-wide)", {"colour_measure": "Story | Util Colour"}),
             ("Story | Critical High Risks", "Critical / high risks", {"value_colour": "#FF8A80"}),
             ("Story | Benefits Realised KPI", "Benefits realised vs due", {"size": 18})]
    w = (1720 - 5 * 12) / 6
    for k, (m, label, o) in enumerate(pulse):
        o = dict(o)
        o.setdefault("value_colour", "#FFFFFF")
        o.setdefault("size", 22)
        pg.add(round(40 + k * (w + 12), 2), 158, round(w, 2), 84, card(m, label, dark=True, **o), key=f"pulse{k}")
    # chapter tiles 4 x 2
    tiles = [
        ("exec", "Are we on course?", "Executive board · monthly",
         "One number per question, the three decisions this month asks for."),
        ("portfolio", "Are we funding the right work?", "Portfolio board · quarterly",
         "Where the money goes, strategic fit, value versus priority."),
        ("finance", "Are we spending as planned?", "Finance & PMO · monthly close",
         "Budget, EAC and variance at completion, budget to date — then Pareto and the portfolio P&L."),
        ("resources", "Do we have the people?", "Resource managers · monthly",
         "Capacity against scheduled work, who is overloaded, where committed and scheduled hours disagree."),
        ("schedule", "Will we deliver on time?", "Delivery leads · weekly",
         "Schedule health, milestones, late work — and plan vs baseline: cost, days, hours, FTE."),
        ("risk", "What could go wrong?", "Risk owners · fortnightly",
         "Heat map, exposure concentration and the risks to escalate."),
        ("benefits", "Will it pay off?", "Sponsors & benefit owners · quarterly",
         "Planned benefits against EAC, benefits due to date and what is actually realised."),
        ("governance", "Can we trust the data?", "PMO · weekly",
         "Governance score, failing OnePlan insight rules, hygiene gaps."),
    ]
    tw, th, gx, gy = (1720 - 3 * 20) / 4, 330, 20, 20
    for k, (pk, q, who, what) in enumerate(tiles):
        col, row = k % 4, k // 4
        x = round(40 + col * (tw + gx), 2)
        y = 262 + row * (th + gy)
        pg.add(x, y, round(tw, 2), th, shape(NAVY_TILE, radius=8, line=NAVY_LINE), key=f"tile{k}")
        pg.add(x, y, 4, th, shape(ORANGE), key=f"tilebar{k}")
        pg.add(x + 18, y + 14, 60, 34, textbox([[(f"0{k + 1}", st("DIN", 20, ORANGE, True))]]), key=f"tnum{k}")
        pg.add(x + 18, y + 50, round(tw - 36, 2), 90, textbox([[(q, st("DIN", 19, "#FFFFFF", True))]]), key=f"tq{k}")
        pg.add(x + 18, y + 142, round(tw - 36, 2), 30, textbox([[(who, st("Segoe UI", 10, PEACH, True))]]), key=f"tw{k}")
        pg.add(x + 18, y + 174, round(tw - 36, 2), 80, textbox([[(what, st("Segoe UI", 11, SLATE))]]), key=f"td{k}")
        # a chapter with follow-on pages gets one button per page on its tile
        keys = [pk] + SUBPAGES.get(pk, [])
        bw_ = round((tw - 36 - 8 * (len(keys) - 1)) / len(keys), 2)
        # Segoe UI Bold ≈ 7 px/char at 10pt, 6.3 at 9pt. Only the first button carries the chapter number
        # ("4 · People ›"); follow-on buttons show the short name ("Time ›"). Four buttons (≈ 89 px each) need 9pt
        # and a 4 px left margin; three (≈ 121 px) fit at 10pt with 8 px; one or two keep 11pt / 12 px.
        size, margin = (9, 4) if len(keys) > 3 else (10, 8) if len(keys) > 2 else (11, 12)
        for j, kk in enumerate(keys):
            if len(keys) == 1:
                label = f"Open chapter {k + 1}  ›"
            elif j == 0:
                label = dict(PAGES)[kk].split(" · ")[0] + " · " + SHORT[kk] + " ›"
            else:
                label = SHORT[kk] + " ›"
            pg.add(round(x + 18 + j * (bw_ + 8), 2), y + th - 56, bw_, 38,
                   nav_button(label, PID[kk], what if j == 0 else dict(PAGES)[kk], fill=NAVY_BTN, hover=NAVY_BTN,
                              press=ORANGE, font=PEACH, align="left", outline=ORANGE, size=size, margin=margin),
                   key=f"tb{k}" + ("" if j == 0 else f"_{kk}"))
    pg.add(40, 952, 1720, 1, shape(NAVY_LINE), key="rule2")
    pg.add(40, 960, 400, 31, textbox([[("BFUSION  ·  bfusion.eu", st("Segoe UI", 9, SLATE, True))]]), key="foot1")
    pg.add(960, 958, 800, 34, headline("Story | Refreshed", bg=NAVY_BG, border=NAVY_BG, size=9, colour=SLATE), key="foot2")
    return pg


def people_combo(ttl):
    """Capacity (columns) against scheduled and committed hours on project plans (lines), organisation-wide, on ONE
    axis. Committed is a separate resource-manager figure, not a subset of scheduled — it can sit above it."""
    cap, sch, com = M("Capacity | Resource Capacity"), M("Story | Scheduled Hours"), M("Story | Committed Hours")
    return chart("lineClusteredColumnComboChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(cap, "Capacity (h)")],
         "Y2": [P(sch, "Scheduled (h)"), P(com, "Committed (h)")]},
        ttl,
        {"dataPoint": [measure_fill(cap, "#D9DDE3"), measure_fill(sch, NAVY), measure_fill(com, TEAL)],
         "legend": legend("Top"), "valueAxis": one_axis(),
         "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}]},
        sort=[(MONTH, "Ascending")])


# ================================================================= 1 EXECUTIVE
def build_exec():
    pg = analytic_page("exec", "EXECUTIVE", "ARE WE ON COURSE?",
                       "Health, money, people and risk on one page. Year filters money and people only; people KPIs are organisation-wide.",
                       STD_SLICERS, "Story | Exec Headline")
    section(pg, Y1, 1, "The pulse — one number per question",
            "Green is fine, amber needs a look, red needs a decision. Money is at completion; people are organisation-wide.")
    kpi_row(pg, Y1K, [
        ("Story | Active Projects", "Active projects"),
        ("Story | On Track %", "Active projects on track"),
        ("Story | EAC Variance %", "EAC vs budget", {"colour_measure": "Story | Variance Colour"}),
        ("Story | Burn %", "Budget spent (lifetime)", {"colour_measure": "Story | Burn Colour"}),
        ("Story | Utilisation %", "Utilisation (org-wide)", {"colour_measure": "Story | Util Colour"}),
        ("Story | Over-allocated People", "Over 100% (org-wide)", {"value_colour": RED}),
        ("Story | Critical High Risks", "Critical / high risks", {"value_colour": RED}),
        ("Story | Benefits Realised KPI", "Benefits realised vs due", {"size": 18}),
    ])
    section(pg, Y2, 2, "Where is the portfolio heading?", "Health of active projects, money at completion and the people curve.")
    health = DP("OverallHealth_Value")
    active = M("Story | Active Projects")
    pg.add(16, Y2V, 560, H2, chart("donutChart",
        {"Category": [P(health, "Overall health")], "Y": [P(active, "Active projects")]},
        "Overall health of active projects",
        {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Bottom"),
         "labels": [{"properties": {"show": b(True), "labelStyle": s("Category, percent of total")}}]}), key="v_health")
    bac, eac = M("Story | Budget At Completion"), M("Story | Finance EAC")
    pg.add(592, Y2V, 590, H2, chart("clusteredBarChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Y": [P(bac, "Budget"), P(eac, "EAC")]},
        "Budget versus EAC by portfolio (at completion)",
        {"dataPoint": [measure_fill(bac, "#C9CED8"), measure_fill(eac, ORANGE)], "legend": legend("Top")},
        sort=[(eac, "Descending")]), key="v_bvf")
    pg.add(1198, Y2V, 586, H2, people_combo("People (org-wide): capacity vs scheduled hours"), key="v_people")
    section(pg, Y3, 3, "What needs a decision this month?",
            "Projects ranked by € overrun at completion (EAC − budget), with the three actions the data points to.")
    var, vp = M("Story | EAC Variance"), M("Story | EAC Variance %")
    cols = [P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"), P(health, "Health"),
            P(bac, "Budget"), P(eac, "EAC"), P(var, "EAC − budget"), P(vp, "Variance %"),
            P(M("Story | Active Risk Count"), "Active risks"), P(M("Story | Overdue Tasks"), "Overdue tasks")]
    obj = table_style()
    obj["values"] += [cf_font(var, "Story | Variance Colour"), cf_font(vp, "Story | Variance Colour"),
                      cf_font(health, "Story | Health Colour")]
    pg.add(16, Y3V, 1160, H3, chart("tableEx", {"Values": cols}, "Attention list — biggest € overrun at completion first",
                                    obj, sort=[(var, "Descending")]), key="v_attn", filters=[REAL_PROJECTS])
    for k, m in enumerate(["Story | Exec Action Money", "Story | Exec Action People", "Story | Exec Action Risk"]):
        pg.add(1192, Y3V + k * 136, 592, 124, headline(m, bg="#FFFFFF", border=ORANGE, size=12), key=f"act{k}")
    section(pg, Y4, 4, "Where should I look next?", "Each chapter answers one question in depth.")
    chapters = ORDER[2:]
    per_row = (len(chapters) + 1) // 2
    bw = (1768 - 10 * (per_row - 1)) / per_row
    for k, ck in enumerate(chapters):
        row, col = divmod(k, per_row)
        pg.add(round(16 + col * (bw + 10), 2), Y4V + row * 64, round(bw, 2), 56,
               nav_button(dict(PAGES)[ck] + "  ›", PID[ck], "Open this chapter", fill=NAVY, hover=NAVY_BTN,
                          press=ORANGE, font="#FFFFFF", size=10), key=f"chap{k}")
    vpf = M("Story | EAC Variance %")
    pg.add(16, Y4V + 136, 1768, 264, chart("pivotTable",
        {"Rows": [P(DP("Portfolio Name"), "Portfolio", True), P(DP("Program Name"), "Program", True)],
         "Values": [P(active, "Active projects"), P(M("Story | On Track %"), "On track"),
                    P(bac, "Budget"), P(eac, "EAC"), P(vpf, "Variance %"),
                    P(M("Story | Project Scheduled Hours"), "Scheduled h (demand)"),
                    P(M("Story | Active Risk Count"), "Active risks"),
                    P(M("Story | Benefits At Completion"), "Planned benefits")]},
        "Portfolio scorecard — expand a portfolio to see its programmes",
        dict(table_style(), values=table_style()["values"] + [cf_font(vpf, "Story | Variance Colour")])),
        key="v_scorecard")
    next_chapter(pg, "exec", YNEXT)
    return pg


# ================================================================= 2 PORTFOLIO
def build_portfolio():
    pg = analytic_page("portfolio", "PORTFOLIO", "ARE WE FUNDING THE RIGHT WORK?",
                       "Where the plan-field budget goes, how well it fits the strategy, and whether priority and value line up.",
                       PROJ_SLICERS, "Story | Portfolio Headline")
    section(pg, Y1, 1, "What is in the portfolio?",
            "Size, pipeline and strategic fit. Budget here = the lifetime Budget field on each plan.")
    kpi_row(pg, Y1K, [
        ("Story | Active Projects", "Active projects"),
        ("Story | Proposed Projects", "Proposals in pipeline"),
        ("Story | Plan Budget", "Plan-field budget"),
        ("Story | Aligned Budget %", "Budget strongly aligned"),
        ("Modeler | Alignment Score", "Alignment score (0–100)"),
        ("Story | On Track %", "Active projects on track"),
        ("Project | Total CostofDelay", "Cost of delay"),
    ])
    section(pg, Y2, 2, "Where does the money go?",
            "Plan-field budget by portfolio coloured by strategic alignment, by goal and by project type.")
    align = DP("StrategicAlignment_Value")
    budget = M("Story | Plan Budget")
    pg.add(16, Y2V, 878, H2, chart("barChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Series": [P(align, "Alignment")],
         "Y": [P(budget, "Plan-field budget")]},
        "Plan-field budget by portfolio and strategic alignment",
        {"dataPoint": series_colours(align, {"Extreme": NAVY, "Strong": TEAL, "Moderate": "#7FB7B7", "Low": AMBER,
                                             "Not Rated": "#C9CED8"}),
         "legend": legend("Top")}, sort=[(budget, "Descending")]), key="v_bud_align")
    pg.add(906, Y2V, 434, H2, chart("donutChart",
        {"Category": [P(DP("Goals_Value"), "Goal")], "Y": [P(budget, "Plan-field budget")]}, "Plan-field budget by goal",
        {"legend": legend("Bottom"), "labels": [{"properties": {"show": b(True), "labelStyle": s("Percent of total")}}]}),
        key="v_goal")
    pg.add(1350, Y2V, 434, H2, chart("donutChart",
        {"Category": [P(DP("ProjectType_Value"), "Project type")], "Y": [P(budget, "Plan-field budget")]},
        "Plan-field budget by project type",
        {"legend": legend("Bottom"), "labels": [{"properties": {"show": b(True), "labelStyle": s("Percent of total")}}]}),
        key="v_type")
    section(pg, Y3, 3, "Are the right projects first?",
            "Right = high prioritisation score, up = big budget. Red bubbles on the right are the conversations to have.")
    health = DP("OverallHealth_Value")
    prio = M("Story | Priority Score")
    pg.add(16, Y3V, 1060, H3, chart("scatterChart",
        {"Category": [P(DP("Name"), "Project")], "Series": [P(health, "Health")],
         "X": [P(prio, "Priority score")], "Y": [P(budget, "Plan-field budget")],
         "Size": [P(M("Story | Plan Forecast"), "Plan-field forecast")]},
        "Priority score vs plan-field budget — size = plan forecast, colour = health",
        {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Top"),
         "categoryLabels": [{"properties": {"show": b(True), "fontSize": n(8)}}]}), key="v_scatter")
    pg.add(1092, Y3V, 692, H3, chart("hundredPercentStackedBarChart",
        {"Category": [P(DP("Program Name"), "Program")], "Series": [P(health, "Health")],
         "Y": [P(M("Story | Active Projects"), "Active projects")]},
        "Health mix of active projects per programme",
        {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Top")}), key="v_health_prog")
    section(pg, Y4, 4, "The portfolio register",
            "Portfolio › programme › project, lifetime plan fields. Red variance = plan forecast more than 5% over plan budget.")
    vp = M("Story | Plan Variance %")
    obj = table_style()
    obj["values"] += [cf_font(vp, "Story | Plan Variance Colour")]
    pg.add(16, Y4V, 1768, H4, chart("pivotTable",
        {"Rows": [P(DP("Portfolio Name"), "Portfolio", True), P(DP("Program Name"), "Program", True),
                  P(DP("Name"), "Project", True)],
         "Values": [P(M("Project | Plans Count"), "Projects"), P(budget, "Plan-field budget"),
                    P(M("Story | Plan Forecast"), "Plan-field forecast"), P(vp, "Plan variance %"),
                    P(M("Modeler | Alignment Score"), "Alignment"), P(prio, "Priority score"),
                    P(M("Story | Active Risk Count"), "Active risks"),
                    P(M("Benefits | Planned Benefits"), "Plan-field benefits")]},
        "Portfolio register (plan fields)", obj), key="v_register")
    next_chapter(pg, "portfolio", YNEXT)
    return pg


# ================================================================= 3 FINANCIALS
def build_finance():
    pg = analytic_page("finance", "FINANCIALS", "ARE WE SPENDING AS PLANNED?",
                       "OnePlan financial plans. EAC and variance are at completion (all years); Year filters the to-date and trend views.",
                       STD_SLICERS, "Story | Finance Headline")
    section(pg, Y1, 1, "Where do we stand?",
            "EAC against budget at completion is the number the board asks for; budget to date checks the pace.")
    kpi_row(pg, Y1K, [
        ("Story | Budget At Completion", "Budget at completion"),
        ("Story | Finance EAC", "EAC"),
        ("Story | EAC Variance", "EAC − budget", {"colour_measure": "Story | Variance Colour"}),
        ("Story | EAC Variance %", "EAC variance %", {"colour_measure": "Story | Variance Colour"}),
        ("Story | Budget To Date", "Budget to date"),
        ("Story | Actual Cost", "Actual cost"),
        ("Story | To-Date Variance %", "Actual vs budget to date", {"colour_measure": "Story | To-Date Colour"}),
        ("Story | Projects Over Budget", "Projects over budget", {"value_colour": RED}),
    ])
    section(pg, Y2, 2, "How is spend tracking over time?",
            "Lifetime cumulative curves: EAC above budget means the gap is opening; actuals stop at today.")
    cb, ca, ce = M("Story | Cum Budget"), M("Story | Cum Actual"), M("Story | Cum EAC")
    pg.add(16, Y2V, 1160, H2, chart("lineChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(cb, "Budget (cum.)"), P(ca, "Actual (cum.)"), P(ce, "EAC (cum.)")]},
        "S-curve — lifetime cumulative budget, actual and EAC",
        {"dataPoint": [measure_fill(cb, "#9AA3AF"), measure_fill(ca, NAVY), measure_fill(ce, ORANGE)],
         "legend": legend("Top"), "lineStyles": [{"properties": {"strokeWidth": n(3)}}]},
        sort=[(MONTH, "Ascending")]), key="v_scurve")
    b_, a_, e_ = M("Story | Budget In Period"), M("Story | Actual Cost"), M("Story | EAC In Period")
    qtr = C("DimDate", "QuarterStart")
    pg.add(1192, Y2V, 592, H2, chart("clusteredColumnChart",
        {"Category": [P(qtr, "Quarter")], "Y": [P(b_, "Budget"), P(a_, "Actual"), P(e_, "EAC (phased)")]},
        "Per quarter — budget, actual, phased EAC",
        {"dataPoint": [measure_fill(b_, "#C9CED8"), measure_fill(a_, NAVY), measure_fill(e_, ORANGE)],
         "legend": legend("Top")}, sort=[(qtr, "Ascending")]), key="v_quarter")
    section(pg, Y3, 3, "Where is the variance coming from?",
            "Bars up = programmes whose EAC exceeds budget at completion; the right chart names the projects behind it.")
    var = M("Story | EAC Variance")
    pg.add(16, Y3V, 878, H3, chart("waterfallChart",
        {"Category": [P(DP("Program Name"), "Program")], "Y": [P(var, "EAC − budget")]},
        "Variance bridge by programme (EAC − budget)",
        {"sentimentColors": [{"properties": {"increaseFill": col_solid(RED), "decreaseFill": col_solid(TEAL),
                                             "totalFill": col_solid(NAVY)}}],
         "labels": labels_on(True, 0)}, sort=[(var, "Descending")]), key="v_waterfall")
    pg.add(906, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(var, "EAC − budget")]},
        "Projects ranked by overrun at completion",
        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Variance Colour")}, "selector": FILL_ALL}],
         "labels": labels_on(True, 0)}, sort=[(var, "Descending")]), key="v_proj_var", filters=[REAL_PROJECTS])
    section(pg, Y4, 4, "Project financial register",
            "Sorted by overrun at completion. Red = EAC more than 5% over budget, amber = slightly over, teal = within budget.")
    vp, burn, btd = M("Story | EAC Variance %"), M("Story | Burn %"), M("Story | Budget To Date")
    bac, eac = M("Story | Budget At Completion"), M("Story | Finance EAC")
    obj = table_style()
    obj["values"] += [cf_font(vp, "Story | Variance Colour"), cf_font(var, "Story | Variance Colour"),
                      cf_font(burn, "Story | Burn Colour")]
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"), P(DP("Manager_Value"), "Manager"),
                    P(bac, "Budget"), P(btd, "Budget to date"), P(a_, "Actual"), P(eac, "EAC"),
                    P(var, "EAC − budget"), P(vp, "Variance %"), P(burn, "Spent (lifetime)"),
                    P(DP("FinancialHealth_Value"), "Financial health")]},
        "Project financial register", obj, sort=[(var, "Descending")]), key="v_fin_table", filters=[REAL_PROJECTS])
    next_chapter(pg, "finance", YNEXT)
    return pg


# ================================================================= 3b PARETO & P&L
def pareto(ttl, cat_field, bar, line, bar_label, colour):
    return chart("lineClusteredColumnComboChart",
        {"Category": [P(cat_field, "Project")], "Y": [P(bar, bar_label)], "Y2": [P(line, "Cumulative %")]},
        ttl,
        {"dataPoint": [measure_fill(bar, colour), measure_fill(line, NAVY)], "legend": legend("Top"),
         "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}],
         "valueAxis": [{"properties": {"secShow": b(True), "secStart": n(0), "secEnd": n(1)}}],
         "categoryAxis": [{"properties": {"fontSize": n(8)}}]},
        sort=[(bar, "Descending")])


def build_finance2():
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (DP("ProjectType_Value"), "Project type"), (DP("Goals_Value"), "Goal")]
    pg = analytic_page("finance2", "PARETO & P&L", "WHAT DOES THE MONEY RETURN?",
                       "Pareto (80/20) of EAC and overruns, then an at-completion P&L per portfolio: revenue + benefits − EAC.",
                       slicers, "Story | Pareto PnL Headline")
    section(pg, Y1, 1, "Concentration and return",
            "All figures at completion from the financial plans. Few projects carrying most of the money deserve most of the governance.")
    kpi_row(pg, Y1K, [
        ("Story | Finance EAC", "EAC"),
        ("Story | Projects For 80% Spend", "Projects = 80% of EAC", {"value_colour": ORANGE}),
        ("Story | Concentration %", "Share of projects", {"value_colour": ORANGE}),
        ("Story | Overrun", "Total overrun", {"value_colour": RED}),
        ("Story | Top3 Overrun Share", "Overrun in top 3", {"value_colour": RED}),
        ("Story | Total Value", "Value (revenue + benefits)", {"value_colour": TEAL}),
        ("Story | Net Value", "Net value", {"colour_measure": "Story | Net Colour"}),
        ("Story | Net Margin %", "Net margin", {"colour_measure": "Story | Net Colour"}),
    ])
    section(pg, Y2, 2, "Pareto — which projects carry the EAC and the overrun?",
            "Bars ranked largest first; the line is the cumulative share of the whole selection. Where it crosses 80% is your A-list.")
    eac, cum = M("Story | Finance EAC"), M("Story | Spend Cum %")
    pg.add(16, Y2V, 1160, H2, pareto("Pareto of EAC by project", DP("Name"), eac, cum, "EAC", ORANGE),
           key="v_pareto_spend", filters=[REAL_PROJECTS])
    ov, ocum = M("Story | Overrun"), M("Story | Overrun Cum %")
    pg.add(1192, Y2V, 592, H2, pareto("Pareto of overruns (EAC above budget)", DP("Name"), ov, ocum, "Overrun", RED),
           key="v_pareto_overrun", filters=[REAL_PROJECTS])
    section(pg, Y3, 3, "Which portfolios create net value?",
            "Revenue and benefits against EAC per portfolio, and how each adds to — or takes from — total net value.")
    tv, nv = M("Story | Total Value"), M("Story | Net Value")
    rev, ben = M("Story | Revenue At Completion"), M("Story | Benefits At Completion")
    pg.add(16, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")],
         "Y": [P(rev, "Revenue"), P(ben, "Benefits"), P(eac, "EAC")]},
        "Revenue and benefits versus EAC by portfolio",
        {"dataPoint": [measure_fill(rev, NAVY), measure_fill(ben, TEAL), measure_fill(eac, "#C9CED8")],
         "legend": legend("Top"), "labels": labels_on(False)}, sort=[(eac, "Descending")]), key="v_pnl_bars")
    pg.add(906, Y3V, 878, H3, chart("waterfallChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Y": [P(nv, "Net value")]},
        "Net-value bridge — each portfolio's share of total net value",
        {"sentimentColors": [{"properties": {"increaseFill": col_solid(TEAL), "decreaseFill": col_solid(RED),
                                             "totalFill": col_solid(NAVY)}}],
         "labels": labels_on(True, 0)}, sort=[(nv, "Descending")]), key="v_pnl_bridge")
    section(pg, Y4, 4, "Portfolio P&L statement",
            "Portfolio › programme › project, at completion. Pareto class and share of EAC are across the whole selection.")
    cls, margin, roi = M("Story | Pareto Class"), M("Story | Net Margin %"), M("Story | Net ROI")
    obj = table_style()
    obj["values"] += [cf_font(nv, "Story | Net Colour"), cf_font(margin, "Story | Net Colour"),
                      cf_font(cls, "Story | Pareto Class Colour")]
    pg.add(16, Y4V, 1768, H4, chart("pivotTable",
        {"Rows": [P(DP("Portfolio Name"), "Portfolio", True), P(DP("Program Name"), "Program", True),
                  P(DP("Name"), "Project", True)],
         "Values": [P(rev, "Revenue"), P(ben, "Benefits"), P(tv, "Total value"),
                    P(M("Story | Budget At Completion"), "Budget"),
                    P(eac, "EAC"), P(nv, "Net value"), P(margin, "Net margin"), P(roi, "ROI"),
                    P(M("Story | Spend Share"), "Share of EAC"), P(cls, "Pareto class")]},
        "Portfolio P&L statement (at completion)", obj, sort=[(nv, "Descending")]), key="v_pnl_matrix")
    next_chapter(pg, "finance2", YNEXT)
    return pg


# ================================================================= 4 RESOURCES
def build_resources():
    # No project slicer: FactCapacity has no project link, so a project filter would distort utilisation.
    slicers = [(DR("Department_Value"), "Department"), (DR("Role_Value"), "Role"), (C("DimDate", "Year"), "Year")]
    pg = analytic_page("resources", "RESOURCES", "DO WE HAVE THE PEOPLE?",
                       "Capacity from OnePlan resource calendars against scheduled and committed hours on project plans, "
                       "organisation-wide.",
                       slicers, "Story | Resource Headline")
    section(pg, Y1, 1, "Supply and demand in one line",
            "Utilisation = scheduled hours on project plans ÷ capacity. Above 100% is overload; below 50% is bench.")
    kpi_row(pg, Y1K, [
        ("Resource KPI | Total Resources", "Active resources"),
        ("Resource | Capacity FTE", "Capacity (FTE)"),
        ("Story | Scheduled FTE", "Scheduled (FTE)"),
        ("Story | Utilisation %", "Utilisation", {"colour_measure": "Story | Util Colour"}),
        ("Story | Over-allocated People", "Over 100% in a month", {"value_colour": RED}),
        ("Story | Free Capacity (h)", "Free capacity (h)", {"value_colour": TEAL}),
        ("Story | Committed Gap (h)", "Committed vs scheduled gap (h)", {"value_colour": AMBER}),
        ("Story | Committed Without Schedule (h)", "Committed without a schedule (h)", {"value_colour": AMBER}),
    ])
    section(pg, Y2, 2, "Will supply cover demand over the coming months?",
            "Columns = capacity; lines = scheduled and committed hours on project plans, one axis. Committed is a "
            "separate figure and can exceed scheduled.")
    pg.add(16, Y2V, 1160, H2, people_combo("Capacity vs scheduled and committed hours per month"), key="v_supply")
    util = M("Story | Utilisation %")
    pg.add(1192, Y2V, 592, H2, chart("clusteredBarChart",
        {"Category": [P(DR("Role_Value"), "Role")], "Y": [P(util, "Utilisation")]},
        "Utilisation by role",
        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Util Colour")}, "selector": FILL_ALL}],
         "labels": labels_on(True)}, sort=[(util, "Descending")]), key="v_role")
    section(pg, Y3, 3, "Who is over- or under-loaded, month by month?",
            "Scheduled ÷ capacity per person and month; rolling 12 months (3 back to 8 ahead) — change it in the filter pane.")
    legend_note(pg, 1084, Y3 + 4, 700, [("Over 100%", "#8E1B12"), ("80–100%", TEAL), ("50–80%", "#9A6B00"),
                                        ("Under 50%", MUTED)], "heat_legend")
    obj = table_style(9)
    obj["values"] += [cf_back(util, "Story | Util Cell Colour")]
    pg.add(16, Y3V, 1768, H3, chart("pivotTable",
        {"Rows": [P(DR("Role_Value"), "Role", True), P(DR("Name"), "Resource", True)],
         "Columns": [P(MONTH, "Month", True)], "Values": [P(util, "Util.")]},
        "Utilisation heat map — role › resource × month", obj), key="v_heat",
        filters=[f_between("DimDate", "RelativeMonth", -3, 8)])
    section(pg, Y4, 4, "Where does demand come from, and who can take more?",
            "Scheduled and committed hours per project, and the bench list of active people.")
    sch_p, com_p = M("Story | Project Scheduled Hours"), M("Story | Project Committed Hours")
    pg.add(16, Y4V, 878, H4, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(sch_p, "Scheduled h"), P(com_p, "Committed h")]},
        "Scheduled and committed hours by project",
        {"dataPoint": [measure_fill(sch_p, NAVY), measure_fill(com_p, TEAL)], "legend": legend("Top")},
        sort=[(sch_p, "Descending")]), key="v_demand")
    obj = table_style()
    obj["values"] += [cf_font(util, "Story | Util Colour")]
    pg.add(906, Y4V, 878, H4, chart("tableEx",
        {"Values": [P(DR("Name"), "Resource"), P(DR("Role_Value"), "Role"), P(DR("Department_Value"), "Department"),
                    P(M("Capacity | Resource Capacity"), "Capacity h"), P(M("Story | Scheduled Hours"), "Scheduled h"),
                    P(util, "Utilisation"), P(M("Story | Months Over 100%"), "Months > 100%"),
                    P(M("Story | Free Capacity (h)"), "Free h")]},
        "Bench and overload list — lowest utilisation first", obj, sort=[(util, "Ascending")]), key="v_bench",
        filters=[f_cmp("DimResource", "Inactive", 0, False)])
    next_chapter(pg, "resources", YNEXT)
    return pg


# ================================================================= 5 SCHEDULE
def build_schedule():
    pg = analytic_page("schedule", "SCHEDULE", "WILL WE DELIVER ON TIME?",
                       "Schedule health reported by project managers, checked against baselines, milestones and late work in the work plans.",
                       PROJ_SLICERS, "Story | Schedule Headline")
    section(pg, Y1, 1, "Delivery confidence", "Reported health of active projects first, then what the project work plans say.")
    kpi_row(pg, Y1K, [
        ("Story | On Schedule %", "On schedule (active)"),
        ("Story | Schedule At Risk", "Schedule at risk", {"value_colour": AMBER}),
        ("Story | Schedule Off Track", "Schedule off track", {"value_colour": RED}),
        ("Story | Project Slip (days)", "Avg finish slip (days)", {"value_colour": AMBER}),
        ("Story | Overdue Tasks", "Overdue tasks", {"value_colour": RED}),
        ("Story | Slipped Tasks", "Tasks past baseline", {"value_colour": AMBER}),
        ("Story | Milestones Next 30d", "Milestones next 30 days"),
    ])
    section(pg, Y2, 2, "Which programmes are slipping, and where are projects in the lifecycle?",
            "Schedule health of active projects per programme, and the lifecycle step each project has reached.")
    sh = DP("ScheduleHealth_Value")
    pg.add(16, Y2V, 878, H2, chart("barChart",
        {"Category": [P(DP("Program Name"), "Program")], "Series": [P(sh, "Schedule health")],
         "Y": [P(M("Story | Active Projects"), "Active projects")]},
        "Schedule health of active projects by programme",
        {"dataPoint": series_colours(sh, HEALTH_COLOURS), "legend": legend("Top")}), key="v_sched_prog")
    step_idx = M("Story | Step Index")
    pg.add(906, Y2V, 878, H2, chart("clusteredColumnChart",
        {"Category": [P(DP("ProcessStep"), "Lifecycle step")], "Y": [P(M("Project | Plans Count"), "Projects")],
         "Tooltips": [P(step_idx, "Step #")]},
        "Projects per lifecycle step (in lifecycle order)",
        {"dataPoint": [{"properties": {"fill": col_solid(NAVY)}}], "labels": labels_on(True)},
        sort=[(step_idx, "Ascending")]), key="v_funnel")
    section(pg, Y3, 3, "Which finish dates moved, and what is coming up?",
            "Slip = current finish minus baseline finish. Milestones overdue are red, due within 14 days amber.")
    slip = M("Story | Project Slip (days)")
    pg.add(16, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(slip, "Slip (days)")]},
        "Finish-date slip versus baseline, by project (days)",
        {"dataPoint": [{"properties": {"fill": col_solid(ORANGE)}}], "labels": labels_on(True)},
        sort=[(slip, "Descending")]), key="v_slip")
    obj = table_style()
    obj["values"] += [cf_font(DT("EndDate"), "Story | Due Colour")]
    pg.add(906, Y3V, 878, H3, chart("tableEx",
        {"Values": [P(DT("EndDate"), "Due"), P(DP("Name"), "Project"), P(DT("Name"), "Milestone"),
                    P(DT("PercentDone"), "% done"), P(DT("Status"), "Status")]},
        "Open milestones — soonest first", obj, sort=[(DT("EndDate"), "Ascending")]), key="v_miles",
        filters=[f_in("DimTask", "Milestone", [True]), f_cmp("DimTask", "PercentDone", 3, 100), PROJECT_TASKS])
    section(pg, Y4, 4, "Late-work register",
            "The open project tasks counted under 'Tasks past baseline' — longest slip first.")
    tslip = M("Story | Late Task Slip (days)")
    obj = table_style()
    obj["values"] += [cf_font(tslip, "Story | Slip Colour"), cf_font(DT("EndDate"), "Story | Late Due Colour")]
    # Rows show only where Late Task Slip is non-blank, i.e. exactly the Story | Slipped Tasks population.
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DT("Name"), "Task"), P(DT("AssignedResources"), "Assigned to"),
                    P(DT("BaselineEndDate"), "Baseline finish"), P(DT("EndDate"), "Finish"), P(tslip, "Slip (days)"),
                    P(DT("PercentDone"), "% done"), P(DT("TaskStatus"), "Task status")]},
        "Late-work register", obj, sort=[(tslip, "Descending")]), key="v_late",
        filters=[f_in("DimTask", "WorkType", ["Tasks"]), f_in("DimTask", "Leaf", [True]),
                 f_cmp("DimTask", "PercentDone", 3, 100), f_not_blank("DimTask", "BaselineEndDate"), PROJECT_TASKS])
    next_chapter(pg, "schedule", YNEXT)
    return pg


# ================================================================= 6 RISK
def build_risk():
    pg = analytic_page("risk", "RISK", "WHAT COULD GO WRONG?",
                       "Risks and issues logged on the project work plans: how likely, how bad, where the exposure sits, what to escalate.",
                       PROJ_SLICERS, "Story | Risk Headline")
    section(pg, Y1, 1, "Risk position",
            "Active risks on project plans. Exposure is OnePlan's score (probability % × impact weight), not money.")
    kpi_row(pg, Y1K, [
        ("Story | Active Risk Count", "Active risks"),
        ("Story | Critical High Risks", "Critical / high (heat ≥ 9)", {"value_colour": RED}),
        ("Story | Risk Exposure", "Exposure score", {"value_colour": ORANGE}),
        ("Story | Avg Risk Probability", "Avg probability"),
        ("Story | Unmitigated Risk %", "No mitigation recorded", {"value_colour": AMBER}),
        ("Story | Open Issues", "Open issues", {"value_colour": RED}),
        ("Project | Active Changes", "Open changes"),
    ])
    risk_filter = [f_in("DimTask", "WorkType", ["Risks"]), f_in("DimTask", "State", ["Active"]), PROJECT_TASKS]
    section(pg, Y2, 2, "How likely, how bad?",
            "Heat map of active risks; the orange and red cells (score ≥ 9) are the critical / high risks.")
    rc = M("Story | Active Risk Count")
    obj = table_style(11)
    obj["values"] += [cf_back(rc, "Story | Heat Colour")]
    pg.add(16, Y2V, 700, H2, chart("pivotTable",
        {"Rows": [P(DT("Impact"), "Impact", True)], "Columns": [P(DT("Probability Category"), "Probability", True)],
         "Values": [P(rc, "Risks")]},
        "Risk heat map — impact × probability", obj, sort=[(DT("Impact"), "Ascending")]), key="v_heatmap",
        filters=risk_filter)
    pg.add(728, Y2V, 520, H2, chart("clusteredBarChart",
        {"Category": [P(DT("RiskStage"), "Stage")], "Y": [P(rc, "Risks")]},
        "Where risks are in the response cycle",
        {"dataPoint": [{"properties": {"fill": col_solid(NAVY)}}], "labels": labels_on(True)}), key="v_stage",
        filters=risk_filter)
    exp = M("Story | Risk Exposure")
    pg.add(1260, Y2V, 524, H2, chart("clusteredBarChart",
        {"Category": [P(DP("Program Name"), "Program")], "Y": [P(exp, "Exposure score")]},
        "Exposure score by programme",
        {"dataPoint": [{"properties": {"fill": col_solid(ORANGE)}}], "labels": labels_on(True, 0)},
        sort=[(exp, "Descending")]), key="v_exp_prog")
    section(pg, Y3, 3, "Where is exposure concentrated?",
            "Big tiles = where a single bad outcome scores highest. Issues are risks that already happened.")
    pg.add(16, Y3V, 878, H3, chart("treemap",
        {"Group": [P(DP("Program Name"), "Program")], "Details": [P(DP("Name"), "Project")],
         "Values": [P(exp, "Exposure score")]},
        "Exposure score by programme › project", {"legend": legend("Top", False)}), key="v_treemap")
    iss = M("Story | Open Issues")
    pg.add(906, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(iss, "Open issues"), P(rc, "Active risks")]},
        "Open issues and active risks per project",
        {"dataPoint": [measure_fill(iss, RED), measure_fill(rc, "#C9CED8")],
         "legend": legend("Top")}, sort=[(iss, "Descending")]), key="v_issues")
    section(pg, Y4, 4, "Top-risk register",
            "Highest exposure score first — check every critical or high risk has an owner and a mitigation.")
    obj = table_style()
    obj["values"] += [cf_font(DT("Impact"), "Story | Impact Colour")]
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DT("Name"), "Risk"), P(DT("Impact"), "Impact"),
                    P(DT("Probability Category"), "Probability"), P(exp, "Exposure score"), P(DT("RiskStage"), "Stage"),
                    P(DT("AssignedResources"), "Owner"), P(DT("Mitigation"), "Mitigation"), P(DT("EndDate"), "Due")]},
        "Top-risk register", obj, sort=[(exp, "Descending")]), key="v_risk_table", filters=risk_filter)
    next_chapter(pg, "risk", YNEXT)
    return pg


# ================================================================= 7 BENEFITS
def build_benefits():
    pg = analytic_page("benefits", "VALUE", "WILL IT PAY OFF?",
                       "Planned benefits in the OnePlan financial plans (revenue / cost savings) against EAC — and the actual benefits recorded.",
                       PROJ_SLICERS, "Story | Benefits Headline")
    section(pg, Y1, 1, "The value case",
            "Realised = actual benefits recorded in OnePlan, never estimated from % complete. Ratio below 1.0 = costs more than it returns.")
    kpi_row(pg, Y1K, [
        ("Story | Benefits At Completion", "Planned benefits"),
        ("Story | Benefits Due To Date", "Benefits due to date"),
        ("Story | Benefits Actual Label", "Actually realised", {"size": 20}),
        ("Story | Benefits Realised KPI", "Realised vs due", {"size": 20}),
        ("Story | Finance EAC", "EAC"),
        ("Story | Benefit Cost Ratio", "Benefit ÷ EAC", {"colour_measure": "Story | Ratio Colour"}),
        ("Project | Total CostofDelay", "Cost of delay", {"value_colour": RED}),
    ])
    section(pg, Y2, 2, "When does the value land, and where?",
            "Planned benefits per quarter by type with actuals as the line, and benefits against EAC per portfolio.")
    pb, act, eac = M("Story | Benefits Planned"), M("Story | Benefits Actual"), M("Story | Finance EAC")
    cat = C("FactCost", "CostCategory")
    qtr = C("DimDate", "QuarterStart")
    pg.add(16, Y2V, 1160, H2, chart("lineStackedColumnComboChart",
        {"Category": [P(qtr, "Quarter")], "Series": [P(cat, "Benefit type")], "Y": [P(pb, "Planned benefits")],
         "Y2": [P(act, "Actual benefits")]},
        "Benefits per quarter — planned by type (columns) vs actual (line)",
        {"dataPoint": series_colours(cat, {"Revenue": TEAL, "Cost Savings": NAVY}) + [measure_fill(act, ORANGE)],
         "legend": legend("Top"), "valueAxis": one_axis(),
         "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}]},
        sort=[(qtr, "Ascending")]), key="v_ben_phasing")
    pba = M("Story | Benefits At Completion")
    pg.add(1192, Y2V, 592, H2, chart("clusteredBarChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Y": [P(pba, "Planned benefits"), P(eac, "EAC")]},
        "Planned benefits versus EAC by portfolio",
        {"dataPoint": [measure_fill(pba, TEAL), measure_fill(eac, "#C9CED8")], "legend": legend("Top")},
        sort=[(pba, "Descending")]), key="v_ben_port")
    section(pg, Y3, 3, "Value for money per project",
            "Higher up and further left = more benefit per euro of EAC; the ranking on the right shows benefit ÷ EAC.")
    align = DP("StrategicAlignment_Value")
    pg.add(16, Y3V, 1160, H3, chart("scatterChart",
        {"Category": [P(DP("Name"), "Project")], "Series": [P(align, "Alignment")],
         "X": [P(eac, "EAC")], "Y": [P(pba, "Planned benefits")],
         "Size": [P(M("Story | Benefits Due To Date"), "Due to date")]},
        "Benefits versus EAC — size = benefits due to date",
        {"dataPoint": series_colours(align, {"Extreme": NAVY, "Strong": TEAL, "Moderate": "#7FB7B7", "Low": AMBER,
                                             "Not Rated": "#C9CED8"}),
         "legend": legend("Top"), "categoryLabels": [{"properties": {"show": b(True), "fontSize": n(8)}}]}),
        key="v_ben_scatter")
    ratio = M("Story | Benefit Cost Ratio")
    pg.add(1192, Y3V, 592, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(ratio, "Benefit ÷ EAC")]},
        "Best value for money (benefit ÷ EAC)",
        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Ratio Colour")}, "selector": FILL_ALL}],
         "labels": labels_on(True)}, sort=[(ratio, "Descending")]), key="v_ratio")
    section(pg, Y4, 4, "Benefits register",
            "Projects with an EAC but no planned benefit are the first gap; 'Actual' stays empty until OnePlan records it.")
    obj = table_style()
    obj["values"] += [cf_font(ratio, "Story | Ratio Colour")]
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"), P(DP("Goals_Value"), "Goal"),
                    P(align, "Alignment"), P(eac, "EAC"), P(pba, "Planned benefits"),
                    P(M("Story | Benefits Due To Date"), "Due to date"), P(act, "Actual"), P(ratio, "Benefit ÷ EAC")]},
        "Benefits register", obj, sort=[(pba, "Descending")]), key="v_ben_table")
    next_chapter(pg, "benefits", YNEXT)
    return pg


# ================================================================= 8 GOVERNANCE
def build_governance():
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (C("DimInsightRule", "RuleArea"), "Rule area"), (C("DimInsightRule", "Severity"), "Severity")]
    pg = analytic_page("governance", "GOVERNANCE", "CAN WE TRUST THE DATA?",
                       "OnePlan Plan Insights checks every project plan against governance rules. Unclean data weakens every chapter.",
                       slicers, "PMO | Governance Headline")
    # D-04: project plans only. Power Query sets a missing ProjectKey to -1 (not NULL), so "not blank" would filter
    # nothing; real project keys start at 1 (Int64 column -> Int64 literal "0L").
    pg.add_filters([PROJECT_INSIGHTS])
    section(pg, Y1, 1, "Data health score", "Severity-weighted share of insight checks that pass, on project plans.")
    kpi_row(pg, Y1K, [
        ("PMO | Governance Score", "Governance score", {"colour_measure": "PMO | Governance RAG Colour"}),
        ("PMO | Compliance %", "Compliance"),
        ("PMO | Plans Assessed", "Plans assessed"),
        ("PMO | Plans Failing", "Plans failing", {"value_colour": RED}),
        ("PMO | Problems", "Problems", {"value_colour": RED}),
        ("PMO | Warnings", "Warnings", {"value_colour": AMBER}),
        ("PMO | Insight Coverage %", "Insight coverage"),
    ])
    section(pg, Y2, 2, "Which rules fail most?", "Fix the rule that fails on most plans first — it moves the score fastest.")
    pf = M("PMO | Plans Failing")
    pg.add(16, Y2V, 1060, H2, chart("clusteredBarChart",
        {"Category": [P(C("DimInsightRule", "RuleName"), "Rule")], "Y": [P(pf, "Plans failing")]},
        "Plans failing per insight rule",
        {"dataPoint": [{"properties": {"fill": col_solid(ORANGE)}}], "labels": labels_on(True)},
        sort=[(pf, "Descending")]), key="v_rules")
    pg.add(1092, Y2V, 692, H2, chart("pivotTable",
        {"Rows": [P(C("DimInsightRule", "RuleArea"), "Area", True)],
         "Columns": [P(C("DimInsightRule", "Severity"), "Severity", True)], "Values": [P(pf, "Plans failing")]},
        "Failing plans by rule area and severity", table_style()), key="v_area")
    section(pg, Y3, 3, "Hygiene gaps", "Plans missing the basics that the other chapters rely on.")
    hyg = [("PMO | Plans Without Financial Plan", "No financial plan"),
           ("PMO | Plans Without Resource Plan", "No resource plan"),
           ("PMO | Plans Without Work Plan", "No work plan"),
           ("PMO | Plans Not Up To Date", "Not up to date"),
           ("PMO | Plans Reported Off Track", "Reported off track"),
           ("PMO | Plans With Unassigned Tasks", "Unassigned tasks"),
           ("PMO | Plans Over Risk Threshold", "Over risk threshold"),
           ("PMO | Plans With Unsubmitted Timesheets", "Unsubmitted timesheets")]
    w = (1768 - 7 * 10) / 8
    for k, (m, label) in enumerate(hyg):
        pg.add(round(16 + k * (w + 10), 2), Y3V, round(w, 2), 110, card(m, label, value_colour=NAVY, size=26),
               key=f"hyg{k}")
    pg.add(16, Y3V + 126, 1768, H3 - 126, chart("tableEx",
        {"Values": [P(C("DimInsightRule", "RuleName"), "Rule"), P(C("DimInsightRule", "RuleArea"), "Area"),
                    P(C("DimInsightRule", "Severity"), "Severity"), P(pf, "Plans failing"),
                    P(C("DimInsightRule", "RecommendedAction"), "Recommended action")]},
        "What to do about each failing rule", table_style(), sort=[(pf, "Descending")]), key="v_actions")
    section(pg, Y4, 4, "Plan-by-plan action list", "Lowest governance score first; send each manager their next action.")
    obj = table_style()
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Manager_Value"), "Manager"), P(M("PMO | Governance Score"), "Score"),
                    P(M("PMO | Problems"), "Problems"), P(M("PMO | Warnings"), "Warnings"),
                    P(M("PMO | Failed Checks"), "Failed checks"), P(M("PMO | Next Action"), "Next action")]},
        "Plan-by-plan action list", obj, sort=[(M("PMO | Governance Score"), "Ascending")]), key="v_plans")
    next_chapter(pg, "governance", YNEXT)
    return pg


def build_all():
    import extensions  # extension pages register in extensions.BUILDERS
    built = {"home": build_home(), "exec": build_exec(), "portfolio": build_portfolio(), "finance": build_finance(),
             "finance2": build_finance2(), "resources": build_resources(), "schedule": build_schedule(),
             "risk": build_risk(), "benefits": build_benefits(), "governance": build_governance()}
    for builder in extensions.BUILDERS:
        for pg in builder():
            built[next(k for k, v in PID.items() if v == pg.id)] = pg
    pages_out = [built[k] for k, _ in PAGES + HIDDEN_PAGES if k in built]
    story = [p for p in pages_out if p.id not in {PID[k] for k, _ in HIDDEN_PAGES}]
    filter_real_projects(story)
    attach_tooltips(story)
    return pages_out


TOOLTIP_TYPES = {"tableEx", "pivotTable", "clusteredBarChart", "barChart", "hundredPercentStackedBarChart",
                 "clusteredColumnChart", "columnChart", "scatterChart", "treemap", "waterfallChart",
                 "lineClusteredColumnComboChart"}
# Visual types that can group by a DimProject column (slicers / cards / text are left alone).
GROUPING_TYPES = TOOLTIP_TYPES | {"donutChart", "pieChart", "lineChart", "lineStackedColumnComboChart",
                                  "stackedBarChart", "stackedColumnChart", "hundredPercentStackedColumnChart"}


def _refs(v):
    return {pr["queryRef"] for role in v.get("query", {}).get("queryState", {}).values()
            for pr in role.get("projections", [])}


def filter_real_projects(story_pages):
    """Every chart / table that groups by a DimProject column (Portfolio, Program, Project, …) gets the
    DimProject[Id]-not-blank visual filter, so the blank DimProject row — where FactCost / FactResourcePlan /
    FactStatusReport rows of non-project plans land — can never show up as a '(Blank)' bar or row."""
    for pg in story_pages:
        for vc in pg.visuals:
            v = vc["visual"]
            if v.get("visualType") not in GROUPING_TYPES:
                continue
            if not any(r.startswith("DimProject.") for r in _refs(v)):
                continue
            flts = vc.setdefault("filterConfig", {"filters": []})["filters"]
            if not any(f["name"] == REAL_PROJECTS["name"] for f in flts):
                flts.append(dict(REAL_PROJECTS))


# Visuals whose rows are tasks / gate steps: the project tooltip would summarise the hovered row, not the project.
NO_PROJECT_TIP_PREFIXES = ("DimTask.", "FactPlanProcessStep.")


def attach_tooltips(story_pages):
    """Hover cards: visuals grouped by project get the project tooltip page, by resource the resource one.
    Visuals that also group by a DimTask or FactPlanProcessStep column get no project tooltip."""
    for pg in story_pages:
        for vc in pg.visuals:
            v = vc["visual"]
            if v.get("visualType") not in TOOLTIP_TYPES:
                continue
            refs = _refs(v)
            target = "tip_project" if "DimProject.Name" in refs else "tip_resource" if "DimResource.Name" in refs else None
            if target == "tip_project" and any(r.startswith(NO_PROJECT_TIP_PREFIXES) for r in refs):
                target = None
            if target and "visualTooltip" not in v.get("visualContainerObjects", {}):
                v.setdefault("visualContainerObjects", {})["visualTooltip"] = [{"properties": {
                    "show": b(True), "type": s("Canvas"), "section": s(PID[target])}}]
