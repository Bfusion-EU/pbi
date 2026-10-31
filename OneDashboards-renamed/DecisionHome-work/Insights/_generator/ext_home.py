"""Home — the command center (replaces pages.build_home).

Measures: report-level, prefix "Story | Home · ", folder Story\\Home. Built on the chapter measures;
history-based numbers (sparklines, change chips) come from FactStatusReport snapshots per report month.
Layout: see build() (Task 4/5). Spec: docs/superpowers/specs/2026-10-31-insights-command-center-design.md
"""
import pages
import pbir
from pbir import (NAVY, ORANGE, TEAL, AMBER, RED, GREY, MUTED, Page, card, headline, chart, textbox, st, shape,
                  image, slicer, nav_button, P, M, C, s, b, n, col_solid, measure_colour, measure_fill, legend)
from story_measures import add, money, T, D, I

PX = "Story | Home · "
FOLDER = "Story\\Home"
C_RED, C_AMBER, C_TEAL = "#FF8A80", "#F2C46B", "#5DCAA5"
PROJECTS = "FILTER ( VALUES ( DimProject[Id] ), NOT ISBLANK ( DimProject[Id] ) )"


def hm(name):
    return PX + name


def _add(name, dtype, expr, fmt=None, desc=None, folder=FOLDER):
    add(hm(name), dtype, expr, fmt, folder, desc)


# ---------------------------------------------------------------- top bar
_add("Greeting", T, """
VAR _h = HOUR ( NOW () )
RETURN IF ( _h < 12, "Good morning", IF ( _h < 18, "Good afternoon", "Good evening" ) )""")

# ---------------------------------------------------------------- act now (per project)
_add("Act Score", I, f"""
VAR _one = HASONEVALUE ( DimProject[Id] ) && NOT ISBLANK ( SELECTEDVALUE ( DimProject[Id] ) )
    && SELECTEDVALUE ( DimProject[State_Value] ) = "Active"
VAR _h = SELECTEDVALUE ( DimProject[OverallHealth_Value] )
RETURN
    IF ( _one,
        SWITCH ( TRUE (),
            LEFT ( _h, 3 ) = "(3)", 100,
            [Story | EAC Variance %] > 0.05, 90,
            [Story | Baseline · Finish Slip (days)] > 10, 80,
            [Story | Project · Overdue Tasks] > 10, 60,
            [Story | Status · Days Since Report] > 30, 50,
            [Story | Project · Failing Rules] > 0, 40 ) )""", "0",
     "Impact rank of the worst reason an active project needs attention (blank = no reason).")
_add("Act Reason", T, f"""
VAR _s = [{hm("Act Score")}]
RETURN
    SWITCH ( _s,
        100, "Reported off track",
        90, "EAC " & FORMAT ( [Story | EAC Variance %], "+0%" ) & " over budget",
        80, FORMAT ( [Story | Baseline · Finish Slip (days)], "+0" ) & " days vs baseline",
        60, FORMAT ( [Story | Project · Overdue Tasks], "0" ) & " overdue tasks",
        50, "No status report for " & FORMAT ( [Story | Status · Days Since Report], "0" ) & " days",
        40, FORMAT ( [Story | Project · Failing Rules], "0" ) & " Plan Insights rule(s) failing" )""")
_add("Act Colour", T, f"""
VAR _s = [{hm("Act Score")}]
RETURN IF ( ISBLANK ( _s ), BLANK (), IF ( _s >= 80, "{C_RED}", "{C_AMBER}" ) )""", folder=FOLDER + "\\Colours")
_add("Act Count", I, f"COUNTROWS ( FILTER ( {PROJECTS}, NOT ISBLANK ( [{hm('Act Score')}] ) ) ) + 0", "0")

