"""5b · Gantt View — a Gantt chart drawn with the native matrix visual.

Rows    Portfolio › Program › Project › Task (DimProject + DimTask[Name]), stepped layout.
Columns DimDate[Period] ("Oct-26", sorted by YearMonth) with DimDate[WeekStart] as the drill level.
Value   `Story | Gantt · Bar` — one glyph per period in which the row is active; the cell background
        (`… · Bar Colour`) draws the bar and the font colour (`… · Bar Font`) equals the background,
        so only the coloured cell shows. Milestones show an orange ◆, the current period a │ marker.

DimDate has no relationship with DimTask / DimProject, so every cell compares the period in the
column (MIN / MAX of DimDate[Date]) with the row's start / end:
  task rows     DimTask[StartDate] / [EndDate]  (+ BaselineEndDate, PercentDone, Milestone, Leaf)
  project rows  DimProject[Summary_StartDate] / [Summary_EndDate] (+ Summary_BaselineEndDate)
  higher rows   earliest task start → latest task finish of the tasks below
No iterator runs inside a cell: only MIN / MAX / SELECTEDVALUE over the rows already in context.

Colour logic of a cell (task rows, first match wins)
  completed     teal   — % done = 100 or Status "Completed", or the middle of the cell's overlap lies before the
                         progress point Start + (End − Start) × % done
  late          red    — remaining part of an open task (< 100 % done, Status <> "Completed", as OVERDUE_TASK in
                         story_measures) whose finish date has passed
  baseline slip amber  — remaining part after the baseline finish when the finish moved later
  remaining     navy
  summary task  grey (amber tail when slipped), project bar slate (amber tail), programme / portfolio light grey
  milestone     ◆ in the period of its finish date: orange open, teal done, red late
  today         │ on a peach cell in the current period for rows that are not active there

Sort order: the matrix is sorted by the Bar measure ascending. At the column-total level (no period in
scope) the measure returns a sort key instead of a glyph — task rows "00042" (DimTask[taskorder]), higher
rows the start date "yyyymmdd" — so tasks follow the plan order and projects their start date. Column
subtotals are off, so the key is never displayed.

Grand total: the row with no Portfolio in scope gets nothing (State and Bar are blank there), so the stepped
layout shows no grand-total bar and no grand-total sort key. Every other row — portfolio, programme, project and
task — has the Portfolio in scope and keeps its glyphs and its sort key.
"""
import pages
import pbir
from pbir import C, M, P, b, chart, col_solid, cf_back, cf_font, n, s, i, table_style
from pbir import NAVY, TEAL, AMBER, RED, ORANGE, ORANGE_SOFT, GREY, MUTED, BORDER, INK
from story_measures import add, T, D, I

PFX = "Story | Gantt · "
FOLDER = "Story\\Gantt"

SLATE_BAR = "#5B6B8C"     # project summary bar
ROLLUP_BAR = "#C9CED8"    # programme / portfolio span
WINDOW = (-3, 9)          # DimDate[RelativeMonth] window: 3 months back, 9 ahead (13 month columns)


def m(name):
    return PFX + name


def ref(name):
    return f"[{PFX}{name}]"


# ------------------------------------------------------------------ DAX building blocks
PERIOD_IN_SCOPE = ("ISINSCOPE ( DimDate[Period] ) || ISINSCOPE ( DimDate[WeekStart] ) "
                   "|| ISINSCOPE ( DimDate[MonthStart] )")
# Every row except the matrix grand total has the top row level (Portfolio) in scope.
ROW_IN_SCOPE = "ISINSCOPE ( DimProject[Portfolio Name] )"
# Row level: 1 task, 2 project, 3 programme / portfolio / grand total
LEVEL = "IF ( ISINSCOPE ( DimTask[Name] ), 1, IF ( ISINSCOPE ( DimProject[Name] ), 2, 3 ) )"
# Start / finish of the row; project rows use the plan's summary dates, but only when the project has
# tasks in the visual's scope (so a project without schedule tasks never gets a row).
SPAN = f"""
VAR _lvl = {LEVEL}
VAR _ts = MIN ( DimTask[StartDate] )
VAR _te = MAX ( DimTask[EndDate] )
VAR _s = IF ( ISBLANK ( _ts ), BLANK (), IF ( _lvl = 2, COALESCE ( MIN ( DimProject[Summary_StartDate] ), _ts ), _ts ) )
VAR _e = IF ( ISBLANK ( _te ), BLANK (), IF ( _lvl = 2, COALESCE ( MAX ( DimProject[Summary_EndDate] ), _te ), _te ) )"""

