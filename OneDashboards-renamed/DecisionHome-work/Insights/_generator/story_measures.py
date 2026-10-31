"""Report-level ("thin report") measures that carry the storytelling.

They live in reportExtensions.json, so the pack works against the published
OneModel360Star model without changing it. Everything here builds only on
model measures/columns of the published model.

Conventions (owner decisions D-01 .. D-05, see README):
- Utilisation = Scheduled hours / capacity, organisation-wide (no project filter:
  FactCapacity has no project link). Scheduled hours count PROJECT plans only.
  Committed is a separate resource-manager figure; it is NOT a subset of Scheduled
  (on the tenant committed > scheduled, and cells exist with committed but no schedule).
- Financial variance is measured at completion: EAC - Budget, ignoring the date
  filter. "To date" figures (budget to date vs actuals) respect it.
- Benefits come from the time-phased financial plan (FactCost CostType "Benefits");
  actual benefits from ACTUAL_BENEFITS_COST_TYPE. No "% done x planned" proxy.
- Counts, money, benefits and demand are PROJECT plans only. FactCost and
  FactResourcePlan keep rows of every plan type; non-project plans get a NULL
  ProjectKey and land on the blank DimProject row, so every base measure carries
  PROJ (DimProject[Id] not blank). Tasks: DimTask[ProjectKey] not blank.
- Priority = DimProject[PrioritizationScore].
"""

# FactCost cost type that holds realised (actual) benefits. This tenant has none yet;
# change the literal here when OnePlan gets one.
ACTUAL_BENEFITS_COST_TYPE = "Actual Benefits"
BENEFITS_COST_TYPE = "Benefits"
EAC_COST_TYPE = "EAC"
REVENUE_COST_TYPE = "Forecasted Revenue"

# "Active" = State "Active" exactly (Plans.json project states: Active / Proposed / On Hold / Closed / blank).
# A NOT IN {...} test would be TRUE for a blank state (and for the blank DimProject row).
ACTIVE_STATE = "Active"
ACTIVE = f'KEEPFILTERS ( DimProject[State_Value] = "{ACTIVE_STATE}" )'
# Project plans only: excludes the blank DimProject row that collects non-project plan rows of FactCost /
# FactResourcePlan / FactStatusReport (NULL ProjectKey after the left join in Power Query).
PROJ = "KEEPFILTERS ( NOT ISBLANK ( DimProject[Id] ) )"
PROJ_TASK = "KEEPFILTERS ( NOT ISBLANK ( DimTask[ProjectKey] ) )"
# ONE overdue definition (story pages, One-Pager, tooltip): open leaf work-plan tasks on project plans whose
# finish date has passed. Leaf = TRUE drops summary tasks; a blank EndDate would compare as < TODAY(), so it
# is excluded explicitly; Status <> "Completed" is also TRUE for a blank status.
OVERDUE_TASK = ('DimTask[WorkType] = "Tasks" && DimTask[Leaf] = TRUE () && NOT ISBLANK ( DimTask[ProjectKey] ) '
                '&& DimTask[PercentDone] < 100 && DimTask[Status] <> "Completed" '
                '&& NOT ISBLANK ( DimTask[EndDate] ) && DimTask[EndDate] < TODAY ()')
RISK = f'KEEPFILTERS ( DimTask[WorkType] = "Risks" ), KEEPFILTERS ( DimTask[State] = "Active" ), {PROJ_TASK}'
IMPACT_SCORE = 'SWITCH ( LEFT ( DimTask[Impact], 3 ), "(1)", 4, "(2)", 3, "(3)", 2, "(4)", 1, 0 )'
PROB_SCORE = 'SWITCH ( LEFT ( DimTask[Probability Category], 3 ), "(1)", 4, "(2)", 3, "(3)", 2, "(4)", 1, 0 )'
HIGH_HEAT = 9  # impact x probability on the 4x4 grid (see Story | Heat Colour)


def money(v):
    """DAX text for a compact euro amount of variable/expression v."""
    return (f'IF ( ISBLANK ( {v} ), "–", IF ( ABS ( {v} ) >= 1000000, "€" & FORMAT ( {v} / 1000000, "#,0.0" ) & "M", '
            f'IF ( ABS ( {v} ) >= 1000, "€" & FORMAT ( {v} / 1000, "#,0" ) & "K", "€" & FORMAT ( {v}, "#,0" ) ) ) )')


def cnt(v):
    return f'FORMAT ( COALESCE ( {v}, 0 ), "#,0" )'


def pct(v, f="0%"):
    return f'IF ( ISBLANK ( {v} ), "–", FORMAT ( {v}, "{f}" ) )'


T, D, I = "Text", "Double", "Integer"
MEASURES = []


def add(name, dtype, expr, fmt=None, folder="Story", desc=None):
    MEASURES.append({"name": name, "dataType": dtype, "expression": expr.strip(), "formatString": fmt,
                     "displayFolder": folder, "description": desc})


def colour3(var_expr, red, amber):
    """Teal / amber / red rule on a ratio; BLANK in, BLANK out (no colour, no phantom rows)."""
    return f"""
VAR _p = {var_expr}
RETURN IF ( ISBLANK ( _p ), BLANK (), IF ( _p > {red}, "#C0392B", IF ( _p > {amber}, "#D9A832", "#1E6D6E" ) ) )"""


# ------------------------------------------------------------------ shared
add("Story | Active Projects", I, f"""
CALCULATE ( COUNTROWS ( DimProject ), {ACTIVE} ) + 0""", "#,##0", "Story\\Portfolio",
    'Project plans whose state is "Active" (a blank state does not count).')
add("Story | On Track %", D, f"""
VAR _tot = CALCULATE ( COUNTROWS ( DimProject ), {ACTIVE}, KEEPFILTERS ( NOT ISBLANK ( DimProject[OverallHealth_Value] ) ) )
VAR _ok = CALCULATE ( COUNTROWS ( DimProject ), {ACTIVE}, KEEPFILTERS ( DimProject[OverallHealth_Value] = "(1) On Track" ) )
RETURN IF ( _tot > 0, DIVIDE ( COALESCE ( _ok, 0 ), _tot ) )""", "0%",
    desc="Share of active projects whose overall health is (1) On Track.")

add("Story | Refreshed", T, """
VAR _t = MAX ( RefreshTime[Last Refreshed (Belgium Time)] )
RETURN IF ( ISBLANK ( _t ), "POWERED BY ONEPLAN", "POWERED BY ONEPLAN  ·  REFRESHED " & UPPER ( FORMAT ( _t, "dd mmm yyyy hh:nn" ) ) & " CET" )
""")

# ------------------------------------------------------------------ finance (FactCost, time-phased plan)
add("Story | Finance EAC", D, f"""
CALCULATE ( SUM ( FactCost[Cost] ), KEEPFILTERS ( FactCost[CostType] = "{EAC_COST_TYPE}" ), REMOVEFILTERS ( DimDate ), {PROJ} )""",
    "#,##0", "Story\\Finance", "Estimate at completion (FactCost EAC) of project plans, lifetime: ignores the date filter.")