_add("Briefing", T, f"""
VAR _n = [{hm("Act Count")}]
VAR _a = [Story | Active Projects]
VAR _ob = [Story | Projects Over Budget] + 0
VAR _sl = [Story | Baseline · Late Projects] + 0
VAR _nm = EOMONTH ( TODAY (), 0 ) + 1
VAR _op = CALCULATE ( [Story | Over-allocated People], DimDate[MonthStart] = _nm, REMOVEFILTERS ( DimDate ) ) + 0
RETURN
    IF ( _n = 0, "No active project needs a decision this week. Keep the data fresh.",
        FORMAT ( _n, "0" ) & " of " & FORMAT ( _a, "0" ) & " active projects need a decision — "
            & FORMAT ( _ob, "0" ) & " over budget, " & FORMAT ( _sl, "0" ) & " slipping, "
            & FORMAT ( _op, "0" ) & " people above 100% in " & FORMAT ( _nm, "mmmm" ) & "." )""")

# ---------------------------------------------------------------- history from status-report snapshots
# Per report month: each project's latest report in that month. Months older than 6 return blank (sparkline window).
LATEST = """( VAR _e = CALCULATE ( MAX ( FactStatusReport[Report_ReportEnd] ) )
            RETURN CALCULATE ( MAX ( FactStatusReport[{col}] ), FactStatusReport[Report_ReportEnd] = _e ) )"""
WINDOW = "MAX ( DimDate[MonthStart] ) >= EDATE ( EOMONTH ( TODAY (), -1 ) + 1, -5 ) && MIN ( DimDate[MonthStart] ) <= TODAY ()"
_add("EAC Var % (reports)", D, f"""
VAR _b = SUMX ( {PROJECTS}, {LATEST.format(col="Budget")} )
VAR _f = SUMX ( {PROJECTS}, {LATEST.format(col="Forecast")} )
RETURN IF ( {WINDOW}, DIVIDE ( _f - _b, _b ) )""", "+0.0%;-0.0%;0.0%",
     "Forecast vs budget as reported in the status reports of the month (latest report per project).")
_add("On Track % (reports)", D, f"""
VAR _t = ADDCOLUMNS ( {PROJECTS}, "@h", {LATEST.format(col="OverallHealth")} )
VAR _n = COUNTROWS ( FILTER ( _t, NOT ISBLANK ( [@h] ) ) )
VAR _ok = COUNTROWS ( FILTER ( _t, LEFT ( [@h], 3 ) = "(1)" ) )
RETURN IF ( {WINDOW} && _n > 0, DIVIDE ( _ok, _n ) )""", "0%",
     "Share of reporting projects whose latest report in the month says On Track.")

CHANGE = """
VAR _m = CALCULATETABLE ( VALUES ( DimDate[MonthStart] ), FactStatusReport, REMOVEFILTERS ( DimDate ) )
VAR _last = MAXX ( _m, DimDate[MonthStart] )
VAR _prev = MAXX ( FILTER ( _m, DimDate[MonthStart] < _last ), DimDate[MonthStart] )
VAR _a = CALCULATE ( [{src}], DimDate[MonthStart] = _last, REMOVEFILTERS ( DimDate ) )
VAR _b = CALCULATE ( [{src}], DimDate[MonthStart] = _prev, REMOVEFILTERS ( DimDate ) )
VAR _d = ROUND ( ( _a - _b ) * 100, 1 )
RETURN
    IF ( NOT ISBLANK ( _a ) && NOT ISBLANK ( _b ),
        IF ( _d > 0, "▲ ", IF ( _d < 0, "▼ ", "= " ) ) & FORMAT ( _d, "+0.0;-0.0;0.0" ) & " pt vs last month" )"""
_add("EAC Change", T, CHANGE.format(src=hm("EAC Var % (reports)")), desc="Change vs previous report month, points.")
_add("On Track Change", T, CHANGE.format(src=hm("On Track % (reports)")), desc="Change vs previous report month, points.")

# ---------------------------------------------------------------- next 30 days (milestone table row filter)
_add("Due In 30d", I, 'VAR _d = MAX ( DimTask[EndDate] ) RETURN IF ( _d >= TODAY () && _d <= TODAY () + 30, 1 )', "0",
     "1 for a task due in the next 30 days; drives the Next 30 days table on Home.")

