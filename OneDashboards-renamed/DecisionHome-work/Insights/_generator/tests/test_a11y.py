import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402
import a11y  # noqa: E402
import pbir  # noqa: E402

NO_ALT = {"textbox", "shape"}


@pytest.fixture(scope="module")
def built():
    return pages.build_all()


def _visuals(built):
    for pg in built:
        for vc in pg.visuals:
            if "visual" in vc:
                yield pg, vc


def _alt(vc):
    gen = vc["visual"].get("visualContainerObjects", {}).get("general", [{}])[0]
    return a11y._lit(gen.get("properties", {}).get("altText"))


def _syn(vtype, title=None, proj=None, **extra):
    v = {"visualType": vtype, "query": {"queryState": {"Values": {"projections": [
        {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "T"}}, "Property": p}},
         "nativeQueryRef": p} for p in (proj or ["M"])]}}}}
    if title:
        v["visualContainerObjects"] = {"title": [{"properties": {"text": pbir.s(title)}}]}
    v.update(extra)
    return v


def _img(name, linked):
    v = pbir.image("rail-x-grey.png", name)
    if linked:
        v["visualContainerObjects"] = {"visualLink": [{"properties": {}}]}
    return v


def _btn(text, tip=""):
    v = {"visualType": "actionButton", "objects": {"text": [{"properties": {"text": pbir.s(text)}}]}}
    if tip:
        v["visualContainerObjects"] = {"visualLink": [{"properties": {"tooltip": pbir.s(tip)}}]}
    return v


def _slc():
    return {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [
        {"field": {"Column": {"Property": "Year"}}, "nativeQueryRef": "Year", "displayName": "Year"}]}}}}


@pytest.mark.parametrize("v,expected", [
    (_syn("lineChart", "Cost trend"), "Cost trend"),
    (_syn("card", "Total"), "KPI: Total"),
    (_syn("card"), ""),
    (_syn("tableEx"), ""),
    (_slc(), "Filter: Year"),
    (_btn("Open"), "Open"),
    (_btn("", "Go home"), "Go home"),
    (_img("Risk icon", True), "Icon: Risk"),
    (_img("Risk icon", False), ""),
    (_img("OnePlan logo", False), "Logo: OnePlan"),
])
def test_alt_text_rules(v, expected):
    assert a11y.alt_text(v) == expected


def test_field_names_tolerates_other_projections():
    v = {"query": {"queryState": {"Y": {"projections": [{"field": {"HierarchyLevel": {}}}]}}}}
    assert a11y._field_names(v) == []


def test_titled_content_has_alt_text(built):
    n = 0
    for pg, vc in _visuals(built):
        v = vc["visual"]
        t = v["visualType"]
        titled = bool(a11y._title_text(v)) and t not in {"image", "textbox", "shape"}
        if a11y._decorative(vc):              # breadcrumb separators are buttons now, but decorative
            continue
        if t in {"slicer", "actionButton"} or titled:
            n += 1
            assert _alt(vc), (pg.display, t, vc["name"])
    assert n > 300


def test_alt_text_clean_and_short(built):
    for pg, vc in _visuals(built):
        alt = _alt(vc)
        assert len(alt) <= 250
        for bad in ("Story |", " · Story", "MonthStart", "Home:"):
            assert bad not in alt, (pg.display, vc["name"], alt)


def test_home_sparklines_have_trend_alt(built):
    pg = next(p for p in built if p.id == pages.PID["home"])
    sparks = [vc for vc in pg.visuals if vc["name"].endswith("_spark")] or              [vc for vc in pg.visuals if "visual" in vc and vc["visual"]["visualType"] == "areaChart"]
    assert sparks
    for vc in sparks:
        assert _alt(vc).startswith("Trend: "), vc["name"]


def test_tab_order_groups(built):
    from collections import defaultdict
    for pg in built:
        groups = defaultdict(list)
        for vc in pg.visuals:
            groups[vc.get("parentGroupName")].append(vc)
        for vcs in groups.values():
            ordered = sorted(vcs, key=lambda vc: vc["position"]["tabOrder"])
            keys = [(a11y._decorative(vc), vc["position"]["y"], vc["position"]["x"]) for vc in ordered]
            assert keys == sorted(keys), pg.display


def test_apply_idempotent(built):
    import json
    before = json.dumps([p.visuals for p in built], sort_keys=True)
    a11y.apply(built)
    assert json.dumps([p.visuals for p in built], sort_keys=True) == before


def test_textbox_and_shape_get_no_alt(built):
    for _, vc in _visuals(built):
        if vc["visual"]["visualType"] in NO_ALT:
            assert not _alt(vc)


def _top(pg):
    return [vc for vc in pg.visuals if "parentGroupName" not in vc]


def _content(vc):
    return not a11y._decorative(vc)


@pytest.mark.parametrize("key", ["home", "exec"])
def test_content_precedes_shapes(built, key):
    pg = next(p for p in built if p.id == pages.PID[key])
    top = _top(pg)
    shapes = [vc["position"]["tabOrder"] for vc in top if a11y._decorative(vc)]
    content = [vc["position"]["tabOrder"] for vc in top if _content(vc)]
    assert content
    if key == "home":
        assert shapes
    assert not shapes or max(content) < min(shapes)


def test_exec_content_in_reading_order(built):
    pg = next(p for p in built if p.id == pages.PID["exec"])
    content = sorted((vc for vc in _top(pg) if _content(vc)),
                     key=lambda vc: (vc["position"]["y"], vc["position"]["x"]))
    orders = [vc["position"]["tabOrder"] for vc in content]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)
