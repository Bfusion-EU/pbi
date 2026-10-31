import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
from story_measures import MEASURES  # noqa: E402

NAMES = {m["name"] for m in MEASURES}
HOME = ["Greeting", "Briefing", "Act Score", "Act Reason", "Act Colour", "Act Count", "EAC Var % (reports)",
        "On Track % (reports)", "EAC Change", "On Track Change", "Refreshed", "Colour EAC", "Colour Util", "Colour Trust",
        "Line Portfolio", "Line Financials", "Line Resources", "Line Schedule", "Line Risk", "Line Benefits",
        "Line Timesheets", "Line Governance", "Colour Portfolio", "Colour Schedule", "Colour Risk",
        "Colour Benefits", "Colour Timesheets", "Answer Finance", "Answer Schedule", "Answer Resources",
        "Answer Benefits", "Due In 30d", "Due"]


def test_home_measures_registered():
    missing = [n for n in HOME if f"Story | Home · {n}" not in NAMES]
    assert missing == []


import pbir  # noqa: E402
import ext_home  # noqa: E402


def _home():
    return ext_home.build()[0]


def _links(pg):
    out = []
    for vc in pg.visuals:
        v = vc.get("visual", {})
        for l in v.get("visualContainerObjects", {}).get("visualLink", []):
            out.append(l["properties"])
    return out


def test_home_page_identity_and_size():
    pg = _home()
    assert pg.id == pages.PID["home"]
    assert (pg.width, pg.height) == (1800, 1000)


