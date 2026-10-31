"""Home — the command center (replaces pages.build_home).

Measures: report-level, prefix "Story | Home · ", folder Story\\Home. Built on the chapter measures;
history-based numbers (sparklines, change chips) come from FactStatusReport snapshots per report month.
Layout: see build() (Task 4/5). Spec: docs/superpowers/specs/2026-10-31-insights-command-center-design.md
"""
import pbir
from pbir import NAVY, ORANGE, TEAL, AMBER, RED, GREY, MUTED
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
LATEST = """CALCULATE ( MAX ( FactStatusReport[{col}] ),
            TOPN ( 1, FactStatusReport, FactStatusReport[Report_ReportEnd], DESC ) )"""
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
VAR _d = ( _a - _b ) * 100
RETURN
    IF ( NOT ISBLANK ( _a ) && NOT ISBLANK ( _b ),
        IF ( _d > 0, "▲ ", IF ( _d < 0, "▼ ", "= " ) ) & FORMAT ( _d, "+0.0;-0.0;0.0" ) & " pt vs last month" )"""
_add("EAC Change", T, CHANGE.format(src=hm("EAC Var % (reports)")), desc="Change vs previous report month, points.")
_add("On Track Change", T, CHANGE.format(src=hm("On Track % (reports)")), desc="Change vs previous report month, points.")

# ---------------------------------------------------------------- next 30 days (milestone table row filter)
_add("Due In 30d", I, 'VAR _d = MAX ( DimTask[EndDate] ) RETURN IF ( _d >= TODAY () && _d <= TODAY () + 30, 1 )', "0",
     "1 for a task due in the next 30 days; drives the Next 30 days table on Home.")

# ---------------------------------------------------------------- progress-bar remainders
_add("Util Remainder", D, "VAR _u = [Story | Utilisation %] RETURN IF ( _u < 1, 1 - _u )", "0%")
_add("Trust Remainder", D, "VAR _g = [PMO | Governance Score] RETURN IF ( NOT ISBLANK ( _g ), 100 - _g )", "0")

# ---------------------------------------------------------------- area tiles
_add("Line Portfolio", T, 'FORMAT ( [Story | Aligned Budget %], "0%" ) & " budget aligned"')
_add("Line Financials", T, 'FORMAT ( [Story | Projects Over Budget] + 0, "0" ) & " over EAC"')
_add("Line Resources", T, 'FORMAT ( [Story | Over-allocated People] + 0, "0" ) & " over 100%"')
_add("Line Schedule", T, 'FORMAT ( [Story | Baseline · Late Projects] + 0, "0" ) & " slipping"')
_add("Line Risk", T, 'FORMAT ( [Story | Critical High Risks] + 0, "0" ) & " critical"')
_add("Line Benefits", T, 'IF ( ISBLANK ( [Story | Benefit Cost Ratio] ), "no benefits plan", "Benefit/cost " & FORMAT ( [Story | Benefit Cost Ratio], "0.0" ) )')
_add("Line Timesheets", T, 'FORMAT ( [Story | TS Status · Missing Timesheets] + 0, "0" ) & " missing"')
_add("Line Governance", T, '"Score " & FORMAT ( [PMO | Governance Score], "0" )')
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


def build():
    return []
