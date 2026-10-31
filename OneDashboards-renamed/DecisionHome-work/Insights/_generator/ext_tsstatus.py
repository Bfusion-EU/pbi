"""4c · Timesheet Status — are the timesheets in and approved: who is missing, who is waiting on whom?

Sibling of 4b (Timesheets vs Plan), which compares approved hours with the plan. This page is only about the
timesheet workflow: one cell per person and timesheet period, the approval queue and the audit trail.

Model notes (checked in ModeL360Star.bim and against the live model, 2026-10-26):
- FactTimesheet is one row per timesheet LINE x entry day. TimesheetStatus is a LINE status (Draft / Approved),
  not a sheet status: one timesheet can hold approved lines plus empty (0 h) draft lines. The cell status
  therefore looks at lines with hours, and only falls back to "Draft" when a sheet has nothing else.
- IsApproved = TimeApproved = 10 AND PlanApproved = 10. A submitted line with TimeApproved = 10 but
  PlanApproved <> 10 waits on the plan owner; TimeApproved <> 10 waits on the timesheet manager.
- Timesheet periods run Sunday to Saturday (FactTimesheet[PeriodStart] is a Sunday); DimDate[WeekStart] is a
  Monday. The grid uses DimDate[WeekStart] so that weeks in which NOBODY logged time still get a column, and
  maps each week to the period that starts the day before (WeekStart - 1).
- "Missing" reuses the model's [Timesheet | Resources Missing Time] rule: a named (non-generic), active resource
  with committed hours ([Capacity | Total Hours Committed] > 0) who has no timesheet. Committed hours are
  month-anchored, so a period is expected when the resource has committed hours in a month the period touches.
  A period only counts as missing once it is complete plus two days' grace (due by the Monday after).
- The reference date is the model refresh date (RefreshTime), falling back to TODAY().
- FactTimesheetAudit has one row per workflow action (Submit / Approve / Recall / Unlock). It has no
  relationship on TimesheetBK, so audit look-ups use the BK as a filter value.
"""
import pages
import pbir
from pbir import (C, M, P, AMBER, GREY, NAVY, RED, TEAL, b, card, chart, cf_back, cf_font, labels_on, legend,
                  measure_fill, n, series_colours, table_style)
from story_measures import add

PFX = "Story | TS Status · "
FOLDER = "Story\\Timesheet Status"
COLOURS = "Story\\Colours"
T, D, I = "Text", "Double", "Integer"
RETURNED = "#8E1B12"
GRACE_DAYS = 2  # a Sun-Sat period is due by the Monday after it ends


def _m(name):
    return PFX + name


def _r(name):
    return f"[{_m(name)}]"


# The timesheet periods behind the DimDate weeks in the filter context (period = WeekStart - 1).
PERIODS = 'TREATAS ( SELECTCOLUMNS ( VALUES ( DimDate[WeekStart] ), "@p", DimDate[WeekStart] - 1 ), FactTimesheet[PeriodStart] )'


def _per_period(expr):
    """Evaluate a FactTimesheet expression by timesheet PERIOD instead of entry date."""
    return f"CALCULATE ( {expr}, REMOVEFILTERS ( DimDate ), {PERIODS} )"


# ------------------------------------------------------------------ window
add(_m("Reference Date"), "DateTime", """
VAR _r = MAX ( RefreshTime[Last Refreshed (Belgium Time)] )
RETURN IF ( ISBLANK ( _r ), TODAY (), DATE ( YEAR ( _r ), MONTH ( _r ), DAY ( _r ) ) )""",
    "dd mmm yyyy", FOLDER, "Date of the last model refresh (TODAY() if unknown). Waiting days and 'missing' count up to here.")

add(_m("Window Start"), "DateTime", """
CALCULATE ( MIN ( FactTimesheet[PeriodStart] ), REMOVEFILTERS () )""",
    "dd mmm yyyy", FOLDER, "First timesheet period in the model (ignores all filters). Nothing before it is 'missing'.")

