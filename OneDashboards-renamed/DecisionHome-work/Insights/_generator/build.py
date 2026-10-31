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
# INSIGHTS_OUT lets parallel workers build into their own folder (validation only)
OUT = Path(os.environ["INSIGHTS_OUT"]) / f"{NAME}.Report" if os.environ.get("INSIGHTS_OUT") else ROOT / f"{NAME}.Report"

sys.path.insert(0, str(HERE))
import pbir  # noqa: E402
from story_measures import MEASURES  # noqa: E402
import pages  # noqa: E402
import extensions  # noqa: E402,F401  (registers extension measures)

pbir.EXTENSION_MEASURES.update(m["name"] for m in MEASURES)

RESOURCES = ["bfv5_footer_band_1800x1800.png", "bfv5_footer_band_1800x1000.png",
             "OnePlan_logo_-_dark_background9901469509814106.png"]
ICON_DIR = HERE / "assets" / "icons"
ICONS = sorted(p.name for p in ICON_DIR.glob("rail-*.png"))


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


def report_json():
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
               "items": [{"name": r, "path": r, "type": "Image"} for r in RESOURCES + ICONS]})
    return {"$schema": ref["$schema"], "themeCollection": ref["themeCollection"],
            "filterConfig": {"filters": keep}, "objects": ref.get("objects", {}),
            "resourcePackages": rp, "settings": ref["settings"],
            "slowDataSourceSettings": ref.get("slowDataSourceSettings", {})}


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    # pbip + item metadata
    dump(OUT.parent / f"{NAME}.pbip", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
                                 "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                 "settings": {"enableAutoRecovery": True}})
    plat = json.loads((REF / ".platform").read_text(encoding="utf-8"))
    plat["metadata"]["displayName"] = NAME
    plat["config"]["logicalId"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "bfusion/" + NAME))
    dump(OUT / ".platform", plat)
    shutil.copy(REF / "definition.pbir", OUT / "definition.pbir")
    (OUT / "definition").mkdir(parents=True, exist_ok=True)
    shutil.copy(REF / "definition" / "version.json", OUT / "definition" / "version.json")
    for r in RESOURCES:
        dst = OUT / "StaticResources" / "RegisteredResources" / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REF / "StaticResources" / "RegisteredResources" / r, dst)
    for r in ICONS:
        dst = OUT / "StaticResources" / "RegisteredResources" / r
        shutil.copy(ICON_DIR / r, dst)
    _, model_measures = load_model()
    dump(OUT / "definition" / "report.json", report_json())
    dump(OUT / "definition" / "reportExtensions.json", extension_json(model_measures))
    built = pages.build_all()
    for pg in built:
        base = OUT / "definition" / "pages" / pg.id
        dump(base / "page.json", pg.page)
        for vc in pg.visuals:
            dump(base / "visuals" / vc["name"] / "visual.json", vc)
    dump(OUT / "definition" / "pages" / "pages.json",
         {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
          "pageOrder": [pg.id for pg in built], "activePageName": built[0].id})
    if pbir.BOOKMARKS:
        bdir = OUT / "definition" / "bookmarks"
        for bm in pbir.BOOKMARKS:
            dump(bdir / f"{bm['name']}.bookmark.json", bm)
        dump(bdir / "bookmarks.json",
             {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
              "items": [{"name": bm["name"]} for bm in pbir.BOOKMARKS]})
    print(f"built {len(built)} pages, {sum(len(p.visuals) for p in built)} visuals, {len(MEASURES)} story measures -> {OUT}")
    return built


# ------------------------------------------------------------------ checks
def check(built):
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
    files = sorted(OUT.rglob("*.json"))
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
            print(f"SCHEMA {f.relative_to(OUT)}: {'/'.join(map(str, e.absolute_path))}: {e.message[:200]}")
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

    for f in OUT.rglob("visual.json"):
        walk(json.loads(f.read_text(encoding="utf-8")))
    walk(json.loads((OUT / "definition" / "report.json").read_text(encoding="utf-8")))
    # filter column refs use Source aliases; check field entries
    for f in OUT.rglob("visual.json"):
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
    # layout: visuals inside page, above footer band
    for pg in built:
        limit = pg.height * 0.928 if pg.height == 1800 else pg.height
        groups = {v["name"]: v["position"] for v in pg.visuals}
        for vc in pg.visuals:
            p = dict(vc["position"])
            if vc.get("parentGroupName"):
                # child positions are stored relative to the parent group; resolve to page coordinates
                gp = groups[vc["parentGroupName"]]
                p["x"] += gp["x"]
                p["y"] += gp["y"]
            if p["x"] < 0 or p["x"] + p["width"] > pg.width + 0.5 or p["y"] + p["height"] > limit:
                errors += 1
                print(f"LAYOUT {pg.display}: {vc.get('visual', {}).get('visualType', 'group')} at {p} outside page/footer")
    print("OK" if errors == 0 else f"{errors} problem(s)")
    return errors


if __name__ == "__main__":
    b = build()
    if "--check" in sys.argv:
        sys.exit(1 if check(b) else 0)
