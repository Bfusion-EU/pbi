"""5d · Plan vs Baseline — "Is the plan still the plan we approved?"

Compares the current work plan with a baseline, per project and for the portfolio in view:
cost, days (start / finish / duration), hours and average FTE, plus a smart signal per project.

Which baseline
  The model holds one baseline per plan (DimProject[Summary_Baseline*], the current one). Every status report
  also stores the baseline that was in force when it was written (FactStatusReport[Summary_Baseline*], keyed by
  Summary_LastBaselineDate = the moment the baseline was saved). So each distinct Summary_LastBaselineDate of a
  project is one saved baseline version.
  - Baseline slicer empty   -> compare with the CURRENT baseline (DimProject).
  - Baseline slicer picked  -> every project is compared with the baseline it had IN FORCE at that moment: its latest
                               baseline saved on or before the picked date (values as the latest status report under
                               that baseline recorded them; the current DimProject baseline if that is the one).
                               Projects that had no baseline yet at that moment drop out. Several picks = the latest.
  FactStatusReport -> DimProject is single-direction, so the slicer narrows nothing but the baseline values.
  Task-level baselines only exist for the current baseline (DimTask[Baseline*]).

Units
  Start / finish shift: calendar days (same rule as the Gantt slip label). Duration: OnePlan work-plan duration
  (working days). FTE: average FTE over the plan = hours / (duration × [Resource | FTE Hours per Day]).
  Cost, hours and FTE totals are like-for-like: only projects whose baseline holds that number.
"""
import pbir
from pbir import (n, qref, headline, chart, table_style, cf_font, slicer, P, M, C, b, measure_fill, legend, labels_on,
                  f_in, f_not_blank, NAVY, ORANGE, TEAL, AMBER, RED, GREY, MUTED, BORDER, INK)
import pages
from pages import DP, DT, section, kpi_row, next_chapter, analytic_page, Y1, Y1K, YNEXT, PROJECT_TASKS
from story_measures import add, money, T, D, I

KEY = "baseline"
PX = "Story | Baseline · "
FOLDER = "Story\\Baseline"
DTM = "DateTime"


def bm(name):
    return PX + name


def _add(name, dtype, expr, fmt=None, desc=None, folder=FOLDER):
    add(bm(name), dtype, expr, fmt, folder, desc)


SEL = "ISFILTERED ( FactStatusReport[Summary_LastBaselineDate] )"
PROJECTS = "FILTER ( VALUES ( DimProject[Id] ), NOT ISBLANK ( DimProject[Id] ) )"
SIGNED = "+#,##0;-#,##0;0"
SIGNED_PCT = "+0.0%;-0.0%;0.0%"


# The picked moment: latest selected save date, read across all projects (each save belongs to one project).
PICK = """CALCULATE ( MAX ( FactStatusReport[Summary_LastBaselineDate] ),
        REMOVEFILTERS ( DimProject ), REMOVEFILTERS ( DimProgram ), REMOVEFILTERS ( DimPortfolio ), REMOVEFILTERS ( DimDate ) )"""


def bl_value(col):
    """Value of DimProject/FactStatusReport[col] in the compared baseline, for one project (blank otherwise)."""
    return f"""
VAR _sel = {SEL}
VAR _pick = IF ( _sel, {PICK} )
VAR _cur = MAX ( DimProject[Summary_LastBaselineDate] )
VAR _hist =
    IF ( _sel,
        CALCULATE ( MAX ( FactStatusReport[Summary_LastBaselineDate] ),
            FactStatusReport[Summary_LastBaselineDate] <= _pick, REMOVEFILTERS ( DimDate ) ) )
VAR _useCur = NOT _sel || ( NOT ISBLANK ( _cur ) && _cur <= _pick && ( ISBLANK ( _hist ) || _cur > _hist ) )
VAR _r =
    IF ( NOT ISBLANK ( _hist ),
        CALCULATE ( MAX ( FactStatusReport[Report_ReportEnd] ),
            FactStatusReport[Summary_LastBaselineDate] = _hist, REMOVEFILTERS ( DimDate ) ) )
RETURN
    IF ( HASONEVALUE ( DimProject[Id] ),
        IF ( _useCur,
            MAX ( DimProject[{col}] ),
            IF ( NOT ISBLANK ( _hist ),
                CALCULATE ( MAX ( FactStatusReport[{col}] ), FactStatusReport[Summary_LastBaselineDate] = _hist,
                    FactStatusReport[Report_ReportEnd] = _r, REMOVEFILTERS ( DimDate ) ) ) ) )"""


def plan_value(col):
    return f"IF ( HASONEVALUE ( DimProject[Id] ), MAX ( DimProject[{col}] ) )"


# ====================================================================== per-project building blocks
_add("Baseline Saved On", DTM, bl_value("Summary_LastBaselineDate"), "dd mmm yyyy",
     "When the compared baseline was saved: the one in force on the picked date, or the plan's current one.")
