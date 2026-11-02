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


def _names(pg):
    return {v["name"] for v in pg.visuals}


def test_breadcrumb_on_every_story_page():
    for k, _ in pages.PAGES:
        if k == "home":
            continue
        assert pbir.uid(pages.PID[k], "nav_home", "actionButton") in _names(page(k)), k


def test_chapter_strip():
    with_strip = set()
    for k, _ in pages.PAGES:
        if k == "home":
            continue
        pg = page(k)
        chap, members = layout.chapter_of(k)
        strip_names = {pbir.uid(pg.id, f"nav_strip_{m}", "actionButton") for m in members}
        strip = [v for v in pg.visuals if v["name"] in strip_names]
        if len(members) > 1:
            with_strip.add(chap)
            assert len(strip) == len(members), k
            current = [v for v in strip if "#E8612A" in json.dumps(v)]
            assert [v["name"] for v in current] == [pbir.uid(pg.id, f"nav_strip_{k}", "actionButton")], k
        else:
            assert strip == [], k
    assert with_strip == {"portfolio", "finance", "resources", "schedule"}


def test_headline_moved_below_nav_row():
    pg = page("finance")
    head = next(v for v in pg.visuals if v["name"] == pbir.uid(pg.id, "headline", "card"))
    assert head["position"]["y"] == 84 + layout.NAV_SHIFT


def test_passes_are_idempotent():
    pg = page("finance")
    before = json.dumps(pg.visuals, sort_keys=True)
    layout.act_first(pg)
    layout.nav_row(pg, "finance")
    assert json.dumps(pg.visuals, sort_keys=True) == before


def test_nothing_overlaps_nav_row():
    for k, _ in pages.PAGES:
        if k == "home":
            continue
        pg = page(k)
        top = [v for v in pg.visuals if not v.get("parentGroupName")]
        nav = [v for v in top if v["position"]["y"] == layout.NAV_Y and v["position"]["height"] == layout.NAV_H]
        assert nav, k
        names = {v["name"] for v in nav}
        for v in top:
            if v["name"] in names:
                continue
            y, h = v["position"]["y"], v["position"]["height"]
            assert y + h <= layout.NAV_Y or y >= layout.NAV_Y + layout.NAV_H, (k, v["name"], y, h)


def test_onepager_status_cards_keep_height():
    pg = page("onepager")
    cards = [v for v in pg.visuals if any(f"Project · {m}" in json.dumps(v, ensure_ascii=False)
                                           for m in ("Accomplishments", "Planned Activities", "Additional Comments"))
             and v["visual"]["visualType"] != "actionButton" and v["position"]["height"] < 400]
    cards = [v for v in cards if v["name"] in {pbir.uid(pg.id, f"sr{i}", v["visual"]["visualType"]) for i in range(3)}]
    assert len(cards) == 3
    assert all(v["position"]["height"] >= 170 for v in cards), [v["position"]["height"] for v in cards]
