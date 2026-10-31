"""4d · Resource Detail — "Everything about one person: how loaded, on what, and is their time in?"

Two pages from one builder (_build_page), same content:
  * 4d · Resource Detail (key "resource") — a normal, visible story page with a single-select Resource slicer
    (DimResource[Name]) in the header. No drill-through binding: a drill filter on the same field would stick as a
    page filter and narrow the slicer's own list to the drilled person.
  * Resource Detail (drill-through) (key "resource_dt", pages.HIDDEN_PAGES) — hidden in view mode, drill-through
    target on DimResource[Name] ("Drill through › Resource Detail (drill-through)" from any visual that shows a
    resource), no Resource slicer, a Back button. The binding does not accept the source filter context
    (acceptsFilterContext "None", same shape as the Project One-Pager): only the drilled name travels; the synced
    Year slicer still carries the year.
The Resource slicer is NOT synced and saves no selection, so a fresh visit starts on "all people" and the headline
asks for one name. Visual names stay unique per page: Page.add derives them from the page id.

Model notes (ModeL360Star.bim):
- DimResource filters FactCapacity, FactResourcePlan, FactAssignment, FactTimesheet and FactTimeOff, never DimTask.
  The assigned-task list is driven only by assignment measures (blank where the person has no FactAssignment row
  on the task), so it never cross-joins every task with every resource. Counts use CALCULATE ( …, FactAssignment ):
  the expanded FactAssignment table narrows DimTask to the tasks assigned to the resource(s) in view.
- Utilisation = scheduled hours on project plans ÷ capacity (D-01), via the shared Story measures; those remove
  project filters (organisation-wide), which is right here because the page filters by resource.
- FactTimeOff holds one row per request (Start, End, HoursPerDay); the model's [Resource | TimeOff Hours] sums
  HoursPerDay once per request. Time off here = HoursPerDay × business days from Start to End.
- Resource-plan rows are daily; timesheet periods run Sunday–Saturday; DimDate[WeekStart] is a Monday. Weekly
  visuals use DimDate[WeekStart]; the plan side is limited to whole weeks inside the timesheet window.
- 49 of 51 resources are flagged Generic on this tenant: nothing filters Generic out.
"""
import pages
import pbir
from pbir import (C, M, P, AMBER, GREY, MUTED, NAVY, RED, TEAL, b, card, chart, cf_back, cf_font, f_cmp,
                  f_in, legend, measure_fill, slicer, table_style, uid)
from story_measures import add, OVERDUE_TASK, pct

PX = "Story | Resource · "
FOLDER = "Story\\Resource"
T, D, I = "Text", "Double", "Integer"
KEY = "resource"


def rm(name):
    """Full name of one of this module's measures."""
    return PX + name


# ====================================================================== measures
ONE = "HASONEVALUE ( DimResource[Name] )"


def ident(col):
    """Text of a DimResource column for the one resource in view; '–' when blank or several resources.
    OnePlan choice values can end in a non-breaking space (e.g. 'Project Manager' + U+00A0): strip it."""
    return f"""
VAR _v = IF ( {ONE}, TRIM ( SUBSTITUTE ( SELECTEDVALUE ( DimResource[{col}] ), UNICHAR ( 160 ), " " ) ) )
RETURN IF ( COALESCE ( _v, "" ) = "", "–", _v )"""


# --- identity
add(rm("Name"), T, f'IF ( {ONE}, SELECTEDVALUE ( DimResource[Name] ), "Pick one person" )', folder=FOLDER,
    desc="The resource in view, or a prompt when the slicer leaves several (or none).")
add(rm("Role"), T, ident("Role_Value"), folder=FOLDER)
add(rm("Department"), T, ident("Department_Value"), folder=FOLDER)
add(rm("Manager"), T, ident("Manager_DisplayName"), folder=FOLDER, desc="Resource manager (DimResource[Manager_DisplayName]).")
add(rm("Timesheet Manager"), T, ident("TimesheetManager_DisplayName"), folder=FOLDER,
    desc="Timesheet approver (DimResource[TimesheetManager_DisplayName]).")