_add("Baseline Start", DTM, bl_value("Summary_BaselineStartDate"), "dd mmm yyyy")
_add("Baseline Finish", DTM, bl_value("Summary_BaselineEndDate"), "dd mmm yyyy")
_add("Baseline Duration", D, bl_value("Summary_BaselineDuration"), "#,##0", "Baseline duration in working days.")
_add("Baseline Hours (project)", D, bl_value("Summary_BaselineEffort"), "#,##0")
_add("Baseline Cost (project)", D, bl_value("Summary_BaselineTotalCost"), "#,##0")
_add("Plan Start", DTM, plan_value("Summary_StartDate"), "dd mmm yyyy")
_add("Plan Finish", DTM, plan_value("Summary_EndDate"), "dd mmm yyyy")
_add("Plan Duration", D, plan_value("Summary_Duration"), "#,##0", "Current work-plan duration in working days.")
_add("Plan Hours (project)", D, plan_value("Summary_Effort"), "#,##0")
_add("Plan Cost (project)", D, plan_value("Summary_TotalCost"), "#,##0")


def per_project(expr):
    """Average of a per-project expression over the projects in view (blank projects ignored)."""
    return f"AVERAGEX ( {PROJECTS}, {expr} )"


# ---------------------------------------------------------------- schedule deviations (avg over projects)
_add("Start Shift (days)", D, per_project(f"""
    VAR _p = [{bm("Plan Start")}]
    VAR _b = [{bm("Baseline Start")}]
    RETURN IF ( NOT ISBLANK ( _p ) && NOT ISBLANK ( _b ), INT ( _p ) - INT ( _b ) )"""), SIGNED,
     "Plan start minus baseline start, calendar days (average over the projects in view).")
_add("Finish Slip (days)", D, per_project(f"""
    VAR _p = [{bm("Plan Finish")}]
    VAR _b = [{bm("Baseline Finish")}]
    RETURN IF ( NOT ISBLANK ( _p ) && NOT ISBLANK ( _b ), INT ( _p ) - INT ( _b ) )"""), SIGNED,
     "Plan finish minus baseline finish, calendar days (average over the projects in view). Positive = later.")
_add("Duration Change (wd)", D, per_project(f"""
    VAR _p = [{bm("Plan Duration")}]
    VAR _b = [{bm("Baseline Duration")}]
    RETURN IF ( NOT ISBLANK ( _p ) && NOT ISBLANK ( _b ), _p - _b )"""), SIGNED,
     "Plan duration minus baseline duration, working days (average over the projects in view).")

# ---------------------------------------------------------------- money / hours / FTE (like-for-like sums)
_add("Plan Cost", D, f"SUMX ( {PROJECTS}, [{bm('Plan Cost (project)')}] )", "#,##0",
     "Current work-plan total cost (all projects in view).")
_add("Plan Hours", D, f"SUMX ( {PROJECTS}, [{bm('Plan Hours (project)')}] )", "#,##0",
     "Current work-plan effort in hours (all projects in view).")
_add("Baseline Cost", D, f"SUMX ( {PROJECTS}, VAR _b = [{bm('Baseline Cost (project)')}] RETURN IF ( _b > 0, _b ) )",
     "#,##0", "Baseline total cost, projects whose baseline holds a cost.")
_add("Plan Cost vs Baseline", D,
     f"SUMX ( {PROJECTS}, IF ( [{bm('Baseline Cost (project)')}] > 0, [{bm('Plan Cost (project)')}] ) )", "#,##0",
     "Plan cost of the projects that have a cost baseline (like-for-like with Baseline Cost).")
_add("Cost Variance", D, f"""
VAR _b = [{bm("Baseline Cost")}]
RETURN IF ( NOT ISBLANK ( _b ), [{bm("Plan Cost vs Baseline")}] - _b )""", "+#,##0;-#,##0;0",
     "Plan cost minus baseline cost (like-for-like).")
_add("Cost Variance %", D, f'DIVIDE ( [{bm("Cost Variance")}], [{bm("Baseline Cost")}] )', SIGNED_PCT)
_add("Baseline Hours", D, f"SUMX ( {PROJECTS}, VAR _b = [{bm('Baseline Hours (project)')}] RETURN IF ( _b > 0, _b ) )",
     "#,##0", "Baseline effort in hours, projects whose baseline holds hours.")
_add("Plan Hours vs Baseline", D,
     f"SUMX ( {PROJECTS}, IF ( [{bm('Baseline Hours (project)')}] > 0, [{bm('Plan Hours (project)')}] ) )", "#,##0",
     "Plan hours of the projects that have an hours baseline.")
_add("Hours Variance", D, f"""
VAR _b = [{bm("Baseline Hours")}]
RETURN IF ( NOT ISBLANK ( _b ), [{bm("Plan Hours vs Baseline")}] - _b )""", SIGNED)
_add("Hours Variance %", D, f'DIVIDE ( [{bm("Hours Variance")}], [{bm("Baseline Hours")}] )', SIGNED_PCT)

