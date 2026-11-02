"""5c · What Changed — month-on-month change briefing (§ month on month) plus each project against its own previous
status report, and who is not reporting?

Data: FactStatusReport (one row per OnePlan status report; ReportEndKey -> DimDate
is the active date relationship, ProjectKey -> DimProject).

"Previous report" logic
-----------------------
The model's `Status Report | … Previous Total …` measures shift by one DAY
(DATEADD -1 DAY), so they never find the previous report. Everything here works
per project instead:

    _cur  = latest Report_ReportEnd of the project inside the current filter
            context (so the report-period slicer / heat-strip column picks it)
    _prev = latest Report_ReportEnd of the same project strictly before _cur,
            with DimDate filters removed (the previous report may sit in an
            earlier month than the one selected)

Values are read at exactly that report end (REMOVEFILTERS(DimDate) +
Report_ReportEnd = date). Health texts "(1) On Track" … are ranked on their
leading digit (lower = better); two reports with the same end date resolve to
the worse one. Portfolio-level numbers iterate the non-blank VALUES(DimProject[ProjectKey]) so
each project is compared with its own previous report and the results add up; the blank member
(status reports of non-project plans) is never iterated, and every table on the page carries the
DimProject[Id]-not-blank visual filter (pages.filter_real_projects).
"""
import pages
import pbir
from pbir import AMBER_TEXT, GREY_TEXT
from pbir import C, M, P, b, chart, cf_back, cf_font, table_style
from pbir import NAVY, TEAL, AMBER, RED, GREY
from story_measures import add, money, T, D, I, MEASURES

PFX = "Story | Status · "
FOLDER = "Story\\Status"
DT_ = "DateTime"

END = "FactStatusReport[Report_ReportEnd]"
PK = "DimProject[ProjectKey]"
# Iterate real projects only: VALUES ( DimProject[ProjectKey] ) also returns the blank member, where status
# reports of non-project plans (NULL ProjectKey) land; it would count as one extra "project".
PKS = f"FILTER ( VALUES ( {PK} ), NOT ISBLANK ( {PK} ) )"
STALE_DAYS = 30
DIMS = [("Overall", "OverallHealth"), ("Schedule", "ScheduleHealth"), ("Financial", "FinancialHealth"),
        ("Effort", "EffortHealth"), ("Issue", "IssueHealth")]
DRIFT = [("Budget", "Budget"), ("Forecast", "Forecast"), ("Active Risks", "ActiveRisks")]


def m(name):
    return PFX + name


def ref(name):
    return f"[{PFX}{name}]"


# ------------------------------------------------------------------ DAX building blocks
CUR = f"CALCULATE ( MAX ( {END} ) )"  # latest report end of the project in context


def prev_end(cur="_cur"):
    """Latest report end of the project strictly before `cur` (date filters ignored)."""
    return f"CALCULATE ( MAX ( {END} ), REMOVEFILTERS ( DimDate ), {END} < {cur}, {END} > DATE ( 1900, 1, 1 ) )"


def at(expr, d):
    """Evaluate expr on the project's report(s) that end on date d."""
    return f"CALCULATE ( {expr}, REMOVEFILTERS ( DimDate ), {END} = {d} )"


def rank(col):
    return f'MAXX ( FactStatusReport, SWITCH ( LEFT ( FactStatusReport[{col}], 3 ), "(1)", 1, "(2)", 2, "(3)", 3, "(4)", 4, "(5)", 5 ) )'


def label(r):
    return f'SWITCH ( {r}, 1, "On Track", 2, "At Risk", 3, "Off Track", 4, "Level 4", 5, "Level 5" )'


def clean(x):
    """Strip the common OnePlan rich-text tags from a narrative field."""
    out = x
    for tag, rep in [("<p>", ""), ("</p>", " "), ("<br>", " "), ("<br/>", " "), ("<br />", " "),
                     ("<strong>", ""), ("</strong>", ""), ("<b>", ""), ("</b>", ""), ("<em>", ""), ("</em>", ""),
                     ("<ul>", ""), ("</ul>", ""), ("<ol>", ""), ("</ol>", ""), ("<li>", "• "), ("</li>", " "),
                     ("<div>", ""), ("</div>", " "), ("&nbsp;", " "), ("&amp;", "&")]:
        out = f'SUBSTITUTE ( {out}, "{tag}", "{rep}" )'
    return f"TRIM ( {out} )"


ONE = f"( HASONEVALUE ( {PK} ) && NOT ISBLANK ( SELECTEDVALUE ( {PK} ) ) )"

# ------------------------------------------------------------------ report dates
add(m("Latest Report End"), DT_, f"IF ( {ONE}, MAX ( {END} ) )", "dd mmm yyyy", FOLDER,
    "End date of the project's latest status report in the selected report period.")
