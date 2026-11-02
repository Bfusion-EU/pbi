# OneDashboards – Insights (native story pack)

A second dashboard pack next to `OneDashboards - Bfusion.pbip`. It has the same branding (BFusion footer band,
navy/orange palette, DIN titles, OnePlan logo) and the same live connection to **OneModel360Star**. It uses
**only native Power BI visuals**: no BFusion custom visuals, no AppSource visuals.

Open `OneDashboards - Insights.pbip` in Power BI Desktop. It connects to the published model in the
`OneModel` workspace, just like the Bfusion pack.

## The story

Every chapter answers **one question** and reads from top to bottom:

1. **Header**: `AREA | QUESTION?` with slicers on the right. Portfolio, Program and State slicers are synced across pages.
   A Year slicer appears only where it really filters the page (money and people); project-based pages use State instead.
2. **Orange headline**: one sentence that a DAX measure writes from the data in the current filter.
   It gives the answer before the charts do.
3. **① The pulse**: KPI cards. Teal is fine, amber needs a look, red needs a decision.
4. **② The list to act on**: a register sorted so the first row is the first thing to do (it sits right under the pulse, visible without scrolling).
5. **③ Trend / composition**: where things are heading.
6. **④ Drivers**: why the numbers are what they are.
7. **Next chapter ›**: a button to the next page in the story, plus a link back to the command center.

Story grammar: headline → ① pulse → ② list to act on → ③ trend → ④ drivers. Pages that keep their own order:
Executive (④ is navigation), 2b (its list is ③), 4c (④ is the workflow audit trail) and 5c (the ledger is already ②).
The custom layouts 2d, 4d, 5b and 5d are skipped (the build prints "act_first skipped ...").

**Navigation.** The tab bar shows 9 tabs: Home and chapters 1-8. The 10 deep-dives (2b, 2c, 2d, 3b, 4b, 4c, 4d, 5b, 5c, 5d)
are hidden from the tab bar and reached through the chapter strip, the breadcrumb, the Home rail and card footers, the
Executive chapter row, "Next chapter" and drill-through. Every story page has a breadcrumb under the header
(Home › chapter › page); chapters 2-5 also carry a chapter strip on the right with the current page in orange.
On Executive, ④ is one row of 7 chapter buttons.

| # | Page | Question | Audience |
|---|---|---|---|
| – | Home: Command center | What needs attention, then go there | everyone |
| 1 | Executive Summary | Are we on course? | Executive board, monthly |
| 2 | Portfolio | Are we investing in the right things? | Portfolio board, quarterly |
| 2b | Pipeline, Gates & Dependencies (hidden tab: reach via the chapter strip) | Where is the pipeline stuck, and who waits on whom? | PMO, portfolio board |
| 2c | Scenario Comparison (hidden tab: reach via the chapter strip) | If we fund scenario A instead of B, what do we gain? | Portfolio board |
| 2d | Project One-Pager (hidden tab: reach via the chapter strip) | Everything about one project before I decide (pick it in the Project slicer) | Sponsors, PMO |
| 3 | Financials | Are we spending as planned (at completion)? | Finance & PMO, monthly close |
| 3b | Pareto & Portfolio P&L (hidden tab: reach via the chapter strip) | Where does the money concentrate, and what does it return? | Finance & portfolio board |
| 4 | Resource Management | Do we have the people? | Resource managers, monthly |
| 4b | Timesheets vs Plan (hidden tab: reach via the chapter strip) | Is the work happening as planned, and is the time in? | Resource managers, PMO |
| 4c | Timesheet Status (hidden tab: reach via the chapter strip) | Are the timesheets in, and who is waiting on whom? | Timesheet managers, weekly |
| 4d | Resource Detail (hidden tab: reach via the chapter strip) | Everything about one person: load, work, time in | Resource managers |
| 5 | Planning & Scheduling | Will we deliver on time? | Delivery leads, weekly |
| 5b | Gantt View (matrix) (hidden tab: reach via the chapter strip) | What runs when, and what is late? | Delivery leads, PMO |
| 5c | What Changed (hidden tab: reach via the chapter strip) | What changed since last month — who got worse, which dates and money moved? | PMO, delivery leads, board |
| 5d | Plan vs Baseline (hidden tab: reach via the chapter strip) | Is the plan still the plan we approved? (cost, days, hours, FTE) | PMO, sponsors, delivery leads |
| 6 | Risk Management | What could go wrong? | Risk owners, fortnightly |
| 7 | Benefits & Value | Will it pay off? | Sponsors, quarterly |
| 8 | Governance & Data Trust | Can we trust the data? | PMO, weekly |

Hidden pages: **Resource Detail (drill-through)** (right-click any resource), **Project One-Pager (drill-through)** (right-click any project → *Drill through*, with an *Open in OnePlan* button; page 2d has the same content with a Project slicer, 36 px lower because of the navigation row)
and two hover cards (project, resource) that appear on charts and tables grouped by project or resource.

