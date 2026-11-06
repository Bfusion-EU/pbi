"""Build the 'OneDashboards - Insights' PBIP (native visuals only).

    python build.py            # writes ../OneDashboards - Insights.pbip + .Report
    python build.py --check    # build + validate JSON schemas and model references

Reads the reference pack (OneDashboards - Bfusion) for the dataset connection,
theme, report filters and background images, and the semantic model .bim for
reference validation.
"""
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REF = ROOT.parent / "OneDashboards - Bfusion.Report"
BIM = Path(r"C:\Users\HassanBezzizi\repos\BFusion-Apps\SemanticModel\ModeL360Star.bim")
NAME = "OneDashboards - Insights"
BOARD_NAME = "OneDashboards - Board Pack"
# INSIGHTS_OUT lets parallel workers build into their own folder (validation only)
OUT = Path(os.environ["INSIGHTS_OUT"]) / f"{NAME}.Report" if os.environ.get("INSIGHTS_OUT") else ROOT / f"{NAME}.Report"
BOARD_OUT = OUT.parent / f"{BOARD_NAME}.Report"

sys.path.insert(0, str(HERE))
import pbir  # noqa: E402
from story_measures import MEASURES  # noqa: E402
import pages  # noqa: E402
import extensions  # noqa: E402,F401  (registers extension measures)

pbir.EXTENSION_MEASURES.update(m["name"] for m in MEASURES)

RESOURCES = ["bfv5_footer_band_1800x1800.png", "bfv5_footer_band_1800x1000.png",
             "OnePlan_logo_-_dark_background9901469509814106.png"]
ICON_DIR = HERE / "assets" / "icons"
# the nine rail icons every report registers (Tabler, assets/make_icons.mjs) ...
BASE_ICON_KEYS = ["cc", "exec", "portfolio", "finance", "resources", "schedule", "risk", "benefits", "governance"]
ICONS = sorted(f"rail-{k}-{c}.png" for k in BASE_ICON_KEYS for c in ("grey", "white"))
# ... and the icons of chapters only a role report has (illustrations.RAIL_ICONS), registered where a page uses them
EXTRA_ICONS = sorted(p.name for p in ICON_DIR.glob("rail-*.png") if p.name not in ICONS)


def used_icons(pages_):
    """rail-*.png files the pages show, in RegisteredResources order: the nine base icons, then any extra ones."""
    used = set()
    for pg in pages_:
        for vc in pg.visuals:
            used.update(re.findall(r"rail-[\w-]+?-(?:grey|white)\.png", json.dumps(vc)))
    unknown = used - set(ICONS) - set(EXTRA_ICONS)
    assert not unknown, f"rail icon(s) used but not in {ICON_DIR}: {sorted(unknown)}"
    return ICONS + [i for i in EXTRA_ICONS if i in used]


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_model():
    m = json.loads(BIM.read_text(encoding="utf-8-sig"))["model"]
    cols, meas = set(), set()
    for t in m["tables"]:
        for c in t.get("columns", []):
            cols.add((t["name"], c["name"]))
        for x in t.get("measures", []):
            meas.add(x["name"])
    return cols, meas


def extension_json(model_measures):
    ext_names = {m["name"] for m in MEASURES}
    out = []
    for m in MEASURES:
        refs = []
        expr = re.sub(r'"[^"]*"', '""', m["expression"])  # ignore string literals
        for name in dict.fromkeys(re.findall(r"(?<![\w\]'])\[([^\]@][^\]]*)\]", expr)):
            if name in ext_names and name != m["name"]:
                refs.append({"schema": "extension", "entity": "_Measures", "name": name})
            elif name in model_measures:
                refs.append({"entity": "_Measures", "name": name})
        item = {"name": m["name"], "dataType": m["dataType"], "expression": m["expression"],
                "displayFolder": m["displayFolder"]}
        if m.get("formatString"):
            item["formatString"] = m["formatString"]
        if m.get("description"):
            item["description"] = m["description"]
        if refs:
            item["references"] = {"measures": refs}
        out.append(item)
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/reportExtension/1.0.0/schema.json",
            "name": "extension", "entities": [{"name": "_Measures", "measures": out}]}


def report_json(extra_filters=None, icons=ICONS):
    ref = json.loads((REF / "definition" / "report.json").read_text(encoding="utf-8"))
    keep = []
    seen = set()
    for f in ref["filterConfig"]["filters"]:
        fld = f["field"].get("Column", {})
        key = (fld.get("Expression", {}).get("SourceRef", {}).get("Entity"), fld.get("Property"),
               json.dumps(f.get("filter", {}).get("Where")))
        if key[0] in ("NavMenu", "Period Grain") or key in seen:
            continue
        seen.add(key)
        keep.append(f)
    rp = [p for p in ref["resourcePackages"] if p["type"] == "SharedResources"]
    rp.append({"name": "RegisteredResources", "type": "RegisteredResources",
               "items": [{"name": r, "path": r, "type": "Image"} for r in RESOURCES + icons]})
    rp[-1]["items"].append({"name": pbir.THEME_FILE, "path": pbir.THEME_FILE, "type": "CustomTheme"})
    themes = dict(ref["themeCollection"])
    themes["customTheme"] = {"name": pbir.THEME_FILE, "reportVersionAtImport": themes["baseTheme"]["reportVersionAtImport"],
                             "type": "RegisteredResources"}
    return {"$schema": ref["$schema"], "themeCollection": themes,
            "filterConfig": {"filters": keep + list(extra_filters or [])}, "objects": ref.get("objects", {}),
            "resourcePackages": rp, "settings": ref["settings"],
            "slowDataSourceSettings": ref.get("slowDataSourceSettings", {})}


