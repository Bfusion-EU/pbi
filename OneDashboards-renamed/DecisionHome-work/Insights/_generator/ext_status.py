"""5b · Status-Report Trend — which projects got better or worse since their last
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
from pbir import C, M, P, b, chart, cf_back, cf_font, measure_fill, table_style, title, labels_on, legend
from pbir import NAVY, TEAL, AMBER, RED, GREY
from story_measures import add, money, T, D, I

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
RETURN IF ( ISBLANK ( _m ) || _m = 0, "{GREY}", IF ( _m < 0, "{TEAL}", "{RED}" ) )""", folder="Story\\Colours")

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
RETURN IF ( ISBLANK ( _d ) || _d = 0, "{GREY}", IF ( _d > 0, "{RED if nm != 'Budget' else NAVY}", "{TEAL if nm != 'Budget' else AMBER}" ) )""",
        folder="Story\\Colours")
add(m("Projects Forecast Up"), I, f"""
SUMX ( {PKS}, IF ( {ref("Forecast Drift")} > 0, 1 ) ) + 0""", "#,##0", FOLDER + "\\Drift",
    "Projects whose forecast is higher on the latest report than on the previous one.")

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
def _movement_bar(dim, ttl):
    imp, unc, wor = (M(m(f"{dim} {w}")) for w in ("Improved", "Unchanged", "Worsened"))
    return chart("barChart", {"Y": [P(imp, "Improved"), P(unc, "Unchanged"), P(wor, "Worsened")]}, ttl,
                 {"dataPoint": [measure_fill(imp, TEAL), measure_fill(unc, "#C9CED8"), measure_fill(wor, RED)],
                  "legend": legend("Top", False), "labels": labels_on(True, 0, 9),
                  "categoryAxis": [{"properties": {"show": b(False)}}],
                  "valueAxis": [{"properties": {"show": b(False)}}]},
                 extra_vco={"title": title(ttl, 10)})


def build():
    DP = pages.DP
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (DP("ProjectType_Value"), "Project type"), (C("DimDate", "Period"), "Report period")]
    pg = pages.analytic_page("status", "STATUS REPORTS", "GETTING BETTER OR WORSE?",
                             "Each project compared with its own previous OnePlan status report — health, money and risks — "
                             "plus who has stopped reporting. The report-period slicer picks the 'latest' report.",
                             slicers, m("Headline"))
    assert pg.id == pages.PID["status"] and pg.display == dict(pages.PAGES)["status"]

    # ① pulse
    pages.section(pg, pages.Y1, 1, "The reporting pulse",
                  "Movement counts compare each project's latest report with the one before it.")
    pages.kpi_row(pg, pages.Y1K, [
        (m("Projects Reporting"), "Projects reporting"),
        (m("Overall Improved"), "Improved overall", {"value_colour": TEAL}),
        (m("Overall Worsened"), "Worsened overall", {"value_colour": RED}),
        (m("Forecast Drift"), "Forecast drift", {"colour_measure": m("Forecast Drift Colour")}),
        (m("Active Risks Drift"), "Active-risk drift", {"colour_measure": m("Active Risks Drift Colour")}),
        (m("Avg Days Since Report"), "Avg days since last report"),
        (m("Not Reporting"), f"Not reporting ({STALE_DAYS} d)", {"value_colour": RED}),
        ("Story | PMO · Plans With Open Status Report", "Plans with open report", {"value_colour": AMBER}),
    ])

    # ② movement
    Y2, Y2V, H2 = pages.Y2, pages.Y2V, pages.H2
    pages.section(pg, Y2, 2, "Who got better or worse since the last report?",
                  "Per health dimension, then project by project — worst moves first.")
    pages.legend_note(pg, 1084, Y2 + 4, 700, [("Improved", TEAL), ("Unchanged", "#8A93A0"), ("Worsened", RED)],
                      "move_legend")
    bh, gap = 64, 5
    for k, (dim, _) in enumerate(DIMS):
        pg.add(16, Y2V + k * (bh + gap), 560, bh, _movement_bar(dim, f"{dim} health"), key=f"v_move_{dim}")
    cols = [P(DP("Name"), "Project"), P(M(m("Previous Report End")), "Previous report"),
            P(M(m("Latest Report End")), "Latest report"), P(M(m("Overall Change")), "Overall: before → now"),
            P(M(m("Overall Move")), "Overall Δ")]
    obj = table_style(9)
    obj["values"] += [cf_font(M(m("Overall Change")), m("Overall Now Colour")),
                      cf_font(M(m("Overall Move")), m("Overall Arrow Colour"))]
    for dim, _ in DIMS[1:]:
        f = M(m(f"{dim} Arrow"))
        cols.append(P(f, dim))
        obj["values"].append(cf_font(f, m(f"{dim} Arrow Colour")))
    pg.add(588, Y2V, 1196, H2, chart("tableEx", {"Values": cols},
                                     "Movement since the previous report — Δ +1 = one health level worse",
                                     obj, sort=[(M(m("Overall Move")), "Descending")]), key="v_move_table")

    # ③ heat strip + drift
    Y3, Y3V, H3 = pages.Y3, pages.Y3V, pages.H3
    pages.section(pg, Y3, 3, "How has health evolved, and what drifted?",
                  "Latest overall health per report month; budget, forecast and risks on the latest versus previous report.")
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
