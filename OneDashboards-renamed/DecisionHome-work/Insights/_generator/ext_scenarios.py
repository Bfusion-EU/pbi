"""2c · Scenario Comparison — OnePlan Portfolio Modeler, scenario A versus scenario B.

Answers: "If we fund scenario A instead of B, what do we gain, and what don't we fund?"

Data:
  * DimScenario            — one row per Modeler scenario: totals, targets and commit details.
  * FactModelerScenarioPlan — one row per plan per scenario (Checked = funded in that scenario);
                              ScenarioKey -> DimScenario, ProjectKey -> DimProject.
  * ModelerScenario_A / _B  — disconnected copies of the scenario names, used as the two pickers.

All plan-level measures here are keyed on the ProjectKey relationship (TREATAS over
DimProject[ProjectKey]) instead of the model's ScenarioCompare | … measures, which match
plans by name. The scenario is resolved once in "Key A" / "Key B"; when nobody picked one,
A falls back to the most recently committed scenario and B to the first other scenario.

Scenario names repeat across Modeler models (the pickers are DISTINCT names). DimScenario carries
ParentModelId / ModelName_Star, so a Model slicer (DimScenario[ModelName_Star]) scopes the
resolution: a picked name is looked up inside the selected model(s) only, and the "latest committed"
default is the latest committed scenario of the selected model(s). The slicer filters DimScenario
directly; no DimProject slicer reaches DimScenario (single-direction relationships via
FactModelerScenarioPlan). The A/B pickers themselves still list every name (ModelerScenario_A/_B are
model calculated tables); restricting their lists needs a model change.

Scenario totals (Modeler) and plan sums (DimProject[Budget] / [Benefits]) are different
numbers: Modeler totals are scenario-wide and are not cut by the Portfolio / Program slicers,
the plan sums are. The page labels them separately.
"""
import pages
import pbir
from pbir import (AMBER, GREY, NAVY, ORANGE, PEACH, RED, SLATE, TEAL, C, M, P, b, chart, col_solid,
                  labels_on, legend, measure_fill, n, s, slicer, table_style)
from pages import H2, H3, H4, Y1, Y1K, Y2, Y2V, Y3, Y3V, Y4, Y4V, YNEXT
from story_measures import D, I, T, add, cnt, money

PFX = "Story | Scenario · "
FOLDER = "Story\\Scenario"


def mn(name):
    return PFX + name


def _add(name, dtype, expr, fmt=None, desc=None):
    add(mn(name), dtype, expr, fmt, FOLDER, desc)


def smoney(v):
    """Signed compact euro amount: +€1.2M / −€300K."""
    return f'IF ( ISBLANK ( {v} ), "–", IF ( {v} >= 0, "+", "−" ) & {money(f"ABS ( {v} )")} )'


# ------------------------------------------------------------------ scenario resolution
# Scenarios in the selected Modeler model(s): the Model slicer filters DimScenario[ModelName_Star]; nothing else on
# the page filters DimScenario. No model picked = every model (names may then be ambiguous; the headline says so).
_add("Key A", I, f"""
VAR _s = SELECTEDVALUE ( ModelerScenario_A[Name] )
VAR _models = VALUES ( DimScenario[ParentModelId] )
VAR _picked =
    IF ( NOT ISBLANK ( _s ),
        CALCULATE ( MAX ( DimScenario[ScenarioKey] ), ALL ( DimScenario ), TREATAS ( {{ _s }}, DimScenario[Name] ),
            TREATAS ( _models, DimScenario[ParentModelId] ) ) )
VAR _committed =
    MAXX (
        TOPN ( 1,
            FILTER ( ALL ( DimScenario ),
                DimScenario[CommitDetails_Committed] = TRUE () && DimScenario[ParentModelId] IN _models ),
            DimScenario[CommitDetails_CommittedOn], DESC, DimScenario[ScenarioKey], DESC ),
        DimScenario[ScenarioKey] )
VAR _first =
    CALCULATE ( MIN ( DimScenario[ScenarioKey] ), ALL ( DimScenario ), TREATAS ( _models, DimScenario[ParentModelId] ) )
RETURN COALESCE ( _picked, _committed, _first )""", "0",
     "ScenarioKey of scenario A inside the selected Modeler model(s): the ModelerScenario_A pick, else the latest "
     "committed scenario of that model, else its first scenario.")

