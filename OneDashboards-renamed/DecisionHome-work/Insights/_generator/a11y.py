"""Accessibility pass over built pages: alt text on content visuals, tab order in reading order."""
import re
from collections import defaultdict

import pbir

MAX_ALT = 250
DECORATIVE = {"shape"}          # plus images without a click action (see _decorative)
NO_ALT = {"textbox", "shape"}   # screen readers read textboxes; shapes are decorative


def _lit(prop):
    """Python string behind a pbir.s(...) literal, or '' when absent."""
    val = prop.get("expr", {}).get("Literal", {}).get("Value", "") if isinstance(prop, dict) else ""
    return val[1:-1].replace("''", "'") if len(val) >= 2 and val[0] == val[-1] == "'" else ""


def _nice(prop_name):
    """Measure / column name -> plain words ('Story | Home · Chip' -> 'Home: Chip')."""
    return prop_name.replace("Story | ", "").replace(" · ", ": ").strip()


def _title_text(v):
    props = v.get("visualContainerObjects", {}).get("title", [{}])[0].get("properties", {})
    return _lit(props.get("text"))


def _field_names(v):
    """Distinct display names of the visual's projected fields (fallback for untitled visuals)."""
    out = []
    for role in v.get("query", {}).get("queryState", {}).values():
        for pr in role.get("projections", []):
            f = pr["field"]
            name = _nice(f[("Measure" if "Measure" in f else "Column")]["Property"])
            if name and name not in out:
                out.append(name)
    return out


def _slicer_label(v):
    pr = v["query"]["queryState"]["Values"]["projections"][0]
    return pr.get("displayName") or pr["nativeQueryRef"]


def _button_text(v):
    for entry in v.get("objects", {}).get("text", []):
        txt = _lit(entry.get("properties", {}).get("text"))
        if txt:
            return txt
    return ""


def _button_tooltip(v):
    link = v.get("visualContainerObjects", {}).get("visualLink", [{}])[0].get("properties", {})
    return _lit(link.get("tooltip"))


def _image_name(v):
    item = v["objects"]["image"][0]["properties"]["sourceFile"]["image"]["url"]["expr"]["ResourcePackageItem"]["ItemName"]
    stem = re.sub(r"\.\w+$", "", item)
    stem = re.sub(r"^rail-|-(grey|white)$", "", stem)
    return re.sub(r"\d{6,}$", "", stem).replace("_", " ").replace("-", " ").strip()


def alt_text(v):
    """Alt text for one visual, or '' when it gets none."""
    t = v["visualType"]
    if t in NO_ALT:
        return ""
    if t == "slicer":
        return "Filter: " + _slicer_label(v)
    if t == "actionButton":
        return _button_text(v) or _button_tooltip(v) or "Button"
    if t == "image":
        return "Icon: " + _image_name(v)
    text = _title_text(v) or ", ".join(_field_names(v)[:3]) or t
    return "KPI: " + text if t == "card" else text


def _set_alt(v, text):
    gen = v.setdefault("visualContainerObjects", {}).setdefault("general", [{"properties": {}}])
    props = gen[0].setdefault("properties", {})
    if "altText" not in props:
        props["altText"] = pbir.s(text[:MAX_ALT])


def _decorative(vc):
    v = vc.get("visual")
    if v is None:
        return False
    return v["visualType"] in DECORATIVE or (
        v["visualType"] == "image" and "visualLink" not in v.get("visualContainerObjects", {}))


def _renumber(vcs):
    """Content first, then decorative; each in (y, x) order; step 100."""
    ordered = sorted(vcs, key=lambda vc: (_decorative(vc), vc["position"]["y"], vc["position"]["x"]))
    for k, vc in enumerate(ordered, 1):
        vc["position"]["tabOrder"] = k * 100


def apply(pages):
    """Alt text on every content visual and reading-order tab order, on every page."""
    for pg in pages:
        by_parent = defaultdict(list)
        for vc in pg.visuals:
            by_parent[vc.get("parentGroupName")].append(vc)
            if "visual" in vc:
                text = alt_text(vc["visual"])
                if text:
                    _set_alt(vc["visual"], text)
        for vcs in by_parent.values():
            _renumber(vcs)