add(m("Previous Report End"), DT_, f"""
IF ( {ONE},
    VAR _cur = MAX ( {END} )
    RETURN {prev_end()}
)""", "dd mmm yyyy", FOLDER, "End date of the project's status report before the latest one (any earlier period).")
add(m("Projects Reporting"), I, f"""
COUNTROWS ( FILTER ( {PKS}, NOT ISBLANK ( {CUR} ) ) ) + 0""", "#,##0", FOLDER,
    "Projects with at least one status report in the selected report period.")

# ------------------------------------------------------------------ health movement per dimension
for dim, col in DIMS:
    add(m(f"{dim} Rank"), I, f"""
MAXX (
    {PKS},
    VAR _cur = {CUR}
    RETURN IF ( NOT ISBLANK ( _cur ), {at(rank(col), "_cur")} )
)""", "0", FOLDER + "\\Movement",
        f"{dim} health of the latest report (1 = On Track, 2 = At Risk, 3 = Off Track). Several projects: the worst.")
    add(m(f"{dim} Prev Rank"), I, f"""
MAXX (
    {PKS},
    VAR _cur = {CUR}
    VAR _prev = {prev_end()}
    RETURN IF ( NOT ISBLANK ( _prev ), {at(rank(col), "_prev")} )
)""", "0", FOLDER + "\\Movement", f"{dim} health of the report before the latest one.")
    add(m(f"{dim} Move"), I, f"""
IF ( {ONE},
    VAR _c = {ref(dim + " Rank")}
    VAR _p = {ref(dim + " Prev Rank")}
    RETURN IF ( NOT ISBLANK ( _c ) && NOT ISBLANK ( _p ), _c - _p )
)""", "+0;-0;0", FOLDER + "\\Movement",
        f"Latest minus previous {dim.lower()} health rank for one project: positive = worse, negative = better.")
    for word, cond in [("Improved", "_m < 0"), ("Unchanged", "_m = 0"), ("Worsened", "_m > 0")]:
        add(m(f"{dim} {word}"), I, f"""
SUMX ( {PKS}, VAR _m = {ref(dim + " Move")} RETURN IF ( NOT ISBLANK ( _m ) && {cond}, 1 ) ) + 0""",
            "#,##0", FOLDER + "\\Movement",
            f"Projects whose {dim.lower()} health is {word.lower()} versus their previous status report.")
    add(m(f"{dim} Arrow"), T, f"""
IF ( {ONE} && NOT ISBLANK ( {ref(dim + " Rank")} ),
    VAR _m = {ref(dim + " Move")}
    RETURN IF ( ISBLANK ( _m ), "• first report", IF ( _m < 0, "▲ better", IF ( _m > 0, "▼ worse", "= same" ) ) )
)""", folder=FOLDER + "\\Movement")
    add(m(f"{dim} Arrow Colour"), T, f"""
VAR _m = {ref(dim + " Move")}
RETURN IF ( ISBLANK ( _m ) || _m = 0, "{GREY_TEXT}", IF ( _m < 0, "{TEAL}", "{RED}" ) )""", folder="Story\\Colours")

add(m("Overall Now"), T, f"IF ( {ONE}, {label(ref('Overall Rank'))} )", folder=FOLDER + "\\Movement")
add(m("Overall Change"), T, f"""
IF ( {ONE},
    VAR _c = {ref("Overall Rank")}
    VAR _p = {ref("Overall Prev Rank")}
    RETURN IF ( NOT ISBLANK ( _c ), IF ( ISBLANK ( _p ), "– → ", {label("_p")} & " → " ) & {label("_c")} )
)""", folder=FOLDER + "\\Movement", desc="Overall health of the previous report → latest report.")
add(m("Overall Now Colour"), T, f"""
SWITCH ( {ref("Overall Rank")}, 1, "{TEAL}", 2, "#9A6B00", 3, "{RED}", "#666666" )""", folder="Story\\Colours")

# heat strip: one cell = project × report month, coloured by the month's latest overall health
add(m("Heat Cell"), T, f"{label(ref('Overall Rank'))}", folder=FOLDER,
    desc="Overall health of the latest status report in the cell (project × report period).")
add(m("Heat Colour"), T, f"""
SWITCH ( {ref("Overall Rank")}, 1, "{TEAL}", 2, "{AMBER}", 3, "{RED}", 4, "#8E1B12", 5, "#8E1B12", "#FFFFFF" )""",
    folder="Story\\Colours")
add(m("Heat Font"), T, f"""
IF ( {ref("Overall Rank")} = 2, "{NAVY}", "#FFFFFF" )""", folder="Story\\Colours")