add("Story | Budget At Completion", D, f"CALCULATE ( [Finance | Budget Cost], REMOVEFILTERS ( DimDate ), {PROJ} )", "#,##0",
    "Story\\Finance", "Total budget of project plans over the plan lifetime (FactCost Budget), ignores the date filter.")
add("Story | Budget In Period", D, f"CALCULATE ( [Finance | Budget Cost], {PROJ} )", "#,##0", "Story\\Finance",
    "Budget of project plans phased by date (respects the date filter).")
add("Story | Actual Cost", D, f"CALCULATE ( [Finance | Actual Cost], {PROJ} )", "#,##0", "Story\\Finance",
    "Actual cost of project plans phased by date (respects the date filter).")
add("Story | Forecast Cost", D, f"CALCULATE ( [Finance | Forecast Cost], {PROJ} )", "#,##0", "Story\\Finance",
    "Forecast cost of project plans phased by date (respects the date filter).")
add("Story | EAC Variance", D, """
VAR _e = [Story | Finance EAC]
VAR _b = [Story | Budget At Completion]
RETURN IF ( ISBLANK ( _e ) && ISBLANK ( _b ), BLANK (), COALESCE ( _e, 0 ) - COALESCE ( _b, 0 ) )""", "#,##0",
    "Story\\Finance", "EAC minus budget at completion. Positive = expected overrun.")
add("Story | EAC Variance %", D, "DIVIDE ( [Story | EAC Variance], [Story | Budget At Completion] )", "+0.0%;-0.0%;0.0%",
    "Story\\Finance")
add("Story | EAC In Period", D, f"""
CALCULATE ( SUM ( FactCost[Cost] ), KEEPFILTERS ( FactCost[CostType] = "{EAC_COST_TYPE}" ), {PROJ} )""", "#,##0", "Story\\Finance",
    "EAC of project plans phased by date (respects the date filter) — for trend charts only.")
add("Story | Budget To Date", D, "CALCULATE ( [Story | Budget In Period], KEEPFILTERS ( DimDate[Date] <= TODAY () ) )",
    "#,##0", "Story\\Finance", "Budget of project plans phased up to today (within the selected period).")
add("Story | To-Date Variance", D, """
VAR _a = [Story | Actual Cost]
VAR _b = [Story | Budget To Date]
RETURN IF ( ISBLANK ( _a ) && ISBLANK ( _b ), BLANK (), COALESCE ( _a, 0 ) - COALESCE ( _b, 0 ) )""", "#,##0",
    "Story\\Finance", "Actual cost minus budget to date. Positive = spending ahead of plan.")
add("Story | To-Date Variance %", D, "DIVIDE ( [Story | To-Date Variance], [Story | Budget To Date] )", "+0.0%;-0.0%;0.0%",
    "Story\\Finance")
add("Story | Burn %", D, """
DIVIDE ( CALCULATE ( [Story | Actual Cost], REMOVEFILTERS ( DimDate ) ), [Story | Budget At Completion] )""", "0%",
    "Story\\Finance", "Lifetime actual cost as a share of budget at completion.")
add("Story | Projects Over Budget", I, """
COUNTROWS (
    FILTER (
        VALUES ( DimProject[Id] ),
        VAR _b = [Story | Budget At Completion]
        RETURN NOT ISBLANK ( DimProject[Id] ) && _b > 0 && [Story | Finance EAC] > _b
    )
) + 0""", "#,##0", "Story\\Finance", "Projects with a budget whose EAC exceeds it.")
# kept for compatibility (time-phased Forecast Cost vs Budget); the pages use the EAC measures
add("Story | Forecast Variance", D, "[Story | Forecast Cost] - [Story | Budget In Period]", "#,##0",
    "Story\\Finance", "Forecast cost minus budget cost of project plans in the selected period (FactCost).")
add("Story | Forecast Variance %", D, "DIVIDE ( [Story | Forecast Variance], [Story | Budget In Period] )",
    "+0.0%;-0.0%;0.0%", "Story\\Finance")
add("Story | Variance Colour", T, colour3("[Story | EAC Variance %]", 0.05, 0), folder="Story\\Colours",
    desc="Red > 5% over budget at completion, amber slightly over, teal within budget.")
add("Story | To-Date Colour", T, colour3("[Story | To-Date Variance %]", 0.05, 0), folder="Story\\Colours")
add("Story | Burn Colour", T, colour3("[Story | Burn %]", 1, 0.9), folder="Story\\Colours")

_FIN_RANGE = f"""
VAR _d = MAX ( DimDate[Date] )
VAR _first = CALCULATE ( MIN ( FactCost[Date] ), REMOVEFILTERS ( DimDate ), {PROJ} )
VAR _last = CALCULATE ( MAX ( FactCost[Date] ), REMOVEFILTERS ( DimDate ), {PROJ} )
VAR _out = ISBLANK ( _first ) || MIN ( DimDate[Date] ) > _last || _d < _first"""
add("Story | Cum Budget", D, _FIN_RANGE + """
RETURN IF ( NOT _out, CALCULATE ( [Story | Budget In Period], REMOVEFILTERS ( DimDate ), DimDate[Date] <= _d ) )""",
    "#,##0", "Story\\Finance", "Lifetime cumulative budget up to the end of the period on the axis.")
add("Story | Cum Actual", D, _FIN_RANGE + """
VAR _cut = MIN ( _d, TODAY () )
RETURN IF ( NOT _out && MIN ( DimDate[Date] ) <= TODAY (),
    CALCULATE ( [Story | Actual Cost], REMOVEFILTERS ( DimDate ), DimDate[Date] <= _cut ) )""",
    "#,##0", "Story\\Finance", "Lifetime cumulative actual cost; blank after today.")
add("Story | Cum EAC", D, _FIN_RANGE + f"""
RETURN IF ( NOT _out,
    CALCULATE ( [Story | EAC In Period], REMOVEFILTERS ( DimDate ), DimDate[Date] <= _d ) )""",
    "#,##0", "Story\\Finance", "Lifetime cumulative phased EAC; ends at the EAC.")

add("Story | Finance Headline", T, f"""
VAR _bac = [Story | Budget At Completion]
VAR _eac = [Story | Finance EAC]
VAR _v = [Story | EAC Variance]
VAR _absv = ABS ( _v )
VAR _btd = [Story | Budget To Date]
VAR _a = [Story | Actual Cost]
VAR _n = [Story | Projects Over Budget]
VAR _top =
    TOPN ( 1,
        FILTER (
            ADDCOLUMNS ( VALUES ( DimProject[Id] ), "@n", CALCULATE ( MAX ( DimProject[Name] ) ),
                "@b", [Story | Budget At Completion], "@v", [Story | EAC Variance] ),
            NOT ISBLANK ( DimProject[Id] ) && [@b] > 0 && [@v] > 0 ),
        [@v], DESC, DimProject[Id], ASC )
VAR _tn = MAXX ( _top, [@n] )
VAR _tv = MAXX ( _top, [@v] )
RETURN
    IF ( ISBLANK ( _bac ) && ISBLANK ( _eac ),
        "No financial plan data in the current selection.",
        "At completion: budget " & {money("_bac")} & ", EAC " & {money("_eac")}
            & IF ( COALESCE ( _v, 0 ) >= 0, "  →  +", "  →  −" ) & {money("_absv")} & " ("
            & {pct("DIVIDE ( _v, _bac )", "+0.0%;-0.0%")} & "). To date: actuals " & {money("_a")} & " against "
            & {money("_btd")} & " budgeted (" & {pct("DIVIDE ( _a, _btd )")} & "). "
            & IF ( _n > 0,
                FORMAT ( _n, "0" ) & " project(s) have an EAC above budget; the largest overrun is " & _tn & " (+" & {money("_tv")} & ").",
                "No project has an EAC above its budget." )
    )""", folder="Story\\Headlines")

