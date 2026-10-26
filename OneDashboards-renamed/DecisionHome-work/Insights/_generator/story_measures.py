"""Report-level ("thin report") measures that carry the storytelling.

They live in reportExtensions.json, so the pack works against the published
OneModel360Star model without changing it. Everything here builds only on
model measures/columns that the existing OneDashboards pack already uses.
"""


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


# ------------------------------------------------------------------ shared
add("Story | On Track %", D, """
DIVIDE (
    CALCULATE ( COUNTROWS ( DimProject ), DimProject[OverallHealth_Value] = "(1) On Track" ),
    CALCULATE ( COUNTROWS ( DimProject ), NOT ISBLANK ( DimProject[OverallHealth_Value] ) )
)""", "0%", desc="Share of projects whose overall health is (1) On Track.")

add("Story | Refreshed", T, """
VAR _t = MAX ( RefreshTime[Last Refreshed (Belgium Time)] )
RETURN IF ( ISBLANK ( _t ), "POWERED BY ONEPLAN", "POWERED BY ONEPLAN  ·  REFRESHED " & UPPER ( FORMAT ( _t, "dd mmm yyyy hh:nn" ) ) & " CET" )
""")

# ------------------------------------------------------------------ finance
add("Story | Forecast Variance", D, "[Finance | Forecast Cost] - [Finance | Budget Cost]", "#,##0",
    "Story\\Finance", "Forecast cost minus budget cost (FactCost). Positive = forecast over budget.")
add("Story | Forecast Variance %", D, "DIVIDE ( [Story | Forecast Variance], [Finance | Budget Cost] )", "+0.0%;-0.0%;0.0%",
    "Story\\Finance")
add("Story | Burn %", D, "DIVIDE ( [Finance | Actual Cost], [Finance | Budget Cost] )", "0%", "Story\\Finance",
    "Actual cost as a share of budget cost.")
add("Story | Projects Over Budget", I, """
COUNTROWS (
    FILTER (
        VALUES ( DimProject[Id] ),
        [Finance | Budget Cost] > 0 && [Finance | Forecast Cost] > [Finance | Budget Cost]
    )
) + 0""", "#,##0", "Story\\Finance")
add("Story | Variance Colour", T, """
VAR _p = [Story | Forecast Variance %]
RETURN IF ( ISBLANK ( _p ), "#666666", IF ( _p > 0.05, "#C0392B", IF ( _p > 0, "#D9A832", "#1E6D6E" ) ) )""",
    folder="Story\\Colours")
add("Story | Burn Colour", T, """
VAR _p = [Story | Burn %]
RETURN IF ( ISBLANK ( _p ), "#666666", IF ( _p > 1, "#C0392B", IF ( _p > 0.9, "#D9A832", "#1E6D6E" ) ) )""",
    folder="Story\\Colours")
add("Story | Finance Headline", T, f"""
VAR _b = [Finance | Budget Cost]
VAR _a = [Finance | Actual Cost]
VAR _f = [Finance | Forecast Cost]
VAR _v = _f - _b
VAR _absv = ABS ( _v )
VAR _n = [Story | Projects Over Budget]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Name] ), "@v", [Finance | Forecast Cost] - [Finance | Budget Cost] ), [@v] > 0 ),
        [@v], DESC )
VAR _tn = MAXX ( _top, DimProject[Name] )
VAR _tv = MAXX ( _top, [@v] )
RETURN
    IF ( ISBLANK ( _b ) && ISBLANK ( _f ),
        "No financial plan data in the current selection.",
        "Budget " & {money("_b")} & "  ·  actuals " & {money("_a")} & " (" & {pct("DIVIDE ( _a, _b )")} & " burned)  ·  forecast "
            & {money("_f")} & IF ( _v >= 0, "  →  +", "  →  −" ) & {money("_absv")} & " ("
            & {pct("DIVIDE ( _v, _b )", "+0.0%;-0.0%")} & ") versus budget. "
            & IF ( _n > 0,
                FORMAT ( _n, "0" ) & " project(s) forecast over budget; the largest overrun is " & _tn & " (+" & {money("_tv")} & ").",
                "No project is forecast over budget." )
    )""", folder="Story\\Headlines")

# ------------------------------------------------------------------ portfolio
add("Story | Proposed Projects", I, 'CALCULATE ( COUNTROWS ( DimProject ), DimProject[State_Value] = "Proposed" ) + 0',
    "#,##0", "Story\\Portfolio")
