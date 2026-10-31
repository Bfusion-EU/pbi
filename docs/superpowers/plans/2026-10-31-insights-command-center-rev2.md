# Insights Command Center — Revision 2 (one card per subject area) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Home command center to spec revision 2
(`docs/superpowers/specs/2026-10-31-insights-command-center-design.md`). The new page has 8 uniform
subject cards in a 4 × 2 grid, a slim briefing strip, and a right column that switches between
Act now (PMO view) and the three decisions (Executive view).

**Architecture:** Everything stays in the generator module `ext_home.py`. Rev 1 already provides
the rail, the top bar, the history measures, Act-now ranking, bookmarks and visual groups, so
those are kept. The rev-1 body is replaced: `build_pulse`, `build_pmo`, `build_exec` and the
`AREAS` tiles give way to `build_brief`, `subject_card` / `build_cards`, `build_right_pmo` and
`build_right_exec`. A spike (Task 1) decides how left-aligned values are rendered. Either the
native "Card (new)" (`cardVisual`) is used, or a one-cell table with its header blended into the
card.

**Tech Stack:** Python 3.14 + pytest, PBIR JSON, report-level DAX, Power BI Desktop for the
visual check.

## Global Constraints

- Native Power BI visuals only. No model change. New measures are report-level, folder `Story\Home`, prefix `Story | Home · `.
- Reuse an existing measure wherever one answers the question. Delete Home measures and helpers that nothing uses any more.
- Page 1800 × 1000, `FitToPage`, canvas `#141C2F`; cards `#1B2540`, radius 14; text `#E8ECF4`, labels `#8C98B3`; accent `#E8612A`; status red `#FF8A80`, amber `#F2C46B`, teal `#5DCAA5`, grey `#8C98B3`; pill fills `#3A1E22` / `#3A2F18` / `#173A33` / `#26314F`.
- Layout: subject grid at x 104–1340, 4 columns × 2 rows, gap 16, column width 297, row height 406, rows at y 160 and y 582. Right column at x 1356–1784, y 160–988. Briefing strip at x 104–1784, y 92–148.
- Every subject card has the same five rows, all left-aligned: header with pill; number and label; trend or bar or empty; sentence; footer links.
- Only right-column visuals belong to the groups `grp_pmo` / `grp_exec`. The bookmarks are display-only (`suppressData`). The default view is PMO.
- `Page.add(..., parent=grp)` takes absolute coordinates and stores them group-relative. A group must be added before its children.
- `python build.py --check` (with `INSIGHTS_OUT` pointing to a scratch folder, except in the final task) and `python dax_check.py` (0 errors) must pass before each commit that touches the report.
- Paths are relative to `C:\pbi-rn\OneDashboards-renamed\DecisionHome-work\Insights\_generator` unless they start with `C:\`.
- Commits go to branch `report-updates-20260914` of `C:\pbi-rn`. Stage only the named files, never `.pbix`. Each message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## File structure

| File | Responsibility |
|---|---|
| `ext_home.py` (modify) | measures (new: Briefing Reasons, Insight ×8, Pill ×8, Colour Status, Pill Fill ×8; removed: Line ×8, Answer ×4, Colour Timesheets), the value/text helpers chosen in Task 1, the new layout |
| `tests/test_home.py` (modify) | rev-2 structure tests; the rev-1 tile, KPI-row and answers tests are removed |
| `../README.md` (modify) | Home section rewritten for rev 2 |

---

### Task 1: Spike — left-aligned value and text visuals

**Files:**
- Modify: `ext_home.py` (helpers `value_cell`, `text_cell`, constant `VALUE_VISUAL`)
- Test: `tests/test_home.py` (`test_value_and_text_cells`)

**Interfaces:**
- Produces:
  - `value_cell(measure: str, colour_measure: str | None = None, size: int = 28) -> dict`: the visual JSON for one left-aligned value.
  - `text_cell(measure: str, size: int = 11, colour: str = INK2, colour_measure: str | None = None) -> dict`: one left-aligned, wrapping sentence.
  - Module constant `VALUE_VISUAL` set to `"cardVisual"` or `"tableEx"`, recording which route won.

- [ ] **Step 1: Write the failing test** (append to `tests/test_home.py`)

```python
def test_value_and_text_cells():
    v = ext_home.value_cell("Story | Active Projects", size=28)
    t = ext_home.text_cell("Story | Home · Greeting", size=11)
    assert v["visualType"] == ext_home.VALUE_VISUAL
    assert t["visualType"] == ext_home.VALUE_VISUAL
    for vis in (v, t):
        roles = vis["query"]["queryState"]
        projs = [p for r in roles.values() for p in r["projections"]]
        assert len(projs) == 1  # exactly one measure, nothing else
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_home.py::test_value_and_text_cells -v`
Expected: FAIL, `AttributeError: module 'ext_home' has no attribute 'value_cell'`.

- [ ] **Step 3: Try route A, `cardVisual`**

Add to `ext_home.py` (below `text_line`):

```python
VALUE_VISUAL = "cardVisual"


