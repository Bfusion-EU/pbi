# OneDashboards – Insights (native story pack)

A second dashboard pack next to `OneDashboards - Bfusion.pbip`. It has the same branding (BFusion footer band,
navy/orange palette, DIN titles, OnePlan logo) and the same live connection to **OneModel360Star**. It uses
**only native Power BI visuals**: no BFusion custom visuals, no AppSource visuals.

Open `OneDashboards - Insights.pbip` in Power BI Desktop. It connects to the published model in the
`OneModel` workspace, just like the Bfusion pack.

## The story

Every chapter answers **one question** and reads from top to bottom:

1. **Header**: `AREA | QUESTION?` with slicers on the right. Portfolio, Program and Year are synced across pages.
2. **Orange headline**: one sentence that a DAX measure writes from the data in the current filter.
   It gives the answer before the charts do.
3. **① The pulse**: KPI cards. Teal is fine, amber needs a look, red needs a decision.
4. **② Trend / composition**: where things are heading.
5. **③ Drivers**: why the numbers are what they are.
6. **④ The list to act on**: a register sorted so the first row is the first thing to do.
7. **Next chapter ›**: a button to the next page in the story, plus a link back to the navigator.

| # | Page | Question | Audience |
|---|---|---|---|
| – | Home: Story Navigator | Pick the question you came to answer | everyone |
| 1 | Executive Summary | Are we on course? | Executive board, monthly |
| 2 | Portfolio | Are we investing in the right things? | Portfolio board, quarterly |
| 3 | Financials | Are we spending as planned? | Finance & PMO, monthly close |
| 3b | Pareto & Portfolio P&L | Where does the money concentrate, and what does it return? | Finance & portfolio board |
| 4 | Resource Management | Do we have the people? | Resource managers, monthly |
| 5 | Planning & Scheduling | Will we deliver on time? | Delivery leads, weekly |
| 6 | Risk Management | What could go wrong? | Risk owners, fortnightly |
| 7 | Benefits & Value | Will it pay off? | Sponsors, quarterly |
| 8 | Governance & Data Trust | Can we trust the data? | PMO, weekly |

The page design takes ideas from OnePlan's own personas and questions ("Are we funding the right things?",
"What is our investment delivering?", "Can we execute what we've planned?") and from its modules:
Strategic/Portfolio planning, Financial plans, Resource plans, Work plans, Plan Insights, Lifecycle.
`my.oneplan.ai` requires a sign-in, so the tenant UI itself was not analysed.

## Storytelling measures

The headlines, action prompts and colour rules are **report-level measures** (`reportExtensions.json`,
display folder `Story`), so the published model needs **no change**. They build only on model measures
and columns that the existing pack already uses. Examples:

- `Story | Finance Headline`: budget, actuals, burn, forecast against budget, and the largest overrun.
- `Story | Resource Headline`: capacity, utilisation, people over-allocated, the most stretched role, and how much demand is still soft.
- `Story | Exec Action Money / People / Risk`: the three decisions on the Executive page.
- `Story | * Colour`: hex colours used for conditional formatting (variance, utilisation, heat map, due dates).

## Data notes (from the model audit)

- The report-level filters are copied from the Bfusion pack: `FactCost[DetailRow] = false` (avoids double-counting
  the cost-category tree) and the "Template" exclusions on project, program and portfolio.
- Capacity sits on the 1st of each month, so every time axis uses `DimDate[MonthStart]`. Choose a **Year** on
  the Resource page for a clean heat map.
- Portfolio and Benefits pages use the plan fields (`DimProject[Budget]`, `[Forecast]`, `[Benefits]`).
  Financials uses the time-phased financial plan (`FactCost`). The two can differ if plans are not in sync.
- Project-level visuals use `DimProject[Portfolio Name]` and `[Program Name]`. DimPortfolio and DimProgram
  do not filter DimProject or DimTask.

## Rebuilding

The pack is generated. Change the Python and rebuild rather than editing JSON by hand:

```bash
cd "_generator"
python build.py --check
```

`--check` validates every file against the Microsoft PBIR JSON schemas. It also checks that every column,
measure and DAX reference exists in `SemanticModel/ModeL360Star.bim`, and that no visual sits on the footer band.
Formatting you change in Desktop is lost on the next rebuild, so move it into `_generator/pages.py`.
