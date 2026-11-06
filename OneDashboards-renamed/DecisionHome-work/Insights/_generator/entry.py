"""The entry layer shared by the BFusion packs: welcome page, questions page, chapter brief pages and the back /
home buttons. Each pack hands in its own pages through use(Context(...)) before building them, so the Story pack
and the Insights pack get the same pages with their own chapters, deep dives, questions and headlines.

    welcome  ->  questions (dark bento grid)  ->  chapter brief  ->  chapter and deep dives
"""
from dataclasses import dataclass, field
from pathlib import Path
import shutil

import illustrations
import layout
import pbir
import story_measures
from pbir import Page, M, s, b, st, textbox, shape, nav_button, home_icon_button, headline, image, ORANGE

W = 1800
LOGO_FILE = Path(__file__).parent / "assets" / "bfusion_logo.png"   # 300x189, Branding/Logo/logo.jpg + rounded corners
LOGO_RES = "bfusion_logo.png"
ONEPLAN_RES = "OnePlan_logo_-_dark_background9901469509814106.png"   # 211x92 on #0E1C2D
INK = "#0E1C2D"                      # the OnePlan logo's own background: the welcome page uses it so the logo blends


@dataclass
class Context:
    """What a pack tells the entry layer about itself."""
    pid: dict                  # page key -> page id
    names: dict                # page key -> display name ("3 · Financials", "3b · ...")
    pages: list                # [(key, display)] in story order
    chapters: list             # chapter keys in order
    questions: dict            # page key -> header question (as written in the header)
    headline: dict             # chapter key -> headline measure
    blurbs: dict               # page key -> one line under the question on a brief tile
    title: str                 # big title on the welcome page
    home_label: str = "Decision Center"
    inside: dict = field(default_factory=dict)   # chapter key -> chips on the questions page start tile
    art: dict = field(default_factory=dict)      # chapter key -> chapter whose brief scene illustration it borrows
    home_url: str = None                         # None: the pack has a welcome page; else the URL the house opens


CTX = None


def use(ctx):
    global CTX
    CTX = ctx


def register_resources(out):
    """Logo and illustrations into the report's RegisteredResources (call after build.write_report)."""
    import json
    rj = out / "definition" / "report.json"
    rep = json.loads(rj.read_text(encoding="utf-8"))
    reg = next(p for p in rep["resourcePackages"] if p["type"] == "RegisteredResources")
    have = {i["name"] for i in reg["items"]}
    res = out / "StaticResources" / "RegisteredResources"
    for f, srcf in [(LOGO_RES, LOGO_FILE)] + [(f, illustrations.OUT / f) for f in illustrations.files()]:
        if f not in have:
            reg["items"].append({"name": f, "path": f, "type": "Image"})
        shutil.copy(srcf, res / f)
    rj.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def back_button(colour=ORANGE):
    """Arrow that returns to the page the user came from (Power BI's Back action), not to a fixed page."""
    btn = home_icon_button("", colour)
    btn["visualContainerObjects"]["visualLink"] = [{"properties": {"show": b(True), "type": s("Back"),
                                                                   "tooltip": s("Back to the previous page")}}]
    return layout._alt(btn, "Back to the previous page")


def home_button(pg, x, y, size=40, target=None):
    """Orange house that always goes to the welcome page (target: that page's id, when the caller has it)."""
    pg.add(x, y, size, size, shape(ORANGE, radius=10), key="home_bg")
    ico = round(size * 0.56)
    pg.add(x + (size - ico) / 2, y + (size - ico) / 2, ico, ico, _logo(illustrations.HOME_FILE, "Home icon"),
           key="home_ico")
    if target is None and CTX.home_url is not None:
        tip = "Back to the role overview" if CTX.home_url else "Role overview: link not set yet (app_links.json)"
        pg.add(x, y, size, size, layout._alt(web_ghost(CTX.home_url, tip, hover=INK), tip), key="home")
        return
    pg.add(x, y, size, size, layout._alt(_ghost("", target or CTX.pid["welcome"], "Go to the welcome page", hover=INK),
                                         "Go to the welcome page"), key="home")


def _crumb_w(text):
    # bold Segoe UI 10 pt + the button's own margins ("Home" fits whole); wider with the type bump (pbir.fscale)
    return round(len(text) * 7.6 * pbir.fscale(10) + 40)


def _crumb_label(text, colour, bold=True, size=10):
    """A button with no action: Desktop centres button text vertically, so every breadcrumb level (links,
    separators and the current page) sits on one line — textboxes put their text at the top instead."""
    btn = nav_button(text, "", "", fill="#FFFFFF", hover="#FFFFFF", press="#FFFFFF", font=colour, size=size, margin=0)
    btn["objects"]["text"][1]["properties"]["bold"] = b(bold)
    btn["visualContainerObjects"].pop("visualLink")
    return btn


# ================================================================ WELCOME + QUESTIONS
# Both are one screen (1800x1000, FitToPage): the welcome page is the cover, the questions page the menu.
SH = 1000