The page design takes ideas from OnePlan's own personas and questions ("Are we funding the right things?",
"What is our investment delivering?", "Can we execute what we've planned?") and from its modules:
Strategic/Portfolio planning, Financial plans, Resource plans, Work plans, Plan Insights, Lifecycle.
`my.oneplan.ai` requires a sign-in, so the tenant UI itself was not analysed.

## Home — command center

One card per subject area, all built the same way (status pill, number, trend or bar, one sentence, links):
Financials, Schedule, Resources, Risk, Portfolio, Benefits, Status reports, Governance.

- **Briefing strip**: how many active projects need a decision, and why (counts per reason; they add up).
- **Right column**, switched by the PMO / Executive buttons (display-only bookmarks — slicers stay):
  PMO = *Act now* (active projects ranked by worst reason: off track > EAC +5% > 10 d late vs baseline >
  may slip (2 of 4 signals or > 10 overdue tasks) > no report 30 d > failing rules; the list scrolls; open the One-Pager from a selected row) and *Next 30 days*;
  Executive = the three decisions (money, people, risk).
- Trend lines and "vs last month" chips come from status-report history (each active project's latest report
  as of month end, last 6 months).
- Icon rail on the left to every chapter; card footers link to every follow-on page.
- Portfolio and Program slicers on Home are synced with every chapter.
- Measures: report-level, folder `Story\Home` (`ext_home.py`).
## Storytelling measures

The headlines, action prompts and colour rules are **report-level measures** (`reportExtensions.json`,
display folder `Story`), so the published model needs **no change**. They build only on model measures
and columns that the existing pack already uses. Examples:

- `Story | Finance Headline`: budget, actuals, burn, forecast against budget, and the largest overrun.
- `Story | Resource Headline`: capacity, utilisation, people over-allocated, the most stretched role, and how much demand is still soft.
- `Story | Exec Action Money / People / Risk`: the three decisions on the Executive page.
- `Story | * Colour`: hex colours used for conditional formatting (variance, utilisation, heat map, due dates).

## Definitions agreed with the PMO (2026-10-26)

- **Utilisation** = scheduled hours ÷ capacity, organisation-wide (project slicers don't apply, because capacity has
  no project). Over-allocated = above 100% in any month in view.
- **Financial variance** is measured at completion: EAC − budget (FactCost, all dates). Budget to date versus actuals is
  shown next to it.
- **Benefits** must be real actuals. They come from FactCost CostType `"Actual Benefits"` (one constant,
  `ACTUAL_BENEFITS_COST_TYPE` in `story_measures.py`). This tenant doesn't record them yet, so the pack shows planned
  benefits and benefits due to date, and says realisation cannot be measured.
- **Counts** (risks, issues, tasks, milestones, insights) include project plans only.
- **Priority** = `DimProject[PrioritizationScore]`.
- No row-level security.

Added 2026-11-02 (one definition per number):

- **Data-trust notes** (`_generator/trust.py`). When less than 95% of the active projects have the data a headline
  rests on, the headline ends with a note such as "ⓘ Based on N of M active projects with a financial plan (P%)":
  - **3 and 3b:** a budget or an EAC.
  - **4:** scheduled hours.
  - **5:** at least one work-plan task.
  - **7:** planned benefits, out of the projects with an EAC.

  The Executive headline always ends with the governance data-trust score. Some headlines are left alone:
  - 4b, 5c, 5d and Portfolio already state their own coverage.
  - Risk has no honest test, because a project can genuinely have no risks.

- **Finish slip vs baseline** has one definition, `Story | Baseline · Finish Slip (days)` (page 5d). Page 5 and the Home
  Schedule card count **active** projects late against their current baseline. They say how many active projects
  have a baseline, and the headline warns when fewer than half do.
- **Value ratio** = (planned benefits + forecasted revenue) ÷ EAC, at completion (`Story | Value Ratio`). It is used on
  Home, page 7 and the 3b P&L, and Net ROI = value ratio − 1. The scenario page's "Benefits per €" is a different
  figure: it comes from the Modeler scenario.
- **On track %** leaves out active projects with no health rating, and the headlines say how many those are ("n not rated").
- **Plan accuracy (4b)** counts only projects that have both scheduled hours to date and approved hours. The headline
  gives that overlap, and says "not comparable" when it is below 30%. The month line shows all booked hours ÷ all
  scheduled hours.
- **EAC vs budget** on Financials, Executive and Act now comes from the financial plan (FactCost). Portfolio uses the plan
  fields and labels them that way. The Home Financials trend line comes from status reports, and its caption says so.
- **Executive focus "resource overload"** triggers when at least 10% of active people are above 100% in a month in view.
- **May slip:** an active project with at least 2 of: behind pace by more than 15 pt (time elapsed % − % complete);
  an open milestone due within 30 d and under 50% done; late tasks rising since the previous report; finish 7+ d
  later than last month. It also fires on more than 10 overdue tasks. Missing data never makes a signal true.
