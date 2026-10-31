"""4b · Timesheets vs Plan — is the work happening as planned, and is the time actually in?

Plan = resource-plan *Scheduled* hours (FactResourcePlan, via [Capacity | Total Hours Scheduled]).
Actual = approved timesheet project hours (FactTimesheet, via [Timesheet | Actual Hours]; time off excluded).

Model notes (checked in ModeL360Star.bim):
- FactTimesheet[ProjectKey] -> DimProject is INACTIVE. Project filters reach timesheets only through
  FactTimesheet[TaskKey] -> DimTask -> DimProject (both active, single direction). Every project-level
  visual here groups on DimProject columns, so the filter flows down that task path; no USERELATIONSHIP is
  used (activating it would open a second, ambiguous path DimProject -> FactTimesheet).
- Time-off lines are excluded by [Timesheet | Actual Hours] (IsTimeOff = 0); they also drop out as soon as
  any DimProject filter is applied, because their task is not on a project plan.
- Never reconcile against the resource-plan "Timesheets" cost type: it is the plan's own monthly actuals,
  not the timesheet lines (Obsidian: fact-oneplan-timesheets-semantics).
- "Scheduled to date" is the plan for the timesheet window only: from the first timesheet period start to the
  last timesheet period end in the model, on PROJECT plans only. Months before timesheets were in use and months
  nobody could have booked yet no longer dilute plan accuracy (the model's [Timesheet | Actual vs Scheduled %]
  divides by all scheduled hours in context), and non-project plans (blank DimProject row) are left out.
"""
import pages
import pbir
from pbir import (C, M, P, AMBER, GREY, MUTED, NAVY, ORANGE, RED, TEAL, b, card, chart, f_cmp, labels_on, legend,
                  measure_fill, n, table_style, cf_font)
from story_measures import add

PFX = "Story | Timesheet · "
FOLDER = "Story\\Timesheets"
T, D, I = "Text", "Double", "Integer"
UNPLANNED = "#8E1B12"


def _m(name):
    return PFX + name


# ------------------------------------------------------------------ measures
add(_m("Actuals Cut-off"), "DateTime", """
COALESCE ( CALCULATE ( MAX ( FactTimesheet[PeriodEnd] ), REMOVEFILTERS () ), TODAY () )""",
    "dd mmm yyyy", FOLDER,
    "Last timesheet period end in the model (ignores all filters). Plan figures are cut here so that months "
    "nobody could book yet do not count as 'not done'.")

add(_m("Actuals Start"), "DateTime", """
CALCULATE ( MIN ( FactTimesheet[PeriodStart] ), REMOVEFILTERS () )""",
    "dd mmm yyyy", FOLDER,
    "First timesheet period start in the model (ignores all filters). Plan figures start here so that months "
    "before timesheets were in use do not count as 'not done'.")

add(_m("Scheduled To Date"), D, f"""
VAR _from = [{_m('Actuals Start')}]
VAR _cut = [{_m('Actuals Cut-off')}]
RETURN
    CALCULATE (
        [Capacity | Total Hours Scheduled],
        KEEPFILTERS ( DimDate[Date] <= _cut ),
        KEEPFILTERS ( DimDate[Date] >= _from ),
        KEEPFILTERS ( NOT ISBLANK ( DimProject[Id] ) )
    )""",
    "#,##0", FOLDER,
    "Resource-plan Scheduled hours on project plans inside the timesheet window (first timesheet period start to "
    "the actuals cut-off). The plan side of plan-versus-actual.")

add(_m("Variance Hours"), D, f"""
VAR _s = [{_m('Scheduled To Date')}]
VAR _a = [Timesheet | Actual Hours]
RETURN IF ( ISBLANK ( _s ) && ISBLANK ( _a ), BLANK (), COALESCE ( _a, 0 ) - COALESCE ( _s, 0 ) )""",
    "+#,##0;-#,##0;0", FOLDER,
    "Approved timesheet project hours minus scheduled hours to date. Positive = effort over-run.")

add(_m("Plan Accuracy %"), D, f"""
DIVIDE ( [Timesheet | Actual Hours], [{_m('Scheduled To Date')}] )""",
    "0%", FOLDER,
    "Approved timesheet project hours ÷ scheduled hours to date. 80–120% = on plan.")

