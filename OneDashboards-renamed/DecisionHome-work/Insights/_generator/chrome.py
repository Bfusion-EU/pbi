"""Story navigation chrome: a chapter rail on the left of every chapter page and a filter-context bar under the headline.

The rail replaces hunting for the chapter strip, breadcrumb and Next buttons: one click from any page to any chapter.
The bar says which slicers are set and how many active projects the page covers, so two pages that show different
numbers because their filters differ explain themselves.
"""
import json
import shutil
from pathlib import Path

import confidence
import layout
import pbir
from pbir import (NAVY, ORANGE, BORDER, MUTED, b, col_solid, headline, image, n, nav_button, shape, st, textbox)
from story_measures import add, T

RAIL_W = 80
BAR_H = 34
# the 1800x1000 footer band padded 80 px on the left (first pixel column repeated) and with body rows added above the
# band, so it fits the 1880 x 1058 (16:9) story screens without stretching the logo
BG_WIDE = "bfv5_footer_band_1880x1058.png"
BG_FILE = Path(__file__).resolve().parent / "assets" / BG_WIDE
TILE, STEP, TOP = 56, 74, 16
FILTER_MEASURE = "Story | Filter Context"
RAIL_BG, RAIL_INK = "#141C2F", "#8C98B3"
# icon, chapter key (None = decision center), short label
RAIL = [("cc", "home", "Decision"), ("exec", "exec", "Executive"), ("portfolio", "portfolio", "Portfolio"),
        ("finance", "finance", "Financials"), ("resources", "resources", "Resources"),
        ("schedule", "schedule", "Schedule"), ("risk", "risk", "Risk"), ("benefits", "benefits", "Benefits"),
        ("governance", "governance", "Governance")]

# slicer columns the bar reports, in reading order: (label, table, column)
FILTERS = [("Portfolio", "DimProject", "Portfolio Name"), ("Portfolio", "DimPortfolio", "Name"),
           ("Program", "DimProject", "Program Name"), ("Program", "DimProgram", "Name"),
           ("Project", "DimProject", "Name"), ("Project type", "DimProject", "ProjectType_Value"),
           ("Project type", "DimPortfolio", "ProjectType_Value"), ("State", "DimProject", "State_Value"),
           ("Plan type", "DimProject", "PlanType"), ("Business unit", "DimProject", "BusinessUnit_Value"),
           ("Business unit", "DimPortfolio", "BusinessUnit_Value"), ("Department", "DimResource", "Department_Value"),
           ("Role", "DimResource", "Role_Value"), ("Year", "DimDate", "Year")]


REPORT_FILTERED = {("DimProject", "Name"), ("DimPortfolio", "Name"), ("DimProgram", "Name")}


def _part(label, table, col):
    c = f"'{table}'[{col}]"
    # report-level filters ('Template', test plans) sit on these name columns, so ISFILTERED is always true there:
    # report them only when a few values are picked
    narrowed = f" && COUNTROWS ( VALUES ( {c} ) ) <= 3" if (table, col) in REPORT_FILTERED else ""
    cond = f"ISFILTERED ( {c} ) && COUNTROWS ( VALUES ( {c} ) ) > 0" + narrowed
    return (f'IF ( {cond}, "{label}: " & IF ( COUNTROWS ( VALUES ( {c} ) ) <= 3, '
            f'CONCATENATEX ( VALUES ( {c} ), {c}, ", " ), FORMAT ( COUNTROWS ( VALUES ( {c} ) ), "0" ) & " selected" ) & "  ·  " )')


add(FILTER_MEASURE, T, f"""
VAR _f = {" & ".join(_part(*f) for f in FILTERS)}
VAR _n = [Story | Active Projects]
RETURN
    "Showing:  " & IF ( _f = "", "all portfolios, all years (no filter set)  ·  ", _f )
        & FORMAT ( COALESCE ( _n, 0 ), "0" ) & IF ( _n = 1, " active project", " active projects" )
        & " in scope  ·  test plans hidden"
""", folder="Story\\Navigation",
    desc="One line under every story headline: which slicers are set and how many active projects the page covers.")
pbir.EXTENSION_MEASURES.add(FILTER_MEASURE)


def _chapter_of(key, names, chapters):
    if key == "home":
        return "home"
    code = layout._code(names[key])
    if not code:
        return None
    return next((c for c in chapters if layout._code(names[c])[0] == code[0]), None)