# ------------------------------------------------------------------ the cell: one resource x one week
add(_m("Status Code"), I, f"""
VAR _ws = SELECTEDVALUE ( DimDate[WeekStart] )
VAR _ps = _ws - 1
VAR _ref = {_r('Reference Date')}
RETURN
    IF (
        NOT ISBLANK ( _ws ) && HASONEVALUE ( DimResource[ResourceKey] )
            && _ps >= {_r('Window Start')} && _ps <= _ref,
        VAR _lines = CALCULATETABLE ( FactTimesheet, REMOVEFILTERS ( DimDate ), FactTimesheet[PeriodStart] = _ps )
        VAR _n = COUNTROWS ( _lines )
        VAR _appr = COUNTROWS ( FILTER ( _lines, FactTimesheet[IsApproved] = 1 && FactTimesheet[Hours] > 0 ) )
        VAR _wait = COUNTROWS ( FILTER ( _lines,
            FactTimesheet[IsSubmitted] = 1 && FactTimesheet[IsApproved] = 0 && FactTimesheet[Hours] > 0 ) )
        VAR _draft = FILTER ( _lines, FactTimesheet[IsSubmitted] = 0 && FactTimesheet[Hours] > 0 )
        VAR _bounced = CALCULATETABLE ( VALUES ( FactTimesheetAudit[TimesheetBK] ), REMOVEFILTERS ( DimDate ),
            FactTimesheetAudit[Action] IN {{ "Recall", "Unlock" }} )
        VAR _ret = COUNTROWS ( FILTER ( _draft, FactTimesheet[TimesheetBK] IN _bounced ) )
        VAR _due = _ps + 6 + {GRACE_DAYS} < _ref
        VAR _named = COUNTROWS ( FILTER ( DimResource, DimResource[Generic] = FALSE () && DimResource[Inactive] = FALSE () ) ) > 0
        VAR _committed = CALCULATE ( [Capacity | Total Hours Committed], REMOVEFILTERS ( DimDate ),
            DimDate[Date] >= EOMONTH ( _ps, -1 ) + 1, DimDate[Date] <= EOMONTH ( _ps + 6, 0 ) )
        RETURN
            SWITCH (
                TRUE (),
                _ret > 0, 4,
                COUNTROWS ( _draft ) > 0, 3,
                _wait > 0, 2,
                _appr > 0, 1,
                _n > 0, 3,
                _due && _named && _committed > 0, 5
            )
    )""", "0", FOLDER,
    "Timesheet status of one resource in one week: 1 Approved, 2 Awaiting approval, 3 Draft, 4 Returned "
    "(recalled / unlocked and not resubmitted), 5 Missing (committed work, no timesheet, period overdue). "
    "Blank = nothing expected. Only meaningful for one resource and one week.")

add(_m("Status"), T, f"""
SWITCH ( {_r('Status Code')}, 1, "Approved", 2, "Awaiting", 3, "Draft", 4, "Returned", 5, "Missing" )""",
    folder=FOLDER, desc="Approved / Awaiting (submitted, not yet approved) / Draft / Returned / Missing.")

add(_m("Status Colour"), T, f"""
SWITCH ( {_r('Status Code')}, 1, "{TEAL}", 2, "{AMBER}", 3, "#C9CED8", 4, "{RETURNED}", 5, "{RED}" )""",
    folder=COLOURS, desc="Cell background per status; blank when there is no status (no phantom cells).")

add(_m("Status Font"), T, f"""
VAR _c = {_r('Status Code')}
RETURN IF ( NOT ISBLANK ( _c ), IF ( _c = 2 || _c = 3, "{NAVY}", "#FFFFFF" ) )""", folder=COLOURS)


