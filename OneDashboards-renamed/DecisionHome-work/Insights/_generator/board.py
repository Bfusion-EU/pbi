"""Board Pack: 6 export-ready 1280x720 slides built from the same measures and factories as the Insights pack."""
import pages
import story_measures
import pbir
import extensions  # noqa: F401  (registers extension measures)
import a11y
from ext_status import mm
from pbir import (Page, P, M, C, s, b, st, textbox, shape, image, chart, legend, labels_on,
                  measure_colour, series_colours, table_style, cf_font, cf_back, f_in, headline, NAVY, ORANGE, RED,
                  TEAL, HEALTH_COLOURS)

MONTH_TITLE = "Story | Board · Month Title"
story_measures.add(MONTH_TITLE, story_measures.T,
                   '"Status month: " & [Story | Status · MoM Month Label] & "  ·  compared with " '
                   '& [Story | Status · MoM Previous Month Label]', None, "Story\\Board",
                   "Board Pack: month line shown under the title bar of every slide.")

pbir.EXTENSION_MEASURES.add(MONTH_TITLE)

W, H = 1280, 720
DP, DT, DR = pages.DP, pages.DT, pages.DR
SLIDES = [("summary", "BOARD SUMMARY"), ("course", "ARE WE ON COURSE?"), ("money", "WHERE WILL THE MONEY LAND?"),
          ("people", "DO WE HAVE THE PEOPLE?"), ("risk", "WHAT COULD GO WRONG?"),
          ("changes", "WHAT CHANGED SINCE LAST MONTH?")]
DISPLAYS = {"summary": "1 · Board summary", "course": "2 · On course", "money": "3 · Money", "people": "4 · People",
            "risk": "5 · Risk", "changes": "6 · What changed"}
LOGO_RES = "OnePlan_logo_-_dark_background9901469509814106.png"   # same resource as the Home logo
Y0, YK, YB, HB = 96, 162, 252, 416          # headline, KPI row, chart/table band (252-668)
LEFT = (16, YB, 500, HB)
RIGHT = (526, YB, 738, HB)
FULL = (16, YB, 1248, HB)