# ------------------------------------------------------------------ portfolio (plan fields on DimProject, lifetime)
add("Story | Proposed Projects", I,
    'CALCULATE ( COUNTROWS ( DimProject ), KEEPFILTERS ( DimProject[State_Value] = "Proposed" ) ) + 0',
    "#,##0", "Story\\Portfolio")
add("Story | Aligned Budget %", D, """
DIVIDE (
    CALCULATE ( SUM ( DimProject[Budget] ), KEEPFILTERS ( DimProject[StrategicAlignment_Value] IN { "Strong", "Extreme" } ) ),
    SUM ( DimProject[Budget] )
)""", "0%", "Story\\Portfolio", "Share of plan-field budget in projects rated Strong or Extreme strategic alignment.")
add("Story | Plan Budget", D, "SUM ( DimProject[Budget] )", "#,##0", "Story\\Portfolio",
    "Budget field on the project plan (DimProject), lifetime, not time-phased.")
add("Story | Plan Forecast", D, "SUM ( DimProject[Forecast] )", "#,##0", "Story\\Portfolio",
    "Forecast field on the project plan (DimProject), lifetime, not time-phased.")
add("Story | Plan Variance %", D, "DIVIDE ( [Story | Plan Forecast] - [Story | Plan Budget], [Story | Plan Budget] )",
    "+0.0%;-0.0%;0.0%", "Story\\Portfolio")
add("Story | Plan Variance Colour", T, colour3("[Story | Plan Variance %]", 0.05, 0), folder="Story\\Colours")
add("Story | Priority Score", D, "AVERAGE ( DimProject[PrioritizationScore] )", "#,##0.0", "Story\\Portfolio",
    "Prioritisation score from the OnePlan plan (DimProject[PrioritizationScore]).")
add("Story | Health Colour", T, """
SWITCH ( SELECTEDVALUE ( DimProject[OverallHealth_Value] ),
    "(1) On Track", "#1E6D6E",
    "(2) At Risk", "#D9A832",
    "(3) Off Track", "#C0392B",
    "#666666" )""", folder="Story\\Colours")
add("Story | Step Index", I, "MIN ( DimProject[ProcessStepIndex] )", "0", "Story\\Portfolio",
    "Lifecycle step order, used to sort lifecycle charts.")
add("Story | Portfolio Headline", T, f"""
VAR _n = [Story | Active Projects]
VAR _p =
    COUNTROWS ( FILTER ( VALUES ( DimProject[Portfolio Name] ),
        NOT ISBLANK ( DimProject[Portfolio Name] ) && DimProject[Portfolio Name] <> "(No portfolio)" ) )
VAR _b = [Story | Plan Budget]
VAR _al = [Story | Aligned Budget %]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Portfolio Name] ), "@b", CALCULATE ( SUM ( DimProject[Budget] ) ) ),
            NOT ISBLANK ( DimProject[Portfolio Name] ) && [@b] > 0 ),
        [@b], DESC, DimProject[Portfolio Name], ASC )
VAR _tn = MAXX ( _top, DimProject[Portfolio Name] )
VAR _tb = MAXX ( _top, [@b] )
VAR _prop = [Story | Proposed Projects]
VAR _ot = [Story | On Track %]
RETURN
    FORMAT ( _n, "0" ) & " active projects across " & FORMAT ( COALESCE ( _p, 0 ), "0" ) & " portfolios; the plans carry "
        & {money("_b")} & " of plan-field budget. " & {pct("_al")} & " of it sits in Strong/Extreme-aligned work; the largest share goes to "
        & _tn & " (" & {pct("DIVIDE ( _tb, _b )")} & "). " & {pct("_ot")} & " of active projects report On Track overall and "
        & FORMAT ( _prop, "0" ) & " proposal(s) wait in the pipeline."
""", folder="Story\\Headlines")

# ------------------------------------------------------------------ resources (organisation-wide; D-01)
# Org-wide = project filters removed; still PROJECT plans only (the blank DimProject row holds non-project plans).
_ORG_PROJ = "REMOVEFILTERS ( DimProject ), NOT ISBLANK ( DimProject[Id] )"
add("Story | Scheduled Hours", D, f"CALCULATE ( [Capacity | Total Hours Scheduled], {_ORG_PROJ} )",
    "#,##0", "Story\\Resources",
    "Scheduled resource-plan hours on project plans, organisation-wide (project slicers ignored).")
add("Story | Committed Hours", D, f"CALCULATE ( [Capacity | Committed], {_ORG_PROJ} )",
    "#,##0", "Story\\Resources",
    "Committed resource-plan hours on project plans, organisation-wide. A separate figure, not a subset of scheduled.")
add("Story | Scheduled FTE", D, f"CALCULATE ( [Project | Scheduled FTE], {_ORG_PROJ} )", "#,##0.0",
    "Story\\Resources", "Scheduled FTE on project plans, organisation-wide.")
add("Story | Project Scheduled Hours", D, f"CALCULATE ( [Capacity | Total Hours Scheduled], {PROJ} )", "#,##0",
    "Story\\Resources", "Scheduled resource-plan hours of project plans; follows project filters (demand by project).")
add("Story | Project Committed Hours", D, f"CALCULATE ( [Capacity | Total Hours Committed], {PROJ} )", "#,##0",
    "Story\\Resources", "Committed resource-plan hours of project plans; follows project filters.")
add("Story | Utilisation %", D, """
VAR _c = [Capacity | Resource Capacity]
RETURN IF ( _c > 0, DIVIDE ( COALESCE ( [Story | Scheduled Hours], 0 ), _c ) )""", "0%", "Story\\Resources",
    "Scheduled hours on project plans ÷ capacity, organisation-wide. Blank when there is no capacity.")
add("Story | Over-allocated People", I, """
VAR _t =
    CALCULATETABLE (
        ADDCOLUMNS ( SUMMARIZE ( FactCapacity, DimResource[ResourceKey], DimDate[MonthStart] ), "@u", [Story | Utilisation %] ),
        KEEPFILTERS ( DimResource[Inactive] = FALSE () )
    )
RETURN COUNTROWS ( DISTINCT ( SELECTCOLUMNS ( FILTER ( _t, [@u] > 1 ), "@k", DimResource[ResourceKey] ) ) ) + 0""",
    "#,##0", "Story\\Resources", "Active people above 100% utilisation in at least one month in view.")
