import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
from story_measures import MEASURES  # noqa: E402

NAMES = {m["name"]: m for m in MEASURES}
MOM = ["This Month End", "Month Label", "Previous Month Label", "Health Then", "Health Now", "Health Move",
       "Health Change", "Health Change Colour", "Finish Shift (d)", "Forecast Then", "Forecast Delta",
       "Forecast Moved", "Risks Delta", "State Then", "State Now", "State Change", "Is New", "Comparable",
       "Change Size", "Worsened", "Improved", "Dates Moved", "Net Days", "Dates KPI", "Forecast Net", "Risks Net",
       "New", "Closed", "New Closed KPI", "Not Comparable", "Changed Projects", "Has Previous Month", "Headline",
       "L · Health Change", "L · Finish Shift (d)", "L · Forecast Delta", "L · Risks Delta", "L · State Change",
       "L · Size"]


def test_mom_measures_registered():
    missing = [n for n in MOM if f"Story | Status · MoM {n}" not in NAMES]
    assert missing == []


def test_mom_reads_month_end_snapshots():
    expr = NAMES["Story | Status · MoM Health Now"]["expression"]
    assert "EOMONTH" in expr and "<= _te" in expr          # latest report on or before this month's end
    assert "REMOVEFILTERS ()" in NAMES["Story | Status · MoM This Month End"]["expression"]


def test_mom_thresholds_in_change_size():
    expr = NAMES["Story | Status · MoM Change Size"]["expression"]
    assert "> 30" in expr and ">= 7" in expr and "0.05" in expr


SLIP = ["Pace Gap (pt)", "Behind Pace", "Milestone At Risk", "Milestone Text", "Late Tasks Rising", "Late Tasks Text",
        "Finish Slipping", "Signals", "Flag", "Flag Text", "Reason", "Projects"]


def test_slip_measures_registered():
    missing = [n for n in SLIP if f"Story | Slip · {n}" not in NAMES]
    assert missing == []


def test_slip_flag_rule():
    expr = NAMES["Story | Slip · Flag"]["expression"]
    assert ">= 2" in expr and "[Story | Project · Overdue Tasks] > 10" in expr and '"Active"' in expr


def test_slip_pace_uses_percent_0_100():
    assert "/ 100" in NAMES["Story | Slip · Pace Gap (pt)"]["expression"]