# ------------------------------------------------------------------ cell counts over resource x week
GRID = f"""
    VAR _from = {_r('Window Start')}
    VAR _to = {_r('Reference Date')}
    VAR _grid = CROSSJOIN (
        FILTER ( VALUES ( DimResource[ResourceKey] ), NOT ISBLANK ( DimResource[ResourceKey] ) ),
        FILTER ( VALUES ( DimDate[WeekStart] ), DimDate[WeekStart] - 1 >= _from && DimDate[WeekStart] - 1 <= _to )
    )"""


def _cells(cond, desc, name):
    add(_m(name), I, f"""{GRID}
    RETURN IF ( ISEMPTY ( _grid ), BLANK (), COALESCE ( SUMX ( _grid, VAR _c = {_r('Status Code')} RETURN IF ( {cond}, 1 ) ), 0 ) )""",
        "#,##0", FOLDER, desc)


_cells("_c = 1", "Resource-weeks whose timesheet is fully approved.", "Approved Weeks")
_cells("_c = 2", "Resource-weeks with submitted hours still awaiting approval.", "Awaiting Weeks")
_cells("_c = 3", "Resource-weeks with a timesheet still in draft.", "Draft Weeks")
_cells("_c = 4", "Resource-weeks with a timesheet that was recalled or unlocked and not resubmitted.", "Returned Weeks")
_cells("_c = 5", "Missing resource-weeks: one per person and overdue week with committed work but no timesheet. "
       "Counts weeks, not people (4b's 'People who booked no time' counts people).",
       "Missing Timesheets")
_cells("NOT ISBLANK ( _c )", "Resource-weeks where a timesheet exists or is expected.", "Tracked Weeks")

add(_m("Approved Weeks %"), D, f"DIVIDE ( {_r('Approved Weeks')}, {_r('Tracked Weeks')} )", "0%", FOLDER,
    "Share of tracked resource-weeks that are fully approved.")

# ------------------------------------------------------------------ hours by status, per timesheet period
add(_m("Approved Hours"), D, _per_period("[Timesheet | Approved Hours]"), "#,##0.0", FOLDER,
    "Approved timesheet hours, by timesheet period (time off included).")
add(_m("Awaiting Manager Hours"), D, _per_period(
    "CALCULATE ( [Timesheet | Hours], KEEPFILTERS ( FactTimesheet[IsSubmitted] = 1 ), "
    "KEEPFILTERS ( FactTimesheet[TimeApproved] <> 10 ) )"), "#,##0.0", FOLDER,
    "Submitted hours the timesheet manager has not approved yet, by timesheet period.")
add(_m("Awaiting Plan Owner Hours"), D, _per_period(
    "CALCULATE ( [Timesheet | Hours], KEEPFILTERS ( FactTimesheet[IsSubmitted] = 1 ), "
    "KEEPFILTERS ( FactTimesheet[TimeApproved] = 10 ), KEEPFILTERS ( FactTimesheet[PlanApproved] <> 10 ) )"),
    "#,##0.0", FOLDER,
    "Submitted hours approved by the timesheet manager but not yet by the plan owner, by timesheet period.")
add(_m("Draft Hours"), D, _per_period("[Timesheet | Draft Hours]"), "#,##0.0", FOLDER,
    "Hours on draft (not submitted) lines, by timesheet period.")

# ------------------------------------------------------------------ KPIs
add(_m("On-Time %"), D, f"""
VAR _t = CALCULATETABLE (
    SUMMARIZE ( FactTimesheet, FactTimesheet[TimesheetBK], FactTimesheet[PeriodEnd] ),
    KEEPFILTERS ( FactTimesheet[IsSubmitted] = 1 )
)
VAR _x = ADDCOLUMNS ( _t, "@first",
    VAR _bk = FactTimesheet[TimesheetBK]
    RETURN CALCULATE ( MIN ( FactTimesheetAudit[DateOfAction] ), REMOVEFILTERS ( DimDate ),
        REMOVEFILTERS ( FactTimesheetAudit ), FactTimesheetAudit[TimesheetBK] = _bk,
        FactTimesheetAudit[Action] = "Submit" ) )
VAR _known = FILTER ( _x, NOT ISBLANK ( [@first] ) )
RETURN DIVIDE ( COUNTROWS ( FILTER ( _known, [@first] < FactTimesheet[PeriodEnd] + {GRACE_DAYS + 1} ) ), COUNTROWS ( _known ) )""",
    "0%", FOLDER,
    f"Submitted timesheets whose FIRST submit came by the Monday after the period ended (period end + {GRACE_DAYS} days). "
    "Timesheets without a Submit in the audit trail are left out.")