FTE_ONE = """
    VAR _h = {h}
    VAR _d = {d}
    RETURN IF ( _h > 0 && _d > 0, DIVIDE ( _h, _d * [Resource | FTE Hours per Day] ) )"""
_add("Plan FTE", D, f"""SUMX ( {PROJECTS},
    IF ( [{bm("Baseline Hours (project)")}] > 0 && [{bm("Baseline Duration")}] > 0, {FTE_ONE.format(
        h=f"[{bm('Plan Hours (project)')}]", d=f"[{bm('Plan Duration')}]")} ) )""", "#,##0.0",
     "Average FTE the current plan needs (hours ÷ duration × hours per day), projects with an hours baseline.")
_BL_FTE_ONE = FTE_ONE.format(h=f"[{bm('Baseline Hours (project)')}]", d=f"[{bm('Baseline Duration')}]")
_add("Baseline FTE", D, f"""SUMX ( {PROJECTS},
    IF ( [{bm("Plan Hours (project)")}] > 0 && [{bm("Plan Duration")}] > 0, {_BL_FTE_ONE} ) )""", "#,##0.0",
     "Average FTE the baseline assumed (baseline hours ÷ baseline duration × hours per day).")
_add("FTE Variance %", D, f"""
VAR _b = [{bm("Baseline FTE")}]
RETURN IF ( _b > 0, DIVIDE ( [{bm("Plan FTE")}] - _b, _b ) )""", SIGNED_PCT,
     "Change in average FTE intensity: + = the same plan now needs more people at once.")

# ---------------------------------------------------------------- counts
_add("Projects", I, f"COUNTROWS ( {PROJECTS} ) + 0", "#,##0")
_add("Baselined Projects", I,
     f"COUNTROWS ( FILTER ( {PROJECTS}, NOT ISBLANK ( [{bm('Baseline Finish')}] ) ) ) + 0", "#,##0",
     "Projects in view that have the compared baseline.")
_add("Coverage", T, f"""
VAR _b = [{bm("Baselined Projects")}]
VAR _n = [{bm("Projects")}]
RETURN FORMAT ( _b, "0" ) & " of " & FORMAT ( _n, "0" )""", desc="Baselined projects out of the projects in view.")
_add("Coverage Colour", T, f"""
VAR _p = DIVIDE ( [{bm("Baselined Projects")}], [{bm("Projects")}] )
RETURN IF ( ISBLANK ( _p ), "{MUTED}", IF ( _p < 0.5, "{RED}", IF ( _p < 0.9, "{AMBER}", "{TEAL}" ) ) )""",
     folder=FOLDER + "\\Colours")
_add("Late Projects", I, f"COUNTROWS ( FILTER ( {PROJECTS}, [{bm('Finish Slip (days)')}] > 0 ) ) + 0", "#,##0",
     "Projects whose plan finish is later than the compared baseline finish.")
_add("Versions", I, """
VAR _hist =
    SELECTCOLUMNS (
        CALCULATETABLE ( DISTINCT ( FactStatusReport[Summary_LastBaselineDate] ),
            REMOVEFILTERS ( FactStatusReport[Summary_LastBaselineDate] ), REMOVEFILTERS ( DimDate ) ),
        "@d", FactStatusReport[Summary_LastBaselineDate] )
VAR _cur = ROW ( "@d", MAX ( DimProject[Summary_LastBaselineDate] ) )
RETURN IF ( HASONEVALUE ( DimProject[Id] ), COUNTROWS ( FILTER ( DISTINCT ( UNION ( _hist, _cur ) ), NOT ISBLANK ( [@d] ) ) ) )""",
     "#,##0", "Baselines saved for the project: the current one plus earlier ones seen in its status reports.")
_add("Rebaselined Projects", I, f"COUNTROWS ( FILTER ( {PROJECTS}, [{bm('Versions')}] > 1 ) ) + 0", "#,##0")

# ---------------------------------------------------------------- colours
_add("Slip Colour", T, f"""
VAR _d = [{bm("Finish Slip (days)")}]
RETURN IF ( ISBLANK ( _d ), "{MUTED}", IF ( _d > 10, "{RED}", IF ( _d > 0, "{AMBER}", "{TEAL}" ) ) )""",
     folder=FOLDER + "\\Colours")
_add("Late Colour", T, f'IF ( [{bm("Late Projects")}] > 0, "{RED}", "{TEAL}" )', folder=FOLDER + "\\Colours")
for _nm, _m in [("Cost", "Cost Variance %"), ("Hours", "Hours Variance %")]:
    _add(f"{_nm} Colour", T, f"""
VAR _p = [{bm(_m)}]
RETURN IF ( ISBLANK ( _p ), "{MUTED}", IF ( _p > 0.05, "{RED}", IF ( _p > 0, "{AMBER}", "{TEAL}" ) ) )""",
         folder=FOLDER + "\\Colours")
