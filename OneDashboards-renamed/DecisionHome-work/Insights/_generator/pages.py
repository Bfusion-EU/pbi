"""Page layouts for the BFusion Insights pack — one story per subject area.

Every analytic page follows the same narrative grammar (copied from the
Timesheet Dashboard in OneDashboards - Bfusion):
  header (AREA | QUESTION?) -> orange headline sentence (measure) ->
  ① the pulse (KPI cards) -> ② trend / composition -> ③ drivers -> ④ the list to act on
  -> "Next chapter" button.
"""
from pbir import *  # noqa: F401,F403
import pbir

W = 1800
TALL = 1800
BG_TALL = "bfv5_footer_band_1800x1800.png"

PAGES = [  # (key, display name)
    ("home", "Home — Story Navigator"),
    ("exec", "1 · Executive Summary"),
    ("portfolio", "2 · Portfolio"),
    ("finance", "3 · Financials"),
    ("finance2", "3b · Pareto & Portfolio P&L"),
    ("resources", "4 · Resource Management"),
    ("schedule", "5 · Planning & Scheduling"),
    ("risk", "6 · Risk Management"),
    ("benefits", "7 · Benefits & Value"),
    ("governance", "8 · Governance & Data Trust"),
]
PID = {k: uid("insights-page", k) for k, _ in PAGES}
ORDER = [k for k, _ in PAGES]

# ---------------------------------------------------------------- common bits
DP = lambda p: C("DimProject", p)  # noqa: E731
DT = lambda p: C("DimTask", p)  # noqa: E731
DR = lambda p: C("DimResource", p)  # noqa: E731
MONTH = C("DimDate", "MonthStart")
CIRCLED = "①②③④⑤"


def header(pg, area, question, subtitle, slicers):
    pg.add(0, 4, 60, 58, home_icon_button(PID["home"]), key="home")
    pg.add(62, 8, 960, 46, textbox([[(f"{area} | ", st("DIN", 24, ORANGE, True)),
                                      (question, st("DIN", 24, NAVY, True))]]), key="title")
    pg.add(62, 52, 975, 26, textbox([[(subtitle, st("Segoe UI", 11, MUTED))]]), key="subtitle")
    x = W - 16 - len(slicers) * 188 + 8
    for k, (field, label) in enumerate(slicers):
        pg.add(x + k * 188, 10, 180, 62, slicer(field, label), key=f"slicer{k}")


def section(pg, y, num, question, explain, width=1768, x=16):
    pg.add(x, y, width, 34, textbox([[(f"{CIRCLED[num - 1]}  {question}", st("Segoe UI Semibold", 15, NAVY, True)),
                                      (f"   {explain}", st("Segoe UI", 11, MUTED))]]), key=f"sec{num}")


def kpi_row(pg, y, items, h=90, x0=16, width=1768, gap=10):
    w = (width - gap * (len(items) - 1)) / len(items)
    for k, it in enumerate(items):
        measure, label = it[0], it[1]
        opts = it[2] if len(it) > 2 else {}
        pg.add(round(x0 + k * (w + gap), 2), y, round(w, 2), h, card(measure, label, **opts), key=f"kpi{y}_{k}")


def next_chapter(pg, key, y):
    idx = ORDER.index(key)
    if idx + 1 < len(ORDER):
        nxt = ORDER[idx + 1]
        label = dict(PAGES)[nxt].split("·", 1)[-1].strip()
        pg.add(W - 16 - 300, y, 300, 36, nav_button(f"Next chapter: {label}  ›", PID[nxt],
                                                     "Continue the story on the next page"), key="next")
    pg.add(16, y, 220, 36, nav_button("‹  Story navigator", PID["home"], "Back to the home page",
                                      fill="#FFFFFF", hover=ORANGE_SOFT, press=ORANGE, font=NAVY, outline=BORDER),
           key="back")


def legend_note(pg, x, y, w, items, key):
    runs = []
    for k, (label, colour) in enumerate(items):
        runs.append(("■ " if k == 0 else "     ■ ", st("Segoe UI", 12, colour)))
        runs.append((label, st("Segoe UI", 10, colour, True)))
    pg.add(x, y, w, 28, textbox([runs], align="right"), key=key)


def analytic_page(key, area, question, subtitle, slicers, headline_measure):
    pg = Page(PID[key], dict(PAGES)[key], W, TALL, background_image=BG_TALL)
    header(pg, area, question, subtitle, slicers)
    pg.add(16, 84, 1768, 56, headline(headline_measure), key="headline")
    return pg


STD_SLICERS = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (DP("ProjectType_Value"), "Project type"), (C("DimDate", "Year"), "Year")]

Y1, Y1K = 150, 188           # ① section + KPI row
Y2, Y2V, H2 = 294, 334, 340  # ② section + visuals
Y3, Y3V, H3 = 690, 730, 400  # ③
Y4, Y4V, H4 = 1146, 1186, 400  # ④
YNEXT = 1606


