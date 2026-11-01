import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
from story_measures import MEASURES  # noqa: E402

NAMES = {m["name"] for m in MEASURES}
CHIPN = ["Off Track", "Over Budget", "Late", "Overdue Work", "Not Reporting", "Failing Rules"]
SUBJECTS = ["Financials", "Schedule", "Resources", "Risk", "Portfolio", "Benefits", "Status", "Governance"]
HOME = (["Briefing Pill", "Act Score", "Act Reason", "Act Colour", "Act Count",
         "EAC Var % (reports)", "On Track % (reports)", "EAC Change", "On Track Change", "Due",
         "Colour Financials", "Colour Util", "Colour Trust", "Colour Portfolio", "Colour Schedule", "Colour Risk",
         "Colour Benefits", "Colour Status"]
        + [f"Chip {c}" for c in CHIPN] + [f"Chip Colour {c}" for c in CHIPN]
        + [f"Insight {s}" for s in SUBJECTS] + [f"Pill {s}" for s in SUBJECTS] + [f"Pill Fill {s}" for s in SUBJECTS]
        + [f"Tip {c}" for c in CHIPN]
        + [f"Tip {t}" for t in ("Financials", "Schedule", "Resources", "Risk", "Portfolio", "Portfolio Budget",
                                "Benefits", "Status", "Status Days", "Governance")]
        + [f"Tip {t} Key" for t in ("Portfolio", "Benefits", "Status", "Governance")]
        + [f"Tip {t} {x}" for t in ("Portfolio", "Benefits", "Status", "Governance") for x in ("Sub", "More")]
        + ["Gov Failing Projects"])


REMOVED = ([f"Line {s}" for s in ["Portfolio", "Financials", "Resources", "Schedule", "Risk", "Benefits", "Timesheets",
                                  "Governance"]] + [f"Answer {a}" for a in ["Finance", "Schedule", "Resources", "Benefits"]]
           + ["Colour Timesheets", "Greeting", "Refreshed", "Briefing", "Briefing Reasons"])


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


BUCKETS = ["off track", "over budget", "late", "overdue work", "not reporting", "failing rules"]
SLUGS = [b.replace(" ", "_") for b in BUCKETS]
GROUP_NAMES = {"PMO view", "Executive view", "Act now · all"} | {f"Act now · {b}" for b in BUCKETS}
BOOKMARK_NAMES = ({"Home · PMO view", "Home · Executive view"} | {f"Home · Act now — {b}" for b in BUCKETS})


def test_view_groups_and_bookmarks():
    pbir.BOOKMARKS.clear()
    pg = _home()
    groups = {vc["visualGroup"]["displayName"]: vc for vc in pg.visuals if "visualGroup" in vc}
    assert set(groups) == GROUP_NAMES
    # default = PMO view with the full Act-now list: only the PMO panel group and act_all are visible
    assert {n for n, g in groups.items() if not g.get("isHidden")} == {"PMO view", "Act now · all"}
    assert {bm["displayName"] for bm in pbir.BOOKMARKS} == BOOKMARK_NAMES
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
    assert {round(p["y"]) for p in pos} == {100, 552}
    assert {(round(p["width"]), round(p["height"])) for p in pos} == {(297, 436)}


def test_only_right_column_is_grouped():
    pg = _home()
    groups = {vc["name"]: vc for vc in pg.visuals if "visualGroup" in vc}
    assert {g["visualGroup"]["displayName"] for g in groups.values()} == GROUP_NAMES
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
    rest = [("act_bg", "shape"), ("act_drill", "actionButton"), ("act_hint", "textbox"),
            ("next_title", "textbox"), ("next_tbl", "tableEx"), ("view_pill_pmo", "shape")]
    act_all = [("act_title", "textbox"), ("act_tbl", "tableEx")]
    exe = ([(f"dec_bg{k}", "shape") for k in range(3)] + [(f"dec_lbl{k}", "textbox") for k in range(3)]
           + [(f"dec{k}", "tableEx") for k in range(3)] + [(f"dec_go{k}", "actionButton") for k in range(3)]
           + [("view_pill_exec", "shape")])
    expect = {gid["PMO view"]: rest, gid["Act now · all"]: act_all, gid["Executive view"]: exe}
    for b, slug in zip(BUCKETS, SLUGS):
        expect[gid[f"Act now · {b}"]] = [(f"act_title_{slug}", "textbox"), (f"act_all_{slug}", "actionButton"),
                                         (f"act_tbl_{slug}", "tableEx")]
    for g, members in expect.items():
        for key, vt in members:
            assert _vc(pg, key, vt).get("parentGroupName") == g, key
        # and nothing else sits in that group
        assert len([vc for vc in pg.visuals if vc.get("parentGroupName") == g]) == len(members), g


