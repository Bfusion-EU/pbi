"""Project One-Pager (drill-through) and the two report-page tooltips.

Pages (keys/ids registered in pages.HIDDEN_PAGES / pages.PID):
  project      — drill-through on DimProject[Name]: "Everything about this project before I decide."
  tip_project  — 320×240 report-page tooltip for a hovered project (DimProject[Name]).
  tip_resource — 320×240 report-page tooltip for a hovered resource (DimResource[Name]).

All report-level measures registered here are prefixed "Story | Project · ".
Lifetime money (Budget / Actual / EAC) ignores the date filters (REMOVEFILTERS DimDate)
because "at completion" must not change with a Year slicer. The drill-through binding does not accept the
source filter context (acceptsFilterContext "None"): only the drilled DimProject[Name] travels, so the
monthly charts show the whole plan. Money and overdue measures delegate to story_measures.py (one definition).
"""
import pbir
from pbir import (Page, card, headline, chart, textbox, st, table_style, cf_font, nav_button, title, panel,
                  P, M, C, s, b, n, i, uid, col_solid, legend, labels_on, measure_fill, f_in, f_cmp,
                  NAVY, ORANGE, ORANGE_SOFT, TEAL, AMBER, RED, GREY, MUTED, BORDER)
import pages
from pages import W, TALL, BG_TALL, PID, HIDDEN_PAGES, DP, DT, DR, MONTH, section
from story_measures import add, money, T, D, I

PX = "Story | Project · "
FOLDER = "Story\\Project"
NAMES = dict(HIDDEN_PAGES)


def pm(name):
    """Full name of one of this module's measures."""
    return PX + name


# ====================================================================== DAX helpers
def health_label(var):
    """'(2) At Risk' -> 'At Risk'; blank -> 'Not reported' (inline expression on a variable)."""
    return (f'IF ( ISBLANK ( {var} ) || {var} = "", "Not reported", '
            f'IF ( LEFT ( {var}, 1 ) = "(" && FIND ( ")", {var}, 1, 0 ) > 0, '
            f'TRIM ( MID ( {var}, FIND ( ")", {var}, 1, 0 ) + 1, 100 ) ), {var} ) )')


def health_colour(var):
    return (f'SWITCH ( LEFT ( {var}, 3 ), "(1)", "{TEAL}", "(2)", "{AMBER}", "(3)", "{RED}", "{GREY}" )')


# OnePlan rich-text fields arrive as HTML (<div>, <p>, <b>, <br>…). Strip every tag generically:
# turn < and > into PATH delimiters and keep the odd items (text between tags).
_ODD = ", ".join("{ %d }" % k for k in range(1, 400, 2))


def strip_html(src, out="_clean"):
    return ("VAR _h0 = SUBSTITUTE ( SUBSTITUTE ( COALESCE ( " + src + ', "" ), "|", "/" ), "<", "|" )\n'
            'VAR _h1 = SUBSTITUTE ( _h0, ">", "|" )\n'
            "VAR _hn = PATHLENGTH ( _h1 )\n"
            'VAR _h2 = CONCATENATEX ( FILTER ( DATATABLE ( "@i", INTEGER, { ' + _ODD + " } ), [@i] <= _hn ), "
            'PATHITEM ( _h1, [@i] ), " ", [@i], ASC )\n'
            "VAR " + out + ' = TRIM ( SUBSTITUTE ( SUBSTITUTE ( SUBSTITUTE ( SUBSTITUTE ( _h2, "&nbsp;", " " ), '
            '"&amp;", "&" ), "&lt;", "<" ), "&gt;", ">" ) )\n')


LAST_REPORT = "CALCULATE ( MAX ( FactStatusReport[Report_ReportEnd] ), REMOVEFILTERS ( DimDate ) )"


def latest_report_field(col):
    """Text of FactStatusReport[col] on the latest report (by ReportEnd); fall back to DimProject[col]."""
    return f"""
VAR _last = {LAST_REPORT}
VAR _raw =
    IF ( ISBLANK ( _last ),
        SELECTEDVALUE ( DimProject[{col}] ),
        CALCULATE (
            CONCATENATEX ( VALUES ( FactStatusReport[{col}] ), FactStatusReport[{col}], " " ),
            FactStatusReport[Report_ReportEnd] = _last,
            REMOVEFILTERS ( DimDate )
        )
    )
{strip_html("_raw")}RETURN
    IF ( ISBLANK ( SELECTEDVALUE ( DimProject[Name] ) ), "Drill through on one project.",
        IF ( LEN ( _clean ) = 0,
            IF ( ISBLANK ( _last ), "No status report yet, and the plan field is empty.", "Left empty in the latest status report." ),
            IF ( LEN ( _clean ) > 900, LEFT ( _clean, 900 ) & " …", _clean ) ) )"""