_add("FTE Colour", T, f"""
VAR _p = ABS ( [{bm("FTE Variance %")}] )
RETURN IF ( ISBLANK ( _p ), "{MUTED}", IF ( _p > 0.25, "{RED}", IF ( _p > 0.1, "{AMBER}", "{TEAL}" ) ) )""",
     folder=FOLDER + "\\Colours", desc="FTE intensity moved more than 10% (amber) or 25% (red), either way.")

# ---------------------------------------------------------------- smart signal per project
_add("Signal", T, f"""
VAR _one = HASONEVALUE ( DimProject[Id] ) && NOT ISBLANK ( SELECTEDVALUE ( DimProject[Id] ) )
VAR _bf = [{bm("Baseline Finish")}]
VAR _slip = [{bm("Finish Slip (days)")}]
VAR _hp = DIVIDE ( [{bm("Plan Hours (project)")}] - [{bm("Baseline Hours (project)")}], [{bm("Baseline Hours (project)")}] )
VAR _cp = DIVIDE ( [{bm("Plan Cost (project)")}] - [{bm("Baseline Cost (project)")}], [{bm("Baseline Cost (project)")}] )
VAR _fp = [{bm("FTE Variance %")}]
VAR _age = IF ( NOT ISBLANK ( [{bm("Baseline Saved On")}] ), INT ( TODAY () ) - INT ( [{bm("Baseline Saved On")}] ) )
VAR _late = _slip > 0
VAR _early = _slip < 0
VAR _more = _hp > 0.05
VAR _same = NOT ISBLANK ( _hp ) && ABS ( _hp ) <= 0.05
VAR _main =
    SWITCH ( TRUE (),
        _late && _more, "▲ Scope growth: +" & FORMAT ( _slip, "0" ) & " d, " & FORMAT ( _hp, "+0%" ) & " hours",
        _late && _same, "▲ Stretched: +" & FORMAT ( _slip, "0" ) & " d for the same work"
            & IF ( ISBLANK ( _fp ), "", " (FTE " & FORMAT ( _fp, "+0%;-0%" ) & ")" ),
        _late, "▲ Late: +" & FORMAT ( _slip, "0" ) & " d" & IF ( ISBLANK ( _hp ), "", ", " & FORMAT ( _hp, "+0%;-0%" ) & " hours" ),
        _early, "▼ Ahead: " & FORMAT ( _slip, "0" ) & " d" & IF ( _more, ", " & FORMAT ( _hp, "+0%" ) & " hours", "" ),
        _more, "▲ Compressed: " & FORMAT ( _hp, "+0%" ) & " hours, same finish"
            & IF ( ISBLANK ( _fp ), "", " (FTE " & FORMAT ( _fp, "+0%;-0%" ) & ")" ),
        _cp > 0.05, "▲ Cost up " & FORMAT ( _cp, "+0%" ) & ", dates held",
        "● On baseline" )
RETURN
    IF ( _one,
        IF ( ISBLANK ( _bf ),
            IF ( {SEL}, "◇ No baseline on that date", "◇ No baseline" ),
            _main
                & IF ( NOT ( [{bm("Baseline Cost (project)")}] > 0 ), "  ·  no cost in baseline record", "" )
                & IF ( _age > 90 && _main <> "● On baseline", "  ·  baseline " & FORMAT ( _age, "0" ) & " d old", "" ) ) )""",
     desc="Smart indicator per project: the pattern behind the deviation (scope growth, stretched, compressed, ahead).")
_add("Signal Colour", T, f"""
VAR _s = LEFT ( [{bm("Signal")}], 1 )
RETURN SWITCH ( _s, "▲", IF ( [{bm("Finish Slip (days)")}] > 10, "{RED}", "{AMBER}" ), "▼", "{TEAL}", "●", "{TEAL}",
    "◇", "{GREY}", BLANK () )""", folder=FOLDER + "\\Colours")
_add("Next Step", T, f"""
VAR _s = [{bm("Signal")}]
RETURN
    SWITCH ( TRUE (),
        ISBLANK ( _s ), BLANK (),
        LEFT ( _s, 14 ) = "▲ Scope growth", "Raise a change request, or re-baseline with the sponsor",
        LEFT ( _s, 11 ) = "▲ Stretched", "Recover the date (resources, scope) or agree a new baseline",
        LEFT ( _s, 6 ) = "▲ Late", "Recover the date or agree a new baseline with the sponsor",
        LEFT ( _s, 12 ) = "▲ Compressed", "Check the team can absorb the extra load",
        LEFT ( _s, 9 ) = "▲ Cost up", "Explain the cost change before the next board",
        LEFT ( _s, 7 ) = "▼ Ahead", "Release capacity or pull the next milestones forward",
        _s = "◇ No baseline", "Save a baseline at gate approval",
        LEFT ( _s, 1 ) = "◇", "Pick a later date or clear the Baseline slicer",
        "None" )""", desc="What to do about the signal.")

