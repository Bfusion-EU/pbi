"""The entry layer (entry.py) in the Insights pack: welcome -> questions -> chapter brief -> chapter pages."""
import json

import pages
import pbir

BUILT = {next(k for k, v in pages.PID.items() if v == p.id): p for p in pages.build_all()}


def _targets(pg):
    out = set()
    for vc in pg.visuals:
        for link in vc.get("visual", {}).get("visualContainerObjects", {}).get("visualLink", []):
            sec = link["properties"].get("navigationSection")
            if sec:
                out.add(sec["expr"]["Literal"]["Value"].strip("'"))
    return out


def test_entry_route_reaches_every_story_page():
    reach = _targets(BUILT["welcome"]) | _targets(BUILT["questions"])
    for c in [k for k in pages.ENTRY_PAGES if k.startswith("brief_")]:
        reach |= _targets(BUILT[c])
    missing = [k for k, _ in pages.PAGES if k != "welcome" and pages.PID[k] not in reach]
    assert missing == [], missing


def test_back_and_home_on_every_page_but_welcome():
    for k, pg in BUILT.items():
        if k == "welcome" or k.startswith("tip_"):
            continue
        dump = json.dumps(pg.visuals)
        assert "'Back'" in dump, k
        assert pages.PID["welcome"] in _targets(pg), k


def test_briefs_hidden_and_one_visual_name_per_key():
    for k in pages.ENTRY_PAGES:
        pg = BUILT[k]
        if k.startswith("brief_"):
            assert pg.page.get("visibility") == "HiddenInViewMode", k
    for k, pg in BUILT.items():
        names = [v["name"] for v in pg.visuals]
        assert len(names) == len(set(names)), k


def test_brief_takeaway_measures_registered():
    import entry
    for c in entry.BRIEF_TAKEAWAYS:
        if f"brief_{c}" not in pages.PID:      # a Story role-report chapter
            continue
        for m in entry.brief_measures()[c][0]:
            assert m in pbir.EXTENSION_MEASURES