add(_m("Accuracy Colour"), T, f"""
VAR _s = [{_m('Scheduled To Date')}]
VAR _a = [Timesheet | Actual Hours]
VAR _r = DIVIDE ( _a, _s )
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( _s ) && ISBLANK ( _a ), "#9AA3AF",
        COALESCE ( _s, 0 ) = 0, "{UNPLANNED}",
        _r > 1.2, "{RED}",
        _r >= 0.8, "{TEAL}",
        "{AMBER}"
    )""", folder="Story\\Colours")

add(_m("Accuracy Band"), T, f"""
VAR _s = [{_m('Scheduled To Date')}]
VAR _a = [Timesheet | Actual Hours]
VAR _r = DIVIDE ( _a, _s )
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( _s ) && ISBLANK ( _a ), BLANK (),
        COALESCE ( _s, 0 ) = 0, "Unplanned work",
        ISBLANK ( _a ), "No time booked",
        _r > 1.2, "Over-run",
        _r >= 0.8, "On plan",
        "Under-run"
    )""", folder=FOLDER, desc="Unplanned work / Over-run (>120%) / On plan (80–120%) / Under-run (<80%) / No time booked.")

add(_m("Unplanned Hours"), D, f"""
SUMX (
    FILTER ( VALUES ( DimProject[ProjectKey] ), NOT ISBLANK ( DimProject[ProjectKey] ) ),
    VAR _a = [Timesheet | Actual Hours]
    RETURN IF ( COALESCE ( [{_m('Scheduled To Date')}], 0 ) = 0, _a )
)""", "#,##0", FOLDER,
    "Approved timesheet hours on projects that have no scheduled hours to date in the current selection.")

add(_m("Unplanned Share %"), D, f"""
DIVIDE ( [{_m('Unplanned Hours')}], [Timesheet | Actual Hours] )""", "0%", FOLDER,
    "Share of approved timesheet hours booked on projects without a schedule.")


def _count(cond):
    return f"""
COUNTROWS (
    FILTER (
        FILTER ( VALUES ( DimProject[ProjectKey] ), NOT ISBLANK ( DimProject[ProjectKey] ) ),
        VAR _s = COALESCE ( [{_m('Scheduled To Date')}], 0 )
        VAR _a = COALESCE ( [Timesheet | Actual Hours], 0 )
        RETURN {cond}
    )
) + 0"""


add(_m("Projects Over-running"), I, _count("_s > 0 && _a > 1.2 * _s"), "#,##0", FOLDER,
    "Projects whose approved hours exceed 120% of scheduled hours to date.")
add(_m("Projects Under-running"), I, _count("_s > 0 && _a < 0.8 * _s"), "#,##0", FOLDER,
    "Projects with scheduled hours to date but less than 80% of them booked (including none at all).")
add(_m("Projects Unplanned"), I, _count("_s = 0 && _a > 0"), "#,##0", FOLDER,
    "Projects with approved timesheet hours but no scheduled hours to date.")

add(_m("Not Approved Hours"), D, """
COALESCE ( [Timesheet | Hours], 0 ) - COALESCE ( [Timesheet | Approved Hours], 0 )""", "#,##0.0", FOLDER,
    "Timesheet hours still in draft or awaiting approval (time off included).")

add(_m("Approval Colour"), T, """
VAR _p = [Timesheet | Approval %]
RETURN IF ( ISBLANK ( _p ), "#9AA3AF", IF ( _p >= 0.95, "#1E6D6E", IF ( _p >= 0.8, "#D9A832", "#C0392B" ) ) )""",
    folder="Story\\Colours")

add(_m("Compliance Colour"), T, """
VAR _p = [Timesheet | Reporting Compliance %]
RETURN IF ( ISBLANK ( _p ), "#9AA3AF", IF ( _p >= 0.9, "#1E6D6E", IF ( _p >= 0.7, "#D9A832", "#C0392B" ) ) )""",
    folder="Story\\Colours")

