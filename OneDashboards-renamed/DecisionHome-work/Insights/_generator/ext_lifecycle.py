"""2b · Pipeline, Gates & Dependencies — "Where is the pipeline stuck, which projects
have sat at a gate too long, and who is waiting on whom?"

Data notes (checked against ModeL360Star.bim):
  * DimProject holds PROJECT plans only; ProcessStep / ProcessStepIndex / ProcessStepStart
    describe the gate each project sits at now. DimDate does not filter DimProject, so no Year slicer.
  * FactPlanProcessStep -> DimProject via ProjectKey (active). The approver column is dropped in
    Power Query, so "who approves" cannot be shown — only the requesting project and its manager.
  * DimProcessStep has NO relationship; it is not used here (gate order comes from ProcessStepIndex).
  * BridgePlanDependency: FromProjectKey -> DimProject is active, ToProjectKey is INACTIVE. Successor
    attributes are read with TREATAS(... ToProjectKey ..., DimProject[ProjectKey]) + REMOVEFILTERS so a
    successor outside the sliced portfolio is still found.
"""
import pbir
from pbir import (C, M, P, b, n, s, i, chart, col_solid, headline, legend, labels_on, measure_fill,
                  table_style, cf_font, f_not_blank, NAVY, ORANGE, RED, AMBER, TEAL, GREY)
import pages
from pages import DP, Y1, Y1K, Y2, Y2V, H2, Y3, Y3V, H3, Y4, Y4V, H4, YNEXT
from story_measures import add, T, D, I, cnt

PRE = "Story | Lifecycle · "
FOLDER = "Story\\Lifecycle"


def L(name):
    return PRE + name


def _add(name, dtype, expr, fmt=None, desc=None):
    add(L(name), dtype, expr, fmt, FOLDER, desc)


# ------------------------------------------------------------------ gate ageing
_DAYS = "DATEDIFF ( DimProject[ProcessStepStart], TODAY (), DAY )"
_AGED = "FILTER ( DimProject, NOT ISBLANK ( DimProject[ProcessStepStart] ) )"
# "Open" = a known state that is not Closed / Cancelled. A blank state is not counted (a NOT IN / <> test would be
# TRUE for it), same idea as Story | Active Projects (State = "Active").
_OPEN = ('NOT ISBLANK ( DimProject[State_Value] ) && NOT ( DimProject[State_Value] IN { "Closed", "Cancelled" } )')

_add("Stuck Threshold Days", I, "90", "#,0",
     "Days in the current process step after which a project counts as stuck. Change here only.")
_add("Step Order", I, "MIN ( DimProject[ProcessStepIndex] )", "0",
     "Gate order of the process step (DimProject[ProcessStepIndex]); used to sort charts in lifecycle order.")
_add("In Pipeline", I, """
COUNTROWS (
    FILTER ( DimProject, DimProject[State_Value] = "Proposed"
        || ( NOT ISBLANK ( DimProject[ProcessStepIndex] ) && DimProject[ProcessStepIndex] = 0 ) )
) + 0""", "#,0", "Projects still proposed or sitting at the first gate (ProcessStepIndex = 0).")
_add("Avg Days in Step", D, f"AVERAGEX ( {_AGED}, {_DAYS} )", "#,0",
     "Average days since DimProject[ProcessStepStart] — how long projects have been at their current gate.")
_add("Median Days in Step", D, f"MEDIANX ( {_AGED}, {_DAYS} )", "#,0",
     "Median days in the current process step.")
_add("Max Days in Step", D, f"MAXX ( {_AGED}, {_DAYS} )", "#,0",
     "Longest time any project in context has been at its current gate.")
_add("Stuck Projects", I, f"""
VAR _thr = [{L("Stuck Threshold Days")}]
RETURN
    COUNTROWS (
        FILTER (
            DimProject,
            NOT ISBLANK ( DimProject[ProcessStepStart] )
                && {_OPEN}
                && {_DAYS} > _thr
        )
    ) + 0""", "#,0", "Open projects that have been in their current step longer than the threshold.")