_add("Key B", I, f"""
VAR _s = SELECTEDVALUE ( ModelerScenario_B[Name] )
VAR _a = [{mn("Key A")}]
VAR _models = VALUES ( DimScenario[ParentModelId] )
VAR _picked =
    IF ( NOT ISBLANK ( _s ),
        CALCULATE ( MAX ( DimScenario[ScenarioKey] ), ALL ( DimScenario ), TREATAS ( {{ _s }}, DimScenario[Name] ),
            TREATAS ( _models, DimScenario[ParentModelId] ) ) )
VAR _other =
    CALCULATE ( MIN ( DimScenario[ScenarioKey] ), ALL ( DimScenario ), DimScenario[ScenarioKey] <> _a,
        TREATAS ( _models, DimScenario[ParentModelId] ) )
RETURN COALESCE ( _picked, _other )""", "0",
     "ScenarioKey of scenario B inside the selected Modeler model(s): the ModelerScenario_B pick, else the first "
     "other scenario of that model.")


def _scen_col(col, side, agg="SUM"):
    return f"""
VAR _k = [{mn("Key " + side)}]
RETURN IF ( NOT ISBLANK ( _k ),
    CALCULATE ( {agg} ( DimScenario[{col}] ), ALL ( DimScenario ), DimScenario[ScenarioKey] = _k ) )"""


SCEN_COLS = [  # (measure stem, DimScenario column, type, format)
    ("Budget", "TotalBudget", D, "#,##0"),
    ("Target Budget", "TargetBudget", D, "#,##0"),
    ("Benefits", "TotalBenefits", D, "#,##0"),
    ("Target Benefits", "TargetBenefits", D, "#,##0"),
    ("Effort", "TotalCommittedEffort", D, "#,##0"),
    ("Target Effort", "TargetCommittedEffort", D, "#,##0"),
    ("Plans", "TotalPlans", I, "#,##0"),
    ("Checked Plans", "TotalCheckedPlans", I, "#,##0"),
]

for side in "AB":
    _add(f"Name {side}", T, _scen_col("Name", side, "MAX"), desc=f"Name of scenario {side}.")
    for stem, col, dt, fmt in SCEN_COLS:
        _add(f"{stem} {side}", dt, _scen_col(col, side), fmt,
             f"DimScenario[{col}] of scenario {side} (Modeler, scenario-wide; not cut by Portfolio/Program).")
    _add(f"Budget Gap {side}", D, f"""
VAR _t = [{mn("Target Budget " + side)}]
RETURN IF ( NOT ISBLANK ( _t ) && _t <> 0, [{mn("Budget " + side)}] - _t )""", "+#,##0;-#,##0;0",
         f"Scenario {side} total budget minus its target budget. Positive = over target.")
    _add(f"Budget Gap % {side}", D, f"""
DIVIDE ( [{mn("Budget Gap " + side)}], [{mn("Target Budget " + side)}] )""", "+0.0%;-0.0%;0.0%")
    _add(f"Benefits per € {side}", D, f"""
DIVIDE ( [{mn("Benefits " + side)}], [{mn("Budget " + side)}] )""", "0.00",
         f"Scenario {side} total benefits per euro of total budget.")
    _add(f"Gap Colour {side}", T, f"""
VAR _p = [{mn("Budget Gap % " + side)}]
RETURN IF ( ISBLANK ( _p ), "#666666", IF ( _p > 0.05, "{RED}", IF ( _p > 0, "{AMBER}", "{TEAL}" ) ) )""")
    _add(f"Plans Text {side}", T, f"""
VAR _k = [{mn("Key " + side)}]
RETURN IF ( ISBLANK ( _k ), "–",
    {cnt(f'[{mn("Checked Plans " + side)}]')} & " of " & {cnt(f'[{mn("Plans " + side)}]')} )""",
         desc=f"Funded (checked) plans of all plans in scenario {side}.")
    _add(f"Commit Text {side}", T, f"""
VAR _k = [{mn("Key " + side)}]
VAR _c =
    CALCULATE ( COUNTROWS ( DimScenario ), ALL ( DimScenario ), DimScenario[ScenarioKey] = _k,
        DimScenario[CommitDetails_Committed] = TRUE () ) > 0
VAR _on = CALCULATE ( MAX ( DimScenario[CommitDetails_CommittedOn] ), ALL ( DimScenario ), DimScenario[ScenarioKey] = _k )
RETURN IF ( ISBLANK ( _k ), BLANK (),
    IF ( _c,
        "committed" & IF ( ISBLANK ( _on ), "", " on " & FORMAT ( _on, "dd mmm yyyy" ) ),
        "not committed" ) )""")