def test_bookmarks_hide_the_other_view():
    pbir.BOOKMARKS.clear()
    pg = _home()
    g = {k: pbir.uid(pg.id, k, "group") for k in ["grp_pmo_rest", "grp_act_all", "grp_exec"]
         + [f"grp_act_{s_}" for s_ in SLUGS]}
    every = set(g.values())

    def only(*keys):
        return {name: name not in {g[k] for k in keys} for name in every}
    assert len(pbir.BOOKMARKS) == 8
    assert _hidden(_bm("Home · PMO view")) == only("grp_pmo_rest", "grp_act_all")
    assert _hidden(_bm("Home · Executive view")) == only("grp_exec")
    for b, slug in zip(BUCKETS, SLUGS):
        assert _hidden(_bm(f"Home · Act now — {b}")) == only("grp_pmo_rest", f"grp_act_{slug}"), b
    for bm in pbir.BOOKMARKS:
        assert bm["options"]["suppressData"] is True
        assert set(bm["options"]["targetVisualNames"]) == every


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
    groups = [z[_name(pg, k, "group")] for k in ["grp_pmo_rest", "grp_act_all", "grp_exec"]
              + [f"grp_act_{s_}" for s_ in SLUGS]]
    buttons = [z[_name(pg, "switch0", "actionButton")], z[_name(pg, "switch1", "actionButton")]]
    assert bg < min(groups)
    assert max(groups) < min(buttons)


def test_chips_break_down_act_count():
    exprs = [next(m["expression"] for m in MEASURES if m["name"] == f"Story | Home · Chip {c}") for c in CHIPN]
    for k, expr in zip((100, 90, 80, 60, 50, 40), exprs):
        assert f"[Story | Home · Act Score] = {k}" in expr


def test_value_and_text_cells():
    v = ext_home.value_cell("Story | Active Projects", size=28)
    t = ext_home.text_cell("Story | Home · Briefing Pill", size=11)
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
    # brand sits inside the one header band
    band = _vc(pg, "band_bg", "shape")["position"]
    for key, vt in [("brand_word", "textbox"), ("brand_sub", "textbox")] + [(f"brand_bar{k}", "shape") for k in range(5)]:
        p = _vc(pg, key, vt)["position"]
        assert band["x"] <= p["x"] and p["x"] + p["width"] <= band["x"] + band["width"], key
        assert band["y"] <= p["y"] and p["y"] + p["height"] <= band["y"] + band["height"], key


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
            # the number cell must stop above the label row (it would block the card click there), so it only keeps
            # ~10 px of headroom: 34 pt = ~45 px of text + the 1 pt header row ~ 64 px, the cell is 78
            need = size * 1.33 + 22 + (10 if part == "num" else 28)
            assert vc["position"]["height"] >= need, (c, part)
    # header row ~22 px; the sentence cell may sit under the spark / bar (they are drawn on top of it)
    # rows stay inside the card
    r = ext_home
    assert r.R_SENT + r.SENT_H <= r.R_RULE


def test_header_single_band():
    pg = _home()
    band = _vc(pg, "band_bg", "shape")["position"]
    assert (band["x"], band["y"], band["width"], band["height"]) == (104, 8, 1680, 76)
    top, bottom = band["y"], band["y"] + band["height"]
    # nothing sits in the 16 px between the band and the grid, nothing pokes out of the band
    for vc in pg.visuals:
        p = vc["position"]
        if "visualGroup" in vc or vc.get("parentGroupName") or p["y"] >= bottom:
            continue
        if vc["name"] in {_name(pg, k, "shape") for k in ("rail_bg",)} or p["x"] < 100:
            continue                                                  # the rail, left of the band
        assert p["y"] + p["height"] <= bottom + 0.01 and p["y"] >= 0, vc["name"]
        assert not (bottom < p["y"] + p["height"] and p["y"] < ext_home.GRID_Y[0]), vc["name"]
    # pill + six chip cells; each chip has an outline and a dot; greeting / refresh / strip are gone
    assert "Briefing Pill" in repr(_vc(pg, "pill", "card")["visual"]["query"])
    for k in range(6):
        assert "Chip" in repr(_vc(pg, f"chip{k}", "card")["visual"]["query"]), k
        assert _vc(pg, f"chip_bg{k}", "shape") is not None and _vc(pg, f"chip_dot{k}", "shape") is not None, k
    assert [k for k in ("greet", "refreshed", "brief", "brief_reasons") for vt in ("card", "tableEx", "textbox")
            if _vc(pg, k, vt) is not None] == []
    assert _vc(pg, "brief_bg", "shape") is None
    # chips: fit between the pill and the slicers, no overlap, wide enough for their text
    geo = ext_home.chip_geometry()
    slicer_x = min(vc["position"]["x"] for vc in pg.visuals if vc.get("visual", {}).get("visualType") == "slicer")
    for k, x, y, w in geo:
        assert w >= len("00 " + ext_home.CHIPS[k][1]) * ext_home.CH_CHAR_PX + ext_home.CH_DOT_X + ext_home.CH_DOT
        assert x >= ext_home.PILL_X + ext_home.PILL_W and x + w <= slicer_x - 8, k
    for row in (geo[:3], geo[3:]):
        assert all(b[1] - (a[1] + a[3]) >= ext_home.CH_GAP - 0.01 for a, b in zip(row, row[1:]))
    # slicers and view switch live inside the band, vertically centred on it
    for vc in pg.visuals:
        if vc.get("visual", {}).get("visualType") == "slicer" or vc["name"] in (_name(pg, "switch0", "actionButton"),):
            p = vc["position"]
            assert top <= p["y"] and p["y"] + p["height"] <= bottom
            assert abs(p["y"] + p["height"] / 2 - (top + bottom) / 2) <= 2