add("Story | Aligned Budget %", D, """
DIVIDE (
    CALCULATE ( SUM ( DimProject[Budget] ), DimProject[StrategicAlignment_Value] IN { "Strong", "Extreme" } ),
    SUM ( DimProject[Budget] )
)""", "0%", "Story\\Portfolio", "Share of plan budget in projects rated Strong or Extreme strategic alignment.")
add("Story | Plan Budget", D, "SUM ( DimProject[Budget] )", "#,##0", "Story\\Portfolio",
    "Budget field on the project plan (DimProject), not time-phased.")
add("Story | Plan Forecast", D, "SUM ( DimProject[Forecast] )", "#,##0", "Story\\Portfolio")
add("Story | Plan Variance %", D, "DIVIDE ( [Story | Plan Forecast] - [Story | Plan Budget], [Story | Plan Budget] )",
    "+0.0%;-0.0%;0.0%", "Story\\Portfolio")
add("Story | Plan Variance Colour", T, """
VAR _p = [Story | Plan Variance %]
RETURN IF ( ISBLANK ( _p ), "#666666", IF ( _p > 0.05, "#C0392B", IF ( _p > 0, "#D9A832", "#1E6D6E" ) ) )""",
    folder="Story\\Colours")
add("Story | Health Colour", T, """
SWITCH ( SELECTEDVALUE ( DimProject[OverallHealth_Value] ),
    "(1) On Track", "#1E6D6E",
    "(2) At Risk", "#D9A832",
    "(3) Off Track", "#C0392B",
    "#666666" )""", folder="Story\\Colours")
add("Story | Portfolio Headline", T, f"""
VAR _n = COALESCE ( [Portfolio 360 | Active Projects], 0 )
VAR _p = CALCULATE ( DISTINCTCOUNT ( DimProject[Portfolio Name] ), DimProject[Portfolio Name] <> "(No portfolio)" )
VAR _b = [Story | Plan Budget]
VAR _al = [Story | Aligned Budget %]
VAR _top =
    TOPN ( 1, ADDCOLUMNS ( VALUES ( DimProject[Portfolio Name] ), "@b", CALCULATE ( SUM ( DimProject[Budget] ) ) ), [@b], DESC )
VAR _tn = MAXX ( _top, DimProject[Portfolio Name] )
VAR _tb = MAXX ( _top, [@b] )
VAR _prop = [Story | Proposed Projects]
VAR _ot = [Story | On Track %]
RETURN
    FORMAT ( _n, "0" ) & " active projects across " & FORMAT ( COALESCE ( _p, 0 ), "0" ) & " portfolios carry " & {money("_b")}
        & " of plan budget. " & {pct("_al")} & " of that budget sits in Strong/Extreme-aligned work; the largest share goes to "
        & _tn & " (" & {pct("DIVIDE ( _tb, _b )")} & "). " & {pct("_ot")} & " of projects report On Track overall and "
        & FORMAT ( _prop, "0" ) & " proposal(s) wait in the pipeline."
""", folder="Story\\Headlines")

# ------------------------------------------------------------------ resources
add("Story | Util Colour", T, """
VAR _u = [Capacity | Resource Utilization%]
RETURN IF ( ISBLANK ( _u ) || _u = 0, "#9AA3AF", IF ( _u > 1, "#C0392B", IF ( _u >= 0.8, "#1E6D6E", IF ( _u >= 0.5, "#D9A832", "#9AA3AF" ) ) ) )""",
    folder="Story\\Colours")
add("Story | Util Cell Colour", T, """
VAR _u = [Capacity | Resource Utilization%]
RETURN IF ( ISBLANK ( _u ) || _u = 0, "#FFFFFF", IF ( _u > 1, "#F8D0CC", IF ( _u >= 0.8, "#D3EEDB", IF ( _u >= 0.5, "#FBEFD0", "#EEF0F3" ) ) ) )""",
    folder="Story\\Colours")
add("Story | Soft Demand %", D, """
DIVIDE ( [Capacity | Forecast], [Capacity | Committed] + [Capacity | Forecast] + [Resource | Scheduled] )""",
    "0%", "Story\\Resources", "Share of planned demand that is still Forecast (not Committed or Scheduled).")
