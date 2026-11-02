import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
import ext_slip  # noqa: E402
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
    assert (">= 2" in expr and f"[Story | Project · Overdue Tasks] > {ext_slip.OVERDUE_MAX}" in expr
            and '"Active"' in expr)


def test_slip_pace_uses_percent_0_100():
    assert "/ 100" in NAMES["Story | Slip · Pace Gap (pt)"]["expression"]


GUARDED = [n for n in SLIP if n not in ("Projects", "Flag Text", "Reason")]


def test_slip_missing_data_is_false():
    for n in ("Pace Gap (pt)", "Late Tasks Rising", "Late Tasks Text"):
        assert "NOT ISBLANK" in NAMES[f"Story | Slip · {n}"]["expression"], n
    rising = NAMES["Story | Slip · Late Tasks Rising"]["expression"]
    assert "NOT ISBLANK ( _ln )" in rising and "NOT ISBLANK ( _lp )" in rising
    for n in GUARDED:
        assert "HASONEVALUE ( DimProject[Id] )" in NAMES[f"Story | Slip · {n}"]["expression"], n


def test_slip_reason_strips_prefix():
    expr = NAMES["Story | Slip · Reason"]["expression"]
    assert "MID ( _t, 3" in expr and "overdue tasks" in expr


def test_act_buckets_order():
    import ext_home
    assert [k for k, _ in ext_home._BUCKETS] == [100, 90, 80, 70, 50, 40]
    assert dict(ext_home._BUCKETS)[70] == "may slip"
    expr = NAMES["Story | Home · Act Score"]["expression"]
    assert "[Story | Slip · Flag] = 1, 70" in expr and "Overdue Tasks] > 10, 60" not in expr
    assert "[Story | Slip · Reason]" in NAMES["Story | Home · Act Reason"]["expression"]


def test_tip_buckets_follow_chips():
    assert pages.HOME_TIP_BUCKETS == ["off_track", "over_budget", "late", "may_slip", "not_reporting", "failing_rules"]


import json  # noqa: E402


def _status_page():
    import ext_status
    return ext_status.build()[0]


def test_status_page_is_what_changed():
    assert dict(pages.PAGES)["status"] == "5c · What Changed"
    pg = _status_page()
    pulse = [vc for vc in pg.visuals if vc.get("visual", {}).get("visualType") == "card"
             and vc["position"]["y"] == pages.Y1K]
    assert len(pulse) == 7
    ledger = [vc for vc in pg.visuals if "Story | Status · MoM L · Size" in json.dumps(vc, ensure_ascii=False)]
    assert len(ledger) == 1
    ltxt = json.dumps(ledger[0], ensure_ascii=False)
    # (a) the May-slip column is the change-gated ledger measure, not the ungated slip flag
    assert "Story | Status · MoM L · May Slip" in ltxt
    assert "Story | Slip · Flag Text" not in ltxt
    # (b) the ledger carries the REAL_PROJECTS visual filter
    assert "filterConfig" in ledger[0] and ledger[0]["filterConfig"]["filters"]
    assert "Story | Status · MoM Headline" in json.dumps(pg.visuals, ensure_ascii=False)


def test_status_page_subtitle_fits():
    # (c) the page subtitle is a textbox run that must fit on one line (pages.SUBTITLE_MAX)
    pg = _status_page()
    runs = []
    for vc in pg.visuals:
        vis = vc.get("visual", {})
        if vis.get("visualType") != "textbox":
            continue
        for general in vis["objects"]["general"]:
            for para in general["properties"]["paragraphs"]:
                runs += [r["value"] for r in para["textRuns"]]
    subs = [r for r in runs if "Report period picks the month" in r]
    assert len(subs) == 1
    assert len(subs[0]) <= pages.SUBTITLE_MAX, (len(subs[0]), pages.SUBTITLE_MAX)