# ---------------------------------------------------------------- KPI card texts (no "(Blank)" on a card)
for _m, _f, _none in [("Finish Slip (days)", '"+0;-0;0"', "no baseline"), ("Start Shift (days)", '"+0;-0;0"', "no baseline"),
                      ("Duration Change (wd)", '"+0;-0;0"', "no baseline"), ("Cost Variance %", '"+0.0%;-0.0%;0.0%"', "no cost baseline"),
                      ("Hours Variance %", '"+0.0%;-0.0%;0.0%"', "no hours baseline"),
                      ("FTE Variance %", '"+0%;-0%;0%"', "no hours baseline")]:
    _add(f"{_m} · Card", T, f'VAR _v = [{bm(_m)}] RETURN IF ( ISBLANK ( _v ), "{_none}", FORMAT ( _v, {_f} ) )',
         folder=FOLDER + "\\Cards")

# ---------------------------------------------------------------- task level (current baseline only)
TASK_MOVED = """
VAR _m =
    COUNTROWS (
        FILTER ( DimTask,
            NOT ISBLANK ( DimTask[BaselineEndDate] ) && NOT ISBLANK ( DimTask[EndDate] )
                && ( INT ( DimTask[EndDate] ) <> INT ( DimTask[BaselineEndDate] )
                    || INT ( DimTask[StartDate] ) <> INT ( DimTask[BaselineStartDate] )
                    || COALESCE ( DimTask[Effort], 0 ) <> COALESCE ( DimTask[BaselineEffort], 0 ) ) ) )
RETURN IF ( _m > 0, {v} )"""
_add("Task Finish Shift", D, TASK_MOVED.format(v="""AVERAGEX ( FILTER ( DimTask, NOT ISBLANK ( DimTask[BaselineEndDate] ) ),
    INT ( DimTask[EndDate] ) - INT ( DimTask[BaselineEndDate] ) )"""), SIGNED,
     "Task finish minus its (current) baseline finish, calendar days; blank for tasks that did not move.")
_add("Task Start Shift", D, TASK_MOVED.format(v="""AVERAGEX ( FILTER ( DimTask, NOT ISBLANK ( DimTask[BaselineStartDate] ) ),
    INT ( DimTask[StartDate] ) - INT ( DimTask[BaselineStartDate] ) )"""), SIGNED)
_add("Task Hours Change", D, TASK_MOVED.format(v="SUM ( DimTask[Effort] ) - SUM ( DimTask[BaselineEffort] )"), SIGNED)
_add("Task Baseline Finish", DTM, TASK_MOVED.format(v="MAX ( DimTask[BaselineEndDate] )"), "dd mmm yyyy")
_add("Task Finish", DTM, TASK_MOVED.format(v="MAX ( DimTask[EndDate] )"), "dd mmm yyyy")
_add("Task Slip Colour", T, f"""
VAR _d = [{bm("Task Finish Shift")}]
RETURN IF ( ISBLANK ( _d ), BLANK (), IF ( _d > 10, "{RED}", IF ( _d > 0, "{AMBER}", "{TEAL}" ) ) )""",
     folder=FOLDER + "\\Colours")

# ---------------------------------------------------------------- narrative
_add("Comparing With", T, f"""
VAR _d = {PICK}
RETURN IF ( {SEL}, "the baselines in force on " & FORMAT ( _d, "dd mmm yyyy" ), "each project's current baseline" )""")
WORST = f"""
VAR _w =
    TOPN ( 1, FILTER ( ADDCOLUMNS ( {PROJECTS}, "@s", [{bm("Finish Slip (days)")}] ), [@s] > 0 ), [@s], DESC, DimProject[Id], ASC )
VAR _wn = CALCULATE ( SELECTEDVALUE ( DimProject[Name] ), TREATAS ( SELECTCOLUMNS ( _w, "@id", DimProject[Id] ), DimProject[Id] ) )
VAR _ws = MAXX ( _w, [@s] )"""
_add("Headline", T, f"""
VAR _n = [{bm("Projects")}]
VAR _b = [{bm("Baselined Projects")}]
VAR _late = [{bm("Late Projects")}]
VAR _cv = [{bm("Cost Variance %")}]
VAR _hv = [{bm("Hours Variance %")}]
{WORST}
RETURN
    IF ( _b = 0,
        "None of the " & FORMAT ( _n, "0" ) & " projects in view has " & IF ( {SEL}, "a baseline on that date", "a baseline" )
            & ", so nothing can be compared yet. Save a baseline when a project passes its approval gate.",
        "Against " & [{bm("Comparing With")}] & ", " & FORMAT ( _late, "0" ) & " of " & FORMAT ( _b, "0" )
            & " baselined projects " & IF ( _late = 1, "finishes", "finish" ) & " later"
            & IF ( _late > 0, " (worst: " & _wn & ", +" & FORMAT ( _ws, "0" ) & " days)", "" )
            & ". "
            & IF ( ISBLANK ( _cv ), "No baseline in view holds a cost", "Cost " & FORMAT ( _cv, "+0%;-0%;0%" ) & " against baseline" )
            & IF ( ISBLANK ( _hv ), ". ", ", hours " & FORMAT ( _hv, "+0%;-0%;0%" ) & ". " )
            & IF ( _b < _n,
                FORMAT ( _n - _b, "0" ) & IF ( {SEL}, " project(s) had no baseline yet on that date.",
                    " project(s) have no baseline and cannot be tracked." ), "" ) )""",
     desc="One-sentence answer: how far the plans moved from the baseline, and the worst case.")