# Population for the KPIs: schedule tasks on project plans that overlap the page's date window.
IN_VIEW = ('DimTask[WorkType] = "Tasks" && NOT ISBLANK ( DimTask[ProjectKey] ) '
           '&& NOT ISBLANK ( DimTask[StartDate] ) && NOT ISBLANK ( DimTask[EndDate] ) '
           '&& DimTask[StartDate] <= _we && DimTask[EndDate] >= _ws')
WIN = "VAR _ws = MIN ( DimDate[Date] )\nVAR _we = MAX ( DimDate[Date] )"

# ------------------------------------------------------------------ cell measures
add(m("State"), I, f"""{SPAN}
VAR _ps = MIN ( DimDate[Date] )
VAR _pe = MAX ( DimDate[Date] )
VAR _t = TODAY ()
VAR _todayCol = _t >= _ps && _t <= _pe
VAR _active = NOT ISBLANK ( _s ) && NOT ISBLANK ( _e ) && _s <= _pe && _e >= _ps
VAR _ms = _lvl = 1 && SELECTEDVALUE ( DimTask[Milestone], FALSE () ) = TRUE ()
VAR _pct = IF ( _lvl = 1, COALESCE ( MAX ( DimTask[PercentDone] ), 0 ), BLANK () )
-- Status "Completed" counts as done, so it is never painted late (same rule as OVERDUE_TASK)
VAR _cmp = _lvl = 1 && SELECTEDVALUE ( DimTask[Status] ) = "Completed"
VAR _be = SWITCH ( _lvl, 1, MAX ( DimTask[BaselineEndDate] ), 2, MAX ( DimProject[Summary_BaselineEndDate] ) )
VAR _om = ( MAX ( _s, _ps ) + MIN ( _e, _pe ) ) / 2
VAR _slip = NOT ISBLANK ( _be ) && INT ( _be ) < INT ( _e ) && _om > _be
VAR _bar =
    SWITCH ( TRUE (),
        _ms, IF ( _e >= _ps && _e <= _pe, IF ( _pct >= 100 || _cmp, 9, IF ( _e < _t, 10, 8 ) ) ),
        _lvl = 3, 7,
        _lvl = 2, IF ( _slip, 4, 6 ),
        SELECTEDVALUE ( DimTask[Leaf], TRUE () ) == FALSE (), IF ( _slip, 4, 5 ),
        _pct >= 100 || _cmp || ( _pct > 0 && _om <= _s + ( _e - _s ) * _pct / 100 ), 1,
        _e < _t, 3,
        _slip, 4,
        2
    )
VAR _inWindow =
    _todayCol && NOT ISBLANK ( _s )
        && _s <= CALCULATE ( MAX ( DimDate[Date] ), ALLSELECTED ( DimDate ) )
        && _e >= CALCULATE ( MIN ( DimDate[Date] ), ALLSELECTED ( DimDate ) )
RETURN
    IF ( {ROW_IN_SCOPE} && ( {PERIOD_IN_SCOPE} ),
        IF ( _active && NOT ISBLANK ( _bar ), _bar, IF ( _inWindow, 11 ) ) )""",
    "0", FOLDER,
    "Gantt cell state: 1 done, 2 remaining, 3 late, 4 baseline slip, 5 summary task, 6 project, 7 programme / "
    "portfolio, 8/9/10 milestone open / done / late, 11 today marker. Blank outside a period column and on the "
    "grand-total row.")