add("Story | Months Over 100%", I, """
COUNTROWS (
    FILTER ( ADDCOLUMNS ( SUMMARIZE ( FactCapacity, DimDate[MonthStart] ), "@u", [Story | Utilisation %] ), [@u] > 1 )
) + 0""", "#,##0", "Story\\Resources", "Months in view in which utilisation is above 100%.")
add("Story | Free Capacity (h)", D, """
SUMX (
    SUMMARIZE ( FactCapacity, DimResource[ResourceKey], DimDate[MonthStart] ),
    VAR _c = [Capacity | Resource Capacity]
    RETURN IF ( _c > 0, MAX ( 0, _c - COALESCE ( [Story | Scheduled Hours], 0 ) ) )
)""", "#,##0", "Story\\Resources",
    "Unscheduled capacity, summed per person and month (overload in one month does not cancel bench in another).")
# Committed is NOT the firm part of Scheduled: on the tenant committed exceeds scheduled and many
# person × project × month cells are committed with nothing scheduled. Report the signed gap instead.
add("Story | Committed Gap (h)", D, """
VAR _s = [Story | Scheduled Hours]
VAR _k = [Story | Committed Hours]
RETURN IF ( ISBLANK ( _s ) && ISBLANK ( _k ), BLANK (), COALESCE ( _k, 0 ) - COALESCE ( _s, 0 ) )""",
    "+#,##0;-#,##0;0", "Story\\Resources",
    "Committed minus scheduled hours on project plans, organisation-wide. Positive = more committed than scheduled.")
add("Story | Committed Without Schedule (h)", D, f"""
VAR _t =
    CALCULATETABLE (
        SUMMARIZE ( FactResourcePlan, FactResourcePlan[ProjectKey], DimResource[ResourceKey], DimDate[MonthStart] ),
        {_ORG_PROJ}
    )
RETURN
    SUMX ( _t,
        VAR _s = COALESCE ( [Story | Scheduled Hours], 0 )
        VAR _k = COALESCE ( [Story | Committed Hours], 0 )
        RETURN IF ( _s = 0 && _k > 0, _k ) )""", "#,##0", "Story\\Resources",
    "Committed hours in person × project × month cells that have no scheduled hours at all (project plans, "
    "organisation-wide).")
add("Story | Util Colour", T, """
VAR _u = [Story | Utilisation %]
RETURN IF ( ISBLANK ( _u ), BLANK (), IF ( _u > 1, "#C0392B", IF ( _u >= 0.8, "#1E6D6E", IF ( _u >= 0.5, "#D9A832", "#9AA3AF" ) ) ) )""",
    folder="Story\\Colours")
add("Story | Util Cell Colour", T, """
VAR _u = [Story | Utilisation %]
RETURN IF ( ISBLANK ( _u ), BLANK (), IF ( _u > 1, "#F8D0CC", IF ( _u >= 0.8, "#D3EEDB", IF ( _u >= 0.5, "#FBEFD0", "#EEF0F3" ) ) ) )""",
    folder="Story\\Colours")
_TOP_ROLE = """
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimResource[Role_Value] ), "@u", [Story | Utilisation %] ),
            NOT ISBLANK ( DimResource[Role_Value] ) && [@u] > 0 ),
        [@u], DESC, DimResource[Role_Value], ASC )"""
add("Story | Resource Headline", T, f"""
VAR _r = [Resource KPI | Total Resources]
VAR _c = [Capacity | Resource Capacity]
VAR _s = [Story | Scheduled Hours]
VAR _u = [Story | Utilisation %]
VAR _o = [Story | Over-allocated People]
VAR _role = {_TOP_ROLE}
VAR _rn = TRIM ( MAXX ( _role, DimResource[Role_Value] ) )
VAR _ru = MAXX ( _role, [@u] )
VAR _k = [Story | Committed Hours]
VAR _gap = [Story | Committed Gap (h)]
VAR _absg = ABS ( COALESCE ( _gap, 0 ) )
VAR _nos = COALESCE ( [Story | Committed Without Schedule (h)], 0 )
RETURN
    IF ( COALESCE ( _c, 0 ) = 0,
        "No capacity in the current selection — pick a year or department with resource calendars.",
        {cnt("_r")} & " people offer " & FORMAT ( _c, "#,0" ) & " h of capacity; " & FORMAT ( COALESCE ( _s, 0 ), "#,0" )
            & " h are scheduled on project plans  →  " & {pct("_u")} & " utilised (organisation-wide). " & FORMAT ( _o, "0" )
            & " people go above 100% in at least one month"
            & IF ( NOT ISBLANK ( _rn ), "; the most stretched role is " & _rn & " at " & {pct("_ru")}, "" ) & ". "
            & IF ( ISBLANK ( _k ), "No committed hours are recorded.",
                "Committed hours (" & FORMAT ( _k, "#,0" ) & " h) are "
                    & IF ( _absg = 0, "equal to scheduled",
                        FORMAT ( _absg, "#,0" ) & " h " & IF ( _gap > 0, "above", "below" ) & " scheduled" )
                    & IF ( _nos > 0, "; " & FORMAT ( _nos, "#,0" ) & " h are committed where nothing is scheduled", "" )
                    & " — reconcile the resource plans." )
    )""", folder="Story\\Headlines")

# ------------------------------------------------------------------ schedule (project plans only; D-04)
def _sched(v):
    return f'CALCULATE ( COUNTROWS ( DimProject ), {ACTIVE}, KEEPFILTERS ( DimProject[ScheduleHealth_Value] = "{v}" ) )'

add("Story | On Schedule %", D, f"""
VAR _tot = CALCULATE ( COUNTROWS ( DimProject ), {ACTIVE}, KEEPFILTERS ( NOT ISBLANK ( DimProject[ScheduleHealth_Value] ) ) )
VAR _ok = {_sched("(1) On Track")}
RETURN IF ( _tot > 0, DIVIDE ( COALESCE ( _ok, 0 ), _tot ) )""", "0%", "Story\\Schedule",
    "Share of active projects whose schedule health is (1) On Track.")
add("Story | Schedule At Risk", I, _sched("(2) At Risk") + " + 0", "#,##0", "Story\\Schedule",
    "Active projects with schedule health (2) At Risk.")
add("Story | Schedule Off Track", I, _sched("(3) Off Track") + " + 0", "#,##0", "Story\\Schedule",
    "Active projects with schedule health (3) Off Track.")
add("Story | Overdue Tasks", I, f"""
COUNTROWS ( FILTER ( DimTask, {OVERDUE_TASK} ) ) + 0""", "#,##0", "Story\\Schedule",
    "Open leaf tasks on project plans (not Completed, under 100%) whose finish date has passed. Summary tasks "
    "are excluded. The one overdue definition used on every page.")
add("Story | Days Overdue", D, f"""
MAXX ( FILTER ( DimTask, {OVERDUE_TASK} ), INT ( TODAY () ) - INT ( DimTask[EndDate] ) )""", "#,##0", "Story\\Schedule",
    "Days past the finish date for the tasks counted by Story | Overdue Tasks; blank for any other task "
    "(drives the late-task lists).")