_add("Insight Coverage", T, f"""
VAR _n = [{bm("Projects")}]
VAR _b = [{bm("Baselined Projects")}]
RETURN
    IF ( _n = 0, "No projects in view.",
        IF ( _b = _n, "Coverage — every project in view has a baseline, so every deviation below is measured.",
            IF ( {SEL}, "Coverage — on " & FORMAT ( {PICK}, "dd mmm yyyy" ) & " only " & FORMAT ( _b, "0" ) & " of "
                & FORMAT ( _n, "0" ) & " projects in view had a baseline; the others drop out. Clear the slicer to use every current baseline.",
            "Coverage — only " & FORMAT ( _b, "0" ) & " of " & FORMAT ( _n, "0" ) & " projects (" & FORMAT ( DIVIDE ( _b, _n ), "0%" )
                & ") have a baseline. The other " & FORMAT ( _n - _b, "0" )
                & " can drift unseen: ask their managers to save a baseline at the next gate." ) ) )""")
_add("Insight Schedule", T, f"""
VAR _b = [{bm("Baselined Projects")}]
VAR _late = [{bm("Late Projects")}]
VAR _ss = [{bm("Start Shift (days)")}]
VAR _dd = AVERAGEX ( FILTER ( {PROJECTS}, [{bm("Finish Slip (days)")}] > 0 ), [{bm("Duration Change (wd)")}] )
{WORST}
RETURN
    IF ( _b = 0, "Schedule — nothing to compare yet.",
        IF ( _late = 0, "Schedule — no baselined project finishes later than planned. Hold the dates.",
            "Schedule — " & FORMAT ( _late, "0" ) & " of " & FORMAT ( _b, "0" ) & IF ( _late = 1, " finishes", " finish" ) & " late; " & _wn & " slipped most (+"
                & FORMAT ( _ws, "0" ) & " days). "
                & IF ( ABS ( _ss ) < 1, "Starts held, so the delay comes from longer execution ("
                    & FORMAT ( _dd, "+0;-0" ) & " working days per late project) — look at progress, not at late starts.",
                    "Starts moved " & FORMAT ( _ss, "+0;-0" ) & " days on average — check what held up the kick-off." ) ) )""")
_add("Insight Cost", T, f"""
VAR _b = [{bm("Baselined Projects")}]
VAR _cb = [{bm("Baseline Cost")}]
VAR _cv = [{bm("Cost Variance")}]
VAR _cp = [{bm("Cost Variance %")}]
VAR _nocost = COUNTROWS ( FILTER ( {PROJECTS}, NOT ISBLANK ( [{bm("Baseline Finish")}] ) && NOT ( [{bm("Baseline Cost (project)")}] > 0 ) ) ) + 0
RETURN
    IF ( _b = 0, "Cost — nothing to compare yet.",
        IF ( ISBLANK ( _cb ), "Cost — none of the baselines holds a cost, so cost drift is invisible. Assign rates before the next baseline.",
            "Cost — plan " & {money(f'[{bm("Plan Cost vs Baseline")}]')} & " against a baseline of " & {money("_cb")}
                & " (" & FORMAT ( _cp, "+0.0%;-0.0%;0.0%" ) & ")"
                & IF ( _cp > 0.05, ": above the 5% tolerance, explain it before the next board.", IF ( _cv > 0, ": inside tolerance.", ": on or under budget." ) )
                & IF ( _nocost > 0, " " & FORMAT ( _nocost, "0" ) & " baselined project(s) hold no cost in the baseline.", "" ) ) )""")
_add("Insight Effort", T, f"""
VAR _hb = [{bm("Baseline Hours")}]
VAR _hp = [{bm("Hours Variance %")}]
VAR _fb = [{bm("Baseline FTE")}]
VAR _fp = [{bm("Plan FTE")}]
VAR _fv = [{bm("FTE Variance %")}]
RETURN
    IF ( ISBLANK ( _hb ), "Hours & FTE — no baseline in view holds hours.",
        "Hours & FTE — hours " & FORMAT ( _hp, "+0%;-0%;0%" ) & "; "
            & IF ( ISBLANK ( _fb ) || ISBLANK ( _fp ), "FTE cannot be compared (a duration is missing). ",
                "people needed at once (sum of project averages) " & FORMAT ( _fb, "0.0" ) & " → " & FORMAT ( _fp, "0.0" )
                    & " FTE (" & FORMAT ( _fv, "+0%;-0%;0%" ) & "). " )
            & SWITCH ( TRUE (),
                _hp > 0.05 && _fv > 0.1, "More work in the same window: the team must grow or dates will move.",
                _hp > 0.05, "More work, spread over a longer window: scope grew — is there a change request?",
                _fv < -0.1, "The same work is spread thinner: people are released, or the plan is waiting on them.",
                _fv > 0.1, "The same work is squeezed into less time: check the people can absorb it.",
                "Effort and intensity are in line with the baseline." ) )""")