add(_m("Draft Timesheets"), I, """
COUNTROWS (
    FILTER (
        VALUES ( FactTimesheet[TimesheetBK] ),
        CALCULATE ( SUM ( FactTimesheet[Hours] ), KEEPFILTERS ( FactTimesheet[IsSubmitted] = 0 ) ) > 0
            || CALCULATE ( COUNTROWS ( FactTimesheet ), KEEPFILTERS ( FactTimesheet[IsSubmitted] = 1 ) ) = 0
    )
) + 0""", "#,##0", FOLDER,
    "Timesheets not submitted: draft lines with hours, or nothing submitted at all. Empty draft lines inside a "
    "submitted timesheet do not count (the model's [Timesheet | Draft Timesheets] does count them).")

add(_m("Awaiting Timesheets"), I, "COALESCE ( [Timesheet | Timesheets Awaiting Approval], 0 )", "#,##0", FOLDER,
    "Timesheets with submitted lines not yet approved (0 instead of blank).")
add(_m("Awaiting Hours"), D, "COALESCE ( [Timesheet | Awaiting Approval Hours], 0 )", "#,##0.0", FOLDER,
    "Submitted hours not yet approved (0 instead of blank).")

add(_m("Rework Actions"), I, "COALESCE ( [Timesheet | Recalls], 0 ) + COALESCE ( [Timesheet | Unlocks], 0 )",
    "#,##0", FOLDER, "Recalls plus unlocks in the audit trail: timesheets that went back for rework.")

add(_m("Approval Lag"), T, """
VAR _a = [Timesheet | Avg Approval Lag (days)]
VAR _x = [Timesheet | Max Approval Lag (days)]
RETURN IF ( ISBLANK ( _a ), "–", FORMAT ( _a, "0.0" ) & " / " & FORMAT ( _x, "0.0" ) & " d" )""",
    folder=FOLDER, desc="Average / maximum days from submit to approve (model's ApprovalLagDays).")

add(_m("Oldest Waiting Days"), I, f"""
VAR _lines = CALCULATETABLE (
    SUMMARIZE ( FactTimesheet, FactTimesheet[TimesheetLineBK], FactTimesheet[PeriodEnd] ),
    KEEPFILTERS ( FactTimesheet[IsSubmitted] = 1 ),
    KEEPFILTERS ( FactTimesheet[IsApproved] = 0 )
)
VAR _since = MINX ( _lines,
    VAR _l = FactTimesheet[TimesheetLineBK]
    VAR _s = CALCULATE ( MAX ( FactTimesheetAudit[DateOfAction] ), REMOVEFILTERS ( DimDate ),
        REMOVEFILTERS ( FactTimesheetAudit ), FactTimesheetAudit[TimesheetLineBK] = _l,
        FactTimesheetAudit[Action] = "Submit" )
    RETURN COALESCE ( _s, FactTimesheet[PeriodEnd] ) )
RETURN IF ( NOT ISBLANK ( _since ), INT ( {_r('Reference Date')} - _since ) )""", "#,##0", FOLDER,
    "Days the oldest unapproved submitted line has been waiting since its last Submit (period end if no audit row).")

