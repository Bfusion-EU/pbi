import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bfstory  # noqa: E402
import roles  # noqa: E402
import app_links  # noqa: E402


FULL = dict(bfstory.PAGES)


def test_modeller_pages_are_renumbered_as_chapters():
    assert roles.role_pages(roles.ROLES["modeller"], FULL) == [
        ("map", "Map — every page"),
        ("portfolio", "1 · Portfolio"), ("strategy", "1b · Strategy & Value"),
        ("selection", "2 · Selection & Funding Line"),
        ("scenarios", "3 · Scenarios & Trade-offs"),
        ("constraints", "4 · Constraints & Sequencing"),
        ("resources", "5 · Resources"), ("capacity", "5b · Capacity & Allocation"),
    ]


def test_deep_dives_get_letters_and_pmo_gets_home_after_map():
    ppm = roles.role_pages(roles.ROLES["ppm"], FULL)
    assert ("health", "1b · Portfolio 360 & Health") in ppm
    assert ("benefits", "2c · Benefits & Value") in ppm
    assert ("budgetrisk", "3c · Budget Risk & Early Warning") in ppm
    assert ("roadmap", "1d · Roadmap & Delivery") in roles.role_pages(roles.ROLES["pm"], FULL)
    pmo = [k for k, _ in roles.role_pages(roles.ROLES["pmo"], FULL)]
    assert pmo[:2] == ["map", "home"]
    assert pmo[2:] == ["exec", "roadmap", "trend", "schedule", "psr", "timeline", "risk", "riskmap",
                       "governance", "recon", "hygiene", "timesheets"]


def test_agreed_page_split():
    keys = {r: {k for k, _ in roles.role_pages(roles.ROLES[r], FULL) if k != "map"} for r in roles.ROLES}
    assert keys["ppm"] == {"exec", "health", "roadmap", "drift", "trend", "portfolio", "selection", "benefits",
                           "realised", "strategy", "finance", "fintree", "budgetrisk", "projfin", "schedule",
                           "critical", "timeline", "risk", "riskmap"}
    assert keys["modeller"] == {"portfolio", "strategy", "selection", "scenarios", "constraints", "resources", "capacity"}
    assert keys["pm"] == {"schedule", "critical", "psr", "roadmap", "timeline", "finance", "projfin", "mywork", "risk",
                          "riskmap", "kpigrid"}
    assert keys["resources"] == {"resources", "fte", "org", "timesheets", "mywork", "capacity", "selection",
                                 "constraints"}
    assert keys["pmo"] == {"home", "exec", "roadmap", "trend", "schedule", "psr", "timeline", "risk", "riskmap",
                           "governance", "recon", "hygiene", "timesheets"}


def test_key_visuals_reach_the_roles_that_need_them():
    """Gantt, roadmap, schedule risk forecast and risk radar come with the pages that carry them."""
    gantt, roadmap, srf, radar = {"schedule", "mywork", "psr"}, {"roadmap"}, {"schedule"}, {"risk"}
    keys = {r: {k for k, _ in roles.role_pages(roles.ROLES[r], FULL)} for r in roles.ROLES}
    assert {r for r in keys if keys[r] & gantt} == {"ppm", "pm", "resources", "pmo"}
    for need in (roadmap, srf, radar):
        assert {r for r in keys if keys[r] & need} == {"ppm", "pm", "pmo"}
    assert all(len(roles.ROLES[r].chapters) <= 5 for r in roles.ROLES)


def test_report_names_are_short():
    assert all(len(r.report) <= 15 for r in roles.ROLES.values())


def test_rail_starts_at_the_hub_and_uses_known_icons():
    import illustrations
    icons = {i for i, _, _ in __import__("chrome").RAIL} | set(illustrations.RAIL_ICONS)
    for r in roles.ROLES.values():
        rl = roles.rail(r)
        assert rl[0] == ("questions", "map", "Map")
        hub = 2 if r.home else 1
        assert (rl[1] == ("cc", "home", "Decision")) == r.home
        assert [t for _, t, _ in rl[hub:]] == [c for c, _ in r.chapters]
        assert all(i in icons for i, _, _ in rl)