# ---------------------------------------------------------------- top bar: refresh line (sentence case) + dark status colours
_add("Refreshed", T, """
VAR _t = MAX ( RefreshTime[Last Refreshed (Belgium Time)] )
RETURN IF ( ISBLANK ( _t ), "Powered by OnePlan", "Powered by OnePlan  ·  refreshed " & FORMAT ( _t, "dd mmm yyyy hh:nn" ) & " CET" )""")
_COL = FOLDER + "\\Colours"
_add("Colour EAC", T, f"""
VAR _p = [Story | EAC Variance %]
RETURN IF ( ISBLANK ( _p ), BLANK (), IF ( _p > 0.05, "{C_RED}", IF ( _p > 0, "{C_AMBER}", "{C_TEAL}" ) ) )""",
     desc="Same thresholds as Story | Variance Colour, light-on-dark colours.", folder=_COL)
_add("Colour Util", T, f"""
VAR _u = [Story | Utilisation %]
RETURN IF ( ISBLANK ( _u ), BLANK (), IF ( _u > 1, "{C_RED}", IF ( _u >= 0.8, "{C_TEAL}", IF ( _u >= 0.5, "{C_AMBER}", "#8C98B3" ) ) ) )""",
     desc="Same thresholds as Story | Util Colour, light-on-dark colours.", folder=_COL)
_add("Colour Trust", T, f"""
VAR _g = [PMO | Governance Score]
RETURN IF ( ISBLANK ( _g ), BLANK (), IF ( _g >= 90, "{C_TEAL}", IF ( _g >= 75, "{C_AMBER}", "{C_RED}" ) ) )""",
     desc="Same thresholds as PMO | Governance RAG Colour (90 / 75), light-on-dark colours.", folder=_COL)
# ---------------------------------------------------------------- area tiles
_add("Line Portfolio", T, 'IF ( NOT ISBLANK ( [Story | Aligned Budget %] ), FORMAT ( [Story | Aligned Budget %], "0%" ) & " budget aligned" )')
_add("Line Financials", T, 'FORMAT ( [Story | Projects Over Budget] + 0, "0" ) & " over EAC"')
_add("Line Resources", T, 'FORMAT ( [Story | Over-allocated People] + 0, "0" ) & " over 100%"')
_add("Line Schedule", T, 'FORMAT ( [Story | Baseline · Late Projects] + 0, "0" ) & " slipping"')
_add("Line Risk", T, 'FORMAT ( [Story | Critical High Risks] + 0, "0" ) & " critical"')
_add("Line Benefits", T, 'IF ( ISBLANK ( [Story | Benefit Cost Ratio] ), "no benefits plan", "Benefit/cost " & FORMAT ( [Story | Benefit Cost Ratio], "0.0" ) )')
_add("Line Timesheets", T, 'FORMAT ( [Story | TS Status · Missing Timesheets] + 0, "0" ) & " missing"')
_add("Line Governance", T, 'IF ( NOT ISBLANK ( [PMO | Governance Score] ), "Score " & FORMAT ( [PMO | Governance Score], "0" ) )')
_add("Colour Portfolio", T, f"""
VAR _p = [Story | Aligned Budget %]
RETURN IF ( ISBLANK ( _p ), "{GREY}", IF ( _p >= 0.8, "{C_TEAL}", IF ( _p >= 0.6, "{C_AMBER}", "{C_RED}" ) ) )""",
     folder=FOLDER + "\\Colours")
_add("Colour Schedule", T, f"""
VAR _late10 = COUNTROWS ( FILTER ( {PROJECTS}, [Story | Baseline · Finish Slip (days)] > 10 ) )
RETURN IF ( _late10 > 0, "{C_RED}", IF ( [Story | Baseline · Late Projects] > 0, "{C_AMBER}", "{C_TEAL}" ) )""",
     folder=FOLDER + "\\Colours")
_add("Colour Risk", T, f'IF ( [Story | Critical High Risks] > 0, "{C_RED}", "{C_TEAL}" )', folder=FOLDER + "\\Colours")
_add("Colour Benefits", T, f'IF ( [Story | Benefit Cost Ratio] >= 1, "{C_TEAL}", "{C_AMBER}" )', folder=FOLDER + "\\Colours")
_add("Colour Timesheets", T, f'IF ( [Story | TS Status · Missing Timesheets] > 0, "{C_AMBER}", "{C_TEAL}" )',
     folder=FOLDER + "\\Colours")