add("Story | Resource Headline", T, f"""
VAR _r = [Resource KPI | Total Resources]
VAR _c = [Capacity | Resource Capacity]
VAR _s = [Capacity | Total Hours Scheduled]
VAR _u = DIVIDE ( _s, _c )
VAR _o = COALESCE ( [Capacity | Over-Allocated Resource Count], 0 )
VAR _role =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimResource[Role_Value] ), "@u", [Capacity | Resource Utilization%] ),
            NOT ISBLANK ( DimResource[Role_Value] ) && [@u] > 0 ),
        [@u], DESC )
VAR _rn = TRIM ( MAXX ( _role, DimResource[Role_Value] ) )
VAR _ru = MAXX ( _role, [@u] )
VAR _soft = [Story | Soft Demand %]
RETURN
    IF ( ISBLANK ( _c ),
        "No capacity in the current selection — pick a year or department with resource calendars.",
        {cnt("_r")} & " people offer " & FORMAT ( _c, "#,0" ) & " h of capacity; " & FORMAT ( COALESCE ( _s, 0 ), "#,0" )
            & " h are scheduled  →  " & {pct("_u")} & " utilised. " & FORMAT ( _o, "0" )
            & " people are over-allocated (above 100%)"
            & IF ( NOT ISBLANK ( _rn ), "; the most stretched role is " & _rn & " at " & {pct("_ru")}, "" ) & ". "
            & {pct("_soft")} & " of demand is still soft forecast — firm it up before committing new work."
    )""", folder="Story\\Headlines")

# ------------------------------------------------------------------ schedule
add("Story | Milestones Next 30d", I, """
CALCULATE (
    COUNTROWS ( DimTask ),
    DimTask[Milestone] = TRUE (),
    DimTask[PercentDone] < 100,
    DimTask[EndDate] >= TODAY (),
    DimTask[EndDate] < TODAY () + 31
) + 0""", "#,##0", "Story\\Schedule")
add("Story | Project Slip (days)", D, """
AVERAGEX (
    FILTER ( DimProject, NOT ISBLANK ( DimProject[Summary_EndDate] ) && NOT ISBLANK ( DimProject[Summary_BaselineEndDate] ) ),
    INT ( DimProject[Summary_EndDate] ) - INT ( DimProject[Summary_BaselineEndDate] )
)""", "#,##0", "Story\\Schedule", "Average finish date minus baseline finish date, in days (projects with a baseline).")
add("Story | Task Slip (days)", D, """
AVERAGEX (
    FILTER ( DimTask, NOT ISBLANK ( DimTask[EndDate] ) && NOT ISBLANK ( DimTask[BaselineEndDate] ) ),
    INT ( DimTask[EndDate] ) - INT ( DimTask[BaselineEndDate] )
)""", "#,##0", "Story\\Schedule")
add("Story | Slipped Tasks", I, """
COUNTROWS (
    FILTER ( DimTask,
        DimTask[WorkType] = "Tasks"
            && NOT ISBLANK ( DimTask[BaselineEndDate] )
            && DimTask[EndDate] > DimTask[BaselineEndDate]
            && DimTask[Status] <> "Completed" )
) + 0""", "#,##0", "Story\\Schedule", "Open tasks whose current finish is later than their baseline finish.")
add("Story | Due Colour", T, """
VAR _d = MAX ( DimTask[EndDate] )
VAR _p = MAX ( DimTask[PercentDone] )
RETURN IF ( ISBLANK ( _d ), "#666666", IF ( _d < TODAY () && _p < 100, "#C0392B", IF ( _d < TODAY () + 14, "#D9A832", "#1F2A44" ) ) )""",
    folder="Story\\Colours")
add("Story | Slip Colour", T, """
VAR _d = [Story | Task Slip (days)]
RETURN IF ( ISBLANK ( _d ), "#666666", IF ( _d > 20, "#C0392B", IF ( _d > 0, "#D9A832", "#1E6D6E" ) ) )""",
    folder="Story\\Colours")