add("Story | Milestones Next 30d", I, f"""
CALCULATE (
    COUNTROWS ( DimTask ),
    KEEPFILTERS ( DimTask[Milestone] = TRUE () ),
    KEEPFILTERS ( DimTask[PercentDone] < 100 ),
    KEEPFILTERS ( DimTask[EndDate] >= TODAY () && DimTask[EndDate] < TODAY () + 31 ),
    {PROJ_TASK}
) + 0""", "#,##0", "Story\\Schedule")
add("Story | Project Slip (days)", D, """
AVERAGEX (
    FILTER ( DimProject, NOT ISBLANK ( DimProject[Summary_EndDate] ) && NOT ISBLANK ( DimProject[Summary_BaselineEndDate] ) ),
    INT ( DimProject[Summary_EndDate] ) - INT ( DimProject[Summary_BaselineEndDate] )
)""", "#,##0", "Story\\Schedule", "Average finish date minus baseline finish date, in days (projects with a baseline).")
_OPEN_TASK = ('DimTask[WorkType] = "Tasks" && DimTask[Leaf] = TRUE () && NOT ISBLANK ( DimTask[ProjectKey] ) '
              '&& DimTask[PercentDone] < 100 && DimTask[Status] <> "Completed"')
_LATE_TASK = (_OPEN_TASK + " && NOT ISBLANK ( DimTask[EndDate] ) && NOT ISBLANK ( DimTask[BaselineEndDate] )"
              " && DimTask[EndDate] > DimTask[BaselineEndDate]")
add("Story | Task Slip (days)", D, """
AVERAGEX (
    FILTER ( DimTask, DimTask[WorkType] = "Tasks" && DimTask[Leaf] = TRUE () && NOT ISBLANK ( DimTask[ProjectKey] )
        && NOT ISBLANK ( DimTask[EndDate] ) && NOT ISBLANK ( DimTask[BaselineEndDate] ) ),
    INT ( DimTask[EndDate] ) - INT ( DimTask[BaselineEndDate] )
)""", "#,##0", "Story\\Schedule", "Average task finish minus baseline finish (leaf project tasks with a baseline).")
add("Story | Slipped Tasks", I, f"""
COUNTROWS ( FILTER ( DimTask, {_LATE_TASK} ) ) + 0""", "#,##0", "Story\\Schedule",
    "Open leaf project tasks whose current finish is later than their baseline finish (summary tasks excluded).")
add("Story | Late Task Slip (days)", D, f"""
AVERAGEX ( FILTER ( DimTask, {_LATE_TASK} ), INT ( DimTask[EndDate] ) - INT ( DimTask[BaselineEndDate] ) )""",
    "#,##0", "Story\\Schedule",
    "Slip in days of the tasks counted by Story | Slipped Tasks; blank for any other task (drives the late-work register).")
add("Story | Due Colour", T, """
VAR _d = MAX ( DimTask[EndDate] )
VAR _p = MAX ( DimTask[PercentDone] )
RETURN IF ( ISBLANK ( _d ), BLANK (), IF ( _d < TODAY () && _p < 100, "#C0392B", IF ( _d < TODAY () + 14, "#D9A832", "#1F2A44" ) ) )""",
    folder="Story\\Colours")
add("Story | Late Due Colour", T, """
IF ( ISBLANK ( [Story | Late Task Slip (days)] ), BLANK (), [Story | Due Colour] )""", folder="Story\\Colours")
add("Story | Slip Colour", T, """
VAR _d = [Story | Late Task Slip (days)]
RETURN IF ( ISBLANK ( _d ), BLANK (), IF ( _d > 20, "#C0392B", IF ( _d > 0, "#D9A832", "#1E6D6E" ) ) )""",
    folder="Story\\Colours")
add("Story | Schedule Headline", T, f"""
VAR _ot = [Story | On Schedule %]
VAR _ar = [Story | Schedule At Risk]
VAR _sl = [Story | Schedule Off Track]
VAR _od = [Story | Overdue Tasks]
VAR _ms = [Story | Milestones Next 30d]
VAR _slip = [Story | Project Slip (days)]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Id] ), "@n", CALCULATE ( MAX ( DimProject[Name] ) ),
            "@d", [Story | Project Slip (days)] ), NOT ISBLANK ( DimProject[Id] ) && [@d] > 0 ),
        [@d], DESC, DimProject[Id], ASC )
RETURN
    {pct("_ot")} & " of active projects are on schedule; " & FORMAT ( _ar, "0" ) & " are at risk and " & FORMAT ( _sl, "0" )
        & " are off track. " & FORMAT ( _od, "#,0" ) & " project tasks are overdue and " & FORMAT ( _ms, "0" )
        & " milestone(s) fall due in the next 30 days. "
        & IF ( ISBLANK ( _slip ), "No baselines are set, so slippage cannot be measured yet.",
            "Projects now finish on average " & FORMAT ( ABS ( _slip ), "0" ) & " days " & IF ( _slip >= 0, "later", "earlier" )
                & " than baselined"
                & IF ( COUNTROWS ( _top ) > 0,
                    "; the biggest move is " & MAXX ( _top, [@n] ) & " (+" & FORMAT ( MAXX ( _top, [@d] ), "0" ) & " days).",
                    "." ) )
""", folder="Story\\Headlines")

# ------------------------------------------------------------------ risk (active risks on project plans; D-04)
add("Story | Active Risk Count", I, f"CALCULATE ( COUNTROWS ( DimTask ), {RISK} ) + 0", "#,##0", "Story\\Risk",
    "Active risks on project plans.")
add("Story | Open Issues", I, f"""
CALCULATE ( COUNTROWS ( DimTask ), KEEPFILTERS ( DimTask[WorkType] = "Issues" ), KEEPFILTERS ( DimTask[State] = "Active" ), {PROJ_TASK} ) + 0""",
    "#,##0", "Story\\Risk", "Active issues on project plans.")
add("Story | Critical High Risks", I, f"""
COUNTROWS (
    FILTER (
        CALCULATETABLE ( DimTask, {RISK} ),
        VAR _i = {IMPACT_SCORE}
        VAR _p = {PROB_SCORE}
        RETURN _i * _p >= {HIGH_HEAT}
    )
) + 0""", "#,##0", "Story\\Risk",
    f"Active project risks scoring {HIGH_HEAT} or more on the 4×4 impact × probability grid.")
add("Story | Risk Exposure", D, f"CALCULATE ( SUM ( DimTask[Exposure] ), {RISK} )", "#,##0", "Story\\Risk",
    "Sum of the OnePlan Exposure score (probability % × impact weight) on active project risks. A score, not money.")
add("Story | Avg Risk Probability", D, f"DIVIDE ( CALCULATE ( AVERAGE ( DimTask[Probability] ), {RISK} ), 100 )",
    "0%", "Story\\Risk")