def _logo(res, name):
    vc = image(res, name)
    vc["objects"]["image"][0]["properties"]["sourceFile"]["image"]["scaling"] = s("Fit")
    return vc


def build_welcome():
    pg = Page(CTX.pid["welcome"], CTX.names["welcome"], W, SH, background_colour=INK, display_option="FitToPage")
    pg.page["objects"]["outspace"] = [{"properties": {"color": pbir.col_solid(INK), "transparency": pbir.n(0)}}]
    pg.add(0, 0, W, 8, shape(ORANGE), key="top_bar")
    x = 120
    pg.add(x, 110, 190, 120, _logo(LOGO_RES, "BFusion logo"), key="bfusion_logo")
    pg.add(x, 270, 860, 34, textbox([[("PMO DECISION PACK", st("DIN", 15, ORANGE, True))]]), key="eyebrow")
    pg.add(x, 306, 900, 96, textbox([[(CTX.title, st("DIN", 50, "#FFFFFF", True))]]), key="title")
    pg.add(x, 410, 860, 80, textbox([[("Eight questions, one answer each: from the portfolio pulse to the decision "
                                       "you need to take today.", st("Segoe UI", 18, "#C9D2E0"))]]), key="subtitle")
    pg.add(x, 530, 380, 64, nav_button(f"Open the {CTX.home_label}  ›", CTX.pid["home"], "Open the decision center",
                                       size=16), key="go_home")
    pg.add(x + 400, 530, 380, 64, nav_button("Browse the questions  ›", CTX.pid["questions"],
                                             "Pick a question and open the dashboard that answers it",
                                             fill=INK, hover="#1B2C42", press="#22344D", font="#FFFFFF", size=16,
                                             outline="#FFFFFF"), key="go_questions")
    pg.add(x, 680, 400, 30, textbox([[("DATA SOURCE", st("Segoe UI Semibold", 11, "#8A97AB", True))]]), key="src_label")
    pg.add(x, 710, 211, 92, _logo(ONEPLAN_RES, "OnePlan logo"), key="oneplan_logo")
    pg.add(x + 230, 724, 560, 70, textbox([[("Portfolio, project, resource, cost and status data, read from OnePlan.",
                                             st("Segoe UI", 13, "#C9D2E0"))]]), key="src_text")
    # right: how every page reads
    px, py, pw, ph = 1080, 110, 600, 700
    pg.add(px, py, pw, ph, shape("#15263B", radius=12, line="#22344D"), key="how_bg")
    pg.add(px + 36, py + 32, pw - 72, 40, textbox([[("How every page reads", st("DIN", 22, "#FFFFFF", True))]]),
           key="how_title")
    steps = [("Pulse", "KPIs against last period, with an up or down arrow."),
             ("Act", "The list of projects that need a decision now."),
             ("Explain", "Charts and deep dives that show why."),
             ("Next", "Every page ends with the next question in the story.")]
    for k, (head_, body) in enumerate(steps):
        sy = py + 100 + k * 140
        pg.add(px + 36, sy, 56, 56, shape(ORANGE, radius=28), key=f"how_dot{k}")
        pg.add(px + 36, sy + 8, 56, 40, textbox([[(str(k + 1), st("DIN", 20, "#FFFFFF", True))]], align="center"),
               key=f"how_num{k}")
        pg.add(px + 112, sy, pw - 148, 110, textbox([[(head_, st("Segoe UI Semibold", 16, "#FFFFFF", True))],
                                                     [(body, st("Segoe UI", 13, "#C9D2E0"))]]), key=f"how_step{k}")
    pg.add(0, 860, W, 1, shape("#22344D"), key="foot_rule")
    pg.add(x, 872, 600, 30, textbox([[("bfusion.eu", st("Segoe UI", 11, "#8A97AB"))]]), key="foot_left")
    pg.add(W - 120 - 600, 872, 600, 30, textbox([[("BFUSION · Data from OnePlan · Power BI",
                                                   st("Segoe UI", 11, "#8A97AB"))]], align="right"), key="foot_right")
    return pg


def _sentence(q):
    out = (q[0] + q[1:].lower()).replace(" a instead of b", " A instead of B")
    return " ".join("I" if w == "i" else w for w in out.split(" "))


# ---------------------------------------------------------------- questions page: dark bento grid
# Executive summary is the tall orange "start here" tile; the chapters with deep dives are tiles that list them;
# risk / benefits / governance (no deep dives) are wide bars. Every tile is one click to its chapter: a transparent
# button lies over the tile's text, and the deep-dive row buttons lie over that.
TILE, TILE_LINE, ROW, BADGE = "#15263B", "#22344D", "#1B2E46", "#2A3F5C"
SOFT_INK, MUTED_INK = "#AEB8C7", "#8A97AB"


def _ghost(text, target, tip, font="#FFFFFF", size=10, margin=12, hover="#FFFFFF"):
    """Button with no fill of its own: the tile or row drawn under it shows through; hover lightens it."""
    btn = nav_button(text, target, tip, fill=INK, hover=hover, press=hover, font=font, size=size, align="left",
                     margin=margin)
    fills = btn["objects"]["fill"]
    fills[1]["properties"]["transparency"] = pbir.n(100)
    fills[2]["properties"]["transparency"] = pbir.n(90)
    fills[3]["properties"]["transparency"] = pbir.n(80)
    return btn


