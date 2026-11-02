"""Home — the command center (replaces pages.build_home).

Measures: report-level, prefix "Story | Home · ", folder Story\\Home. Built on the chapter measures;
history-based numbers (sparklines, change chips) come from FactStatusReport snapshots per report month.
Layout: see build() (Task 4/5). Spec: docs/superpowers/specs/2026-10-31-insights-command-center-design.md
"""
import pages
import pbir
from pbir import (ORANGE, PEACH, GREY, Page, headline, chart, textbox, st, shape, image, slicer, nav_button,
                  P, M, C, s, b, n, col_solid, measure_colour, measure_fill, legend)
from story_measures import add, T, D, I, money, RISK, IMPACT_SCORE, PROB_SCORE, HIGH_HEAT
from ext_status import STALE_DAYS  # same threshold as Story | Status · Not Reporting

PX = "Story | Home · "
FOLDER = "Story\\Home"
C_RED, C_AMBER, C_TEAL = "#FF8A80", "#F2C46B", "#5DCAA5"
C_GREY = "#8C98B3"
PROJECTS = "FILTER ( VALUES ( DimProject[Id] ), NOT ISBLANK ( DimProject[Id] ) )"


def hm(name):
    return PX + name


def _add(name, dtype, expr, fmt=None, desc=None, folder=FOLDER):
    add(hm(name), dtype, expr, fmt, folder, desc)


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
            [Story | Slip · Flag] = 1, 70,
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
        70, [Story | Slip · Reason],
        50, "No status report for " & FORMAT ( [Story | Status · Days Since Report], "0" ) & " days",
        40, FORMAT ( [Story | Project · Failing Rules], "0" ) & " Plan Insights rule(s) failing" )""")
_add("Act Colour", T, f"""
VAR _s = [{hm("Act Score")}]
RETURN IF ( ISBLANK ( _s ), BLANK (), IF ( _s >= 80, "{C_RED}", "{C_AMBER}" ) )""", folder=FOLDER + "\\Colours")
_add("Act Count", I, f"COUNTROWS ( FILTER ( {PROJECTS}, NOT ISBLANK ( [{hm('Act Score')}] ) ) ) + 0", "0")

# Reasons are counted from the same Act Score buckets as the Act-now table, so the parts add up to Act Count.
_BUCKETS = [(100, "off track"), (90, "over budget"), (80, "late"), (70, "may slip"),
            (50, "not reporting"), (40, "failing rules")]
_add("Briefing Pill", T, f"""
VAR _n = [{hm("Act Count")}]
VAR _a = [Story | Active Projects] + 0
RETURN IF ( _n = 0, "No project needs a decision",
    FORMAT ( _n, "0" ) & " of " & FORMAT ( _a, "0" ) & IF ( _n = 1, " needs", " need" ) & " a decision" )""",
     desc="How many active projects need a decision (Act-now count), short form for the header pill.")
# One chip per Act-score bucket (same buckets as the Act-now table, so the six counts add up to Act Count).
CHIPS = [(k, lbl, lbl.title(), C_RED if k >= 80 else C_AMBER) for k, lbl in _BUCKETS]    # (score, label, name, dot colour)
CHIP_ON, CHIP_OFF = "#E8ECF4", "#8C98B3"   # off = dimmed but readable (5.2:1 on the card navy)
for _k, _lbl, _nm, _dot in CHIPS:
    _cnt = f"COUNTROWS ( FILTER ( {PROJECTS}, [{hm('Act Score')}] = {_k} ) ) + 0"
    # The count alone: its own card, centred in a fixed-width box so 1- and 2-digit counts line up on every chip.
    _add(f"Chip {_nm}", T, f'''FORMAT ( {_cnt}, "0" )''',
         desc=f"Active projects whose Act score is {_k} ({_lbl}); 0 when none. The six chips add up to Act Count.")
    _add(f"Chip Label {_nm}", T, f'"{_lbl}"',
         desc=f"Label of the '{_lbl}' chip (its own card, so the label starts at the same x on every chip).")
    _add(f"Chip Colour {_nm}", T, f'''IF ( {_cnt} > 0, "{CHIP_ON}", "{CHIP_OFF}" )''',
         desc=f"Chip text colour: light when the count is above 0, dim when 0.", folder=FOLDER + "\\Colours")

# ---------------------------------------------------------------- hover lists: "what's behind this number"
# Every list is a table whose only measures are blank unless the row qualifies, so the other rows vanish (a visual
# filter on an extension measure rendered an EMPTY table in Desktop, so no visual measure filters).
_TIPS = FOLDER + "\\Tooltips"
ONE_PROJECT = "HASONEVALUE ( DimProject[Id] ) && NOT ISBLANK ( SELECTEDVALUE ( DimProject[Id] ) )"
for _k, _lbl, _nm, _dot in CHIPS:
    _add(f"Tip {_nm}", T, f'IF ( [{hm("Act Score")}] = {_k}, [{hm("Act Reason")}] )', folder=_TIPS,
         desc=f"Act-now reason of a project whose Act score is {_k} ({_lbl}); blank for every other project, so the "
              f"chip's hover list and the '{_lbl}' Act-now view show only that bucket.")
_add("Tip Financials", D, f"""
VAR _b = [Story | Budget At Completion]
VAR _e = [Story | Finance EAC]
RETURN IF ( {ONE_PROJECT} && _b > 0 && _e > _b, [Story | EAC Variance %] )""", "+0.0%;-0.0%;0.0%",
     "EAC variance % of a project whose EAC is above its budget (same rule as Story | Projects Over Budget); blank otherwise.",
     folder=_TIPS)
_add("Tip Schedule", D, f"""
VAR _s = [Story | Baseline · Finish Slip (days)]
RETURN IF ( {ONE_PROJECT} && _s > 0, _s )""", "+0",
     "Finish slip in days of a project finishing later than its baseline (same rule as Story | Baseline · Late "
     "Projects); blank otherwise.", folder=_TIPS)
_add("Tip Resources", D, """
VAR _pk =
    MAXX (
        CALCULATETABLE (
            ADDCOLUMNS ( SUMMARIZE ( FactCapacity, DimDate[MonthStart] ), "@u", [Story | Utilisation %] ),
            KEEPFILTERS ( DimResource[Inactive] = FALSE () )
        ),
        [@u]
    )
RETURN IF ( HASONEVALUE ( DimResource[Name] ) && _pk > 1, _pk )""", "0%",
     "Peak monthly utilisation of an active person above 100% in at least one month in view (same rule as Story | "
     "Over-allocated People); blank otherwise.", folder=_TIPS)
_add("Tip Risk", D, f"""
VAR _t =
    FILTER (
        CALCULATETABLE ( DimTask, {RISK} ),
        VAR _i = {IMPACT_SCORE}
        VAR _p = {PROB_SCORE}
        RETURN _i * _p >= {HIGH_HEAT}
    )
RETURN IF ( HASONEVALUE ( DimTask[Name] ) && NOT ISEMPTY ( _t ), SUMX ( _t, DimTask[Exposure] ) + 0 )""", "#,##0",
     f"Exposure score of an active project risk scoring {HIGH_HEAT}+ on the 4×4 grid (same rule as Story | Critical "
     "High Risks); blank otherwise.", folder=_TIPS)

# ---- long lists: at most TIP_ROWS rows. A tooltip cannot scroll, so the list is cut by the same blank-unless pattern:
# the row's Tip measure is BLANK when its rank among the qualifying projects (RANKX over ALLSELECTED of the row column,
# ties broken by name so the cut is exact) is beyond TIP_ROWS. No TopN, no visual measure filter.
TIP_ROWS = 12


def _capped(key, order, then):
    """DAX of a Tip measure: `then` (an expression over _v = the key) when the row is within the top TIP_ROWS."""
    k = f"[{hm(key)}]"
    return f"""
VAR _v = {k}
VAR _nm = SELECTEDVALUE ( DimProject[Name] )
VAR _q = FILTER ( ALLSELECTED ( DimProject[Name] ), NOT ISBLANK ( {k} ) )
VAR _rank = RANKX ( _q, {k}, _v, {order} ) + COUNTROWS ( FILTER ( _q, {k} = _v && DimProject[Name] < _nm ) )
RETURN IF ( NOT ISBLANK ( _v ) && _rank <= {TIP_ROWS}, {then} )"""


def _tip_count(key):
    return f"COUNTROWS ( FILTER ( {PROJECTS}, NOT ISBLANK ( [{hm(key)}] ) ) ) + 0"


def _list_footer(stem, key, noun, order_note, chapter):
    """Subtitle ('16 projects · top 12 by x') and footer ('+4 more · open the X page') cards of a long-list tooltip."""
    _add(f"Tip {stem} Sub", T, f"""
VAR _n = {_tip_count(key)}
RETURN IF ( _n = 0, "None right now",
    FORMAT ( _n, "0" ) & IF ( _n = 1, " {noun[0]}", " {noun[1]}" )
        & IF ( _n > {TIP_ROWS}, " · {order_note[1]}", " · {order_note[0]}" ) )""",
         desc=f"Subtitle of the {stem} hover list: how many rows qualify, and the cut to {TIP_ROWS}.", folder=_TIPS)
    _add(f"Tip {stem} More", T, f"""