def test_view_groups_contain_their_pills():
    pg = _home()
    for gkey, pkey in (("grp_pmo_rest", "view_pill_pmo"), ("grp_exec", "view_pill_exec")):
        g, p = _vc(pg, gkey, "group")["position"], _vc(pg, pkey, "shape")["position"]
        px, py = g["x"] + p["x"], g["y"] + p["y"]      # group children are stored relative to the group
        assert g["x"] <= px and px + p["width"] <= g["x"] + g["width"]
        assert g["y"] <= py and py + p["height"] <= g["y"] + g["height"]


# ---------------------------------------------------------------- hover lists and click-to-filter
def _all_home_pages():
    return {pg.id: pg for pg in ext_home.build()}


def _tip_section(vc):
    t = vc["visual"]["visualContainerObjects"]["visualTooltip"][0]["properties"]
    assert t["show"] == pbir.b(True) and t["type"] == pbir.s("Canvas")
    return t["section"]["expr"]["Literal"]["Value"].strip("'")


def _tip_measures(tip):
    tbl = next(vc for vc in tip.visuals if vc["name"] == pbir.uid(tip.id, "tip_tbl", "tableEx"))
    return [pr["field"]["Measure"]["Property"] for pr in tbl["visual"]["query"]["queryState"]["Values"]["projections"]
            if "Measure" in pr["field"]], tbl


def _is_tooltip_page(pg):
    return (pg.page.get("type") == "Tooltip" and pg.page.get("visibility") == "HiddenInViewMode"
            and (pg.width, pg.height) in {(360, 260), (360, ext_home.TIP_H_LONG)} and pg.page["pageBinding"]["type"] == "Tooltip")


def test_tooltip_pages_registered_hidden():
    keys = [k for k, _ in pages.HIDDEN_PAGES if k.startswith("tip_home_")]
    assert len(keys) == 1 + 6 + 8
    assert len({pages.PID[k] for k in keys}) == 15
    built = _all_home_pages()
    for k in keys:
        assert pages.PID[k] in built, k
        assert _is_tooltip_page(built[pages.PID[k]]), k
    # the tooltip pages come out of build_all() too, and none of them is in the story flow
    ids = {p.id for p in pages.build_all()}
    assert {pages.PID[k] for k in keys} <= ids
    assert not {k for k, _ in pages.PAGES} & set(keys)


def test_pill_chips_and_numbers_point_to_their_tooltip_page():
    built = _all_home_pages()
    pg = built[pages.PID["home"]]
    assert _tip_section(_vc(pg, "pill", "card")) == pages.PID["tip_home_act"]
    for k, slug in enumerate(SLUGS):
        assert _tip_section(_vc(pg, f"chip{k}", "card")) == pages.PID[f"tip_home_{slug}"], slug
    for c in CARD_KEYS:
        assert _tip_section(_vc(pg, f"card_{c}_num", ext_home.VALUE_VISUAL)) == pages.PID[f"tip_home_{c}"], c
    for sec in [pages.PID["tip_home_act"]] + [pages.PID[f"tip_home_{x}"] for x in SLUGS + CARD_KEYS]:
        assert _is_tooltip_page(built[sec])
        want = ext_home.TIP_H_LONG if sec in {pages.PID[f"tip_home_{x}"] for x in ext_home.LONG_TIPS} else 260
        assert built[sec].height == want, sec