add(rm("Type"), T, f"""
IF ( {ONE}, IF ( SELECTEDVALUE ( DimResource[Generic] ) = TRUE (), "Generic", "Named" ), "–" )""", folder=FOLDER,
    desc="Generic (placeholder / role) or named resource. Most resources on this tenant are Generic.")
add(rm("Status"), T, f"""
IF ( {ONE}, IF ( SELECTEDVALUE ( DimResource[Inactive] ) = TRUE (), "Inactive", "Active" ), "–" )""", folder=FOLDER)
add(rm("Utilisation Goal"), D, f"""
VAR _g = IF ( {ONE}, MAX ( DimResource[UtilizationGoal] ) )
RETURN IF ( _g > 0, DIVIDE ( _g, 100 ) )""", "0%", FOLDER,
    "Utilisation goal of the resource (DimResource[UtilizationGoal], stored as a percentage number). Blank when 0 / not set.")
add(rm("Goal Label"), T, f"""
VAR _g = [{rm("Utilisation Goal")}]
RETURN IF ( NOT {ONE}, "–", IF ( ISBLANK ( _g ), "Not set", FORMAT ( _g, "0%" ) ) )""", folder=FOLDER)

# --- time off (FactTimeOff: one row per request)
_TO_DAYS = """
        VAR _s = DATE ( YEAR ( FactTimeOff[Start] ), MONTH ( FactTimeOff[Start] ), DAY ( FactTimeOff[Start] ) )
        VAR _e0 = COALESCE ( FactTimeOff[End], FactTimeOff[Start] )
        VAR _e = DATE ( YEAR ( _e0 ), MONTH ( _e0 ), DAY ( _e0 ) )
        VAR _d =
            CALCULATE ( COUNTROWS ( DimDate ), REMOVEFILTERS ( DimDate ),
                DimDate[Date] >= _s, DimDate[Date] <= _e, DimDate[IsBusinessDay] = TRUE () )"""
add(rm("Time Off Days"), D, f"""
SUMX ( FactTimeOff,{_TO_DAYS}
        RETURN _d
)""", "#,##0.#", FOLDER, "Business days covered by the time-off requests in view (Start to End, inclusive).")
add(rm("Time Off Hours"), D, f"""
SUMX ( FactTimeOff,{_TO_DAYS}
        RETURN COALESCE ( FactTimeOff[HoursPerDay], 0 ) * _d
)""", "#,##0", FOLDER,
    "Time-off hours = hours per day × business days from Start to End of each request (FactTimeOff, any status). "
    "The model's [Resource | TimeOff Hours] counts hours per day only once per request.")

# --- assigned tasks (FactAssignment -> DimTask). Every measure is blank where the resource(s) in view have no
# assignment on the task, so a task list next to a resource filter never becomes tasks × resources.
_ASSIGNED = "NOT ISEMPTY ( FactAssignment )"
add(rm("Task Units"), D, f"""
IF ( {_ASSIGNED}, DIVIDE ( SUM ( FactAssignment[Units] ), 100 ) + 0 )""", "0%", FOLDER,
    "Assignment units on the task (100% = full time) for the resource(s) in view; blank when not assigned. "
    "Drives the rows of the assigned-task list.")
add(rm("Task Days Overdue"), D, f"""
IF ( {_ASSIGNED}, [Story | Days Overdue] )""", "#,##0", FOLDER,
    "Days past the finish date (Story | Days Overdue definition) for tasks assigned to the resource(s) in view.")
add(rm("Task Due Colour"), T, f"""
IF ( {_ASSIGNED}, [Story | Due Colour] )""", folder=FOLDER + "\\Colours")
_OPEN = ('DimTask[WorkType] = "Tasks" && DimTask[Leaf] = TRUE () && NOT ISBLANK ( DimTask[ProjectKey] ) '
         '&& DimTask[PercentDone] < 100 && DimTask[Status] <> "Completed"')
add(rm("Open Tasks"), I, f"""
CALCULATE ( COUNTROWS ( FILTER ( DimTask, {_OPEN} ) ), FactAssignment ) + 0""", "#,##0", FOLDER,
    "Open leaf project tasks (under 100%, not Completed) assigned to the resource(s) in view.")