add(_m("No Manager People"), I, """
COUNTROWS (
    FILTER (
        DimResource,
        DimResource[Generic] = FALSE ()
            && DimResource[Inactive] = FALSE ()
            && ( ISBLANK ( DimResource[TimesheetManager] ) || DimResource[TimesheetManager] = "" )
            && ( COALESCE ( [Timesheet | Submitted Hours], 0 ) > 0 || [Capacity | Total Hours Committed] > 0 )
    )
) + 0""", "#,##0", FOLDER,
    "Active named people who book time or have committed work but no timesheet manager in OnePlan.")

# queue columns: blank instead of 0 so that only people with open work get a row
add(_m("Queue Drafts"), I, f"VAR _d = {_r('Draft Timesheets')} RETURN IF ( _d > 0, _d )", "#,##0", FOLDER,
    "Draft (unsubmitted) timesheets; blank when none.")
add(_m("Queue Missing"), I, f"VAR _m = {_r('Missing Timesheets')} RETURN IF ( _m > 0, _m )", "#,##0", FOLDER,
    "Missing resource-weeks; blank when none.")

add(_m("Actions"), I, "SUM ( FactTimesheetAudit[ActionCount] )", "#,##0", FOLDER,
    "Workflow actions in the timesheet audit trail.")

add(_m("Action Colour"), T, f"""
SWITCH ( SELECTEDVALUE ( FactTimesheetAudit[Action] ), "Approve", "{TEAL}", "Submit", "{NAVY}",
    "Recall", "{RED}", "Unlock", "#9A6B00", "#666666" )""", folder=COLOURS)

add(_m("On-Time Colour"), T, f"""
VAR _p = {_r('On-Time %')}
RETURN IF ( ISBLANK ( _p ), "{GREY}", IF ( _p >= 0.9, "{TEAL}", IF ( _p >= 0.7, "{AMBER}", "{RED}" ) ) )""",
    folder=COLOURS)
add(_m("Approval Colour"), T, f"""
VAR _p = [Timesheet | Approval %]
RETURN IF ( ISBLANK ( _p ), "{GREY}", IF ( _p >= 0.95, "{TEAL}", IF ( _p >= 0.8, "{AMBER}", "{RED}" ) ) )""",
    folder=COLOURS)
add(_m("Missing Colour"), T, f"""
IF ( COALESCE ( {_r('Missing Timesheets')}, 0 ) > 0, "{RED}", "{TEAL}" )""", folder=COLOURS)

add(_m("Headline"), T, f"""
VAR _tracked = {_r('Tracked Weeks')}
VAR _ok = COALESCE ( {_r('Approved Weeks')}, 0 )
VAR _miss = COALESCE ( {_r('Missing Timesheets')}, 0 )
VAR _wait = {_r('Awaiting Timesheets')}
VAR _draft = {_r('Draft Timesheets')}
VAR _ret = COALESCE ( {_r('Returned Weeks')}, 0 )
VAR _ontime = {_r('On-Time %')}
VAR _oldest = {_r('Oldest Waiting Days')}
VAR _who = MAXX ( TOPN ( 1, FILTER ( ADDCOLUMNS ( VALUES ( DimResource[Name] ), "@m", {_r('Missing Timesheets')} ), [@m] > 0 ),
    [@m], DESC, DimResource[Name], ASC ), DimResource[Name] )
VAR _appr = MAXX ( TOPN ( 1, FILTER ( ADDCOLUMNS ( VALUES ( DimResource[TimesheetManager_DisplayName] ), "@w",
    [Timesheet | Awaiting Approval Hours] ), [@w] > 0 ), [@w], DESC ), DimResource[TimesheetManager_DisplayName] )
RETURN
    IF (
        ISBLANK ( _tracked ) || _tracked = 0,
        "No timesheets expected or logged in this selection.",
        _ok & " of " & _tracked & " resource-weeks fully approved"
            & IF ( NOT ISBLANK ( _ontime ), "; " & FORMAT ( _ontime, "0%" ) & " of timesheets submitted on time", "" ) & ". "
            & SWITCH (
                TRUE (),
                _miss > 0, _miss & " missing resource-week(s) (committed work, no timesheet)"
                    & IF ( NOT ISBLANK ( _who ), ", most for " & _who, "" ) & ". Action: chase the missing timesheets.",
                _wait > 0, _wait & " timesheet(s) waiting on "
                    & IF ( _appr = "" || ISBLANK ( _appr ), "an approver (no timesheet manager set)", _appr )
                    & IF ( NOT ISBLANK ( _oldest ), ", oldest " & _oldest & " days", "" ) & ". Action: chase the approver.",
                _ret > 0, _ret & " timesheet(s) returned and not resubmitted. Action: get them resubmitted.",
                _draft > 0, _draft & " timesheet(s) still in draft. Action: remind the owners to submit.",
                "Everything is in and approved."
            )
    )""", folder=FOLDER)


