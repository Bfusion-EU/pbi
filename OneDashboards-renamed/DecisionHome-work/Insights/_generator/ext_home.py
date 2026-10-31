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

# ---------------------------------------------------------------- progress-bar remainders
_add("Util Remainder", D, "VAR _u = [Story | Utilisation %] RETURN IF ( NOT ISBLANK ( _u ) && _u < 1, 1 - _u )", "0%")
_add("Trust Remainder", D, "VAR _g = [PMO | Governance Score] RETURN IF ( NOT ISBLANK ( _g ), 100 - _g )", "0")

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
BODY_Y = 396                # top of the view bodies
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
    return headline(measure, bg=bg, border=bg, size=size, colour=colour)


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


def progress(value_measure, rest_measure, colour):
    v = chart("hundredPercentStackedBarChart", {"Y": [P(M(value_measure), "v"), P(M(rest_measure), "rest")]}, "",
              {"dataPoint": [measure_fill(M(value_measure), colour), measure_fill(M(rest_measure), "#26314F")],
               "legend": legend(show=False), "categoryAxis": [{"properties": {"show": b(False)}}],
               "valueAxis": [{"properties": {"show": b(False)}}]})
    vco = v["visualContainerObjects"]
    vco["title"] = [{"properties": {"show": b(False)}}]
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    return v


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
    pg.add(X0, 4, 700, 52, text_line(hm("Greeting"), size=16, bg=CANVAS), key="greet")
    pg.add(X0, 54, 700, 38, text_line("Story | Refreshed", size=10, colour=LABEL, bg=CANVAS), key="refreshed")
    pg.add(1180, 14, 180, 62, dark_slicer(pages.DP("Portfolio Name"), "Portfolio"), key="sl_portfolio")
    pg.add(1370, 14, 180, 62, dark_slicer(pages.DP("Program Name"), "Program"), key="sl_program")


def build_pulse(pg):
    # briefing (orange) + two lead KPIs with sparkline and change chip
    panel(pg, X0, 92, 640, 150, "brief_bg", fill=ORANGE)
    pg.add(X0 + 16, 100, 608, 24, textbox([[("This week's briefing", st("Segoe UI", 10, "#FFFFFF"))]]), key="brief_lbl")
    pg.add(X0 + 8, 124, 624, 108, headline(hm("Briefing"), bg=ORANGE, border=ORANGE, size=14, colour="#FFFFFF"), key="brief")
    for k, (m, label, cm, series, chg, col) in enumerate([
            ("Story | EAC Variance %", "EAC vs budget", "Story | Variance Colour", hm("EAC Var % (reports)"),
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
             ("Story | Utilisation %", "Utilisation", "Story | Util Colour", (hm("Util Remainder"), C_AMBER), "resources"),
             ("Story | Critical High Risks", "Critical risks", None, None, "risk"),
             ("PMO | Governance Score", "Data trust", "PMO | Governance RAG Colour", (hm("Trust Remainder"), C_TEAL), "governance")]
    w = (X1 - X0 - 3 * 16) / 4
    for k, (m, label, cm, bar, target) in enumerate(small):
        x = round(X0 + k * (w + 16), 2)
        panel(pg, x, 254, round(w, 2), 134, f"kpi_bg{k}")
        pg.add(x + 8, 258, round(w - 16, 2), 92, dark_card(m, label, colour_measure=cm), key=f"kpi{k}")
        if bar:
            pg.add(x + 8, 350, round(w - 16, 2), 36, progress(m, bar[0], bar[1]), key=f"kpi_bar{k}")
        pg.add(x, 254, round(w, 2), 134, ghost_link(target, label), key=f"kpi_go{k}")


def build():
    pg = Page(pages.PID["home"], dict(pages.PAGES)["home"], pages.W, 1000, background_colour=CANVAS,
              display_option="FitToPage")
    build_rail(pg)
    build_top(pg)
    build_pulse(pg)
    return [pg]