def test_one_icon_per_meaning():
    """Every rail entry shows its own chapter's icon: no icon stands for two chapters in any report."""
    for r in roles.ROLES.values():
        assert all(icon == target for icon, target, _ in roles.rail(r) if target not in ("map", "home"))
    meaning = {}
    for r in roles.ROLES.values():
        for icon, target, _ in roles.rail(r):
            assert meaning.setdefault(icon, target) == target, (r.key, icon, target, meaning[icon])
    for icon, target, _ in __import__("chrome").RAIL:
        assert meaning.setdefault(icon, target) == target, (icon, target, meaning[icon])


def test_app_links_blank_until_filled(tmp_path, monkeypatch):
    f = tmp_path / "links.json"
    f.write_text(json.dumps({"app_id": "", "reports": {k: "" for k in app_links.KEYS}}), encoding="utf-8")
    monkeypatch.setenv("BFSTORY_APP_LINKS", str(f))
    assert app_links.url("ppm", "abc") == ""
    assert app_links.missing() == ["app_id"] + app_links.KEYS
    f.write_text(json.dumps({"app_id": "APP", "reports": {"ppm": "R1"}}), encoding="utf-8")
    assert app_links.url("ppm", "abc") == f"https://app.powerbi.com/groups/me/apps/APP/reports/R1/abc?ctid={app_links.TENANT}"
    assert app_links.url("pm", "abc") == ""


import entry  # noqa: E402
import chrome  # noqa: E402


def test_web_ghost_links_or_stays_inert():
    on = entry.web_ghost("https://x/y", "Open")
    vl = on["visualContainerObjects"]["visualLink"][0]["properties"]
    assert vl["type"]["expr"]["Literal"]["Value"] == "'WebUrl'"
    assert vl["webUrl"]["expr"]["Literal"]["Value"] == "'https://x/y'"
    off = entry.web_ghost("", "Open")
    assert "visualLink" not in off["visualContainerObjects"]


def test_context_defaults_keep_the_full_pack_behaviour():
    ctx = entry.Context(pid={}, names={}, pages=[], chapters=[], questions={}, headline={}, blurbs={}, title="t")
    assert ctx.home_url is None and ctx.art == {}


def test_chrome_apply_takes_a_rail():
    import inspect
    sig = inspect.signature(chrome.apply)
    assert "rail" in sig.parameters and "art" in sig.parameters


import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

import pytest  # noqa: E402