def test_each_tooltip_table_uses_its_own_blank_unless_measure():
    built = _all_home_pages()
    act, _ = _tip_measures(built[pages.PID["tip_home_act"]])
    assert act[0] == "Story | Home · Act Reason"
    for slug, nm in zip(SLUGS, CHIPN):
        ms, tbl = _tip_measures(built[pages.PID[f"tip_home_{slug}"]])
        assert ms == [f"Story | Home · Tip {nm}"], slug
        assert all("Measure" not in f["field"] for f in tbl.get("filterConfig", {}).get("filters", []))
    own = {"fin": "Tip Financials", "sch": "Tip Schedule", "res": "Tip Resources", "risk": "Tip Risk",
           "port": "Tip Portfolio", "ben": "Tip Benefits", "sr": "Tip Status", "gov": "Tip Governance"}
    for c, m in own.items():
        ms, tbl = _tip_measures(built[pages.PID[f"tip_home_{c}"]])
        assert ms and all(x.startswith("Story | Home · Tip ") for x in ms), c       # only blank-unless measures
        assert f"Story | Home · {m}" in ms, c
        # never a visual measure filter (rendered an empty table in Desktop)
        assert all("Measure" not in f["field"] for f in tbl.get("filterConfig", {}).get("filters", [])), c
    # each bucket measure is blank unless the Act score is that bucket's
    for k, nm in zip((100, 90, 80, 60, 50, 40), CHIPN):
        expr = next(m["expression"] for m in MEASURES if m["name"] == f"Story | Home · Tip {nm}")
        assert f"[Story | Home · Act Score] = {k}" in expr and expr.strip().startswith("IF"), nm