add("Story | Unmitigated Risk %", D, f"""
VAR _all = [Story | Active Risk Count]
VAR _un =
    COUNTROWS (
        FILTER ( CALCULATETABLE ( DimTask, {RISK} ),
            LEN ( DimTask[Mitigation] ) = 0
                && LEN ( DimTask[MitigationActions] ) = 0
                && NOT ( DimTask[RiskStage] IN {{ "Mitigating", "Monitoring" }} ) ) )
RETURN IF ( _all > 0, DIVIDE ( COALESCE ( _un, 0 ), _all ) )""",
    "0%", "Story\\Risk",
    "Share of active project risks with no mitigation text, no mitigation actions and not in the Mitigating/Monitoring stage.")
add("Story | Heat Colour", T, f"""
VAR _i = SWITCH ( LEFT ( SELECTEDVALUE ( DimTask[Impact] ), 3 ), "(1)", 4, "(2)", 3, "(3)", 2, "(4)", 1, 0 )
VAR _p = SWITCH ( LEFT ( SELECTEDVALUE ( DimTask[Probability Category] ), 3 ), "(1)", 4, "(2)", 3, "(3)", 2, "(4)", 1, 0 )
VAR _sc = _i * _p
RETURN IF ( _sc = 0, BLANK (), IF ( _sc >= 12, "#E57368", IF ( _sc >= {HIGH_HEAT}, "#F2B880", IF ( _sc >= 4, "#F7E3A1", "#D3EEDB" ) ) ) )""",
    folder="Story\\Colours")
add("Story | Impact Colour", T, """
SWITCH ( LEFT ( SELECTEDVALUE ( DimTask[Impact] ), 3 ),
    "(1)", "#C0392B", "(2)", "#E8612A", "(3)", "#D9A832", "(4)", "#1E6D6E", "#666666" )""", folder="Story\\Colours")
add("Story | Risk Headline", T, f"""
VAR _r = [Story | Active Risk Count]
VAR _ch = [Story | Critical High Risks]
VAR _e = [Story | Risk Exposure]
VAR _i = [Story | Open Issues]
VAR _u = [Story | Unmitigated Risk %]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Program Name] ), "@e", [Story | Risk Exposure] ),
            NOT ISBLANK ( DimProject[Program Name] ) && [@e] > 0 ),
        [@e], DESC, DimProject[Program Name], ASC )
RETURN
    FORMAT ( _r, "0" ) & " active project risks (" & FORMAT ( _ch, "0" ) & " critical or high on impact × probability) carry an exposure score of "
        & FORMAT ( COALESCE ( _e, 0 ), "#,0" ) & ", and " & FORMAT ( _i, "0" ) & " issue(s) are open. "
        & IF ( COUNTROWS ( _top ) > 0,
            "Exposure is concentrated in " & MAXX ( _top, DimProject[Program Name] ) & " ("
                & {pct("DIVIDE ( MAXX ( _top, [@e] ), _e )")} & "). ", "" )
        & IF ( _r > 0, {pct("_u")} & " of active risks have no mitigation recorded yet.", "" )
""", folder="Story\\Headlines")

# ------------------------------------------------------------------ benefits (FactCost; D-03)
add("Story | Benefits Planned", D, f"""
CALCULATE ( SUM ( FactCost[Cost] ), KEEPFILTERS ( FactCost[CostType] = "{BENEFITS_COST_TYPE}" ), {PROJ} )""", "#,##0",
    "Story\\Benefits", "Planned benefits of project plans from the financial plan (FactCost Benefits), phased by date; "
    "split by cost category Revenue / Cost Savings.")
add("Story | Benefits Actual", D, f"""
CALCULATE ( SUM ( FactCost[Cost] ), KEEPFILTERS ( FactCost[CostType] = "{ACTUAL_BENEFITS_COST_TYPE}" ), {PROJ} )""", "#,##0",
    "Story\\Benefits", f"Realised benefits of project plans recorded in OnePlan (FactCost cost type "
    f"\"{ACTUAL_BENEFITS_COST_TYPE}\"). None are recorded yet on this tenant, so this stays blank.")
add("Story | Benefits Due To Date", D, "CALCULATE ( [Story | Benefits Planned], KEEPFILTERS ( DimDate[Date] <= TODAY () ) )",
    "#,##0", "Story\\Benefits", "Planned benefits phased up to today.")
add("Story | Benefits At Completion", D, "CALCULATE ( [Story | Benefits Planned], REMOVEFILTERS ( DimDate ) )", "#,##0",
    "Story\\Benefits", "Planned benefits over the plan lifetime.")
add("Story | Benefits Realised %", D, "DIVIDE ( [Story | Benefits Actual], [Story | Benefits Due To Date] )", "0%",
    "Story\\Benefits", "Actual benefits ÷ benefits due to date. Blank while no actuals are recorded.")
add("Story | Benefits Actual Label", T, f"""
VAR _a = [Story | Benefits Actual]
RETURN IF ( ISBLANK ( _a ), "Not recorded", {money("_a")} )""", folder="Story\\Benefits")
add("Story | Benefits Realised KPI", T, f"""
VAR _a = [Story | Benefits Actual]
VAR _d = [Story | Benefits Due To Date]
RETURN IF ( ISBLANK ( _a ), "Not recorded", IF ( COALESCE ( _d, 0 ) = 0, {money("_a")}, FORMAT ( DIVIDE ( _a, _d ), "0%" ) & " of due" ) )""",
    folder="Story\\Benefits", desc="Actual vs due-to-date benefits, or 'Not recorded' when OnePlan holds no actuals.")
add("Story | Benefit Cost Ratio", D, "DIVIDE ( [Story | Benefits At Completion], [Story | Finance EAC] )", "0.00",
    "Story\\Benefits", "Planned benefits at completion divided by EAC.")
add("Story | Ratio Colour", T, """
VAR _r = [Story | Benefit Cost Ratio]
RETURN IF ( ISBLANK ( _r ), BLANK (), IF ( _r >= 2, "#1E6D6E", IF ( _r >= 1, "#D9A832", "#C0392B" ) ) )""",
    folder="Story\\Colours")
add("Story | Benefits Headline", T, f"""
VAR _b = [Story | Benefits At Completion]
VAR _due = [Story | Benefits Due To Date]
VAR _a = [Story | Benefits Actual]
VAR _c = [Story | Finance EAC]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Id] ), "@n", CALCULATE ( MAX ( DimProject[Name] ) ),
            "@x", [Story | Benefit Cost Ratio] ), NOT ISBLANK ( DimProject[Id] ) && [@x] > 0 ),
        [@x], DESC, DimProject[Id], ASC )
VAR _neg = COUNTROWS ( FILTER ( VALUES ( DimProject[Id] ),
    NOT ISBLANK ( DimProject[Id] ) && [Story | Finance EAC] > 0 && COALESCE ( [Story | Benefits At Completion], 0 ) = 0 ) )
RETURN
    IF ( COALESCE ( _b, 0 ) = 0,
        "No planned benefits in the financial plans of this selection — capture expected benefits in OnePlan to tell the value story.",
        "The selection plans " & {money("_b")} & " of benefits against an EAC of " & {money("_c")}
            & IF ( COALESCE ( _c, 0 ) > 0, " (" & FORMAT ( DIVIDE ( _b, _c ), "0.0" ) & "× return)", "" ) & ". "
            & IF ( ISBLANK ( _a ),
                "No actual benefits recorded yet in OnePlan — realisation cannot be measured; benefits due to date: " & {money("_due")} & ".",
                "Actual benefits " & {money("_a")} & " against " & {money("_due")} & " due to date ("
                    & {pct("DIVIDE ( _a, _due )")} & ")." )
            & IF ( COUNTROWS ( _top ) > 0,
                " Best value for money: " & MAXX ( _top, [@n] ) & " (" & FORMAT ( MAXX ( _top, [@x] ), "0.0" ) & "×).", "" )
            & " " & FORMAT ( COALESCE ( _neg, 0 ), "0" ) & " project(s) with an EAC have no planned benefit."
    )""", folder="Story\\Headlines")