# ---------------------------------------------------------------- executive answers: first sentence of each headline
FIRST = 'VAR _h = [{src}] RETURN IF ( ISBLANK ( _h ), BLANK (), LEFT ( _h, FIND ( ". ", _h & ". " ) ) )'
for _a, _src in [("Finance", "Story | Finance Headline"), ("Schedule", "Story | Schedule Headline"),
                 ("Resources", "Story | Resource Headline"), ("Benefits", "Story | Benefits Headline")]:
    _add(f"Answer {_a}", T, FIRST.format(src=_src))


# ====================================================================== layout
CANVAS, PANEL, INK2, LABEL = "#141C2F", "#1B2540", "#E8ECF4", "#8C98B3"
X0, X1 = 104, 1784          # body left / right edge
CHART_H = 110              # progress-bar chart height (Desktop min ~100px)
BODY_Y = 400                # top of the view bodies
RAIL = [("cc", "home", "Command center"),
        ("exec", "exec", "1 Executive summary"),
        ("portfolio", "portfolio", "2 Portfolio — Gates · Scenarios · Project One-Pager"),
        ("finance", "finance", "3 Financials — Pareto and P&L"),
        ("resources", "resources", "4 Resources — Timesheets · TS status · Person"),
        ("schedule", "schedule", "5 Schedule — Gantt · Status trend · Plan vs baseline"),
        ("risk", "risk", "6 Risk"),
        ("benefits", "benefits", "7 Benefits"),
        ("governance", "governance", "8 Governance")]


def panel(pg, x, y, w, h, key, parent=None, fill=PANEL):
    return pg.add(x, y, w, h, shape(fill, radius=14), key=key, parent=parent)


def ghost_link(target_key, tooltip):
    """Transparent page-navigation button laid over a card / icon."""
    v = nav_button("", pages.PID[target_key], tooltip, fill=CANVAS, hover=CANVAS, press=CANVAS)
    v["objects"]["fill"] = [{"properties": {"show": b(True)}},
                            {"properties": {"fillColor": col_solid(CANVAS), "transparency": n(100)}, "selector": {"id": "default"}},
                            {"properties": {"fillColor": col_solid("#FFFFFF"), "transparency": n(92)}, "selector": {"id": "hover"}}]
    return v


def dark_card(measure, label, colour_measure=None, colour=INK2, size=26):
    v = card(measure, label, value_colour=colour, colour_measure=colour_measure, size=size, dark=True)
    vco = v["visualContainerObjects"]
    vco["title"] = pbir.title(label, 10, LABEL)
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    return v


def text_line(measure, size=11, colour=INK2, bg=PANEL):
    v = headline(measure, bg=bg, border=bg, size=size, colour=colour)
    # card chrome padding eats the text box; zero it so short single-line cards do not clip
    v["visualContainerObjects"]["padding"] = [{"properties": {"top": n(0), "bottom": n(0), "left": n(0), "right": n(0)}}]
    return v


def sparkline(measure, colour):
    v = chart("lineChart", {"Category": [P(C("DimDate", "MonthStart"), "Month")], "Y": [P(M(measure), " ")]}, "",
              {"dataPoint": [measure_fill(M(measure), colour)], "legend": legend(show=False),
               "categoryAxis": [{"properties": {"show": b(False)}}], "valueAxis": [{"properties": {"show": b(False)}}],
               "lineStyles": [{"properties": {"strokeWidth": n(2), "showMarker": b(False)}}]},
              sort=[(C("DimDate", "MonthStart"), "Ascending")])
    vco = v["visualContainerObjects"]
    vco["title"] = [{"properties": {"show": b(False)}}]
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    return v