VAR _n = {_tip_count(key)}
RETURN IF ( _n > {TIP_ROWS}, "+" & FORMAT ( _n - {TIP_ROWS}, "0" ) & " more · open the {chapter} page", " " )""",
         desc=f"Footer of the {stem} hover list. When every row fits in the {TIP_ROWS} it is a single space: it shows "
              "nothing, where a blank card would print '(Blank)'.", folder=_TIPS)


_add("Tip Portfolio Key", D, f"""
VAR _b = SUM ( DimProject[Budget] )
RETURN IF ( {ONE_PROJECT} && _b > 0, _b )""", "#,##0",
     "Sort key of the Portfolio hover list: plan-field budget of a project that has one (uncapped); blank otherwise.",
     folder=_TIPS)
_add("Tip Portfolio", T, _capped("Tip Portfolio Key", "DESC", """
IF ( SELECTEDVALUE ( DimProject[StrategicAlignment_Value] ) IN { "Strong", "Extreme" }, "Aligned", "Not aligned" )
        & IF ( SELECTEDVALUE ( DimProject[State_Value] ) = "Proposed", " · proposed", "" )"""),
     desc=f"Aligned (Strong / Extreme strategic alignment) or Not aligned, for the {TIP_ROWS} projects with the largest "
          "plan budget; blank otherwise.", folder=_TIPS)
_add("Tip Portfolio Budget", D, f'IF ( NOT ISBLANK ( [{hm("Tip Portfolio")}] ), SUM ( DimProject[Budget] ) )', "#,##0",
     "Plan-field budget of a project listed by Tip Portfolio; blank otherwise.", folder=_TIPS)
_list_footer("Portfolio", "Tip Portfolio Key", ("project", "projects"), ("largest budget first", "top 12 by budget"), "Portfolio")
_add("Tip Benefits Key", D, f"""
VAR _r = [Story | Value Ratio]
RETURN IF ( {ONE_PROJECT} && _r > 0, _r )""", "0.00",
     "Sort key of the Benefits hover list: value ratio of a project that has one (uncapped); blank otherwise.",
     folder=_TIPS)
_add("Tip Benefits", D, _capped("Tip Benefits Key", "ASC", "_v"), "0.00",
     f"Value ratio of the {TIP_ROWS} weakest projects (lowest ratio first); blank otherwise.", folder=_TIPS)
_list_footer("Benefits", "Tip Benefits Key", ("project", "projects"), ("weakest first", "12 weakest first"), "Benefits")
_add("Tip Status Key", I, """
VAR _g = [Story | Status · Reporting Gap]
RETURN IF ( _g >= 1, IF ( _g = 2, 9999, [Story | Status · Days Since Report] ) )""", "0",
     "Sort key of the Status hover list: 9999 for a project that never submitted a report, otherwise the days since "
     "its last one; blank for a project that counts as reporting.", folder=_TIPS)
_add("Tip Status", T, _capped("Tip Status Key", "DESC", """
SWITCH ( [Story | Status · Reporting Gap], 1, "Overdue", 2, "Nothing submitted" )"""),
     desc=f"Overdue / Nothing submitted for the {TIP_ROWS} longest-silent projects that count as not reporting (same "
          "rule as Story | Status · Not Reporting); blank otherwise.", folder=_TIPS)
_add("Tip Status Days", I, f"""
VAR _k = [{hm("Tip Status Key")}]
RETURN IF ( NOT ISBLANK ( [{hm("Tip Status")}] ) && _k < 9999, _k )""", "0",
     "Days since the last submitted report of a listed project; blank when it never submitted one (its sort key is 9999).",
     folder=_TIPS)
_list_footer("Status", "Tip Status Key", ("project not reporting", "projects not reporting"),
             ("longest silence first", "top 12 · longest silence first"), "What Changed")
_add("Tip Governance Key", I, f"""
VAR _f = [Story | Project · Failing Rules]
RETURN IF ( {ONE_PROJECT} && _f > 0, _f )""", "0",
     "Sort key of the Governance hover list: Plan Insights rules failing for a project plan that fails at least one "
     "(uncapped); blank otherwise.", folder=_TIPS)
_add("Tip Governance", I, _capped("Tip Governance Key", "DESC", "_v"), "0",
     f"Number of Plan Insights rules failing for the {TIP_ROWS} project plans that fail the most; blank otherwise.",
     folder=_TIPS)
_list_footer("Governance", "Tip Governance Key", ("project plan", "project plans"),
             ("most failing rules first", "top 12 by failing rules"), "Governance")
_add("Gov Failing Projects", I, f"COUNTROWS ( FILTER ( {PROJECTS}, [Story | Project · Failing Rules] > 0 ) ) + 0", "0",
     "Project plans that fail at least one Plan Insights rule (the rows the Governance hover list can show). "
     "[PMO | Plans Failing] also counts non-project plans, which have no row to list.")

# ---------------------------------------------------------------- history from status-report snapshots
# Per month: every ACTIVE project's latest report as of month end (carried forward, not only projects that reported
# in the month). Months older than 6 return blank (sparkline window).
ACTIVE_PROJECTS = f'CALCULATETABLE ( {PROJECTS}, DimProject[State_Value] = "Active" )'
LATEST = """( VAR _e = CALCULATE ( MAX ( FactStatusReport[Report_ReportEnd] ), REMOVEFILTERS ( DimDate ),
                              FactStatusReport[Report_ReportEnd] < _me + 1 )
            RETURN CALCULATE ( MAX ( FactStatusReport[{col}] ), REMOVEFILTERS ( DimDate ),
                               FactStatusReport[Report_ReportEnd] = _e ) )"""
WINDOW = "MAX ( DimDate[MonthStart] ) >= EDATE ( EOMONTH ( TODAY (), -1 ) + 1, -5 ) && MIN ( DimDate[MonthStart] ) <= TODAY ()"
_add("EAC Var % (reports)", D, f"""
VAR _me = EOMONTH ( MAX ( DimDate[MonthStart] ), 0 )
VAR _act = {ACTIVE_PROJECTS}
VAR _b = SUMX ( _act, {LATEST.format(col="Budget")} )
VAR _f = SUMX ( _act, {LATEST.format(col="Forecast")} )
RETURN IF ( {WINDOW}, DIVIDE ( _f - _b, _b ) )""", "+0.0%;-0.0%;0.0%",
     "Forecast vs budget of active projects, each on its latest status report as of the month end (carried forward).")
_add("On Track % (reports)", D, f"""
VAR _me = EOMONTH ( MAX ( DimDate[MonthStart] ), 0 )
VAR _t = ADDCOLUMNS ( {ACTIVE_PROJECTS}, "@h", {LATEST.format(col="OverallHealth")} )
VAR _n = COUNTROWS ( FILTER ( _t, NOT ISBLANK ( [@h] ) ) )
VAR _ok = COUNTROWS ( FILTER ( _t, LEFT ( [@h], 3 ) = "(1)" ) )
RETURN IF ( {WINDOW} && _n > 0, DIVIDE ( _ok, _n ) )""", "0%",
     "Share of active projects whose latest report as of the month end says On Track (carried forward).")

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
_add("Due", "DateTime", 'VAR _d = MIN ( DimTask[EndDate] ) RETURN IF ( _d >= TODAY () && _d <= TODAY () + 30, _d )',
     "dd mmm yyyy", "Due date of a task due in the next 30 days (blank otherwise); the Next 30 days table on Home lists "
     "only rows where it is not blank.")

# ---------------------------------------------------------------- dark status colours
_COL = FOLDER + "\\Colours"
# remainder to the axis max for the stacked progress bars (fill + remainder = one visual, so they always line up)
_add("Util Rest", D, """VAR _u = [Story | Utilisation %]
RETURN MAX ( 0, 1 - COALESCE ( _u, 0 ) )""", "0%",
     "Remainder of the utilisation progress bar (1 minus utilisation, never below 0; full track when blank).")
_add("Aligned Rest", D, """VAR _p = [Story | Aligned Budget %]
RETURN MAX ( 0, 1 - COALESCE ( _p, 0 ) )""", "0%",
     "Remainder of the budget-aligned progress bar (1 minus aligned share, never below 0; full track when blank).")
_add("Trust Rest", D, """VAR _g = [PMO | Governance Score]
RETURN MAX ( 0, 100 - COALESCE ( _g, 0 ) )""", "0.0",
     "Remainder of the data-trust progress bar (100 minus the score, never below 0; full track when blank).")
_add("Colour EAC", T, f"""
VAR _p = [Story | EAC Variance %]
RETURN IF ( ISBLANK ( _p ), BLANK (), IF ( _p > 0.05, "{C_RED}", IF ( _p > 0, "{C_AMBER}", "{C_TEAL}" ) ) )""",
     desc="Same thresholds as Story | Variance Colour, light-on-dark colours.", folder=_COL)
_add("Colour Util", T, f"""
VAR _u = [Story | Utilisation %]
RETURN IF ( ISBLANK ( _u ), BLANK (), IF ( _u > 1, "{C_RED}", IF ( _u >= 0.8, "{C_TEAL}", IF ( _u >= 0.5, "{C_AMBER}", "{C_GREY}" ) ) ) )""",
     desc="Same thresholds as Story | Util Colour, light-on-dark colours.", folder=_COL)
_add("Colour Trust", T, f"""
VAR _g = [PMO | Governance Score]
RETURN IF ( ISBLANK ( _g ), BLANK (), IF ( _g >= 90, "{C_TEAL}", IF ( _g >= 75, "{C_AMBER}", "{C_RED}" ) ) )""",
     desc="Same thresholds as PMO | Governance RAG Colour (90 / 75), light-on-dark colours.", folder=_COL)
_add("Colour Portfolio", T, f"""
VAR _p = [Story | Aligned Budget %]
RETURN IF ( ISBLANK ( _p ), "{GREY}", IF ( _p >= 0.8, "{C_TEAL}", IF ( _p >= 0.6, "{C_AMBER}", "{C_RED}" ) ) )""",
     folder=FOLDER + "\\Colours")
_add("Colour Schedule", T, f"""
VAR _late10 = COUNTROWS ( FILTER ( {ACTIVE_PROJECTS}, [Story | Baseline · Finish Slip (days)] > 10 ) )
RETURN IF ( _late10 > 0, "{C_RED}", IF ( [Story | Late Active Projects] > 0, "{C_AMBER}", "{C_TEAL}" ) )""",
     folder=FOLDER + "\\Colours")
_add("Colour Risk", T, f'IF ( [Story | Critical High Risks] > 0, "{C_RED}", "{C_TEAL}" )', folder=FOLDER + "\\Colours")
_add("Colour Benefits", T, f"""
VAR _r = [Story | Value Ratio]
RETURN IF ( ISBLANK ( _r ), "{GREY}", IF ( _r >= 1, "{C_TEAL}", "{C_AMBER}" ) )""", folder=FOLDER + "\\Colours",
     desc="Grey when there is no value ratio; teal at 1.0 or more; else amber.")
_add("Colour Financials", T, f"""
VAR _red = COUNTROWS ( FILTER ( {PROJECTS}, [Story | EAC Variance %] > 0.05 ) )
RETURN IF ( _red > 0, "{C_RED}", IF ( [Story | Projects Over Budget] + 0 > 0, "{C_AMBER}", "{C_TEAL}" ) )""",
     folder=_COL, desc="Red: any project more than 5% over EAC; amber: any project over budget; else teal. Matches the card number.")

_add("Colour Status", T, f"""
VAR _w = [Story | Status · MoM Worsened] + 0
VAR _n = [Story | Status · Not Reporting] + 0
RETURN IF ( _w >= 3 || _n >= 5, "{C_RED}", IF ( _w >= 1 || _n >= 1, "{C_AMBER}", "{C_TEAL}" ) )""",
     folder=_COL, desc="Red: 3+ projects worse than last month (as on page 5c) or 5+ not reporting; amber: any; else teal.")

# ---------------------------------------------------------------- subject cards: sentence, pill word, pill fill
WORST = """
VAR _w = TOPN ( 1, FILTER ( ADDCOLUMNS ( {projects}, "@v", {expr} ), NOT ISBLANK ( [@v] ) ), [@v], DESC, DimProject[Id], ASC )
VAR _wn = CALCULATE ( SELECTEDVALUE ( DimProject[Name] ), TREATAS ( SELECTCOLUMNS ( _w, "@id", DimProject[Id] ), DimProject[Id] ) )
VAR _wv = MAXX ( _w, [@v] )"""
SUBJECT_COLOUR = {"Financials": hm("Colour Financials"), "Schedule": hm("Colour Schedule"), "Resources": hm("Colour Util"),
                  "Risk": hm("Colour Risk"), "Portfolio": hm("Colour Portfolio"), "Benefits": hm("Colour Benefits"),
                  "Status": hm("Colour Status"), "Governance": hm("Colour Trust")}
for _s, _cm in SUBJECT_COLOUR.items():
    _add(f"Pill {_s}", T, f"""
VAR _c = [{_cm}]
RETURN SWITCH ( _c, "{C_RED}", "Act", "{C_AMBER}", "Watch", "{C_TEAL}", "OK", "{C_GREY}", "Low", "–" )""",
         desc=f"Status word of the {_s} card, from its colour measure.")
    _add(f"Pill Fill {_s}", T, f"""
