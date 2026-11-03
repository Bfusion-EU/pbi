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
            kind = f.get("Measure") or f.get("Column") or {}
            name = _nice(kind.get("Property", ""))
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


def _image_label(v):
    """Display name stored by pbir.image (filename-derived when empty)."""
    img = v["objects"]["image"][0]["properties"]["sourceFile"]["image"]
    name = _lit(img.get("name"))
    if not name:
        item = img["url"]["expr"]["ResourcePackageItem"]["ItemName"]
        stem = re.sub(r"\.\w+$", "", item)
        stem = re.sub(r"^rail-|-(grey|white)$", "", stem)
        name = re.sub(r"\d{6,}$", "", stem).replace("_", " ").replace("-", " ").strip()
    return name


def _is_linked(v):
    return "visualLink" in v.get("visualContainerObjects", {})


def alt_text(v):
    """Alt text for one visual, or '' when it gets none (value-bearing / decorative: read natively)."""
    t = v["visualType"]
    if t in NO_ALT:
        return ""
    if t == "slicer":
        return "Filter: " + _slicer_label(v)
    if t == "actionButton":
        if _button_text(v) == "›" and "visualLink" not in v.get("visualContainerObjects", {}):
            return ""                                              # breadcrumb separator: decorative
        return _button_text(v) or _button_tooltip(v) or "Button"
    if t == "image":
        name = _image_label(v)
        if re.search(r"(^|\s)logo$", name, re.I):
            return "Logo: " + re.sub(r"\s*logo$", "", name, flags=re.I).strip()
        if not _is_linked(v):
            return ""
        return "Icon: " + (re.sub(r"\s+icon$", "", name, flags=re.I).strip() or name)
    title = _title_text(v)
    if title:
        return "KPI: " + title if t == "card" else title
    return ""   # untitled card/table/chart: value read natively; charts may carry a caller-supplied label


def _set_alt(v, text):
    gen = v.setdefault("visualContainerObjects", {}).setdefault("general", [{"properties": {}}])
    props = gen[0].setdefault("properties", {})
    if "altText" not in props:
        props["altText"] = pbir.s(text[:MAX_ALT])


def _only_text(v):
    """All text of a textbox visual, concatenated."""
    paras = v.get("objects", {}).get("general", [{}])[0].get("properties", {}).get("paragraphs", [])
    return "".join(r.get("value", "") for p in paras for r in p.get("textRuns", [])).strip()


def _decorative(vc):
    v = vc.get("visual")
    if v is None:
        return False
    if v["visualType"] == "textbox" and _only_text(v) == "›":      # breadcrumb separator
        return True
    if v["visualType"] == "actionButton" and "visualLink" not in v.get("visualContainerObjects", {})             and _button_text(v) == "›":                            # breadcrumb separator drawn as a button
        return True
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
