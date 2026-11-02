import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402
import a11y  # noqa: E402

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


def test_every_content_visual_has_alt_text(built):
    n = 0
    for pg, vc in _visuals(built):
        if vc["visual"]["visualType"] in NO_ALT:
            continue
        n += 1
        alt = _alt(vc)
        assert alt, (pg.display, vc["visual"]["visualType"], vc["name"])
        assert len(alt) <= 250
    assert n > 500


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
    assert shapes or key == "exec"  # the Executive page has no decorative shapes at all
    assert not shapes or max(content) < min(shapes)


def test_exec_content_in_reading_order(built):
    pg = next(p for p in built if p.id == pages.PID["exec"])
    content = sorted((vc for vc in _top(pg) if _content(vc)),
                     key=lambda vc: (vc["position"]["y"], vc["position"]["x"]))
    orders = [vc["position"]["tabOrder"] for vc in content]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)
