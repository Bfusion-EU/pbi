import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board  # noqa: E402
import build  # noqa: E402
from story_measures import MEASURES  # noqa: E402

PAGES = board.build_board()


def _all(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _all(v)
    elif isinstance(o, list):
        for v in o:
            yield from _all(v)


def _texts(vc):
    return [r["value"] for d in _all(vc) if "textRuns" in d for r in d["textRuns"]]


def test_six_pages_1280x720_visible():
    assert len(PAGES) == 6
    for pg in PAGES:
        assert (pg.width, pg.height) == (1280, 720)
        assert "visibility" not in pg.page
        assert pg.page["displayOption"] == "FitToPage"


def test_frame_headline_and_page_number():
    for pg in PAGES:
        pos = [(v["position"], v.get("visual", {}).get("visualType")) for v in pg.visuals]
        assert any(p["x"] == 0 and p["y"] == 0 and p["width"] == 1280 and p["height"] == 56 and t == "shape"
                   for p, t in pos)
        assert any(p["y"] == 96 and t == "card" for p, t in pos)
        assert any("/ 6" in x for v in pg.visuals for x in _texts(v))


def test_nothing_but_frame_in_title_bar():
    for pg in PAGES:
        for vc in pg.visuals:
            if vc["position"]["y"] < 56:
                assert vc["visual"]["visualType"] in ("shape", "textbox")


def test_inside_page():
    for pg in PAGES:
        for vc in pg.visuals:
            p = vc["position"]
            assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["width"] <= 1280 and p["y"] + p["height"] <= 720


def test_measures_exist():
    _, model = build.load_model()
    ext = {m["name"] for m in MEASURES}
    used = {d["Measure"]["Property"] for pg in PAGES for vc in pg.visuals for d in _all(vc)
            if isinstance(d.get("Measure"), dict) and "Property" in d["Measure"]}
    assert used and [m for m in used if m not in model and m not in ext] == []


def test_act_now_sort():
    pg = PAGES[0]
    tbl = next(vc for vc in pg.visuals if vc.get("visual", {}).get("visualType") == "tableEx")
    srt = tbl["visual"]["query"]["sortDefinition"]["sort"][0]
    assert srt["field"]["Measure"]["Property"] == "Story | Home · Act Score" and srt["direction"] == "Descending"
    assert "filterConfig" in tbl and all("Measure" not in json.dumps(f["field"]) for f in tbl["filterConfig"]["filters"])