def frame(pg, n_, question):
    pg.add(0, 0, W, 56, shape(NAVY), key="titlebar")
    pg.add(16, 10, 124, 36, textbox([[("BFUSION", st("DIN", 16, "#FFFFFF", True))]]), key="brand")
    pg.add(150, 8, 960, 40, textbox([[(question, st("DIN", 20, "#FFFFFF", True))]]), key="question")
    pg.add(1180, 16, 84, 28, textbox([[(f"{n_} / 6", st("Segoe UI", 11, "#FFFFFF"))]], align="right"), key="pageno")
    month = headline(MONTH_TITLE, bg="#FFFFFF", border="#FFFFFF", size=11)
    month["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    month["visualContainerObjects"]["background"] = [{"properties": {"show": b(False)}}]
    month["objects"]["labels"][0]["properties"]["fontFamily"] = s("Segoe UI Semibold")
    pg.add(16, 62, 600, 24, month, key="month")
    logo = image(LOGO_RES, "OnePlan logo")
    logo["objects"]["image"][0]["properties"]["sourceFile"]["image"]["scaling"] = s("Fit")
    pg.add(1150, 680, 114, 30, logo, key="oneplan_logo")


def slide(key, n_, head, kpis=None):
    pg = Page(pbir.uid("board-page", key), DISPLAYS[key], W, H, background_colour="#FFFFFF", display_option="FitToPage")
    frame(pg, n_, dict(SLIDES)[key])
    pg.add(16, Y0, 1248, 56, headline(head, size=12), key="headline")
    if kpis:
        pages.kpi_row(pg, YK, kpis, h=80, x0=16, width=1248)
    return pg


def put(pg, box, visual, key, filters=None):
    pg.add(*box, visual, key=key, filters=filters)


def build_summary():
    pg = slide("summary", 1, "Story | Exec Headline", [
        ("Story | Active Projects", "Active projects"),
        ("Story | On Track %", "On track"),
        ("Story | EAC Variance %", "EAC vs budget", {"colour_measure": "Story | Variance Colour"}),
        ("Story | Utilisation %", "Utilisation", {"colour_measure": "Story | Util Colour"}),
        ("Story | Critical High Risks", "Critical / high risks", {"value_colour": RED}),
        ("PMO | Governance Score", "Data trust"),
    ])
    for k, m in enumerate(["Story | Exec Action Money", "Story | Exec Action People", "Story | Exec Action Risk"]):
        pg.add(16, YB + k * 144, 500, 128, headline(m, bg="#FFFFFF", border=ORANGE, size=12), key=f"act{k}")
    score = M("Story | Home · Act Score")
    # Rows only where the project is flagged: Act Reason and Act Score are blank for the others.
    # No filter on the extension measure (it renders empty in Desktop).
    fields = [DP("Name"), M("Story | Home · Act Reason"), score]
    style = table_style(10)
    style["columnWidth"] = [{"properties": {"value": pbir.n(w)}, "selector": {"metadata": pbir.qref(f)}}
                            for f, w in zip(fields, (300, 360, 60))]
    t = chart("tableEx", {"Values": [P(fields[0], "Project"), P(fields[1], "Why"), P(score, "Impact")]},
              "Act now — ranked by impact", style, sort=[(score, "Descending")])
    put(pg, RIGHT, t, "v_act")
    return pg


def build_course():
    pg = slide("course", 2, "Story | Schedule Headline", [
        ("Story | On Schedule %", "On schedule"),
        ("Story | Schedule At Risk", "Schedule at risk", {"value_colour": pbir.AMBER}),
        ("Story | Schedule Off Track", "Schedule off track", {"value_colour": RED}),
        ("Story | Late vs Baseline KPI", "Late vs baseline", {"size": pbir.KPI_TEXT_PT}),
        ("Story | Overdue Tasks", "Overdue tasks", {"value_colour": RED}),
    ])
    health, active = DP("OverallHealth_Value"), M("Story | Active Projects")
    put(pg, LEFT, chart("donutChart", {"Category": [P(health, "Overall health")], "Y": [P(active, "Active projects")]},
                        "Overall health of active projects",
                        {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Bottom"),
                         "labels": [{"properties": {"show": b(True), "labelStyle": s("Category, percent of total")}}]}),
        "v_health")
    put(pg, RIGHT, chart("hundredPercentStackedBarChart",
                         {"Category": [P(DP("Program Name"), "Program")], "Series": [P(health, "Health")],
                          "Y": [P(active, "Active projects")]},
                         "Health mix of active projects per programme",
                         {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Top")}),
        "v_health_prog")
    return pg


def build_money():
    pg = slide("money", 3, "Story | Finance Headline", [
        ("Story | Budget At Completion", "Budget at completion"),
        ("Story | Finance EAC", "EAC"),
        ("Story | EAC Variance", "EAC − budget", {"colour_measure": "Story | Variance Colour"}),
        ("Story | EAC Variance %", "EAC variance %", {"colour_measure": "Story | Variance Colour"}),
        ("Story | To-Date Variance %", "Actual vs budget to date", {"colour_measure": "Story | To-Date Colour"}),
    ])
    var, vp = M("Story | EAC Variance"), M("Story | EAC Variance %")
    put(pg, LEFT, chart("clusteredBarChart", {"Category": [P(DP("Name"), "Project")], "Y": [P(var, "EAC − budget")]},
                        "Projects ranked by overrun at completion",
                        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Variance Fill")},
                                        "selector": pages.FILL_ALL}], "labels": labels_on(True, 0)},
                        sort=[(var, "Descending")]), "v_proj_var", filters=[pages.REAL_PROJECTS])
    bac, eac = M("Story | Budget At Completion"), M("Story | Finance EAC")
    obj = table_style(10)
    obj["values"] += [cf_font(vp, "Story | Variance Colour"), cf_font(var, "Story | Variance Colour")]
    put(pg, RIGHT, chart("tableEx", {"Values": [P(DP("Name"), "Project"), P(bac, "Budget"), P(eac, "EAC"),
                                                 P(var, "EAC − budget"), P(vp, "Variance %")]},
                         "Project financial register", obj, sort=[(var, "Descending")]),
        "v_fin_table", filters=[pages.REAL_PROJECTS])
    return pg