# ================================================================= HOME
def build_home():
    pg = Page(PID["home"], dict(PAGES)["home"], W, 1000, background_colour=NAVY_BG, display_option="FitToPage")
    # brand mark (equaliser bars like the Pulse home page)
    for k, (x, h) in enumerate([(40, 10), (48, 17), (56, 13), (64, 20), (72, 9)]):
        pg.add(x, 30 - h / 2 + 5, 5, h, shape(ORANGE), key=f"bar{k}")
    pg.add(87, 16, 240, 41, textbox([[("BFUSION", st("DIN", 18, "#FFFFFF", True))]]), key="brand")
    pg.add(1648, 12, 125, 55, image("OnePlan_logo_-_dark_background9901469509814106.png", "OnePlan logo"), key="logo")
    pg.add(40, 52, 1100, 60, textbox([[("PPM Insights 360°", st("DIN", 28, "#FFFFFF", True)),
                                       ("   native story pack", st("DIN", 16, PEACH, False))]]), key="title")
    pg.add(40, 108, 1300, 32, textbox([[("Eight chapters, one question each. Read the orange headline first, "
                                         "then follow ① → ④ down the page to the list you act on.",
                                         st("Segoe UI", 12, SLATE))]]), key="sub")
    pg.add(40, 146, 1720, 1, shape(NAVY_LINE), key="rule1")
    # pulse strip
    pulse = [("Portfolio 360 | Active Projects", "Active projects", {}),
             ("Story | On Track %", "On track", {}),
             ("Story | Forecast Variance %", "Forecast vs budget", {"colour_measure": "Story | Variance Colour"}),
             ("Capacity | Resource Utilization%", "Utilisation", {"colour_measure": "Story | Util Colour"}),
             ("Story | Critical High Risks", "Critical / high risks", {"value_colour": "#FF8A80"}),
             ("Benefits | Realization Rate (%)", "Benefits realised", {})]
    w = (1720 - 5 * 12) / 6
    for k, (m, label, o) in enumerate(pulse):
        o = dict(o)
        o.setdefault("value_colour", "#FFFFFF")
        pg.add(round(40 + k * (w + 12), 2), 158, round(w, 2), 84, card(m, label, size=22, dark=True, **o), key=f"pulse{k}")
    # chapter tiles 4 x 2
    tiles = [
        ("exec", "Are we on course?", "Executive board · monthly",
         "One number per question, the three decisions this month asks for."),
        ("portfolio", "Are we investing in the right things?", "Portfolio board · quarterly",
         "Where the money goes, strategic fit, value versus priority."),
        ("finance", "Are we spending as planned?", "Finance & PMO · monthly close",
         "Budget, actuals, forecast and variance — then Pareto and the portfolio P&L."),
        ("resources", "Do we have the people?", "Resource managers · monthly",
         "Capacity against demand, who is overloaded, where demand is still soft."),
        ("schedule", "Will we deliver on time?", "Delivery leads · weekly",
         "Schedule health, baseline slippage, milestones and late work."),
        ("risk", "What could go wrong?", "Risk owners · fortnightly",
         "Heat map, exposure concentration and the risks to escalate."),
        ("benefits", "Will it pay off?", "Sponsors & benefit owners · quarterly",
         "Benefits against cost, realisation so far, value for money."),
        ("governance", "Can we trust the data?", "PMO · weekly",
         "Governance score, failing OnePlan insight rules, hygiene gaps."),
    ]
    tw, th, gx, gy = (1720 - 3 * 20) / 4, 330, 20, 20
    for k, (pk, q, who, what) in enumerate(tiles):
        col, row = k % 4, k // 4
        x = round(40 + col * (tw + gx), 2)
        y = 262 + row * (th + gy)
        pg.add(x, y, round(tw, 2), th, shape(NAVY_TILE, radius=8, line=NAVY_LINE), key=f"tile{k}")
        pg.add(x, y, 4, th, shape(ORANGE), key=f"tilebar{k}")
        pg.add(x + 18, y + 14, 60, 34, textbox([[(f"0{k + 1}", st("DIN", 20, ORANGE, True))]]), key=f"tnum{k}")
        pg.add(x + 18, y + 50, round(tw - 36, 2), 90, textbox([[(q, st("DIN", 19, "#FFFFFF", True))]]), key=f"tq{k}")
        pg.add(x + 18, y + 142, round(tw - 36, 2), 30, textbox([[(who, st("Segoe UI", 10, PEACH, True))]]), key=f"tw{k}")
        pg.add(x + 18, y + 174, round(tw - 36, 2), 80, textbox([[(what, st("Segoe UI", 11, SLATE))]]), key=f"td{k}")
        if pk == "finance":
            half = round((tw - 36 - 10) / 2, 2)
            pg.add(x + 18, y + th - 56, half, 38,
                   nav_button("3 · Spend  ›", PID[pk], what, fill=NAVY_BTN, hover=NAVY_BTN, press=ORANGE,
                              font=PEACH, align="left", outline=ORANGE), key=f"tb{k}")
            pg.add(round(x + 28 + half, 2), y + th - 56, half, 38,
                   nav_button("3b · Pareto & P&L  ›", PID["finance2"], "Pareto analysis and the portfolio P&L",
                              fill=NAVY_BTN, hover=NAVY_BTN, press=ORANGE, font=PEACH, align="left", outline=ORANGE),
                   key=f"tb{k}b")
        else:
            pg.add(x + 18, y + th - 56, round(tw - 36, 2), 38,
                   nav_button(f"Open chapter {k + 1}  ›", PID[pk], what, fill=NAVY_BTN, hover=NAVY_BTN, press=ORANGE,
                              font=PEACH, align="left", outline=ORANGE), key=f"tb{k}")
    pg.add(40, 952, 1720, 1, shape(NAVY_LINE), key="rule2")
    pg.add(40, 960, 400, 31, textbox([[("BFUSION  ·  bfusion.eu", st("Segoe UI", 9, SLATE, True))]]), key="foot1")
    pg.add(960, 958, 800, 34, headline("Story | Refreshed", bg=NAVY_BG, border=NAVY_BG, size=9, colour=SLATE), key="foot2")
    return pg