VAR _c = [{_cm}]
RETURN SWITCH ( _c, "{C_RED}", "#3A1E22", "{C_AMBER}", "#3A2F18", "{C_TEAL}", "#173A33", "#26314F" )""",
         folder=_COL, desc=f"Pill background of the {_s} card (also the icon tile and the status capsule).")

# ---------------------------------------------------------------- subject cards (design A): unit, chip, facts, captions
_CARD = FOLDER + "\\Cards"
INK = "#E8ECF4"                    # fact value default colour (same as INK2 of the layout)
FIG = "UNICHAR ( 8199 )"           # figure space: 12 pt ~9 px; one extra 38 pt digit (~28 px) = 3 of them

# Unit label right of the hero number. The number is left-aligned and its width depends on the data, so the unit is a
# measure padded with figure spaces: 3 per character beyond the narrowest form of the number ("8", "8%", "0.00", "0.0").
# (subject, number measure, format of the number, narrowest length, unit text)
UNITS = [("Financials", "Story | Projects Over Budget", "#,##0", 1, "projects over EAC"),
         ("Schedule", "Story | Late Active Projects", "#,##0", 1, "slipping vs baseline"),
         ("Resources", "Story | Utilisation %", "0%", 2, "utilisation"),
         ("Risk", "Story | Critical High Risks", "#,##0", 1, "critical risks"),
         ("Portfolio", "Story | Aligned Budget %", "0%", 2, "budget aligned"),
         ("Benefits", "Story | Value Ratio", "0.00", 4, "value / cost"),
         ("Status", "Story | Status · Not Reporting", "#,##0", 1, f"not reporting {STALE_DAYS}+ days"),
         ("Governance", "PMO | Governance Score", "0.0", 3, "data trust score")]
for _s, _num, _fmt, _base, _unit in UNITS:
    _add(f"Unit {_s}", T, f"""
VAR _v = [{_num}]
VAR _extra = IF ( ISBLANK ( _v ), 0, MAX ( 0, LEN ( FORMAT ( _v, "{_fmt}" ) ) - {_base} ) )
RETURN REPT ( {FIG}, 3 * _extra ) & "{_unit}" """, folder=_CARD,
         desc=f"Unit label of the {_s} card number ('{_unit}'), padded with figure spaces so it starts right after the "
              "number however many digits it has.")

# Delta / context chip right of the hero line. A change chip is blank (a single space, and the canvas fill so the
# capsule vanishes) when there is no previous month.
# (subject, change measure, colour when it goes down, colour when it goes up)
MOVES = [("Financials", hm("EAC Change"), C_TEAL, C_RED), ("Schedule", hm("On Track Change"), C_RED, C_TEAL)]
for _s, _src, _down, _up in MOVES:
    _add(f"Delta {_s}", T, f"""
VAR _c = [{_src}]
RETURN IF ( ISBLANK ( _c ), " ",
    SUBSTITUTE ( SUBSTITUTE ( SUBSTITUTE ( _c, " vs last month", "" ), "+", "" ), "-", "" ) )""", folder=_CARD,
         desc=f"Short form of {_src.split('· ')[-1]} for the {_s} chip ('▲ 1.2 pt'); a single space when blank.")
    _add(f"Delta Colour {_s}", T, f"""
VAR _c = [{_src}]
RETURN IF ( ISBLANK ( _c ), "{C_GREY}", SWITCH ( LEFT ( _c, 1 ), "▲", "{_up}", "▼", "{_down}", "{C_GREY}" ) )""",
         folder=_COL, desc=f"{_s} chip text colour: teal when the change is good, red when it is bad, grey when flat.")
    _add(f"Delta Fill {_s}", T, f"""
VAR _c = [{_src}]
VAR _k = IF ( ISBLANK ( _c ), "", LEFT ( _c, 1 ) )
RETURN SWITCH ( TRUE (), _k = "", "#1B2540",
    _k = "▲", "{'#3A1E22' if _up == C_RED else '#173A33'}", _k = "▼", "{'#3A1E22' if _down == C_RED else '#173A33'}",
    "#26314F" )""", folder=_COL, desc=f"{_s} chip fill: tinted like its text; the card colour (invisible) when blank.")
_add("Delta Risk", T, '"of " & FORMAT ( [Story | Active Risk Count] + 0, "0" ) & " active"', folder=_CARD,
     desc="Context chip of the Risk card: how many active risks the critical ones are part of.")
_add("Delta Status", T, f"""
VAR _n = COUNTROWS ( FILTER ( {PROJECTS}, NOT ISBLANK ( [Story | Status · Reporting Gap] ) ) ) + 0
RETURN "of " & FORMAT ( _n, "0" ) & IF ( _n = 1, " project", " projects" )""", folder=_CARD,
     desc="Context chip of the Status reports card: projects in view that are expected to report (same scope as Not Reporting).")

# Sparkline captions: first and last month in the 6-month window that has a value.
SPARK_SRC = {"Financials": hm("EAC Var % (reports)"), "Schedule": hm("On Track % (reports)")}
_WIN_MONTHS = """CALCULATETABLE ( VALUES ( DimDate[MonthStart] ), REMOVEFILTERS ( DimDate ),
        DimDate[MonthStart] >= EDATE ( EOMONTH ( TODAY (), -1 ) + 1, -5 ), DimDate[MonthStart] <= TODAY () )"""
for _s, _src in SPARK_SRC.items():
    for _end, _fn in (("From", "MINX"), ("To", "MAXX")):
        _add(f"Spark {_end} {_s}", T, f"""
VAR _m = FILTER ( {_WIN_MONTHS},
    VAR _ms = DimDate[MonthStart]
    RETURN NOT ISBLANK ( CALCULATE ( [{_src}], REMOVEFILTERS ( DimDate ), DimDate[MonthStart] = _ms ) ) )
VAR _d = {_fn} ( _m, DimDate[MonthStart] )
RETURN IF ( ISBLANK ( _d ), " ", FORMAT ( _d, "mmm" ) )""", folder=_CARD,
             desc=f"{'First' if _end == 'From' else 'Last'} month drawn in the {_s} sparkline (caption); a space when none.")

_add("Unmitigated Rest", D, """VAR _p = [Story | Unmitigated Risk %]
RETURN MAX ( 0, 1 - COALESCE ( _p, 0 ) )""", "0%",
     "Remainder of the without-mitigation progress bar (1 minus the share, never below 0; full track when blank).")

# Facts: two label / value rows per card. Labels are static text; values are text measures ("–" when blank) so a
# blank never prints "(Blank)" or drops the row.
def SHORT(k):
    """Project name cut to k characters (with an ellipsis), so the fact value fits its row."""
    return f'IF ( LEN ( _wn ) > {k}, LEFT ( _wn, {k - 1} ) & "…", _wn )'


def _cnt(expr):
    return f'FORMAT ( {expr} + 0, "0" )'


def _pct(expr):
    return f'VAR _v = {expr}\nRETURN IF ( ISBLANK ( _v ), "–", FORMAT ( _v, "0%" ) )'


def _rag(var_expr, red, amber):
    """Colour of a count-like fact: red at `red`+, amber at `amber`+, else the default ink."""
    r = f'_v >= {red}, "{C_RED}", ' if red is not None else ""
    return f'VAR _v = {var_expr}\nRETURN SWITCH ( TRUE (), {r}_v >= {amber}, "{C_AMBER}", "{INK}" )'


_W_FIN = WORST.format(projects=PROJECTS, expr="[Story | EAC Variance %]")
_W_SCH = WORST.format(projects=PROJECTS, expr="[Story | Baseline · Finish Slip (days)]")
# subject -> [(label, value DAX, colour DAX or an existing colour measure name or None)] x 2
FACTS = {
    "Financials": [
        ("EAC vs budget", 'VAR _v = [Story | EAC Variance %]\nRETURN IF ( ISBLANK ( _v ), "–", FORMAT ( _v, "+0.0%;-0.0%;0.0%" ) )',
         hm("Colour EAC")),
        ("Worst project", f'{_W_FIN}\nRETURN IF ( _wv > 0, {SHORT(14)} & " " & FORMAT ( _wv, "+0%" ), "none over budget" )',
         f'{_W_FIN}\nRETURN IF ( _wv > 0.05, "{C_RED}", IF ( _wv > 0, "{C_AMBER}", "{INK}" ) )')],
    "Schedule": [
        ("On track", _pct("[Story | On Track %]"), None),
        ("Worst slip", f'{_W_SCH}\nRETURN IF ( _wv > 0, {SHORT(18)} & " +" & FORMAT ( _wv, "0" ) & " d", "none late" )',
         f'{_W_SCH}\nRETURN IF ( _wv > 10, "{C_RED}", IF ( _wv > 0, "{C_AMBER}", "{INK}" ) )')],
    "Resources": [
        ("Over 100%", 'VAR _o = [Story | Over-allocated People] + 0\nRETURN FORMAT ( _o, "0" ) & IF ( _o = 1, " person", " people" )',
         _rag("[Story | Over-allocated People] + 0", 1, 1)),
        ("Timesheets missing", _cnt("[Story | TS Status · Missing Timesheets]"),
         _rag("[Story | TS Status · Missing Timesheets] + 0", None, 1))],
    "Risk": [
        ("Active risks", _cnt("[Story | Active Risk Count]"), None),
        ("Without mitigation", _pct("[Story | Unmitigated Risk %]"), _rag("[Story | Unmitigated Risk %] + 0", 0.5, 0.0001))],
    "Portfolio": [
        ("Active projects", _cnt("[Story | Active Projects]"), None),
        ("Proposed", _cnt("[Story | Proposed Projects]"), None)],
    "Benefits": [
        ("Planned benefits", f'VAR _b = [Story | Benefits At Completion]\nRETURN {money("_b")}', None),
        ("EAC", f'VAR _e = [Story | Finance EAC]\nRETURN {money("_e")}', None)],
    "Status": [
        ("Worse vs last month", _cnt("[Story | Status · MoM Worsened]"),
         _rag("[Story | Status · MoM Worsened] + 0", 3, 1)),
        ("Avg days since",
         'VAR _d = [Story | Status · Avg Days Since Report]\nRETURN IF ( ISBLANK ( _d ), "–", FORMAT ( _d, "0" ) & " d" )', None)],
    "Governance": [
        ("Project plans failing", _cnt(f"[{hm('Gov Failing Projects')}]"), _rag(f"[{hm('Gov Failing Projects')}] + 0", None, 1)),
        ("Other plans failing", f"""