# ------------------------------------------------------------------ drift between reports
for nm, col in DRIFT:
    add(m(f"{nm} Latest"), D, f"""
SUMX (
    {PKS},
    VAR _cur = {CUR}
    RETURN IF ( NOT ISBLANK ( _cur ), {at(f"MAX ( FactStatusReport[{col}] )", "_cur")} )
)""", "#,##0", FOLDER + "\\Drift", f"{col} on each project's latest status report, summed.")
    add(m(f"{nm} Previous"), D, f"""
SUMX (
    {PKS},
    VAR _cur = {CUR}
    VAR _prev = {prev_end()}
    RETURN IF ( NOT ISBLANK ( _prev ), {at(f"MAX ( FactStatusReport[{col}] )", "_prev")} )
)""", "#,##0", FOLDER + "\\Drift", f"{col} on each project's previous status report, summed.")
    add(m(f"{nm} Drift"), D, f"""
SUMX (
    {PKS},
    VAR _cur = {CUR}
    VAR _prev = {prev_end()}
    RETURN
        IF ( NOT ISBLANK ( _cur ) && NOT ISBLANK ( _prev ),
            COALESCE ( {at(f"MAX ( FactStatusReport[{col}] )", "_cur")}, 0 )
                - COALESCE ( {at(f"MAX ( FactStatusReport[{col}] )", "_prev")}, 0 ) )
)""", "+#,##0;-#,##0;0", FOLDER + "\\Drift",
        f"Latest minus previous {col} per project (projects with both reports), summed.")
    add(m(f"{nm} Drift Colour"), T, f"""
VAR _d = {ref(nm + " Drift")}
RETURN IF ( ISBLANK ( _d ) || _d = 0, "{GREY_TEXT}", IF ( _d > 0, "{RED if nm != 'Budget' else NAVY}", "{TEAL if nm != 'Budget' else AMBER_TEXT}" ) )""",
        folder="Story\\Colours")
add(m("Projects Forecast Up"), I, f"""
SUMX ( {PKS}, IF ( {ref("Forecast Drift")} > 0, 1 ) ) + 0""", "#,##0", FOLDER + "\\Drift",
    "Projects whose forecast is higher on the latest report than on the previous one.")

# ------------------------------------------------------------------ month on month (page 5c "What changed")
# "This month" = the month of the report-period pick (last date in the DimDate filter), capped at the latest status
# report in the model, so with no pick it is the latest month that has a report. Each project is read on its latest
# report ON OR BEFORE the month end (carried forward, same rule as the Home sparklines), this month and last month.
DATE_MOVE_D = 7                         # finish date moved: at least this many days
BIG_DATE_D = 30                         # ... a big move (change size 2) above this
FC_MOVE_PCT, FC_MOVE_EUR = 0.02, 10000  # forecast moved: at least max(2% of last month's forecast, EUR 10K)
BIG_FC_PCT = 0.05                       # ... a big move (change size 2) above 5%
THIS_END = f"EOMONTH ( MIN ( MAX ( DimDate[Date] ), CALCULATE ( MAX ( {END} ), REMOVEFILTERS () ) ), 0 )"
MFOLDER = FOLDER + "\\MoM"


def snap_end(d):
    """The project's latest report end on or before date d (date filters ignored)."""
    return f"CALCULATE ( MAX ( {END} ), REMOVEFILTERS ( DimDate ), {END} <= {d}, {END} > DATE ( 1900, 1, 1 ) )"


MOM = f"""
    VAR _te = {THIS_END}
    VAR _pe = EOMONTH ( _te, -1 )
    VAR _n = {snap_end("_te")}
    VAR _p = {snap_end("_pe")}"""


def val(col, d):
    return at(f"MAX ( FactStatusReport[{col}] )", d)


def mm(name):
    return m("MoM " + name)


def mref(name):
    return ref("MoM " + name)


add(mm("This Month End"), DT_, THIS_END, "dd mmm yyyy", MFOLDER,
    "End of the month under review: the report-period pick, capped at the latest status report in the model.")
add(mm("Month Label"), T, f'FORMAT ( {THIS_END}, "mmm yyyy" )', folder=MFOLDER)
add(mm("Previous Month Label"), T, f'FORMAT ( EOMONTH ( {THIS_END}, -1 ), "mmm yyyy" )', folder=MFOLDER)

# per project (one project in context); portfolio totals below iterate PKS
add(mm("Health Then"), I, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _p ), {at(rank("OverallHealth"), "_p")} ) )""", "0", MFOLDER,
    "Overall health rank on the project's latest report as of last month's end (1 = On Track).")
add(mm("Health Now"), I, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _n ), {at(rank("OverallHealth"), "_n")} ) )""", "0", MFOLDER,
    "Overall health rank on the project's latest report as of this month's end (1 = On Track).")
add(mm("Health Move"), I, f"""
IF ( {ONE},
    VAR _c = {mref("Health Now")}
    VAR _b = {mref("Health Then")}
    RETURN IF ( NOT ISBLANK ( _c ) && NOT ISBLANK ( _b ), _c - _b ) )""", "+0;-0;0", MFOLDER,
    "This month's minus last month's overall health rank: positive = worse.")
