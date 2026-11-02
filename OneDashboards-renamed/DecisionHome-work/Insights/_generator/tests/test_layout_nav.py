import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402
import pbir  # noqa: E402
import layout  # noqa: E402

BUILT = {pg.id: pg for pg in pages.build_all()}
STANDARD = ["portfolio", "finance", "finance2", "resources", "schedule", "risk", "benefits", "governance"]


def page(key):
    return BUILT[pages.PID[key]]


def sec(pg, n):
    return next(v for v in pg.visuals if v["name"] == pbir.uid(pg.id, f"sec{n}", "textbox"))


def sec_text(vc):
    return vc["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"]


def test_standard_pages_are_act_first():
    for k in STANDARD:
        pg = page(k)
        s2, s3, s4 = sec(pg, 2), sec(pg, 3), sec(pg, 4)
        assert s4["position"]["y"] < s2["position"]["y"] < s3["position"]["y"], k   # register first
        assert sec_text(s4).startswith("②") and sec_text(s2).startswith("③") and sec_text(s3).startswith("④"), k


def test_skip_list():
    names = dict(pages.PAGES)
    assert not any(names[k] in pages.LAYOUT_SKIPPED for k in STANDARD)
    assert names["exec"] not in pages.LAYOUT_SKIPPED            # excluded on purpose, not "skipped"


def test_status_keeps_its_ledger_first():
    pg = page("status")
    s2, s3, s4 = sec(pg, 2), sec(pg, 3), sec(pg, 4)
    assert s2["position"]["y"] < s3["position"]["y"] < s4["position"]["y"]
    assert sec_text(s2).startswith("②")
    assert dict(pages.PAGES)["status"] not in pages.LAYOUT_SKIPPED