- **What changed (5c):** each project's latest report as of this month end is compared with the one as of last
  month end. The Report period slicer picks the month; the default is the latest. "Moved" means a finish date
  shift of 7+ d, or a forecast shift of at least 2% or €10K. Snapshots use each project's latest status report regardless of its workflow state (draft or submitted), as on the rest of 5c.

## Data notes (from the model audit)

- The report-level filters are copied from the Bfusion pack: `FactCost[DetailRow] = false` and the "Template"
  exclusions on project, program and portfolio.
- Capacity sits on the 1st of each month, so every time axis uses `DimDate[MonthStart]`. The utilisation heat map
  shows a rolling 12 months.
- DimDate filters only fact tables, never DimProject or DimTask. That is why project-based pages have no Year slicer.
- The resource plan has only the Scheduled, Committed and Timesheets types (no Forecast).
- Risk "Exposure" is a score (probability × impact weight), not money.
- The Portfolio page uses the plan fields (`DimProject[Budget]`, `[Forecast]`), and they are labelled as such.
  Financials and the 3b P&L use the time-phased financial plan (`FactCost`) at completion.
- Project-level visuals use `DimProject[Portfolio Name]` and `[Program Name]`. DimPortfolio and DimProgram do not
  filter DimProject or DimTask.
- Data gaps in this tenant that make pages look sparse: timesheets and scheduled hours sit on different plans
  (page 4b); there are no actual benefits (page 7); and gate approvals and plan dependencies may be empty (page 2b,
  which shows a note when they are).

## Checking the DAX against the real model

Open `SemanticModel/OneModel360Star.pbix` in Power BI Desktop, then run `python dax_check.py` in `_generator`.
It evaluates every report measure, including the measures it depends on, as a total and grouped by project, resource
and month, and lists any errors. Use `--only <text>` to check a subset and `--show <text>` to print values.

## Theme, colours and KPI tiles

- The build writes a custom report theme, `BFusionInsightsTheme.json`, from the palette in `pbir.py`. It sets the
  colours and text classes, and hides the hover header on shapes, text boxes, images and buttons.
- **Fill colours and text colours are kept apart.** Amber `#D9A832` and grey `#9AA3AF` are used only for fills (bars,
  cells, swatches). Text uses `AMBER_TEXT #9A6B00` and `GREY_TEXT #6B7280`, which reach at least 4.5:1 contrast on
  white. The `Story | * Colour` measures return text colours. For bars that need the same rule, use the
  `Story | * Fill` twins.
- **KPI tiles** are 90 px high. Numbers use `KPI_VALUE_PT` (24) and text values use `KPI_TEXT_PT` (20).

## Rebuilding

The pack is generated. Change the Python and rebuild rather than editing JSON by hand:

```bash
cd "_generator"
python build.py --check
```

`--check` validates every file against the Microsoft PBIR JSON schemas. It also checks that every column,
measure and DAX reference exists in `SemanticModel/ModeL360Star.bim`, and that no visual sits on the footer band.
Extension pages live in `_generator/ext_*.py`, each registering its own `Story | <Area> · …` measures and
listed in `extensions.py`. Set `INSIGHTS_OUT` to build into another folder when only validating.
Layout passes (`layout.py`) run in `pages.build_all` in this order: filters, tooltips, layout (act-first, navigation row,
hidden deep-dives), a11y. Positions are regenerated on every build. After act_first the internal keys `sec2`/`sec3`/`sec4`
no longer match the visible numbers (`sec4` holds ②).
Formatting you change in Desktop is lost on the next rebuild, so move it into `_generator/pages.py`.

## Plan vs Baseline (5d)

- **Which baseline.** The model holds one baseline per plan (`DimProject[Summary_Baseline*]`, the current one). Every status
  report also stores the baseline in force when it was written (`FactStatusReport[Summary_Baseline*]`), keyed by
  `Summary_LastBaselineDate`. Each distinct date of a project is one saved baseline. The *Baselines in force on* slicer picks a moment: each project is compared with the baseline it had then (its latest baseline saved on or before that date);
  left empty, each project is compared with its current baseline.
- **Units.** Start/finish shift in calendar days; duration in OnePlan working days; average FTE = hours ÷ (duration × `Resource | FTE Hours per Day`).
  Cost, hours and FTE totals are like-for-like: only projects whose baseline holds that number.
- **Smart signal per project:** Scope growth (later and more hours), Stretched (later, same work: FTE down),
  Compressed (more hours, same finish: FTE up), Ahead, Cost up, On baseline, No baseline — each with a next step.
  Baselines older than 90 days that no longer match the plan are flagged.
- **Tasks** compare with the current baseline only: OnePlan keeps task baselines for the latest baseline.
- Measures: report-level, folder `Story\Baseline` (`ext_baseline.py`). No model change.