def _card_new(measure, size, colour_measure=None, colour=INK2):
    """Native 'Card (new)': one measure, value left-aligned, no category label, no chrome."""
    fc = measure_colour(colour_measure) if colour_measure else col_solid(colour)
    v = {"visualType": "cardVisual",
         "query": {"queryState": {"Data": {"projections": [P(M(measure))]}}},
         "objects": {
             "value": [{"properties": {"fontSize": n(size), "fontColor": fc, "fontFamily": s("Segoe UI Semibold"),
                                       "horizontalAlignment": s("left")}, "selector": {"id": "default"}}],
             "label": [{"properties": {"show": b(False)}, "selector": {"id": "default"}}],
             "layout": [{"properties": {"alignment": s("left")}}],
             "accentBar": [{"properties": {"show": b(False)}, "selector": {"id": "default"}}],
             "fillCustom": [{"properties": {"show": b(False)}, "selector": {"id": "default"}}],
             "outline": [{"properties": {"show": b(False)}, "selector": {"id": "default"}}]},
         "visualContainerObjects": {"title": [{"properties": {"show": b(False)}}],
                                    "background": [{"properties": {"show": b(False)}}],
                                    "border": [{"properties": {"show": b(False)}}],
                                    "padding": [{"properties": {"top": n(0), "bottom": n(0), "left": n(0), "right": n(0)}}]},
         "drillFilterOtherVisuals": True}
    return v


def value_cell(measure, colour_measure=None, size=28):
    return _card_new(measure, size, colour_measure)


def text_cell(measure, size=11, colour=INK2, colour_measure=None):
    return _card_new(measure, size, colour_measure, colour)