_add("Stuck Projects (bars)", I, f"""
VAR _v = [{L("Stuck Projects")}]
RETURN IF ( _v = 0, BLANK (), _v )""", "#,0", "Same as Stuck Projects but blank instead of 0 (charts).")
_add("Stuck Days", D, f"""
VAR _thr = [{L("Stuck Threshold Days")}]
VAR _d =
    MAXX (
        FILTER ( DimProject, NOT ISBLANK ( DimProject[ProcessStepStart] ) && {_OPEN} ),
        {_DAYS}
    )
RETURN IF ( _d > _thr, _d )""", "#,0",
     "Days in step, only when above the threshold (blank otherwise, so the list shows stuck projects only).")
_add("Ageing Colour", T, f"""
VAR _d = [{L("Max Days in Step")}]
VAR _thr = [{L("Stuck Threshold Days")}]
RETURN IF ( ISBLANK ( _d ), "#666666", IF ( _d > 2 * _thr, "#C0392B", IF ( _d > _thr, "#D9A832", "#1E6D6E" ) ) )""",
     desc="Red = more than twice the threshold, amber = over the threshold, teal = within.")

# ------------------------------------------------------------------ gate approvals (FactPlanProcessStep)
_PENDING = """FILTER (
        FactPlanProcessStep,
        VAR _a = UPPER ( TRIM ( FactPlanProcessStep[ApprovalState] ) )
        RETURN
            _a <> ""
                && ( CONTAINSSTRING ( _a, "PEND" ) || CONTAINSSTRING ( _a, "WAIT" ) || CONTAINSSTRING ( _a, "SUBMIT" )
                    || CONTAINSSTRING ( _a, "REQUEST" ) || CONTAINSSTRING ( _a, "REVIEW" ) || CONTAINSSTRING ( _a, "PROGRESS" )
                    || _a = "OPEN" )
    )"""
_add("Gate Steps", I, "COUNTROWS ( FactPlanProcessStep )", "#,0", "Process-step records (FactPlanProcessStep).")
_add("Pending Approvals", I, f"COUNTROWS ( {_PENDING} ) + 0", "#,0",
     "Gate steps whose ApprovalState reads pending / waiting / submitted / requested / in review / open.")
_add("Avg Step Duration", D, """
AVERAGEX (
    FILTER (
        FactPlanProcessStep,
        NOT ISBLANK ( FactPlanProcessStep[Start] ) && NOT ISBLANK ( FactPlanProcessStep[End] )
            && FactPlanProcessStep[End] >= FactPlanProcessStep[Start]
    ),
    DATEDIFF ( FactPlanProcessStep[Start], FactPlanProcessStep[End], DAY )
)""", "#,0", "Average duration of a process step: days from step Start to step End, over every step where both "
     "dates exist (all approval states — not an approval lead time).")
_add("Days Waiting", D, f"""
VAR _p = {_PENDING}
VAR _d = MAXX ( FILTER ( _p, NOT ISBLANK ( FactPlanProcessStep[Start] ) ), DATEDIFF ( FactPlanProcessStep[Start], TODAY (), DAY ) )
RETURN IF ( COUNTROWS ( _p ) > 0, COALESCE ( _d, 0 ) )""", "#,0",
     "Days since a pending gate step started (blank for steps that are not pending).")
_add("Approvals Note", T, f"""
VAR _all = CALCULATE ( COUNTROWS ( FactPlanProcessStep ), REMOVEFILTERS ( DimProject ) )
VAR _n = [{L("Gate Steps")}]
VAR _p = [{L("Pending Approvals")}]
VAR _lt = [{L("Avg Step Duration")}]
RETURN
    IF ( COALESCE ( _all, 0 ) = 0, "No gate-approval records (PlanProcessSteps) in OnePlan yet.",
        IF ( COALESCE ( _n, 0 ) = 0, "No gate steps recorded for the selected projects.",
            {cnt("_p")} & " of " & {cnt("_n")} & " gate steps wait for approval"
                & IF ( ISBLANK ( _lt ), ".", " · a step lasts " & FORMAT ( _lt, "#,0" ) & " days on average (start → end)." ) ) )""")