def test_rail_reaches_every_chapter():
    targets = {p.get("navigationSection", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
               for p in _links(_home())}
    chapters = ["exec", "portfolio", "finance", "resources", "schedule", "risk", "benefits", "governance"]
    assert all(pages.PID[k] in targets for k in chapters)


def test_everything_inside_page():
    pg = _home()
    for vc in pg.visuals:
        p = vc["position"]
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["width"] <= 1800.5 and p["y"] + p["height"] <= 1000.5, vc["name"]


def _name(pg, key, vtype):
    return pbir.uid(pg.id, key, vtype)


def test_rail_buttons_target_their_pages():
    pg = _home()
    by_name = {vc["name"]: vc for vc in pg.visuals}
    rail = [(icon, target) for icon, target, _ in ext_home.RAIL if target != "home"]
    assert len(rail) == 8
    for icon, target in rail:
        vc = by_name[_name(pg, f"rail_btn_{icon}", "actionButton")]
        link = vc["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
        assert link["navigationSection"]["expr"]["Literal"]["Value"].strip("'") == pages.PID[target]
    assert sum(1 for vc in pg.visuals if vc.get("visual", {}).get("visualType") == "actionButton"
               and vc["name"] in {_name(pg, f"rail_btn_{i}", "actionButton") for i, _ in rail}) == 8


def test_build_all_has_single_ext_home_page():
    built = [p for p in pages.build_all() if p.id == pages.PID["home"]]
    assert len(built) == 1
    assert _name(built[0], "rail_bg", "shape") in {vc["name"] for vc in built[0].visuals}


def test_home_slicers_sync():
    sl = [vc for vc in _home().visuals if vc.get("visual", {}).get("visualType") == "slicer"]
    assert len(sl) == 2
    assert all("syncGroup" in vc["visual"] for vc in sl)


def test_body_area_fits():
    assert ext_home.BODY_Y >= 388 + 12 and ext_home.BODY_Y + 588 <= 988


def _bm(name):
    return next(bm for bm in pbir.BOOKMARKS if bm["displayName"] == name)


def _hidden(bm):
    sec = next(iter(bm["explorationState"]["sections"].values()))
    return {g: v["isHidden"] for g, v in sec["visualContainerGroups"].items()}


def test_two_view_groups_and_bookmarks():
    pbir.BOOKMARKS.clear()
    pg = _home()
    groups = {vc["visualGroup"]["displayName"]: vc for vc in pg.visuals if "visualGroup" in vc}
    assert set(groups) == {"PMO view", "Executive view"}
    assert groups["Executive view"].get("isHidden") is True
    assert not groups["PMO view"].get("isHidden")
    assert {bm["displayName"] for bm in pbir.BOOKMARKS} == {"Home · PMO view", "Home · Executive view"}
    children = [vc for vc in pg.visuals if vc.get("parentGroupName")]
    assert len(children) > 20


VTYPES = ("shape", "textbox", "tableEx", "actionButton", "card", "lineChart", "clusteredBarChart", "image", "slicer")


def _parent(pg, key):
    """parentGroupName of the visual added with `key` (None = top level); fails if no such visual."""
    by = {vc["name"]: vc for vc in pg.visuals}
    hits = [by[pbir.uid(pg.id, key, t)] for t in VTYPES if pbir.uid(pg.id, key, t) in by]
    assert len(hits) == 1, key
    return hits[0].get("parentGroupName")


def test_children_belong_to_the_right_group():
    pbir.BOOKMARKS.clear()
    pg = _home()
    pmo, ex = (pbir.uid(pg.id, k, "group") for k in ("grp_pmo", "grp_exec"))
    for k in ["act_bg", "act_title", "act_tbl", "act_drill", "act_hint", "next_title", "next_tbl", "area_bg0",
              "area_lbl7", "area_stripe3", "area_line5", "area_link0_0", "view_pill_pmo"]:
        assert _parent(pg, k) == pmo, k
    for k in ["dec_bg0", "dec_bg2", "dec_stripe1", "dec0", "dec_go1", "ans_bg3", "ans_q2", "ans3", "ans_go0",
              "view_pill_exec"]:
        assert _parent(pg, k) == ex, k
    # switch buttons and the briefing link stay on top level
    for k in ("switch0", "switch1", "brief_link"):
        assert _parent(pg, k) is None, k


def test_bookmarks_hide_the_other_view():
    pbir.BOOKMARKS.clear()
    pg = _home()
    pmo_g, ex_g = (pbir.uid(pg.id, k, "group") for k in ("grp_pmo", "grp_exec"))
    assert _hidden(_bm("Home · PMO view")) == {pmo_g: False, ex_g: True}
    assert _hidden(_bm("Home · Executive view")) == {pmo_g: True, ex_g: False}
    for bm in pbir.BOOKMARKS:
        assert bm["options"]["suppressData"] is True


def _bookmark_target(vc):
    link = vc["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
    assert link["type"]["expr"]["Literal"]["Value"].strip("'") == "Bookmark"
    return link["bookmark"]["expr"]["Literal"]["Value"].strip("'")


def test_switch_buttons_target_their_bookmark():
    pbir.BOOKMARKS.clear()
    pg = _home()
    by = {vc["name"]: vc for vc in pg.visuals}
    assert _bookmark_target(by[pbir.uid(pg.id, "switch0", "actionButton")]) == _bm("Home · PMO view")["name"]
    assert _bookmark_target(by[pbir.uid(pg.id, "switch1", "actionButton")]) == _bm("Home · Executive view")["name"]
    assert _bookmark_target(by[pbir.uid(pg.id, "brief_link", "actionButton")]) == _bm("Home · PMO view")["name"]


def test_next30_due_is_a_short_date_measure():
    m = next(m for m in MEASURES if m["name"] == "Story | Home · Due")
    assert m["dataType"] == "DateTime" and m["formatString"] == "dd mmm yyyy"
    pg = _home()
    tbl = next(vc for vc in pg.visuals if vc["name"] == pbir.uid(pg.id, "next_tbl", "tableEx"))
    assert "EndDate" not in repr(tbl["visual"]["query"]["queryState"])
    assert "Home · Due" in repr(tbl["visual"]["query"]["queryState"])


def test_all_pages_reachable_from_home():
    pg = _home()
    targets = set()
    for p in _links(pg):
        for key in ("navigationSection", "drillthroughSection"):
            if key in p:
                targets.add(p[key]["expr"]["Literal"]["Value"].strip("'"))
    story = [k for k, _ in pages.PAGES if k != "home"]
    missing = [k for k in story if pages.PID[k] not in targets]
    assert missing == [], missing
    assert pages.PID["project"] in targets  # drill-through to the One-Pager twin


def test_briefing_link_targets_pmo_bookmark():
    pbir.BOOKMARKS.clear()
    pg = _home()
    pmo = next(bm for bm in pbir.BOOKMARKS if bm["displayName"] == "Home · PMO view")["name"]
    hits = [p for p in _links(pg) if p.get("bookmark", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'") == pmo]
    # one switch button + one briefing link point at the PMO bookmark
    assert len(hits) == 2