add(rm("Overdue Tasks"), I, """
CALCULATE ( [Story | Overdue Tasks], FactAssignment ) + 0""", "#,##0", FOLDER,
    "Story | Overdue Tasks (open leaf project tasks past their finish date) assigned to the resource(s) in view.")

# --- is their time in (weekly; whole Monday weeks inside the timesheet window)
add(rm("Scheduled In Timesheet Weeks"), D, """
VAR _from = CALCULATE ( MIN ( FactTimesheet[PeriodStart] ), REMOVEFILTERS () )
VAR _to = CALCULATE ( MAX ( FactTimesheet[PeriodEnd] ), REMOVEFILTERS () )
RETURN
    IF ( NOT ISBLANK ( _from ),
        CALCULATE ( [Story | Scheduled Hours],
            KEEPFILTERS ( DimDate[WeekStart] >= _from && DimDate[WeekStart] <= _to ) ) )""", "#,##0", FOLDER,
    "Scheduled hours on project plans (Story | Scheduled Hours) in the whole weeks inside the timesheet window "
    "(first timesheet period start to last period end in the model) — the plan side of 'is the time in?'.")
add(rm("Time In %"), D, f"""
DIVIDE ( [Timesheet | Actual Hours], [{rm("Scheduled In Timesheet Weeks")}] )""", "0%", FOLDER,
    "Approved timesheet project hours ÷ scheduled hours in the same weeks.")

# --- headline
add(rm("Headline"), T, f"""
VAR _n = SELECTEDVALUE ( DimResource[Name] )
VAR _c = [Capacity | Resource Capacity]
VAR _s = [Story | Scheduled Hours]
VAR _u = [Story | Utilisation %]
VAR _g = [{rm("Utilisation Goal")}]
VAR _mo = [Story | Months Over 100%]
VAR _f = [Story | Free Capacity (h)]
VAR _ot = [{rm("Open Tasks")}]
VAR _od = [{rm("Overdue Tasks")}]
VAR _a = [Timesheet | Actual Hours]
VAR _sw = [{rm("Scheduled In Timesheet Weeks")}]
VAR _to = [{rm("Time Off Hours")}]
VAR _role = [{rm("Role")}]
VAR _dept = [{rm("Department")}]
VAR _who = _n & IF ( _role = "–" && _dept = "–", "", " (" & IF ( _role = "–", "", _role )
    & IF ( _role <> "–" && _dept <> "–", ", ", "" ) & IF ( _dept = "–", "", _dept ) & ")" )
VAR _action =
    SWITCH ( TRUE (),
        _od > 0, "Action: clear or re-plan the overdue tasks.",
        _mo > 0, "Action: move work out of the months above 100%.",
        COALESCE ( _sw, 0 ) > 0 && COALESCE ( _a, 0 ) = 0, "Action: chase the missing timesheets.",
        COALESCE ( _c, 0 ) > 0 && COALESCE ( _u, 0 ) < 0.5, "Action: offer the free capacity to the pipeline.",
        "No action needed." )
RETURN
    IF ( NOT {ONE},
        IF ( ISEMPTY ( VALUES ( DimResource[Name] ) ),
            "No resource in view — clear the filters or pick another person.",
            "Pick one person in the Resource slicer, or right-click a resource on any page and choose "
                & "Drill through › Resource Detail (drill-through)." ),
        _who & ": "
            & IF ( COALESCE ( _c, 0 ) = 0, "no capacity calendar in this period, " & FORMAT ( COALESCE ( _s, 0 ), "#,0" )
                    & " h scheduled on project plans. ",
                FORMAT ( _c, "#,0" ) & " h of capacity, " & FORMAT ( COALESCE ( _s, 0 ), "#,0" )
                    & " h scheduled on project plans  →  " & {pct("_u")} & " utilised"
                    & IF ( ISBLANK ( _g ), "", " (goal " & FORMAT ( _g, "0%" ) & ")" )
                    & "; above 100% in " & FORMAT ( _mo, "0" ) & " month(s), " & FORMAT ( COALESCE ( _f, 0 ), "#,0" )
                    & " h still free. " )
            & FORMAT ( _ot, "0" ) & " open task(s) assigned, " & FORMAT ( _od, "0" ) & " overdue. "
            & IF ( ISBLANK ( _a ) && COALESCE ( _sw, 0 ) = 0, "No timesheet hours and nothing scheduled in the timesheet weeks. ",
                FORMAT ( COALESCE ( _a, 0 ), "#,0" ) & " approved timesheet h against " & FORMAT ( COALESCE ( _sw, 0 ), "#,0" )
                    & " h scheduled in the same weeks. " )
            & IF ( _to > 0, FORMAT ( _to, "#,0" ) & " h of time off booked. ", "" )
            & _action )""", folder="Story\\Headlines", desc="One-sentence briefing on the resource in view.")