# ------------------------------------------------------------------ page
def build():
    DR = pages.DR
    WEEK = C("DimDate", "WeekStart")
    slicers = [(DR("Department_Value"), "Department"), (DR("Role_Value"), "Role"),
               (DR("TimesheetManager_DisplayName"), "Timesheet manager"), (C("DimDate", "Year"), "Year")]
    pg = pages.analytic_page(
        "tsstatus", "TIMESHEET STATUS", "ARE THE TIMESHEETS IN?",
        "Per person and week: approved, waiting, draft, returned or missing — and who has to act next.",
        slicers, _m("Headline"))

    # ① pulse
    pages.section(pg, pages.Y1, 1, "Is the time in and approved?",
                  "On time = first submit by the Monday after the period. Missing = resource-weeks with committed work but no timesheet.")
    pages.kpi_row(pg, pages.Y1K, [
        (_m("On-Time %"), "Submitted on time", {"colour_measure": _m("On-Time Colour")}),
        ("Timesheet | Approval %", "Submitted hours approved", {"colour_measure": _m("Approval Colour")}),
        (_m("Awaiting Timesheets"), "Timesheets awaiting approval", {"value_colour": AMBER}),
        (_m("Awaiting Hours"), "Hours awaiting approval", {"value_colour": AMBER}),
        (_m("Draft Timesheets"), "Drafts not submitted", {"value_colour": "#6B7280"}),
        (_m("Missing Timesheets"), "Missing resource-weeks (no timesheet)", {"colour_measure": _m("Missing Colour")}),
        (_m("Approval Lag"), "Approval lag avg / max", {"size": 20}),
        (_m("Rework Actions"), "Rework (recalls + unlocks)", {"value_colour": RETURNED}),
    ])

    # ② status grid
    status = M(_m("Status"))
    pages.section(pg, pages.Y2, 2, "Who is missing, week by week?",
                  "One cell per person and timesheet period (columns = Monday of the Sun–Sat period).")
    pages.legend_note(pg, 984, pages.Y2 + 4, 800, [("Approved", TEAL), ("Awaiting", AMBER), ("Draft", GREY),
                                                  ("Returned", RETURNED), ("Missing", RED)], "tss_legend")
    obj = table_style(9)
    obj["values"] += [cf_back(status, _m("Status Colour")), cf_font(status, _m("Status Font"))]
    obj["subTotals"] = [{"properties": {"rowSubtotals": b(False), "columnSubtotals": b(False)}}]
    pg.add(16, pages.Y2V, 1768, pages.H2, chart("pivotTable",
        {"Rows": [P(DR("Name"), "Resource", True)], "Columns": [P(WEEK, "Week of", True)],
         "Values": [P(status, "Status")]},
        "Timesheet status grid — resource × week", obj), key="v_tss_grid")

    # ③ status by period + who is waiting on whom
    pages.section(pg, pages.Y3, 3, "Where does the time sit, and who has to act?",
                  "Hours per period by approval step; the queue groups open work by timesheet manager.")
    ap, wm = M(_m("Approved Hours")), M(_m("Awaiting Manager Hours"))
    wp, dr = M(_m("Awaiting Plan Owner Hours")), M(_m("Draft Hours"))
    miss = M(_m("Missing Timesheets"))
    pg.add(16, pages.Y3V, 878, pages.H3, chart("lineStackedColumnComboChart",
        {"Category": [P(WEEK, "Week of")],
         "Y": [P(ap, "Approved"), P(wp, "Awaiting plan owner"), P(wm, "Awaiting manager"), P(dr, "Draft")],
         "Y2": [P(miss, "Missing resource-weeks")]},
        "Hours per timesheet period by status — line = missing resource-weeks",
        {"dataPoint": [measure_fill(ap, TEAL), measure_fill(wp, "#E8C468"), measure_fill(wm, AMBER),
                       measure_fill(dr, "#C9CED8"), measure_fill(miss, RED)],
         "legend": legend("Top"), "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}]},
        sort=[(WEEK, "Ascending")]), key="v_tss_period")
    wait_h, wait_t = M("Timesheet | Awaiting Approval Hours"), M("Timesheet | Timesheets Awaiting Approval")
    qmiss = M(_m("Queue Missing"))
    oldest = M(_m("Oldest Waiting Days"))
    qobj = table_style(9)
    qobj["values"] += [cf_font(qmiss, _m("Missing Colour"))]
    pg.add(906, pages.Y3V, 878, pages.H3, chart("pivotTable",
        {"Rows": [P(DR("TimesheetManager_DisplayName"), "Timesheet manager", True), P(DR("Name"), "Resource", True)],
         "Values": [P(wait_t, "Awaiting sheets"), P(wait_h, "Awaiting h"),
                    P(wm, "Waiting on manager h"), P(wp, "Waiting on plan owner h"), P(oldest, "Oldest wait (d)"),
                    P(M(_m("Queue Drafts")), "Drafts"), P(qmiss, "Missing weeks")]},
        "Approver queue — open work by timesheet manager › resource (blank manager = nobody assigned)", qobj,
        # no Generic filter: the queue counts the same population as the KPI cards above
        sort=[(wait_h, "Descending")]), key="v_tss_queue")

    # ④ workflow trail
    pages.section(pg, pages.Y4, 4, "What happened in the workflow?",
                  "Latest submit / approve / recall / unlock actions from the OnePlan audit trail.")
    act = C("FactTimesheetAudit", "Action")
    actions = M(_m("Actions"))
    tobj = table_style(9)
    tobj["values"] += [cf_font(act, _m("Action Colour")), cf_font(actions, _m("Action Colour"))]
    pg.add(16, pages.Y4V, 1160, pages.H4, chart("tableEx",
        {"Values": [P(C("FactTimesheetAudit", "DateOfAction"), "When"), P(act, "Action"),
                    P(DR("Name"), "Timesheet owner"), P(C("FactTimesheetAudit", "ActionBy"), "Done by"),
                    P(C("DimTask", "Name"), "Task"), P(C("FactTimesheetAudit", "Message"), "Message"),
                    P(C("FactTimesheetAudit", "ApprovalLagDays"), "Lag (d)"), P(actions, "Lines")]},
        "Workflow trail — newest first", tobj,
        sort=[(C("FactTimesheetAudit", "DateOfAction"), "Descending")]), key="v_tss_trail")
    pg.add(1192, pages.Y4V, 592, pages.H4, chart("columnChart",
        {"Category": [P(WEEK, "Week of action")], "Series": [P(act, "Action")], "Y": [P(actions, "Actions")]},
        "Workflow actions per week",
        {"dataPoint": series_colours(act, {"Submit": NAVY, "Approve": TEAL, "Recall": RED, "Unlock": "#9A6B00"}),
         "legend": legend("Top"), "labels": labels_on(False)},
        sort=[(WEEK, "Ascending")]), key="v_tss_actions")

    pages.next_chapter(pg, "tsstatus", pages.YNEXT)
    return [pg]
