"""Build 'Story Launcher': one navy page that opens the five role reports (and the full story) in the Power BI app.

    python launcher.py            # writes ../../Story/Story Launcher.pbip + .Report
    python launcher.py --check    # build + validate; WARN for every app link not filled in yet (app_links.json)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bfstory  # noqa: E402  (registers the story measures the headline cards use)
import build  # noqa: E402
import entry  # noqa: E402
import layout  # noqa: E402
import pbir  # noqa: E402
import roles  # noqa: E402
import app_links  # noqa: E402
from pbir import Page, shape, st, headline, b, ORANGE  # noqa: E402
from entry import (INK, W, SH, LOGO_RES, ONEPLAN_RES, TILE, TILE_LINE, SOFT_INK, MUTED_INK,  # noqa: E402
                   _logo, _text, web_ghost)

NAME = "Story Launcher"


def _role_tile(pg, x, y, w, h, k, role):
    key = f"r{k}"
    url = app_links.url(role.key, roles.MAP_PAGE_ID)
    pg.add(x, y, w, h, shape(TILE, radius=16, line=TILE_LINE), key=f"{key}_bg")
    _text(pg, x + 24, y + 24, w - 48, 28, "YOUR ROLE", st("Segoe UI Semibold", 10, ORANGE, True), f"{key}_eyebrow")
    _text(pg, x + 24, y + 54, w - 48, 72, role.title, st("DIN", 24, "#FFFFFF", True), f"{key}_title")
    _text(pg, x + 24, y + 128, w - 48, 64, role.purpose, st("Segoe UI", 12, SOFT_INK), f"{key}_purpose")
    hl = headline(role.headline, bg=TILE, border=TILE, size=10, colour="#E5EAF1")
    hl["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    pg.add(x + 14, y + 200, w - 28, h - 300, hl, key=f"{key}_hl")
    pg.add(x + 24, y + h - 76, w - 48, 52, shape(ORANGE if url else "#2A3F5C", radius=26), key=f"{key}_btn_bg")
    _text(pg, x + 24, y + h - 70, w - 48, 40, "Open  →" if url else "Link not set yet",
          st("Segoe UI Semibold", 13, "#FFFFFF", True), f"{key}_btn_t", align="center")
    tip = f"Open the {role.title} report" if url else f"{role.title}: app link not set yet (app_links.json)"
    pg.add(x, y, w, h, layout._alt(web_ghost(url, tip), tip), key=f"{key}_go")


def build_launcher():
    pg = Page(roles.LAUNCHER_PAGE_ID, "Choose your role", W, SH, background_colour=INK, display_option="FitToPage")
    pg.page["objects"]["outspace"] = [{"properties": {"color": pbir.col_solid(INK), "transparency": pbir.n(0)}}]
    pg.add(0, 0, W, 8, shape(ORANGE), key="top_bar")
    pg.add(120, 60, 190, 120, _logo(LOGO_RES, "BFusion logo"), key="bfusion_logo")
    pg.add(W - 120 - 211, 74, 211, 92, _logo(ONEPLAN_RES, "OnePlan logo"), key="oneplan_logo")
    _text(pg, 120, 210, 900, 34, "PMO DECISION PACK", st("DIN", 15, ORANGE, True), "eyebrow")
    _text(pg, 120, 244, 1400, 70, "Which role are you?", st("DIN", 44, "#FFFFFF", True), "title")
    _text(pg, 120, 318, 1400, 40, "Each report holds only the questions your role asks, from the same OnePlan data.",
          st("Segoe UI", 16, "#C9D2E0"), "subtitle")
    gap, top, h = 18, 390, 450
    tw = (1768 - gap * (len(roles.ROLES) - 1)) / len(roles.ROLES)
    for k, role in enumerate(roles.ROLES.values()):
        _role_tile(pg, 16 + k * (tw + gap), top, tw, h, k, role)
    full = app_links.url("full", roles.MAP_PAGE_ID)
    tip = "Open the full story: every chapter in one report" if full else "Full story: app link not set yet"
    pg.add(16, 862, 520, 48, shape(INK, radius=24, line="#FFFFFF"), key="full_bg")
    _text(pg, 16, 868, 520, 36, "Full story: every chapter in one report  ›", st("Segoe UI Semibold", 12, "#FFFFFF", True),
          "full_t", align="center")
    pg.add(16, 862, 520, 48, layout._alt(web_ghost(full, tip, hover=INK), tip), key="full_go")
    pg.add(16, 930, 1768, 1, shape(TILE_LINE), key="foot_rule")
    _text(pg, W - 16 - 600, 952, 600, 26, "BFUSION · Data from OnePlan", st("Segoe UI", 9, MUTED_INK), "foot_right",
          align="right")
    return [pg]


def write(pages_, out_dir):
    out = build.write_report(NAME, pages_, [], out_dir, extra_filters=[bfstory.NO_TEST_PROJECTS])
    entry.register_resources(out)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = Path(args[args.index("--out") + 1]) if "--out" in args else bfstory.OUT_DIR
    pages_ = build_launcher()
    out = write(pages_, out_dir)
    print(f"built launcher -> {out}")
    if "--check" in args:
        for k in app_links.missing():
            print(f"WARN app_links.json: {k} not filled in (its button has no link yet)")
        e = build.check(pages_, out) or 0
        more = bfstory.layout_errors(pages_) + bfstory.path_errors(out)
        for m in more:
            print(m)
        tot = e + len(more)
        print("OK" if tot == 0 else f"FAILED ({tot} problem(s))")
        sys.exit(1 if tot else 0)