# ------------------------------------------------------------------ executive
add("Story | Exec Headline", T, f"""
VAR _n = [Story | Active Projects]
VAR _ot = [Story | On Track %]
VAR _vp = [Story | EAC Variance %]
VAR _u = [Story | Utilisation %]
VAR _o = [Story | Over-allocated People]
VAR _ch = [Story | Critical High Risks]
VAR _focus =
    SWITCH ( TRUE (),
        NOT ISBLANK ( _vp ) && _vp > 0.05, "cost overrun",
        _o > 0 && NOT ISBLANK ( _u ) && _u > 1, "resource overload",
        NOT ISBLANK ( _ot ) && _ot < 0.7, "delivery health",
        _ch > 5, "risk exposure",
        "keeping the course" )
RETURN
    FORMAT ( _n, "0" ) & " active projects, " & {pct("_ot")} & " on track. EAC is "
        & {pct("_vp", "+0.0%;-0.0%;0.0%")} & " versus budget at completion. Organisation-wide, people are " & {pct("_u")}
        & " utilised (" & FORMAT ( _o, "0" ) & " above 100% in at least one month) and " & FORMAT ( _ch, "0" )
        & " critical/high risks are open. This month's focus: " & _focus & "."
""", folder="Story\\Headlines")
add("Story | Exec Action Money", T, f"""
VAR _n = [Story | Projects Over Budget]
VAR _top =
    TOPN ( 1,
        FILTER (
            ADDCOLUMNS ( VALUES ( DimProject[Id] ), "@n", CALCULATE ( MAX ( DimProject[Name] ) ),
                "@b", [Story | Budget At Completion], "@v", [Story | EAC Variance] ),
            NOT ISBLANK ( DimProject[Id] ) && [@b] > 0 && [@v] > 0 ),
        [@v], DESC, DimProject[Id], ASC )
RETURN
    IF ( _n > 0,
        "1 · Money — review the " & FORMAT ( _n, "0" ) & " project(s) whose EAC is above budget — start with " & MAXX ( _top, [@n] )
            & " (+" & {money("MAXX ( _top, [@v] )")} & ").",
        "1 · Money — EAC is within budget on every project — protect the contingency and release unused budget." )
""", folder="Story\\Actions")
add("Story | Exec Action People", T, f"""
VAR _o = [Story | Over-allocated People]
VAR _role = {_TOP_ROLE}
RETURN
    IF ( _o > 0,
        "2 · People — rebalance " & FORMAT ( _o, "0" ) & " people who go above 100% in at least one month; the most stretched role is "
            & TRIM ( MAXX ( _role, DimResource[Role_Value] ) ) & " (" & {pct("MAXX ( _role, [@u] )")} & ", organisation-wide).",
        "2 · People — nobody goes above 100% in any month — there is room to pull work forward from the pipeline." )
""", folder="Story\\Actions")
add("Story | Exec Action Risk", T, """
VAR _ch = [Story | Critical High Risks]
VAR _od = [Story | Overdue Tasks]
RETURN
    IF ( _ch > 0,
        "3 · Risk — escalate " & FORMAT ( _ch, "0" ) & " critical/high risk(s) to their owners and clear " & FORMAT ( _od, "#,0" ) & " overdue task(s).",
        "3 · Risk — no critical or high risk is open — " & FORMAT ( _od, "#,0" ) & " overdue task(s) remain to clear." )
""", folder="Story\\Actions")


# ------------------------------------------------------------------ pareto & P&L (Financials II) — at completion
def _by_project(cols):
    """Per-project table across the whole selection (not the matrix row): ALLSELECTED(DimProject)."""
    return (f"FILTER ( CALCULATETABLE ( ADDCOLUMNS ( VALUES ( DimProject[Id] ), {cols} ), ALLSELECTED ( DimProject ) ), "
            "NOT ISBLANK ( DimProject[Id] ) )")


def _cum(measure):
    return f"""
VAR _cur = {measure}
VAR _id = MAX ( DimProject[Id] )
VAR _t = {_by_project('"@c", ' + measure)}
VAR _all = SUMX ( _t, [@c] )
RETURN
    IF ( ISINSCOPE ( DimProject[Name] ) && NOT ISBLANK ( _id ) && _cur > 0,
        DIVIDE ( SUMX ( FILTER ( _t, [@c] > _cur || ( [@c] = _cur && DimProject[Id] <= _id ) ), [@c] ), _all ) )"""


add("Story | Overrun", D, """
SUMX (
    FILTER ( VALUES ( DimProject[Id] ), NOT ISBLANK ( DimProject[Id] ) ),
    VAR _b = [Story | Budget At Completion]
    VAR _v = [Story | Finance EAC] - _b
    RETURN IF ( _b > 0 && _v > 0, _v )
)""", "#,##0", "Story\\Pareto",
    "Sum of positive project overruns at completion (EAC above budget, projects with a budget); underruns do not net them off.")
add("Story | Spend Cum %", D, _cum("[Story | Finance EAC]"), "0%", "Story\\Pareto",
    "Pareto line: cumulative share of EAC across the selection, projects ranked from largest to smallest.")
add("Story | Overrun Cum %", D, _cum("[Story | Overrun]"), "0%", "Story\\Pareto")
add("Story | Spend Share", D, f"""
DIVIDE ( [Story | Finance EAC], SUMX ( {_by_project('"@c", [Story | Finance EAC]')}, [@c] ) )""",
    "0.0%", "Story\\Pareto", "Share of the EAC of the whole selection.")
add("Story | Pareto Class", T, """
VAR _cum = [Story | Spend Cum %]
VAR _prev = _cum - [Story | Spend Share]
RETURN IF ( ISBLANK ( _cum ), BLANK (), IF ( _prev < 0.8, "A · top 80%", IF ( _prev < 0.95, "B · next 15%", "C · tail 5%" ) ) )""",
    folder="Story\\Pareto")
add("Story | Pareto Class Colour", T, """
VAR _c = LEFT ( [Story | Pareto Class], 1 )
RETURN SWITCH ( _c, "A", "#E8612A", "B", "#1F2A44", "C", "#9AA3AF", BLANK () )""", folder="Story\\Colours")
add("Story | Projects For 80% Spend", I, f"""
VAR _t = FILTER ( {_by_project('"@c", [Story | Finance EAC]')}, [@c] > 0 )
VAR _all = SUMX ( _t, [@c] )
VAR _r =
    ADDCOLUMNS ( _t, "@prev",
        VAR _x = [@c]
        VAR _id = DimProject[Id]
        RETURN SUMX ( FILTER ( _t, [@c] > _x || ( [@c] = _x && DimProject[Id] < _id ) ), [@c] ) )
RETURN COUNTROWS ( FILTER ( _r, COALESCE ( [@prev], 0 ) < 0.8 * _all ) ) + 0""", "#,##0", "Story\\Pareto",
    "How many of the largest projects together make up 80% of EAC.")
