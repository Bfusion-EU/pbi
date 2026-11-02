"""Data-trust notes: a headline whose data covers fewer than TRUST_MIN of the active projects ends with
"ⓘ Based on N of M active projects with …". The Executive headline always ends with the governance data-trust score.
Each wrapped headline keeps its name (visuals are untouched): its text moves to "<name> · Core".
Spec: BFusion-Apps docs/superpowers/plans/2026-11-02-insights-data-trust.md
"""
from story_measures import MEASURES, add, T, I

TRUST_MIN = 0.95
FOLDER = "Story\\Trust"
ACTIVE_IDS = ('CALCULATETABLE ( FILTER ( VALUES ( DimProject[Id] ), NOT ISBLANK ( DimProject[Id] ) ), '
              'KEEPFILTERS ( DimProject[State_Value] = "Active" ) )')
FIN = "[Story | Budget At Completion] > 0 || [Story | Finance EAC] > 0"
# (area, numerator condition per project, denominator condition per project or None = all active, wording, base wording)
AREAS = [
    ("Finance", FIN, None, "with a financial plan", "active projects"),
    ("Resources", "CALCULATE ( [Story | Project Scheduled Hours], REMOVEFILTERS ( DimDate ) ) > 0", None,
     "with a resource plan", "active projects"),
    ("Schedule", 'CALCULATE ( COUNTROWS ( DimTask ), KEEPFILTERS ( DimTask[WorkType] = "Tasks" ) ) > 0', None,
     "with a work plan", "active projects"),
    ("Benefits", "[Story | Benefits At Completion] > 0", "[Story | Finance EAC] > 0", "with planned benefits",
     "active projects with an EAC"),
]
WRAP = {"Story | Finance Headline": "Finance", "Story | Pareto PnL Headline": "Finance",
        "Story | Resource Headline": "Resources", "Story | Schedule Headline": "Schedule",
        "Story | Benefits Headline": "Benefits"}


def t(name):
    return "Story | Trust · " + name


for area, num, den, words, base in AREAS:
    base_set = f"FILTER ( {ACTIVE_IDS}, {den} )" if den else ACTIVE_IDS
    add(t(f"Base {area}"), I, f"COUNTROWS ( {base_set} ) + 0", "#,##0", FOLDER,
        f"Denominator of the {area.lower()} data-trust note: {base}.")
    add(t(f"Covered {area}"), I, f"COUNTROWS ( FILTER ( {base_set}, {num} ) ) + 0", "#,##0", FOLDER,
        f"{base.capitalize()} {words}.")
    add(t(f"Note {area}"), T, f"""
VAR _n = [{t(f"Covered {area}")}]
VAR _m = [{t(f"Base {area}")}]
RETURN IF ( _m > 0 && DIVIDE ( _n, _m ) < {TRUST_MIN},
    "  ⓘ Based on " & FORMAT ( _n, "0" ) & " of " & FORMAT ( _m, "0" ) & " {base} {words} ("
        & FORMAT ( DIVIDE ( _n, _m ), "0%" ) & ")." )""", folder=FOLDER,
        desc=f"Shown after the headline only when fewer than {TRUST_MIN:.0%} of {base} are {words}.")


def _wrap(name, tail):
    m = next(x for x in MEASURES if x["name"] == name)
    m["name"] = name + " · Core"
    add(name, T, f"[{name} · Core] & {tail}", folder=m["displayFolder"], desc=m.get("description"))


for _name, _area in WRAP.items():
    _wrap(_name, f"[{t('Note ' + _area)}]")
add(t("Exec Score"), T, """
VAR _g = [PMO | Governance Score]
RETURN IF ( ISBLANK ( _g ), "", " Data trust: " & FORMAT ( _g, "0" ) & "/100." )""", folder=FOLDER,
    desc="Appended to the Executive headline: the governance data-trust score (Governance page).")
_wrap("Story | Exec Headline", f"[{t('Exec Score')}]")


def build():
    return []      # measures only