# ====================================================================== measures
# --- identity
add(pm("Name"), T, 'SELECTEDVALUE ( DimProject[Name], "Select one project" )', folder=FOLDER)
add(pm("Manager"), T, 'COALESCE ( SELECTEDVALUE ( DimProject[Manager_Value] ), "–" )', folder=FOLDER)
add(pm("Portfolio"), T, 'COALESCE ( SELECTEDVALUE ( DimProject[Portfolio Name] ), "–" )', folder=FOLDER)
add(pm("Programme"), T, 'COALESCE ( SELECTEDVALUE ( DimProject[Program Name] ), "–" )', folder=FOLDER)
add(pm("Lifecycle Step"), T, 'COALESCE ( SELECTEDVALUE ( DimProject[ProcessStep] ), "–" )', folder=FOLDER)
add(pm("% Complete"), D, "DIVIDE ( MAX ( DimProject[Summary_PercentDone] ), 100 )", "0%", FOLDER,
    "Work-plan summary % complete.")
add(pm("Finish"), T, """
VAR _f = MAX ( DimProject[Summary_EndDate] )
VAR _bl = MAX ( DimProject[Summary_BaselineEndDate] )
VAR _slip = IF ( NOT ISBLANK ( _f ) && NOT ISBLANK ( _bl ), INT ( _f ) - INT ( _bl ) )
RETURN
    IF ( ISBLANK ( _f ), "–",
        FORMAT ( _f, "dd mmm yyyy" ) & IF ( ISBLANK ( _slip ), "", IF ( _slip > 0, "  (+" & FORMAT ( _slip, "0" ) & "d)", "" ) ) )""",
    folder=FOLDER, desc="Work-plan finish date, with days of slip against the baseline finish.")
add(pm("OnePlan Url"), T, "SELECTEDVALUE ( DimProject[PMO Plan Url] )", folder=FOLDER,
    desc="Deep link to the plan in OnePlan (DimProject[PMO Plan Url]); drives the 'Open in OnePlan' button.")

HEALTH = [("Overall", "OverallHealth_Value"), ("Schedule", "ScheduleHealth_Value"), ("Financial", "FinancialHealth_Value"),
          ("Effort", "EffortHealth_Value"), ("Issue", "IssueHealth_Value"), ("Scope", "ScopeHealth_Value")]
for _lbl, _col in HEALTH:
    add(pm(f"{_lbl} Health"), T, f"VAR _h = SELECTEDVALUE ( DimProject[{_col}] )\nRETURN {health_label('_h')}",
        folder=FOLDER)
    add(pm(f"{_lbl} Health Colour"), T, f"VAR _h = SELECTEDVALUE ( DimProject[{_col}] )\nRETURN {health_colour('_h')}",
        folder=FOLDER + "\\Colours")

# --- money (lifetime: ignores date filters). ONE definition: these delegate to the story-page measures
# (story_measures.py), so the One-Pager, the tooltip and the story pages always show the same EAC variance.
add(pm("Budget"), D, "[Story | Budget At Completion]", "#,##0", FOLDER,
    "Lifetime budget from the financial plan (FactCost Budget), all dates — same as Story | Budget At Completion.")
add(pm("Actual"), D, "CALCULATE ( [Story | Actual Cost], REMOVEFILTERS ( DimDate ) )", "#,##0", FOLDER,
    "Lifetime actual cost (FactCost Actual Cost), all dates.")
add(pm("EAC"), D, "[Story | Finance EAC]", "#,##0", FOLDER,
    "Estimate at completion (FactCost EAC), all dates — same as Story | Finance EAC.")
add(pm("EAC Variance"), D, "[Story | EAC Variance]", "#,##0", FOLDER,
    "EAC minus budget at completion (Story | EAC Variance). Positive = expected overrun.")
add(pm("EAC Variance %"), D, "[Story | EAC Variance %]", "+0.0%;-0.0%;0.0%", FOLDER,
    "EAC variance as a share of budget at completion (Story | EAC Variance %).")
add(pm("EAC Colour"), T, f"""
VAR _p = [{pm("EAC Variance %")}]
RETURN IF ( ISBLANK ( _p ), "{MUTED}", IF ( _p > 0.05, "{RED}", IF ( _p > 0, "{AMBER}", "{TEAL}" ) ) )""",
    folder=FOLDER + "\\Colours")