# ------------------------------------------------------------------ plan dependencies (BridgePlanDependency)
# Each key is read into a VAR while the ADDCOLUMNS row context is still live, then used as a
# CALCULATE filter. (A bare BridgePlanDependency[...] inside CALCULATE's expression has no row
# context any more — that was the "single value for ToProjectKey cannot be determined" error.)
_DEP_T = """ADDCOLUMNS (
        BridgePlanDependency,
        "@pf",
            VAR _k = BridgePlanDependency[FromProjectKey]
            RETURN CALCULATE ( MAX ( DimProject[Summary_EndDate] ), REMOVEFILTERS ( DimProject ), DimProject[ProjectKey] = _k ),
        "@ss",
            VAR _k = BridgePlanDependency[ToProjectKey]
            RETURN CALCULATE ( MIN ( DimProject[Summary_StartDate] ), REMOVEFILTERS ( DimProject ), DimProject[ProjectKey] = _k )
    )"""
_HAS_DEP = "COUNTROWS ( BridgePlanDependency ) > 0"
_add("Dependency Count", I, "COUNTROWS ( BridgePlanDependency )", "#,0",
     "Plan dependencies whose predecessor (FromProjectKey) is in context. Blank when none (matrix rows).")
_add("Dependencies", I, f"[{L('Dependency Count')}] + 0", "#,0", "Dependency Count, 0 instead of blank (cards).")
_add("At Risk Count", I, f"""
VAR _t = {_DEP_T}
RETURN COUNTROWS ( FILTER ( _t, NOT ISBLANK ( [@pf] ) && NOT ISBLANK ( [@ss] ) && [@pf] > [@ss] ) )""", "#,0",
     "Dependencies where the predecessor's finish (Summary_EndDate) is later than the successor's start "
     "(Summary_StartDate). Blank when none.")
_add("Dependencies At Risk", I, f"[{L('At Risk Count')}] + 0", "#,0", "At Risk Count, 0 instead of blank (cards).")
_add("Successor", T, f"""
VAR _keys = VALUES ( BridgePlanDependency[ToProjectKey] )
VAR _r =
    CALCULATE (
        CONCATENATEX ( VALUES ( DimProject[Name] ), DimProject[Name], ", " ),
        TREATAS ( _keys, DimProject[ProjectKey] ),
        REMOVEFILTERS ( DimProject )
    )
RETURN IF ( {_HAS_DEP}, COALESCE ( _r, "(not a project plan)" ) )""",
     desc="Successor project(s) via the inactive ToProjectKey relationship (TREATAS).")
_add("Predecessor Finish", "DateTime", f"""
IF ( {_HAS_DEP},
    CALCULATE (
        MAX ( DimProject[Summary_EndDate] ),
        TREATAS ( VALUES ( BridgePlanDependency[FromProjectKey] ), DimProject[ProjectKey] ),
        REMOVEFILTERS ( DimProject )
    ) )""", "dd mmm yyyy")
_add("Successor Start", "DateTime", f"""
IF ( {_HAS_DEP},
    CALCULATE (
        MIN ( DimProject[Summary_StartDate] ),
        TREATAS ( VALUES ( BridgePlanDependency[ToProjectKey] ), DimProject[ProjectKey] ),
        REMOVEFILTERS ( DimProject )
    ) )""", "dd mmm yyyy")