add(mm("Health Change"), T, f"""
IF ( {ONE},
    VAR _c = {mref("Health Now")}
    VAR _b = {mref("Health Then")}
    RETURN IF ( NOT ISBLANK ( _c ),
        IF ( ISBLANK ( _b ), "new · " & {label("_c")}, {label("_b")} & " → " & {label("_c")} ) ) )""",
    folder=MFOLDER, desc="Overall health last month → this month ('new' when there was no report last month).")
add(mm("Health Change Colour"), T, f"""
VAR _m = {mref("Health Move")}
RETURN IF ( _m > 0, "{RED}", IF ( _m < 0, "{TEAL}", "{NAVY}" ) )""", folder="Story\\Colours")
add(mm("Finish Shift (d)"), I, f"""
IF ( {ONE},{MOM}
    VAR _fn = IF ( NOT ISBLANK ( _n ), {val("Summary_EndDate", "_n")} )
    VAR _fp = IF ( NOT ISBLANK ( _p ), {val("Summary_EndDate", "_p")} )
    RETURN IF ( NOT ISBLANK ( _fn ) && NOT ISBLANK ( _fp ), INT ( _fn ) - INT ( _fp ) ) )""", "+0;-0;0", MFOLDER,
    "Finish date this month minus last month, in days (both status reports must hold a finish date).")
add(mm("Forecast Then"), D, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _p ), {val("Forecast", "_p")} ) )""", "#,##0", MFOLDER)
add(mm("Forecast Delta"), D, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _n ) && NOT ISBLANK ( _p ),
        COALESCE ( {val("Forecast", "_n")}, 0 ) - COALESCE ( {val("Forecast", "_p")}, 0 ) ) )""",
    "+#,##0;-#,##0;0", MFOLDER, "Forecast this month minus last month (status reports).")
add(mm("Forecast Moved"), I, f"""
VAR _d = {mref("Forecast Delta")}
VAR _b = COALESCE ( {mref("Forecast Then")}, 0 )
RETURN IF ( NOT ISBLANK ( _d ) && ABS ( _d ) >= MAX ( {FC_MOVE_PCT} * ABS ( _b ), {FC_MOVE_EUR} ), 1, 0 )""", "0",
    MFOLDER, f"1 when the forecast moved by at least {FC_MOVE_PCT:.0%} of last month's forecast or EUR {FC_MOVE_EUR:,}.")
add(mm("Risks Delta"), I, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _n ) && NOT ISBLANK ( _p ),
        COALESCE ( {val("ActiveRisks", "_n")}, 0 ) - COALESCE ( {val("ActiveRisks", "_p")}, 0 ) ) )""",
    "+0;-0;0", MFOLDER, "Active risks this month minus last month (status reports).")
add(mm("State Then"), T, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _p ), {val("State", "_p")} ) )""", folder=MFOLDER)
add(mm("State Now"), T, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _n ), {val("State", "_n")} ) )""", folder=MFOLDER)
add(mm("State Change"), T, f"""
VAR _a = {mref("State Then")}
VAR _b = {mref("State Now")}
RETURN IF ( NOT ISBLANK ( _a ) && NOT ISBLANK ( _b ) && _a <> _b, _a & " → " & _b )""", folder=MFOLDER)
add(mm("Is New"), I, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _n ) && ISBLANK ( _p ), 1, 0 ) )""", "0", MFOLDER,
    "1 when the project has a report this month but none on or before last month's end.")
add(mm("Comparable"), I, f"""
IF ( {ONE},{MOM}
    RETURN IF ( NOT ISBLANK ( _n ) && NOT ISBLANK ( _p ), 1, 0 ) )""", "0", MFOLDER,
    "1 when the project has a report as of both month ends.")
add(mm("Change Size"), I, f"""
IF ( {ONE},
    VAR _hm = {mref("Health Move")}
    VAR _sh = ABS ( {mref("Finish Shift (d)")} )
    VAR _fd = {mref("Forecast Delta")}
    VAR _fb = {mref("Forecast Then")}
    VAR _s =
        IF ( _hm > 0, 3, IF ( _hm < 0, 1, 0 ) )
            + IF ( _sh > {BIG_DATE_D}, 2, IF ( _sh >= {DATE_MOVE_D}, 1, 0 ) )
            + IF ( {mref("Forecast Moved")} = 1, IF ( ABS ( DIVIDE ( _fd, _fb ) ) > {BIG_FC_PCT}, 2, 1 ), 0 )
            + IF ( COALESCE ( {mref("Risks Delta")}, 0 ) <> 0, 1, 0 )
            + IF ( NOT ISBLANK ( {mref("State Change")} ), 1, 0 )
            + COALESCE ( {mref("Is New")}, 0 )
    RETURN IF ( _s > 0, _s ) )""", "0", MFOLDER,
    f"Ledger sort key: health worse 3; finish moved > {BIG_DATE_D} d or forecast > {BIG_FC_PCT:.0%} 2; any other "
    "change 1 (added up). Blank = no change.")

