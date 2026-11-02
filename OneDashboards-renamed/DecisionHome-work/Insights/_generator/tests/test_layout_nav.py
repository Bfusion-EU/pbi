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


def test_act_first_bands_do_not_overlap():
    for k in STANDARD:
        pg = page(k)
        tops = sorted((v["position"]["y"], v["position"]["y"] + v["position"]["height"])
                      for v in pg.visuals if not v.get("parentGroupName") and pages.Y2 <= v["position"]["y"] < pages.YNEXT)
        assert all(bottom <= pages.YNEXT for _, bottom in tops), k
        s2, s3, s4 = sec(pg, 2), sec(pg, 3), sec(pg, 4)
        for upper, lower in ((s4, s2), (s2, s3)):
            band_bottom = max(b for t, b in tops if upper["position"]["y"] <= t < lower["position"]["y"])
            assert band_bottom <= lower["position"]["y"], k


def test_excluded_pages_keep_their_order():
    for k in ("lifecycle", "tsstatus", "status"):
        pg = page(k)
        assert sec(pg, 2)["position"]["y"] < sec(pg, 3)["position"]["y"] < sec(pg, 4)["position"]["y"], k