add("Story | Projects With Spend", I, f"""
COUNTROWS ( FILTER ( {_by_project('"@c", [Story | Finance EAC]')}, [@c] > 0 ) ) + 0""", "#,##0", "Story\\Pareto")
add("Story | Concentration %", D, "DIVIDE ( [Story | Projects For 80% Spend], [Story | Projects With Spend] )", "0%",
    "Story\\Pareto", "Share of projects that make up 80% of EAC (lower = more concentrated).")
add("Story | Top3 Overrun Share", D, f"""
VAR _t = {_by_project('"@o", [Story | Overrun]')}
RETURN DIVIDE ( SUMX ( TOPN ( 3, _t, [@o], DESC, DimProject[Id], ASC ), [@o] ), SUMX ( _t, [@o] ) )""", "0%", "Story\\Pareto")

add("Story | Plan Revenue", D, "SUM ( DimProject[EstimatedRevenue] )", "#,##0", "Story\\P&L",
    "Estimated revenue field on the plan (lifetime). Not used by the P&L, which reads the financial plan.")
add("Story | Revenue At Completion", D, f"""
CALCULATE ( SUM ( FactCost[Cost] ), KEEPFILTERS ( FactCost[CostType] = "{REVENUE_COST_TYPE}" ), REMOVEFILTERS ( DimDate ), {PROJ} )""",
    "#,##0", "Story\\P&L", "Forecasted revenue of project plans from the financial plan, lifetime. Blank while only "
    "non-project plans (e.g. engagements) carry forecasted revenue.")
add("Story | Total Value", D, """
VAR _r = [Story | Revenue At Completion]
VAR _b = [Story | Benefits At Completion]
RETURN IF ( ISBLANK ( _r ) && ISBLANK ( _b ), BLANK (), COALESCE ( _r, 0 ) + COALESCE ( _b, 0 ) )""",
    "#,##0", "Story\\P&L", "Forecasted revenue plus planned benefits at completion (FactCost).")
add("Story | Net Value", D, """
VAR _v = [Story | Total Value]
VAR _c = [Story | Finance EAC]
RETURN IF ( ISBLANK ( _v ) && ISBLANK ( _c ), BLANK (), COALESCE ( _v, 0 ) - COALESCE ( _c, 0 ) )""", "#,##0", "Story\\P&L",
    "Total value minus EAC, at completion (FactCost).")
add("Story | Net Margin %", D, "DIVIDE ( [Story | Net Value], [Story | Total Value] )", "0%;-0%;0%", "Story\\P&L")
add("Story | Net ROI", D, "DIVIDE ( [Story | Net Value], [Story | Finance EAC] )", "0%;-0%;0%", "Story\\P&L",
    "Net value as a share of EAC.")
add("Story | Net Colour", T, """
VAR _n = [Story | Net Value]
RETURN IF ( ISBLANK ( _n ), BLANK (), IF ( _n < 0, "#C0392B", IF ( [Story | Net Margin %] < 0.2, "#D9A832", "#1E6D6E" ) ) )""",
    folder="Story\\Colours")
add("Story | Pareto PnL Headline", T, f"""
VAR _k = [Story | Projects For 80% Spend]
VAR _m = [Story | Projects With Spend]
VAR _top =
    TOPN ( 1, {_by_project('"@n", CALCULATE ( MAX ( DimProject[Name] ) ), "@c", [Story | Finance EAC]')},
        [@c], DESC, DimProject[Id], ASC )
VAR _tshare = DIVIDE ( MAXX ( _top, [@c] ), SUMX ( {_by_project('"@c", [Story | Finance EAC]')}, [@c] ) )
VAR _o = [Story | Overrun]
VAR _o3 = [Story | Top3 Overrun Share]
VAR _v = [Story | Total Value]
VAR _c = [Story | Finance EAC]
VAR _n = [Story | Net Value]
VAR _p =
    ADDCOLUMNS (
        FILTER ( VALUES ( DimProject[Portfolio Name] ),
            NOT ISBLANK ( DimProject[Portfolio Name] ) && DimProject[Portfolio Name] <> "(No portfolio)" ),
        "@n", [Story | Net Value] )
VAR _best = TOPN ( 1, FILTER ( _p, NOT ISBLANK ( [@n] ) ), [@n], DESC, DimProject[Portfolio Name], ASC )
VAR _worst = TOPN ( 1, FILTER ( _p, NOT ISBLANK ( [@n] ) ), [@n], ASC, DimProject[Portfolio Name], ASC )
RETURN
    IF ( _m = 0, "No EAC in the current selection.",
        FORMAT ( _k, "0" ) & " of " & FORMAT ( _m, "0" ) & " projects (" & {pct("DIVIDE ( _k, _m )")}
            & ") make up 80% of EAC; the largest, " & MAXX ( _top, [@n] ) & ", alone takes "
            & {pct("_tshare")} & ". "
            & IF ( COALESCE ( _o, 0 ) > 0,
                "Overruns at completion total " & {money("_o")} & " and the top 3 projects carry " & {pct("_o3")} & " of it. ",
                "No project has an EAC above its budget. " )
            & "At completion: value " & {money("_v")} & " against EAC " & {money("_c")} & "  →  net "
            & {money("_n")} & " (" & {pct("DIVIDE ( _n, _v )")} & " margin)"
            & IF ( COUNTROWS ( _best ) > 0,
                "; strongest portfolio " & MAXX ( _best, DimProject[Portfolio Name] ) & " (" & {money("MAXX ( _best, [@n] )")}
                    & "), weakest " & MAXX ( _worst, DimProject[Portfolio Name] ) & " (" & {money("MAXX ( _worst, [@n] )")} & ").",
                "." )
    )""", folder="Story\\Headlines")


# ------------------------------------------------------------------ governance (FactPlanInsight, project plans only)
# FactPlanInsight keeps checks of every plan type; Power Query sets a missing ProjectKey to -1 (not NULL), so
# "ProjectKey not blank" filters nothing. Project plans = ProjectKey > 0. The governance page carries the same
# rule as a page filter; these wrappers carry it for PMO counts shown on other pages.
PMO_PROJ = "KEEPFILTERS ( FactPlanInsight[ProjectKey] > 0 )"
for _pmo in ("Plans With Open Status Report", "Plans With Unsubmitted Timesheets", "Plans Not Up To Date"):
    add(f"Story | PMO · {_pmo}", I, f"CALCULATE ( [PMO | {_pmo}], {PMO_PROJ} ) + 0", "#,##0", "Story\\Governance",
        f"[PMO | {_pmo}] on project plans only (FactPlanInsight[ProjectKey] > 0).")