```

Run: `python -m pytest tests/test_home.py::test_value_and_text_cells -v` → PASS.
Run: `$env:INSIGHTS_OUT="$env:TEMP\cc_spike"; python build.py --check`. Expected: `OK`. If the
schema check rejects an object name, look up the property names in the cardVisual section of
the cached visualContainer schema
(`.schema-cache/*visualContainer*`, search for `cardVisual`). Correct them and rerun until it
passes.

- [ ] **Step 4: Desktop spike**

Temporarily add to the end of `build_top` (spike only, not committed):

```python
    pg.add(X0, 420, 297, 60, value_cell("Story | Active Projects", size=28), key="spike_v")
    pg.add(X0, 490, 297, 50, text_cell(hm("Briefing"), size=11), key="spike_t")
```

Build to `$env:TEMP\cc_spike` and open `$env:TEMP\cc_spike\OneDashboards - Insights.pbip`. Wait
about 90 s, then capture with PrintWindow (no CopyFromScreen, no foreground) to
`$env:TEMP\cc_spike.png` and Read it.

**Route A wins** if all four hold:
(1) both visuals render;
(2) "15" is left-aligned;
(3) the briefing sentence is left-aligned and wraps to 2 lines without an ellipsis;
(4) there is no label or box.
If so, keep the code and go to Step 6.

- [ ] **Step 5: Route B (only if route A fails a check)**

Replace `VALUE_VISUAL` and the two helpers with the one-cell-table route:

```python
VALUE_VISUAL = "tableEx"


def _cell(measure, size, colour_measure=None, colour=INK2):
    """One-cell table: left-aligned, wrapping text; header blended into the card (panel colour, 1pt)."""
    fc = measure_colour(colour_measure) if colour_measure else col_solid(colour)
    obj = {"columnHeaders": [{"properties": {"backColor": col_solid(PANEL), "fontColor": col_solid(PANEL),
                                             "fontSize": n(1), "outline": s("None")}}],
           "values": [{"properties": {"fontSize": n(size), "fontColorPrimary": fc, "backColorPrimary": col_solid(PANEL),
                                      "fontColorSecondary": fc, "backColorSecondary": col_solid(PANEL),
                                      "wordWrap": b(True), "outline": s("None")}}],
           "grid": [{"properties": {"gridHorizontal": b(False), "gridVertical": b(False), "rowPadding": n(0),
                                    "outlineColor": col_solid(PANEL)}}],
           "total": [{"properties": {"totals": b(False)}}]}
    if colour_measure:
        obj["values"].append(pbir.cf_font(M(measure), colour_measure))
    v = chart("tableEx", {"Values": [P(M(measure), " ")]}, "", obj)
    vco = v["visualContainerObjects"]
    vco["title"] = [{"properties": {"show": b(False)}}]
    vco["background"] = [{"properties": {"show": b(False)}}]
    vco["border"] = [{"properties": {"show": b(False)}}]
    return v


def value_cell(measure, colour_measure=None, size=28):
    return _cell(measure, size, colour_measure)


def text_cell(measure, size=11, colour=INK2, colour_measure=None):
    return _cell(measure, size, colour_measure, colour)
```

Rebuild, reopen and recapture. Route B passes if the value and the sentence are left-aligned,
the header strip is invisible, and the sentence wraps. If route B also fails, stop and report
BLOCKED with both screenshots.

- [ ] **Step 6: Remove the spike lines, run the tests and the build check, then commit**

Run: `python -m pytest tests -v` → all pass. Run: `python build.py --check` (scratch) → `OK`.

```bash
git -C C:/pbi-rn add "OneDashboards-renamed/DecisionHome-work/Insights/_generator/ext_home.py" "OneDashboards-renamed/DecisionHome-work/Insights/_generator/tests/test_home.py"
git -C C:/pbi-rn commit -m "feat(insights): left-aligned value/text cells for the command center (spike result: <cardVisual|tableEx>)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Rev-2 measures

**Files:**
- Modify: `ext_home.py` (measures section)
- Test: `tests/test_home.py` (`HOME` list, `test_home_measures_registered`)

**Interfaces:**
- Consumes: the existing measures named in the spec's card table. The status-report ones are `Story | Status · Overall Worsened` and `Story | Status · Not Reporting`. The governance one is `PMO | Plans Failing`.
- Produces (all `Story | Home · …`): `Briefing` (short sentence), `Briefing Reasons`, `Insight Financials`, `Insight Schedule`, `Insight Resources`, `Insight Risk`, `Insight Portfolio`, `Insight Benefits`, `Insight Status`, `Insight Governance`, `Colour Status`, `Pill <Subject>` and `Pill Fill <Subject>` for the subjects Financials, Schedule, Resources, Risk, Portfolio, Benefits, Status, Governance.
- Removes: `Line …` (8), `Answer …` (4), `Colour Timesheets`.

- [ ] **Step 1: Update the test list (failing)**

In `tests/test_home.py` replace the `HOME` list with:

```python
SUBJECTS = ["Financials", "Schedule", "Resources", "Risk", "Portfolio", "Benefits", "Status", "Governance"]
HOME = (["Greeting", "Refreshed", "Briefing", "Briefing Reasons", "Act Score", "Act Reason", "Act Colour", "Act Count",
         "EAC Var % (reports)", "On Track % (reports)", "EAC Change", "On Track Change", "Due",
         "Colour EAC", "Colour Util", "Colour Trust", "Colour Portfolio", "Colour Schedule", "Colour Risk",
         "Colour Benefits", "Colour Status"]
        + [f"Insight {s}" for s in SUBJECTS] + [f"Pill {s}" for s in SUBJECTS] + [f"Pill Fill {s}" for s in SUBJECTS])
REMOVED = [f"Line {s}" for s in ["Portfolio", "Financials", "Resources", "Schedule", "Risk", "Benefits", "Timesheets",
                                  "Governance"]] + [f"Answer {a}" for a in ["Finance", "Schedule", "Resources", "Benefits"]] \
          + ["Colour Timesheets"]


def test_removed_measures_gone():
    assert [n for n in REMOVED if f"Story | Home · {n}" in NAMES] == []
```

Run: `python -m pytest tests/test_home.py -k "measures" -v`. Expected: FAIL, with the new names
missing and the removed ones still present.

- [ ] **Step 2: Implement the measures in `ext_home.py`**

Replace the `Briefing` measure and add `Briefing Reasons` (`_bvars` / `_BUCKETS` already exist):

```python
_add("Briefing", T, f"""
VAR _n = [{hm("Act Count")}]
VAR _a = [Story | Active Projects]
RETURN IF ( _n = 0, "No active project needs a decision this week",
    FORMAT ( _n, "0" ) & " of " & FORMAT ( _a, "0" ) & " active projects need a decision" )""",
     desc="How many active projects need a decision (Act-now count).")
_rparts = "\n        & ".join(f'IF ( _b{k} > 0, "  ·  " & FORMAT ( _b{k}, "0" ) & " {lbl}" )' for k, lbl in _BUCKETS)
_add("Briefing Reasons", T, f"""
{_bvars}
VAR _p = {_rparts}
RETURN IF ( LEN ( _p ) > 0, MID ( _p, 6, LEN ( _p ) ) )""",
     desc="Act-now projects per reason (same Act Score buckets, so the parts add up to Act Count).")
```

Shorten the bucket labels in `_BUCKETS` to: `(100, "off track"), (90, "over budget"), (80, "late"),
(60, "overdue work"), (50, "not reporting"), (40, "failing rules")`.

Delete the `Line …` block, the `Answer …` loop (and `FIRST`), and `Colour Timesheets`. Then add:

```python
_add("Colour Status", T, f"""
VAR _w = [Story | Status · Overall Worsened] + 0
RETURN IF ( _w >= 3, "{C_RED}", IF ( _w >= 1, "{C_AMBER}", "{C_TEAL}" ) )""", folder=_COL)

# ---------------------------------------------------------------- subject cards: sentence, pill word, pill fill
WORST = """
VAR _w = TOPN ( 1, FILTER ( ADDCOLUMNS ( {projects}, "@v", {expr} ), NOT ISBLANK ( [@v] ) ), [@v], DESC, DimProject[Id], ASC )
VAR _wn = CALCULATE ( SELECTEDVALUE ( DimProject[Name] ), TREATAS ( SELECTCOLUMNS ( _w, "@id", DimProject[Id] ), DimProject[Id] ) )
VAR _wv = MAXX ( _w, [@v] )"""
_add("Insight Financials", T, f"""
VAR _v = [Story | EAC Variance %]
{WORST.format(projects=PROJECTS, expr="[Story | EAC Variance %]")}
RETURN IF ( ISBLANK ( _v ), "No EAC in the financial plans yet.",
    "EAC " & FORMAT ( _v, "+0.0%;-0.0%;0.0%" ) & " vs budget"
        & IF ( _wv > 0, "; worst " & _wn & " " & FORMAT ( _wv, "+0%" ) & ".", "." ) )""")
_add("Insight Schedule", T, f"""
VAR _o = [Story | On Track %]
VAR _c = [{hm("On Track Change")}]
{WORST.format(projects=PROJECTS, expr="[Story | Baseline · Finish Slip (days)]")}
RETURN FORMAT ( _o, "0%" ) & " on track" & IF ( ISBLANK ( _c ), "", " (" & _c & ")" )
    & IF ( _wv > 0, "; " & _wn & " +" & FORMAT ( _wv, "0" ) & " d vs baseline.", "." )""")
_add("Insight Resources", T, """
VAR _o = [Story | Over-allocated People] + 0
VAR _m = [Story | TS Status · Missing Timesheets] + 0
RETURN FORMAT ( _o, "0" ) & IF ( _o = 1, " person", " people" ) & " over 100% in view; "
    & FORMAT ( _m, "0" ) & IF ( _m = 1, " timesheet", " timesheets" ) & " missing." """)
_add("Insight Risk", T, """
VAR _a = [Story | Active Risk Count] + 0
VAR _u = [Story | Unmitigated Risk %]
RETURN FORMAT ( _a, "0" ) & " active risks"
    & IF ( ISBLANK ( _u ), ".", "; " & FORMAT ( _u, "0%" ) & " without mitigation." )""")
_add("Insight Portfolio", T, """
VAR _a = [Story | Active Projects] + 0
VAR _p = [Story | Proposed Projects] + 0
RETURN FORMAT ( _a, "0" ) & " active, " & FORMAT ( _p, "0" ) & " proposed in the pipeline." """)
_add("Insight Benefits", T, f"""
VAR _b = [Story | Benefits At Completion]
VAR _e = [Story | Finance EAC]
RETURN IF ( ISBLANK ( _b ), "No benefits plan in view.",
    {money("_b")} & " planned benefits against " & {money("_e")} & " EAC." )""")
_add("Insight Status", T, """
VAR _n = [Story | Status · Not Reporting] + 0
RETURN IF ( _n = 0, "Every project reported recently.",
    FORMAT ( _n, "0" ) & IF ( _n = 1, " project has", " projects have" ) & " not reported for 30+ days." )""")
_add("Insight Governance", T, """
VAR _f = [PMO | Plans Failing] + 0
RETURN IF ( _f = 0, "All plans pass the Plan Insights rules.",
    FORMAT ( _f, "0" ) & IF ( _f = 1, " plan fails", " plans fail" ) & " Plan Insights rules." )""")

SUBJECT_COLOUR = {"Financials": hm("Colour EAC"), "Schedule": hm("Colour Schedule"), "Resources": hm("Colour Util"),
                  "Risk": hm("Colour Risk"), "Portfolio": hm("Colour Portfolio"), "Benefits": hm("Colour Benefits"),
                  "Status": hm("Colour Status"), "Governance": hm("Colour Trust")}
for _s, _cm in SUBJECT_COLOUR.items():
    _add(f"Pill {_s}", T, f"""
VAR _c = [{_cm}]
RETURN SWITCH ( _c, "{C_RED}", "Act", "{C_AMBER}", "Watch", "{C_TEAL}", "OK", "–" )""",
         desc=f"Status word of the {_s} card, from its colour measure.")
    _add(f"Pill Fill {_s}", T, f"""
VAR _c = [{_cm}]
RETURN SWITCH ( _c, "{C_RED}", "#3A1E22", "{C_AMBER}", "#3A2F18", "{C_TEAL}", "#173A33", "#26314F" )""",
         folder=_COL, desc=f"Pill background of the {_s} card.")
```

Add `money` back to the `from story_measures import …` line if Task 4 of rev 1 removed it.

- [ ] **Step 3: Run the tests, the build check and dax_check**

Run: `python -m pytest tests -v`. The measure tests pass; layout tests that reference removed
measures may now fail, and Task 3 replaces them.
Run: `python build.py --check` (scratch). Expected: `OK`, no `REF dax measure` errors.
Open the model with `Start-Process "C:\Users\HassanBezzizi\repos\BFusion-Apps\SemanticModel\OneModel360Star.pbix"`,
wait about 90 s, then run `python dax_check.py --only "Home ·"`. Expected: `0 measure(s) with errors`.
Then:
- `python dax_check.py --only "Home ·" --show "Briefing"` should print both the short sentence and
  the reasons line.
- `--show "Insight"` should print 8 readable sentences.
- `--show "Pill"` should print words that match the colours.

Close the model when done.

- [ ] **Step 4: Commit** (only `ext_home.py` and `tests/test_home.py`), with the message
`feat(insights): rev-2 command-center measures (briefing reasons, subject sentences, status pills)`.

---

### Task 3: Rev-2 layout — briefing strip, subject cards, right column

**Files:**
- Modify: `ext_home.py` (layout section). Delete `build_pulse`, `build_pmo`, `build_exec`, `AREAS`, `CHART_H` (if `progress` is reworked), `BODY_Y`, and the rev-1 `stripe` usages.
- Test: `tests/test_home.py`. Replace the rev-1 tile, answer, body-area and z-order tests with the ones below.

**Interfaces:**
- Consumes: `value_cell` / `text_cell` (Task 1), the Task 2 measures, and from rev 1 `panel`, `ghost_link`, `sparkline`, `progress`, `link_chip`, `view_pill`, `build_rail`, `build_top`, `build_switch`, `dark_slicer`.
- Produces: `SUBJECTS_LAYOUT` (list), `subject_card(pg, x, y, spec)`, `build_brief(pg)`, `build_cards(pg)`, `build_right_pmo(pg, grp)`, `build_right_exec(pg, grp)`, plus the constants `GRID_X0 = 104`, `GRID_Y = (160, 582)`, `COL_W = 297`, `ROW_H = 406`, `RIGHT_X = 1356`, `RIGHT_W = 428`.

- [ ] **Step 1: Write the failing tests** (replace the rev-1 layout tests in `tests/test_home.py`)

```python
CARD_KEYS = ["fin", "sch", "res", "risk", "port", "ben", "sr", "gov"]
# visual names are uid(page, key, visualType) hashes; _name() (already in this file) rebuilds them
PART_TYPE = {"bg": "shape", "icon": "image", "title": "textbox", "pill": "card", "lbl": "textbox",
             "go": "actionButton"}


def _vc(pg, key, vtype):
    return next((vc for vc in pg.visuals if vc["name"] == _name(pg, key, vtype)), None)


def test_eight_subject_cards_with_five_rows():
    pg = _home()
    for c in CARD_KEYS:
        for part, vtype in PART_TYPE.items():
            assert _vc(pg, f"card_{c}_{part}", vtype) is not None, (c, part)
        for part in ("num", "sent"):
            assert _vc(pg, f"card_{c}_{part}", ext_home.VALUE_VISUAL) is not None, (c, part)


def test_cards_align_in_grid():
    pg = _home()
    pos = [_vc(pg, f"card_{c}_bg", "shape")["position"] for c in CARD_KEYS]
    assert {round(p["x"]) for p in pos} == {104, 417, 730, 1043}
    assert {round(p["y"]) for p in pos} == {160, 582}
    assert {(round(p["width"]), round(p["height"])) for p in pos} == {(297, 406)}


def test_only_right_column_is_grouped():
    pg = _home()
    groups = {vc["name"]: vc for vc in pg.visuals if "visualGroup" in vc}
    assert {g["visualGroup"]["displayName"] for g in groups.values()} == {"PMO view", "Executive view"}
    for vc in pg.visuals:
        if vc.get("parentGroupName"):
            gx = groups[vc["parentGroupName"]]["position"]["x"]
            assert gx + vc["position"]["x"] >= 1356 - 0.5, vc["name"]


def test_footer_links_target_pages():
    pg = _home()
    targets = {p["navigationSection"]["expr"]["Literal"]["Value"].strip("'")
               for p in _links(pg) if "navigationSection" in p}
    for key in ["finance", "finance2", "schedule", "gantt", "baseline", "resources", "timesheets", "resource",
                "risk", "lifecycle", "scenarios", "onepager", "benefits", "status", "governance"]:
        assert pages.PID[key] in targets, key
```

Keep the rev-1 tests that still apply: the rail buttons, `build_all` producing a single Home page,
slicer sync, bookmark maps, the switch and bookmark targets, every page reachable, and the
measures. Delete the tests for `area_*`, `ans_*`, `dec_*` at the old positions, `kpi_*`,
`lead_*`, `brief_link`, `test_body_area_fits` and `test_next30_due_is_a_short_date_measure` only
if it references removed keys (otherwise keep it). Update the group-membership test to:

```python
def test_children_belong_to_the_right_group():
    pg = _home()
    gid = {vc["visualGroup"]["displayName"]: vc["name"] for vc in pg.visuals if "visualGroup" in vc}
    pmo = [("act_bg", "shape"), ("act_title", "textbox"), ("act_tbl", "tableEx"), ("act_drill", "actionButton"),
           ("next_title", "textbox"), ("next_tbl", "tableEx"), ("view_pill_pmo", "shape")]
    exe = [(f"dec_bg{k}", "shape") for k in range(3)] + [(f"dec_go{k}", "actionButton") for k in range(3)]           + [("view_pill_exec", "shape")]
    for key, vt in pmo:
        assert _vc(pg, key, vt).get("parentGroupName") == gid["PMO view"], key
    for key, vt in exe:
        assert _vc(pg, key, vt).get("parentGroupName") == gid["Executive view"], key
```

Run: `python -m pytest tests/test_home.py -v`. Expected: the new tests FAIL.

- [ ] **Step 2: Implement the layout**

In `ext_home.py`, replace everything from `AREAS = [` through the end of `build_exec` with the
code below. Keep `link_chip`, `view_pill`, `build_switch`, `panel`, `ghost_link`, `sparkline`,
`progress`, `dark_slicer`, `build_rail` and `build_top`. Delete `BODY_Y` and `stripe`.

```python
GRID_X0, GRID_Y, COL_W, ROW_H, GAP = 104, (160, 582), 297, 406, 16
RIGHT_X, RIGHT_W, RIGHT_Y, RIGHT_H = 1356, 428, 160, 828

# (key, subject, icon, number measure, number format note, label, row-3 kind, row-3 arg, colour measure,
#  card link page, footer [(text, page)])
SUBJECTS_LAYOUT = [
    ("fin", "Financials", "finance", "Story | Projects Over Budget", "projects over EAC",
     "spark", hm("EAC Var % (reports)"), hm("Colour EAC"), "finance", [("Spend", "finance"), ("Pareto", "finance2")]),
    ("sch", "Schedule", "schedule", "Story | Baseline · Late Projects", "slipping vs baseline",
     "spark", hm("On Track % (reports)"), hm("Colour Schedule"), "schedule",
     [("Schedule", "schedule"), ("Gantt", "gantt"), ("Baseline", "baseline")]),
    ("res", "Resources", "resources", "Story | Utilisation %", "utilisation",
     "bar", (0, 1), hm("Colour Util"), "resources", [("People", "resources"), ("Time", "timesheets"), ("Person", "resource")]),
    ("risk", "Risk", "risk", "Story | Critical High Risks", "critical risks",
     None, None, hm("Colour Risk"), "risk", [("Risk", "risk")]),
    ("port", "Portfolio", "portfolio", "Story | Aligned Budget %", "budget aligned",
     "bar", (0, 1), hm("Colour Portfolio"), "portfolio",
     [("Gates", "lifecycle"), ("Scenarios", "scenarios"), ("Project", "onepager")]),
    ("ben", "Benefits", "benefits", "Story | Benefit Cost Ratio", "benefit / cost",
     None, None, hm("Colour Benefits"), "benefits", [("Benefits", "benefits")]),
    ("sr", "Status reports", "exec", "Story | Status · Overall Worsened", "worse since last report",
     None, None, hm("Colour Status"), "status", [("Trend", "status")]),
    ("gov", "Governance", "governance", "PMO | Governance Score", "data trust score",
     "bar", (0, 100), hm("Colour Trust"), "governance", [("Governance", "governance")]),
]
_PILL_NAME = {"fin": "Financials", "sch": "Schedule", "res": "Resources", "risk": "Risk", "port": "Portfolio",
              "ben": "Benefits", "sr": "Status", "gov": "Governance"}


def pill(measure_word, measure_fill_name):
    v = text_line(measure_word, size=9, colour=INK2, bg="#26314F")
    v["visualContainerObjects"]["background"] = [{"properties": {"show": b(True),
                                                                 "color": measure_colour(measure_fill_name)}}]
    return v


def subject_card(pg, x, y, spec):
    key, name, icon, num, label, kind, arg, colour, link, footer = spec
    p = f"card_{key}"
    panel(pg, x, y, COL_W, ROW_H, f"{p}_bg")
    pg.add(x + 16, y + 16, 20, 20, image(f"rail-{icon}-grey.png", f"{name} icon"), key=f"{p}_icon")
    pg.add(x + 44, y + 14, 170, 24, textbox([[(name, st("Segoe UI Semibold", 11, INK2, True))]]), key=f"{p}_title")
    pg.add(x + COL_W - 76, y + 16, 60, 22, pill(hm(f"Pill {_PILL_NAME[key]}"), hm(f"Pill Fill {_PILL_NAME[key]}")),
           key=f"{p}_pill")
    pg.add(x + 16, y + 52, COL_W - 32, 56, value_cell(num, colour_measure=colour, size=28), key=f"{p}_num")
    pg.add(x + 16, y + 108, COL_W - 32, 20, textbox([[(label, st("Segoe UI", 10, LABEL))]]), key=f"{p}_lbl")
    if kind == "spark":
        pg.add(x + 8, y + 136, COL_W - 16, 96, sparkline(arg, colour), key=f"{p}_spark")
    elif kind == "bar":
        progress(pg, x + 16, y + 176, COL_W - 32, 12, num, arg[0], arg[1], colour, f"{p}_bar")
    pg.add(x + 16, y + 244, COL_W - 32, 96, text_cell(hm(f"Insight {_PILL_NAME[key]}"), size=11), key=f"{p}_sent")
    pg.add(x + 16, y + ROW_H - 52, COL_W - 32, 1, shape("#26314F"), key=f"{p}_rule")
    # whole-card link first, footer links on top of it
    pg.add(x, y, COL_W, ROW_H - 56, ghost_link(link, name), key=f"{p}_go")
    cw = (COL_W - 32 - 6 * (len(footer) - 1)) / len(footer)
    for j, (txt, target) in enumerate(footer):
        pg.add(round(x + 16 + j * (cw + 6), 2), y + ROW_H - 44, round(min(cw, 110), 2), 28, link_chip(txt, target),
               key=f"{p}_ft{j}")


def build_brief(pg):
    panel(pg, GRID_X0, 92, X1 - GRID_X0, 56, "brief_bg", fill=ORANGE)
    pg.add(GRID_X0 + 16, 104, 700, 32, text_cell(hm("Briefing"), size=14, colour="#FFFFFF"), key="brief")
    pg.add(GRID_X0 + 740, 106, X1 - GRID_X0 - 756, 28, text_cell(hm("Briefing Reasons"), size=11, colour="#FFFFFF"),
           key="brief_reasons")


def build_cards(pg):
    for k, spec in enumerate(SUBJECTS_LAYOUT):
        x = GRID_X0 + (k % 4) * (COL_W + GAP)
        y = GRID_Y[k // 4]
        subject_card(pg, x, y, spec)


def build_right_pmo(pg, grp):
    view_pill(pg, grp, 0, "view_pill_pmo")
    x, y = RIGHT_X, RIGHT_Y
    panel(pg, x, y, RIGHT_W, RIGHT_H, "act_bg", parent=grp)
    pg.add(x + 16, y + 12, 380, 28, textbox([[("Act now", st("Segoe UI Semibold", 13, INK2, True)),
                                              ("   top 8, ranked by impact", st("Segoe UI", 10, LABEL))]]),
           key="act_title", parent=grp)
    obj = pbir.table_style(10, header_bg=PANEL)
    obj["values"] = [{"properties": {"fontSize": n(10), "fontColorPrimary": col_solid(INK2),
                                     "backColorPrimary": col_solid(PANEL), "fontColorSecondary": col_solid(INK2),
                                     "backColorSecondary": col_solid(PANEL), "wordWrap": b(True)}},
                     pbir.cf_font(M(hm("Act Reason")), hm("Act Colour"))]
    obj["grid"] = [{"properties": {"gridHorizontal": b(True), "gridHorizontalColor": col_solid("#26314F"),
                                   "rowPadding": n(6)}}]
    obj["total"] = [{"properties": {"totals": b(False)}}]
    tbl = chart("tableEx", {"Values": [P(pages.DP("Name"), "Project"), P(M(hm("Act Reason")), "Why"),
                                       P(M(hm("Act Score")), "Impact")]},
                "", obj, sort=[(M(hm("Act Score")), "Descending")])
    for o in ("title", "background", "border"):
        tbl["visualContainerObjects"][o] = [{"properties": {"show": b(False)}}]
    pg.add(x + 8, y + 44, RIGHT_W - 16, 408, tbl, key="act_tbl", parent=grp, filters=[pages.REAL_PROJECTS])
    pg.add(x + 16, y + 460, 200, 32, pbir.drill_button("Open One-Pager ›", pages.PID["project"],
           "Select a project row first", fill=ORANGE, size=10), key="act_drill", parent=grp)
    pg.add(x + 224, y + 464, RIGHT_W - 240, 26, textbox([[("or right-click › Drill through", st("Segoe UI", 9, LABEL))]]),
           key="act_hint", parent=grp)
    pg.add(x + 16, y + 512, 300, 28, textbox([[("Next 30 days", st("Segoe UI Semibold", 13, INK2, True))]]),
           key="next_title", parent=grp)
    mobj = pbir.table_style(10, header_bg=PANEL)
    mobj["values"] = obj["values"][:1]
    mobj["grid"] = obj["grid"]
    mobj["total"] = obj["total"]
    due = M(hm("Due"))
    miles = chart("tableEx", {"Values": [P(due, "Due"), P(pages.DP("Name"), "Project"), P(pages.DT("Name"), "Milestone")]},
                  "", mobj, sort=[(due, "Ascending")])
    for o in ("title", "background", "border"):
        miles["visualContainerObjects"][o] = [{"properties": {"show": b(False)}}]
    pg.add(x + 8, y + 544, RIGHT_W - 16, RIGHT_H - 556, miles, key="next_tbl", parent=grp,
           filters=[pbir.f_in("DimTask", "Milestone", [True]), pbir.f_cmp("DimTask", "PercentDone", 3, 100),
                    pages.PROJECT_TASKS])


def build_right_exec(pg, grp):
    view_pill(pg, grp, 1, "view_pill_exec")
    decisions = [("Money decision", "Story | Exec Action Money", hm("Colour EAC"), "finance"),
                 ("People decision", "Story | Exec Action People", hm("Colour Util"), "resources"),
                 ("Risk decision", "Story | Exec Action Risk", hm("Colour Risk"), "risk")]
    h = (RIGHT_H - 2 * GAP) / 3
    for k, (label, m, colour, target) in enumerate(decisions):
        y = round(RIGHT_Y + k * (h + GAP), 2)
        panel(pg, RIGHT_X, y, RIGHT_W, round(h, 2), f"dec_bg{k}", parent=grp)
        pg.add(RIGHT_X + 16, y + 14, 300, 22, textbox([[(label, st("Segoe UI Semibold", 11, INK2, True))]]),
               key=f"dec_lbl{k}", parent=grp)
        pg.add(RIGHT_X + 16, y + 44, RIGHT_W - 32, round(h - 100, 2), text_cell(m, size=12), key=f"dec{k}", parent=grp)
        pg.add(RIGHT_X + 16, round(y + h - 44, 2), 180, 28,
               link_chip(dict(pages.PAGES)[target].split("·", 1)[-1].strip(), target), key=f"dec_go{k}", parent=grp)
```

Replace `build()`:

```python
def build():
    pg = Page(pages.PID["home"], dict(pages.PAGES)["home"], pages.W, 1000, background_colour=CANVAS,
              display_option="FitToPage")
    build_rail(pg)
    build_top(pg)
    build_brief(pg)
    build_cards(pg)
    panel(pg, 1580, 24, 196, 44, "switch_bg")
    # groups hold only the right column and their view pill (pill sits at y 30, so the group starts at y 24)
    g_pmo = pg.add_group(RIGHT_X, 24, 1784 - RIGHT_X, 988 - 24, "PMO view", key="grp_pmo")
    g_exec = pg.add_group(RIGHT_X, 24, 1784 - RIGHT_X, 988 - 24, "Executive view", key="grp_exec", hidden=True)
    build_right_pmo(pg, g_pmo)
    build_right_exec(pg, g_exec)
    bm_pmo = pbir.bookmark("Home · PMO view", "home_pmo", pg.id, {g_pmo: False, g_exec: True})
    bm_exec = pbir.bookmark("Home · Executive view", "home_exec", pg.id, {g_pmo: True, g_exec: False})
    build_switch(pg, bm_pmo, bm_exec)
    return [pg]
```

`view_pill` places the pills at x 1586 / 1680, which is inside a group that starts at x 1356, so
the conversion to group-relative coordinates works. Card visuals are not grouped. The briefing
link of rev 1 is removed; update the tests that referenced `brief_link`.

- [ ] **Step 3: Run the tests and the build check**

Run: `python -m pytest tests -v` → all pass.
Run: `python build.py --check` (scratch) → `OK`, with no layout errors.

- [ ] **Step 4: Desktop look**

Open the scratch build and capture the PMO view to `$env:TEMP\cc_rev2_pmo.png`. For the
Executive view, swap `isHidden` on the two group `visual.json` files in a second scratch copy
only, then capture to `$env:TEMP\cc_rev2_exec.png`. Read both. Check:
- the 8 cards line up row by row, with every row the same height;
- the numbers and sentences are left-aligned, and no sentence is cut off;
- the pills show matching words and colours;
- the Act-now table shows 8 whole rows;
- the decision texts are readable.

Adjust the row offsets inside `subject_card` only, never the grid constants, until all of this
holds. Close only the Desktop windows you opened.

- [ ] **Step 5: Commit** `ext_home.py` and `tests/test_home.py` with the message
`feat(insights): command-center rev 2 — subject cards, briefing strip, right-column views`.

---

### Task 4: Real build, README, Obsidian

**Files:**
- Modify: `C:\pbi-rn\OneDashboards-renamed\DecisionHome-work\Insights\README.md` (the "Home — command center" section)
- Regenerate: `…\Insights\OneDashboards - Insights.Report\**`

- [ ] **Step 1: Full checks.** Run `python -m pytest tests -v` (all pass). With the model open,
run `python dax_check.py` (0 errors), then close the model.

- [ ] **Step 2: README.** Replace the "Home — command center" section with:

```markdown
## Home — command center

One card per subject area, all built the same way (status pill, number, trend or bar, one sentence, links):
Financials, Schedule, Resources, Risk, Portfolio, Benefits, Status reports, Governance.

- **Briefing strip**: how many active projects need a decision, and why (counts per reason; they add up).
- **Right column**, switched by the PMO / Executive buttons (display-only bookmarks — slicers stay):
  PMO = *Act now* (top 8 active projects by worst reason: off track > EAC +5% > 10 d late vs baseline >
  10 overdue tasks > no report 30 d > failing rules; open the One-Pager from a selected row) and *Next 30 days*;
  Executive = the three decisions (money, people, risk).
- Trend lines and "vs last month" chips come from status-report history (each active project's latest report
  as of month end, last 6 months).
- Icon rail on the left to every chapter; card footers link to every follow-on page.
- Portfolio and Program slicers on Home are synced with every chapter.
- Measures: report-level, folder `Story\Home` (`ext_home.py`).
```

- [ ] **Step 3: Real build.** Run `python build.py --check` without `INSIGHTS_OUT`. Expected: `OK`.

- [ ] **Step 4: Commit.** Stage with
`git -C C:/pbi-rn add -A -- "OneDashboards-renamed/DecisionHome-work/Insights/OneDashboards - Insights.Report" "OneDashboards-renamed/DecisionHome-work/Insights/README.md"`.
Check that `git diff --cached --name-only` lists nothing outside `Insights/` and no `.pbix`. Commit
with the message `feat(insights): command-center rev 2 in the generated report; README`.

- [ ] **Step 5: Obsidian.** Append a section "## 2026-10-31 Command center rev 2" to
`decision-native-insights-pack.md` (vault `C:\Obsidian\skyfall`, find it under `Memory`). Cover:
- rev 1 looked messy because subjects were repeated and card styles were mixed;
- rev 2 has one uniform card per subject area;
- only the right column switches with the view;
- the spike result: `cardVisual` or the one-cell table for left alignment.

Do not commit in the vault.

- [ ] **Step 6: Manual click checks (the user).** List them in the report:
1. The view switch toggles the right column.
2. A slicer pick survives the switch and carries into a chapter.
3. The rail icons, cards and footer links land on the right pages.
4. "Open One-Pager ›" opens the selected project.