def build_people():
    pg = slide("people", 4, "Story | Resource Headline", [
        ("Story | Utilisation %", "Utilisation", {"colour_measure": "Story | Util Colour"}),
        ("Story | Over-allocated People", "Over 100% in a month", {"value_colour": RED}),
        ("Story | Free Capacity (h)", "Free capacity (h)", {"value_colour": TEAL}),
        ("Story | Scheduled Hours", "Scheduled hours"),
    ])
    util = M("Story | Utilisation %")
    put(pg, FULL, chart("clusteredBarChart", {"Category": [P(DR("Role_Value"), "Role")], "Y": [P(util, "Utilisation")]},
                        "Utilisation by role",
                        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Util Fill")},
                                        "selector": pages.FILL_ALL}], "labels": labels_on(True)},
                        sort=[(util, "Descending")]), "v_role")
    return pg


def build_risk():
    pg = slide("risk", 5, "Story | Risk Headline", [
        ("Story | Active Risk Count", "Active risks"),
        ("Story | Critical High Risks", "Critical / high", {"value_colour": RED}),
        ("Story | Open Issues", "Open issues", {"value_colour": RED}),
        ("Story | Unmitigated Risk %", "No mitigation recorded", {"value_colour": pbir.AMBER}),
    ])
    risk_filter = [f_in("DimTask", "WorkType", ["Risks"]), f_in("DimTask", "State", ["Active"]), pages.PROJECT_TASKS]
    rc, exp = M("Story | Active Risk Count"), M("Story | Risk Exposure")
    obj = table_style(10)
    obj["values"] += [cf_back(rc, "Story | Heat Colour")]
    put(pg, LEFT, chart("pivotTable", {"Rows": [P(DT("Impact"), "Impact", True)],
                                        "Columns": [P(DT("Probability Category"), "Probability", True)],
                                        "Values": [P(rc, "Risks")]},
                        "Risk heat map — impact × probability", obj, sort=[(DT("Impact"), "Ascending")]),
        "v_heatmap", filters=risk_filter)
    obj = table_style(10)
    obj["values"] += [cf_font(DT("Impact"), "Story | Impact Colour")]
    put(pg, RIGHT, chart("tableEx", {"Values": [P(DP("Name"), "Project"), P(DT("Name"), "Risk"), P(DT("Impact"), "Impact"),
                                                 P(DT("Probability Category"), "Probability"),
                                                 P(exp, "Exposure score"), P(DT("AssignedResources"), "Owner")]},
                         "Top-risk register", obj, sort=[(exp, "Descending")]), "v_risk_table", filters=risk_filter)
    return pg


def build_changes():
    pg = slide("changes", 6, mm("Headline"), [
        (mm("Worsened"), "Health worse", {"value_colour": RED}),
        (mm("Improved"), "Health better", {"value_colour": TEAL}),
        (mm("Dates KPI"), "Finish dates moved (net)", {"size": pbir.KPI_TEXT_PT}),
        (mm("Forecast Net"), "Forecast moved (net €)"),
        (mm("Risks Net"), "Active risks (net)"),
        (mm("New Closed KPI"), "New · closed", {"size": pbir.KPI_TEXT_PT}),
        (mm("Not Comparable"), "Not comparable", {"value_colour": pbir.AMBER}),
    ])
    size, hc = M(mm("L · Size")), M(mm("L · Health Change"))
    obj = table_style(10)
    obj["values"] += [cf_font(hc, mm("Health Change Colour"))]
    put(pg, FULL, chart("tableEx", {"Values": [P(DP("Name"), "Project"), P(hc, "Health: last month → now"),
                                                P(M(mm("L · Finish Shift (d)")), "Finish Δ days"),
                                                P(M(mm("L · Forecast Delta")), "Forecast Δ"),
                                                P(M(mm("L · Risks Delta")), "Risks Δ"),
                                                P(M(mm("L · State Change")), "State"),
                                                P(M(mm("L · May Slip")), "May slip"), P(size, "Change size")]},
                         "Change ledger — this month versus last month", obj, sort=[(size, "Descending")]),
        "v_ledger", filters=[pages.REAL_PROJECTS])
    return pg


def build_board():
    built = [build_summary(), build_course(), build_money(), build_people(), build_risk(), build_changes()]
    pages.filter_real_projects(built)
    a11y.apply(built)
    return built


def period_filter():
    """Unlocked DimDate[Period] report filter: lets the user pick the status month before exporting."""
    return {"name": pbir.uid("board-filter", "period"), "ordinal": 20,
            "field": C("DimDate", "Period"), "type": "Categorical", "howCreated": "User"}