# ====================================================================== page helpers (local)
def add_drillthrough(pg, field, key):
    """Drill-through pageBinding on one field — the shape of ext_project.binding_page (as Desktop saves it):
    a Drillthrough-created page filter plus the binding that points at it."""
    ent = field["Column"]["Expression"]["SourceRef"]["Entity"]
    prop = field["Column"]["Property"]
    fname = uid("bind-filter", key, ent, prop)
    pg.page.setdefault("filterConfig", {"filters": []})["filters"].append(
        {"name": fname, "field": field, "type": "Categorical", "howCreated": "Drillthrough"})
    pg.page["pageBinding"] = {"name": uid("bind", key), "type": "Drillthrough",
                              "parameters": [{"name": uid("bind-param", key), "boundFilter": fname, "fieldExpr": field}],
                              # "Keep all filters" off: only the drilled DimResource[Name] travels with the drill.
                              "acceptsFilterContext": "None"}


def resource_slicer(field):
    """Single-select dropdown, no 'Select all'. Not synced: the pick belongs to this page only."""
    v = slicer(field, "Resource", sync=False)
    v["objects"]["selection"] = [{"properties": {"strictSingleSelect": b(True), "selectAllCheckboxEnabled": b(False)}}]
    return v


# ====================================================================== pages
DT_KEY = "resource_dt"  # hidden drill-through twin (pages.HIDDEN_PAGES)


def build():
    """4d (visible, slicer only) plus its hidden drill-through twin with the same content."""
    pg = _build_page(KEY, drill=False)
    dt = _build_page(DT_KEY, drill=True)
    # hidden pages are left out of pages.build_all's story-page passes; give the twin the same treatment as 4d
    pages.filter_real_projects([dt])
    pages.attach_tooltips([dt])
    return [pg, dt]


