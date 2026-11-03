"""Data confidence: does each active project have the data the story's numbers rely on?

Eight checks per active project, one per OnePlan source. They feed three things:
- a one-line strip next to the filter-context bar on every chapter screen ("Data confidence  ⚠ EAC 9/15 · ...");
- the 8b Reconciliation page: coverage per source and one row per project with the gaps to fix;
- its headline: how many projects are complete and which source is weakest.
A source counts as covered when at least COVERED of the active projects have it. Every check looks at the whole
project life (date filters removed) and ignores the Baseline slicer, so a strip never mixes time bases.
"""
import pbir
from story_measures import add, ACTIVE, T, D, I

FOLDER = "Story\\Confidence"
PX = "Story | Confidence · "
COVERED = 0.8
LIFE_ACTUAL = "CALCULATE ( [Story | Actual Cost], REMOVEFILTERS ( DimDate ) )"
ACTIVE_IDS = f"FILTER ( CALCULATETABLE ( VALUES ( DimProject[Id] ), {ACTIVE} ), NOT ISBLANK ( DimProject[Id] ) )"

# key, label (cards, gaps list), short (strip), condition evaluated for one project
CHECKS = [
    ("budget", "Budget", "budget", "[Story | Budget At Completion] > 0"),
    ("eac", "EAC beyond actuals", "EAC", f"[Story | Finance EAC] > COALESCE ( {LIFE_ACTUAL}, 0 )"),
    ("actuals", "Actual cost", "actuals", f"{LIFE_ACTUAL} > 0"),
    ("schedule", "Scheduled hours", "schedule",
     "CALCULATE ( [Story | Project Scheduled Hours], REMOVEFILTERS ( DimDate ) ) > 0"),
    ("timesheets", "Timesheet hours", "timesheets", "CALCULATE ( [Timesheet | Actual Hours], REMOVEFILTERS ( DimDate ) ) > 0"),
    ("baseline", "Baseline", "baseline", "NOT ISBLANK ( CALCULATE ( [Story | Baseline · Baseline Finish], "
                                         "REMOVEFILTERS ( FactStatusReport[Summary_LastBaselineDate] ) ) )"),
    ("status", "Status report ≤ 30 d", "status ≤30d",
     "COALESCE ( [Story | Status · Days Since Report], 99999 ) <= [Story | Status · Stale Days]"),
    ("benefits", "Planned benefits", "benefits", "[Story | Benefits At Completion] > 0"),
]
LABEL = {k: lbl for k, lbl, _s, _c in CHECKS}
SHORT = {k: s for k, _l, s, _c in CHECKS}
# which sources each chapter's numbers stand on
CHAPTER_CHECKS = {
    "exec": ["budget", "eac", "actuals", "schedule", "status"],
    "portfolio": ["budget", "benefits", "status"],
    "finance": ["budget", "eac", "actuals"],
    "resources": ["schedule", "timesheets"],
    "schedule": ["schedule", "baseline", "status"],
    "risk": ["status", "baseline"],
    "benefits": ["benefits", "eac", "actuals"],
    "governance": ["status", "baseline", "schedule", "timesheets"],
}


def has(key):
    return f"{PX}Has {LABEL[key]}"


def count(key):
    return f"{PX}{LABEL[key]} Projects"


def ratio(key):
    return f"{PX}{LABEL[key]} Coverage"


def ratio_colour(key):
    return f"{PX}{LABEL[key]} Coverage Colour"


def strip(chapter):
    return f"{PX}Strip {chapter}"


def strip_colour(chapter):
    return f"{PX}Strip Colour {chapter}"


HEADLINE = PX + "Headline"
GAPS = PX + "Gaps"
GAP_COUNT = PX + "Gap Count"
GAP_COLOUR = PX + "Gap Colour"
LIFETIME_ACTUAL = PX + "Actual Cost (lifetime)"
COMPLETE = PX + "Complete Projects"

add(LIFETIME_ACTUAL, D, LIFE_ACTUAL, "€#,##0;-€#,##0;€0", FOLDER, "Actual cost of the project plan, all years.")
for k, lbl, _s, cond in CHECKS:
    add(has(k), I, f"IF ( HASONEVALUE ( DimProject[Id] ), IF ( {cond}, 1, 0 ) )", "0", FOLDER,
        f"1 when the project has: {lbl}.")
    add(count(k), I, f"SUMX ( {ACTIVE_IDS}, [{has(k)}] ) + 0", "#,##0", FOLDER,
        f"Active projects that have: {lbl}.")
    add(ratio(k), T, f'''
VAR _c = [{count(k)}]
VAR _n = [Story | Active Projects]
RETURN FORMAT ( _c, "0" ) & " of " & FORMAT ( _n, "0" ) & IF ( _n > 0, "  (" & FORMAT ( DIVIDE ( _c, _n ), "0%" ) & ")" )''',
        folder=FOLDER, desc=f"Active projects that have: {lbl}, as 'x of N (p%)'.")
    add(ratio_colour(k), T, f'IF ( DIVIDE ( [{count(k)}], [Story | Active Projects] ) >= {COVERED}, "{pbir.TEAL}", "#854F0B" )',
        folder=FOLDER)

