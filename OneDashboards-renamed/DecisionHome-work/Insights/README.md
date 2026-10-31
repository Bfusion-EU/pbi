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
4. **② Trend / composition**: where things are heading.
5. **③ Drivers**: why the numbers are what they are.
6. **④ The list to act on**: a register sorted so the first row is the first thing to do.
7. **Next chapter ›**: a button to the next page in the story, plus a link back to the command center.

| # | Page | Question | Audience |
|---|---|---|---|
| – | Home: Command center | What needs attention, then go there | everyone |
| 1 | Executive Summary | Are we on course? | Executive board, monthly |
| 2 | Portfolio | Are we investing in the right things? | Portfolio board, quarterly |
| 2b | Pipeline, Gates & Dependencies | Where is the pipeline stuck, and who waits on whom? | PMO, portfolio board |
| 2c | Scenario Comparison | If we fund scenario A instead of B, what do we gain? | Portfolio board |
| 2d | Project One-Pager | Everything about one project before I decide (pick it in the Project slicer) | Sponsors, PMO |
| 3 | Financials | Are we spending as planned (at completion)? | Finance & PMO, monthly close |
| 3b | Pareto & Portfolio P&L | Where does the money concentrate, and what does it return? | Finance & portfolio board |
| 4 | Resource Management | Do we have the people? | Resource managers, monthly |
| 4b | Timesheets vs Plan | Is the work happening as planned, and is the time in? | Resource managers, PMO |
| 4c | Timesheet Status | Are the timesheets in, and who is waiting on whom? | Timesheet managers, weekly |
| 4d | Resource Detail | Everything about one person: load, work, time in | Resource managers |
| 5 | Planning & Scheduling | Will we deliver on time? | Delivery leads, weekly |
| 5b | Gantt View (matrix) | What runs when, and what is late? | Delivery leads, PMO |
| 5c | Status-Report Trend | Which projects got worse since their last report? | PMO, delivery leads |
| 5d | Plan vs Baseline | Is the plan still the plan we approved? (cost, days, hours, FTE) | PMO, sponsors, delivery leads |
| 6 | Risk Management | What could go wrong? | Risk owners, fortnightly |
| 7 | Benefits & Value | Will it pay off? | Sponsors, quarterly |
| 8 | Governance & Data Trust | Can we trust the data? | PMO, weekly |

Hidden pages: **Resource Detail (drill-through)** (right-click any resource), **Project One-Pager (drill-through)** (right-click any project → *Drill through*, with an *Open in OnePlan* button; page 2d is the same page with a Project slicer)
and two hover cards (project, resource) that appear on charts and tables grouped by project or resource.

The page design takes ideas from OnePlan's own personas and questions ("Are we funding the right things?",
"What is our investment delivering?", "Can we execute what we've planned?") and from its modules:
Strategic/Portfolio planning, Financial plans, Resource plans, Work plans, Plan Insights, Lifecycle.
`my.oneplan.ai` requires a sign-in, so the tenant UI itself was not analysed.

## Home — command center

The Home page is a command center for two audiences, switched by the PMO / Executive buttons (bookmarks,
display only — slicers stay):

- **Icon rail** (left, always visible): one icon per chapter; hover for the chapter and its follow-on pages.
- **Pulse**: weekly briefing sentence, EAC vs budget and On track with 6-month sparklines and a change chip
  (vs the previous status-report month), active projects, utilisation, critical risks, data trust.
- **PMO view**: *Act now* (active projects ranked by their worst reason: off track > EAC +5% > 10 d late vs
  baseline > 10 overdue tasks > no report 30 d > failing rules; open the One-Pager from a selected row),
  *Next 30 days* milestones, and eight *area health* tiles with links to every follow-on page.
- **Executive view**: the three decisions (money, people, risk) and the board's four questions answered.
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