add(m("Bar"), T, f"""{SPAN}
VAR _st = {ref("State")}
RETURN
    IF ( NOT {ROW_IN_SCOPE}, BLANK (),   -- grand-total row: no bar, no sort key
    IF ( {PERIOD_IN_SCOPE},
        SWITCH ( _st, 8, "◆", 9, "◆", 10, "◆", 11, "│", BLANK (), BLANK (), "■" ),
        -- column-total level: sort key (task order inside a project, start date above it); only rows that
        -- overlap the selected date window get one, so rows outside the window disappear
        IF ( NOT ISBLANK ( _s ) && _s <= MAX ( DimDate[Date] ) && _e >= MIN ( DimDate[Date] ),
            IF ( _lvl = 1, FORMAT ( COALESCE ( MIN ( DimTask[taskorder] ), 99999 ), "00000" ),
                FORMAT ( _s, "yyyyMMdd" ) ) ) ) )""",
    None, FOLDER,
    "Gantt matrix value: a glyph per active period (hidden by the font colour), ◆ for milestones, │ for "
    "today; at the column-total level a sort key (task order / start date). Blank on the grand-total row.")

add(m("Bar Colour"), T, f"""
VAR _st = {ref("State")}
VAR _today = TODAY () >= MIN ( DimDate[Date] ) && TODAY () <= MAX ( DimDate[Date] )
RETURN
    SWITCH ( _st,
        1, "{TEAL}", 2, "{NAVY}", 3, "{RED}", 4, "{AMBER}", 5, "{GREY}", 6, "{SLATE_BAR}", 7, "{ROLLUP_BAR}",
        8, IF ( _today, "{ORANGE_SOFT}", "#FFFFFF" ), 9, IF ( _today, "{ORANGE_SOFT}", "#FFFFFF" ),
        10, IF ( _today, "{ORANGE_SOFT}", "#FFFFFF" ), 11, "{ORANGE_SOFT}"
    )""", None, "Story\\Colours", "Background of a Gantt cell (the bar).")

# Font: same palette as the bar (so the ■ glyph disappears into its cell); the glyph colour for ◆ and │.
# Mapped straight from State (not via Bar Colour) so a cell evaluates State only once per measure.
add(m("Bar Font"), T, f"""
VAR _st = {ref("State")}
RETURN
    SWITCH ( _st,
        1, "{TEAL}", 2, "{NAVY}", 3, "{RED}", 4, "{AMBER}", 5, "{GREY}", 6, "{SLATE_BAR}", 7, "{ROLLUP_BAR}",
        8, "{ORANGE}", 9, "{TEAL}", 10, "{RED}", 11, "{ORANGE}"
    )""", None, "Story\\Colours",
    "Font of a Gantt cell: the bar colour itself (so the glyph is invisible), the milestone / today colour otherwise.")

# ------------------------------------------------------------------ KPI measures
add(m("Tasks In View"), I, f"""
{WIN}
RETURN COUNTROWS ( FILTER ( DimTask, {IN_VIEW} ) ) + 0""", "#,##0", FOLDER,
    "Schedule tasks (summary and leaf) on project plans whose start–finish overlaps the selected date window.")
add(m("Projects In View"), I, f"""
{WIN}
RETURN COUNTROWS ( SUMMARIZE ( FILTER ( DimTask, {IN_VIEW} ), DimTask[ProjectKey] ) ) + 0""", "#,##0", FOLDER,
    "Project plans with at least one schedule task in the selected date window.")
add(m("Done % In View"), D, f"""
{WIN}
RETURN DIVIDE ( AVERAGEX ( FILTER ( DimTask, {IN_VIEW} && DimTask[Leaf] = TRUE () ), DimTask[PercentDone] ), 100 )""",
    "0%", FOLDER, "Average % complete of the leaf tasks in the selected date window.")
add(m("Milestones In View"), I, f"""
{WIN}
RETURN COUNTROWS ( FILTER ( DimTask, {IN_VIEW} && DimTask[Milestone] = TRUE () ) ) + 0""", "#,##0", FOLDER,
    "Milestones on project plans that fall in the selected date window.")