_add("Benefits A − B", D, f"[{mn('Benefits A')}] - [{mn('Benefits B')}]", "+#,##0;-#,##0;0",
     "Scenario totals: benefits of A minus benefits of B.")
_add("Budget A − B", D, f"[{mn('Budget A')}] - [{mn('Budget B')}]", "+#,##0;-#,##0;0",
     "Scenario totals: budget of A minus budget of B.")
_add("Delta Colour", T, f"""
VAR _d = [{mn("Benefits A − B")}]
RETURN IF ( ISBLANK ( _d ), "#666666", IF ( _d >= 0, "{TEAL}", "{RED}" ) )""")

# ------------------------------------------------------------------ plan sets (ProjectKey)
# Funded plans of a scenario = checked FactModelerScenarioPlan rows, as DimProject keys.
# They respect DimProject filters (Portfolio / Program slicers, table rows).
SETS = f"""
VAR _ka = [{mn("Key A")}]
VAR _kb = [{mn("Key B")}]
VAR _a =
    CALCULATETABLE (
        FILTER ( VALUES ( FactModelerScenarioPlan[ProjectKey] ), NOT ISBLANK ( FactModelerScenarioPlan[ProjectKey] ) ),
        ALL ( DimScenario ), DimScenario[ScenarioKey] = _ka, FactModelerScenarioPlan[Checked] = TRUE () )
VAR _b =
    CALCULATETABLE (
        FILTER ( VALUES ( FactModelerScenarioPlan[ProjectKey] ), NOT ISBLANK ( FactModelerScenarioPlan[ProjectKey] ) ),
        ALL ( DimScenario ), DimScenario[ScenarioKey] = _kb, FactModelerScenarioPlan[Checked] = TRUE () )
VAR _onlyA = EXCEPT ( _a, _b )
VAR _onlyB = EXCEPT ( _b, _a )
VAR _both = INTERSECT ( _a, _b )"""

PLAN_SETS = {  # set stem -> (DAX var, description)
    "In A": ("_a", "funded in scenario A"),
    "In B": ("_b", "funded in scenario B"),
    "Only A": ("_onlyA", "funded in A but not in B (what B does not fund)"),
    "Only B": ("_onlyB", "funded in B but not in A (what A does not fund)"),
    "Both": ("_both", "funded in both scenarios"),
}

for stem, (var, desc) in PLAN_SETS.items():
    _add(f"Plans {stem}", I, f"{SETS}\nRETURN COUNTROWS ( {var} ) + 0", "#,##0", f"Plans {desc}.")
    for what, col in (("Budget", "Budget"), ("Benefits", "Benefits")):
        _add(f"{what} {stem}", D, f"""{SETS}
RETURN IF ( COUNTROWS ( {var} ) > 0,
    COALESCE ( CALCULATE ( SUM ( DimProject[{col}] ), TREATAS ( {var}, DimProject[ProjectKey] ) ), 0 ) )""",
             "#,##0", f"Plan {what.lower()} (DimProject[{col}]) of plans {desc}; blank when there are none.")
    _add(f"Benefits per € {stem}", D, f"""
DIVIDE ( [{mn("Benefits " + stem)}], [{mn("Budget " + stem)}] )""", "0.00")

