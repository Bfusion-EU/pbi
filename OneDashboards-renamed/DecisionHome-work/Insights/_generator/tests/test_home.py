import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
from story_measures import MEASURES  # noqa: E402

NAMES = {m["name"] for m in MEASURES}
SUBJECTS = ["Financials", "Schedule", "Resources", "Risk", "Portfolio", "Benefits", "Status", "Governance"]
HOME = (["Greeting", "Refreshed", "Briefing", "Briefing Reasons", "Act Score", "Act Reason", "Act Colour", "Act Count",
         "EAC Var % (reports)", "On Track % (reports)", "EAC Change", "On Track Change", "Due",
         "Colour Financials", "Colour Util", "Colour Trust", "Colour Portfolio", "Colour Schedule", "Colour Risk",
         "Colour Benefits", "Colour Status"]
        + [f"Insight {s}" for s in SUBJECTS] + [f"Pill {s}" for s in SUBJECTS] + [f"Pill Fill {s}" for s in SUBJECTS])


REMOVED = ([f"Line {s}" for s in ["Portfolio", "Financials", "Resources", "Schedule", "Risk", "Benefits", "Timesheets",
                                  "Governance"]] + [f"Answer {a}" for a in ["Finance", "Schedule", "Resources", "Benefits"]]
           + ["Colour Timesheets"])


def test_removed_measures_gone():
    assert [n for n in REMOVED if f"Story | Home · {n}" in NAMES] == []


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
    assert len(children) > 15


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


def test_financials_and_status_cards_use_their_own_measures():
    spec = {s[0]: s for s in ext_home.SUBJECTS_LAYOUT}
    assert spec["fin"][3] == "Story | Projects Over Budget"
    assert spec["fin"][7] == ext_home.hm("Colour Financials")
    assert ext_home.SUBJECT_COLOUR["Financials"] == ext_home.hm("Colour Financials")
    assert spec["sr"][3] == "Story | Status · Not Reporting"
    assert "not reporting" in spec["sr"][4]


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


def test_children_belong_to_the_right_group():
    pg = _home()
    gid = {vc["visualGroup"]["displayName"]: vc["name"] for vc in pg.visuals if "visualGroup" in vc}
    pmo = [("act_bg", "shape"), ("act_title", "textbox"), ("act_tbl", "tableEx"), ("act_drill", "actionButton"),
           ("next_title", "textbox"), ("next_tbl", "tableEx"), ("view_pill_pmo", "shape")]
    exe = ([(f"dec_bg{k}", "shape") for k in range(3)] + [(f"dec_go{k}", "actionButton") for k in range(3)]
           + [("view_pill_exec", "shape")])
    for key, vt in pmo:
        assert _vc(pg, key, vt).get("parentGroupName") == gid["PMO view"], key
    for key, vt in exe:
        assert _vc(pg, key, vt).get("parentGroupName") == gid["Executive view"], key


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


@pytest.fixture(autouse=True)
def _clear_bookmarks():
    pbir.BOOKMARKS.clear()
    yield
    pbir.BOOKMARKS.clear()


def test_z_order_background_groups_buttons():
    pg = _home()
    z = {vc["name"]: vc["position"]["z"] for vc in pg.visuals}
    bg = z[_name(pg, "switch_bg", "shape")]
    groups = [z[_name(pg, "grp_pmo", "group")], z[_name(pg, "grp_exec", "group")]]
    buttons = [z[_name(pg, "switch0", "actionButton")], z[_name(pg, "switch1", "actionButton")]]
    assert bg < min(groups)
    assert max(groups) < min(buttons)


def test_briefing_breaks_down_act_count():
    expr = next(m["expression"] for m in MEASURES if m["name"] == "Story | Home · Briefing Reasons")
    for k in (100, 90, 80, 60, 50, 40):
        assert f"[Story | Home · Act Score] = {k}" in expr