def progress(pg, x, y, w, h, value_measure, lo, hi, colour, key):
    """Track (grey rounded shape, x/y/w/h) with a single-measure bar chart on top; value axis fixed to lo..hi.
    Desktop shows only a placeholder icon for a bar chart shorter than ~100px, so the chart is CHART_H tall and
    centred on the track (its bar is a thin line in the middle). It is transparent and sits below the Task 5 body."""
    pg.add(x, y, w, h, shape("#3A4768", radius=4), key=f"{key}_track")
    v = chart("clusteredBarChart", {"Y": [P(M(value_measure), "v")]}, "",
              {"dataPoint": [measure_fill(M(value_measure), colour)], "legend": legend(show=False),
               "categoryAxis": [{"properties": {"show": b(False)}}],
               "valueAxis": [{"properties": {"show": b(False), "start": n(lo), "end": n(hi)}}]})
    vco = v["visualContainerObjects"]
    vco["title"] = [{"properties": {"show": b(False)}}]
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    # the chart's plot area is inset ~15px on both sides, so the chart is 30px wider than the track
    pg.add(x - 15, round(y + h / 2 - CHART_H / 2, 2), w + 30, CHART_H, v, key=key)


def dark_slicer(field, label):
    v = slicer(field, label, dark=True)
    v["objects"]["items"] = [{"properties": {"fontFamily": s("Segoe UI"), "textSize": n(10),
                                             "fontColor": col_solid(INK2), "background": col_solid(PANEL)}}]
    return v


def build_rail(pg):
    panel(pg, 16, 16, 72, 968, "rail_bg")
    for k, (icon, target, tip) in enumerate(RAIL):
        y = 32 + k * 64
        on = target == "home"
        if on:
            pg.add(26, y, 52, 52, shape(ORANGE, radius=12), key=f"rail_on_{icon}")
        pg.add(36, y + 10, 32, 32, image(f"rail-{icon}-{'white' if on else 'grey'}.png", f"{icon} icon"), key=f"rail_img_{icon}")
        if not on:
            pg.add(26, y, 52, 52, ghost_link(target, tip), key=f"rail_btn_{icon}")


def build_top(pg):
    pg.add(X0, 8, 700, 40, text_line(hm("Greeting"), size=16, bg=CANVAS), key="greet")
    pg.add(X0, 50, 700, 32, text_line(hm("Refreshed"), size=11, colour=LABEL, bg=CANVAS), key="refreshed")
    pg.add(1180, 14, 180, 62, dark_slicer(pages.DP("Portfolio Name"), "Portfolio"), key="sl_portfolio")
    pg.add(1370, 14, 180, 62, dark_slicer(pages.DP("Program Name"), "Program"), key="sl_program")


def build_pulse(pg):
    # briefing (orange) + two lead KPIs with sparkline and change chip
    panel(pg, X0, 92, 640, 150, "brief_bg", fill=ORANGE)
    pg.add(X0 + 16, 100, 608, 24, textbox([[("This week's briefing", st("Segoe UI", 10, "#FFFFFF"))]]), key="brief_lbl")
    pg.add(X0 + 8, 124, 624, 84, headline(hm("Briefing"), bg=ORANGE, border=ORANGE, size=14, colour="#FFFFFF"), key="brief")
    for k, (m, label, cm, series, chg, col) in enumerate([
            ("Story | EAC Variance %", "EAC vs budget", hm("Colour EAC"), hm("EAC Var % (reports)"),
             hm("EAC Change"), C_RED),
            ("Story | On Track %", "On track", None, hm("On Track % (reports)"), hm("On Track Change"), C_TEAL)]):
        x = X0 + 656 + k * 520
        panel(pg, x, 92, 504, 150, f"lead_bg{k}")
        pg.add(x + 8, 96, 250, 104, dark_card(m, label, colour_measure=cm, size=30), key=f"lead{k}")
        pg.add(x + 270, 100, 220, 44, text_line(chg, size=11, colour=LABEL), key=f"lead_chg{k}")
        pg.add(x + 270, 148, 226, 88, sparkline(series, col), key=f"lead_spark{k}")
        pg.add(x, 92, 504, 150, ghost_link("finance" if k == 0 else "exec", label), key=f"lead_go{k}")
    # four small KPIs
    small = [("Story | Active Projects", "Active projects", None, None, "portfolio"),
             ("Story | Utilisation %", "Utilisation", hm("Colour Util"), (0, 1, C_AMBER), "resources"),
             ("Story | Critical High Risks", "Critical risks", None, None, "risk"),
             ("PMO | Governance Score", "Data trust", hm("Colour Trust"), (0, 100, C_TEAL), "governance")]
    w = (X1 - X0 - 3 * 16) / 4
    for k, (m, label, cm, bar, target) in enumerate(small):
        x = round(X0 + k * (w + 16), 2)
        panel(pg, x, 254, round(w, 2), 134, f"kpi_bg{k}")
        pg.add(x + 8, 258, round(w - 16, 2), 92, dark_card(m, label, colour_measure=cm), key=f"kpi{k}")
        if bar:
            progress(pg, x + 16, 356, round(w - 32, 2), 16, m, bar[0], bar[1], bar[2], f"kpi_bar{k}")
        pg.add(x, 254, round(w, 2), 134, ghost_link(target, label), key=f"kpi_go{k}")


