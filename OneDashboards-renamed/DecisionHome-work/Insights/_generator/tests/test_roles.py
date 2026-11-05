import json
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