add(pm("Burn %"), D, "[Story | Burn %]", "0%", FOLDER, "Lifetime actual cost as a share of budget at completion.")

# --- risk / schedule. These summarise the whole project: REMOVEFILTERS ( DimTask ) so a hovered or drilled
# task / risk row cannot shrink them to that one row.
add(pm("Active Risks"), I, "CALCULATE ( [Project | Active Risks], REMOVEFILTERS ( DimTask ), VALUES ( DimProject[Id] ) ) + 0", "#,##0", FOLDER)
add(pm("Active Issues"), I, "CALCULATE ( [Project | Active Issues], REMOVEFILTERS ( DimTask ), VALUES ( DimProject[Id] ) ) + 0", "#,##0", FOLDER)
add(pm("Risk Exposure"), D,
    'CALCULATE ( SUM ( DimTask[Exposure] ), REMOVEFILTERS ( DimTask ), VALUES ( DimProject[Id] ), DimTask[WorkType] = "Risks", DimTask[State] = "Active" )',
    "#,##0", FOLDER)
add(pm("Risks And Issues"), T, f"""
VAR _r = [{pm("Active Risks")}]
VAR _i = [{pm("Active Issues")}]
RETURN FORMAT ( _r, "0" ) & IF ( _r = 1, " risk", " risks" ) & "  ·  " & FORMAT ( _i, "0" ) & IF ( _i = 1, " issue", " issues" )""",
    folder=FOLDER)
add(pm("Overdue Tasks"), I, "CALCULATE ( [Story | Overdue Tasks], REMOVEFILTERS ( DimTask ), VALUES ( DimProject[Id] ) ) + 0", "#,##0", FOLDER,
    "Story | Overdue Tasks for the whole project: open leaf tasks (not Completed, under 100%) past their finish date.")
add(pm("Overdue Colour"), T, f"""
VAR _o = [{pm("Overdue Tasks")}]
RETURN IF ( _o = 0, "{TEAL}", IF ( _o <= 3, "{AMBER}", "{RED}" ) )""", folder=FOLDER + "\\Colours")
add(pm("Next Milestone"), T, """
VAR _m =
    TOPN ( 1,
        CALCULATETABLE ( DimTask, REMOVEFILTERS ( DimTask ), VALUES ( DimProject[Id] ), DimTask[Milestone] = TRUE (), DimTask[PercentDone] < 100,
            NOT ISBLANK ( DimTask[EndDate] ) ),
        DimTask[EndDate], ASC )
VAR _d = MINX ( _m, DimTask[EndDate] )
VAR _nm = MINX ( _m, DimTask[Name] )
RETURN
    IF ( ISBLANK ( _d ), "No open milestones",
        _nm & "  ·  " & FORMAT ( _d, "dd mmm yyyy" ) & IF ( _d < TODAY (), "  (overdue)", "" ) )""",
    folder=FOLDER, desc="Earliest open milestone (under 100%) and its due date.")

# --- governance
add(pm("Failing Rules"), I,
    "CALCULATE ( DISTINCTCOUNT ( FactPlanInsight[InsightRuleKey] ), FactPlanInsight[IsFailed] = 1 ) + 0", "#,##0", FOLDER,
    "Number of distinct OnePlan Plan Insights rules failing for this plan.")
add(pm("Rule Weight"), D, "MAX ( DimInsightRule[SeverityWeight] )", "0", FOLDER,
    "Severity weight of the rule (used to rank failing rules: heavier first).")
# Governance score colour: the model's own rule (PMO | Governance RAG Colour, 90 / 75), used directly on the page.

# --- narrative (latest status report)
add(pm("Status Report"), T, f"""
VAR _last = {LAST_REPORT}
VAR _o = CALCULATE ( MAX ( FactStatusReport[OverallHealth] ), FactStatusReport[Report_ReportEnd] = _last, REMOVEFILTERS ( DimDate ) )
VAR _sc = CALCULATE ( MAX ( FactStatusReport[ScheduleHealth] ), FactStatusReport[Report_ReportEnd] = _last, REMOVEFILTERS ( DimDate ) )
VAR _fi = CALCULATE ( MAX ( FactStatusReport[FinancialHealth] ), FactStatusReport[Report_ReportEnd] = _last, REMOVEFILTERS ( DimDate ) )
VAR _st = CALCULATE ( MAX ( FactStatusReport[Report_State] ), FactStatusReport[Report_ReportEnd] = _last, REMOVEFILTERS ( DimDate ) )
RETURN
    IF ( ISBLANK ( _last ),
        "No status report submitted yet — the texts below come from the plan's own fields.",
        "Latest status report: period ending " & FORMAT ( _last, "dd mmm yyyy" )
            & "   ·   Overall: " & {health_label("_o")} & "   ·   Schedule: " & {health_label("_sc")}
            & "   ·   Financial: " & {health_label("_fi")} & IF ( ISBLANK ( _st ), "", "   ·   " & _st ) )""",
    folder=FOLDER, desc="Header line of the latest status report (by Report_ReportEnd).")