add("Story | Schedule Headline", T, f"""
VAR _ot = [Portfolio 360 | On-Time Delivery %]
VAR _ar = COALESCE ( [Portfolio 360 | At-Risk Count], 0 )
VAR _sl = COALESCE ( [Portfolio 360 | Slipping Count], 0 )
VAR _od = COALESCE ( [Task | Overdue Tasks], 0 )
VAR _ms = [Story | Milestones Next 30d]
VAR _slip = [Story | Project Slip (days)]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Name] ), "@d", [Story | Project Slip (days)] ), [@d] > 0 ),
        [@d], DESC )
RETURN
    {pct("_ot")} & " of projects are on schedule; " & FORMAT ( _ar, "0" ) & " are at risk and " & FORMAT ( _sl, "0" )
        & " are slipping. " & FORMAT ( _od, "#,0" ) & " tasks are overdue and " & FORMAT ( _ms, "0" )
        & " milestone(s) fall due in the next 30 days. "
        & IF ( ISBLANK ( _slip ), "No baselines are set, so slippage cannot be measured yet.",
            "Projects now finish on average " & FORMAT ( _slip, "0" ) & " days " & IF ( _slip >= 0, "later", "earlier" )
                & " than baselined"
                & IF ( COUNTROWS ( _top ) > 0,
                    "; the biggest move is " & MAXX ( _top, DimProject[Name] ) & " (+" & FORMAT ( MAXX ( _top, [@d] ), "0" ) & " days).",
                    "." ) )
""", folder="Story\\Headlines")

# ------------------------------------------------------------------ risk
add("Story | Critical High Risks", I,
    'CALCULATE ( [Project | Active Risks], DimTask[Impact] IN { "(1) Critical", "(2) High" } ) + 0', "#,##0", "Story\\Risk")
add("Story | Risk Exposure", D,
    'CALCULATE ( SUM ( DimTask[Exposure] ), DimTask[WorkType] = "Risks", DimTask[State] = "Active" )', "#,##0", "Story\\Risk",
    "Sum of the Exposure field on active risks.")
add("Story | Avg Risk Probability", D,
    'DIVIDE ( CALCULATE ( AVERAGE ( DimTask[Probability] ), DimTask[WorkType] = "Risks", DimTask[State] = "Active" ), 100 )',
    "0%", "Story\\Risk")
add("Story | Unmitigated Risk %", D,
    'DIVIDE ( CALCULATE ( [Project | Active Risks], DimTask[RiskStage] = "Identify" ), [Project | Active Risks] )',
    "0%", "Story\\Risk", "Share of active risks still in the Identify stage (no mitigation started).")
add("Story | Active Risk Count", I, "[Project | Active Risks] + 0", "#,##0", "Story\\Risk")
add("Story | Heat Colour", T, """
VAR _i = SWITCH ( LEFT ( SELECTEDVALUE ( DimTask[Impact] ), 3 ), "(1)", 4, "(2)", 3, "(3)", 2, "(4)", 1, 0 )
VAR _p = SWITCH ( LEFT ( SELECTEDVALUE ( DimTask[Probability Category] ), 3 ), "(1)", 4, "(2)", 3, "(3)", 2, "(4)", 1, 0 )
VAR _sc = _i * _p
RETURN IF ( _sc = 0, "#FFFFFF", IF ( _sc >= 12, "#E57368", IF ( _sc >= 6, "#F2B880", IF ( _sc >= 3, "#F7E3A1", "#D3EEDB" ) ) ) )""",
    folder="Story\\Colours")
add("Story | Impact Colour", T, """
SWITCH ( LEFT ( SELECTEDVALUE ( DimTask[Impact] ), 3 ),
    "(1)", "#C0392B", "(2)", "#E8612A", "(3)", "#D9A832", "(4)", "#1E6D6E", "#666666" )""", folder="Story\\Colours")
add("Story | Risk Headline", T, f"""
VAR _r = COALESCE ( [Project | Active Risks], 0 )
VAR _ch = [Story | Critical High Risks]
VAR _e = [Story | Risk Exposure]
VAR _i = COALESCE ( [Project | Active Issues], 0 )
VAR _u = [Story | Unmitigated Risk %]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Program Name] ), "@e", [Story | Risk Exposure] ), [@e] > 0 ),
        [@e], DESC )
RETURN
    FORMAT ( _r, "0" ) & " active risks (" & FORMAT ( _ch, "0" ) & " critical or high) carry " & {money("_e")}
        & " of exposure, and " & FORMAT ( _i, "0" ) & " issue(s) are open. "
        & IF ( COUNTROWS ( _top ) > 0,
            "Exposure is concentrated in " & MAXX ( _top, DimProject[Program Name] ) & " ("
                & {pct("DIVIDE ( MAXX ( _top, [@e] ), _e )")} & "). ", "" )
        & {pct("_u")} & " of risks are still at 'Identify' with no mitigation started."
""", folder="Story\\Headlines")