# ================================================================= 1 EXECUTIVE
def build_exec():
    pg = analytic_page("exec", "EXECUTIVE", "ARE WE ON COURSE?",
                       "The whole portfolio on one page: health, money, people and risk — and the three decisions this month asks for.",
                       STD_SLICERS, "Story | Exec Headline")
    section(pg, Y1, 1, "The pulse — one number per question",
            "Green is fine, amber needs a look, red needs a decision.")
    kpi_row(pg, Y1K, [
        ("Portfolio 360 | Active Projects", "Active projects"),
        ("Story | On Track %", "Projects on track"),
        ("Story | Forecast Variance %", "Forecast vs budget", {"colour_measure": "Story | Variance Colour"}),
        ("Story | Burn %", "Budget burned", {"colour_measure": "Story | Burn Colour"}),
        ("Capacity | Resource Utilization%", "Utilisation", {"colour_measure": "Story | Util Colour"}),
        ("Capacity | Over-Allocated Resource Count", "Over-allocated people", {"value_colour": RED}),
        ("Story | Critical High Risks", "Critical / high risks", {"value_colour": RED}),
        ("Benefits | Realization Rate (%)", "Benefits realised"),
    ])
    section(pg, Y2, 2, "Where is the portfolio heading?", "Health mix, money by portfolio and the people curve.")
    health = DP("OverallHealth_Value")
    pg.add(16, Y2V, 560, H2, chart("donutChart",
        {"Category": [P(health, "Overall health")], "Y": [P(M("Project | Plans Count"), "Projects")]},
        "Overall health of the portfolio",
        {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Bottom"),
         "labels": [{"properties": {"show": b(True), "labelStyle": s("Category, percent of total")}}]}), key="v_health")
    bud, fc = M("Finance | Budget Cost"), M("Finance | Forecast Cost")
    pg.add(592, Y2V, 590, H2, chart("clusteredBarChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Y": [P(bud, "Budget"), P(fc, "Forecast")]},
        "Budget versus forecast by portfolio",
        {"dataPoint": [measure_fill(bud, "#C9CED8"), measure_fill(fc, ORANGE)], "legend": legend("Top")},
        sort=[(fc, "Descending")]), key="v_bvf")
    cap, sch = M("Capacity | Resource Capacity"), M("Capacity | Total Hours Scheduled")
    pg.add(1198, Y2V, 586, H2, chart("lineClusteredColumnComboChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(cap, "Capacity (h)")], "Y2": [P(sch, "Scheduled (h)")]},
        "People: capacity versus scheduled hours per month",
        {"dataPoint": [measure_fill(cap, "#D9DDE3"), measure_fill(sch, NAVY)], "legend": legend("Top"),
         "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}]},
        sort=[(MONTH, "Ascending")]), key="v_people")
    section(pg, Y3, 3, "What needs a decision this month?",
            "Projects ranked by forecast overrun, with the three actions the data points to.")
    vp = M("Story | Plan Variance %")
    cols = [P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"), P(health, "Health"),
            P(M("Story | Plan Budget"), "Budget"), P(M("Story | Plan Forecast"), "Forecast"), P(vp, "Variance %"),
            P(M("Project | Active Risks"), "Active risks"), P(M("Task | Overdue Tasks"), "Overdue tasks")]
    obj = table_style()
    obj["values"] += [cf_font(vp, "Story | Plan Variance Colour"), cf_font(health, "Story | Health Colour")]
    pg.add(16, Y3V, 1160, H3, chart("tableEx", {"Values": cols}, "Attention list — biggest forecast overruns first",
                                    obj, sort=[(vp, "Descending")]), key="v_attn")
    for k, m in enumerate(["Story | Exec Action Money", "Story | Exec Action People", "Story | Exec Action Risk"]):
        pg.add(1192, Y3V + k * 136, 592, 124, headline(m, bg="#FFFFFF", border=ORANGE, size=12), key=f"act{k}")
    section(pg, Y4, 4, "Where should I look next?", "Each chapter answers one question in depth.")
    chapters = ORDER[2:]
    bw = (1768 - 10 * (len(chapters) - 1)) / len(chapters)
    for k, ck in enumerate(chapters):
        label = dict(PAGES)[ck]
        pg.add(round(16 + k * (bw + 10), 2), Y4V, round(bw, 2), 60,
               nav_button(label + "  ›", PID[ck], "Open this chapter", fill=NAVY, hover=NAVY_BTN, press=ORANGE,
                          font="#FFFFFF", size=11), key=f"chap{k}")
    pg.add(16, Y4V + 80, 1768, 300, chart("pivotTable",
        {"Rows": [P(DP("Portfolio Name"), "Portfolio", True), P(DP("Program Name"), "Program", True)],
         "Values": [P(M("Portfolio 360 | Active Projects"), "Active projects"), P(M("Story | On Track %"), "On track"),
                    P(M("Finance | Budget Cost"), "Budget"), P(M("Finance | Forecast Cost"), "Forecast"),
                    P(M("Story | Forecast Variance %"), "Variance %"),
                    P(M("Capacity | Total Hours Scheduled"), "Scheduled h"),
                    P(M("Project | Active Risks"), "Active risks"),
                    P(M("Benefits | Planned Benefits"), "Planned benefits")]},
        "Portfolio scorecard — expand a portfolio to see its programmes",
        dict(table_style(), values=table_style()["values"] + [cf_font(M("Story | Forecast Variance %"), "Story | Variance Colour")])),
        key="v_scorecard")
    next_chapter(pg, "exec", YNEXT)
    return pg


# ================================================================= 2 PORTFOLIO
def build_portfolio():
    pg = analytic_page("portfolio", "PORTFOLIO", "ARE WE INVESTING IN THE RIGHT THINGS?",
                       "Where the plan budget goes, how well it fits the strategy, and whether priority and value line up.",
                       STD_SLICERS, "Story | Portfolio Headline")
    section(pg, Y1, 1, "What is in the portfolio?", "Size, pipeline and strategic fit at a glance.")
    kpi_row(pg, Y1K, [
        ("Portfolio 360 | Active Projects", "Active projects"),
        ("Story | Proposed Projects", "Proposals in pipeline"),
        ("Story | Plan Budget", "Plan budget"),
        ("Story | Aligned Budget %", "Budget strongly aligned"),
        ("Modeler | Alignment Score", "Alignment score (0–100)"),
        ("Story | On Track %", "Projects on track"),
        ("Project | Total CostofDelay", "Cost of delay"),
    ])
    section(pg, Y2, 2, "Where does the money go?", "Budget by portfolio coloured by strategic alignment, by goal and by project type.")
    align = DP("StrategicAlignment_Value")
    budget = M("Story | Plan Budget")
    pg.add(16, Y2V, 878, H2, chart("barChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Series": [P(align, "Alignment")], "Y": [P(budget, "Budget")]},
        "Plan budget by portfolio and strategic alignment",
        {"dataPoint": series_colours(align, {"Extreme": NAVY, "Strong": TEAL, "Moderate": "#7FB7B7", "Low": AMBER,
                                             "Not Rated": "#C9CED8"}),
         "legend": legend("Top")}, sort=[(budget, "Descending")]), key="v_bud_align")
    pg.add(906, Y2V, 434, H2, chart("donutChart",
        {"Category": [P(DP("Goals_Value"), "Goal")], "Y": [P(budget, "Budget")]}, "Budget by strategic goal",
        {"legend": legend("Bottom"), "labels": [{"properties": {"show": b(True), "labelStyle": s("Percent of total")}}]}),
        key="v_goal")
    pg.add(1350, Y2V, 434, H2, chart("donutChart",
        {"Category": [P(DP("ProjectType_Value"), "Project type")], "Y": [P(budget, "Budget")]}, "Budget by project type",
        {"legend": legend("Bottom"), "labels": [{"properties": {"show": b(True), "labelStyle": s("Percent of total")}}]}),
        key="v_type")
    section(pg, Y3, 3, "Are the right projects first?",
            "Top-right = high priority and big budget. Red bubbles high up are the conversations to have.")
    health = DP("OverallHealth_Value")
    pg.add(16, Y3V, 1060, H3, chart("scatterChart",
        {"Category": [P(DP("Name"), "Project")], "Series": [P(health, "Health")],
         "X": [P(M("Modeler | Priority Score"), "Priority score")], "Y": [P(budget, "Plan budget")],
         "Size": [P(M("Story | Plan Forecast"), "Forecast")]},
        "Priority versus budget — bubble size = forecast, colour = overall health",
        {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Top"),
         "categoryLabels": [{"properties": {"show": b(True), "fontSize": n(8)}}]}), key="v_scatter")
    pg.add(1092, Y3V, 692, H3, chart("hundredPercentStackedBarChart",
        {"Category": [P(DP("Program Name"), "Program")], "Series": [P(health, "Health")],
         "Y": [P(M("Project | Plans Count"), "Projects")]},
        "Health mix per programme",
        {"dataPoint": series_colours(health, HEALTH_COLOURS), "legend": legend("Top")}), key="v_health_prog")
    section(pg, Y4, 4, "The portfolio register", "Portfolio › programme › project. Red variance = forecast more than 5% over plan budget.")
    vp = M("Story | Plan Variance %")
    obj = table_style()
    obj["values"] += [cf_font(vp, "Story | Plan Variance Colour")]
    pg.add(16, Y4V, 1768, H4, chart("pivotTable",
        {"Rows": [P(DP("Portfolio Name"), "Portfolio", True), P(DP("Program Name"), "Program", True),
                  P(DP("Name"), "Project", True)],
         "Values": [P(M("Project | Plans Count"), "Projects"), P(budget, "Plan budget"),
                    P(M("Story | Plan Forecast"), "Forecast"), P(vp, "Variance %"),
                    P(M("Modeler | Alignment Score"), "Alignment"), P(M("Modeler | Priority Score"), "Priority"),
                    P(M("Project | Active Risks"), "Active risks"), P(M("Benefits | Planned Benefits"), "Benefits")]},
        "Portfolio register", obj), key="v_register")
    next_chapter(pg, "portfolio", YNEXT)
    return pg