add(m("Headline"), T, f"""
{WIN}
VAR _n = {ref("Tasks In View")}
VAR _p = {ref("Projects In View")}
VAR _done = {ref("Done % In View")}
VAR _od = [Story | Overdue Tasks]
VAR _sl = [Story | Slipped Tasks]
VAR _slip = [Story | Late Task Slip (days)]
VAR _next =
    TOPN ( 1,
        FILTER ( DimTask, DimTask[WorkType] = "Tasks" && NOT ISBLANK ( DimTask[ProjectKey] )
            && DimTask[Milestone] = TRUE () && DimTask[PercentDone] < 100 && DimTask[EndDate] >= TODAY () ),
        DimTask[EndDate], ASC, DimTask[TaskKey], ASC )
VAR _nn = TRIM ( MAXX ( _next, DimTask[Name] ) )
VAR _nd = MAXX ( _next, DimTask[EndDate] )
VAR _np = MAXX ( _next, RELATED ( DimProject[Name] ) )
RETURN
    IF ( _n = 0,
        "No project schedule tasks fall in the selected months — clear a slicer or widen the date window in the filter pane.",
        FORMAT ( _n, "#,0" ) & " schedule tasks on " & FORMAT ( _p, "#,0" ) & " project plans run between "
            & FORMAT ( _ws, "mmm yyyy" ) & " and " & FORMAT ( _we, "mmm yyyy" ) & "; leaf tasks are "
            & IF ( ISBLANK ( _done ), "–", FORMAT ( _done, "0%" ) ) & " complete on average. "
            & FORMAT ( _od, "#,0" ) & " open tasks are overdue (red) and " & FORMAT ( _sl, "#,0" )
            & " finish after their baseline (amber"
            & IF ( ISBLANK ( _slip ), "", ", +" & FORMAT ( _slip, "#,0" ) & " days on average" ) & "). "
            & IF ( ISBLANK ( _nd ), "No open milestone is planned.",
                "Next milestone: " & _nn & IF ( ISBLANK ( _np ), "", " (" & _np & ")" ) & " on "
                    & FORMAT ( _nd, "d mmm yyyy" ) & "." )
    )""", folder="Story\\Headlines")


# ------------------------------------------------------------------ helpers (local)
def _expanded_rows(fields):
    """expansionStates that open every row level, so the Gantt shows tasks without clicking. Every non-leaf level
    carries identityKeys (the field itself), as Desktop saves it; the leaf level has none."""
    levels = []
    for k, f in enumerate(fields):
        lv = {"queryRefs": [pbir.qref(f)]}
        if k < len(fields) - 1:
            lv["identityKeys"] = [f]
        lv["isPinned"] = True
        levels.append(lv)
    return [{"roles": ["Rows"], "levels": levels, "root": {}}]


def _gantt_objects(bar, row_header_field):
    obj = table_style(9)
    obj["values"] = [{"properties": {"fontSize": n(9), "fontColorPrimary": col_solid(INK),
                                     "backColorPrimary": col_solid("#FFFFFF"), "fontColorSecondary": col_solid(INK),
                                     "backColorSecondary": col_solid("#FFFFFF")}},
                     # matchingOption 0 (values and totals): project / programme / portfolio rows are subtotal
                     # rows in the stepped layout and need the bar colours too
                     cf_back(bar, m("Bar Colour"), matching=0), cf_font(bar, m("Bar Font"), matching=0)]
    obj["columnHeaders"] = [{"properties": {"backColor": col_solid(NAVY), "fontColor": col_solid("#FFFFFF"),
                                            "bold": b(True), "fontSize": n(9), "alignment": s("Center"),
                                            "wordWrap": b(False)}}]
    obj["rowHeaders"] = [{"properties": {"fontColor": col_solid(NAVY), "fontSize": n(9), "wordWrap": b(False),
                                         "steppedLayoutIndentation": n(14), "showExpandCollapseButtons": b(True),
                                         "expandCollapseButtonsColor": col_solid(ORANGE)}}]
    obj["grid"] = [{"properties": {"gridHorizontal": b(True), "gridHorizontalColor": col_solid("#EEF0F4"),
                                   "gridVertical": b(False), "rowPadding": n(1),
                                   "outlineColor": col_solid(NAVY)}}]
    obj["general"] = [{"properties": {"layout": s("Compact")}}]  # stepped layout
    obj["subTotals"] = [{"properties": {"rowSubtotals": b(True), "columnSubtotals": b(False),
                                        "bold": b(True), "fontColor": col_solid(NAVY)}}]
    obj["columnWidth"] = [{"properties": {"value": n(96)}, "selector": {"metadata": pbir.qref(bar)}},
                          {"properties": {"value": n(430)}, "selector": {"metadata": pbir.qref(row_header_field)}}]
    obj["columnFormatting"] = [{"properties": {"alignment": s("Center")}, "selector": {"metadata": pbir.qref(bar)}}]
    return obj