# ------------------------------------------------------------------ benefits
add("Story | Benefit Cost Ratio", D, "DIVIDE ( [Benefits | Planned Benefits], [Story | Plan Budget] )", "0.00",
    "Story\\Benefits", "Planned benefits divided by plan budget.")
add("Story | Ratio Colour", T, """
VAR _r = [Story | Benefit Cost Ratio]
RETURN IF ( ISBLANK ( _r ), "#666666", IF ( _r >= 2, "#1E6D6E", IF ( _r >= 1, "#D9A832", "#C0392B" ) ) )""",
    folder="Story\\Colours")
add("Story | Benefits Headline", T, f"""
VAR _b = [Benefits | Planned Benefits]
VAR _c = [Story | Plan Budget]
VAR _r = [Benefits | Realized Benefits]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Name] ), "@x", [Story | Benefit Cost Ratio] ), [@x] > 0 ),
        [@x], DESC )
VAR _neg = COUNTROWS ( FILTER ( VALUES ( DimProject[Id] ), [Story | Plan Budget] > 0 && COALESCE ( [Benefits | Planned Benefits], 0 ) = 0 ) )
RETURN
    IF ( COALESCE ( _b, 0 ) = 0,
        "No benefits are recorded on the plans in this selection — capture expected benefits in OnePlan to tell the value story.",
        "The selection plans " & {money("_b")} & " of benefits on " & {money("_c")} & " of budget ("
            & FORMAT ( DIVIDE ( _b, _c ), "0.0" ) & "× return). Pro-rata on progress, " & {money("_r")} & " ("
            & {pct("DIVIDE ( _r, _b )")} & ") is realised so far. Best value for money: " & MAXX ( _top, DimProject[Name] )
            & " (" & FORMAT ( MAXX ( _top, [@x] ), "0.0" ) & "×). " & FORMAT ( COALESCE ( _neg, 0 ), "0" )
            & " funded project(s) have no benefit recorded."
    )""", folder="Story\\Headlines")

# ------------------------------------------------------------------ executive
add("Story | Exec Headline", T, f"""
VAR _n = COALESCE ( [Portfolio 360 | Active Projects], 0 )
VAR _ot = [Story | On Track %]
VAR _vp = [Story | Forecast Variance %]
VAR _u = [Capacity | Resource Utilization%]
VAR _o = COALESCE ( [Capacity | Over-Allocated Resource Count], 0 )
VAR _ch = [Story | Critical High Risks]
VAR _focus =
    SWITCH ( TRUE (),
        _vp > 0.05, "cost overrun",
        _o > 0 && _u > 1, "resource overload",
        _ot < 0.7, "delivery health",
        _ch > 5, "risk exposure",
        "keeping the course" )
RETURN
    FORMAT ( _n, "0" ) & " active projects, " & {pct("_ot")} & " on track. Forecast is "
        & {pct("_vp", "+0.0%;-0.0%;0.0%")} & " versus budget, people are " & {pct("_u")} & " utilised ("
        & FORMAT ( _o, "0" ) & " over-allocated) and " & FORMAT ( _ch, "0" )
        & " critical/high risks are open. This month's focus: " & _focus & "."
""", folder="Story\\Headlines")
add("Story | Exec Action Money", T, f"""
VAR _n = [Story | Projects Over Budget]
VAR _top =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Name] ), "@v", [Story | Forecast Variance] ), [@v] > 0 ),
        [@v], DESC )
RETURN
    IF ( _n > 0,
        "1 · Money — review the " & FORMAT ( _n, "0" ) & " project(s) forecast over budget — start with " & MAXX ( _top, DimProject[Name] )
            & " (+" & {money("MAXX ( _top, [@v] )")} & ").",
        "1 · Money — spend is within budget on every project — protect the contingency and release unused budget." )
""", folder="Story\\Actions")
add("Story | Exec Action People", T, f"""
VAR _o = COALESCE ( [Capacity | Over-Allocated Resource Count], 0 )
VAR _role =
    TOPN ( 1,
        FILTER ( ADDCOLUMNS ( VALUES ( DimResource[Role_Value] ), "@u", [Capacity | Resource Utilization%] ),
            NOT ISBLANK ( DimResource[Role_Value] ) && [@u] > 0 ),
        [@u], DESC )
RETURN
    IF ( _o > 0,
        "2 · People — rebalance " & FORMAT ( _o, "0" ) & " over-allocated people; the most stretched role is "
            & TRIM ( MAXX ( _role, DimResource[Role_Value] ) ) & " (" & {pct("MAXX ( _role, [@u] )")} & ").",
        "2 · People — nobody is over-allocated — there is room to pull work forward from the pipeline." )
""", folder="Story\\Actions")
add("Story | Exec Action Risk", T, """
VAR _ch = [Story | Critical High Risks]
VAR _od = COALESCE ( [Task | Overdue Tasks], 0 )
RETURN
    IF ( _ch > 0,
        "3 · Risk — escalate " & FORMAT ( _ch, "0" ) & " critical/high risk(s) to their owners and clear " & FORMAT ( _od, "#,0" ) & " overdue task(s).",
        "3 · Risk — no critical or high risk is open — " & FORMAT ( _od, "#,0" ) & " overdue task(s) remain to clear." )
""", folder="Story\\Actions")