_add("Overlap Days", D, f"""
VAR _t = {_DEP_T}
RETURN MAXX ( FILTER ( _t, NOT ISBLANK ( [@pf] ) && NOT ISBLANK ( [@ss] ) ), DATEDIFF ( [@ss], [@pf], DAY ) )""",
     "+#,0;-#,0;0", "Predecessor finish minus successor start, in days. Positive = the successor starts "
     "before its predecessor finishes.")
_add("Dependency Flag", T, f"""
VAR _r = [{L("At Risk Count")}]
VAR _o = [{L("Overlap Days")}]
RETURN
    IF ( {_HAS_DEP},
        IF ( _r > 0, "At risk: predecessor finishes after successor start",
            IF ( ISBLANK ( _o ), "Dates missing", "OK" ) ) )""")
_add("Dependency Flag Colour", T, f"""
VAR _r = [{L("At Risk Count")}]
VAR _o = [{L("Overlap Days")}]
RETURN IF ( _r > 0, "#C0392B", IF ( ISBLANK ( _o ), "#9AA3AF", "#1E6D6E" ) )""")
_add("Dependency Note", T, f"""
VAR _all = CALCULATE ( COUNTROWS ( BridgePlanDependency ), REMOVEFILTERS ( DimProject ) )
VAR _n = [{L("Dependencies")}]
VAR _r = [{L("Dependencies At Risk")}]
RETURN
    IF ( COALESCE ( _all, 0 ) = 0,
        "No plan dependencies recorded in OnePlan. Link predecessor and successor plans in OnePlan to see who is waiting on whom.",
        IF ( _n = 0, "None of the selected projects is a predecessor in a recorded plan dependency.",
            {cnt("_n")} & " plan dependencies start from the selected projects; " & {cnt("_r")}
                & " at risk because the predecessor finishes after the successor is due to start." ) )""")

# ------------------------------------------------------------------ headline
_add("Headline", T, f"""
VAR _n = [Project | Plans Count]
VAR _top =
    TOPN ( 1,
        ADDCOLUMNS ( FILTER ( VALUES ( DimProject[ProcessStep] ), NOT ISBLANK ( DimProject[ProcessStep] ) ),
            "@c", [Project | Plans Count] ),
        [@c], DESC )
VAR _ts = MAXX ( _top, DimProject[ProcessStep] )
VAR _tc = MAXX ( _top, [@c] )
VAR _thr = [{L("Stuck Threshold Days")}]
VAR _stuck = [{L("Stuck Projects")}]
VAR _long =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Name] ), "@d", [{L("Stuck Days")}] ),
            NOT ISBLANK ( DimProject[Name] ) && NOT ISBLANK ( [@d] ) ),
        [@d], DESC, DimProject[Name], ASC )
VAR _ln = MAXX ( _long, DimProject[Name] )
VAR _ld = MAXX ( _long, [@d] )
VAR _p = [{L("Pending Approvals")}]
VAR _r = [{L("Dependencies At Risk")}]
RETURN
    IF ( COALESCE ( _n, 0 ) = 0, "No project plans in the current selection.",
        {cnt("_tc")} & " of " & {cnt("_n")} & " projects sit in " & COALESCE ( _ts, "an unnamed step" ) & ". "
            & IF ( _stuck = 0, "No open project has been at its gate longer than " & FORMAT ( _thr, "0" ) & " days",
                {cnt("_stuck")} & " open projects have been at their gate longer than " & FORMAT ( _thr, "0" )
                    & " days — longest: " & _ln & " (" & FORMAT ( _ld, "#,0" ) & " days)" )
            & ". " & {cnt("_p")} & " gate approvals pending, " & {cnt("_r")} & " dependencies at risk." )""")


# ------------------------------------------------------------------ local helpers
def _no_totals(obj):
    obj["total"] = [{"properties": {"totals": b(False)}}]
    return obj


def _ref_line(value, colour, label):
    return [{"properties": {"show": b(True), "displayName": s(label), "value": n(value),
                            "lineColor": col_solid(colour), "transparency": n(0), "style": s("dashed"),
                            "position": s("front"), "dataLabelShow": b(True)},
             "selector": {"id": "1"}}]