add(pm("Accomplishments"), T, latest_report_field("Accomplishments"), folder=FOLDER)
add(pm("Planned Activities"), T, latest_report_field("PlannedActivities"), folder=FOLDER)
add(pm("Additional Comments"), T, latest_report_field("AdditionalComments"), folder=FOLDER)

# --- headline
add(pm("Headline"), T, f"""
VAR _n = SELECTEDVALUE ( DimProject[Name] )
VAR _b = [{pm("Budget")}]
VAR _e = [{pm("EAC")}]
VAR _v = [{pm("EAC Variance %")}]
VAR _r = [{pm("Active Risks")}]
VAR _i = [{pm("Active Issues")}]
VAR _od = [{pm("Overdue Tasks")}]
VAR _f = [{pm("Failing Rules")}]
RETURN
    IF ( ISBLANK ( _n ),
        "Pick a project in the slicer at the top right, or right-click a project on any page and choose Drill through › Project One-Pager (drill-through).",
        _n & " sits at the " & [{pm("Lifecycle Step")}] & " step, managed by " & [{pm("Manager")}]
            & ". Overall health: " & [{pm("Overall Health")}] & ". "
            & IF ( ISBLANK ( _e ), "No EAC in the financial plan yet. ",
                "Expected to land at " & {money("_e")} & " against a budget of " & {money("_b")}
                    & IF ( ISBLANK ( _v ), "", " (" & FORMAT ( _v, "+0%;-0%;0%" ) & ")" ) & ". " )
            & FORMAT ( _r, "0" ) & " active risk(s), " & FORMAT ( _i, "0" ) & " open issue(s) and " & FORMAT ( _od, "0" )
            & " overdue task(s); next milestone: " & [{pm("Next Milestone")}] & ". "
            & IF ( _f > 0, FORMAT ( _f, "0" ) & " Plan Insights rule(s) fail — fix those before trusting the numbers.",
                "All Plan Insights checks pass." ) )""",
    folder=FOLDER, desc="One-sentence briefing on the drilled-through project.")

# --- resource tooltip
add(pm("Resource Name"), T, 'SELECTEDVALUE ( DimResource[Name], "Several resources" )', folder=FOLDER)
add(pm("Resource Role"), T, """
VAR _r = SELECTEDVALUE ( DimResource[Role_Value] )
VAR _d = SELECTEDVALUE ( DimResource[Department_Value] )
RETURN COALESCE ( _r, "–" ) & IF ( ISBLANK ( _d ), "", "  ·  " & _d )""", folder=FOLDER)
add(pm("Resource Capacity"), D, "[Capacity | Resource Capacity]", "#,##0", FOLDER, "Calendar capacity hours (FactCapacity).")
# Same definition as the Resources page (D-01): scheduled hours on project plans, organisation-wide — a project
# filter from the hovered visual must not shrink the person's load.
add(pm("Resource Scheduled"), D, "[Story | Scheduled Hours]", "#,##0", FOLDER,
    "Scheduled hours on project plans, organisation-wide (Story | Scheduled Hours).")
add(pm("Resource Utilisation"), D, "[Story | Utilisation %]", "0%", FOLDER,
    "Scheduled hours ÷ capacity, organisation-wide (Story | Utilisation %).")
add(pm("Resource Util Colour"), T, f"""
VAR _u = [{pm("Resource Utilisation")}]
RETURN IF ( ISBLANK ( _u ) || _u = 0, "{GREY}", IF ( _u > 1, "{RED}", IF ( _u >= 0.8, "{TEAL}", IF ( _u >= 0.5, "{AMBER}", "{GREY}" ) ) ) )""",
    folder=FOLDER + "\\Colours")