_gap_parts = " & ".join(f'IF ( [{has(k)}] = 0, "✗ {lbl}  " )' for k, lbl, _s, _c in CHECKS)
add(GAP_COUNT, I, "IF ( HASONEVALUE ( DimProject[Id] ), " + " + ".join(f"( 1 - [{has(k)}] )" for k, *_ in CHECKS) + " )",
    "0", FOLDER, "Sources missing for the project (0 = every source in place).")
add(GAPS, T, f"""
IF ( HASONEVALUE ( DimProject[Id] ),
    VAR _g = TRIM ( {_gap_parts} )
    RETURN IF ( _g = "", "✓ every source in place", _g )
)""", folder=FOLDER, desc="The sources the project is missing, to send to its manager.")
add(GAP_COLOUR, T, f'IF ( [{GAP_COUNT}] > 0, "{pbir.RED}", "{pbir.TEAL}" )', folder=FOLDER)
add(COMPLETE, I, f"COUNTROWS ( FILTER ( {ACTIVE_IDS}, [{GAP_COUNT}] = 0 ) ) + 0", "#,##0", FOLDER,
    "Active projects with every source in place.")

# headline: complete projects and the weakest source
_vars = "\n".join(f"VAR _{k} = [{count(k)}]" for k, *_ in CHECKS)
_min = "MIN ( " * (len(CHECKS) - 1) + f"_{CHECKS[0][0]}, " + ", ".join(
    f"_{k} )" for k, *_ in CHECKS[1:])
_weak = "SWITCH ( TRUE (), " + ", ".join(f'_{k} = _min, "{lbl}"' for k, lbl, *_ in CHECKS) + ' )'
add(HEADLINE, T, f"""
{_vars}
VAR _n = [Story | Active Projects]
VAR _ok = [{COMPLETE}]
VAR _min = {_min}
RETURN
    SWITCH ( TRUE (),
        COALESCE ( _n, 0 ) = 0, "No active project in the current selection.",
        _ok = _n, "All " & FORMAT ( _n, "0" ) & " active projects have every source in place: the story's numbers cover the whole portfolio.",
        FORMAT ( _ok, "0" ) & " of " & FORMAT ( _n, "0" ) & IF ( _n = 1, " active project has", " active projects have" )
            & " every source in place. Weakest source: " & {_weak} & " (" & FORMAT ( _min, "0" ) & " of " & FORMAT ( _n, "0" ) & ")"
            & IF ( DIVIDE ( _min, _n ) >= {COVERED}, ", still above the {COVERED:.0%} bar. Close the remaining gaps per project below.",
                " — every number built on it covers only part of the portfolio. Fix that source first." )
    )""", folder="Story\\Headlines", desc="Reconciliation headline: complete projects and the weakest source.")

# strip per chapter
for ch, keys in CHAPTER_CHECKS.items():
    vars_ = "\n".join(f"VAR _{k} = [{count(k)}]" for k in keys)
    items = ' & "   ·   " & '.join(
        f'IF ( DIVIDE ( _{k}, _n ) >= {COVERED}, "✓ ", "⚠ " ) & "{SHORT[k]} " & FORMAT ( _{k}, "0" ) & "/" & FORMAT ( _n, "0" )'
        for k in keys).replace('"   ·   "', '"  ·  "')
    ok = " && ".join(f"DIVIDE ( _{k}, _n ) >= {COVERED}" for k in keys)
    add(strip(ch), T, f"""
{vars_}
VAR _n = [Story | Active Projects]
RETURN
    IF ( COALESCE ( _n, 0 ) = 0, "Data confidence: no active project in view",
        IF ( {ok}, "Data confidence ✓   ", "Data confidence ⚠   " ) & {items} )""", folder=FOLDER,
        desc=f"Coverage of the sources the {ch} chapter stands on (✓ when {COVERED:.0%} of active projects have it).")
    add(strip_colour(ch), T, f"""
{vars_}
VAR _n = [Story | Active Projects]
RETURN IF ( {ok}, "{pbir.TEAL}", "#854F0B" )""", folder=FOLDER)

for name in [LIFETIME_ACTUAL, GAP_COUNT, GAPS, GAP_COLOUR, COMPLETE, HEADLINE] + [has(k) for k, *_ in CHECKS] \
        + [count(k) for k, *_ in CHECKS] + [ratio(k) for k, *_ in CHECKS] + [ratio_colour(k) for k, *_ in CHECKS] \
        + [strip(c) for c in CHAPTER_CHECKS] + [strip_colour(c) for c in CHAPTER_CHECKS]:
    pbir.EXTENSION_MEASURES.add(name)