AREAS = [  # (label, line measure, colour measure, [(link text, page key)])
    ("Portfolio", "Line Portfolio", hm("Colour Portfolio"), [("Portfolio", "portfolio"), ("Gates", "lifecycle"),
                                                             ("Scenarios", "scenarios"), ("Project", "onepager")]),
    ("Financials", "Line Financials", hm("Colour EAC"), [("Spend", "finance"), ("Pareto", "finance2")]),
    ("Resources", "Line Resources", hm("Colour Util"), [("People", "resources"), ("Time", "timesheets"),
                                                           ("Person", "resource")]),
    ("Schedule", "Line Schedule", hm("Colour Schedule"), [("Schedule", "schedule"), ("Gantt", "gantt"),
                                                          ("Trend", "status"), ("Baseline", "baseline")]),
    ("Risk", "Line Risk", hm("Colour Risk"), [("Risk", "risk")]),
    ("Benefits", "Line Benefits", hm("Colour Benefits"), [("Benefits", "benefits")]),
    ("Timesheets", "Line Timesheets", hm("Colour Timesheets"), [("TS status", "tsstatus")]),
    ("Governance", "Line Governance", hm("Colour Trust"), [("Governance", "governance")]),
]


def link_chip(text, target):
    return nav_button(f"{text} ›", pages.PID[target], dict(pages.PAGES)[target], fill=PANEL, hover="#26314F",
                      press=ORANGE, font="#F29A6B", size=9, align="left", margin=4)


def stripe(measure):
    """Thin status stripe: a rectangle whose fill is the colour measure (fx field value)."""
    v = shape(PANEL)
    v["objects"]["fill"] = [{"properties": {"show": b(True), "fillColor": measure_colour(measure), "transparency": n(0)},
                             "selector": {"id": "default"}}]
    return v