add(pm("Resource Top Projects"), T, """
VAR _t =
    TOPN ( 3,
        FILTER ( ADDCOLUMNS ( VALUES ( DimProject[Name] ), "@h", [Story | Project Scheduled Hours] ),
            NOT ISBLANK ( DimProject[Name] ) && [@h] > 0 ),
        [@h], DESC )
RETURN
    IF ( COUNTROWS ( _t ) = 0, "No scheduled project work in this period.",
        CONCATENATEX ( _t, DimProject[Name] & " (" & FORMAT ( [@h], "#,0" ) & " h)", "   ·   ", [@h], DESC ) )""",
    folder=FOLDER, desc="Top three projects by scheduled hours for the hovered resource.")


# ====================================================================== visual helpers (local)
def int_cmp(entity, prop, kind, value):
    """Advanced filter on an int64 column (Int64 literal)."""
    return f_cmp(entity, prop, kind, value, int64=True)


def small_card(measure, label, value_colour=NAVY, colour_measure=None, size=14, title_size=9, units=0):
    v = card(measure, label, value_colour=value_colour, colour_measure=colour_measure, size=size, units=units)
    v["visualContainerObjects"]["title"] = title(label, title_size, MUTED)
    return v


def text_card(measure, label, size=10):
    v = headline(measure, bg="#FFFFFF", border=BORDER, size=size, colour="#2B2F36")
    v["visualContainerObjects"]["title"] = title(label, 11, NAVY)
    return v


def back_button(icon=True, text="‹  Back", tooltip="Back to the page you came from"):
    link = {"visualLink": [{"properties": {"show": b(True), "type": s("Back"), "tooltip": s(tooltip)}}],
            "border": [{"properties": {"show": b(False)}}],
            "background": [{"properties": {"show": b(False)}}]}
    if icon:
        return {"visualType": "actionButton",
                "objects": {"icon": [{"properties": {"shapeType": s("back"), "lineColor": col_solid(ORANGE),
                                                     "iconSize": n(40)}, "selector": {"id": "default"}}],
                            "fill": [{"properties": {"show": b(False)}}]},
                "visualContainerObjects": link, "drillFilterOtherVisuals": True}
    v = nav_button(text, PID["home"], tooltip, fill="#FFFFFF", hover=ORANGE_SOFT, press=ORANGE, font=NAVY, outline=BORDER)
    v["visualContainerObjects"]["visualLink"] = link["visualLink"]
    return v


def web_button(text, url_measure, tooltip):
    """Action button whose Web URL comes from a measure (button action › Web URL › fx field value)."""
    v = nav_button(text, PID["home"], tooltip)
    v["visualContainerObjects"]["visualLink"] = [{"properties": {
        "show": b(True), "type": s("WebUrl"), "webUrl": {"expr": M(url_measure)}, "tooltip": s(tooltip)}}]
    return v


def binding_page(key, width, height, display_option, binding_type, field, background=None, page_type=None):
    """Page with a pageBinding (Drillthrough / Tooltip) on one field, plus the bound page filter."""
    kw = {"background_image": background} if background else {"background_colour": "#FFFFFF"}
    pg = Page(PID[key], NAMES[key], width, height, display_option=display_option, **kw)
    ent = field["Column"]["Expression"]["SourceRef"]["Entity"]
    prop = field["Column"]["Property"]
    fname = uid("bind-filter", key, ent, prop)
    pg.page["filterConfig"] = {"filters": [{"name": fname, "field": field, "type": "Categorical",
                                            "howCreated": "Drillthrough"}]}
    pg.page["pageBinding"] = {"name": uid("bind", key), "type": binding_type,
                              "parameters": [{"name": uid("bind-param", key), "boundFilter": fname, "fieldExpr": field}]}
    if binding_type == "Drillthrough":
        # "Keep all filters" off: only the bound DimProject[Name] value travels with the drill. Row filters of the
        # source visual (a task, a month, a resource, a rule …) and its page slicers no longer narrow the One-Pager.
        pg.page["pageBinding"]["acceptsFilterContext"] = "None"
    if page_type:
        pg.page["type"] = page_type
    pg.page["visibility"] = "HiddenInViewMode"
    return pg


# ====================================================================== 1 PROJECT ONE-PAGER
def wrap_card(measure, label, size=14, **kw):
    """KPI card whose value wraps onto a second line instead of being cut off with '…'."""
    v = card(measure, label, size=size, **kw)
    v["objects"]["wordWrap"] = [{"properties": {"show": b(True)}}]
    return v