GEN = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_path():
    """A short build folder: --check fails any file over 259 characters, and pytest's own tmp_path is ~50
    characters longer than the real Story folder, so the longest custom visual path would fail there only."""
    d = Path(tempfile.mkdtemp(prefix="bfs"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_every_role_chapter_has_card_text_and_takeaways():
    for r in roles.ROLES.values():
        for ch, _ in r.chapters:
            assert ch in bfstory.CARD_TEXT, ch
            assert ch in entry.BRIEF_TAKEAWAYS, ch
            assert all(k in bfstory.BUILDERS for k, _ in roles.role_pages(r, FULL))


def test_takeaway_measures_are_numbers():
    import story_measures
    names = {m["name"]: m for m in story_measures.MEASURES}
    for ch in ("selection", "scenarios", "constraints"):
        for m, _, _ in entry.BRIEF_TAKEAWAYS[ch]:
            assert m in entry._MODEL_FORMATS or (m in names and names[m]["formatString"]), m


def _build(args, out):
    return subprocess.run([sys.executable, "bfstory.py", *args, "--out", str(out)], cwd=GEN,
                          capture_output=True, text=True, encoding="utf-8")


def _report_pages(rep):
    return {json.loads(p.read_text(encoding="utf-8"))["displayName"]: p.parent.name
            for p in rep.glob("definition/pages/*/page.json")}


def test_modeller_report_builds_clean(tmp_path):
    r = _build(["--role", "modeller", "--check"], tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    rep = tmp_path / "Story Modeller.Report"
    q = roles.MAP_PAGE_ID
    assert any("MODELLER · MAP" in f.read_text(encoding="utf-8")
               for f in rep.glob(f"definition/pages/{q}/visuals/*/visual.json"))
    shown = {d.split(" (")[0] for d in _report_pages(rep)}
    assert shown == ({n for _, n in roles.role_pages(roles.ROLES["modeller"], FULL)}
                     | {d.name for d in bfstory.DRILLS if d.host == "modeller"})


def test_pmo_report_has_home_and_no_dangling_links(tmp_path):
    r = _build(["--role", "pmo", "--check"], tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    assert "Home — Decision center" in _report_pages(tmp_path / "Story PMO.Report")


def test_launcher_links_every_role_and_the_full_story(tmp_path):
    links = tmp_path / "links.json"
    links.write_text(json.dumps({"app_id": "APP", "reports": {k: k.upper() for k in app_links.KEYS}}),
                     encoding="utf-8")
    env = {**__import__("os").environ, "BFSTORY_APP_LINKS": str(links)}
    r = subprocess.run([sys.executable, "launcher.py", "--out", str(tmp_path), "--check"], cwd=GEN, env=env,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    urls = []
    for f in (tmp_path / "Story Launcher.Report").glob("definition/pages/*/visuals/*/visual.json"):
        for vl in json.loads(f.read_text(encoding="utf-8")).get("visual", {}).get(
                "visualContainerObjects", {}).get("visualLink", []):
            if "webUrl" in vl["properties"]:
                urls.append(vl["properties"]["webUrl"]["expr"]["Literal"]["Value"].strip("'"))
    rj = (tmp_path / "Story Launcher.Report" / "definition" / "report.json").read_text(encoding="utf-8")
    assert bfstory.NO_TEST_PROJECTS["name"] in rj and "NIKO Test 2" in rj
    q = roles.MAP_PAGE_ID
    tail = f"?ctid={app_links.TENANT}"
    assert sorted(urls) == sorted([f"https://app.powerbi.com/groups/me/apps/APP/reports/{k.upper()}/{q}{tail}"
                                   for k in roles.ROLES] +
                                  [f"https://app.powerbi.com/groups/me/apps/APP/reports/FULL/{q}{tail}"])


def test_seventh_deep_dive_raises_instead_of_vanishing():
    names = {**FULL, **{f"x{i}": FULL["health"] for i in range(7)}}
    role = roles.Role("t", "Story T", "T", "p", "h", [("exec", [f"x{i}" for i in range(7)])])
    with pytest.raises(ValueError):
        roles.role_pages(role, names)


def test_role_chapters_are_visible_tabs(tmp_path):
    r = _build(["--role", "modeller"], tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    shown = set()
    for f in (tmp_path / "Story Modeller.Report").glob("definition/pages/*/page.json"):
        pj = json.loads(f.read_text(encoding="utf-8"))
        if pj.get("visibility") != "HiddenInViewMode":
            shown.add(pj["displayName"])
    assert {"1 · Portfolio", "2 · Selection & Funding Line", "3 · Scenarios & Trade-offs",
            "4 · Constraints & Sequencing", "5 · Resources"} <= shown


def test_ppm_tabs_are_map_and_chapters_only(tmp_path):
    r = _build(["--role", "ppm"], tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    shown = set()
    for f in (tmp_path / "Story PPM.Report").glob("definition/pages/*/page.json"):
        pj = json.loads(f.read_text(encoding="utf-8"))
        if pj.get("visibility") != "HiddenInViewMode":
            shown.add(pj["displayName"])
    assert shown == {"Map — every page", "1 · Executive Summary", "2 · Portfolio", "3 · Financials",
                     "4 · Schedule", "5 · Risk"}


STORY = Path(__file__).resolve().parents[3] / "Story"


def test_cross_report_drillthrough_host_and_sources():
    """Each drill page sits in its host role report only; every Story report may drill into all of them."""
    for name in ["Bfusion Story"] + [r.report for r in roles.ROLES.values()]:
        rep = json.loads((STORY / f"{name}.Report" / "definition" / "report.json").read_text(encoding="utf-8"))
        assert rep["settings"]["useCrossReportDrillthrough"] is True, name
        got = {p.parent.name: json.loads(p.read_text(encoding="utf-8"))
               for p in (STORY / f"{name}.Report" / "definition" / "pages").glob("*/page.json")}
        got = {k: v for k, v in got.items() if v.get("pageBinding", {}).get("referenceScope") == "CrossReport"}
        want = {bfstory.uid("bfstory-page", d.key) for d in bfstory.DRILLS if roles.ROLES[d.host].report == name}
        assert set(got) == want, name
        for page in got.values():
            assert page["visibility"] == "HiddenInViewMode"
            assert page["pageBinding"]["type"] == "Drillthrough"
            assert page["pageBinding"]["acceptsFilterContext"] == "None"


def test_every_role_hosts_a_drill_page():
    assert {d.host for d in bfstory.DRILLS} == set(roles.ROLES)
    assert len({d.key for d in bfstory.DRILLS}) == len(bfstory.DRILLS)