def _overlap(a, b):
    return (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
            and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"])


def test_tooltip_visuals_sit_above_ghost_links():
    pg = _home()
    for c in CARD_KEYS:
        num, go = _vc(pg, f"card_{c}_num", ext_home.VALUE_VISUAL), _vc(pg, f"card_{c}_go", "actionButton")
        assert num["position"]["z"] > go["position"]["z"], c
        # the number does not cover the whole row, so the rest of the card still clicks through ...
        assert num["position"]["width"] < go["position"]["width"] - 80, c
        # ... and it ends above the label row, which must keep the whole-card click
        lbl = _vc(pg, f"card_{c}_lbl", "textbox")
        assert num["position"]["y"] + num["position"]["height"] <= lbl["position"]["y"], c
        assert not _overlap(num["position"], lbl["position"]), c


def test_each_chip_has_a_bookmark_button_to_its_bucket():
    pbir.BOOKMARKS.clear()
    pg = _home()
    for k, (b, slug) in enumerate(zip(BUCKETS, SLUGS)):
        btn, txt = _vc(pg, f"chip_go{k}", "actionButton"), _vc(pg, f"chip{k}", "card")
        bg = _vc(pg, f"chip_bg{k}", "shape")
        assert _bookmark_target(btn) == _bm(f"Home · Act now — {b}")["name"], b
        assert "parentGroupName" not in btn
        bp, tp, cp = btn["position"], txt["position"], bg["position"]
        # click zone: the left part of the chip (dot + count), above the text; hover zone: the rest of the text
        assert bp["z"] > tp["z"] and bp["x"] == cp["x"] and bp["height"] == cp["height"], b
        assert tp["x"] < bp["x"] + bp["width"] < tp["x"] + tp["width"] - 30, b
    pill_go = _vc(pg, "pill_go", "actionButton")
    assert _bookmark_target(pill_go) == _bm("Home · PMO view")["name"]
    assert pill_go["position"]["z"] > _vc(pg, "pill", "card")["position"]["z"]
    assert pill_go["position"]["width"] < ext_home.PILL_W / 2


def test_bucket_views_show_only_their_bucket():
    pbir.BOOKMARKS.clear()
    pg = _home()
    full = _vc(pg, "act_tbl", "tableEx")["position"]
    for b, slug, nm in zip(BUCKETS, SLUGS, CHIPN):
        tbl = _vc(pg, f"act_tbl_{slug}", "tableEx")
        ms = [pr["field"]["Measure"]["Property"] for pr in tbl["visual"]["query"]["queryState"]["Values"]["projections"]
              if "Measure" in pr["field"]]
        assert ms == [f"Story | Home · Tip {nm}"], b             # the only measure: other projects' rows vanish
        assert all("Measure" not in f["field"] for f in tbl["filterConfig"]["filters"])
        assert f"Act now — {b}" in repr(_vc(pg, f"act_title_{slug}", "textbox")["visual"]["objects"])
        assert _bookmark_target(_vc(pg, f"act_all_{slug}", "actionButton")) == _bm("Home · PMO view")["name"]
        p = tbl["position"]
        assert (p["x"], p["y"], p["width"], p["height"]) == (full["x"], full["y"], full["width"], full["height"]), b


# ---------------------------------------------------------------- review fixes (rev 2, round 2)
def _expr(name):
    return next(m["expression"] for m in MEASURES if m["name"] == f"Story | Home · {name}")


def test_long_lists_are_capped_with_blank_unless_rank():
    for stem in ("Portfolio", "Benefits", "Status", "Governance"):
        e = _expr(f"Tip {stem}")
        assert "RANKX" in e and "ALLSELECTED ( DimProject[Name] )" in e and "<= 12" in e, stem
        assert "TOPN" not in e.upper(), stem                  # blank-unless pattern, no TopN
        more, sub = _expr(f"Tip {stem} More"), _expr(f"Tip {stem} Sub")
        assert "_n > 12" in more and "more · open the" in more, stem
        assert "12" in sub, stem
    assert "ASC" in _expr("Tip Benefits")                      # weakest first
    assert "9999" in _expr("Tip Status Key")
    assert "Proposed" not in _expr("Tip Portfolio Key")         # proposed-with-no-budget rows are gone
    assert "_b > 0" in _expr("Tip Portfolio Key")


def test_long_tooltip_pages_are_tall_with_footer_and_total():
    built = _all_home_pages()
    for c in ext_home.LONG_TIPS:
        pg = built[pages.PID[f"tip_home_{c}"]]
        assert pg.height == ext_home.TIP_H_LONG, c
        more = _vc(pg, "tip_more", "card")
        assert more is not None and "More" in repr(more["visual"]["query"] if "visual" in more else more), c
        sub = _vc(pg, "tip_sub", ext_home.VALUE_VISUAL)
        assert "Sub" in repr(sub), c
        tbl = _vc(pg, "tip_tbl", "tableEx")["position"]
        assert tbl["y"] + tbl["height"] <= more["position"]["y"], c        # footer sits under the table
        assert more["position"]["y"] + more["position"]["height"] <= ext_home.TIP_H_LONG, c


def test_tooltip_titles_say_what_they_explain():
    for key, (title, *_rest) in ext_home.card_tips().items():
        assert title.startswith("Behind "), key


def test_governance_sentence_counts_listable_plans():
    assert "COUNTROWS" in _expr("Gov Failing Projects") and "Failing Rules" in _expr("Gov Failing Projects")
    e = _expr("Insight Governance")
    assert "Gov Failing Projects" in e and "project plans fail" in e and "other plan" in e
    assert "MAX ( 0, _f - _n )" in e                                   # the " (+M other plans)" tail only when M > 0


def test_click_zones():
    assert ext_home.PILL_HIT_W >= 115 and ext_home.PILL_HIT_W < ext_home.PILL_W / 2
    pg = _home()
    btn = _vc(pg, "chip_go0", "actionButton")
    fill = btn["visual"]["objects"]["fill"]
    rest = next(f for f in fill if f.get("selector", {}).get("id") == "default")["properties"]["transparency"]
    assert rest["expr"]["Literal"]["Value"].rstrip("D") != "100"      # visible at rest

def test_status_movement_charts_two_rows_inside_the_standard_section():
    import ext_status
    pg = next(p for p in ext_status.build() if p.id == pages.PID["status"])
    vcs = {d: next(v for v in pg.visuals if v["name"] == pbir.uid(pg.id, f"v_move_{d}", "barChart"))["position"]
           for d, _ in ext_status.DIMS}
    assert {p["height"] for p in vcs.values()} == {150}              # a bar chart needs ~150 px to draw its bars
    assert {vcs[d]["y"] for d in ("Overall", "Schedule")} == {pages.Y2V}
    assert {vcs[d]["y"] for d in ("Financial", "Effort", "Issue")} == {pages.Y2V + 155}
    assert max(p["y"] + p["height"] for p in vcs.values()) <= pages.Y2V + pages.H2
    assert [round(vcs[d]["width"]) for d in ("Overall", "Schedule")] == [278, 278]
    assert [round(vcs[d]["width"]) for d in ("Financial", "Effort", "Issue")] == [183, 183, 183]
    sec = {n: next(v for v in pg.visuals if v["name"] == pbir.uid(pg.id, f"sec{n}", "textbox"))["position"]["y"]
           for n in (3, 4)}
    assert (sec[3], sec[4]) == (pages.Y3, pages.Y4)                    # sections 3 and 4 are back in place