# portfolio totals (each project against its own two snapshots; the parts add up)
add(mm("Worsened"), I, f"SUMX ( {PKS}, IF ( {mref('Health Move')} > 0, 1 ) ) + 0", "#,##0", MFOLDER)
add(mm("Improved"), I, f"SUMX ( {PKS}, IF ( {mref('Health Move')} < 0, 1 ) ) + 0", "#,##0", MFOLDER)
add(mm("Dates Moved"), I, f"SUMX ( {PKS}, IF ( ABS ( {mref('Finish Shift (d)')} ) >= {DATE_MOVE_D}, 1 ) ) + 0",
    "#,##0", MFOLDER, f"Projects whose finish date moved {DATE_MOVE_D}+ days since last month.")
add(mm("Net Days"), I, f"""
SUMX ( {PKS}, VAR _s = {mref("Finish Shift (d)")} RETURN IF ( ABS ( _s ) >= {DATE_MOVE_D}, _s ) )""", "+0;-0;0",
    MFOLDER, "Net finish-date movement of the projects counted by Dates Moved, in days.")
add(mm("Dates KPI"), T, f"""
VAR _c = {mref("Dates Moved")}
RETURN FORMAT ( _c, "0" ) & IF ( _c > 0, " (" & FORMAT ( {mref("Net Days")}, "+0;-0;0" ) & " d)", "" )""",
    folder=MFOLDER)
add(mm("Forecast Net"), D, f"SUMX ( {PKS}, {mref('Forecast Delta')} )", "+#,##0;-#,##0;0", MFOLDER,
    "Net forecast movement since last month, projects with a report in both months.")
add(mm("Risks Net"), I, f"SUMX ( {PKS}, {mref('Risks Delta')} ) + 0", "+0;-0;0", MFOLDER)
add(mm("New"), I, f"SUMX ( {PKS}, {mref('Is New')} ) + 0", "#,##0", MFOLDER)
add(mm("Closed"), I, f"""
SUMX ( {PKS}, IF ( {mref("State Now")} = "Closed" && NOT ISBLANK ( {mref("State Change")} ), 1 ) ) + 0""",
    "#,##0", MFOLDER)
add(mm("New Closed KPI"), T,
    f'FORMAT ( {mref("New")}, "0" ) & " new · " & FORMAT ( {mref("Closed")}, "0" ) & " closed"', folder=MFOLDER)
add(mm("Not Comparable"), I, f"""
CALCULATE ( SUMX ( {PKS}, IF ( {mref("Comparable")} = 0, 1 ) ), KEEPFILTERS ( DimProject[State_Value] = "Active" ) ) + 0""",
    "#,##0", MFOLDER, "Active projects without a report as of one of the two month ends.")
add(mm("Changed Projects"), I, f"SUMX ( {PKS}, IF ( {mref('Change Size')} > 0, 1 ) ) + 0", "#,##0", MFOLDER)
add(mm("Has Previous Month"), I, f"""
IF ( CALCULATE ( COUNTROWS ( FactStatusReport ), REMOVEFILTERS (), {END} <= EOMONTH ( {THIS_END}, -1 ),
    {END} > DATE ( 1900, 1, 1 ) ) > 0, 1, 0 )""", "0", MFOLDER,
    "1 when any status report exists on or before last month's end (else there is nothing to compare).")

# ledger columns: blank unless the project changed, so unchanged projects drop out of the table
for _nm in ("Health Change", "Finish Shift (d)", "Forecast Delta", "Risks Delta", "State Change"):
    _src = next(x for x in MEASURES if x["name"] == mm(_nm))
    add(mm("L · " + _nm), _src["dataType"], f"IF ( NOT ISBLANK ( {mref('Change Size')} ), {mref(_nm)} )",
        _src["formatString"], MFOLDER + "\\Ledger", f"{_nm} of a project that changed since last month; blank otherwise.")
add(mm("L · Size"), I, mref("Change Size"), "0", MFOLDER + "\\Ledger")