# ================================================================= 3 FINANCIALS
def build_finance():
    pg = analytic_page("finance", "FINANCIALS", "ARE WE SPENDING AS PLANNED?",
                       "Time-phased budget, actuals and forecast from the OnePlan financial plans — and the projects that drive the variance.",
                       STD_SLICERS, "Story | Finance Headline")
    section(pg, Y1, 1, "Where do we stand?", "Forecast at completion against budget is the number the board asks for.")
    kpi_row(pg, Y1K, [
        ("Finance | Budget Cost", "Budget"),
        ("Finance | Actual Cost", "Actual cost"),
        ("Finance | Forecast Cost", "Forecast"),
        ("Story | Forecast Variance", "Forecast − budget", {"colour_measure": "Story | Variance Colour"}),
        ("Story | Forecast Variance %", "Variance %", {"colour_measure": "Story | Variance Colour"}),
        ("Story | Burn %", "Budget burned", {"colour_measure": "Story | Burn Colour"}),
        ("Story | Projects Over Budget", "Projects over budget", {"value_colour": RED}),
    ])
    section(pg, Y2, 2, "How is spend tracking over time?",
            "Cumulative curves: forecast above budget means the gap is opening; actuals flattening means delivery slowed.")
    cb, ca, cf = M("Finance | Cumulative Budget Cost"), M("Finance | Cumulative Actual Cost"), M("Finance | Cumulative Forecast Cost")
    pg.add(16, Y2V, 1160, H2, chart("lineChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(cb, "Budget (cum.)"), P(ca, "Actual (cum.)"), P(cf, "Forecast (cum.)")]},
        "S-curve — cumulative budget, actuals and forecast",
        {"dataPoint": [measure_fill(cb, "#9AA3AF"), measure_fill(ca, NAVY), measure_fill(cf, ORANGE)],
         "legend": legend("Top"), "lineStyles": [{"properties": {"strokeWidth": n(3)}}]},
        sort=[(MONTH, "Ascending")]), key="v_scurve")
    b_, a_, f_ = M("Finance | Budget Cost"), M("Finance | Actual Cost"), M("Finance | Forecast Cost")
    pg.add(1192, Y2V, 592, H2, chart("clusteredColumnChart",
        {"Category": [P(C("DimDate", "Quarter Name"), "Quarter")], "Y": [P(b_, "Budget"), P(a_, "Actual"), P(f_, "Forecast")]},
        "Per quarter — budget, actual, forecast",
        {"dataPoint": [measure_fill(b_, "#C9CED8"), measure_fill(a_, NAVY), measure_fill(f_, ORANGE)],
         "legend": legend("Top")}, sort=[(C("DimDate", "Quarter Name"), "Ascending")]), key="v_quarter")
    section(pg, Y3, 3, "Where is the variance coming from?",
            "Bars up = programmes forecasting more than budget; the right chart names the projects behind it.")
    var = M("Story | Forecast Variance")
    pg.add(16, Y3V, 878, H3, chart("waterfallChart",
        {"Category": [P(DP("Program Name"), "Program")], "Y": [P(var, "Forecast − budget")]},
        "Variance bridge by programme (forecast − budget)",
        {"sentimentColors": [{"properties": {"increaseFill": col_solid(RED), "decreaseFill": col_solid(TEAL),
                                             "totalFill": col_solid(NAVY)}}],
         "labels": labels_on(True, 0)}, sort=[(var, "Descending")]), key="v_waterfall")
    pg.add(906, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(var, "Forecast − budget")]},
        "Projects ranked by forecast overrun",
        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Variance Colour")},
                        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
         "labels": labels_on(True, 0)}, sort=[(var, "Descending")]), key="v_proj_var")
    section(pg, Y4, 4, "Project financial register",
            "Sorted by overrun. Red = more than 5% over budget, amber = slightly over, teal = within budget.")
    vp, burn = M("Story | Forecast Variance %"), M("Story | Burn %")
    obj = table_style()
    obj["values"] += [cf_font(vp, "Story | Variance Colour"), cf_font(var, "Story | Variance Colour"),
                      cf_font(burn, "Story | Burn Colour")]
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"), P(DP("Manager_Value"), "Manager"),
                    P(b_, "Budget"), P(a_, "Actual"), P(f_, "Forecast"), P(var, "Forecast − budget"), P(vp, "Variance %"),
                    P(burn, "Burned"), P(DP("FinancialHealth_Value"), "Financial health")]},
        "Project financial register", obj, sort=[(var, "Descending")]), key="v_fin_table")
    next_chapter(pg, "finance", YNEXT)
    return pg


# ================================================================= 3b PARETO & P&L
def pareto(ttl, cat_field, bar, line, bar_label, colour):
    return chart("lineClusteredColumnComboChart",
        {"Category": [P(cat_field, "Project")], "Y": [P(bar, bar_label)], "Y2": [P(line, "Cumulative %")]},
        ttl,
        {"dataPoint": [measure_fill(bar, colour), measure_fill(line, NAVY)], "legend": legend("Top"),
         "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}],
         "valueAxis": [{"properties": {"secShow": b(True), "secStart": n(0), "secEnd": n(1)}}],
         "categoryAxis": [{"properties": {"fontSize": n(8)}}]},
        sort=[(bar, "Descending")])