def test_value_and_text_cells():
    v = ext_home.value_cell("Story | Active Projects", size=28)
    t = ext_home.text_cell("Story | Home · Greeting", size=11)
    assert v["visualType"] == ext_home.VALUE_VISUAL
    assert t["visualType"] == ext_home.VALUE_VISUAL
    for vis in (v, t):
        roles = vis["query"]["queryState"]
        projs = [p for r in roles.values() for p in r["projections"]]
        assert len(projs) == 1  # exactly one measure, nothing else


def test_branding_present():
    pg = _home()
    word = _vc(pg, "brand_word", "textbox")
    assert word is not None
    assert "BFUSION" in repr(word["visual"]["objects"]["general"])
    assert all(_vc(pg, f"brand_bar{k}", "shape") is not None for k in range(5))
    logo = _vc(pg, "oneplan_logo", "image")
    assert logo is not None and "OnePlan_logo" in repr(logo["visual"]["objects"]["image"])
    sub = _vc(pg, "brand_sub", "textbox")
    assert "Command center" in repr(sub["visual"]["objects"]["general"])
    # logo: bottom-right corner of the right-column panel, above the groups, not in a group
    pos = logo["position"]
    assert (pos["x"], pos["y"], pos["width"], pos["height"]) == (1646, 924, 110, 48)
    assert "parentGroupName" not in logo
    assert pos["z"] > max(vc["position"]["z"] for vc in pg.visuals if vc.get("parentGroupName"))
    assert logo["visual"]["objects"]["image"][0]["properties"]["sourceFile"]["image"]["scaling"]["expr"]["Literal"][
        "Value"] == "'Fit'"
    greet = _vc(pg, "greet", "card")["position"]
    assert greet["x"] >= 500


def test_footer_chips_wide_enough_for_their_text():
    pg = _home()
    for spec in ext_home.SUBJECTS_LAYOUT:
        c, footer = spec[0], spec[-1]
        labels, size, widths = ext_home.chip_layout(footer)
        edge = None
        for j, (label, w) in enumerate(zip(labels, widths)):
            vc = _vc(pg, f"card_{c}_ft{j}", "actionButton")
            pos = vc["position"]
            assert pos["width"] >= ext_home.chip_text_w(label, size) + 8, (c, label)
            if edge is not None:
                assert pos["x"] - edge >= ext_home.CHIP_GAP - 0.01, (c, label)   # 10 px gap, no overlap
            edge = pos["x"] + pos["width"]
        card = _vc(pg, f"card_{c}_bg", "shape")["position"]
        assert edge <= card["x"] + card["width"] - 16 + 0.01, c


def test_progress_bars_are_one_stacked_chart():
    pg = _home()
    for c in ("res", "port", "gov"):
        bar = _vc(pg, f"card_{c}_bar", "barChart")
        assert bar is not None, c
        assert _vc(pg, f"card_{c}_bar_track", "shape") is None, c      # no separate track shape
        proj = bar["visual"]["query"]["queryState"]["Y"]["projections"]
        assert len(proj) == 2 and "Rest" in repr(proj[1]), c           # value + remainder
        assert bar["position"]["height"] >= 100                        # Desktop placeholder below ~100 px
    names = {m["name"] for m in MEASURES}
    assert {f"Story | Home · {n}" for n in ("Util Rest", "Aligned Rest", "Trust Rest")} <= names


def test_cells_have_service_headroom():
    """The Service renders text taller than Desktop; every value/text cell needs >= 28 px over its text height."""
    pg = _home()
    pts = {"num": 34, "sent": 13 * 4}   # sentence: 4 lines in the Service
    for c in CARD_KEYS:
        for part, size in pts.items():
            vc = _vc(pg, f"card_{c}_{part}", ext_home.VALUE_VISUAL)
            assert vc["position"]["height"] >= size * 1.33 + 22 + 28, (c, part)
    # header row ~22 px; the sentence cell may sit under the spark / bar (they are drawn on top of it)
    # rows stay inside the card
    r = ext_home
    assert r.R_SENT + r.SENT_H <= r.R_RULE