def _build_page(key, drill):
    from ext_project import back_button  # Back-type action button (module already imported by extensions)
    DP, DR, DT, MONTH = pages.DP, pages.DR, pages.DT, pages.MONTH
    W = pages.W
    WEEK = C("DimDate", "WeekStart")
    area, question = "RESOURCE", "HOW LOADED, ON WHAT, TIME IN?"
    year = [(C("DimDate", "Year"), "Year")]
    if not drill:
        pg = pages.analytic_page(
            key, area, question,
            "Everything about one person. Pick a name, or right-click a resource anywhere › Drill through › "
            "Resource Detail (drill-through).",
            year, rm("Headline"))
        # the Resource slicer sits left of the (synced) Year slicer that pages.header placed at the right edge
        pg.add(W - 16 - 188 + 8 - 10 - 320, 10, 320, 62, resource_slicer(DR("Name")), key="slicer_resource")
    else:
        pg = pbir.Page(pages.PID[key], dict(pages.HIDDEN_PAGES)[key], W, pages.TALL, background_image=pages.BG_TALL)
        pages.header(pg, area, question,
                     "Drill-through page: only the person travels with the drill; the synced Year slicer sets the "
                     "year. ‹ Back returns to the page you came from.", year)
        # header's first visual is the home icon: on a drill-through page it goes back to the source page instead
        pg.visuals[0]["visual"] = back_button()
        pg.add(16, 84, 1768, 56, pbir.headline(rm("Headline")), key="headline")
        add_drillthrough(pg, DR("Name"), key)
        pg.page["visibility"] = "HiddenInViewMode"

    # vertical rhythm: the standard 1800×1800 grid, shifted down by DY for the identity strip in ①
    DY = 64
    y2, y2v, h2 = pages.Y2 + DY, pages.Y2V + DY, pages.H2
    y3, y3v, h3 = pages.Y3 + DY, pages.Y3V + DY, pages.H3 - 44
    y4, y4v = pages.Y4 + 20, pages.Y4V + 20
    h4 = pages.YNEXT - 16 - y4v

    # ① identity + pulse
    pages.section(pg, pages.Y1, 1, "Who is this, and how loaded?",
                  "Utilisation = scheduled hours on project plans ÷ capacity, across all projects. "
                  "Approved hours exclude time off; time off = business days × hours per day.")
    iy, ih = pages.Y1K, 62
    pg.add(16, iy, 360, ih, card(rm("Name"), "Resource", size=16), key="id_name")
    ident_cards = [("Role", "Role"), ("Department", "Department"), ("Manager", "Resource manager"),
                   ("Timesheet Manager", "Timesheet manager"), ("Type", "Generic / named"), ("Status", "Active / inactive"),
                   ("Goal Label", "Utilisation goal")]
    w = (1768 - 360 - 10 * len(ident_cards)) / len(ident_cards)
    for k, (m, label) in enumerate(ident_cards):
        pg.add(round(386 + k * (w + 10), 2), iy, round(w, 2), ih, card(rm(m), label, size=13), key=f"id{k}")
    pages.kpi_row(pg, iy + ih + 8, [
        ("Capacity | Resource Capacity", "Capacity (h)"),
        ("Story | Scheduled Hours", "Scheduled (h)"),
        ("Story | Committed Hours", "Committed (h)", {"value_colour": TEAL}),
        ("Story | Utilisation %", "Utilisation", {"colour_measure": "Story | Util Colour"}),
        ("Story | Months Over 100%", "Months over 100%", {"value_colour": RED}),
        ("Story | Free Capacity (h)", "Free capacity (h)", {"value_colour": TEAL}),
        ("Timesheet | Actual Hours", "Approved timesheet (h)"),
        (rm("Time Off Hours"), "Time off (h)", {"value_colour": AMBER}),
    ], h=y2 - (iy + ih + 8) - 10)

    # ② load over time
    pages.section(pg, y2, 2, "How loaded, month by month?",
                  "Columns = capacity; lines = scheduled and committed hours on project plans, one axis. "
                  "Bottom row: utilisation per month, rolling 12 months.")
    pages.legend_note(pg, 1084, y2 + 4, 700, [("Over 100%", "#8E1B12"), ("80–100%", TEAL), ("50–80%", "#9A6B00"),
                                              ("Under 50%", MUTED)], "util_legend")
    combo_h = h2 - 122
    pg.add(16, y2v, 1768, combo_h, pages.people_combo("Capacity vs scheduled and committed hours per month"),
           key="v_load")
    util = M("Story | Utilisation %")
    obj = table_style(9)
    obj["values"] += [cf_back(util, "Story | Util Cell Colour")]
    pg.add(16, y2v + combo_h + 10, 1768, h2 - combo_h - 10, chart("pivotTable",
        {"Rows": [P(DR("Name"), "Resource", True)], "Columns": [P(MONTH, "Month", True)], "Values": [P(util, "Util.")]},
        "Utilisation by month (scheduled ÷ capacity) — same colours as the heat map", obj), key="v_util_row",
        filters=[pbir.f_between("DimDate", "RelativeMonth", -3, 8)])

    # ③ on what
    pages.section(pg, y3, 3, "On what?",
                  "Scheduled hours per project and month (project plans, rolling 12 months), and the open tasks "
                  "assigned to this person — overdue first.")
    sch_p = M("Story | Project Scheduled Hours")
    pg.add(16, y3v, 878, h3, chart("pivotTable",
        {"Rows": [P(DP("Name"), "Project", True)], "Columns": [P(MONTH, "Month", True)],
         "Values": [P(sch_p, "Scheduled h")]},
        "Scheduled hours — project × month", table_style(9)), key="v_proj_month",
        filters=[pbir.f_between("DimDate", "RelativeMonth", -3, 8)])
    od, units = M(rm("Task Days Overdue")), M(rm("Task Units"))
    obj = table_style(9)
    obj["values"] += [cf_font(DT("EndDate"), rm("Task Due Colour")), cf_font(od, rm("Task Due Colour"))]
    # Rows exist only where Task Units / Task Days Overdue are non-blank, i.e. the person has an assignment on the
    # task (no tasks × resources cross join). The column filters narrow it to open leaf project tasks.
    pg.add(906, y3v, 878, h3, chart("tableEx",
        {"Values": [P(DT("Name"), "Task"), P(DP("Name"), "Project"), P(DT("EndDate"), "Due"),
                    P(od, "Days overdue"), P(DT("PercentDone"), "% done"), P(DT("Status"), "Status"),
                    P(units, "Units")]},
        "Assigned open tasks — overdue first, then by due date", obj,
        sort=[(od, "Descending"), (DT("EndDate"), "Ascending")]), key="v_tasks",
        filters=[f_in("DimTask", "WorkType", ["Tasks"]), f_in("DimTask", "Leaf", [True]),
                 f_cmp("DimTask", "PercentDone", 3, 100), f_in("DimTask", "Status", ["Completed"], exclude=True),
                 pages.PROJECT_TASKS])

    # ④ is their time in + time off
    pages.section(pg, y4, 4, "Is their time in — and when are they away?",
                  "Weekly timesheet hours by status, approved project hours against scheduled hours for the same "
                  "(Monday) weeks, and the time-off requests.")
    appr, wait, draft = M("Timesheet | Approved Hours"), M("Timesheet | Awaiting Approval Hours"), M("Timesheet | Draft Hours")
    pg.add(16, y4v, 590, h4, chart("columnChart",
        {"Category": [P(WEEK, "Week")], "Y": [P(appr, "Approved"), P(wait, "Awaiting approval"), P(draft, "Draft")]},
        "Timesheet hours per week by status (time off included)",
        {"dataPoint": [measure_fill(appr, TEAL), measure_fill(wait, AMBER), measure_fill(draft, GREY)],
         "legend": legend("Top")}, sort=[(WEEK, "Ascending")]), key="v_ts_status")
    sw, act = M(rm("Scheduled In Timesheet Weeks")), M("Timesheet | Actual Hours")
    pg.add(616, y4v, 590, h4, chart("clusteredColumnChart",
        {"Category": [P(WEEK, "Week")], "Y": [P(sw, "Scheduled (h)"), P(act, "Approved project (h)")]},
        "Approved project hours versus scheduled, per week",
        {"dataPoint": [measure_fill(sw, "#C9CED8"), measure_fill(act, NAVY)], "legend": legend("Top")},
        sort=[(WEEK, "Ascending")]), key="v_ts_vs_plan")
    to = M(rm("Time Off Hours"))
    pg.add(1216, y4v, 568, h4, chart("tableEx",
        {"Values": [P(C("FactTimeOff", "TimeOffCategory"), "Category"), P(C("FactTimeOff", "Start"), "Start"),
                    P(C("FactTimeOff", "End"), "End"), P(to, "Hours"), P(C("FactTimeOff", "Status"), "Status"),
                    P(C("FactTimeOff", "ApproverName"), "Approver")]},
        "Time off — latest first", table_style(9), sort=[(C("FactTimeOff", "Start"), "Descending")]), key="v_timeoff")

    if not drill:
        pages.next_chapter(pg, key, pages.YNEXT)
    else:
        pg.add(16, pages.YNEXT, 180, 36, back_button(icon=False), key="back")
        pg.add(206, pages.YNEXT, 220, 36, pbir.nav_button("‹  Story navigator", pages.PID["home"], "Back to the home page",
                                                          fill="#FFFFFF", hover=pbir.ORANGE_SOFT, press=pbir.ORANGE,
                                                          font=NAVY, outline=pbir.BORDER), key="home_btn")
    return pg