def web_ghost(url, tip, hover="#FFFFFF"):
    """Transparent button that opens a web URL (another report in the app). No URL yet: no action at all."""
    btn = _ghost("", "", tip, hover=hover)
    if url:
        btn["visualContainerObjects"]["visualLink"] = [{"properties": {
            "show": b(True), "type": s("WebUrl"), "webUrl": s(url), "tooltip": s(tip)}}]
    else:
        btn["visualContainerObjects"].pop("visualLink")
    return btn


def _text(pg, x, y, w, h, text, style, key, align=None):
    pg.add(x, y, w, h, textbox([[(text, style)]], align=align), key=key)


def _icon(pg, x, y, ck, fill, key):
    pg.add(x, y, 44, 44, shape(fill, radius=10), key=f"{key}_icobg")
    pg.add(x + 9, y + 9, 26, 26, image(f"rail-{ck}-white.png", f"{ck} icon"), key=f"{key}_ico")


def _arrow(pg, x, y, fill, ink, key):
    pg.add(x, y, 40, 40, shape(fill, radius=20), key=f"{key}_arrow")
    _text(pg, x, y + 4, 40, 32, "→", st("Segoe UI", 14, ink, True), f"{key}_arrow_t", align="center")


def _headline(pg, x, y, w, h, ck, bg, ink, key):
    hl = headline(CTX.headline[ck], bg=bg, border=bg, size=10, colour=ink)
    hl["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    pg.add(x, y, w, h, hl, key=key)


def _deep_row(pg, x, y, w, m, row, badge, badge_ink, ink, key):
    c = layout._code(CTX.names[m])
    pg.add(x, y, w, 30, shape(row, radius=8), key=f"{key}_bg")
    pg.add(x + 8, y + 5, 30, 20, shape(badge, radius=6), key=f"{key}_badge")
    _text(pg, x + 8, y + 3, 30, 22, f"{c[0]}{c[1]}", st("Segoe UI", 8, badge_ink, True), f"{key}_code", align="center")
    q = _sentence(CTX.questions[m])
    size = pbir.fit_size(q, w, (10, 9, 8), pad=46 + 8)     # 12 pt with the type bump, smaller when the row is narrow
    pg.add(x, y, w, 30, layout._alt(_ghost(q, CTX.pid[m], f"Open {CTX.names[m]}", font=ink, size=size,
                                           margin=46), f"Open {CTX.names[m]}"), key=f"{key}_btn")


def _deep(ck):
    code = layout._code(CTX.names[ck])[0]
    return [m for m, d in CTX.pages if layout._code(d) and layout._code(d)[0] == code and m != ck]


def _tile(pg, x, y, w, h, k, ck):
    code = layout._code(CTX.names[ck])
    key = f"t{k}"
    pg.add(x, y, w, h, shape(TILE, radius=14, line=TILE_LINE), key=f"{key}_bg")
    _icon(pg, x + 24, y + 20, ck, TILE_LINE, key)
    _arrow(pg, x + w - 64, y + 20, ORANGE, "#FFFFFF", key)
    _text(pg, x + 20, y + 76, w - 40, 24, f"{code[0]} · {code[2].upper()}", st("Segoe UI Semibold", 9, MUTED_INK, True),
          f"{key}_lbl")
    _text(pg, x + 20, y + 98, w - 40, 44, _sentence(CTX.questions[ck]), st("DIN", 17, "#FFFFFF", True), f"{key}_q")
    _headline(pg, x + 14, y + 140, w - 28, 46, ck, TILE, SOFT_INK, f"{key}_hl")
    _brief_link(pg, x, y, w, h, ck, key)
    for j, m in enumerate(_deep(ck)):
        _deep_row(pg, x + 20, y + 196 + j * 38, w - 40, m, ROW, BADGE, ORANGE, "#E5EAF1", f"{key}_d{j}")


def _brief_link(pg, x, y, w, h, ck, key):
    """The whole tile opens the chapter brief, which leads on to the chapter and its deep dives."""
    tip = f"Open the {layout._code(CTX.names[ck])[2]} brief"
    pg.add(x, y, w, h, layout._alt(_ghost("", CTX.pid[f"brief_{ck}"], tip), tip), key=f"{key}_go")


def _start_tile(pg, x, y, w, h, ck):
    code = layout._code(CTX.names[ck])
    key = "t0"
    pg.add(x, y, w, h, shape(ORANGE, radius=14), key=f"{key}_bg")
    _text(pg, x + 20, y + 22, 220, 28, "START HERE", st("Segoe UI Semibold", 10, "#FFFFFF", True), f"{key}_start")
    _arrow(pg, x + w - 64, y + 20, "#FFFFFF", ORANGE, key)
    _icon(pg, x + 24, y + 60, ck, "#EE8455", key)
    _text(pg, x + 20, y + 118, w - 40, 24, f"{code[0]} · {code[2].upper()}", st("Segoe UI Semibold", 9, "#FFFFFF", True),
          f"{key}_lbl")
    q = _sentence(CTX.questions[ck])
    qsize = 28 if len(q) * 15 <= w - 40 else 20        # 28 pt fits one line only; two lines need 20 pt in 60 px
    _text(pg, x + 20, y + 142, w - 40, 60, q, st("DIN", qsize, "#FFFFFF", True), f"{key}_q")
    _headline(pg, x + 14, y + 204, w - 28, 50, ck, ORANGE, "#FFFFFF", f"{key}_hl")
    _brief_link(pg, x, y, w, h, ck, key)
    for j, m in enumerate(_deep(ck)):
        _deep_row(pg, x + 20, y + 268 + j * 40, w - 40, m, "#EC7A4A", "#F3A27C", "#FFFFFF", "#FFFFFF", f"{key}_d{j}")
    # what the chapter holds, as chips at the foot of the tile
    if not CTX.inside.get(ck):
        return
    place, cx, row = [], x + 24, 0                    # (chip, x, row, width): wrap at the tile's right edge
    for chip in CTX.inside[ck]:
        cw_ = round(len(chip) * 7.2 * pbir.fscale(9) + 30)
        if cx + cw_ > x + w - 20 and cx > x + 24:
            cx, row = x + 24, row + 1
        place.append((chip, cx, row, cw_))
        cx += cw_ + 8
    cy = y + h - 150 - 36 * max(0, row - 2)            # three rows fit under the label; more rows lift the block
    _text(pg, x + 20, cy, w - 40, 24, "INSIDE THIS CHAPTER", st("Segoe UI Semibold", 9, "#FFFFFF", True), f"{key}_in")
    for j, (chip, cx, row, cw_) in enumerate(place):
        ry = cy + 32 + 36 * row
        pg.add(cx, ry, cw_, 28, shape(ORANGE, radius=14, line="#F6B79A"), key=f"{key}_chip{j}")
        _text(pg, cx, ry + 2, cw_, 24, chip, st("Segoe UI", 9, "#FFFFFF"), f"{key}_chip{j}_t", align="center")


def _bar(pg, x, y, w, h, k, ck):
    code = layout._code(CTX.names[ck])
    key = f"t{k}"
    pg.add(x, y, w, h, shape(TILE, radius=14, line=TILE_LINE), key=f"{key}_bg")
    _icon(pg, x + 20, y + (h - 44) / 2, ck, TILE_LINE, key)
    _text(pg, x + 80, y + 18, 420, 24, f"{code[0]} · {code[2].upper()}", st("Segoe UI Semibold", 9, MUTED_INK, True),
          f"{key}_lbl")
    _text(pg, x + 80, y + 42, 440, 44, _sentence(CTX.questions[ck]), st("DIN", 17, "#FFFFFF", True), f"{key}_q")
    _headline(pg, x + 520, y + 16, w - 520 - 84, h - 32, ck, TILE, SOFT_INK, f"{key}_hl")
    _arrow(pg, x + w - 64, y + (h - 40) / 2, ORANGE, "#FFFFFF", key)
    _brief_link(pg, x, y, w, h, ck, key)


def build_questions():
    pg = Page(CTX.pid["questions"], CTX.names["questions"], W, SH, background_colour=INK, display_option="FitToPage")
    pg.page["objects"]["outspace"] = [{"properties": {"color": pbir.col_solid(INK), "transparency": pbir.n(0)}}]
    pg.add(0, 0, W, 6, shape(ORANGE), key="top_bar")
    pg.add(10, 26, 60, 58, back_button(), key="back")
    home_button(pg, 76, 36)
    _text(pg, 132, 24, 600, 28, "START HERE" if CTX.home_url is None else f"{CTX.title.upper()} · START HERE", st("Segoe UI Semibold", 11, ORANGE, True), "eyebrow")
    _text(pg, 132, 50, 1100, 56, "Which question do you have?", st("DIN", 30, "#FFFFFF", True), "title")
    eight = len(CTX.chapters) == 8
    n_q = len(CTX.chapters) + sum(len(_deep(ck)) for ck in CTX.chapters
                                  if not eight or layout._code(CTX.names[ck])[0] not in "678")  # 6-8 are bars
    _text(pg, 132, 104, 1100, 28, f"{len(CTX.chapters)} chapters, {n_q} questions. Click a tile to open its chapter, "
                                 "a row to go one level deeper.", st("Segoe UI", 11, SOFT_INK), "subtitle")
    home_w = max(186, pbir.button_w(f"{CTX.home_label}  ›", 11, pad=40))
    if "welcome" in CTX.pid:
        pg.add(W - 32 - home_w - 14 - 180, 52, 180, 46,
               nav_button("‹  Welcome", CTX.pid["welcome"], "Back to the welcome page", fill=INK, hover="#1B2C42",
                          press="#22344D", font="#FFFFFF", size=11, outline="#FFFFFF", radius=23), key="back_welcome")
    if "home" in CTX.pid:
        pg.add(W - 32 - home_w, 52, home_w, 46, nav_button(f"{CTX.home_label}  ›", CTX.pid["home"], "Open the decision center",
                                                     size=11, radius=23), key="go_home")
    G, top, bottom = 14, 150, 900
    if eight:
        cw = (1768 - 3 * G) / 4
        rh = (bottom - top - G) / 2
        col = [16 + c * (cw + G) for c in range(4)]
        chap = dict(zip([layout._code(CTX.names[k])[0] for k in CTX.chapters], CTX.chapters))
        _start_tile(pg, col[0], top, cw, bottom - top, chap["1"])
        for k, (num, cx, cy) in enumerate([("2", col[1], top), ("3", col[2], top), ("4", col[3], top),
                                           ("5", col[1], top + rh + G)], start=1):
            _tile(pg, cx, cy, cw, rh, k, chap[num])
        bh = (rh - 2 * G) / 3
        for j, num in enumerate("678"):
            _bar(pg, col[2], top + rh + G + j * (bh + G), 2 * cw + G, bh, 5 + j, chap[num])
    else:                                               # a role report: one row, the first chapter is "start here"
        n = len(CTX.chapters)
        cw = (1768 - G * (n - 1)) / n
        for k, ck in enumerate(CTX.chapters):
            x = 16 + k * (cw + G)
            (_start_tile(pg, x, top, cw, bottom - top, ck) if k == 0 else _tile(pg, x, top, cw, bottom - top, k, ck))
    pg.add(16, 930, 1768, 1, shape(TILE_LINE), key="foot_rule")
    pg.add(16, 944, 64, 40, _logo(LOGO_RES, "BFusion logo"), key="foot_logo")
    _text(pg, W - 16 - 600, 952, 600, 26, "BFUSION · Data from OnePlan", st("Segoe UI", 9, MUTED_INK), "foot_right",
          align="right")
    return pg


# ---------------------------------------------------------------- chapter brief pages (navy navigation pages)
# One per chapter, between the Questions page and the chapter: the question, a verdict, three takeaways and one
# tile per page of the chapter. The picture top-right and the drawings in the tiles are faint line art
# (illustrations.py), so they stay behind the text.
RED, AMBER, GREEN, GREY = "#D64545", "#E0A100", "#2E9E6A", "#8A97AB"
BRIEF_FOLDER = "Story\\Brief"
# chapter -> [(value measure, label, rule)]; rule: None (no judgement) | ("hi", amber, red): higher is better,
# below red is red | ("lo", amber, red): lower is better, at or above red is red | "band": utilisation, red above
# 100%, amber below 50%. The thresholds are defaults for the PMO to confirm.
BRIEF_TAKEAWAYS = {
    "exec": [("Story | Active Projects", "active projects", None),
             ("Story | On Track %", "of active projects on track", ("hi", 0.8, 0.6)),
             ("Story | Late Active Projects", "projects running late", ("lo", 1, 5))],
    "portfolio": [("Story | Proposed Projects", "proposals in the pipeline", None),
                  ("Story | Aligned Budget %", "of budget on strongly aligned work", ("hi", 0.7, 0.5)),
                  ("Story | Plan Variance %", "plan forecast against plan budget", ("lo", 0.0001, 0.05))],
    "finance": [("Story | EAC Variance %", "forecast against budget at completion", ("lo", 0.0001, 0.05)),
                ("Story | Projects Over Budget", "projects over budget", ("lo", 1, 5)),
                ("Story | Burn %", "of the budget spent", None)],
    "resources": [("Story | Utilisation %", "utilisation of capacity", "band"),
                  ("Story | Over-allocated People", "people over-allocated", ("lo", 1, 5)),
                  ("Story | Free Capacity (h)", "hours of free capacity", None)],
    "schedule": [("Story | On Schedule %", "of active projects on schedule", ("hi", 0.8, 0.6)),
                 ("Story | Overdue Tasks", "overdue tasks", ("lo", 1, 20)),
                 ("Story | Milestones Next 30d", "milestones in the next 30 days", None)],
    "risk": [("Story | Critical High Risks", "critical or high risks", ("lo", 1, 5)),
             ("Story | Unmitigated Risk %", "of risks without mitigation", ("lo", 0.2, 0.4)),
             ("Story | Open Issues", "open issues", ("lo", 1, 10))],
    "benefits": [("Story | Benefits Realised %", "of benefits due realised", ("hi", 0.9, 0.7)),
                 ("Story | Value Ratio", "value per euro of forecast cost", ("hi", 2, 1)),
                 ("Story | Benefits At Completion", "benefits planned at completion", None)],
    "governance": [("PMO | Governance Score", "governance score", ("hi", 80, 60)),
                   ("PMO | Compliance %", "compliance", ("hi", 0.9, 0.75)),
                   # a count: PMO | Unsubmitted Status Reports is a text list of report dates, not a number
                   ("Story | PMO · Plans With Open Status Report", "plans with a status report not submitted",
                    ("lo", 1, 10))],
}
# Pages that are a chapter in a role report (deep dives in the full pack). The three modelling pages get their own
# takeaways; the others reuse the takeaways of the chapter they belong to in the full pack.
BRIEF_TAKEAWAYS.update({
    "selection": [("Story | Proposed Projects", "proposals in the pipeline", None),
                  ("Story | Aligned Budget %", "of budget on strongly aligned work", ("hi", 0.7, 0.5)),
                  ("Story | Scenario · Plans A", "plans funded in scenario A", None)],
    "scenarios": [("Story | Scenario · Budget Gap % A", "scenario A against its target budget", ("lo", 0.0001, 0.05)),
                  ("Story | Scenario · Budget Gap % B", "scenario B against its target budget", ("lo", 0.0001, 0.05)),
                  ("Story | Scenario · Benefits A", "benefits planned in scenario A", None)],
    "constraints": [("Story | Scenario · Effort A", "hours of effort in scenario A", None),
                    ("Story | Over-allocated People", "people over-allocated", ("lo", 1, 5)),
                    ("Story | Utilisation %", "utilisation of capacity", "band")],
    "kpigrid": BRIEF_TAKEAWAYS["exec"], "mywork": BRIEF_TAKEAWAYS["schedule"], "psr": BRIEF_TAKEAWAYS["schedule"],
    "timesheets": BRIEF_TAKEAWAYS["resources"],
})
_BRIEF_MEASURES = None


def _colour_dax(m, rule):
    if rule is None:
        return f'"{ORANGE}"'
    v = f"VAR _v = [{m}]\nRETURN IF ( ISBLANK ( _v ), \"{GREY}\", "
    if rule == "band":
        return v + f'IF ( _v > 1, "{RED}", IF ( _v < 0.5, "{AMBER}", "{GREEN}" ) ) )'
    kind, amber, red = rule
    if kind == "hi":
        return v + f'IF ( _v < {red}, "{RED}", IF ( _v < {amber}, "{AMBER}", "{GREEN}" ) ) )'
    return v + f'IF ( _v >= {red}, "{RED}", IF ( _v >= {amber}, "{AMBER}", "{GREEN}" ) ) )'


_MODEL_FORMATS = {"PMO | Governance Score": "0", "PMO | Compliance %": "0.0%"}


def _value_dax(m):
    """Takeaways are numbers (compared with thresholds); a model measure must be listed in _MODEL_FORMATS."""
    if m not in _MODEL_FORMATS:
        sm = next(x for x in story_measures.MEASURES if x["name"] == m)
        assert sm["dataType"] != story_measures.T and sm["formatString"], f"takeaway {m} is not a number"
    fmt = _MODEL_FORMATS.get(m) or next(x["formatString"] for x in story_measures.MEASURES if x["name"] == m)
    head = f'VAR _v = [{m}]\nRETURN IF ( ISBLANK ( _v ), "–", '
    if "%" in fmt or "." in fmt:
        return head + f'FORMAT ( _v, "{fmt}" ) )'
    return head + ('IF ( ABS ( _v ) >= 1000000, FORMAT ( _v / 1000000, "#,##0.0" ) & "M", '
                   'IF ( ABS ( _v ) >= 10000, FORMAT ( _v / 1000, "#,##0" ) & "K", FORMAT ( _v, "#,##0" ) ) ) )')


def _brief_measure(name, expr, fmt, desc):
    full = f"Story | Brief · {name}"
    story_measures.add(full, story_measures.D if fmt else story_measures.T, expr, fmt, BRIEF_FOLDER, desc)
    pbir.EXTENSION_MEASURES.add(full)
    return full


def brief_measures():
    """{chapter: ([takeaway colour measures], verdict, verdict colour, [takeaway value texts])}; registered once."""
    global _BRIEF_MEASURES
    if _BRIEF_MEASURES is None:
        _BRIEF_MEASURES = {}
        for ch, items in BRIEF_TAKEAWAYS.items():
            if ch not in CTX.chapters:
                continue
            label = layout._code(CTX.names[ch])[2]
            cols = [_brief_measure(f"{label} {k + 1} Colour", _colour_dax(m, rule), None,
                                   f"Dot colour for the takeaway '{lbl}': {rule or 'no judgement'}.")
                    for k, (m, lbl, rule) in enumerate(items)]
            judged = [c for c, (_, _, rule) in zip(cols, items) if rule]
            count = lambda colour: " + ".join(f'INT ( [{c}] = "{colour}" )' for c in judged)  # noqa: E731
            head = f"VAR _r = {count(RED)}\nVAR _a = {count(AMBER)}\nVAR _g = {count(GREEN)}\nRETURN "
            verdict = _brief_measure(f"{label} Verdict", head + 'IF ( _r > 0, "ACT", IF ( _a > 0, "WATCH", '
                                     'IF ( _g > 0, "ON TRACK", "NO DATA" ) ) )', None,
                                     "ACT when a takeaway is red, WATCH when one is amber, else ON TRACK.")
            vcol = _brief_measure(f"{label} Verdict Colour", head + f'IF ( _r > 0, "{RED}", IF ( _a > 0, "{AMBER}", '
                                  f'IF ( _g > 0, "{GREEN}", "{GREY}" ) ) )', None, "Colour of the verdict pill.")
            texts = [_brief_measure(f"{label} {k + 1} Value", _value_dax(m), None,
                                    f"[{m}] as text for the brief: a dash when blank, M / K for large numbers.")
                     for k, (m, _, _) in enumerate(items)]
            _BRIEF_MEASURES[ch] = (cols, verdict, vcol, texts)
    return _BRIEF_MEASURES


def _fx(measure):
    return {"solid": {"color": {"expr": M(measure)}}}


def _value_card(measure, size, colour, bg=None):
    vc = headline(measure, bg=bg or INK, border=bg or INK, size=size, colour=colour)
    vc["visualContainerObjects"]["border"] = [{"properties": {"show": b(False)}}]
    if bg is None:
        vc["visualContainerObjects"]["background"] = [{"properties": {"show": b(False)}}]
    vc["objects"]["labels"][0]["properties"]["fontFamily"] = s("DIN")
    return vc


def _dot(pg, x, y, d, measure, key):
    vc = shape(GREY, radius=d // 2)
    vc["objects"]["fill"][0]["properties"]["fillColor"] = _fx(measure)
    pg.add(x, y, d, d, vc, key=key)


def _crumb(pg, x, text, target, tip, key, colour=SOFT_INK, bold=False, size=10, w=None, align="center"):
    """One breadcrumb level. Every level, separators and the current page included, is a button: Desktop centres
    button text vertically, so all levels sit on one line (a text box puts its text at the top instead)."""
    w = w or _crumb_w(text) - 16
    btn = nav_button(text, target, tip, fill=INK, hover="#1B2C42" if target else INK, press="#22344D" if target else INK,
                     font=colour, size=size, margin=4, align=align)
    btn["objects"]["text"][1]["properties"]["bold"] = b(bold)
    if not target:
        btn["visualContainerObjects"].pop("visualLink")
    pg.add(x, 26, w, 32, btn if text == "›" else layout._alt(btn, tip), key=key)
    return x + w


def _tile_text(m):
    """(eyebrow, question, blurb) of a navigation tile on a brief page."""
    if m.startswith("brief_"):
        nxt = m[len("brief_"):]
        return f"NEXT QUESTION · {layout._code(CTX.names[nxt])[2].upper()}", _sentence(CTX.questions[nxt]), CTX.blurbs[nxt]
    if m == "home":
        return f"THE {CTX.home_label.upper()}", "What needs a decision now?", "The pulse, the list to act on, every chapter"
    if m == "questions":
        return "ALL QUESTIONS", "Which question do you have?", "Every chapter and deep dive on one page"
    c = layout._code(CTX.names[m])
    return ("START WITH THE CHAPTER" if not c[1] else f"DEEP DIVE {c[0]}{c[1]}"), _sentence(CTX.questions[m]), CTX.blurbs[m]


def _tile_art(m):
    if m.startswith("brief_"):
        return illustrations.spot_file(m[len("brief_"):])
    return illustrations.spot_file({"home": "exec", "questions": "kpigrid"}.get(m, m))


def build_brief(ch):
    key = f"brief_{ch}"
    code = layout._code(CTX.names[ch])
    cols, verdict, vcol, texts = brief_measures()[ch]
    pg = Page(CTX.pid[key], CTX.names[key], W, SH, background_colour=INK, display_option="FitToPage")
    pg.page["objects"]["outspace"] = [{"properties": {"color": pbir.col_solid(INK), "transparency": pbir.n(0)}}]
    pg.page["visibility"] = "HiddenInViewMode"
    pg.add(0, 0, W, 6, shape(ORANGE), key="top_bar")
    pg.add(1000, 70, illustrations.SCENE_W, illustrations.SCENE_H,
           _logo(illustrations.scene_file(CTX.art.get(ch, ch)), f"{code[2]} illustration"), key="scene")
    # home (welcome page) + breadcrumb + all questions
    pg.add(10, 14, 60, 58, back_button(), key="back")
    home_button(pg, 76, 22, 42)
    x = 130
    if "welcome" in CTX.pid:
        x = _crumb(pg, x, "Welcome", CTX.pid["welcome"], "Back to the welcome page", "crumb_welcome")
        x = _crumb(pg, x, "›", "", "then", "crumb_sep1", size=12, w=18)
    x = _crumb(pg, x, "Questions", CTX.pid["questions"], "All questions", "crumb_questions")
    x = _crumb(pg, x, "›", "", "then", "crumb_sep2", size=12, w=18)
    here = f"{code[0]} · {code[2]}"
    _crumb(pg, x, here, "", f"You are here: {here}", "crumb_here", colour="#FFFFFF", bold=True, w=_crumb_w(here),
           align="left")
    aq_w = max(190, pbir.button_w("‹  All questions", 11, pad=40))
    pg.add(W - 32 - aq_w, 22, aq_w, 44, nav_button("‹  All questions", CTX.pid["questions"], "Back to all questions",
                                                 fill=INK, hover="#1B2C42", press="#22344D", font="#FFFFFF", size=11,
                                                 outline="#FFFFFF", radius=22), key="all_questions")
    # question, verdict, headline
    q = _sentence(CTX.questions[ch])
    dy = 40 if len(q) * 29 <= 760 else 0               # one line of 44 pt DIN: centre it in the two-line slot
    _text(pg, 80, 128 + dy, 900, 28, f"CHAPTER {code[0]} · {code[2].upper()}",
          st("Segoe UI Semibold", 11, ORANGE, True), "eyebrow")
    _text(pg, 80, 158 + dy, 780, 150, q, st("DIN", 44, "#FFFFFF", True), "question")
    pg.add(84, 310, 900, 68, shape("#15263B", radius=34, line=TILE_LINE), key="verdict_bg")
    pill = _value_card(verdict, 10, "#FFFFFF", bg=GREY)
    pill["visualContainerObjects"]["background"] = [{"properties": {"show": b(True), "color": _fx(vcol)}}]
    pill["visualContainerObjects"]["border"] = [{"properties": {"show": b(True), "color": _fx(vcol), "radius": pbir.n(16)}}]
    pill["objects"]["labels"][0]["properties"]["fontFamily"] = s("Segoe UI Semibold")
    pg.add(96, 320, 140, 48, pill, key="verdict")
    pg.add(246, 314, 728, 60, _value_card(CTX.headline[ch], 11, "#E5EAF1"), key="headline")
    # three takeaways
    tw = (900 - 2 * 12) / 3
    for k, (m, lbl, _rule) in enumerate(BRIEF_TAKEAWAYS[ch]):
        tx, ty = 84 + k * (tw + 12), 392
        pg.add(tx, ty, tw, 136, shape("#15263B", radius=14, line=TILE_LINE), key=f"take{k}_bg")
        _dot(pg, tx + 18, ty + 20, 14, cols[k], f"take{k}_dot")
        vh = pbir.card_h(24)                            # 80 px: 24 pt value (pbir.card_need_px)
        pg.add(tx + 36, ty + 6, tw - 72, vh, _value_card(texts[k], 24, "#FFFFFF"), key=f"take{k}_val")
        _text(pg, tx + 12, ty + 6 + vh, tw - 24, 130 - vh, lbl, st("Segoe UI", 11, SOFT_INK), f"take{k}_lbl",
              align="center")
    # one tile per page of the chapter: the chapter first, then its deep dives
    keys = [ch] + _deep(ch)
    if len(keys) == 1:                                  # one-page chapter: offer the next question and the list too
        nxt = CTX.chapters[CTX.chapters.index(ch) + 1] if ch != CTX.chapters[-1] else None
        keys += [k for k in [f"brief_{nxt}" if nxt else ("home" if "home" in CTX.pid else None), "questions"] if k]
    n = len(keys)
    gap, ty, th = 18, 560, 340
    tw = (W - 48 - gap * (n - 1)) / n
    qsize = {1: 30, 2: 26, 3: 22, 4: 19, 5: 17}[n]
    for k, m in enumerate(keys):
        tx = 24 + k * (tw + gap)
        main = m == ch
        pg.add(tx, ty, tw, th, shape(ORANGE if main else "#15263B", radius=20, line=None if main else TILE_LINE),
               key=f"tile{k}_bg")
        pg.add(tx + tw - 176, ty + 8, 168, 168, _logo(_tile_art(m), "Tile drawing"), key=f"tile{k}_art")
        eyebrow, question, blurb = _tile_text(m)
        _text(pg, tx + 26, ty + 24, tw - 52, 26, eyebrow, st("Segoe UI Semibold", 10, "#FFFFFF" if main else ORANGE, True),
              f"tile{k}_eyebrow")
        _text(pg, tx + 24, ty + th - 172, tw - 48, 96, question, st("DIN", qsize, "#FFFFFF", True), f"tile{k}_q")
        _text(pg, tx + 24, ty + th - 76, tw - 120, 56, blurb,
              st("Segoe UI", 10, "#FFE6D8" if main else SOFT_INK), f"tile{k}_blurb")
        pg.add(tx + tw - 80, ty + th - 80, 52, 52, shape("#FFFFFF" if main else ORANGE, radius=26), key=f"tile{k}_arrow")
        _text(pg, tx + tw - 80, ty + th - 74, 52, 40, "→", st("Segoe UI", 16, ORANGE if main else "#FFFFFF", True),
              f"tile{k}_arrow_t", align="center")
        tip = f"Open {CTX.names[m]}"
        pg.add(tx, ty, tw, th, layout._alt(_ghost("", CTX.pid[m], tip), tip), key=f"tile{k}_go")
    pg.add(16, 930, 1768, 1, shape(TILE_LINE), key="foot_rule")
    pg.add(16, 944, 64, 40, _logo(LOGO_RES, "BFusion logo"), key="foot_logo")
    _text(pg, W - 16 - 600, 952, 600, 26, "BFUSION · Data from OnePlan", st("Segoe UI", 9, MUTED_INK), "foot_right",
          align="right")
    return pg