def build_finance2():
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (DP("ProjectType_Value"), "Project type"), (DP("Goals_Value"), "Goal")]
    pg = analytic_page("finance2", "FINANCIALS", "WHERE DOES THE MONEY CONCENTRATE — AND WHAT DOES IT RETURN?",
                       "Pareto (80/20) of forecast spend and overruns, then a lifetime P&L per portfolio: revenue + benefits against forecast cost.",
                       slicers, "Story | Pareto PnL Headline")
    section(pg, Y1, 1, "Concentration and return",
            "Few projects carrying most of the money is normal — but those few deserve most of the governance attention.")
    kpi_row(pg, Y1K, [
        ("Finance | Forecast Cost", "Forecast cost"),
        ("Story | Projects For 80% Spend", "Projects = 80% of spend", {"value_colour": ORANGE}),
        ("Story | Concentration %", "Share of projects", {"value_colour": ORANGE}),
        ("Story | Overrun", "Total overrun", {"value_colour": RED}),
        ("Story | Top3 Overrun Share", "Overrun in top 3", {"value_colour": RED}),
        ("Story | Total Value", "Value (revenue + benefits)", {"value_colour": TEAL}),
        ("Story | Net Value", "Net value", {"colour_measure": "Story | Net Colour"}),
        ("Story | Net Margin %", "Net margin", {"colour_measure": "Story | Net Colour"}),
    ])
    section(pg, Y2, 2, "Pareto — which projects carry the spend and the overrun?",
            "Bars ranked largest first; the line is the cumulative share. Where it crosses 80% is your A-list.")
    fc, cum = M("Finance | Forecast Cost"), M("Story | Spend Cum %")
    pg.add(16, Y2V, 1160, H2, pareto("Pareto of forecast cost by project", DP("Name"), fc, cum, "Forecast cost", ORANGE),
           key="v_pareto_spend")
    ov, ocum = M("Story | Overrun"), M("Story | Overrun Cum %")
    pg.add(1192, Y2V, 592, H2, pareto("Pareto of overruns (forecast above budget)", DP("Name"), ov, ocum, "Overrun", RED),
           key="v_pareto_overrun")
    section(pg, Y3, 3, "Which portfolios create net value?",
            "Value promised against forecast cost per portfolio, and how each portfolio adds to — or takes from — total net value.")
    tv, pfc, nv = M("Story | Total Value"), M("Story | Plan Forecast"), M("Story | Net Value")
    rev, ben = M("Story | Plan Revenue"), M("Benefits | Planned Benefits")
    pg.add(16, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")],
         "Y": [P(rev, "Revenue"), P(ben, "Benefits"), P(pfc, "Forecast cost")]},
        "Revenue and benefits versus forecast cost by portfolio",
        {"dataPoint": [measure_fill(rev, NAVY), measure_fill(ben, TEAL), measure_fill(pfc, "#C9CED8")],
         "legend": legend("Top"), "labels": labels_on(False)}, sort=[(pfc, "Descending")]), key="v_pnl_bars")
    pg.add(906, Y3V, 878, H3, chart("waterfallChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Y": [P(nv, "Net value")]},
        "Net-value bridge — each portfolio's contribution to total net value",
        {"sentimentColors": [{"properties": {"increaseFill": col_solid(TEAL), "decreaseFill": col_solid(RED),
                                             "totalFill": col_solid(NAVY)}}],
         "labels": labels_on(True, 0)}, sort=[(nv, "Descending")]), key="v_pnl_bridge")
    section(pg, Y4, 4, "Portfolio P&L statement",
            "Portfolio › programme › project. Lifetime plan figures; Pareto class A = the projects that make up 80% of spend.")
    cls, margin, roi = M("Story | Pareto Class"), M("Story | Net Margin %"), M("Story | Net ROI")
    obj = table_style()
    obj["values"] += [cf_font(nv, "Story | Net Colour"), cf_font(margin, "Story | Net Colour"),
                      cf_font(cls, "Story | Pareto Class Colour")]
    pg.add(16, Y4V, 1768, H4, chart("pivotTable",
        {"Rows": [P(DP("Portfolio Name"), "Portfolio", True), P(DP("Program Name"), "Program", True),
                  P(DP("Name"), "Project", True)],
         "Values": [P(rev, "Revenue"), P(ben, "Benefits"), P(tv, "Total value"), P(M("Story | Plan Budget"), "Budget"),
                    P(pfc, "Forecast cost"), P(nv, "Net value"), P(margin, "Net margin"), P(roi, "ROI"),
                    P(M("Story | Spend Share"), "Share of spend"), P(cls, "Pareto class")]},
        "Portfolio P&L statement", obj, sort=[(nv, "Descending")]), key="v_pnl_matrix")
    next_chapter(pg, "finance2", YNEXT)
    return pg