_add("Plan Benefits A − B", D, f"""
COALESCE ( [{mn("Benefits In A")}], 0 ) - COALESCE ( [{mn("Benefits In B")}], 0 )""", "+#,##0;-#,##0;0",
     "Plan benefits gained by funding A's plans instead of B's (within the Portfolio/Program selection).")

_add("Swap Text", T, f"""
VAR _k = [{mn("Key A")}]
RETURN IF ( ISBLANK ( _k ), "–",
    {cnt(f'[{mn("Plans Only A")}]')} & " in · " & {cnt(f'[{mn("Plans Only B")}]')} & " out" )""",
     desc="Plans A adds that B lacks (in) and plans B funds that A drops (out).")

# ------------------------------------------------------------------ headline
_add("Headline", T, f"""
VAR _n = COUNTROWS ( ALL ( DimScenario ) )
VAR _nm = COUNTROWS ( VALUES ( DimScenario[ParentModelId] ) )
VAR _sa = SELECTEDVALUE ( ModelerScenario_A[Name] )
VAR _sb = SELECTEDVALUE ( ModelerScenario_B[Name] )
VAR _lost =
    ( NOT ISBLANK ( _sa ) && _sa <> [{mn("Name A")}] ) || ( NOT ISBLANK ( _sb ) && _sb <> [{mn("Name B")}] )
VAR _ka = [{mn("Key A")}]
VAR _kb = [{mn("Key B")}]
VAR _na = [{mn("Name A")}]
VAR _nb = [{mn("Name B")}]
VAR _picked = NOT ISBLANK ( SELECTEDVALUE ( ModelerScenario_A[Name] ) ) && NOT ISBLANK ( SELECTEDVALUE ( ModelerScenario_B[Name] ) )
VAR _ba = [{mn("Budget A")}]
VAR _bb = [{mn("Budget B")}]
VAR _ea = [{mn("Benefits A")}]
VAR _eb = [{mn("Benefits B")}]
VAR _db = _ba - _bb
VAR _de = _ea - _eb
VAR _ga = [{mn("Budget Gap A")}]
VAR _oa = [{mn("Plans Only A")}]
VAR _ob = [{mn("Plans Only B")}]
VAR _obb = [{mn("Budget Only B")}]
VAR _obe = [{mn("Benefits Only B")}]
VAR _rA = [{mn("Benefits per € A")}]
VAR _rB = [{mn("Benefits per € B")}]
RETURN
    IF ( COALESCE ( _n, 0 ) = 0,
        "No Portfolio Modeler scenarios found — create and commit scenarios in OnePlan Modeler to compare.",
    IF ( _n = 1 || _ka = _kb,
        "Pick two different scenarios in the Scenario A and Scenario B slicers to compare them.",
        "Funding A “" & _na & "” (" & [{mn("Commit Text A")}] & ") instead of B “" & _nb & "” ("
            & [{mn("Commit Text B")}] & "): budget " & {money("_ba")} & " vs " & {money("_bb")}
            & " (" & {smoney("_db")} & "), benefits " & {money("_ea")} & " vs " & {money("_eb")}
            & " (" & {smoney("_de")} & "); benefits per € " & FORMAT ( _rA, "0.00" ) & " vs " & FORMAT ( _rB, "0.00" ) & ". "
            & IF ( _ob > 0,
                "A does not fund " & FORMAT ( _ob, "0" ) & " plan" & IF ( _ob = 1, "", "s" ) & " that B funds ("
                    & {money("_obb")} & " budget, " & {money("_obe")} & " benefits)",
                "A funds every plan B funds" )
            & IF ( _oa > 0, " and adds " & FORMAT ( _oa, "0" ) & " of its own", "" ) & ". "
            & IF ( ISBLANK ( _ga ), "A has no target budget.",
                "A is " & {money("ABS ( _ga )")} & IF ( _ga > 0, " over", " under" ) & " its target budget." )
            & IF ( _picked, "", "  (Defaulted — pick scenarios in the A and B slicers.)" )
            & IF ( _lost, "  A picked name is not in the selected model, so that side fell back to the default.", "" )
            & IF ( _nm > 1, "  Scenario names can repeat across " & FORMAT ( _nm, "0" )
                & " Modeler models — pick one model to compare within it.", "" )
    ) )""", desc="One-sentence answer: what A gains over B and what it does not fund.")


