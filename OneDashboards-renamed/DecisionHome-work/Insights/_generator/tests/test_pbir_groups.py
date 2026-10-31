import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pbir  # noqa: E402


def test_group_and_children():
    pg = pbir.Page("p1", "Test", 1800, 1000)
    g = pg.add_group(100, 100, 400, 300, "PMO view", key="grp_pmo", hidden=True)
    pg.add(120, 120, 100, 50, pbir.textbox([[("x", pbir.st())]]), key="child", parent=g)
    grp = next(v for v in pg.visuals if v["name"] == g)
    child = next(v for v in pg.visuals if v.get("parentGroupName") == g)
    assert grp["visualGroup"] == {"displayName": "PMO view", "groupMode": "ScaleMode"}
    assert grp["isHidden"] is True
    assert "visual" not in grp
    assert (child["position"]["x"], child["position"]["y"]) == (20, 20)  # group-relative (Desktop spike)


def test_unknown_parent_raises():
    pg = pbir.Page("p1", "Test", 1800, 1000)
    with pytest.raises(ValueError):
        pg.add(120, 120, 100, 50, pbir.textbox([[("x", pbir.st())]]), key="c", parent="nope")


def test_bookmark_registry():
    pbir.BOOKMARKS.clear()
    name = pbir.bookmark("Home · PMO view", "pmo", "p1", {"g1": False, "g2": True})
    bm = pbir.BOOKMARKS[0]
    assert bm["name"] == name
    assert bm["options"] == {"suppressData": True, "applyOnlyToTargetVisuals": True, "targetVisualNames": ["g1", "g2"]}
    st = bm["explorationState"]["sections"]["p1"]
    assert st["visualContainerGroups"] == {"g1": {"isHidden": False}, "g2": {"isHidden": True}}
    assert st["visualContainers"] == {}


def test_bookmark_and_drill_buttons():
    bb = pbir.bookmark_button("PMO", "bm1")
    link = bb["visualContainerObjects"]["visualLink"][0]["properties"]
    assert link["type"] == pbir.s("Bookmark") and link["bookmark"] == pbir.s("bm1")
    db = pbir.drill_button("Open One-Pager ›", "pageX")
    link = db["visualContainerObjects"]["visualLink"][0]["properties"]
    assert link["type"] == pbir.s("Drillthrough") and link["drillthroughSection"] == pbir.s("pageX")



ICON_KEYS = ["cc", "exec", "portfolio", "finance", "resources", "schedule", "risk", "benefits", "governance"]


def test_icons_present():
    d = Path(__file__).resolve().parents[1] / "assets" / "icons"
    for k in ICON_KEYS:
        for c in ("grey", "white"):
            f = d / f"rail-{k}-{c}.png"
            assert f.exists(), f
            assert f.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