add(mm("Headline"), T, f"""
VAR _lbl = {mref("Month Label")}
VAR _plb = {mref("Previous Month Label")}
VAR _ch = {mref("Changed Projects")}
VAR _w = {mref("Worsened")}
VAR _i = {mref("Improved")}
VAR _dm = {mref("Dates Moved")}
VAR _nd = COALESCE ( {mref("Net Days")}, 0 )
VAR _fn = COALESCE ( {mref("Forecast Net")}, 0 )
VAR _fna = ABS ( _fn )
VAR _rk = {mref("Risks Net")}
VAR _nc = {mref("Not Comparable")}
RETURN
    IF ( {mref("Has Previous Month")} = 0,
        "Only one month of status reports so far (" & _lbl & ") — nothing to compare yet.",
        IF ( _ch = 0, "In " & _lbl & " no project changed against " & _plb & ".",
            "In " & _lbl & " versus " & _plb & ": " & FORMAT ( _w, "0" ) & " project(s) got worse and "
                & FORMAT ( _i, "0" ) & " improved; " & FORMAT ( _dm, "0" ) & " finish date(s) moved ("
                & FORMAT ( _nd, "+0;-0;0" ) & " days net); forecast " & IF ( _fn >= 0, "+", "−" ) & {money("_fna")}
                & "; active risks " & FORMAT ( _rk, "+0;-0;0" ) & "; " & {mref("New Closed KPI")} & "." )
            & IF ( _nc > 0, " " & FORMAT ( _nc, "0" )
                & " active project(s) cannot be compared (no report in one of the two months).", "" ) )""",
    folder="Story\\Headlines")

# ------------------------------------------------------------------ reporting discipline
add(m("Stale Days"), I, str(STALE_DAYS), "0", FOLDER + "\\Discipline",
    "Reporting threshold: a project without a submitted report in this many days counts as not reporting.")
add(m("Days Since Report"), I, f"""
IF ( {ONE},
    VAR _d = [PMO | Last Status Report Date]
    RETURN IF ( NOT ISBLANK ( _d ), INT ( TODAY () - _d ) )
)""", "#,##0", FOLDER + "\\Discipline", "Days since the project's last submitted status report (date filters ignored).")
add(m("Avg Days Since Report"), D, f"""
AVERAGEX (
    FILTER ( {PKS}, NOT ISBLANK ( [PMO | Last Status Report Date] ) ),
    INT ( TODAY () - [PMO | Last Status Report Date] )
)""", "#,##0", FOLDER + "\\Discipline")
add(m("Reporting Gap"), I, f"""
IF ( {ONE},
    VAR _st = SELECTEDVALUE ( DimProject[State_Value] )
    VAR _any = NOT ISEMPTY ( CALCULATETABLE ( FactStatusReport, REMOVEFILTERS ( DimDate ) ) )
    VAR _scope =
        SELECTEDVALUE ( DimProject[PlanType] ) = "Project"
            && COALESCE ( _st, "" ) <> "Closed"
            && ( _st = "Active" || _any )
    VAR _d = [PMO | Last Status Report Date]
    RETURN
        IF ( _scope,
            IF ( ISBLANK ( _d ), 2, IF ( INT ( TODAY () - _d ) > {ref("Stale Days")}, 1, 0 ) ) )
)""", "0", FOLDER + "\\Discipline",
    "0 = reported within the threshold, 1 = overdue, 2 = nothing submitted yet. Blank = not expected to report "
    "(not a Project plan, closed, or neither active nor ever reported).")
# Labels read as plain words AND sort worst-first in ascending text order (M < O < R < W), so the discipline
# table sorts on this column: nothing submitted, then overdue (longest silence first), then on time, then waived.
add(m("Reporting Status"), T, f"""
IF ( {ONE},
    VAR _g = {ref("Reporting Gap")}
    RETURN
        SWITCH ( _g,
            2, "Missing — nothing submitted",
            1, "Overdue (> " & {ref("Stale Days")} & " d)",
            0, "Reported on time",
            "Waived — not expected to report" )
)""", folder=FOLDER + "\\Discipline",
    desc="Missing (nothing submitted) / Overdue / Reported on time / Waived (not a Project plan, closed, or neither "
         "active nor ever reported). Sorted A→Z the worst come first.")
add(m("Reporting Colour"), T, f"""
SWITCH ( {ref("Reporting Gap")}, 0, "{TEAL}", 1, "{RED}", 2, "{RED}", "#666666" )""", folder="Story\\Colours")
add(m("Not Reporting"), I, f"""
SUMX ( {PKS}, IF ( {ref("Reporting Gap")} >= 1, 1 ) ) + 0""", "#,##0", FOLDER + "\\Discipline",
    "Projects expected to report with no submitted status report in the last N days (see Stale Days).")
add(m("Unsubmitted Reports"), I, """
CALCULATE (
    COUNTROWS (
        FILTER (
            FactStatusReport,
            ( ISBLANK ( FactStatusReport[Report_SubmitDate] ) || FactStatusReport[Report_SubmitDate] <= DATE ( 1900, 1, 1 ) )
                && FactStatusReport[Report_ReportEnd] > DATE ( 1900, 1, 1 )
                && FactStatusReport[Report_ReportEnd] < TODAY ()
        )
    ),
    KEEPFILTERS ( NOT ISBLANK ( DimProject[Id] ) )
)""", "#,##0", FOLDER + "\\Discipline",
    "Status reports of project plans whose period has ended but that have no submit date (selected report period).")
