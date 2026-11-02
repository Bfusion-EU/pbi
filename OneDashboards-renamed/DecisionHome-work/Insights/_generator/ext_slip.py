"""May slip — an explainable early warning for active projects (Act now on Home, ledger on page 5c).

A project MAY SLIP when at least 2 of the 4 signals below are true, or when it has more than OVERDUE_MAX overdue tasks
(the old 'overdue work' Act-now rule, folded in so no project drops out of Act now). Missing data makes a signal false,
never true. Spec: BFusion-Apps docs/superpowers/specs/2026-11-02-insights-what-changed-design.md
"""
import ext_status
from story_measures import add, T, D, I

PFX = "Story | Slip · "
FOLDER = "Story\\Slip"
PACE_GAP_PT = 15            # S1: time elapsed % minus % complete, in points
MS_DAYS, MS_DONE = 30, 50   # S2: open milestone due within MS_DAYS days and under MS_DONE % done
OVERDUE_MAX = 10            # flag on its own above this many overdue tasks
ONE = "( HASONEVALUE ( DimProject[Id] ) && NOT ISBLANK ( SELECTEDVALUE ( DimProject[Id] ) ) )"
MS = (f"KEEPFILTERS ( DimTask[Milestone] = TRUE () ), KEEPFILTERS ( DimTask[PercentDone] < {MS_DONE} ), "
      f"KEEPFILTERS ( DimTask[EndDate] >= TODAY () && DimTask[EndDate] <= TODAY () + {MS_DAYS} ), "
      "KEEPFILTERS ( NOT ISBLANK ( DimTask[ProjectKey] ) )")
END = ext_status.END


def s(name):
    return PFX + name


def r(name):
    return f"[{PFX}{name}]"


# S1 behind pace (current plan dates and % done on DimProject; % done is 0-100)
add(s("Pace Gap (pt)"), D, f"""
IF ( {ONE},
    VAR _s = MAX ( DimProject[Summary_StartDate] )
    VAR _e = MAX ( DimProject[Summary_EndDate] )
    VAR _d = MAX ( DimProject[Summary_PercentDone] )
    VAR _el = IF ( NOT ISBLANK ( _s ) && NOT ISBLANK ( _e ) && _e > _s,
        MIN ( 1, MAX ( 0, DIVIDE ( TODAY () - _s, _e - _s ) ) ) )
    RETURN IF ( NOT ISBLANK ( _el ) && NOT ISBLANK ( _d ), ( _el - _d / 100 ) * 100 ) )""", "+0;-0;0", FOLDER,
    "Share of the plan's time already used minus % complete, in points. Positive = behind pace.")
add(s("Behind Pace"), I, f"IF ( {ONE}, IF ( {r('Pace Gap (pt)')} > {PACE_GAP_PT}, 1, 0 ) )", "0", FOLDER,
    f"S1: 1 when the project is more than {PACE_GAP_PT} points behind pace.")

# S2 milestone at risk
add(s("Milestone At Risk"), I, f"IF ( {ONE}, IF ( CALCULATE ( COUNTROWS ( DimTask ), {MS} ) > 0, 1, 0 ) )", "0",
    FOLDER, f"S2: 1 when an open milestone is due within {MS_DAYS} days and is under {MS_DONE}% done.")
add(s("Milestone Text"), T, f"""
IF ( {ONE},
    VAR _t = TOPN ( 1, CALCULATETABLE ( DimTask, {MS} ), DimTask[EndDate], ASC, DimTask[Name], ASC, DimTask[TaskKey], ASC )
    VAR _nm = MAXX ( _t, DimTask[Name] )
    RETURN IF ( NOT ISBLANK ( _nm ),
        "milestone " & _nm & " in " & FORMAT ( INT ( MAXX ( _t, DimTask[EndDate] ) ) - INT ( TODAY () ), "0" )
            & " d (" & FORMAT ( MAXX ( _t, DimTask[PercentDone] ), "0" ) & "% done)" ) )""", folder=FOLDER)