# ------------------------------------------------------------------ visuals
def _scenario_slicer(field, label, group):
    """Single-select dropdown slicer with its own sync group (both pickers share the column name 'Name')."""
    v = slicer(field, label, sync=False)
    v["objects"]["selection"] = [{"properties": {"strictSingleSelect": b(True), "selectAllCheckboxEnabled": b(False)}}]
    v["syncGroup"] = {"groupName": group, "fieldChanges": True, "filterChanges": True}
    return v


def _vs_target(stem, ttl):
    a, ta, bb, tb = (M(mn(f"{stem} A")), M(mn(f"Target {stem} A")), M(mn(f"{stem} B")), M(mn(f"Target {stem} B")))
    return chart("clusteredColumnChart",
                 {"Y": [P(a, "A"), P(ta, "A target"), P(bb, "B"), P(tb, "B target")]}, ttl,
                 {"dataPoint": [measure_fill(a, ORANGE), measure_fill(ta, PEACH), measure_fill(bb, NAVY),
                                measure_fill(tb, SLATE)],
                  "legend": legend("Top"), "labels": labels_on(True, 0)})


def _set_table(stem, ttl, colour):
    bud, ben, ratio = M(mn(f"Budget {stem}")), M(mn(f"Benefits {stem}")), M(mn(f"Benefits per € {stem}"))
    obj = table_style()
    obj["columnHeaders"][0]["properties"]["backColor"] = col_solid(colour)
    return chart("tableEx",
                 {"Values": [P(pages.DP("Name"), "Project"), P(pages.DP("Program Name"), "Program"),
                             P(bud, "Plan budget"), P(ben, "Plan benefits"), P(ratio, "Benefit ÷ €")]},
                 ttl, obj, sort=[(ben, "Descending")])