add(m("Latest State"), T, f"""
IF ( {ONE},
    VAR _cur = CALCULATE ( MAX ( {END} ), REMOVEFILTERS ( DimDate ) )
    VAR _st = {at("MAXX ( FactStatusReport, FactStatusReport[Report_State] )", "_cur")}
    RETURN IF ( NOT ISBLANK ( _cur ), COALESCE ( _st, "–" ) )
)""", folder=FOLDER + "\\Discipline", desc="Workflow state of the project's most recent status report.")

# ------------------------------------------------------------------ narrative of the latest report
for nm, col in [("Accomplishments", "Accomplishments"), ("Planned Activities", "PlannedActivities"),
                ("Comments", "AdditionalComments")]:
    add(m(nm), T, f"""
IF ( {ONE},
    VAR _cur = MAX ( {END} )
    VAR _t = {at(f"MAXX ( FactStatusReport, FactStatusReport[{col}] )", "_cur")}
    RETURN IF ( NOT ISBLANK ( _t ), {clean("_t")} )
)""", folder=FOLDER + "\\Narrative", desc=f"{col} of the project's latest status report, rich-text tags removed.")

# ------------------------------------------------------------------ headline
add(m("Headline"), T, f"""
VAR _n = {ref("Projects Reporting")}
VAR _w = {ref("Overall Worsened")}
VAR _i = {ref("Overall Improved")}
VAR _u = {ref("Overall Unchanged")}
VAR _top =
    TOPN ( 1,
        FILTER (
            ADDCOLUMNS ( VALUES ( DimProject[Name] ), "@m", {ref("Overall Move")}, "@r", {ref("Overall Rank")} ),
            NOT ISBLANK ( DimProject[Name] ) && [@m] > 0 ),
        [@m], DESC, [@r], DESC )
VAR _fd = {ref("Forecast Drift")}
VAR _fda = ABS ( _fd )
VAR _rd = COALESCE ( {ref("Active Risks Drift")}, 0 )
VAR _nr = {ref("Not Reporting")}
VAR _os = COALESCE ( {ref("Unsubmitted Reports")}, 0 )
RETURN
    IF ( _n = 0,
        "No status reports in the current selection — pick a wider report period.",
        FORMAT ( _n, "0" ) & " projects reported in the period. Since their previous report " & FORMAT ( _w, "0" )
            & " got worse overall, " & FORMAT ( _i, "0" ) & " improved and " & FORMAT ( _u, "0" ) & " held steady"
            & IF ( COUNTROWS ( _top ) > 0,
                "; the sharpest drop is " & MAXX ( _top, DimProject[Name] ) & " (now " & {label("MAXX ( _top, [@r] )")} & ")",
                "" ) & ". "
            & IF ( ISBLANK ( _fd ), "",
                "Between reports the forecast moved " & IF ( _fd >= 0, "+", "−" ) & {money("_fda")} & " and active risks "
                    & FORMAT ( _rd, "+0;-0;0" ) & ". " )
            & FORMAT ( _nr, "0" ) & " project(s) have not reported in " & FORMAT ( {ref("Stale Days")}, "0" )
            & " days and " & FORMAT ( _os, "0" ) & " report(s) are still unsubmitted."
    )""", folder="Story\\Headlines")