# ================================================================= 4 RESOURCES
def build_resources():
    slicers = [(DR("Department_Value"), "Department"), (DR("Role_Value"), "Role"),
               (DP("Portfolio Name"), "Portfolio"), (C("DimDate", "Year"), "Year")]
    pg = analytic_page("resources", "RESOURCES", "DO WE HAVE THE PEOPLE?",
                       "Capacity from OnePlan resource calendars against scheduled, committed and forecast demand. Pick a year for a clean monthly view.",
                       slicers, "Story | Resource Headline")
    section(pg, Y1, 1, "Supply and demand in one line", "Utilisation above 100% is overload; below 50% is bench.")
    kpi_row(pg, Y1K, [
        ("Resource KPI | Total Resources", "Active resources"),
        ("Resource | Capacity FTE", "Capacity (FTE)"),
        ("Project | Scheduled FTE", "Scheduled (FTE)"),
        ("Capacity | Resource Utilization%", "Utilisation", {"colour_measure": "Story | Util Colour"}),
        ("Capacity | Over-Allocated Resource Count", "Over-allocated people", {"value_colour": RED}),
        ("Capacity | Available Capacity", "Free capacity (h)", {"value_colour": TEAL}),
        ("Story | Soft Demand %", "Demand still forecast", {"value_colour": AMBER}),
    ])
    section(pg, Y2, 2, "Will supply cover demand over the coming months?",
            "Columns = capacity; lines = scheduled and forecast demand. Lines above the columns are the crunch months.")
    cap, sch, fc = M("Capacity | Resource Capacity"), M("Capacity | Total Hours Scheduled"), M("Capacity | Total Hours Forecast")
    pg.add(16, Y2V, 1160, H2, chart("lineClusteredColumnComboChart",
        {"Category": [P(MONTH, "Month")], "Y": [P(cap, "Capacity (h)")], "Y2": [P(sch, "Scheduled (h)"), P(fc, "Forecast (h)")]},
        "Capacity versus demand per month",
        {"dataPoint": [measure_fill(cap, "#D9DDE3"), measure_fill(sch, NAVY), measure_fill(fc, ORANGE)],
         "legend": legend("Top"), "lineStyles": [{"properties": {"strokeWidth": n(3), "showMarker": b(True)}}]},
        sort=[(MONTH, "Ascending")]), key="v_supply")
    util = M("Capacity | Resource Utilization%")
    pg.add(1192, Y2V, 592, H2, chart("clusteredBarChart",
        {"Category": [P(DR("Role_Value"), "Role")], "Y": [P(util, "Utilisation")]},
        "Utilisation by role",
        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Util Colour")},
                        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
         "labels": labels_on(True)}, sort=[(util, "Descending")]), key="v_role")
    section(pg, Y3, 3, "Who is over- or under-loaded, month by month?",
            "Scheduled hours ÷ capacity per person and month.")
    legend_note(pg, 1084, Y3 + 4, 700, [("Over 100%", "#8E1B12"), ("80–100%", TEAL), ("50–80%", "#9A6B00"),
                                        ("Under 50%", MUTED)], "heat_legend")
    obj = table_style(9)
    obj["values"] += [cf_back(util, "Story | Util Cell Colour")]
    pg.add(16, Y3V, 1768, H3, chart("pivotTable",
        {"Rows": [P(DR("Role_Value"), "Role", True), P(DR("Name"), "Resource", True)],
         "Columns": [P(MONTH, "Month", True)], "Values": [P(util, "Util.")]},
        "Utilisation heat map — role › resource × month", obj), key="v_heat")
    section(pg, Y4, 4, "Where does demand come from, and who can take more?",
            "Demand by project and plan type (Committed / Scheduled / Forecast / Timesheets), and the bench list.")
    ctype = C("FactResourcePlan", "CostType")
    dem = M("Capacity | Demand")
    pg.add(16, Y4V, 878, H4, chart("barChart",
        {"Category": [P(DP("Name"), "Project")], "Series": [P(ctype, "Plan type")], "Y": [P(dem, "Hours")]},
        "Demand hours by project and resource-plan type",
        {"dataPoint": series_colours(ctype, {"Committed": NAVY, "Scheduled": TEAL, "Forecast": ORANGE, "Timesheets": GREY}),
         "legend": legend("Top")}, sort=[(dem, "Descending")]), key="v_demand")
    obj = table_style()
    obj["values"] += [cf_font(util, "Story | Util Colour")]
    pg.add(906, Y4V, 878, H4, chart("tableEx",
        {"Values": [P(DR("Name"), "Resource"), P(DR("Role_Value"), "Role"), P(DR("Department_Value"), "Department"),
                    P(cap, "Capacity h"), P(sch, "Scheduled h"), P(util, "Utilisation"),
                    P(M("Capacity | Available Capacity"), "Free h")]},
        "Bench and overload list — lowest utilisation first", obj, sort=[(util, "Ascending")]), key="v_bench",
        filters=[f_cmp("DimResource", "Generic", 0, False)])
    next_chapter(pg, "resources", YNEXT)
    return pg


# ================================================================= 5 SCHEDULE
def build_schedule():
    pg = analytic_page("schedule", "SCHEDULE", "WILL WE DELIVER ON TIME?",
                       "Schedule health reported by project managers, checked against baselines, milestones and late work in the OnePlan work plans.",
                       STD_SLICERS, "Story | Schedule Headline")
    section(pg, Y1, 1, "Delivery confidence", "Reported health first, then what the plan data says.")
    kpi_row(pg, Y1K, [
        ("Portfolio 360 | On-Time Delivery %", "On schedule"),
        ("Portfolio 360 | At-Risk Count", "Projects at risk", {"value_colour": AMBER}),
        ("Portfolio 360 | Slipping Count", "Projects slipping", {"value_colour": RED}),
        ("Story | Project Slip (days)", "Avg finish slip (days)", {"value_colour": AMBER}),
        ("Task | Overdue Tasks", "Overdue tasks", {"value_colour": RED}),
        ("Story | Slipped Tasks", "Tasks past baseline", {"value_colour": AMBER}),
        ("Story | Milestones Next 30d", "Milestones next 30 days"),
    ])
    section(pg, Y2, 2, "Which programmes are slipping, and where are projects in the lifecycle?",
            "Schedule health per programme and the gate each project has reached.")
    sh = DP("ScheduleHealth_Value")
    pg.add(16, Y2V, 878, H2, chart("barChart",
        {"Category": [P(DP("Program Name"), "Program")], "Series": [P(sh, "Schedule health")],
         "Y": [P(M("Project | Plans Count"), "Projects")]},
        "Schedule health by programme",
        {"dataPoint": series_colours(sh, HEALTH_COLOURS), "legend": legend("Top")}), key="v_sched_prog")
    pg.add(906, Y2V, 878, H2, chart("funnel",
        {"Category": [P(DP("ProcessStep"), "Lifecycle step")], "Y": [P(M("Project | Plans Count"), "Projects")]},
        "Projects per lifecycle step",
        {"dataPoint": [{"properties": {"fill": col_solid(NAVY)}}], "labels": labels_on(True)}), key="v_funnel")
    section(pg, Y3, 3, "Which finish dates moved, and what is coming up?",
            "Slip = current finish minus baseline finish. Milestones overdue are red, due within 14 days amber.")
    slip = M("Story | Project Slip (days)")
    pg.add(16, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(slip, "Slip (days)")]},
        "Finish-date slip versus baseline, by project (days)",
        {"dataPoint": [{"properties": {"fill": col_solid(ORANGE)}}], "labels": labels_on(True)},
        sort=[(slip, "Descending")]), key="v_slip")
    obj = table_style()
    obj["values"] += [cf_font(DT("EndDate"), "Story | Due Colour")]
    pg.add(906, Y3V, 878, H3, chart("tableEx",
        {"Values": [P(DT("EndDate"), "Due"), P(DP("Name"), "Project"), P(DT("Name"), "Milestone"),
                    P(DT("PercentDone"), "% done"), P(DT("Status"), "Status")]},
        "Open milestones — soonest first", obj, sort=[(DT("EndDate"), "Ascending")]), key="v_miles",
        filters=[f_in("DimTask", "Milestone", [True]), f_cmp("DimTask", "PercentDone", 3, 100)])
    section(pg, Y4, 4, "Late-work register", "Open tasks that finish after their baseline — longest slip first.")
    tslip = M("Story | Task Slip (days)")
    obj = table_style()
    obj["values"] += [cf_font(tslip, "Story | Slip Colour"), cf_font(DT("EndDate"), "Story | Due Colour")]
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DT("Name"), "Task"), P(DT("AssignedResources"), "Assigned to"),
                    P(DT("BaselineEndDate"), "Baseline finish"), P(DT("EndDate"), "Finish"), P(tslip, "Slip (days)"),
                    P(DT("PercentDone"), "% done"), P(DT("TaskStatus"), "Task status")]},
        "Late-work register", obj, sort=[(tslip, "Descending")]), key="v_late",
        filters=[f_in("DimTask", "WorkType", ["Tasks"]), f_in("DimTask", "Status", ["Completed"], exclude=True),
                 f_not_blank("DimTask", "BaselineEndDate")])
    next_chapter(pg, "schedule", YNEXT)
    return pg