VAR _n = [{hm('Gov Failing Projects')}] + 0
RETURN FORMAT ( MAX ( 0, [PMO | Plans Failing] + 0 - _n ), "0" )""", None)],
}
FACT_COLOUR = {}       # (subject, n) -> colour measure name or None
for _s, _rows in FACTS.items():
    for _n, (_lbl, _val, _col) in enumerate(_rows, 1):
        _add(f"Fact {_s} {_n} Value", T, _val, folder=_CARD, desc=f"{_s} card, fact {_n} ('{_lbl}'): the value as text.")
        if _col is None or _col.startswith(PX):
            FACT_COLOUR[(_s, _n)] = _col
        else:
            _add(f"Fact {_s} {_n} Colour", T, _col, folder=_COL, desc=f"{_s} card, fact {_n} ('{_lbl}'): value colour.")
            FACT_COLOUR[(_s, _n)] = hm(f"Fact {_s} {_n} Colour")


# ====================================================================== layout
CANVAS, PANEL, INK2, LABEL = "#141C2F", "#1B2540", "#E8ECF4", "#8C98B3"
X0, X1 = 104, 1784          # body left / right edge
CHART_H = 110              # progress-bar chart height (Desktop min ~100px)
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
    """Transparent page-navigation button laid over a card / icon. The ghost links deliberately also cover the
    sparkline and change-chip tooltips: hovering them shows the link tooltip instead (accepted; the whole card is a link)."""
    v = nav_button("", pages.PID[target_key], tooltip, fill=CANVAS, hover=CANVAS, press=CANVAS)
    v["objects"]["fill"] = [{"properties": {"show": b(True)}},
                            {"properties": {"fillColor": col_solid(CANVAS), "transparency": n(100)}, "selector": {"id": "default"}},
                            {"properties": {"fillColor": col_solid("#FFFFFF"), "transparency": n(92)}, "selector": {"id": "hover"}}]
    return v


def text_line(measure, size=11, colour=INK2, bg=PANEL):
    v = headline(measure, bg=bg, border=bg, size=size, colour=colour)
    # card chrome padding eats the text box; zero it so short single-line cards do not clip
    v["visualContainerObjects"]["padding"] = [{"properties": {"top": n(0), "bottom": n(0), "left": n(0), "right": n(0)}}]
    return v


VALUE_VISUAL = "tableEx"


def _cell(measure, size, colour_measure=None, colour=INK2, bg=PANEL):
    """One-cell table: left-aligned, wrapping text; header blended into the card (panel colour, 1pt)."""
    fc = measure_colour(colour_measure) if colour_measure else col_solid(colour)
    obj = {"columnHeaders": [{"properties": {"backColor": col_solid(bg), "fontColor": col_solid(bg),
                                             "fontSize": n(1), "outline": s("None")}}],
           "values": [{"properties": {"fontSize": n(size), "fontColorPrimary": fc, "backColorPrimary": col_solid(bg),
                                      "fontColorSecondary": fc, "backColorSecondary": col_solid(bg),
                                      "wordWrap": b(True), "outline": s("None")}}],
           "grid": [{"properties": {"gridHorizontal": b(False), "gridVertical": b(False), "rowPadding": n(0),
                                    "outlineColor": col_solid(bg)}}],
           "total": [{"properties": {"totals": b(False)}}]}
    if colour_measure:
        obj["values"].append(pbir.cf_font(M(measure), colour_measure))
    v = chart("tableEx", {"Values": [P(M(measure), " ")]}, "", obj)
    vco = v["visualContainerObjects"]
    vco["title"] = [{"properties": {"show": b(False)}}]
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    return v


def value_cell(measure, colour_measure=None, size=34):
    return _cell(measure, size, colour_measure)


def text_cell(measure, size=11, colour=INK2, colour_measure=None, bg=PANEL):
    return _cell(measure, size, colour_measure, colour, bg)

def fx_fill(measure_field, colour_measure):
    """Series fill driven by a colour measure (fx field value), as the stripes do."""
    return {"properties": {"fill": measure_colour(colour_measure)}, "selector": {"metadata": pbir.qref(measure_field)}}


BAR_REST = "#3A4768"
BAR_PAD = 69               # category inner padding (%): ~11 px bar in the 110 px chart
BAR_DY = 1                 # Desktop draws the single bar ~1 px below the chart centre at BAR_PAD 69 (~14 at 60)


def progress(pg, x, y, w, h, value_measure, rest_measure, lo, hi, colour, key):
    """One stacked bar chart (barChart) with two measures: the value (status colour) and the remainder to the axis
    max (BAR_REST). Fill and track are the same bars, so they line up by construction. The value axis is fixed to
    lo..hi. Desktop shows only a placeholder for a chart shorter than ~100px, so the chart is CHART_H tall, centred
    on y + h/2; the category inner padding (BAR_PAD %) sets the bar thickness (~11 px). With zero container padding the plot
    area spans the whole chart width, so the chart is exactly as wide as the track."""
    fill = measure_fill(M(value_measure), colour) if colour.startswith("#") else fx_fill(M(value_measure), colour)
    v = chart("barChart", {"Y": [P(M(value_measure), "v"), P(M(rest_measure), "rest")]}, "",
              {"dataPoint": [fill, measure_fill(M(rest_measure), BAR_REST)], "legend": legend(show=False),
               "labels": [{"properties": {"show": b(False)}}],
               "categoryAxis": [{"properties": {"show": b(False), "innerPadding": n(BAR_PAD)}}],
               "valueAxis": [{"properties": {"show": b(False), "start": n(lo), "end": n(hi),
                                             "gridlineShow": b(False)}}]})
    vco = v["visualContainerObjects"]
    vco["title"] = [{"properties": {"show": b(False)}}]
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    vco["padding"] = [{"properties": {"top": n(0), "bottom": n(0), "left": n(0), "right": n(0)}}]
    pg.add(x, round(y + h / 2 - CHART_H / 2 - BAR_DY, 2), w, CHART_H, v, key=key)


def dark_slicer(field, label):
    v = slicer(field, label, dark=True)
    v["objects"]["items"] = [{"properties": {"fontFamily": s("Segoe UI"), "textSize": n(10),
                                             "fontColor": col_solid(INK2), "background": col_solid(PANEL)}}]
    # Desktop ignores items.background / dropdown styling for the closed state (still white box); left as is.
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
    pg.add(16, 944, 72, 24, textbox([[("bfusion.eu", st("Segoe UI", 9, LABEL))]], align="center"), key="rail_site")


BAND = (X0, 8, X1 - X0, 76)    # the one header band: x, y, w, h  (y 8-84)
BAR_H = (10, 17, 13, 20, 9)   # the BFusion "equaliser" mark
BX = X0 + 16                   # brand left edge inside the band


def build_brand(pg):
    """BFusion brand mark (5 orange bars), wordmark and product subtitle, left end of the header band."""
    for k, h in enumerate(BAR_H):
        pg.add(BX + 8 * k, round(32 - h / 2, 2), 5, h, shape(ORANGE), key=f"brand_bar{k}")
    pg.add(BX + 42, 14, 200, 34, textbox([[("BFUSION", st("DIN", 18, "#FFFFFF", True))]]), key="brand_word")
    pg.add(BX, 46, 300, 28, textbox([[("PPM Insights 360°  ·  Command center", st("DIN", 14, PEACH))]]), key="brand_sub")


# ---- middle of the band: decision pill + six reason chips (2 rows of 3)
# The pill and chip texts are card visuals, not one-cell tables: a table's header row (~26 px) leaves no room for text in
# a 28 px chip and its bleed-over would paint outside the band. A card has no header and a transparent background.
PILL_X, PILL_W, PILL_Y, PILL_H = 436, 270, 20, 52
CH_FONT = 12                           # chip text, pt (16 px)
CH_H, CH_GAP, CH_W = 28, 6, 158        # every chip is CH_W x CH_H; columns CH_GAP apart (3 x 158 + 2 x 6 = 486)
CH_ROWS_Y = (14, 50)                   # chip tops: rows at y 14-42 and 50-78 inside the band 8-84 (6 px above and below)
CH_X0 = PILL_X + PILL_W + 14           # first column, 14 px right of the pill
# Offsets inside a chip (x from the chip's left edge, y from its top); identical for all six chips.
CH_CAP = (4, 3, 46, 22)                # click-zone capsule x, y, w, h: covers the dot and the count, 3 px inside the chip
CH_DOT, CH_DOT_X = 8, 10               # dot size, x (y centred in the chip)
CH_CNT_X, CH_CNT_W = 20, 28            # count card: fixed width, text centred, so 1- and 2-digit counts share a centre
CH_LBL_X, CH_LBL_PAD = 54, 4           # label text starts here; its card begins CH_LBL_PAD earlier
CH_TXT_Y, CH_TXT_H = 2, CH_H - 4       # both text cards: same y and height, so the baselines match
# Segoe UI 12 pt widths in px (measured), used to size each label card: a card centres its text, so a card as wide as
# the text plus 2 x CH_LBL_PAD puts the text's left edge at CH_LBL_X for every label.
CH_LABEL_PX = {"off track": 57, "over budget": 84, "late": 25, "may slip": 60, "not reporting": 92, "failing rules": 81}


def chip_label_w(label):
    return CH_LABEL_PX[label] + 2 * CH_LBL_PAD


def chip_geometry():
    """-> [(index, x, y, w)] for the six chips: a fixed grid of 3 columns x 2 rows, all CH_W wide."""
    return [(k, CH_X0 + (k % 3) * (CH_W + CH_GAP), CH_ROWS_Y[k // 3], CH_W) for k in range(6)]


def chip_outline(line="#3A4768"):
    v = shape(PANEL, radius=14, line=line)
    v["objects"]["fill"][0]["properties"]["transparency"] = n(100)
    return v


CHIP_SLUG = {k: lbl.replace(" ", "_") for k, (_s, lbl, _n, _d) in enumerate(CHIPS)}
assert list(CHIP_SLUG.values()) == pages.HOME_TIP_BUCKETS


def with_tip(v, tip_key):
    """Report-page tooltip (Canvas) on a visual: hovering it shows the hidden Tooltip page tip_key."""
    v.setdefault("visualContainerObjects", {})["visualTooltip"] = [{"properties": {
        "show": b(True), "type": s("Canvas"), "section": s(pages.PID[tip_key])}}]
    return v


def ghost_bookmark(bm, tooltip, rest=100, radius=6):
    """Bookmark button (click zone) over a text card. `rest` = its transparency at rest (100 = invisible, 92 = a faint
    capsule that shows where to click); a clear white tint on hover."""
    v = pbir.bookmark_button("", bm, tooltip, fill=CANVAS, hover=CANVAS, press=CANVAS, radius=radius)
    v["objects"]["fill"] = [{"properties": {"show": b(True)}},
                            {"properties": {"fillColor": col_solid("#FFFFFF" if rest < 100 else CANVAS),
                                            "transparency": n(rest)}, "selector": {"id": "default"}},
                            {"properties": {"fillColor": col_solid("#FFFFFF"), "transparency": n(65)}, "selector": {"id": "hover"}},
                            {"properties": {"fillColor": col_solid("#FFFFFF"), "transparency": n(50)}, "selector": {"id": "press"}}]
    return v


# Hover AND click on one chip: a report-page tooltip needs a data visual on top (buttons cannot show one), and a click
# needs a button on top. So each chip is split: the LEFT click zone (the capsule over dot + count, CH_CAP) is a transparent bookmark
# button above the text; the rest of the chip (the label words) is the text card, which shows the hover list.
# The pill works the same way: its left zone ("11 of 15") clicks back to the full list, the rest hovers.
# The pill text is centred ("11 of 15 need a decision" at 15 pt); its "11 of 15" part ends ~101 px from the pill's left
# edge, so the click zone is 120 px and stays well under half the pill (270).
PILL_HIT_W = 120


def build_band_links(pg, bm_all, bm_bucket):
    """Click zones over the pill and the chips; added after the band texts so they sit above them in z-order.
    Each chip's zone is a faint capsule (a visible segment of the chip) that lights up on hover."""
    pg.add(PILL_X, PILL_Y, PILL_HIT_W, PILL_H, ghost_bookmark(bm_all, "Show every Act-now project", radius=10),
           key="pill_go")
    for k, x, y, w in chip_geometry():
        cx, cy, cw, ch = CH_CAP
        pg.add(x + cx, y + cy, cw, ch, ghost_bookmark(bm_bucket[CHIP_SLUG[k]], f"Show only the {CHIPS[k][1]} projects "
                                                                                "in Act now", rest=93, radius=ch // 2),
               key=f"chip_go{k}")


def band_text(measure, size, colour=INK2, colour_measure=None):
    """Single-line card on a transparent ground (no header row, no scroll), text centred."""
    v = text_line(measure, size=size, colour=colour)
    v["visualContainerObjects"]["background"] = [{"properties": {"show": b(False)}}]
    v["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    if colour_measure:
        v["objects"]["labels"][0]["properties"]["color"] = measure_colour(colour_measure)
    return v


def build_band(pg):
    pg.add(*BAND, shape(PANEL, radius=12), key="band_bg")
    build_brand(pg)
    # decision pill: orange shape, white text on top
    pg.add(PILL_X, PILL_Y, PILL_W, PILL_H, shape(ORANGE, radius=10), key="pill_bg")
    pg.add(PILL_X + 8, PILL_Y + 4, PILL_W - 16, PILL_H - 8,
           with_tip(band_text(hm("Briefing Pill"), 15, "#FFFFFF"), "tip_home_act"), key="pill")
    for k, x, y, w in chip_geometry():
        nm = CHIPS[k][2]
        pg.add(x, y, w, CH_H, chip_outline(), key=f"chip_bg{k}")
        pg.add(x + CH_DOT_X, y + (CH_H - CH_DOT) / 2, CH_DOT, CH_DOT, shape(CHIPS[k][3], radius=50), key=f"chip_dot{k}")
        pg.add(x + CH_CNT_X, y + CH_TXT_Y, CH_CNT_W, CH_TXT_H,
               band_text(hm(f"Chip {nm}"), CH_FONT, colour_measure=hm(f"Chip Colour {nm}")), key=f"chip_n{k}")
        pg.add(x + CH_LBL_X - CH_LBL_PAD, y + CH_TXT_Y, chip_label_w(CHIPS[k][1]), CH_TXT_H,
               with_tip(band_text(hm(f"Chip Label {nm}"), CH_FONT, colour_measure=hm(f"Chip Colour {nm}")),
                        f"tip_home_{CHIP_SLUG[k]}"), key=f"chip{k}")
    pg.add(1220, 15, 160, 62, dark_slicer(pages.DP("Portfolio Name"), "Portfolio"), key="sl_portfolio")
    pg.add(1390, 15, 160, 62, dark_slicer(pages.DP("Program Name"), "Program"), key="sl_program")


GRID_X0, GRID_Y, COL_W, ROW_H, GAP = 104, (100, 552), 297, 436, 16
RIGHT_X, RIGHT_W, RIGHT_Y, RIGHT_H = 1356, 428, 100, 888

# One spec per subject card (design A). visual: ("area", measure, caption) / ("bar", (lo, hi, rest measure, target or
# None, caption labels (left, at the marker or centre, right))) / None (an explicit empty slot). chip: a measure
# (dynamic text, colour and fill measures by name) or a static text.
SUBJECTS_LAYOUT = [
    dict(key="fin", name="Financials", icon="finance", num="Story | Projects Over Budget", unit="projects over EAC",
         chip=("measure", "Financials"), visual=("area", hm("EAC Var % (reports)"), "Forecast vs budget · reports"),
         colour=hm("Colour Financials"), link="finance", footer=[("Spend", "finance"), ("Pareto", "finance2")]),
    dict(key="sch", name="Schedule", icon="schedule", num="Story | Late Active Projects", unit="slipping vs baseline",
         chip=("measure", "Schedule"), visual=("area", hm("On Track % (reports)"), "% on track · 6 months"),
         colour=hm("Colour Schedule"), link="schedule",
         footer=[("Schedule", "schedule"), ("Gantt", "gantt"), ("Baseline", "baseline")]),
    dict(key="res", name="Resources", icon="resources", num="Story | Utilisation %", unit="utilisation",
         chip=("text", "target 80%"), visual=("bar", (0, 1, hm("Util Rest"), 0.8, ("0%", "target 80%", "100%"))),
         colour=hm("Colour Util"), link="resources",
         footer=[("People", "resources"), ("Time", "timesheets"), ("TS", "tsstatus"), ("Person", "resource")]),
    dict(key="risk", name="Risk", icon="risk", num="Story | Critical High Risks", unit="critical risks",
         chip=("context", "Risk"), visual=("bar", (0, 1, hm("Unmitigated Rest"), None, ("0%", "without mitigation", "100%")),
                                           "Story | Unmitigated Risk %"),
         colour=hm("Colour Risk"), link="risk", footer=[("Risk", "risk")]),
    dict(key="port", name="Portfolio", icon="portfolio", num="Story | Aligned Budget %", unit="budget aligned",
         chip=("text", "target 80%"), visual=("bar", (0, 1, hm("Aligned Rest"), 0.8, ("0%", "target 80%", "100%"))),
         colour=hm("Colour Portfolio"), link="portfolio",
         footer=[("Gates", "lifecycle"), ("Scenarios", "scenarios"), ("Project", "onepager")]),
    dict(key="ben", name="Benefits", icon="benefits", num="Story | Value Ratio", unit="value / cost",
         chip=("text", "target ≥ 1.0"), visual=None,
         colour=hm("Colour Benefits"), link="benefits", footer=[("Benefits", "benefits")]),
    dict(key="sr", name="Status reports", icon="exec", num="Story | Status · Not Reporting",
         unit=f"not reporting {STALE_DAYS}+ days", chip=("context", "Status"), visual=None,
         colour=hm("Colour Status"), link="status", footer=[("Changes", "status")]),
    dict(key="gov", name="Governance", icon="governance", num="PMO | Governance Score", unit="data trust score",
         chip=("text", "target 90"), visual=("bar", (0, 100, hm("Trust Rest"), 90, ("0", "target 90", "100"))),
         colour=hm("Colour Trust"), link="governance", footer=[("Governance", "governance")]),
]
_PILL_NAME = {"fin": "Financials", "sch": "Schedule", "res": "Resources", "risk": "Risk", "port": "Portfolio",
              "ben": "Benefits", "sr": "Status", "gov": "Governance"}
assert [s_["key"] for s_ in SUBJECTS_LAYOUT] == list(_PILL_NAME)
assert [u[0] for u in UNITS] == list(_PILL_NAME.values()) == list(FACTS)

# ---- card geometry (design A). Offsets are relative to the card's top-left corner and identical for all eight cards,
# so every element sits at the same y in each row of four.
# Every one-cell table is >= 28 px taller than header row (~20 px) + text: the Service renders text taller than Desktop
# and shows a scroll thumb otherwise. Cards (pill word, chip text, month captions) have no header row and no scroll.
PAD = 16                                  # left / right text edge inside a card
R_HEAD, TILE, TILE_R, TILE_IMG = 16, 32, 8, 20      # icon tile 32 x 32 (radius 8) with a 20 px icon on top
TITLE_X = PAD + TILE + 10                 # title text left edge
SP_W, SP_H, SP_R, SP_DOT = 74, 24, 12, 6  # status capsule (pill): fill, 6 px dot, coloured word
R_NUM, NUM_H, NUM_PT = 50, 118, 38        # hero number cell (one-cell table above the ghost link: hover list)
NUM_W = 160                               # number cell width (a 38 pt "100.0" plus the cell padding)
NUM_BASE = 70                             # Desktop: the number's baseline sits ~70 px below the cell top
TBL_PADL, NUM_PADL = 22, 24               # Desktop: a one-cell table's text starts ~22 px (38 pt: ~24 px) right of the cell
UNIT_PT, UNIT_GAP = 12, 8                 # unit label: 12 pt grey, UNIT_GAP right of the narrowest form of the number
UNIT_BASE = 34                            # the unit cell's baseline sits ~34 px below its top
# narrowest form of each card's number in px at 38 pt Segoe UI Semibold ("8", "8%", "0.00", "0.0"; measured)
NUM_MIN_PX = {"fin": 28, "sch": 28, "res": 71, "risk": 28, "port": 71, "ben": 96, "sr": 28, "gov": 68}
CHIP_PT, CHIP_TH, CHIP_R, CHIP_PADX = 10, 18, 9, 8   # delta / context chip: 10 pt, 18 high, radius 9
R_CHIP = R_NUM + 34                       # chip top: level with the top of the digits, above the unit line (right-aligned)
R_VIS, VIS_H = 136, 100                   # visual row: area sparkline y+136..236
R_CAP, CAP_H, CAP_PT = 238, 20, 9         # caption row under the sparkline / bar
R_BAR = R_CAP - 14                        # progress bar centre line, just above its caption
BAR_T, MARK_H = 11, 15                    # bar thickness (px), target marker height (a little taller than the bar)
R_TGT, TGT_W = R_BAR - BAR_T / 2 - 4 - CAP_H, 90     # target label row above the bar, centred on the marker
R_DIV = 270                               # hairline divider above the facts
R_FACT, FACT_H, FACT_PT = (282, 316), 26, 11        # fact label rows (textbox tops)
FACT_DY = 14                              # value cell sits FACT_DY above its label row (header row)
FACT_CELL_H = 66                          # 11 pt text + header + 28 px headroom
VAL_GAP = 10                              # gap between a fact label and the widest value its row can hold
# fact labels in px (Segoe UI 11 pt, measured): the value column takes the rest of the row, right-aligned
FACT_LABEL_PX = {"EAC vs budget": 96, "Worst project": 90, "On track": 55, "Worst slip": 66, "Over 100%": 71,
                 "Timesheets missing": 128, "Active risks": 73, "Without mitigation": 126, "Active projects": 98,
                 "Proposed": 63, "Planned benefits": 110, "EAC": 27, "Worse vs last month": 124,
                 "Avg days since": 97, "Project plans failing": 131, "Other plans failing": 122}
R_FOOT, FOOT_H, FOOT_R, FOOT_GAP = ROW_H - 44, 28, 14, 8     # action pills
CELL_X = 2                 # table cells carry ~14 px of left padding, so they start left of the 16 px text edge
ACT_H = 398                # Act-now table: header + 8 rows

# text widths in px (Segoe UI, measured): chip texts at 10 pt
CHIP_TEXT_PX = {"target 80%": 64, "target ≥ 1.0": 69, "target 90": 53}
CHIP_DYN_W = {"Financials": 76, "Schedule": 76, "Risk": 84, "Status": 100}   # dynamic chips: room for the longest text
MUTED2, RULE2 = "#8C98B3", "#26314F"   # muted text 5.2:1 on the card navy


VAL_CELL_EXTRA = 60        # a table cell wider than its fixed column, so no horizontal scrollbar appears


def fact_value_w(label):
    """Width of a fact's value column: the row (card width minus padding) minus the label and VAL_GAP."""
    return COL_W - 2 * PAD - FACT_LABEL_PX[label] - VAL_GAP


def chip_w(spec):
    kind, arg = spec["chip"]
    return CHIP_TEXT_PX[arg] + 2 * CHIP_PADX if kind == "text" else CHIP_DYN_W[arg]


CHIP_GAP, CHIP_PAD, CHAR_PX = 8, 24, 8.0     # (Executive view links) Desktop pads a button ~16 px beyond its text
# action pills: bold Segoe UI 11 pt widths in px (measured); a pill is its text + FOOT_PAD (text margins FOOT_MARGIN each side)
FOOT_TEXT_PX = {"Spend": 43, "Pareto": 45, "Schedule": 62, "Gantt": 37, "Baseline": 56, "People": 47, "Time": 33, "TS": 16,
                "Person": 47, "Risk": 27, "Gates": 37, "Scenarios": 65, "Project": 48, "Benefits": 54, "Changes": 52,
                "Governance": 82}           # Segoe UI Semibold 11 pt
FOOT_PAD, FOOT_MARGIN, FOOT_FONT = 24, 0, "Segoe UI Semibold"
CHIP_H = 30


def chip_text_w(label, size=11):
    return len(label) * CHAR_PX * size / 11


def foot_text_w(label, size=11):
    return FOOT_TEXT_PX[label] * size / 11


def chip_layout(footer):
    """-> (labels, size, widths). Each action pill is as wide as its text plus padding; pills sit left to right with a
    FOOT_GAP gap. 11 pt, or 10 pt when a card's pills do not fit at 11. Text is never cut."""
    room = COL_W - 2 * PAD
    for size in (11, 10):
        labels = [t for t, _ in footer]
        widths = [round(foot_text_w(l, size) + FOOT_PAD, 2) for l in labels]
        if sum(widths) + FOOT_GAP * (len(widths) - 1) <= room:
            break
    return labels, size, widths


# Neutral buttons (cards and Executive decisions): no orange or status colour on any button, orange is a KPI colour too.
# Transparent fill, 1 px neutral border, Semibold label centred both ways, radius 14; hover: light grey fill, darker border.
# The user's spec gives dark-grey text (#374151); on the dark #1B2540 card that is unreadable at rest, so the resting
# label uses the light neutral BTN_TEXT and turns #374151 on the light hover fill.
BTN_BORDER, BTN_BORDER_HOVER, BTN_HOVER_FILL = "#C9CED8", GREY, "#F3F4F6"
BTN_TEXT, BTN_TEXT_HOVER = "#D0D5DD", "#374151"


def neutral_button(label, target, size=11, radius=FOOT_R):
    v = nav_button(label, pages.PID[target], dict(pages.PAGES)[target], fill="#FFFFFF", hover=BTN_HOVER_FILL,
                   press=BTN_HOVER_FILL, font=BTN_TEXT, size=size, radius=radius, margin=FOOT_MARGIN, outline=BTN_BORDER)
    o = v["objects"]
    o["fill"][1]["properties"]["transparency"] = n(100)                    # rest: transparent
    o["outline"].append({"properties": {"lineColor": col_solid(BTN_BORDER_HOVER), "weight": pbir.i(1),
                                        "transparency": n(0)}, "selector": {"id": "hover"}})
    t = o["text"][1]["properties"]
    t.update({"fontFamily": s(FOOT_FONT), "bold": b(False), "horizontalAlignment": s("center"),
              "verticalAlignment": s("middle"), "leftMargin": n(FOOT_MARGIN), "rightMargin": n(FOOT_MARGIN),
              "topMargin": n(0), "bottomMargin": n(0)})
    for state in ("hover", "press"):
        o["text"].append({"properties": {"fontColor": col_solid(BTN_TEXT_HOVER)}, "selector": {"id": state}})
    return v


def link_chip(label, target, size=11):
    """Executive-view decision link: the same neutral button."""
    return neutral_button(label, target, size, radius=CHIP_H // 2)


def action_pill(label, target, size):
    """Footer action of a subject card: a neutral outline pill (all equal; no orange primary)."""
    return neutral_button(label, target, size)


def view_pill(pg, grp, k, key):
    """Orange rounded pill behind a view-switch button; lives in the view's group so it shows only for that view."""
    pg.add(1586 + k * 94, 30, 90, 32, shape(ORANGE, radius=16), key=key, parent=grp)


def fx_shape(colour_measure, radius):
    """Rounded shape whose fill is a colour measure (fx)."""
    v = shape(PANEL, radius=radius)
    v["objects"]["fill"][0]["properties"]["fillColor"] = measure_colour(colour_measure)
    return v


def card_text(measure, size, colour=INK2, colour_measure=None):
    """Card on a transparent ground (no header row, no scroll); a card centres its text."""
    return band_text(measure, size, colour=colour, colour_measure=colour_measure)


def right_cell(measure, size, col_w, colour_measure=None, colour=INK2):
    """One-cell table with a fixed column width and right-aligned text (fact values)."""
    v = _cell(measure, size, colour_measure, colour)
    v["objects"]["columnWidth"] = [{"properties": {"value": n(col_w)}, "selector": {"metadata": pbir.qref(M(measure))}}]
    v["objects"]["columnFormatting"] = [{"properties": {"alignment": s("Right")}, "selector": {"metadata": pbir.qref(M(measure))}}]
    return v


AREA_TRANSPARENCY = 82     # soft area under the line


def area_spark(measure, colour):
    """Native area chart: status-colour line, soft fill (AREA_TRANSPARENCY %), no axes / gridlines / legend / markers.
    The area fills to zero, so a series that crosses zero (EAC variance) shades above and below the zero line.
    The shading transparency is dataPoint.transparency in Desktop (lineStyles has only areaShow / areaColor)."""
    fill = fx_fill(M(measure), colour)
    fill["properties"]["transparency"] = n(AREA_TRANSPARENCY)
    v = chart("areaChart", {"Category": [P(C("DimDate", "MonthStart"), "Month")], "Y": [P(M(measure), " ")]}, "",
              {"dataPoint": [fill], "legend": legend(show=False),
               "categoryAxis": [{"properties": {"show": b(False), "gridlineShow": b(False)}}],
               "valueAxis": [{"properties": {"show": b(False), "gridlineShow": b(False)}}],
               "labels": [{"properties": {"show": b(False)}}],
               "lineStyles": [{"properties": {"strokeWidth": n(2), "showMarker": b(False), "areaShow": b(True)}}],
               "markers": [{"properties": {"show": b(False)}}]},
              sort=[(C("DimDate", "MonthStart"), "Ascending")])
    vco = v["visualContainerObjects"]
    vco["title"] = [{"properties": {"show": b(False)}}]
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    vco["padding"] = [{"properties": {"top": n(0), "bottom": n(0), "left": n(0), "right": n(0)}}]
    return v


def caption(text, align):
    return textbox([[(text, st("Segoe UI", CAP_PT, MUTED2))]], align=align)


def subject_card(pg, x, y, spec):
    key, name, num, colour = spec["key"], spec["name"], spec["num"], spec["colour"]
    sub = _PILL_NAME[key]
    p = f"card_{key}"
    W = COL_W
    panel(pg, x, y, W, ROW_H, f"{p}_bg")
    # 1 header: icon tile (pill fill) + grey icon, title, status capsule (fill, dot, word)
    pg.add(x + PAD, y + R_HEAD, TILE, TILE, fx_shape(hm(f"Pill Fill {sub}"), TILE_R), key=f"{p}_tile")
    icon = image(f"rail-{spec['icon']}-grey.png", f"{name} icon")
    icon["objects"]["image"][0]["properties"]["sourceFile"]["image"]["scaling"] = s("Fit")
    off = (TILE - TILE_IMG) / 2
    pg.add(x + PAD + off, y + R_HEAD + off, TILE_IMG, TILE_IMG, icon, key=f"{p}_icon")
    pg.add(x + TITLE_X, y + R_HEAD, 170, TILE, textbox([[(name, st("Segoe UI Semibold", 14, INK2, True))]]),
           key=f"{p}_title")
    sx, sy = x + W - PAD - SP_W, y + R_HEAD + (TILE - SP_H) / 2
    pg.add(sx, sy, SP_W, SP_H, fx_shape(hm(f"Pill Fill {sub}"), SP_R), key=f"{p}_pillbg")
    pg.add(sx + 12, sy + (SP_H - SP_DOT) / 2, SP_DOT, SP_DOT, fx_shape(colour, 50), key=f"{p}_dot")
    pg.add(sx + 20, sy, SP_W - 26, SP_H, card_text(hm(f"Pill {sub}"), 10, colour_measure=colour), key=f"{p}_pill")
    # 2 hero line: unit (padded measure, right of the number), chip right-aligned at the top of the digits
    unit_x = x + PAD + NUM_MIN_PX[key] + UNIT_GAP - TBL_PADL
    pg.add(round(unit_x, 2), y + R_NUM + NUM_BASE - UNIT_BASE, W - (unit_x - x) - PAD, 66,
           text_cell(hm(f"Unit {sub}"), size=UNIT_PT, colour=LABEL), key=f"{p}_unit")
    cw = chip_w(spec)
    cx = x + W - PAD - cw
    kind, arg = spec["chip"]
    if kind == "measure":
        pg.add(cx, y + R_CHIP, cw, CHIP_TH, fx_shape(hm(f"Delta Fill {arg}"), CHIP_R), key=f"{p}_chipbg")
        txt = card_text(hm(f"Delta {arg}"), CHIP_PT, colour_measure=hm(f"Delta Colour {arg}"))
    elif kind == "context":
        pg.add(cx, y + R_CHIP, cw, CHIP_TH, shape(RULE2, radius=CHIP_R), key=f"{p}_chipbg")
        txt = card_text(hm(f"Delta {arg}"), CHIP_PT, colour=LABEL)
    else:
        pg.add(cx, y + R_CHIP, cw, CHIP_TH, shape(RULE2, radius=CHIP_R), key=f"{p}_chipbg")
        txt = textbox([[(arg, st("Segoe UI", CHIP_PT, LABEL))]], align="center")
    pg.add(cx, y + R_CHIP - 3, cw, CHIP_TH + 6, txt, key=f"{p}_chip")
    # 3 visual row: area sparkline + month captions, progress bar + marker + captions, or an explicit empty slot
    vis = spec["visual"]
    tw = W - 2 * PAD
    if vis and vis[0] == "area":
        _k, measure, cap = vis
        # captions first: the chart (transparent) is drawn on top of them
        pg.add(x + PAD - 6, y + R_CAP, 44, CAP_H, card_text(hm(f"Spark From {sub}"), CAP_PT, colour=MUTED2), key=f"{p}_cap0")
        pg.add(x + PAD + 40, y + R_CAP, tw - 80, CAP_H, caption(cap, "center"), key=f"{p}_cap1")
        pg.add(x + W - PAD - 38, y + R_CAP, 44, CAP_H, card_text(hm(f"Spark To {sub}"), CAP_PT, colour=MUTED2), key=f"{p}_cap2")
        pg.add(x + PAD - 4, y + R_VIS, tw + 8, VIS_H, area_spark(measure, colour), key=f"{p}_spark")
    elif vis and vis[0] == "bar":
        lo, hi, rest, target, labels = vis[1]
        value = vis[2] if len(vis) > 2 else num
        progress(pg, x + PAD, y + R_BAR - BAR_T / 2, tw, BAR_T, value, rest, lo, hi, colour, f"{p}_bar")
        pg.add(x + PAD - 4, y + R_CAP, 60, CAP_H, caption(labels[0], "left"), key=f"{p}_cap0")
        if target is None:
            pg.add(x + PAD + 60, y + R_CAP, tw - 120, CAP_H, caption(labels[1], "center"), key=f"{p}_cap1")
        else:
            mx = x + PAD + tw * (target - lo) / (hi - lo)
            pg.add(round(mx - 1, 2), y + R_BAR - MARK_H / 2, 2, MARK_H, shape(C_TEAL), key=f"{p}_mark")
            # the target label sits ABOVE the bar, centred on the marker; 0 / 100 stay under the bar ends
            pg.add(round(mx - TGT_W / 2, 2), y + R_TGT, TGT_W, CAP_H, caption(labels[1], "center"), key=f"{p}_cap1")
        pg.add(x + W - PAD - 56, y + R_CAP, 60, CAP_H, caption(labels[2], "right"), key=f"{p}_cap2")
    # 4 facts: hairline, then two label / value rows. Row 2's cell is added first: row 1's cell (on top) keeps its text
    # clear of row 2's header row.
    pg.add(x + PAD, y + R_DIV, tw, 1, shape(RULE2), key=f"{p}_rule")
    for j in (2, 1):
        lbl = FACTS[sub][j - 1][0]
        ry = y + R_FACT[j - 1]
        pg.add(x + PAD, ry, FACT_LABEL_PX[lbl] + 24, FACT_H, textbox([[(lbl, st("Segoe UI", FACT_PT, LABEL))]]), key=f"{p}_f{j}l")
        vw = fact_value_w(lbl)
        vx = x + W - PAD - vw - TBL_PADL
        pg.add(round(vx, 2), ry - FACT_DY, vw + VAL_CELL_EXTRA, FACT_CELL_H,
               right_cell(hm(f"Fact {sub} {j} Value"), FACT_PT, vw, colour_measure=FACT_COLOUR[(sub, j)]),
               key=f"{p}_f{j}v")
    # whole-card link: everything above the footer; the number and the footer pills sit on top of it
    pg.add(x, y, W, R_FOOT - 4, ghost_link(spec["link"], name), key=f"{p}_go")
    # the number sits ABOVE the ghost link so hovering it shows its list (a button cannot show a report-page tooltip);
    # it is only NUM_W wide, so the rest of the hero line still clicks through to the chapter
    pg.add(x + PAD - NUM_PADL, y + R_NUM, NUM_W, NUM_H,
           with_tip(value_cell(num, colour_measure=colour, size=NUM_PT), f"tip_home_{key}"), key=f"{p}_num")
    # 5 action pills
    labels, size, widths = chip_layout(spec["footer"])
    fx = x + PAD
    for j, ((txt_, target), label, w) in enumerate(zip(spec["footer"], labels, widths)):
        pg.add(round(fx, 2), y + R_FOOT, w, FOOT_H, action_pill(label, target, size), key=f"{p}_ft{j}")
        fx += w + FOOT_GAP


def build_cards(pg):
    for k, spec in enumerate(SUBJECTS_LAYOUT):
        x = GRID_X0 + (k % 4) * (COL_W + GAP)
        y = GRID_Y[k // 4]
        subject_card(pg, x, y, spec)


def _dark_table_obj(fields, widths, why=None):
    obj = pbir.table_style(11, header_bg=PANEL)
    obj["values"] = [{"properties": {"fontSize": n(11), "fontColorPrimary": col_solid(INK2),
                                     "backColorPrimary": col_solid(PANEL), "fontColorSecondary": col_solid(INK2),
                                     "backColorSecondary": col_solid(PANEL), "wordWrap": b(True)}}]
    if why:
        obj["values"].append(pbir.cf_font(M(why), hm("Act Colour")))
    obj["grid"] = [{"properties": {"gridHorizontal": b(True), "gridHorizontalColor": col_solid("#26314F"),
                                   "rowPadding": n(6)}}]
    obj["total"] = [{"properties": {"totals": b(False)}}]
    # fixed column widths: auto-sizing pushes the last column off to a horizontal scrollbar
    obj["columnWidth"] = [{"properties": {"value": n(w)}, "selector": {"metadata": pbir.qref(f)}}
                          for f, w in zip(fields, widths)]
    return obj


def act_table(why, impact=True):
    """Act-now table. why = the Why measure: Act Reason (all projects with a reason) or a bucket's Tip measure
    (blank for every other project, so only that bucket's rows show)."""
    if impact:
        fields, widths = [pages.DP("Name"), M(why), M(hm("Act Score"))], (146, 138, 66)
        roles = [P(pages.DP("Name"), "Project"), P(M(why), "Why"), P(M(hm("Act Score")), "Impact")]
        sort = [(M(hm("Act Score")), "Descending")]
    else:
        fields, widths = [pages.DP("Name"), M(why)], (160, 200)
        roles = [P(pages.DP("Name"), "Project"), P(M(why), "Why")]
        sort = [(pages.DP("Name"), "Ascending")]
    tbl = chart("tableEx", {"Values": roles}, "", _dark_table_obj(fields, widths, why), sort=sort)
    for o in ("title", "background", "border"):
        tbl["visualContainerObjects"][o] = [{"properties": {"show": b(False)}}]
    return tbl


ACT_GRP = (RIGHT_X, RIGHT_Y, RIGHT_W, 44 + ACT_H)   # one Act-now version: title row + table
ACT_TX = 24                # title inset: clear of the panel's rounded corner (Desktop draws radius 14 wide at this size)


def build_act(pg, g_all, g_bucket, bm_all):
    """Seven versions of the Act-now list, each its own top-level group: all reasons, and one per chip bucket."""
    x, y = RIGHT_X, RIGHT_Y
    pg.add(x + ACT_TX, y + 12, 392, 32, textbox([[("Act now", st("Segoe UI Semibold", 15, INK2, True)),
                                              ("   ranked by impact", st("Segoe UI", 10, LABEL))]]),
           key="act_title", parent=g_all)
    pg.add(x + 8, y + 44, RIGHT_W - 16, ACT_H, act_table(hm("Act Reason")), key="act_tbl", parent=g_all,
           filters=[pages.REAL_PROJECTS])
    for k, (_s, lbl, nm, _d) in enumerate(CHIPS):
        slug, grp = CHIP_SLUG[k], g_bucket[CHIP_SLUG[k]]
        pg.add(x + ACT_TX, y + 12, 292, 32, textbox([[(f"Act now — {lbl}", st("Segoe UI Semibold", 15, INK2, True))]]),
               key=f"act_title_{slug}", parent=grp)
        pg.add(x + RIGHT_W - 16 - 96, y + 14, 96, 26,
               pbir.bookmark_button("Show all ›", bm_all, "Show every Act-now project", fill=PANEL, hover="#26314F",
                                    press=ORANGE, font="#F29A6B", size=10, align="right", margin=4),
               key=f"act_all_{slug}", parent=grp)
        pg.add(x + 8, y + 44, RIGHT_W - 16, ACT_H, act_table(hm(f"Tip {nm}"), impact=False), key=f"act_tbl_{slug}",
               parent=grp, filters=[pages.REAL_PROJECTS])


def build_right_pmo(pg, grp):
    """Everything in the PMO right column except the Act-now list (that lives in the act groups)."""
    view_pill(pg, grp, 0, "view_pill_pmo")
    x, y = RIGHT_X, RIGHT_Y
    panel(pg, x, y, RIGHT_W, RIGHT_H, "act_bg", parent=grp)
    pg.add(x + 16, y + 44 + ACT_H + 8, 200, 32, pbir.drill_button("Open One-Pager ›", pages.PID["project"],
           "Select a project row first", fill=ORANGE, size=10), key="act_drill", parent=grp)
    pg.add(x + 224, y + 44 + ACT_H + 12, RIGHT_W - 240, 26, textbox([[("or right-click › Drill through", st("Segoe UI", 10, LABEL))]]),
           key="act_hint", parent=grp)
    pg.add(x + 16, y + 44 + ACT_H + 60, 300, 32, textbox([[("Next 30 days", st("Segoe UI Semibold", 15, INK2, True))]]),
           key="next_title", parent=grp)
    due = M(hm("Due"))
    mobj = _dark_table_obj((due, pages.DP("Name"), pages.DT("Name")), (88, 130, 156))
    # rows outside the next 30 days vanish: the only measure in the row (Due) is blank for them
    miles = chart("tableEx", {"Values": [P(due, "Due"), P(pages.DP("Name"), "Project"), P(pages.DT("Name"), "Milestone")]},
                  "", mobj, sort=[(due, "Ascending")])
    for o in ("title", "background", "border"):
        miles["visualContainerObjects"][o] = [{"properties": {"show": b(False)}}]
    pg.add(x + 8, y + 44 + ACT_H + 92, RIGHT_W - 16, LOGO[1] - 8 - (y + 44 + ACT_H + 92), miles, key="next_tbl", parent=grp,
           filters=[pbir.f_in("DimTask", "Milestone", [True]), pbir.f_cmp("DimTask", "PercentDone", 3, 100),
                    pages.PROJECT_TASKS])


def build_right_exec(pg, grp):
    view_pill(pg, grp, 1, "view_pill_exec")
    decisions = [("Money decision", "Story | Exec Action Money", hm("Colour EAC"), "finance"),
                 ("People decision", "Story | Exec Action People", hm("Colour Util"), "resources"),
                 ("Risk decision", "Story | Exec Action Risk", hm("Colour Risk"), "risk")]
    h = (RIGHT_H - 2 * GAP) / 3
    for k, (label, m, colour, target) in enumerate(decisions):
        y = round(RIGHT_Y + k * (h + GAP), 2)
        panel(pg, RIGHT_X, y, RIGHT_W, round(h, 2), f"dec_bg{k}", parent=grp)
        pg.add(RIGHT_X + 16, y + 12, 300, 30, textbox([[(label, st("Segoe UI Semibold", 13, INK2, True))]]),
               key=f"dec_lbl{k}", parent=grp)
        pg.add(RIGHT_X + 16, y + 44, RIGHT_W - 32, round(h - 104, 2), text_cell(m, size=13), key=f"dec{k}", parent=grp)
        chip = dict(pages.PAGES)[target].split("·", 1)[-1].strip() + " ›"
        pg.add(RIGHT_X + 16, round(y + h - 44, 2), round(chip_text_w(chip) + CHIP_PAD, 2), CHIP_H,
               link_chip(chip, target), key=f"dec_go{k}", parent=grp)


LOGO = (1646, 924, 110, 48)    # bottom-right corner of the right-column panel (the user's choice)


def build_logo(pg):
    """OnePlan logo, added after the groups so it sits above the right column and is not inside a group."""
    logo = image("OnePlan_logo_-_dark_background9901469509814106.png", "OnePlan logo")
    logo["objects"]["image"][0]["properties"]["sourceFile"]["image"]["scaling"] = s("Fit")  # 211x92 source, 110x48 box
    pg.add(*LOGO, logo, key="oneplan_logo")


def build_switch(pg, bm_pmo, bm_exec):
    """Buttons only (the backing panel is added before the groups so the pills show through)."""
    for k, (txt, bm) in enumerate([("PMO", bm_pmo), ("Executive", bm_exec)]):
        v = pbir.bookmark_button(txt, bm, f"Show the {txt} view", fill=PANEL, hover=ORANGE, press=ORANGE, font=INK2,
                                 size=10, radius=16)
        # transparent by default so the active view's pill shows through
        v["objects"]["fill"][1]["properties"]["transparency"] = n(100)
        pg.add(1586 + k * 94, 30, 90, 32, v, key=f"switch{k}")


# ====================================================================== hover lists: report-page tooltips
TIP_W, TIP_H = 360, 260
TIP_H_LONG = 430           # long lists (capped at TIP_ROWS rows): 12 rows of 9 pt (~21 px each) + header + footer fit
TIP_COLS = 290             # total column width of a tooltip table (see tip_page)


def tip_page(key, title, subtitle, columns, sort, filters=(), long_list=None):
    """Hidden Tooltip page: title, one-line subtitle, orange rule and ONE light table.
    columns: [(field, display name, width)]. The table's measures are blank unless the row qualifies.
    long_list = (subtitle measure, footer measure) for a capped list: a taller page (TIP_H_LONG), the subtitle becomes a
    measure ("16 projects · top 12 ...") and a footer card says "+N more · open the X page" (blank when nothing is cut)."""
    h = TIP_H_LONG if long_list else TIP_H
    pg = Page(pages.PID[key], dict(pages.HIDDEN_PAGES)[key], TIP_W, h, background_colour="#FFFFFF",
              display_option="ActualSize")
    pg.page["type"] = "Tooltip"
    pg.page["pageBinding"] = {"name": pbir.uid("bind", key), "type": "Tooltip", "parameters": []}
    pg.page["visibility"] = "HiddenInViewMode"
    pg.add(10, 2, 340, 28, textbox([[(title, st("Segoe UI Semibold", 12, pbir.NAVY, True))]]), key="tip_title")
    if long_list:
        # a one-cell table (left aligned, unlike a card): its 1 pt header row eats ~20 px, so the cell is taller than its text
        pg.add(CELL_X + 4, 22, 340, 52, text_cell(long_list[0], size=9, colour=pbir.MUTED, bg="#FFFFFF"), key="tip_sub")
    else:
        pg.add(10, 30, 340, 22, textbox([[(subtitle, st("Segoe UI", 9, pbir.MUTED))]]), key="tip_sub")
    top = 76 if long_list else 60                               # table top; the orange rule sits 6 px above it
    pg.add(14, top - 6, 332, 2, shape(ORANGE), key="tip_rule")
    # 9 pt, one line per row and tight padding: a tooltip cannot scroll, so fit as many rows as possible (~7 in the
    # 260 px pages, ~14 in the 400 px ones). Desktop draws columns wider than their set width (padding), so the widths
    # are capped at TIP_COLS in total or the last column spills into a horizontal scrollbar (seen at 10 pt / 325 px).
    obj = pbir.table_style(9)
    obj["columnHeaders"][0]["properties"]["wordWrap"] = b(False)
    obj["values"][0]["properties"]["wordWrap"] = b(False)
    obj["grid"][0]["properties"]["rowPadding"] = n(2)
    obj["total"] = [{"properties": {"totals": b(False)}}]
    k = min(1.0, TIP_COLS / sum(w for _f, _d, w in columns))
    obj["columnWidth"] = [{"properties": {"value": n(round(w * k))}, "selector": {"metadata": pbir.qref(f)}}
                          for f, _d, w in columns]
    tbl = chart("tableEx", {"Values": [P(f, d) for f, d, _w in columns]}, "", obj, sort=sort)
    for o in ("title", "background", "border"):
        tbl["visualContainerObjects"][o] = [{"properties": {"show": b(False)}}]
    foot = 34 if long_list else 0
    pg.add(6, top, TIP_W - 12, h - top - 6 - foot, tbl, key="tip_tbl", filters=list(filters))
    if long_list:
        more = band_text(long_list[1], 9, colour=pbir.MUTED)       # centred, transparent card; blank = nothing shown
        pg.add(10, h - 32, TIP_W - 20, 26, more, key="tip_more")
    return pg


def _desc(m):
    return [(M(m), "Descending")]


DPN = pages.DP("Name")
def card_tips():
    """card key -> (title, subtitle, columns, sort, extra filters, long-list measures or None); each list uses the same
    rule as the card's number. The titles say what the list explains ("Behind <the number>: ...").
    A function, not a constant: M() must run after build.py has registered the extension measures."""
    return {
        "fin": ("Behind projects over EAC: EAC vs budget", "EAC above the budget at completion",
                [(DPN, "Project", 210), (M(hm("Tip Financials")), "EAC vs budget", 110)], _desc(hm("Tip Financials")), (), None),
        "sch": ("Behind slipping projects: finish slip", "Finish later than the baseline, in days",
                [(DPN, "Project", 210), (M(hm("Tip Schedule")), "Finish slip (d)", 110)], _desc(hm("Tip Schedule")), (), None),
        "res": ("Behind utilisation: people over 100%", "Peak monthly utilisation in view (active people)",
                [(pages.DR("Name"), "Person", 210), (M(hm("Tip Resources")), "Peak util.", 110)], _desc(hm("Tip Resources")), (),
                None),
        "risk": ("Behind critical risks: scoring 9+", f"Active project risks scoring {HIGH_HEAT}+ on the 4×4 grid",
                 [(pages.DT("Name"), "Risk", 150), (DPN, "Project", 110), (M(hm("Tip Risk")), "Exposure", 70)],
                 _desc(hm("Tip Risk")), (pages.PROJECT_TASKS, pbir.f_in("DimTask", "WorkType", ["Risks"]),
                                         pbir.f_in("DimTask", "State", ["Active"])), None),
        "port": ("Behind budget aligned: alignment by project", "Aligned = Strong / Extreme; plan-field budget",
                 [(DPN, "Project", 150), (M(hm("Tip Portfolio")), "Alignment", 100),
                  (M(hm("Tip Portfolio Budget")), "Budget", 80)], _desc(hm("Tip Portfolio Budget")), (),
                 (hm("Tip Portfolio Sub"), hm("Tip Portfolio More"))),
        "ben": ("Behind value / cost: ratio by project", "Planned benefits + revenue at completion ÷ EAC",
                [(DPN, "Project", 220), (M(hm("Tip Benefits")), "Value / cost", 100)],
                [(M(hm("Tip Benefits")), "Ascending")], (), (hm("Tip Benefits Sub"), hm("Tip Benefits More"))),
        "sr": (f"Behind not reporting: no report in {STALE_DAYS}+ days", "Days since the last submitted report",
               [(DPN, "Project", 130), (M(hm("Tip Status")), "Reporting", 115), (M(hm("Tip Status Days")), "Days", 45)],
               [(M(hm("Tip Status")), "Ascending"), (M(hm("Tip Status Days")), "Descending")], (), (hm("Tip Status Sub"), hm("Tip Status More"))),
        "gov": ("Behind data trust: project plans failing rules", "Plan Insights rules failing per plan",
                [(DPN, "Project", 220), (M(hm("Tip Governance")), "Failing rules", 100)], _desc(hm("Tip Governance")), (),
                (hm("Tip Governance Sub"), hm("Tip Governance More"))),
    }
assert [k for k, _ in pages.HOME_TIP_CARDS] == [s_["key"] for s_ in SUBJECTS_LAYOUT]
LONG_TIPS = ("port", "ben", "sr", "gov")


def build_tips():
    out = [tip_page("tip_home_act", "Act now · every project needing a decision", "Worst reason first, ranked by impact",
                    [(DPN, "Project", 120), (M(hm("Act Reason")), "Why", 150), (M(hm("Act Score")), "Impact", 55)],
                    _desc(hm("Act Score")), (pages.REAL_PROJECTS,))]
    for k, (score, lbl, nm, _d) in enumerate(CHIPS):
        out.append(tip_page(f"tip_home_{CHIP_SLUG[k]}", f"Act now · {lbl}", f"Projects whose worst reason is {lbl}",
                            [(DPN, "Project", 140), (M(hm(f"Tip {nm}")), "Why", 185)], [(DPN, "Ascending")],
                            (pages.REAL_PROJECTS,)))
    tips = card_tips()
    assert list(tips) == [k for k, _ in pages.HOME_TIP_CARDS]
    for key, (title, sub, cols, sort, flt, long_list) in tips.items():
        assert (long_list is not None) == (key in LONG_TIPS), key
        real = (pages.REAL_PROJECTS,) if any(f is DPN for f, _d, _w in cols) else ()
        out.append(tip_page(f"tip_home_{key}", title, sub, cols, sort, real + tuple(flt), long_list))
    return out


def build():
    pg = Page(pages.PID["home"], dict(pages.PAGES)["home"], pages.W, 1000, background_colour=CANVAS,
              display_option="FitToPage")
    build_rail(pg)
    build_band(pg)
    build_cards(pg)
    pg.add(1580, 24, 196, 44, shape("#26314F", radius=14), key="switch_bg")
    # Groups hold only the right column. grp_pmo_rest: the PMO panel, pill, One-Pager button, Next 30 days.
    # grp_act_all / grp_act_<bucket>: the seven Act-now versions on top of that panel. grp_exec: the Executive view.
    # The panel group (and its children) come first so the Act-now tables sit above the panel in z-order.
    g_rest = pg.add_group(RIGHT_X, 24, 1784 - RIGHT_X, 988 - 24, "PMO view", key="grp_pmo_rest")
    build_right_pmo(pg, g_rest)
    g_all = pg.add_group(*ACT_GRP, "Act now · all", key="grp_act_all")
    g_bucket = {CHIP_SLUG[k]: pg.add_group(*ACT_GRP, f"Act now · {CHIPS[k][1]}", key=f"grp_act_{CHIP_SLUG[k]}",
                                           hidden=True) for k in range(len(CHIPS))}
    g_exec = pg.add_group(RIGHT_X, 24, 1784 - RIGHT_X, 988 - 24, "Executive view", key="grp_exec", hidden=True)
    every = [g_rest, g_all, *g_bucket.values(), g_exec]

    def shown(*visible):
        return {g: g not in visible for g in every}
    bm_pmo = pbir.bookmark("Home · PMO view", "home_pmo", pg.id, shown(g_rest, g_all))
    bm_exec = pbir.bookmark("Home · Executive view", "home_exec", pg.id, shown(g_exec))
    bm_bucket = {slug: pbir.bookmark(f"Home · Act now — {CHIPS[k][1]}", f"home_act_{slug}", pg.id, shown(g_rest, g))
                 for k, (slug, g) in enumerate(g_bucket.items())}
    build_act(pg, g_all, g_bucket, bm_pmo)
    build_right_exec(pg, g_exec)
    build_switch(pg, bm_pmo, bm_exec)
    build_band_links(pg, bm_pmo, bm_bucket)
    build_logo(pg)
    return [pg] + build_tips()