# ------------------------------------------------------------------ pareto & P&L (Financials II)
def _cum(measure, column):
    return f"""
VAR _cur = {measure}
VAR _t = ADDCOLUMNS ( ALLSELECTED ( {column} ), "@c", {measure} )
VAR _all = SUMX ( _t, [@c] )
RETURN
    IF ( ISINSCOPE ( {column} ) && _cur > 0, DIVIDE ( SUMX ( FILTER ( _t, [@c] >= _cur ), [@c] ), _all ) )"""


add("Story | Overrun", D, """
SUMX ( VALUES ( DimProject[Name] ), VAR _v = [Story | Forecast Variance] RETURN IF ( _v > 0, _v ) )""", "#,##0",
    "Story\Pareto", "Sum of positive project overruns (forecast above budget); underruns do not net them off.")
add("Story | Spend Cum %", D, _cum("[Finance | Forecast Cost]", "DimProject[Name]"), "0%", "Story\Pareto",
    "Pareto line: cumulative share of forecast cost, projects ranked from largest to smallest.")
add("Story | Overrun Cum %", D, _cum("[Story | Overrun]", "DimProject[Name]"), "0%", "Story\Pareto")
add("Story | Spend Share", D, """
DIVIDE ( [Finance | Forecast Cost], CALCULATE ( [Finance | Forecast Cost], ALLSELECTED ( DimProject[Name] ) ) )""",
    "0.0%", "Story\Pareto")
add("Story | Pareto Class", T, """
VAR _cum = [Story | Spend Cum %]
VAR _prev = _cum - [Story | Spend Share]
RETURN IF ( ISBLANK ( _cum ), BLANK (), IF ( _prev < 0.8, "A · top 80%", IF ( _prev < 0.95, "B · next 15%", "C · tail 5%" ) ) )""",
    folder="Story\Pareto")
add("Story | Pareto Class Colour", T, """
VAR _c = LEFT ( [Story | Pareto Class], 1 )
RETURN SWITCH ( _c, "A", "#E8612A", "B", "#1F2A44", "C", "#9AA3AF", "#666666" )""", folder="Story\Colours")
add("Story | Projects For 80% Spend", I, """
VAR _t = FILTER ( ADDCOLUMNS ( ALLSELECTED ( DimProject[Name] ), "@c", [Finance | Forecast Cost] ), [@c] > 0 )
VAR _all = SUMX ( _t, [@c] )
VAR _r = ADDCOLUMNS ( _t, "@prev", VAR _x = [@c] RETURN SUMX ( FILTER ( _t, [@c] > _x ), [@c] ) )
RETURN COUNTROWS ( FILTER ( _r, [@prev] < 0.8 * _all ) ) + 0""", "#,##0", "Story\Pareto",
    "How many of the largest projects together make up 80% of forecast cost.")
add("Story | Projects With Spend", I, """
COUNTROWS ( FILTER ( ALLSELECTED ( DimProject[Name] ), [Finance | Forecast Cost] > 0 ) ) + 0""", "#,##0", "Story\Pareto")
add("Story | Concentration %", D, "DIVIDE ( [Story | Projects For 80% Spend], [Story | Projects With Spend] )", "0%",
    "Story\Pareto", "Share of projects that make up 80% of forecast cost (lower = more concentrated).")