def build():
    key = "scenarios"
    # The Model slicer takes the Program slot (four header slicers fit the title row); the plan sets still follow
    # the Portfolio slicer.
    slicers_ = [(C("DimScenario", "ModelName_Star"), "Modeler model"),
                (C("ModelerScenario_A", "Name"), "Scenario A"), (C("ModelerScenario_B", "Name"), "Scenario B"),
                (pages.DP("Portfolio Name"), "Portfolio")]
    pg = _page(key, slicers_)

    pages.section(pg, Y1, 1, "A versus B in one row",
                  "Scenario totals come from Modeler (selected model); the plan swap counts follow the Portfolio slicer.")
    pages.kpi_row(pg, Y1K, [
        (mn("Budget A"), "Budget — A", {"value_colour": ORANGE}),
        (mn("Budget B"), "Budget — B"),
        (mn("Benefits A"), "Benefits — A", {"value_colour": ORANGE}),
        (mn("Benefits B"), "Benefits — B"),
        (mn("Benefits A − B"), "Benefits gained (A − B)", {"colour_measure": mn("Delta Colour")}),
        (mn("Plans Text A"), "Plans funded — A", {"value_colour": ORANGE}),
        (mn("Plans Text B"), "Plans funded — B"),
        (mn("Swap Text"), "Plans swapped by A", {"value_colour": NAVY}),
    ])

    pages.section(pg, Y2, 2, "How does each scenario sit against its targets?",
                  "Orange = A, navy = B; the lighter bar next to each is the scenario's Modeler target.")
    cw = round((1344 - 2 * 12) / 3, 2)
    for k, (stem, ttl) in enumerate([("Budget", "Budget versus target"), ("Benefits", "Benefits versus target"),
                                     ("Effort", "Committed effort versus target")]):
        pg.add(round(16 + k * (cw + 12), 2), Y2V, cw, H2, _vs_target(stem, ttl), key=f"v_target_{stem.lower()}")
    fx, fw, fh = 1372, 412, (H2 - 10) / 2
    tw = (fw - 10) / 2
    fit = [(mn("Budget Gap A"), "Gap to target budget — A", {"colour_measure": mn("Gap Colour A")}),
           (mn("Budget Gap B"), "Gap to target budget — B", {"colour_measure": mn("Gap Colour B")}),
           (mn("Benefits per € A"), "Benefits per € — A", {"value_colour": ORANGE}),
           (mn("Benefits per € B"), "Benefits per € — B", {"value_colour": NAVY})]
    for k, (m, label, o) in enumerate(fit):
        col, row = k % 2, k // 2
        pg.add(round(fx + col * (tw + 10), 2), round(Y2V + row * (fh + 10), 2), round(tw, 2), round(fh, 2),
               pbir.card(m, label, size=22, **o), key=f"fit{k}")

    pages.section(pg, Y3, 3, "Where does the money move if we pick A?",
                  "Plan budget split by portfolio into only-A, both and only-B plans; right, the benefits A gains or loses.")
    oa, bo, ob = M(mn("Budget Only A")), M(mn("Budget Both")), M(mn("Budget Only B"))
    pg.add(16, Y3V, 878, H3, chart("barChart",
        {"Category": [P(pages.DP("Portfolio Name"), "Portfolio")],
         "Y": [P(oa, "Only in A"), P(bo, "In both"), P(ob, "Only in B")]},
        "Plan budget by portfolio — only in A, in both, only in B",
        {"dataPoint": [measure_fill(oa, ORANGE), measure_fill(bo, GREY), measure_fill(ob, NAVY)],
         "legend": legend("Top")}, sort=[(bo, "Descending")]), key="v_budget_split")
    d = M(mn("Plan Benefits A − B"))
    pg.add(906, Y3V, 878, H3, chart("waterfallChart",
        {"Category": [P(pages.DP("Portfolio Name"), "Portfolio")], "Y": [P(d, "Benefits A − B")]},
        "Plan benefits gained (+) or given up (−) by funding A instead of B, by portfolio",
        {"sentimentColors": [{"properties": {"increaseFill": col_solid(TEAL), "decreaseFill": col_solid(RED),
                                             "totalFill": col_solid(NAVY)}}],
         "labels": labels_on(True, 0)}, sort=[(d, "Descending")]), key="v_benefit_bridge")

    pages.section(pg, Y4, 4, "Which plans are in, and which are out?",
                  "Left: what A adds. Middle: funded either way. Right: what A does not fund — the conversation to have.")
    tw3 = round((1768 - 2 * 12) / 3, 2)
    for k, (stem, ttl, colour) in enumerate([
            ("Only A", "Only in A — B would not fund these", pbir.ORANGE_DK),
            ("Both", "In both — funded either way", NAVY),
            ("Only B", "Only in B — A would not fund these", RED)]):
        pg.add(round(16 + k * (tw3 + 12), 2), Y4V, tw3, H4, _set_table(stem, ttl, colour),
               key=f"v_set_{stem.replace(' ', '').lower()}")

    pages.next_chapter(pg, key, YNEXT)
    return [pg]


def _page(key, slicers_):
    """pages.analytic_page, then swap the two scenario slicers for single-select pickers."""
    pg = pages.analytic_page(key, "SCENARIOS", "IF WE FUND A INSTEAD OF B?",
                             "OnePlan Portfolio Modeler: two scenarios side by side against their targets — "
                             "what A gains, and which plans it does not fund.",
                             slicers_, mn("Headline"))
    for vc in pg.visuals:
        if vc["visual"].get("visualType") != "slicer":
            continue
        fld = vc["visual"]["query"]["queryState"]["Values"]["projections"][0]["field"]["Column"]
        ent = fld["Expression"]["SourceRef"]["Entity"]
        if ent in ("ModelerScenario_A", "ModelerScenario_B"):
            side = ent[-1]
            vc["visual"] = _scenario_slicer(C(ent, "Name"), f"Scenario {side}", f"Modeler Scenario {side}")
        elif ent == "DimScenario":
            vc["visual"] = _scenario_slicer(C(ent, "ModelName_Star"), "Modeler model", "Modeler Model")
    return pg