def build_pmo(pg, grp):
    # left: act now + next 30 days
    lw = 820
    panel(pg, X0, BODY_Y, lw, 588, "act_bg", parent=grp)
    pg.add(X0 + 16, BODY_Y + 8, 400, 30, textbox([[("Act now", st("Segoe UI Semibold", 14, INK2, True)),
                                                   ("   ranked by impact", st("Segoe UI", 10, LABEL))]]),
           key="act_title", parent=grp)
    obj = pbir.table_style(10, header_bg=PANEL)
    obj["values"] = [{"properties": {"fontSize": n(10), "fontColorPrimary": col_solid(INK2),
                                     "backColorPrimary": col_solid(PANEL), "fontColorSecondary": col_solid(INK2),
                                     "backColorSecondary": col_solid(PANEL)}},
                     pbir.cf_font(M(hm("Act Reason")), hm("Act Colour"))]
    obj["grid"] = [{"properties": {"gridHorizontal": b(True), "gridHorizontalColor": col_solid("#26314F"),
                                   "rowPadding": n(6)}}]
    obj["total"] = [{"properties": {"totals": b(False)}}]
    tbl = chart("tableEx", {"Values": [P(pages.DP("Name"), "Project"), P(M(hm("Act Reason")), "Why"),
                                       P(pages.DP("Manager_Value"), "Owner"), P(M(hm("Act Score")), "Impact")]},
                "", obj, sort=[(M(hm("Act Score")), "Descending")])
    tbl["visualContainerObjects"]["title"] = [{"properties": {"show": b(False)}}]
    tbl["visualContainerObjects"]["background"] = [{"properties": {"show": b(False)}}]
    tbl["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    pg.add(X0 + 8, BODY_Y + 42, lw - 16, 300, tbl, key="act_tbl", parent=grp, filters=[pages.REAL_PROJECTS])
    pg.add(X0 + 16, BODY_Y + 348, 260, 34, pbir.drill_button("Open One-Pager ›", pages.PID["project"],
           "Select a project row first", fill=ORANGE, size=10), key="act_drill", parent=grp)
    pg.add(X0 + 290, BODY_Y + 352, 500, 26, textbox([[("Select a row, then open — or right-click › Drill through",
                                                      st("Segoe UI", 9, LABEL))]]), key="act_hint", parent=grp)
    pg.add(X0 + 16, BODY_Y + 392, 400, 28, textbox([[("Next 30 days", st("Segoe UI Semibold", 13, INK2, True))]]),
           key="next_title", parent=grp)
    mobj = pbir.table_style(10, header_bg=PANEL)
    mobj["values"] = obj["values"][:1]
    mobj["grid"] = obj["grid"]
    mobj["total"] = obj["total"]
    due = M(hm("Due In 30d"))
    # rows outside the next 30 days vanish: the only measure in the row is blank for them
    mobj["columnWidth"] = [{"properties": {"value": n(1)}, "selector": {"metadata": pbir.qref(due)}}]
    miles = chart("tableEx", {"Values": [P(pages.DT("EndDate"), "Due"), P(pages.DP("Name"), "Project"),
                                         P(pages.DT("Name"), "Milestone"), P(due, " ")]}, "", mobj,
                  sort=[(pages.DT("EndDate"), "Ascending")])
    miles["visualContainerObjects"]["title"] = [{"properties": {"show": b(False)}}]
    miles["visualContainerObjects"]["background"] = [{"properties": {"show": b(False)}}]
    miles["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    pg.add(X0 + 8, BODY_Y + 422, lw - 16, 158, miles, key="next_tbl", parent=grp,
           filters=[pbir.f_in("DimTask", "Milestone", [True]), pbir.f_cmp("DimTask", "PercentDone", 3, 100),
                    pages.PROJECT_TASKS])
    # right: area health 2 x 4
    ax, aw = X0 + lw + 16, X1 - (X0 + lw + 16)
    tw, th = (aw - 16) / 2, (588 - 3 * 12) / 4
    for k, (label, line, colour, links) in enumerate(AREAS):
        x = round(ax + (k % 2) * (tw + 16), 2)
        y = round(BODY_Y + (k // 2) * (th + 12), 2)
        panel(pg, x, y, round(tw, 2), round(th, 2), f"area_bg{k}", parent=grp)
        pg.add(x, y, round(tw, 2), 4, stripe(colour), key=f"area_stripe{k}", parent=grp)
        pg.add(x + 14, y + 10, 300, 22, textbox([[(label, st("Segoe UI", 10, LABEL))]]), key=f"area_lbl{k}", parent=grp)
        pg.add(x + 8, y + 32, round(tw - 16, 2), 38, text_line(hm(line), size=14), key=f"area_line{k}", parent=grp)
        cw = min(110, (tw - 28 - 6 * (len(links) - 1)) / len(links))
        for j, (txt, target) in enumerate(links):
            pg.add(round(x + 14 + j * (cw + 6), 2), round(y + th - 38, 2), round(cw, 2), 28, link_chip(txt, target),
                   key=f"area_link{k}_{j}", parent=grp)


def build_exec(pg, grp):
    decisions = [("Money decision", "Story | Exec Action Money", hm("Colour EAC"), "finance"),
                 ("People decision", "Story | Exec Action People", hm("Colour Util"), "resources"),
                 ("Risk decision", "Story | Exec Action Risk", hm("Colour Risk"), "risk")]
    dw = (X1 - X0 - 2 * 16) / 3
    for k, (label, m, colour, target) in enumerate(decisions):
        x = round(X0 + k * (dw + 16), 2)
        panel(pg, x, BODY_Y, round(dw, 2), 280, f"dec_bg{k}", parent=grp)
        pg.add(x, BODY_Y, round(dw, 2), 4, stripe(colour), key=f"dec_stripe{k}", parent=grp)
        pg.add(x + 16, BODY_Y + 12, 300, 24, textbox([[(label, st("Segoe UI", 10, LABEL))]]), key=f"dec_lbl{k}", parent=grp)
        pg.add(x + 8, BODY_Y + 40, round(dw - 16, 2), 190, text_line(m, size=16), key=f"dec{k}", parent=grp)
        pg.add(x + 16, BODY_Y + 238, 160, 30, link_chip(dict(pages.PAGES)[target].split("·", 1)[-1].strip(), target),
               key=f"dec_go{k}", parent=grp)
    answers = [("Are we spending as planned?", "Answer Finance", hm("Colour EAC"), "finance"),
               ("Will we deliver on time?", "Answer Schedule", hm("Colour Schedule"), "schedule"),
               ("Do we have the people?", "Answer Resources", hm("Colour Util"), "resources"),
               ("Will it pay off?", "Answer Benefits", hm("Colour Benefits"), "benefits")]
    aw = (X1 - X0 - 3 * 16) / 4
    for k, (q, m, colour, target) in enumerate(answers):
        x = round(X0 + k * (aw + 16), 2)
        y = BODY_Y + 296
        panel(pg, x, y, round(aw, 2), 292, f"ans_bg{k}", parent=grp)
        pg.add(x, y, round(aw, 2), 4, stripe(colour), key=f"ans_stripe{k}", parent=grp)
        pg.add(x + 16, y + 12, round(aw - 32, 2), 26, textbox([[(q, st("Segoe UI Semibold", 11, INK2, True))]]),
               key=f"ans_q{k}", parent=grp)
        pg.add(x + 8, y + 44, round(aw - 16, 2), 196, text_line(hm(m), size=13), key=f"ans{k}", parent=grp)
        pg.add(x + 16, y + 250, 120, 30, link_chip("Open", target), key=f"ans_go{k}", parent=grp)


def build_switch(pg, bm_pmo, bm_exec):
    panel(pg, 1580, 24, 196, 44, "switch_bg")
    for k, (txt, bm) in enumerate([("PMO", bm_pmo), ("Executive", bm_exec)]):
        pg.add(1586 + k * 94, 30, 90, 32, pbir.bookmark_button(txt, bm, f"Show the {txt} view", fill=PANEL,
               hover=ORANGE, press=ORANGE, font=INK2, size=10, radius=16), key=f"switch{k}")


def build():
    pg = Page(pages.PID["home"], dict(pages.PAGES)["home"], pages.W, 1000, background_colour=CANVAS,
              display_option="FitToPage")
    build_rail(pg)
    build_top(pg)
    build_pulse(pg)
    g_pmo = pg.add_group(X0, BODY_Y, X1 - X0, 588, "PMO view", key="grp_pmo")
    g_exec = pg.add_group(X0, BODY_Y, X1 - X0, 588, "Executive view", key="grp_exec", hidden=True)
    build_pmo(pg, g_pmo)
    build_exec(pg, g_exec)
    bm_pmo = pbir.bookmark("Home · PMO view", "home_pmo", pg.id, {g_pmo: False, g_exec: True})
    bm_exec = pbir.bookmark("Home · Executive view", "home_exec", pg.id, {g_pmo: True, g_exec: False})
    build_switch(pg, bm_pmo, bm_exec)
    pg.add(X0 + 8, 208, 220, 28, pbir.bookmark_button("See the act-now list ›", bm_pmo, "Show the PMO view",
           fill=ORANGE, hover="#C84F1D", press="#C84F1D", font="#FFFFFF", size=10, align="left", margin=8),
           key="brief_link")
    return [pg]