# ================================================================= 6 RISK
def build_risk():
    pg = analytic_page("risk", "RISK", "WHAT COULD GO WRONG?",
                       "Risks and issues logged on the OnePlan work plans: how likely, how bad, where the exposure sits, and what to escalate.",
                       STD_SLICERS, "Story | Risk Headline")
    section(pg, Y1, 1, "Risk position", "Exposure is the money at stake on active risks.")
    kpi_row(pg, Y1K, [
        ("Story | Active Risk Count", "Active risks"),
        ("Story | Critical High Risks", "Critical / high", {"value_colour": RED}),
        ("Story | Risk Exposure", "Exposure", {"value_colour": ORANGE}),
        ("Story | Avg Risk Probability", "Avg probability"),
        ("Story | Unmitigated Risk %", "Not yet mitigated", {"value_colour": AMBER}),
        ("Project | Active Issues", "Open issues", {"value_colour": RED}),
        ("Project | Active Changes", "Open changes"),
    ])
    risk_filter = [f_in("DimTask", "WorkType", ["Risks"]), f_in("DimTask", "State", ["Active"])]
    section(pg, Y2, 2, "How likely, how bad?", "Heat map of active risks; top-left is where escalation starts.")
    rc = M("Story | Active Risk Count")
    obj = table_style(11)
    obj["values"] += [cf_back(rc, "Story | Heat Colour")]
    pg.add(16, Y2V, 700, H2, chart("pivotTable",
        {"Rows": [P(DT("Impact"), "Impact", True)], "Columns": [P(DT("Probability Category"), "Probability", True)],
         "Values": [P(rc, "Risks")]},
        "Risk heat map — impact × probability", obj, sort=[(DT("Impact"), "Ascending")]), key="v_heatmap",
        filters=risk_filter)
    pg.add(728, Y2V, 520, H2, chart("clusteredBarChart",
        {"Category": [P(DT("RiskStage"), "Stage")], "Y": [P(rc, "Risks")]},
        "Where risks are in the response cycle",
        {"dataPoint": [{"properties": {"fill": col_solid(NAVY)}}], "labels": labels_on(True)}), key="v_stage",
        filters=risk_filter)
    exp = M("Story | Risk Exposure")
    pg.add(1260, Y2V, 524, H2, chart("clusteredBarChart",
        {"Category": [P(DP("Program Name"), "Program")], "Y": [P(exp, "Exposure")]},
        "Exposure by programme",
        {"dataPoint": [{"properties": {"fill": col_solid(ORANGE)}}], "labels": labels_on(True, 0)},
        sort=[(exp, "Descending")]), key="v_exp_prog")
    section(pg, Y3, 3, "Where is exposure concentrated?",
            "Big tiles = where a single bad outcome hurts most. Issues are risks that already happened.")
    pg.add(16, Y3V, 878, H3, chart("treemap",
        {"Group": [P(DP("Program Name"), "Program")], "Details": [P(DP("Name"), "Project")], "Values": [P(exp, "Exposure")]},
        "Exposure by programme › project", {"legend": legend("Top", False)}), key="v_treemap")
    iss = M("Project | Active Issues")
    pg.add(906, Y3V, 878, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(iss, "Open issues"), P(M("Project | Active Risks"), "Active risks")]},
        "Open issues and risks per project",
        {"dataPoint": [measure_fill(iss, RED), measure_fill(M("Project | Active Risks"), "#C9CED8")],
         "legend": legend("Top")}, sort=[(iss, "Descending")]), key="v_issues")
    section(pg, Y4, 4, "Top-risk register", "Highest exposure first — check every critical or high risk has an owner and a mitigation.")
    obj = table_style()
    obj["values"] += [cf_font(DT("Impact"), "Story | Impact Colour")]
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DT("Name"), "Risk"), P(DT("Impact"), "Impact"),
                    P(DT("Probability Category"), "Probability"), P(exp, "Exposure"), P(DT("RiskStage"), "Stage"),
                    P(DT("AssignedResources"), "Owner"), P(DT("Mitigation"), "Mitigation"), P(DT("EndDate"), "Due")]},
        "Top-risk register", obj, sort=[(exp, "Descending")]), key="v_risk_table", filters=risk_filter)
    next_chapter(pg, "risk", YNEXT)
    return pg


# ================================================================= 7 BENEFITS
def build_benefits():
    pg = analytic_page("benefits", "VALUE", "WILL IT PAY OFF?",
                       "Expected benefits recorded on each plan against its budget; realisation estimated pro-rata on % complete.",
                       STD_SLICERS, "Story | Benefits Headline")
    section(pg, Y1, 1, "The value case", "A ratio below 1.0 means the plan costs more than it promises back.")
    kpi_row(pg, Y1K, [
        ("Benefits | Planned Benefits", "Planned benefits"),
        ("Benefits | Realized Benefits", "Realised so far"),
        ("Benefits | Realization Rate (%)", "Realisation rate"),
        ("Story | Plan Budget", "Plan budget"),
        ("Story | Benefit Cost Ratio", "Benefit ÷ cost", {"colour_measure": "Story | Ratio Colour"}),
        ("Project | Total CostofDelay", "Cost of delay", {"value_colour": RED}),
    ])
    section(pg, Y2, 2, "Which portfolios and goals create the value?", "Benefits next to budget per portfolio, and the goal mix.")
    pb, bud = M("Benefits | Planned Benefits"), M("Story | Plan Budget")
    pg.add(16, Y2V, 1160, H2, chart("clusteredBarChart",
        {"Category": [P(DP("Portfolio Name"), "Portfolio")], "Y": [P(pb, "Planned benefits"), P(bud, "Plan budget")]},
        "Planned benefits versus plan budget by portfolio",
        {"dataPoint": [measure_fill(pb, TEAL), measure_fill(bud, "#C9CED8")], "legend": legend("Top")},
        sort=[(pb, "Descending")]), key="v_ben_port")
    pg.add(1192, Y2V, 592, H2, chart("donutChart",
        {"Category": [P(DP("Goals_Value"), "Goal")], "Y": [P(pb, "Planned benefits")]}, "Benefits by strategic goal",
        {"legend": legend("Bottom"), "labels": [{"properties": {"show": b(True), "labelStyle": s("Percent of total")}}]}),
        key="v_ben_goal")
    section(pg, Y3, 3, "Value for money per project", "Above the diagonal = benefits exceed cost. Colour = strategic alignment.")
    align = DP("StrategicAlignment_Value")
    pg.add(16, Y3V, 1160, H3, chart("scatterChart",
        {"Category": [P(DP("Name"), "Project")], "Series": [P(align, "Alignment")],
         "X": [P(bud, "Plan budget")], "Y": [P(pb, "Planned benefits")],
         "Size": [P(M("Benefits | Realized Benefits"), "Realised")]},
        "Benefits versus budget — bubble size = realised benefits",
        {"dataPoint": series_colours(align, {"Extreme": NAVY, "Strong": TEAL, "Moderate": "#7FB7B7", "Low": AMBER,
                                             "Not Rated": "#C9CED8"}),
         "legend": legend("Top"), "categoryLabels": [{"properties": {"show": b(True), "fontSize": n(8)}}]}),
        key="v_ben_scatter")
    ratio = M("Story | Benefit Cost Ratio")
    pg.add(1192, Y3V, 592, H3, chart("clusteredBarChart",
        {"Category": [P(DP("Name"), "Project")], "Y": [P(ratio, "Benefit ÷ cost")]},
        "Best value for money (benefit ÷ cost)",
        {"dataPoint": [{"properties": {"fill": measure_colour("Story | Ratio Colour")},
                        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
         "labels": labels_on(True)}, sort=[(ratio, "Descending")]), key="v_ratio")
    section(pg, Y4, 4, "Benefits register", "Funded projects with no benefit recorded are the first gap to close.")
    obj = table_style()
    obj["values"] += [cf_font(ratio, "Story | Ratio Colour")]
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Portfolio Name"), "Portfolio"), P(DP("Goals_Value"), "Goal"),
                    P(align, "Alignment"), P(bud, "Plan budget"), P(pb, "Planned benefits"), P(ratio, "Benefit ÷ cost"),
                    P(DP("Summary_PercentDone"), "% done"), P(M("Benefits | Realized Benefits"), "Realised")]},
        "Benefits register", obj, sort=[(pb, "Descending")]), key="v_ben_table")
    next_chapter(pg, "benefits", YNEXT)
    return pg