add(_m("Headline"), T, f"""
VAR _s = [{_m('Scheduled To Date')}]
VAR _a = [Timesheet | Actual Hours]
VAR _acc = DIVIDE ( _a, _s )
VAR _u = [{_m('Unplanned Share %')}]
VAR _miss = COALESCE ( [Timesheet | Resources Missing Time], 0 )
VAR _wait = COALESCE ( [{_m('Not Approved Hours')}], 0 )
VAR _lag = [Timesheet | Avg Approval Lag (days)]
RETURN
    IF (
        ISBLANK ( _s ) && ISBLANK ( _a ),
        "No scheduled or booked hours in this selection.",
        FORMAT ( COALESCE ( _a, 0 ), "#,##0" ) & " approved hours booked against "
            & FORMAT ( COALESCE ( _s, 0 ), "#,##0" ) & " scheduled to date"
            & IF ( NOT ISBLANK ( _acc ), " (plan accuracy " & FORMAT ( _acc, "0%" ) & ")", "" ) & ". "
            & IF ( _u > 0, FORMAT ( _u, "0%" ) & " of booked time went to projects with no schedule. ", "" )
            & SWITCH (
                TRUE (),
                _miss > 0, _miss & " person(s) with committed work booked no time. Action: chase the missing timesheets.",
                _wait > 0, FORMAT ( _wait, "#,##0" ) & " h not yet approved. Action: chase the approvers.",
                _u > 0.2, "Action: put the unplanned work into the resource plans.",
                "Time is in and approved."
            )
            & IF ( NOT ISBLANK ( _lag ), " Approval takes " & FORMAT ( _lag, "0.0" ) & " days on average.", "" )
    )""", folder=FOLDER)