# ================================================================== page
def build():
    DP = pages.DP
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (DP("ProjectType_Value"), "Project type"), (C("DimDate", "Period"), "Report period")]
    pg = pages.analytic_page(
        "status", "STATUS", "WHAT CHANGED SINCE LAST MONTH?",
        f"Latest report per project versus last month's. Moved = finish {DATE_MOVE_D}+ days or forecast "
        f"{FC_MOVE_PCT:.0%} / €{FC_MOVE_EUR // 1000}K. Report period picks the month.",
        slicers, mm("Headline"))
    assert pg.id == pages.PID["status"] and pg.display == dict(pages.PAGES)["status"]

    # ① pulse
    pages.section(pg, pages.Y1, 1, "What moved this month?",
                  "This month's latest report per project against last month's; projects without both are counted apart.")
    pages.kpi_row(pg, pages.Y1K, [
        (mm("Worsened"), "Health worse", {"value_colour": RED}),
        (mm("Improved"), "Health better", {"value_colour": TEAL}),
        (mm("Dates KPI"), "Finish dates moved (net)", {"size": pbir.KPI_TEXT_PT}),
        (mm("Forecast Net"), "Forecast moved (net €)"),
        (mm("Risks Net"), "Active risks (net)"),
        (mm("New Closed KPI"), "New · closed", {"size": pbir.KPI_TEXT_PT}),
        (mm("Not Comparable"), "Not comparable", {"value_colour": AMBER}),
    ])

    # ② change ledger
    Y2, Y2V, H2 = pages.Y2, pages.Y2V, pages.H2
    pages.section(pg, Y2, 2, "Which projects changed — biggest change first?",
                  f"Size: health worse 3 · finish > {BIG_DATE_D} d or forecast > {BIG_FC_PCT:.0%} 2 · any other change 1. "
                  "Unchanged projects are not listed; ✓ = may slip (Act now).")
    size, hc = M(mm("L · Size")), M(mm("L · Health Change"))
    obj = table_style(9)
    obj["values"] += [cf_font(hc, mm("Health Change Colour"))]
    pg.add(16, Y2V, 1768, H2, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(hc, "Health: last month → now"),
                    P(M(mm("L · Finish Shift (d)")), "Finish Δ days"), P(M(mm("L · Forecast Delta")), "Forecast Δ"),
                    P(M(mm("L · Risks Delta")), "Risks Δ"), P(M(mm("L · State Change")), "State"),
                    P(M("Story | Slip · Flag Text"), "May slip"), P(size, "Change size")]},
        "Change ledger — this month versus last month", obj, sort=[(size, "Descending")]),
        key="v_ledger", filters=[pages.REAL_PROJECTS])

    # ③ heat strip + drift
    Y3, Y3V, H3 = pages.Y3, pages.Y3V, pages.H3
    pages.section(pg, Y3, 3, "How has health evolved, and what drifted?",
                  "Latest overall health per report month; drift = each project's latest report versus its own previous one.")
    pages.legend_note(pg, 1084, Y3 + 4, 700, [("On Track", TEAL), ("At Risk", AMBER), ("Off Track", RED)],
                      "heat_legend")
    heat = M(m("Heat Cell"))
    obj = table_style(9)
    obj["values"] += [cf_back(heat, m("Heat Colour")), cf_font(heat, m("Heat Font"))]
    obj["subTotals"] = [{"properties": {"rowSubtotals": b(False), "columnSubtotals": b(False)}}]
    pg.add(16, Y3V, 878, H3, chart("pivotTable",
        {"Rows": [P(DP("Name"), "Project", True)], "Columns": [P(C("DimDate", "Period"), "Report period", True)],
         "Values": [P(heat, "Overall")]},
        "Health heat strip — project × report period (latest report in the month)", obj), key="v_heat")
    fd, rd = M(m("Forecast Drift")), M(m("Active Risks Drift"))
    obj = table_style(9)
    obj["values"] += [cf_font(fd, m("Forecast Drift Colour")), cf_font(rd, m("Active Risks Drift Colour")),
                      cf_font(M(m("Budget Drift")), m("Budget Drift Colour"))]
    pg.add(906, Y3V, 878, H3, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(M(m("Budget Drift")), "Budget Δ"),
                    P(M(m("Forecast Previous")), "Forecast before"), P(M(m("Forecast Latest")), "Forecast now"),
                    P(fd, "Forecast Δ"), P(M(m("Active Risks Previous")), "Risks before"),
                    P(M(m("Active Risks Latest")), "Risks now"), P(rd, "Risks Δ")]},
        "Drift between reports — biggest forecast increase first", obj, sort=[(fd, "Descending")]), key="v_drift")

    # ④ discipline + narrative
    Y4, Y4V, H4 = pages.Y4, pages.Y4V, pages.H4
    pages.section(pg, Y4, 4, "Who is not reporting, and what did the others say?",
                  f"Red = nothing submitted in {STALE_DAYS} days. Narrative = the latest report of each project.")
    gap_f = M(m("Reporting Status"))
    days = M(m("Days Since Report"))
    obj = table_style(9)
    obj["values"] += [cf_font(gap_f, m("Reporting Colour")), cf_font(days, m("Reporting Colour"))]
    pg.add(16, Y4V, 700, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Manager_Value"), "Manager"),
                    P(M("PMO | Last Status Report Date"), "Last submitted"), P(days, "Days since"),
                    P(gap_f, "Reporting"), P(M(m("Latest State")), "Latest state"),
                    P(M(m("Unsubmitted Reports")), "Unsubmitted"),
                    P(M("Story | PMO · Plans Not Up To Date"), "Plan not up to date")]},
        "Reporting discipline — nothing submitted first, then longest silence", obj,
        sort=[(gap_f, "Ascending"), (days, "Descending")]), key="v_discipline",
        filters=[pbir.f_in("DimProject", "PlanType", ["Project"])])
    obj = table_style(9)
    obj["values"][0]["properties"]["wordWrap"] = b(True)
    obj["values"] += [cf_font(M(m("Overall Now")), m("Overall Now Colour"))]
    pg.add(728, Y4V, 1056, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(M(m("Latest Report End")), "Report end"),
                    P(M(m("Overall Now")), "Overall"), P(M(m("Accomplishments")), "Accomplishments"),
                    P(M(m("Planned Activities")), "Planned activities"), P(M(m("Comments")), "Comments")]},
        "What the latest report says", obj, sort=[(DP("Name"), "Ascending")]), key="v_narrative")

    pages.next_chapter(pg, "status", pages.YNEXT)
    return [pg]