# ================================================================= 8 GOVERNANCE
def build_governance():
    slicers = [(DP("Portfolio Name"), "Portfolio"), (DP("Program Name"), "Program"),
               (C("DimInsightRule", "RuleArea"), "Rule area"), (C("DimInsightRule", "Severity"), "Severity")]
    pg = analytic_page("governance", "GOVERNANCE", "CAN WE TRUST THE DATA?",
                       "OnePlan Plan Insights checks every plan against governance rules. If the data is not clean, every other chapter is less reliable.",
                       slicers, "PMO | Governance Headline")
    section(pg, Y1, 1, "Data health score", "Severity-weighted share of insight checks that pass.")
    kpi_row(pg, Y1K, [
        ("PMO | Governance Score", "Governance score", {"colour_measure": "PMO | Governance RAG Colour"}),
        ("PMO | Compliance %", "Compliance"),
        ("PMO | Plans Assessed", "Plans assessed"),
        ("PMO | Plans Failing", "Plans failing", {"value_colour": RED}),
        ("PMO | Problems", "Problems", {"value_colour": RED}),
        ("PMO | Warnings", "Warnings", {"value_colour": AMBER}),
        ("PMO | Insight Coverage %", "Insight coverage"),
    ])
    section(pg, Y2, 2, "Which rules fail most?", "Fix the rule that fails on most plans first — it moves the score fastest.")
    pf = M("PMO | Plans Failing")
    pg.add(16, Y2V, 1060, H2, chart("clusteredBarChart",
        {"Category": [P(C("DimInsightRule", "RuleName"), "Rule")], "Y": [P(pf, "Plans failing")]},
        "Plans failing per insight rule",
        {"dataPoint": [{"properties": {"fill": col_solid(ORANGE)}}], "labels": labels_on(True)},
        sort=[(pf, "Descending")]), key="v_rules")
    pg.add(1092, Y2V, 692, H2, chart("pivotTable",
        {"Rows": [P(C("DimInsightRule", "RuleArea"), "Area", True)],
         "Columns": [P(C("DimInsightRule", "Severity"), "Severity", True)], "Values": [P(pf, "Plans failing")]},
        "Failing plans by rule area and severity", table_style()), key="v_area")
    section(pg, Y3, 3, "Hygiene gaps", "Plans missing the basics that the other chapters rely on.")
    hyg = [("PMO | Plans Without Financial Plan", "No financial plan"),
           ("PMO | Plans Without Resource Plan", "No resource plan"),
           ("PMO | Plans Without Work Plan", "No work plan"),
           ("PMO | Plans Not Up To Date", "Not up to date"),
           ("PMO | Plans Reported Off Track", "Reported off track"),
           ("PMO | Plans With Unassigned Tasks", "Unassigned tasks"),
           ("PMO | Plans Over Risk Threshold", "Over risk threshold"),
           ("PMO | Plans With Unsubmitted Timesheets", "Unsubmitted timesheets")]
    w = (1768 - 7 * 10) / 8
    for k, (m, label) in enumerate(hyg):
        pg.add(round(16 + k * (w + 10), 2), Y3V, round(w, 2), 110, card(m, label, value_colour=NAVY, size=26),
               key=f"hyg{k}")
    pg.add(16, Y3V + 126, 1768, H3 - 126, chart("tableEx",
        {"Values": [P(C("DimInsightRule", "RuleName"), "Rule"), P(C("DimInsightRule", "RuleArea"), "Area"),
                    P(C("DimInsightRule", "Severity"), "Severity"), P(pf, "Plans failing"),
                    P(C("DimInsightRule", "RecommendedAction"), "Recommended action")]},
        "What to do about each failing rule", table_style(), sort=[(pf, "Descending")]), key="v_actions")
    section(pg, Y4, 4, "Plan-by-plan action list", "Lowest governance score first; send each manager their next action.")
    obj = table_style()
    pg.add(16, Y4V, 1768, H4, chart("tableEx",
        {"Values": [P(DP("Name"), "Project"), P(DP("Manager_Value"), "Manager"), P(M("PMO | Governance Score"), "Score"),
                    P(M("PMO | Problems"), "Problems"), P(M("PMO | Warnings"), "Warnings"),
                    P(M("PMO | Failed Checks"), "Failed checks"), P(M("PMO | Next Action"), "Next action")]},
        "Plan-by-plan action list", obj, sort=[(M("PMO | Governance Score"), "Ascending")]), key="v_plans")
    next_chapter(pg, "governance", YNEXT)
    return pg


def build_all():
    return [build_home(), build_exec(), build_portfolio(), build_finance(), build_finance2(), build_resources(), build_schedule(),
            build_risk(), build_benefits(), build_governance()]