# S3 late tasks rising: latest status report versus the one before it (5c previous-report rule)
_LATE = "MAX ( FactStatusReport[NoofLateTasks] )"
_S3 = f"""
    VAR _cur = CALCULATE ( MAX ( {END} ), REMOVEFILTERS ( DimDate ) )
    VAR _prev = {ext_status.prev_end()}
    VAR _ln = IF ( NOT ISBLANK ( _cur ), {ext_status.at(_LATE, "_cur")} )
    VAR _lp = IF ( NOT ISBLANK ( _prev ), {ext_status.at(_LATE, "_prev")} )"""
add(s("Late Tasks Rising"), I, f"""
IF ( {ONE},{_S3}
    RETURN IF ( NOT ISBLANK ( _ln ) && NOT ISBLANK ( _lp ) && _ln > _lp
        && _cur >= TODAY () - 2 * {ext_status.STALE_DAYS}, 1, 0 ) )""", "0", FOLDER,
    "S3: 1 when the latest status report counts more late tasks than the report before it.")
add(s("Late Tasks Text"), T, f"""
IF ( {ONE},{_S3}
    RETURN IF ( NOT ISBLANK ( _ln ) && NOT ISBLANK ( _lp ),
        "late tasks " & FORMAT ( _lp, "0" ) & " → " & FORMAT ( _ln, "0" ) ) )""", folder=FOLDER)

# S4 finish date slipping since last month (page 5c month snapshots)
add(s("Finish Slipping"), I, f"""
IF ( {ONE}, IF ( CALCULATE ( [Story | Status · MoM Finish Shift (d)], REMOVEFILTERS ( DimDate ) ) >= {ext_status.DATE_MOVE_D}, 1, 0 ) )""", "0", FOLDER,
    f"S4: 1 when the finish date moved {ext_status.DATE_MOVE_D}+ days later since last month.")

add(s("Signals"), I, f"""
IF ( {ONE}, COALESCE ( {r("Behind Pace")}, 0 ) + COALESCE ( {r("Milestone At Risk")}, 0 )
    + COALESCE ( {r("Late Tasks Rising")}, 0 ) + COALESCE ( {r("Finish Slipping")}, 0 ) )""", "0", FOLDER,
    "How many of the four slip signals are true (0-4).")
add(s("Flag"), I, f"""
IF ( {ONE} && SELECTEDVALUE ( DimProject[State_Value] ) = "Active",
    IF ( {r("Signals")} >= 2 || [Story | Project · Overdue Tasks] > {OVERDUE_MAX}, 1 ) )""", "0", FOLDER,
    f"1 for an active project with 2+ slip signals or more than {OVERDUE_MAX} overdue tasks; blank otherwise.")
add(s("Flag Text"), T, f'IF ( {r("Flag")} = 1, "✓" )', folder=FOLDER)
add(s("Reason"), T, f"""
IF ( {r("Flag")} = 1,
    VAR _t =
        IF ( {r("Behind Pace")} = 1, ", " & FORMAT ( {r("Pace Gap (pt)")}, "0" ) & " pt behind pace" )
            & IF ( {r("Milestone At Risk")} = 1, ", " & {r("Milestone Text")} )
            & IF ( {r("Late Tasks Rising")} = 1, ", " & {r("Late Tasks Text")} )
            & IF ( {r("Finish Slipping")} = 1,
                ", finish " & FORMAT ( CALCULATE ( [Story | Status · MoM Finish Shift (d)], REMOVEFILTERS ( DimDate ) ), "+0" ) & " d since last month" )
    RETURN "May slip: "
        & IF ( {r("Signals")} >= 2, MID ( _t, 3, 500 ),
            FORMAT ( [Story | Project · Overdue Tasks], "0" ) & " overdue tasks" ) )""", folder=FOLDER,
    desc="Act-now reason: the slip signals that are true, or the overdue-task count when that alone flagged it.")
add(s("Projects"), I, """
SUMX ( FILTER ( VALUES ( DimProject[Id] ), NOT ISBLANK ( DimProject[Id] ) ), IF ( [Story | Slip · Flag] = 1, 1 ) ) + 0""",
    "#,##0", FOLDER, "Active projects that may slip.")


def build():
    return []      # measures only; shown on Home (Act now) and page 5c
