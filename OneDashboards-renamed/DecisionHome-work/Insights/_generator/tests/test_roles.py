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
        ("questions", "Questions — where to start"),
        ("brief_selection", "Brief · Selection & Funding Line"), ("selection", "1 · Selection & Funding Line"),
        ("brief_scenarios", "Brief · Scenarios & Trade-offs"), ("scenarios", "2 · Scenarios & Trade-offs"),
        ("brief_constraints", "Brief · Constraints & Sequencing"), ("constraints", "3 · Constraints & Sequencing"),
        ("brief_resources", "Brief · Resources"), ("resources", "4 · Resources"),
    ]


def test_deep_dives_get_letters_and_pmo_gets_home_after_questions():
    ppm = roles.role_pages(roles.ROLES["ppm"], FULL)
    assert ("health", "1b · Portfolio 360 & Health") in ppm
    assert ("budgetrisk", "3c · Budget Risk & Early Warning") in ppm
    pmo = [k for k, _ in roles.role_pages(roles.ROLES["pmo"], FULL)]
    assert pmo[:2] == ["questions", "home"]
    assert pmo[2:] == ["brief_governance", "governance", "recon", "brief_psr", "psr", "brief_timesheets", "timesheets"]


def test_agreed_page_split():
    keys = {r: {k for k, _ in roles.role_pages(roles.ROLES[r], FULL) if k != "questions" and not k.startswith("brief_")}
            for r in roles.ROLES}
    assert keys["ppm"] == {"exec", "health", "roadmap", "drift", "portfolio", "finance", "fintree", "budgetrisk",
                           "risk", "benefits"}
    assert keys["modeller"] == {"selection", "scenarios", "constraints", "resources"}
    assert keys["pm"] == {"schedule", "critical", "psr", "mywork", "risk", "kpigrid"}
    assert keys["resources"] == {"resources", "fte", "org", "timesheets", "selection"}
    assert keys["pmo"] == {"home", "governance", "recon", "psr", "timesheets"}


def test_report_names_are_short():
    assert all(len(r.report) <= 15 for r in roles.ROLES.values())


def test_rail_starts_at_the_hub_and_uses_known_icons():
    icons = {i for i, _, _ in __import__("chrome").RAIL}
    for r in roles.ROLES.values():
        rl = roles.rail(r)
        assert rl[0] == (("cc", "home", "Decision") if r.home else ("cc", "questions", "Questions"))
        assert [t for _, t, _ in rl[1:]] == [c for c, _ in r.chapters]
        assert all(i in icons for i, _, _ in rl)


def test_app_links_blank_until_filled(tmp_path, monkeypatch):
    f = tmp_path / "links.json"
    f.write_text(json.dumps({"app_id": "", "reports": {k: "" for k in app_links.KEYS}}), encoding="utf-8")
    monkeypatch.setenv("BFSTORY_APP_LINKS", str(f))
    assert app_links.url("ppm", "abc") == ""
    assert app_links.missing() == ["app_id"] + app_links.KEYS
    f.write_text(json.dumps({"app_id": "APP", "reports": {"ppm": "R1"}}), encoding="utf-8")
    assert app_links.url("ppm", "abc") == "https://app.powerbi.com/groups/me/apps/APP/reports/R1/abc"
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
    q = roles.QUESTIONS_PAGE_ID
    assert any("MODELLER · START HERE" in f.read_text(encoding="utf-8")
               for f in rep.glob(f"definition/pages/{q}/visuals/*/visual.json"))
    shown = {d.split(" (")[0] for d in _report_pages(rep)}
    assert shown == {n for _, n in roles.role_pages(roles.ROLES["modeller"], FULL)}


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
    q = roles.QUESTIONS_PAGE_ID
    assert sorted(urls) == sorted([f"https://app.powerbi.com/groups/me/apps/APP/reports/{k.upper()}/{q}"
                                   for k in roles.ROLES] +
                                  [f"https://app.powerbi.com/groups/me/apps/APP/reports/FULL/{roles.WELCOME_PAGE_ID}"])


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
    assert {"1 · Selection & Funding Line", "2 · Scenarios & Trade-offs", "3 · Constraints & Sequencing",
            "4 · Resources"} <= shown