def project_slicer():
    """Single-select dropdown, no 'Select all'. Not synced: the pick belongs to the One-Pager only."""
    v = pbir.slicer(DP("Name"), "Project", sync=False)
    v["objects"]["selection"] = [{"properties": {"strictSingleSelect": b(True), "selectAllCheckboxEnabled": b(False)}}]
    return v


def build_project(drill):
    """drill=True: hidden drill-through page (right-click a project › Drill through).
    drill=False: the same page in the story flow (2d), with a Project slicer instead of the drill binding."""
    if drill:
        pg = binding_page("project", W, TALL, "FitToWidth", "Drillthrough", DP("Name"), background=BG_TALL)
        pg.add(0, 4, 60, 58, back_button(), key="back_icon")
        sub = ("Drill-through page. Only the project travels with the drill (not the filters of the page you came "
               "from): money is lifetime, the monthly charts show the whole plan.")
    else:
        pg = Page(PID["onepager"], dict(pages.PAGES)["onepager"], W, TALL, background_image=BG_TALL)
        pg.add(0, 4, 60, 58, pbir.home_icon_button(PID["home"]), key="home_icon")
        sub = ("Pick a project at the top right, or right-click a project anywhere › Drill through. "
               "Money is lifetime; the monthly charts show the whole plan.")
        pg.add(W - 16 - 260 - 12 - 380, 10, 380, 62, project_slicer(), key="slicer_project",
               filters=[pages.REAL_PROJECTS])  # no (Blank) row for strict single select to land on

    # header (title and subtitle stop short of the slicer / OnePlan button on the right)
    pg.add(62, 8, 1060, 46, textbox([[("PROJECT | ", st("DIN", 24, ORANGE, True)),
                                       ("EVERYTHING ABOUT IT BEFORE I DECIDE", st("DIN", 24, NAVY, True))]]),
           key="title")
    pg.add(62, 52, 1060, 26, textbox([[(sub, st("Segoe UI", 10, MUTED))]]), key="subtitle")
    pg.add(W - 16 - 260, 16, 260, 44, web_button("Open in OnePlan  ↗", pm("OnePlan Url"),
                                                  "Open this plan in OnePlan (new browser tab)"), key="oneplan")
    pg.add(16, 82, 1768, 82, headline(pm("Headline"), size=11), key="headline")  # tall enough to wrap to two lines

    # identity strip: taller cards, each as wide as its longest typical value (names, portfolios, programmes)
    y, h, x = 170, 86, 16
    ident = [("Name", "Project", 380, 16), ("Manager", "Project manager", 210, 13), ("Portfolio", "Portfolio", 300, 13),
             ("Programme", "Programme", 300, 13), ("Lifecycle Step", "Lifecycle step", 150, 13),
             ("% Complete", "% complete", 140, 13), ("Finish", "Finish (vs baseline)", 228, 13)]
    for k, (m, label, w, size) in enumerate(ident):
        pg.add(x, y, w, h, wrap_card(pm(m), label, size=size), key="id_name" if k == 0 else f"id{k - 1}")
        x += w + 10

    # health chips
    y, h = 262, 86
    chips = [(pm(f"{lbl} Health"), f"{lbl} health", pm(f"{lbl} Health Colour")) for lbl, _ in HEALTH]
    chips += [("PMO | Governance Score", "Governance score", "PMO | Governance RAG Colour"),
              (pm("Failing Rules"), "Failing insight rules", None)]
    w = (1768 - 10 * (len(chips) - 1)) / len(chips)
    for k, (m, label, cm) in enumerate(chips):
        opts = {"colour_measure": cm} if cm else {"value_colour": RED}
        pg.add(round(16 + k * (w + 10), 2), y, round(w, 2), h, wrap_card(m, label, size=16, **opts), key=f"chip{k}")

    # ① money
    section(pg, 352, 1, "Money — where will it land?",
            "Budget, actuals and estimate at completion over the whole life of the plan; the line shows the monthly profile.")
    vy, vh = 390, 300
    money_cards = [(pm("Budget"), "Budget", {}), (pm("Actual"), "Actual cost", {}),
                   (pm("EAC"), "EAC at completion", {"value_colour": ORANGE}),
                   (pm("EAC Variance"), "EAC − budget", {"colour_measure": pm("EAC Colour")}),
                   (pm("EAC Variance %"), "EAC variance %", {"colour_measure": pm("EAC Colour")}),
                   (pm("Burn %"), "Budget burned", {})]
    cw, ch = 285, 93
    for k, (m, label, o) in enumerate(money_cards):
        pg.add(16 + (k % 2) * (cw + 10), vy + (k // 2) * (ch + 10), cw, ch, wrap_card(m, label, size=22, **o), key=f"money{k}")
    bud, act, fc = M("Story | Budget In Period"), M("Story | Actual Cost"), M("Story | Forecast Cost")
    pg.add(606, vy, 1178, vh, chart("lineChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(bud, "Budget"), P(act, "Actual"), P(fc, "Forecast")]},
        "Monthly budget, actual and forecast cost",
        {"dataPoint": [measure_fill(bud, "#9AA3AF"), measure_fill(act, NAVY), measure_fill(fc, ORANGE)],
         "legend": legend("Top"), "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}]},
        sort=[(MONTH, "Ascending")]), key="v_money")

    # ② people
    section(pg, 700, 2, "People — is the work staffed?",
            "Scheduled hours (the work plan) against committed hours (what resource managers signed off), and who carries it.")
    vy, vh = 738, 250
    sch, com = M("Story | Project Scheduled Hours"), M("Story | Project Committed Hours")
    pg.add(16, vy, 1160, vh, chart("clusteredColumnChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(sch, "Scheduled (h)"), P(com, "Committed (h)")]},
        "Scheduled versus committed hours per month",
        {"dataPoint": [measure_fill(sch, NAVY), measure_fill(com, TEAL)], "legend": legend("Top")},
        sort=[(MONTH, "Ascending")]), key="v_people")
    pg.add(1192, vy, 592, vh, chart("tableEx",
        {"Values": [P(DR("Name"), "Resource"), P(DR("Role_Value"), "Role"), P(sch, "Scheduled h"), P(com, "Committed h")]},
        "Top resources on this project — most scheduled hours first", table_style(), sort=[(sch, "Descending")]),
        key="v_resources")

    # ③ risk & schedule
    section(pg, 1000, 3, "Risk and schedule — what could stop it?",
            "Active risks and issues by exposure, the next open milestones and the tasks already late.")
    vy, vh = 1038, 260
    obj = table_style(9)
    obj["values"] += [cf_font(DT("Impact"), "Story | Impact Colour")]
    pg.add(16, vy, 700, vh, chart("tableEx",
        {"Values": [P(DT("WorkType"), "Type"), P(DT("Name"), "Risk / issue"), P(DT("Impact"), "Impact"),
                    P(DT("Probability Category"), "Probability"), P(DT("Exposure"), "Exposure"),
                    P(DT("AssignedResources"), "Owner"), P(DT("EndDate"), "Due")]},
        "Active risks and issues — highest exposure first", obj, sort=[(DT("Exposure"), "Descending")]),
        key="v_risks", filters=[f_in("DimTask", "WorkType", ["Risks", "Issues"]), f_in("DimTask", "State", ["Active"])])
    obj = table_style(9)
    obj["values"] += [cf_font(DT("EndDate"), "Story | Due Colour")]
    pg.add(728, vy, 520, vh, chart("tableEx",
        {"Values": [P(DT("EndDate"), "Due"), P(DT("Name"), "Milestone"), P(DT("PercentDone"), "% done")]},
        "Open milestones — soonest first", obj, sort=[(DT("EndDate"), "Ascending")]),
        key="v_miles", filters=[f_in("DimTask", "Milestone", [True]), f_cmp("DimTask", "PercentDone", 3, 100)])
    obj = table_style(9)
    # Rows show only where Story | Days Overdue is non-blank, i.e. exactly the Story | Overdue Tasks population
    # (the column filters below just narrow the scan).
    od = M("Story | Days Overdue")
    pg.add(1260, vy, 524, vh, chart("tableEx",
        {"Values": [P(DT("Name"), "Task"), P(DT("AssignedResources"), "Assigned to"), P(DT("EndDate"), "Was due"),
                    P(od, "Days late"), P(DT("PercentDone"), "% done")]},
        "Late tasks — open work past its finish date", obj, sort=[(od, "Descending")]),
        key="v_late", filters=[f_in("DimTask", "WorkType", ["Tasks"]), f_in("DimTask", "Leaf", [True]),
                               f_cmp("DimTask", "PercentDone", 3, 100)])

    # ④ governance & narrative
    section(pg, 1310, 4, "Governance and the project manager's own words",
            "The OnePlan Plan Insights rules this plan fails, then the latest status report as written.")
    vy, vh = 1348, 256
    obj = table_style(9)
    pg.add(16, vy, 700, vh, chart("tableEx",
        {"Values": [P(C("DimInsightRule", "RuleName"), "Failing rule"), P(C("DimInsightRule", "Severity"), "Severity"),
                    P(C("FactPlanInsight", "ResultText"), "Finding"),
                    P(C("DimInsightRule", "RecommendedAction"), "What to do"), P(M(pm("Rule Weight")), "Weight")]},
        "Failing Plan Insights rules — heaviest first", obj, sort=[(M(pm("Rule Weight")), "Descending")]),
        key="v_rules", filters=[int_cmp("FactPlanInsight", "IsFailed", 0, 1)])
    pg.add(728, vy, 1056, 40, headline(pm("Status Report"), size=10), key="sr_head")
    tw = (1056 - 2 * 10) / 3
    for k, (m, label) in enumerate([("Accomplishments", "Accomplishments"), ("Planned Activities", "Planned activities"),
                                    ("Additional Comments", "Additional comments")]):
        pg.add(round(728 + k * (tw + 10), 2), vy + 50, round(tw, 2), vh - 50, text_card(pm(m), label), key=f"sr{k}")

    # footer buttons
    if drill:
        pg.add(16, 1620, 180, 36, back_button(icon=False), key="back")
        pg.add(206, 1620, 220, 36, nav_button("Story navigator", PID["home"], "Back to the home page",
                                              fill="#FFFFFF", hover=ORANGE_SOFT, press=ORANGE, font=NAVY, outline=BORDER),
               key="home")
    else:
        pages.next_chapter(pg, "onepager", 1620)
    pg.add(W - 16 - 340 - 12 - 280, 1620, 280, 36, nav_button("Plan vs baseline  ›", PID["baseline"],
                                                           "Cost, days, hours and FTE against the baseline (portfolio view: pick the project there)",
                                                           fill="#FFFFFF", hover=ORANGE_SOFT, press=ORANGE, font=NAVY,
                                                           outline=BORDER), key="to_baseline")
    return pg


# ====================================================================== 2 TOOLTIP · PROJECT
TIP_W, TIP_H = 320, 240


def build_tip_project():
    pg = binding_page("tip_project", TIP_W, TIP_H, "ActualSize", "Tooltip", DP("Name"), page_type="Tooltip")
    pg.add(6, 4, 308, 36, headline(pm("Name"), bg=ORANGE_SOFT, border=ORANGE, size=11), key="name")
    pg.add(6, 46, 151, 58, small_card(pm("Overall Health"), "Overall health", colour_measure=pm("Overall Health Colour"),
                                      size=12), key="health")
    pg.add(163, 46, 151, 58, small_card(pm("EAC Variance %"), "EAC vs budget", colour_measure=pm("EAC Colour")),
           key="eac")
    pg.add(6, 110, 151, 58, small_card(pm("Risks And Issues"), "Active risks · issues", value_colour=ORANGE, size=11),
           key="risks")
    pg.add(163, 110, 151, 58, small_card(pm("Overdue Tasks"), "Overdue tasks", colour_measure=pm("Overdue Colour")),
           key="overdue")
    pg.add(6, 174, 308, 60, small_card(pm("Next Milestone"), "Next milestone", size=10), key="milestone")
    return pg


# ====================================================================== 3 TOOLTIP · RESOURCE
def build_tip_resource():
    pg = binding_page("tip_resource", TIP_W, TIP_H, "ActualSize", "Tooltip", DR("Name"), page_type="Tooltip")
    pg.add(6, 4, 308, 36, headline(pm("Resource Name"), bg=ORANGE_SOFT, border=ORANGE, size=11), key="name")
    pg.add(6, 42, 308, 22, headline(pm("Resource Role"), bg="#FFFFFF", border="#FFFFFF", size=9, colour=MUTED), key="role")
    third = (308 - 2 * 6) / 3
    for k, (m, label, o) in enumerate([(pm("Resource Capacity"), "Capacity h", {}),
                                       (pm("Resource Scheduled"), "Scheduled h", {}),
                                       (pm("Resource Utilisation"), "Utilisation",
                                        {"colour_measure": pm("Resource Util Colour")})]):
        pg.add(round(6 + k * (third + 6), 2), 70, round(third, 2), 60, small_card(m, label, **o), key=f"k{k}")
    pg.add(6, 136, 308, 98, text_card(pm("Resource Top Projects"), "Top 3 projects by scheduled hours", size=9),
           key="top3")
    return pg


def build():
    return [build_project(drill=False), build_project(drill=True), build_tip_project(), build_tip_resource()]