def write_report(name, pages_, bookmarks, out_dir, extra_filters=None):
    """Write one complete PBIR report (<out_dir>/<name>.pbip + <name>.Report) and return the .Report folder."""
    out_dir = Path(out_dir)
    out = out_dir / f"{name}.Report"
    if out.exists():
        shutil.rmtree(out)
    # pbip + item metadata
    dump(out_dir / f"{name}.pbip", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
                                    "version": "1.0", "artifacts": [{"report": {"path": f"{name}.Report"}}],
                                    "settings": {"enableAutoRecovery": True}})
    plat = json.loads((REF / ".platform").read_text(encoding="utf-8"))
    plat["metadata"]["displayName"] = name
    plat["config"]["logicalId"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "bfusion/" + name))
    dump(out / ".platform", plat)
    shutil.copy(REF / "definition.pbir", out / "definition.pbir")
    (out / "definition").mkdir(parents=True, exist_ok=True)
    shutil.copy(REF / "definition" / "version.json", out / "definition" / "version.json")
    for r in RESOURCES:
        dst = out / "StaticResources" / "RegisteredResources" / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REF / "StaticResources" / "RegisteredResources" / r, dst)
    icons = used_icons(pages_)
    for r in icons:
        dst = out / "StaticResources" / "RegisteredResources" / r
        shutil.copy(ICON_DIR / r, dst)
    dump(out / "StaticResources" / "RegisteredResources" / pbir.THEME_FILE, pbir.theme())
    _, model_measures = load_model()
    dump(out / "definition" / "report.json", report_json(extra_filters, icons))
    dump(out / "definition" / "reportExtensions.json", extension_json(model_measures))
    for pg in pages_:
        base = out / "definition" / "pages" / pg.id
        dump(base / "page.json", pg.page)
        for vc in pg.visuals:
            dump(base / "visuals" / vc["name"] / "visual.json", vc)
    dump(out / "definition" / "pages" / "pages.json",
         {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
          "pageOrder": [pg.id for pg in pages_], "activePageName": pages_[0].id})
    if bookmarks:
        bdir = out / "definition" / "bookmarks"
        for bm in bookmarks:
            dump(bdir / f"{bm['name']}.bookmark.json", bm)
        dump(bdir / "bookmarks.json",
             {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
              "items": [{"name": bm["name"]} for bm in bookmarks]})
    return out


def build():
    missing = [i for i in ICONS if not (ICON_DIR / i).exists()]
    assert not missing and len(EXTRA_ICONS) == 16, (f"expected the 9 base rail icons and 8 role-chapter icons "
                                                    f"(white/grey) in {ICON_DIR}: missing {missing}, extra {EXTRA_ICONS}")
    built = pages.build_all()
    out = write_report(NAME, built, pbir.BOOKMARKS, OUT.parent)
    import entry
    entry.register_resources(out)      # BFusion logo and the brief-page drawings
    print(f"built {len(built)} pages, {sum(len(p.visuals) for p in built)} visuals, {len(MEASURES)} story measures -> {OUT}")
    print("act_first skipped (custom layouts):", ", ".join(n.replace(" · ", " - ") for n in pages.LAYOUT_SKIPPED) or "none")
    return built


def build_board_pack():
    import board
    built = board.build_board()
    with pbir.font_bump(False):                 # its theme too: the Board Pack keeps its type sizes
        write_report(BOARD_NAME, built, [], OUT.parent, extra_filters=[board.period_filter()])
    print(f"built {len(built)} board slides, {sum(len(p.visuals) for p in built)} visuals -> {BOARD_OUT}")
    return built


# ------------------------------------------------------------------ checks
def layout_errors(pages_):
    """Visuals must sit inside the page and above the footer band. Child positions are stored relative to their
    parent group, so they are resolved to page coordinates first."""
    out = []
    for pg in pages_:
        banded = "image" in pg.page.get("objects", {}).get("background", [{}])[0].get("properties", {})
        limit = pg.height * 0.928 if banded else pg.height        # banded pages keep clear of the footer band
        groups = {v["name"]: v["position"] for v in pg.visuals}
        for vc in pg.visuals:
            p = dict(vc["position"])
            if vc.get("parentGroupName"):
                gp = groups[vc["parentGroupName"]]
                p["x"] += gp["x"]
                p["y"] += gp["y"]
            if p["x"] < 0 or p["x"] + p["width"] > pg.width + 0.5 or p["y"] + p["height"] > limit:
                out.append(f"LAYOUT {pg.display}: {vc.get('visual', {}).get('visualType', 'group')} at {p} outside page/footer")
    return out