# ------------------------------------------------------------------ page
def build():
    DP, DR = pages.DP, pages.DR
    MONTH = pages.MONTH
    slicers = [(DR("Department_Value"), "Department"), (DR("Role_Value"), "Role"),
               (DP("Portfolio Name"), "Portfolio"), (C("DimDate", "Year"), "Year")]
    pg = pages.analytic_page(
        "timesheets", "TIMESHEETS", "IS THE WORK HAPPENING AS PLANNED?",
        "Approved timesheet hours against resource-plan scheduled hours, and whether the time is actually in. "
        "Project filters reach timesheets through the task.",
        slicers, _m("Headline"))

    sched, act = M(_m("Scheduled To Date")), M("Timesheet | Actual Hours")
    acc, var = M(_m("Plan Accuracy %")), M(_m("Variance Hours"))
    band = M(_m("Accuracy Band"))
    acc_col = _m("Accuracy Colour")

    # ① pulse
    pages.section(pg, pages.Y1, 1, "Plan against actuals, and is the time in?",
                  "Plan = scheduled hours on project plans within the timesheet periods. Actual = approved project hours, no time off.")
    pages.kpi_row(pg, pages.Y1K, [
        (_m("Scheduled To Date"), "Scheduled to date (h)"),
        ("Timesheet | Actual Hours", "Approved actuals (h)"),
        (_m("Plan Accuracy %"), "Plan accuracy", {"colour_measure": acc_col}),
        (_m("Unplanned Share %"), "Booked on unplanned work", {"value_colour": UNPLANNED}),
        (_m("Not Approved Hours"), "Hours not yet approved", {"value_colour": AMBER}),
        ("Timesheet | Reporting Compliance %", "Reporting compliance", {"colour_measure": _m("Compliance Colour")}),
        # people-based (the model's rule: named, active, committed work, no hours booked) — 4c counts resource-weeks
        ("Timesheet | Resources Missing Time", "People who booked no time", {"value_colour": RED}),
        ("Timesheet | Avg Approval Lag (days)", "Avg approval lag (days)"),
    ])

    # ② plan vs actuals over time
    pages.section(pg, pages.Y2, 2, "Is the work happening as planned, month by month?",
                  "Columns = scheduled and approved hours; the line is plan accuracy. Line far below 100% = plan not worked or time not in.")
    pg.add(16, pages.Y2V, 1160, pages.H2, chart("lineClusteredColumnComboChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(sched, "Scheduled (h)"), P(act, "Approved actuals (h)")],
         "Y2": [P(acc, "Plan accuracy")]},
        "Scheduled versus approved hours per month",
        {"dataPoint": [measure_fill(sched, "#C9CED8"), measure_fill(act, NAVY), measure_fill(acc, ORANGE)],
         "legend": legend("Top"), "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}]},
        sort=[(MONTH, "Ascending")]), key="v_ts_month")
    dept = DR("Department_Value")
    pg.add(1192, pages.Y2V, 592, pages.H2, chart("clusteredBarChart",
        {"Category": [P(dept, "Department")], "Y": [P(sched, "Scheduled (h)"), P(act, "Approved (h)")]},
        "Scheduled versus approved hours by department",
        {"dataPoint": [measure_fill(sched, "#C9CED8"), measure_fill(act, NAVY)], "legend": legend("Top")},
        sort=[(sched, "Descending")]), key="v_ts_dept")

    # ③ submission compliance
    pages.section(pg, pages.Y3, 3, "Is the time actually in?",
                  "Where the booked hours sit in the approval flow, how long approval takes, and how often sheets bounce back.")
    appr, wait, draft = M("Timesheet | Approved Hours"), M("Timesheet | Awaiting Approval Hours"), M("Timesheet | Draft Hours")
    pg.add(16, pages.Y3V, 700, pages.H3, chart("columnChart",
        {"Category": [P(MONTH, "Month")],
         "Y": [P(appr, "Approved"), P(wait, "Awaiting approval"), P(draft, "Draft")]},
        "Timesheet hours by approval status per month (time off included)",
        {"dataPoint": [measure_fill(appr, TEAL), measure_fill(wait, AMBER), measure_fill(draft, GREY)],
         "legend": legend("Top")}, sort=[(MONTH, "Ascending")]), key="v_ts_status")
    lag = M("Timesheet | Avg Approval Lag (days)")
    pg.add(728, pages.Y3V, 524, pages.H3, chart("clusteredColumnChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(lag, "Avg approval lag (days)")]},
        "Average days from submit to approve, by month of action",
        {"dataPoint": [{"properties": {"fill": pbir.col_solid(ORANGE)}}], "labels": labels_on(True, 0)},
        sort=[(MONTH, "Ascending")]), key="v_ts_lag")
    cw, ch = 255, 195
    tiles = [("Timesheet | Approval %", "Submitted hours approved", {"colour_measure": _m("Approval Colour")}),
             ("Timesheet | Timesheets Awaiting Approval", "Timesheets awaiting approval", {"value_colour": AMBER}),
             ("Timesheet | Rework %", "Rework (recalls + unlocks ÷ submits)", {"value_colour": AMBER}),
             ("Story | PMO · Plans With Unsubmitted Timesheets", "Plans with unsubmitted time", {"value_colour": RED})]
    for k, (m, label, o) in enumerate(tiles):
        x = 1264 + (k % 2) * (cw + 10)
        y = pages.Y3V + (k // 2) * (ch + 10)
        pg.add(x, y, cw, ch, card(m, label, size=26, **o), key=f"ts_tile{k}")

    # ④ where effort over- or under-runs
    pages.section(pg, pages.Y4, 4, "Where does effort over- or under-run?",
                  "Projects and people, biggest over-run first.")
    pages.legend_note(pg, 984, pages.Y4 + 4, 800, [("Unplanned", UNPLANNED), ("Over-run >120%", RED),
                                                  ("On plan 80–120%", TEAL), ("Under-run <80%", AMBER),
                                                  ("No activity", MUTED)], "ts_band_legend")

    def colour_cols():
        obj = table_style()
        obj["values"] += [cf_font(acc, acc_col), cf_font(var, acc_col), cf_font(band, acc_col)]
        return obj

    pg.add(16, pages.Y4V, 878, pages.H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"),
                    P(sched, "Scheduled h"), P(act, "Approved h"), P(var, "Variance h"), P(acc, "Accuracy"),
                    P(band, "Band")]},
        "Projects — approved versus scheduled hours (via task)", colour_cols(),
        sort=[(var, "Descending")]), key="v_ts_projects")
    pg.add(906, pages.Y4V, 878, pages.H4, chart("tableEx",
        {"Values": [P(DR("Name"), "Resource"), P(DR("Role_Value"), "Role"),
                    P(sched, "Scheduled h"), P(act, "Approved h"), P(var, "Variance h"), P(acc, "Accuracy"),
                    P(M("Timesheet | Submitted Hours"), "Submitted h"), P(band, "Band")]},
        "People — approved versus scheduled hours", colour_cols(),
        sort=[(var, "Descending")]), key="v_ts_people",
        filters=[f_cmp("DimResource", "Generic", 0, False)])

    pages.next_chapter(pg, "timesheets", pages.YNEXT)
    return [pg]