add("Story | Top3 Overrun Share", D, """
VAR _t = ADDCOLUMNS ( ALLSELECTED ( DimProject[Name] ), "@o", [Story | Overrun] )
RETURN DIVIDE ( SUMX ( TOPN ( 3, _t, [@o], DESC ), [@o] ), SUMX ( _t, [@o] ) )""", "0%", "Story\Pareto")

add("Story | Plan Revenue", D, "SUM ( DimProject[EstimatedRevenue] )", "#,##0", "Story\P&L",
    "Estimated revenue recorded on the plan.")
add("Story | Total Value", D, "COALESCE ( [Story | Plan Revenue], 0 ) + COALESCE ( [Benefits | Planned Benefits], 0 )",
    "#,##0", "Story\P&L", "Revenue plus planned benefits: everything the plan promises back.")
add("Story | Net Value", D, "[Story | Total Value] - COALESCE ( [Story | Plan Forecast], 0 )", "#,##0", "Story\P&L",
    "Total value minus forecast cost at completion (plan fields, lifetime).")
add("Story | Net Margin %", D, "DIVIDE ( [Story | Net Value], [Story | Total Value] )", "0%;-0%;0%", "Story\P&L")
add("Story | Net ROI", D, "DIVIDE ( [Story | Net Value], [Story | Plan Forecast] )", "0%;-0%;0%", "Story\P&L",
    "Net value as a share of forecast cost.")
add("Story | Net Colour", T, """
VAR _n = [Story | Net Value]
RETURN IF ( ISBLANK ( _n ), "#666666", IF ( _n < 0, "#C0392B", IF ( [Story | Net Margin %] < 0.2, "#D9A832", "#1E6D6E" ) ) )""",
    folder="Story\Colours")
add("Story | Pareto PnL Headline", T, f"""
VAR _k = [Story | Projects For 80% Spend]
VAR _m = [Story | Projects With Spend]
VAR _top =
    TOPN ( 1, ADDCOLUMNS ( ALLSELECTED ( DimProject[Name] ), "@c", [Finance | Forecast Cost] ), [@c], DESC )
VAR _tshare = DIVIDE ( MAXX ( _top, [@c] ), CALCULATE ( [Finance | Forecast Cost], ALLSELECTED ( DimProject[Name] ) ) )
VAR _o = [Story | Overrun]
VAR _o3 = [Story | Top3 Overrun Share]
VAR _v = [Story | Total Value]
VAR _c = [Story | Plan Forecast]
VAR _n = [Story | Net Value]
VAR _p =
    ADDCOLUMNS ( FILTER ( VALUES ( DimProject[Portfolio Name] ), DimProject[Portfolio Name] <> "(No portfolio)" ),
        "@n", [Story | Net Value] )
VAR _best = TOPN ( 1, _p, [@n], DESC )
VAR _worst = TOPN ( 1, _p, [@n], ASC )
RETURN
    IF ( _m = 0, "No forecast cost in the current selection.",
        FORMAT ( _k, "0" ) & " of " & FORMAT ( _m, "0" ) & " projects (" & {pct("DIVIDE ( _k, _m )")}
            & ") drive 80% of forecast spend; the largest, " & MAXX ( _top, DimProject[Name] ) & ", alone takes "
            & {pct("_tshare")} & ". "
            & IF ( COALESCE ( _o, 0 ) > 0,
                "Overruns total " & {money("_o")} & " and the top 3 projects carry " & {pct("_o3")} & " of it. ",
                "No project is forecast over budget. " )
            & "Lifetime P&L: value " & {money("_v")} & " against forecast cost " & {money("_c")} & "  →  net "
            & {money("_n")} & " (" & {pct("DIVIDE ( _n, _v )")} & " margin)"
            & IF ( COUNTROWS ( _best ) > 0,
                "; strongest portfolio " & MAXX ( _best, DimProject[Portfolio Name] ) & " (" & {money("MAXX ( _best, [@n] )")}
                    & "), weakest " & MAXX ( _worst, DimProject[Portfolio Name] ) & " (" & {money("MAXX ( _worst, [@n] )")} & ").",
                "." )
    )""", folder="Story\Headlines")