# ------------------------------------------------------------------ page
def build():
    step, order = DP("ProcessStep"), M(L("Step Order"))
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (DP("ProjectType_Value"), "Project type"), (step, "Process step")]
    pg = pages.analytic_page("lifecycle", "LIFECYCLE", "WHERE IS THE PIPELINE STUCK?",
                             "Projects per gate from OnePlan process steps, how long they have waited there, open gate "
                             "approvals and the plan dependencies that make one project wait on another.",
                             slicers, L("Headline"))

    # ① pulse
    pages.section(pg, Y1, 1, "The pipeline pulse",
                  "Stuck = an open project in the same step for more than 90 days. Project plans only.")
    pages.kpi_row(pg, Y1K, [
        ("Project | Plans Count", "Projects"),
        (L("In Pipeline"), "Proposed / first gate"),
        (L("Median Days in Step"), "Median days in step"),
        (L("Stuck Projects"), "Stuck > 90 days", {"value_colour": RED}),
        (L("Pending Approvals"), "Approvals pending", {"value_colour": AMBER}),
        (L("Avg Step Duration"), "Avg step duration (d)"),
        (L("Dependencies"), "Plan dependencies"),
        (L("Dependencies At Risk"), "Dependencies at risk", {"value_colour": RED}),
    ])

    # ② lifecycle flow + ageing per step
    pages.section(pg, Y2, 2, "Where does the pipeline pile up?",
                  "Steps in gate order, left to right. Orange = projects stuck at that gate; tall bars on the right chart = slow gates.")
    pc, stuck = M("Project | Plans Count"), M(L("Stuck Projects (bars)"))
    step_filter = [f_not_blank("DimProject", "ProcessStep")]
    pg.add(16, Y2V, 878, H2, chart("clusteredColumnChart",
        {"Category": [P(step, "Process step")], "Y": [P(pc, "Projects"), P(stuck, "Stuck > 90 days")],
         "Tooltips": [P(order, "Gate order")]},
        "Projects per process step (gate order)",
        {"dataPoint": [measure_fill(pc, NAVY), measure_fill(stuck, ORANGE)], "legend": legend("Top"),
         "labels": labels_on(True)},
        sort=[(order, "Ascending")]), key="v_flow", filters=step_filter)
    avg, mx = M(L("Avg Days in Step")), M(L("Max Days in Step"))
    pg.add(906, Y2V, 878, H2, chart("clusteredColumnChart",
        {"Category": [P(step, "Process step")], "Y": [P(avg, "Average days"), P(mx, "Longest (days)")],
         "Tooltips": [P(order, "Gate order")]},
        "Days in the current step — average and longest, per gate",
        {"dataPoint": [measure_fill(avg, NAVY), measure_fill(mx, "#C9CED8")], "legend": legend("Top"),
         "labels": labels_on(True), "y1AxisReferenceLine": _ref_line(90, RED, "90-day threshold")},
        sort=[(order, "Ascending")]), key="v_ageing", filters=step_filter)

    # ③ stuck list + gate approvals
    pages.section(pg, Y3, 3, "Who has sat at a gate too long, and which approvals are waiting?",
                  "Left: open projects over 90 days, longest first — call the manager. Right: OnePlan gate approvals.")
    sd = M(L("Stuck Days"))
    obj = _no_totals(table_style())
    obj["values"] += [cf_font(sd, L("Ageing Colour"))]
    pg.add(16, Y3V, 878, H3, chart("tableEx",
        # 5 columns so "Since" and "Days" fit without a horizontal scroll. State is implied (open projects
        # only) and Portfolio is a page slicer, so both are left out.
        {"Values": [P(DP("Name"), "Project"), P(DP("Manager_Value"), "Manager"), P(step, "Step"),
                    P(DP("ProcessStepStart"), "Since"), P(sd, "Days")]},
        "Stuck projects — over 90 days in the current step", obj, sort=[(sd, "Descending")]), key="v_stuck")
    pg.add(906, Y3V, 878, 40, headline(L("Approvals Note"), bg="#FFFFFF", border=ORANGE, size=11), key="appr_note")
    fs = lambda p: C("FactPlanProcessStep", p)  # noqa: E731
    gs = M(L("Gate Steps"))
    pg.add(906, Y3V + 48, 434, 160, chart("barChart",
        {"Category": [P(fs("StepName"), "Step")], "Series": [P(fs("ApprovalState"), "Approval")], "Y": [P(gs, "Steps")]},
        "Gate steps by approval state", {"legend": legend("Top")}, sort=[(gs, "Descending")]), key="v_appr_state")
    lt = M(L("Avg Step Duration"))
    pg.add(1350, Y3V + 48, 434, 160, chart("clusteredBarChart",
        {"Category": [P(fs("StepName"), "Step")], "Y": [P(lt, "Avg duration (days)")]},
        "Average step duration per step (days, Start → End)",
        {"dataPoint": [{"properties": {"fill": col_solid(TEAL)}}], "labels": labels_on(True)},
        sort=[(lt, "Descending")]), key="v_appr_lead")
    dw = M(L("Days Waiting"))
    obj = _no_totals(table_style(9))
    pg.add(906, Y3V + 216, 878, H3 - 216, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Manager_Value"), "Manager"), P(fs("StepName"), "Step"),
                    P(fs("ApprovalState"), "Approval"), P(fs("StepState"), "Step state"), P(fs("Start"), "Started"),
                    P(dw, "Days waiting"), P(fs("Comments"), "Comments")]},
        "Pending gate approvals — longest wait first", obj, sort=[(dw, "Descending")]), key="v_appr_pending")

    # ④ plan dependencies (R8)
    pages.section(pg, Y4, 4, "Who is waiting on whom?",
                  "OnePlan plan dependencies: predecessor → successor. Red = the predecessor finishes after the successor is due to start.")
    pg.add(16, Y4V, 1768, 44, headline(L("Dependency Note"), bg="#FFFFFF", border=ORANGE, size=11), key="dep_note")
    bd = lambda p: C("BridgePlanDependency", p)  # noqa: E731
    dc, ar, succ = M(L("Dependency Count")), M(L("At Risk Count")), M(L("Successor"))
    obj = table_style()
    obj["values"] += [cf_font(ar, L("Dependency Flag Colour"))]
    pg.add(16, Y4V + 54, 700, H4 - 54, chart("pivotTable",
        {"Rows": [P(DP("Name"), "Predecessor", True), P(bd("Type"), "Dependency type", True)],
         "Values": [P(succ, "Successor(s)"), P(dc, "Dependencies"), P(ar, "At risk")]},
        "Dependency matrix — predecessor › type → successor", obj, sort=[(dc, "Descending")]), key="v_dep_matrix")
    flag, ov = M(L("Dependency Flag")), M(L("Overlap Days"))
    obj = _no_totals(table_style())
    obj["values"] += [cf_font(flag, L("Dependency Flag Colour")), cf_font(ov, L("Dependency Flag Colour"))]
    pg.add(728, Y4V + 54, 1056, H4 - 54, chart("tableEx",
        {"Values": [P(DP("Name"), "Predecessor"), P(succ, "Successor"), P(bd("Type"), "Type"),
                    P(bd("Description"), "Description"), P(M(L("Predecessor Finish")), "Predecessor finish"),
                    P(M(L("Successor Start")), "Successor start"), P(ov, "Overlap (days)"), P(flag, "Flag")]},
        "Dependency register — biggest overlap first", obj, sort=[(ov, "Descending")]), key="v_dep_register")

    pages.next_chapter(pg, "lifecycle", YNEXT)
    return [pg]