# ------------------------------------------------------------------ page
def build():
    DP, DT = pages.DP, pages.DT
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"), (DP("Name"), "Project"),
               # own sync group: a Year picked on another page must not empty the Gantt's rolling window
               (C("DimDate", "Year"), "Year (columns)", "Gantt Year")]
    pg = pages.analytic_page("gantt", "GANTT", "WHAT RUNS WHEN — AND WHAT IS LATE?",
                             "Every project schedule task as a bar over a rolling 13 months (3 back, 9 ahead). "
                             "Year and the date window only change the columns; slicers pick the plans.",
                             slicers, m("Headline"))
    assert pg.id == pages.PID["gantt"] and pg.display == dict(pages.PAGES)["gantt"]
    # DimDate filters nothing on this page except the matrix columns and the "in view" KPIs.
    pg.add_filters([pbir.f_between("DimDate", "RelativeMonth", *WINDOW)])

    # ① pulse
    pages.section(pg, pages.Y1, 1, "The schedule pulse",
                  "Tasks in view = schedule tasks on project plans that touch the months shown. Overdue and slip "
                  "count all open leaf tasks of the selected plans.")
    pages.kpi_row(pg, pages.Y1K, [
        (m("Tasks In View"), "Tasks in view"),
        (m("Projects In View"), "Project plans in view"),
        (m("Done % In View"), "Leaf tasks complete (avg)", {"value_colour": TEAL}),
        ("Story | Overdue Tasks", "Overdue tasks", {"value_colour": RED}),
        ("Story | Slipped Tasks", "Tasks past baseline", {"value_colour": AMBER}),
        # same population as the headline's "+N days on average": open leaf tasks past their baseline
        ("Story | Late Task Slip (days)", "Avg slip of slipped open tasks (days)", {"value_colour": AMBER}),
        (m("Milestones In View"), "Milestones in view", {"value_colour": ORANGE}),
        ("Story | Milestones Next 30d", "Milestones next 30 days", {"value_colour": ORANGE}),
    ])

    # ② the Gantt
    Y2 = pages.Y2
    y_mat = pages.Y2V
    h_mat = pages.YNEXT - 16 - y_mat
    pages.section(pg, Y2, 2, "The plan on a timeline",
                  "Portfolio › programme › project › task, in plan order. Drill down on the months to see weeks.",
                  width=900)
    pages.legend_note(pg, 924, Y2 + 4, 860, [("Done", TEAL), ("Remaining", NAVY), ("Late", RED),
                                             ("Past baseline", AMBER), ("Summary", GREY), ("◆ Milestone", ORANGE),
                                             ("│ Today", ORANGE)], "gantt_legend")
    bar = M(m("Bar"))
    rows = [DP("Portfolio Name"), DP("Program Name"), DP("Name"), DT("Name")]
    period, week = C("DimDate", "Period"), C("DimDate", "WeekStart")
    v = chart("pivotTable",
              {"Rows": [P(rows[0], "Portfolio", True), P(rows[1], "Program", True), P(rows[2], "Project", True),
                        P(rows[3], "Task", True)],
               # WeekStart inactive: the matrix opens on months; weeks are one drill level down
               "Columns": [P(period, "Month", True), P(week, "Week", False)],
               "Values": [P(bar, " ")]},
              "Gantt — portfolio › programme › project › task × month",
              _gantt_objects(bar, rows[0]), sort=[(bar, "Ascending")])
    # Sort: PBIR can only sort a matrix level by a field in the query. DimTask[taskorder] cannot sort the
    # DimTask[Name] level without being a row level of its own (it would show as an extra column) or a model
    # sort-by column, so the matrix sorts by the Bar measure. Power BI sorts matrix rows by the value at the
    # column-total level (the row total across the period columns), which is where Bar returns the sort key;
    # column subtotals stay OFF so that key is never displayed.
    v["expansionStates"] = _expanded_rows(rows)
    pg.add(16, y_mat, 1768, h_mat, v, key="v_gantt",
           filters=[pbir.f_in("DimTask", "WorkType", ["Tasks"]), pages.PROJECT_TASKS])

    pages.next_chapter(pg, "gantt", pages.YNEXT)
    return [pg]
