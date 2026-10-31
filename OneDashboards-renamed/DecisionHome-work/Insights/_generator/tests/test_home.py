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
        "Answer Benefits", "Due In 30d"]


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
    assert sum(1 for vc in pg.visuals if vc["visual"].get("visualType") == "actionButton"
               and vc["name"] in {_name(pg, f"rail_btn_{i}", "actionButton") for i, _ in rail}) == 8


def test_build_all_has_single_ext_home_page():
    built = [p for p in pages.build_all() if p.id == pages.PID["home"]]
    assert len(built) == 1
    assert _name(built[0], "rail_bg", "shape") in {vc["name"] for vc in built[0].visuals}


def test_home_slicers_sync():
    sl = [vc for vc in _home().visuals if vc["visual"]["visualType"] == "slicer"]
    assert len(sl) == 2
    assert all("syncGroup" in vc["visual"] for vc in sl)


def test_body_area_fits():
    assert ext_home.BODY_Y >= 388 + 12 and ext_home.BODY_Y + 588 <= 988