CARD_TYPES = {"card", "cardVisual", "multiRowCard"}


card_need_px = pbir.card_need_px      # value_pt * 2.5 + label_pt * 1.6, pt -> px
card_fonts = pbir.card_fonts          # (value pt, label pt) of a card visual


def card_errors(pages_):
    """Every card visual must be tall enough for its value and label at their font sizes (card_need_px)."""
    out = []
    for pg in pages_:
        for vc in pg.visuals:
            v = vc.get("visual", {})
            if v.get("visualType") not in CARD_TYPES:
                continue
            value, label = card_fonts(v)
            need = card_need_px(value, label)
            if vc["position"]["height"] + 0.5 < need:
                out.append(f"CARD {pg.display}: {v['visualType']} {vc['name']} is {vc['position']['height']} px tall, "
                           f"needs {need:.0f} px ({value:g} pt value + {label:g} pt label)")
    return out


def check(built, out, cards=True):
    """cards=False: skip the card-height rule (the Board Pack keeps its frozen layout)."""
    import jsonschema
    from referencing import Registry, Resource
    import urllib.request

    cache = HERE / ".schema-cache"
    cache.mkdir(exist_ok=True)

    def retrieve(uri):
        f = cache / re.sub(r"[^\w.]", "_", uri)
        if not f.exists():
            with urllib.request.urlopen(uri) as r:
                f.write_bytes(r.read())
        return Resource.from_contents(json.loads(f.read_text(encoding="utf-8")))

    registry = Registry(retrieve=retrieve)
    errors = 0
    files = sorted(out.rglob("*.json"))
    for f in files:
        if f.name == "localSettings.json":
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        sch = doc.get("$schema")
        if not sch:
            continue
        schema = retrieve(sch).contents
        v = jsonschema.Draft7Validator(schema, registry=registry)
        errs = list(v.iter_errors(doc))
        for e in errs[:5]:
            errors += 1
            print(f"SCHEMA {f.relative_to(out)}: {'/'.join(map(str, e.absolute_path))}: {e.message[:200]}")
    print(f"schema-checked {len(files)} files")

    cols, meas = load_model()
    ext = {m["name"] for m in MEASURES}
    missing = set()

    def walk(o):
        if isinstance(o, dict):
            if "Measure" in o and isinstance(o["Measure"], dict) and "Property" in o["Measure"]:
                sr = o["Measure"]["Expression"].get("SourceRef", {})
                nm = o["Measure"]["Property"]
                if sr.get("Schema") == "extension":
                    if nm not in ext:
                        missing.add(("ext-measure", nm))
                elif nm not in meas:
                    missing.add(("measure", nm))
            if "Column" in o and isinstance(o["Column"], dict) and "Property" in o["Column"]:
                sr = o["Column"]["Expression"].get("SourceRef", {})
                if "Entity" in sr and (sr["Entity"], o["Column"]["Property"]) not in cols:
                    missing.add(("column", f"{sr['Entity']}[{o['Column']['Property']}]"))
            if "From" in o and isinstance(o["From"], list):
                for fr in o["From"]:
                    pass
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for f in out.rglob("visual.json"):
        walk(json.loads(f.read_text(encoding="utf-8")))
    walk(json.loads((out / "definition" / "report.json").read_text(encoding="utf-8")))
    # filter column refs use Source aliases; check field entries
    for f in out.rglob("visual.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        for flt in d.get("filterConfig", {}).get("filters", []):
            c = flt["field"].get("Column")
            if c is None:  # measure filter: the generic walk() above already checks the measure
                continue
            if (c["Expression"]["SourceRef"]["Entity"], c["Property"]) not in cols:
                missing.add(("filter column", c["Property"]))
    # DAX references in story measures
    for m in MEASURES:
        expr = re.sub(r'"[^"]*"', '""', m["expression"])
        for t, c in re.findall(r"(\w+|'[^']+')\[([^\]]+)\]", expr):
            if (t.strip("'"), c) not in cols:
                missing.add(("dax column", f"{m['name']} -> {t}[{c}]"))
        for nm in re.findall(r"(?<![\w\]'])\[([^\]]+)\]", expr):
            if nm.startswith("@"):
                continue
            if nm not in meas and nm not in ext:
                missing.add(("dax measure", f"{m['name']} -> [{nm}]"))
        if expr.count("(") != expr.count(")"):
            missing.add(("dax parens", m["name"]))
    for kind, nm in sorted(missing):
        errors += 1
        print(f"REF {kind}: {nm}")
    for msg in layout_errors(built) + (card_errors(built) if cards else []):
        errors += 1
        print(msg)
    print("OK" if errors == 0 else f"{errors} problem(s)")
    return errors


if __name__ == "__main__":
    b = build()
    bb = build_board_pack()
    if "--check" in sys.argv:
        e1 = check(b, OUT)
        e2 = check(bb, BOARD_OUT, cards=False)
        tot = (e1 or 0) + (e2 or 0)
        print("OK" if tot == 0 else f"FAILED ({tot} problem(s))")
        sys.exit(1 if tot else 0)