_add("Insight Rebaseline", T, f"""
VAR _r = [{bm("Rebaselined Projects")}]
VAR _t =
    TOPN ( 1, FILTER ( ADDCOLUMNS ( {PROJECTS}, "@v", [{bm("Versions")}] ), [@v] > 1 ), [@v], DESC, DimProject[Id], ASC )
VAR _tn = CALCULATE ( SELECTEDVALUE ( DimProject[Name] ), TREATAS ( SELECTCOLUMNS ( _t, "@id", DimProject[Id] ), DimProject[Id] ) )
VAR _tv = MAXX ( _t, [@v] )
RETURN
    IF ( _r = 0, "Re-baselining — no project in view has re-baselined: every deviation is measured against the original plan.",
        "Re-baselining — " & FORMAT ( _r, "0" ) & " project(s) saved more than one baseline (" & _tn & ": " & FORMAT ( _tv, "0" )
            & "). A new baseline resets the variance to zero — pick an earlier date in the Baseline slicer to see the drift since then." )""")

# ====================================================================== page
def baseline_slicer():
    v = slicer(C("FactStatusReport", "Summary_LastBaselineDate"), "Baselines in force on", sync=False)
    # Not strict single select: strict always forces a pick, and an empty slicer must mean "current baseline".
    # singleSelect = "multi-select only with Ctrl"; a Ctrl multi-pick is harmless (the latest picked date wins).
    v["objects"]["selection"] = [{"properties": {"singleSelect": b(True), "strictSingleSelect": b(False),
                                                 "selectAllCheckboxEnabled": b(False)}}]
    return v


NO_TOTALS = {"total": [{"properties": {"totals": b(False)}}]}


def insight_card(measure):
    return headline(measure, bg="#FFFFFF", border=BORDER, size=11, colour=INK)