def _ghost(target_pid, tip):
    v = nav_button("", target_pid, tip, fill=RAIL_BG, hover=RAIL_BG, press=RAIL_BG)
    v["objects"]["fill"] = [{"properties": {"show": b(True)}},
                            {"properties": {"fillColor": col_solid(RAIL_BG), "transparency": n(100)},
                             "selector": {"id": "default"}},
                            {"properties": {"fillColor": col_solid("#FFFFFF"), "transparency": n(88)},
                             "selector": {"id": "hover"}}]
    return layout._alt(v, tip)


def _rail(pg, current, pid, limit):
    pg.add(0, 0, RAIL_W, limit - 8, shape(RAIL_BG), key="rail_bg")
    for k, (icon, target, label) in enumerate(RAIL):
        y = TOP + k * STEP
        x = (RAIL_W - TILE) / 2
        on = target == current
        if on:
            pg.add(x, y, TILE, TILE + 14, shape(ORANGE, radius=10), key=f"rail_on_{icon}")
        pg.add(x + 13, y + 6, 30, 30, image(f"rail-{icon}-{'white' if on else 'grey'}.png", f"{label} icon"),
               key=f"rail_img_{icon}")
        pg.add(0, y + 40, RAIL_W, 24, textbox([[(label, st("Segoe UI", 8, "#FFFFFF" if on else RAIL_INK, on))]],
                                              align="center"), key=f"rail_lbl_{icon}")
        if not on:
            pg.add(x, y, TILE, TILE + 14, _ghost(pid[target], f"Open {label}"), key=f"rail_btn_{icon}")


NO_STRIP = {"recon"}                 # the reconciliation page shows every source itself
BAR_W = 1000                         # filter context left, data-confidence strip right


def _filter_bar(pg, y, chapter, no_strip=False):
    v = headline(FILTER_MEASURE, bg="#F4F5F7", border=BORDER, size=10, colour=MUTED)
    strip = chapter in confidence.CHAPTER_CHECKS and not no_strip
    pg.add(16, y, BAR_W if strip else 1768, BAR_H, layout._alt(v, "Filters applied to this page"), key="filter_bar")
    if strip:
        s_ = headline(confidence.strip(chapter), bg="#FFFFFF", border=BORDER, size=10)
        s_["objects"]["labels"][0]["properties"]["color"] = pbir.measure_colour(confidence.strip_colour(chapter))
        pg.add(16 + BAR_W + 10, y, 1768 - BAR_W - 10, BAR_H,
               layout._alt(s_, "Data confidence: share of active projects that have the data this chapter uses"),
               key="confidence_strip")


def apply(built, pid, key_of, names, chapters, bar_y):
    """Filter bar on every chapter / deep-dive page, then shift the page right and draw the rail."""
    for pg in built:
        key = key_of.get(pg.id)
        current = _chapter_of(key, names, chapters)
        if current is None:
            continue
        if key != "home":
            _filter_bar(pg, bar_y, current, no_strip=key in NO_STRIP)
        for vc in pg.visuals:
            if "parentGroupName" not in vc:
                vc["position"]["x"] = round(vc["position"]["x"] + RAIL_W, 2)
        pg.page["width"] += RAIL_W
        pg.width += RAIL_W
        bg = pg.page["objects"].get("background", [{}])[0].get("properties", {})
        banded = "image" in bg
        if banded and pg.page["height"] == 1058:
            img = bg["image"]["image"]
            img["name"] = pbir.s(BG_WIDE)
            img["url"]["expr"]["ResourcePackageItem"]["ItemName"] = BG_WIDE
        _rail(pg, current, pid, round(pg.page["height"] * (0.928 if banded else 1)))


def register(out):
    """Copy the wide footer band into the written report and list it under RegisteredResources."""
    rj = out / "definition" / "report.json"
    rep = json.loads(rj.read_text(encoding="utf-8"))
    reg = next(p for p in rep["resourcePackages"] if p["type"] == "RegisteredResources")
    if BG_WIDE not in {i["name"] for i in reg["items"]}:
        reg["items"].append({"name": BG_WIDE, "path": BG_WIDE, "type": "Image"})
    shutil.copy(BG_FILE, out / "StaticResources" / "RegisteredResources" / BG_WIDE)
    rj.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