def build():
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"), (DP("Name"), "Project")]
    pg = analytic_page(KEY, "BASELINE", "IS THE PLAN STILL THE PLAN WE APPROVED?",
                       "Current plan against a baseline: cost, days, hours, FTE. Pick a date: each project's baseline then; "
                       "empty = current baselines.",
                       slicers, bm("Headline"))
    # the baseline picker sits left of the three project slicers placed by pages.header
    x = pages.W - 16 - len(slicers) * 188 + 8 - 10 - 180
    pg.add(x, 10, 180, 62, baseline_slicer(), key="slicer_baseline",
           filters=[f_not_blank("FactStatusReport", "Summary_LastBaselineDate")])

    # ① pulse
    section(pg, Y1, 1, "How far did the plans move?",
            "Days are calendar days (duration: working days). Cost, hours and FTE compare only projects whose baseline holds them.")
    kpi_row(pg, Y1K, [
        (bm("Coverage"), "Projects with a baseline", {"colour_measure": bm("Coverage Colour")}),
        (bm("Late Projects"), "Finish later than baseline", {"colour_measure": bm("Late Colour")}),
        (bm("Finish Slip (days) · Card"), "Avg finish shift (d)", {"colour_measure": bm("Slip Colour")}),
        (bm("Start Shift (days) · Card"), "Avg start shift (d)", {"value_colour": NAVY}),
        (bm("Duration Change (wd) · Card"), "Avg duration Δ (work d)", {"value_colour": NAVY}),
        (bm("Cost Variance % · Card"), "Cost vs baseline", {"colour_measure": bm("Cost Colour")}),
        (bm("Hours Variance % · Card"), "Hours vs baseline", {"colour_measure": bm("Hours Colour")}),
        (bm("FTE Variance % · Card"), "Avg FTE vs baseline", {"colour_measure": bm("FTE Colour")}),
    ])

    # ② per-project comparison
    section(pg, 290, 2, "Where did it move: dates, money, hours, people?",
            "Money, hours and FTE: baseline grey, plan in colour. Projects without the compared baseline are left out.")
    cw = (1768 - 3 * 10) / 4
    name = P(DP("Name"), "Project")
    ss, fs, dc = M(bm("Start Shift (days)")), M(bm("Finish Slip (days)")), M(bm("Duration Change (wd)"))
    pg.add(16, 328, round(cw, 2), 300, chart("clusteredBarChart",
        {"Category": [name], "Y": [P(ss, "Start shift (d)"), P(fs, "Finish shift (d)"), P(dc, "Duration change (wd)")]},
        "Schedule deviation (days)",
        {"dataPoint": [measure_fill(ss, GREY), measure_fill(fs, ORANGE), measure_fill(dc, NAVY)],
         "legend": legend("Top"), "labels": labels_on(True)}, sort=[(fs, "Descending")]), key="v_sched")
    pairs = [("Cost", "Baseline Cost", "Plan Cost vs Baseline", "Cost: baseline vs plan (€)"),
             ("Hours", "Baseline Hours", "Plan Hours vs Baseline", "Hours: baseline vs plan"),
             ("FTE", "Baseline FTE", "Plan FTE", "Average FTE: baseline vs plan")]
    for k, (lbl, bmeas, pmeas, ttl) in enumerate(pairs, start=1):
        bf, pf = M(bm(bmeas)), M(bm(pmeas))
        pg.add(round(16 + k * (cw + 10), 2), 328, round(cw, 2), 300, chart("clusteredBarChart",
            {"Category": [name], "Y": [P(bf, f"Baseline {lbl.lower() if lbl != 'FTE' else 'FTE'}"),
                                        P(pf, f"Plan {lbl.lower() if lbl != 'FTE' else 'FTE'}")]},
            ttl, {"dataPoint": [measure_fill(bf, "#C3C9D2"), measure_fill(pf, NAVY if lbl != "FTE" else TEAL)],
                  "legend": legend("Top"), "labels": labels_on(True)}, sort=[(pf, "Descending")]), key=f"v_{lbl.lower()}")

    # ③ smart insights: one full-width line each, so the sentence fits
    section(pg, 640, 3, "What does it mean?", "Five readings of the numbers above, each ending in what to do.")
    ins = ["Insight Coverage", "Insight Schedule", "Insight Cost", "Insight Effort", "Insight Rebaseline"]
    for k, m in enumerate(ins):
        y = 678 + k * 66
        pg.add(16, y, 6, 60, pbir.shape(NAVY if k == 0 else ORANGE), key=f"ins_bar{k}")
        pg.add(22, y, 1762, 60, insight_card(bm(m)), key=f"ins{k}")

    # ④ register
    section(pg, 1010, 4, "Plan-versus-baseline register",
            "Biggest finish shift first; baseline-vs-plan amounts are in the charts above. The signal names the pattern, the last column what to do.")
    obj = table_style(9)
    obj["values"] += [cf_font(M(bm("Signal")), bm("Signal Colour")), cf_font(fs, bm("Slip Colour")),
                      cf_font(M(bm("Cost Variance %")), bm("Cost Colour")),
                      cf_font(M(bm("Hours Variance %")), bm("Hours Colour")),
                      cf_font(M(bm("FTE Variance %")), bm("FTE Colour"))]
    cols = [(DP("Name"), "Project"), (M(bm("Signal")), "Signal"), (M(bm("Baseline Saved On")), "Baseline saved"),
            (M(bm("Versions")), "Baselines"),
            (M(bm("Baseline Finish")), "Finish (baseline)"), (M(bm("Plan Finish")), "Finish (plan)"),
            (fs, "Finish Δ d"), (ss, "Start Δ d"), (dc, "Duration Δ wd"),
            (M(bm("Plan Cost (project)")), "Cost (plan)"), (M(bm("Cost Variance %")), "Cost Δ %"),
            (M(bm("Plan Hours (project)")), "Hours (plan)"), (M(bm("Hours Variance %")), "Hours Δ %"),
            (M(bm("Plan FTE")), "FTE (plan)"),
            (M(bm("FTE Variance %")), "FTE Δ %"), (M(bm("Next Step")), "Next step")]
    # fixed widths for the wide text columns, so the numbers and Next step fit without a horizontal scrollbar
    widths = {"Project": 170, "Signal": 280, "Next step": 240}
    obj["columnWidth"] = [{"properties": {"value": n(widths[lbl])}, "selector": {"metadata": qref(f)}}
                          for f, lbl in cols if lbl in widths]
    pg.add(16, 1048, 1768, 300, chart("tableEx", {"Values": [P(f, lbl) for f, lbl in cols]},
                                    "Plan-versus-baseline register", {**obj, **NO_TOTALS}, sort=[(fs, "Descending")]), key="v_register")
    # ⑤ task drill (current baseline only)
    section(pg, 1360, 5, "Which tasks moved?",
            "Tasks compare with the current baseline only: OnePlan keeps task baselines for the latest baseline.")
    tf = M(bm("Task Finish Shift"))
    obj = table_style(9)
    obj["values"] += [cf_font(tf, bm("Task Slip Colour"))]
    pg.add(16, 1398, 1768, 196, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DT("Name"), "Task"), P(M(bm("Task Baseline Finish")), "Baseline finish"),
                    P(M(bm("Task Finish")), "Finish"), P(tf, "Finish shift (d)"), P(M(bm("Task Start Shift")), "Start shift (d)"),
                    P(M(bm("Task Hours Change")), "Hours change")]},
        "Tasks that moved against the current baseline — biggest finish shift first", {**obj, **NO_TOTALS},
        sort=[(tf, "Descending")]),
        key="v_tasks", filters=[f_in("DimTask", "WorkType", ["Tasks"]), f_in("DimTask", "Leaf", [True]),
                                f_not_blank("DimTask", "BaselineEndDate"), PROJECT_TASKS])
    next_chapter(pg, KEY, YNEXT)
    return [pg]
