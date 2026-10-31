"""Small PBIR (Power BI enhanced report format) builder helpers.

Only native Power BI visuals. Every helper returns plain dicts that are
serialised as-is into definition/pages/<page>/visuals/<visual>/visual.json.
"""
import hashlib

VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

# BFusion palette (see Obsidian reference-brand-palette)
NAVY = "#1F2A44"
NAVY_BG = "#1E2A44"
NAVY_TILE = "#243352"
NAVY_LINE = "#2F3F63"
NAVY_BTN = "#33405F"
ORANGE = "#E8612A"
ORANGE_DK = "#C94E1C"
ORANGE_SOFT = "#FDF1EB"
PEACH = "#FFB38A"
TEAL = "#1E6D6E"
TEAL_LT = "#2C8B8B"
AMBER = "#D9A832"
RED = "#C0392B"
GREY = "#9AA3AF"
MUTED = "#666666"
BORDER = "#E3E6EC"
INK = "#2B2F36"
SLATE = "#A6B3CC"

HEALTH_COLOURS = {"(1) On Track": TEAL, "(2) At Risk": AMBER, "(3) Off Track": RED}

# Measures that live in reportExtensions.json (filled in by build script)
EXTENSION_MEASURES = set()


def uid(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:20]


# ---------- literals ----------
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def s(v):
    return lit("'" + str(v).replace("'", "''") + "'")


def n(v):
    return lit(f"{v}D")


def i(v):
    return lit(f"{v}L")


def b(v):
    return lit("true" if v else "false")


def col_solid(hexv):
    return {"solid": {"color": s(hexv)}}


# ---------- fields ----------
def M(name):
    src = {"Entity": "_Measures"}
    if name in EXTENSION_MEASURES:
        src = {"Schema": "extension", "Entity": "_Measures"}
    return {"Measure": {"Expression": {"SourceRef": src}, "Property": name}}


def C(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def qref(field):
    k = "Measure" if "Measure" in field else "Column"
    f = field[k]
    return f"{f['Expression']['SourceRef']['Entity']}.{f['Property']}"


def P(field, display=None, active=None):
    p = {"field": field, "queryRef": qref(field),
         "nativeQueryRef": display or field[("Measure" if "Measure" in field else "Column")]["Property"]}
    if display:
        p["displayName"] = display
    if active is not None:
        p["active"] = active
    return p


def measure_colour(name):
    """Colour driven by a text measure returning a hex code ("fx field value")."""
    return {"solid": {"color": {"expr": M(name)}}}


def wildcard_selector(field, matching=1):
    """Conditional-format selector for every cell of a field. matchingOption 1 = values only (default);
    0 = values and totals (matrix subtotal / total rows too, as Desktop saves it for 'Apply to: values and totals')."""
    return {"data": [{"dataViewWildcard": {"matchingOption": matching}}], "metadata": qref(field)}


def scope_selector(field, value):
    return {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": field,
                                                 "Right": {"Literal": {"Value": "'" + value.replace("'", "''") + "'"}}}}}]}


# ---------- container objects ----------
def title(text, size=12, colour=NAVY, show=True):
    return [{"properties": {"show": b(show), "text": s(text), "fontColor": col_solid(colour),
                            "fontSize": n(size), "fontFamily": s("Segoe UI Semibold")}}]


def panel(radius=6, bg="#FFFFFF", border=BORDER, show_bg=True, show_border=True):
    o = {"background": [{"properties": {"show": b(show_bg), "color": col_solid(bg), "transparency": n(0)}}],
         "border": [{"properties": {"show": b(show_border), "color": col_solid(border), "radius": n(radius)}}]}
    return o


def no_chrome():
    return {"background": [{"properties": {"show": b(False)}}],
            "border": [{"properties": {"show": b(False)}}],
            "dropShadow": [{"properties": {"show": b(False)}}]}


# ---------- filters ----------
def _lit_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return f"{v}D"
    return "'" + str(v).replace("'", "''") + "'"


def f_in(entity, prop, values, exclude=False):
    cond = {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}}],
                   "Values": [[{"Literal": {"Value": _lit_value(v)}}] for v in values]}}
    if exclude:
        cond = {"Not": {"Expression": cond}}
    return {"name": uid("f", entity, prop, values, exclude), "field": C(entity, prop), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": cond}]}, "howCreated": "User"}


def f_cmp(entity, prop, kind, value, int64=False):
    """kind: 0 =, 1 >, 2 >=, 3 <, 4 <=.  int64=True writes an Int64 literal (nL) for whole-number columns
    (the default for numbers is a Double literal, nD)."""
    litv = f"{int(value)}L" if int64 else _lit_value(value)
    cond = {"Comparison": {"ComparisonKind": kind,
                           "Left": {"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}},
                           "Right": {"Literal": {"Value": litv}}}}
    return {"name": uid("ci" if int64 else "c", entity, prop, kind, value), "field": C(entity, prop), "type": "Advanced",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": cond}]}, "howCreated": "User"}


def f_not_blank(entity, prop):
    cond = {"Not": {"Expression": {"Comparison": {"ComparisonKind": 0,
            "Left": {"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}},
            "Right": {"Literal": {"Value": "null"}}}}}}
    return {"name": uid("nb", entity, prop), "field": C(entity, prop), "type": "Advanced",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": cond}]}, "howCreated": "User"}


def f_between(entity, prop, lo, hi):
    """Advanced filter lo <= column <= hi. Integers are written as int64 literals (nL)."""
    def lv(v):
        return f"{v}L" if isinstance(v, int) and not isinstance(v, bool) else _lit_value(v)

    def cmp(kind, v):
        return {"Comparison": {"ComparisonKind": kind,
                               "Left": {"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}},
                               "Right": {"Literal": {"Value": lv(v)}}}}
    cond = {"And": {"Left": cmp(2, lo), "Right": cmp(4, hi)}}
    return {"name": uid("bt", entity, prop, lo, hi), "field": C(entity, prop), "type": "Advanced",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": cond}]}, "howCreated": "User"}


# ---------- page ----------
class Page:
    def __init__(self, pid, display, width=1800, height=1800, background_image=None, background_colour=None,
                 display_option="FitToWidth"):
        self.id = pid
        self.display = display
        self.width = width
        self.height = height
        self.visuals = []
        self.z = 1000
        obj = {}
        if background_image:
            obj["background"] = [{"properties": {
                "image": {"image": {"name": s(background_image),
                                    "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources",
                                                                             "PackageType": 1,
                                                                             "ItemName": background_image}}},
                                    "scaling": s("Fit")}},
                "transparency": n(0)}}]
        if background_colour:
            obj["background"] = [{"properties": {"color": col_solid(background_colour), "transparency": n(0)}}]
        self.page = {"$schema": PAGE_SCHEMA, "name": pid, "displayName": display, "displayOption": display_option,
                     "height": height, "width": width, "objects": obj}

    def add_filters(self, filters):
        """Page-level filters (filter pane 'Filters on this page')."""
        self.page.setdefault("filterConfig", {"filters": []})["filters"].extend(filters)

    def add(self, x, y, w, h, visual, filters=None, key=None, parent=None):
        """Add a visual. x/y are ABSOLUTE page coordinates; when parent (a group name from add_group) is set they are
        converted to group-relative, because PBIR stores child positions relative to the parent group (verified in Desktop)."""
        self.z += 100
        name = uid(self.id, key or len(self.visuals), visual.get("visualType"))
        if parent:
            grp = next((v for v in self.visuals if v["name"] == parent), None)
            if grp is None:
                raise ValueError(f"unknown parent group {parent!r}: add the group before its children")
            pp = grp["position"]
            x, y = x - pp["x"], y - pp["y"]
        vc = {"$schema": VC_SCHEMA, "name": name,
              "position": {"x": x, "y": y, "z": self.z, "width": w, "height": h, "tabOrder": self.z},
              "visual": visual}
        if filters:
            vc["filterConfig"] = {"filters": filters}
        if parent:
            vc["parentGroupName"] = parent
        self.visuals.append(vc)
        return vc

    def add_group(self, x, y, w, h, display_name, key, hidden=False):
        """Visual group container (no visual of its own). Children pass parent=<returned name>."""
        self.z += 100
        name = uid(self.id, key, "group")
        vc = {"$schema": VC_SCHEMA, "name": name,
              "position": {"x": x, "y": y, "z": self.z, "width": w, "height": h, "tabOrder": self.z},
              "visualGroup": {"displayName": display_name, "groupMode": "ScaleMode"}}
        if hidden:
            vc["isHidden"] = True
        self.visuals.append(vc)
        return name


# ---------- visual factories ----------
def textbox(runs, align=None):
    """runs: list of paragraphs; each paragraph is a list of (text, style dict)."""
    paras = []
    for para in runs:
        p = {"textRuns": [{"value": t, "textStyle": st} for t, st in para]}
        if align:
            p["horizontalTextAlignment"] = align
        paras.append(p)
    return {"visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": paras}}]},
            "visualContainerObjects": no_chrome(), "drillFilterOtherVisuals": True}


def st(font="Segoe UI", size=11, colour=MUTED, bold=False):
    d = {"fontFamily": font, "fontSize": f"{size}pt", "color": colour}
    if bold:
        d["fontWeight"] = "bold"
    return d


def shape(fill, radius=None, line=None):
    sh = {"tileShape": s("rectangleRounded" if radius else "rectangle")}
    if radius:
        sh["rectangleRoundedCurve"] = i(radius)
    outline = {"show": b(bool(line))}
    if line:
        outline.update({"lineColor": col_solid(line), "weight": i(1), "transparency": n(0)})
    return {"visualType": "shape",
            "objects": {"shape": [{"properties": sh}],
                        "fill": [{"properties": {"show": b(True), "fillColor": col_solid(fill), "transparency": n(0)},
                                  "selector": {"id": "default"}}],
                        "outline": [{"properties": outline, "selector": {"id": "default"}}]},
            "drillFilterOtherVisuals": True}


def nav_button(text, target_page, tooltip="", fill=ORANGE, hover=ORANGE_DK, press=NAVY, font="#FFFFFF",
               size=11, align="center", outline=None, radius=6, margin=12):
    return {"visualType": "actionButton",
            "objects": {
                "icon": [{"properties": {"shapeType": s("blank")}, "selector": {"id": "default"}},
                         {"properties": {"show": b(False)}}],
                "fill": [{"properties": {"show": b(True)}},
                         {"properties": {"fillColor": col_solid(fill), "transparency": n(0)}, "selector": {"id": "default"}},
                         {"properties": {"fillColor": col_solid(hover), "transparency": n(0)}, "selector": {"id": "hover"}},
                         {"properties": {"fillColor": col_solid(press), "transparency": n(0)}, "selector": {"id": "press"}}],
                "outline": ([{"properties": {"show": b(True)}},
                             {"properties": {"lineColor": col_solid(outline), "weight": i(1), "transparency": n(0)},
                              "selector": {"id": "default"}}] if outline else [{"properties": {"show": b(False)}}]),
                "text": [{"properties": {"show": b(True)}},
                         {"properties": {"text": s(text), "fontColor": col_solid(font), "fontSize": s(str(size)),
                                         "fontFamily": s("Segoe UI"), "bold": b(True),
                                         "horizontalAlignment": s(align), "leftMargin": n(margin)},
                          "selector": {"id": "default"}}],
                "shape": [{"properties": {"roundEdge": i(radius)}}]},
            "visualContainerObjects": {
                "visualLink": [{"properties": {"show": b(True), "type": s("PageNavigation"),
                                               "navigationSection": s(target_page), "tooltip": s(tooltip)}}],
                "border": [{"properties": {"show": b(False)}}],
                "background": [{"properties": {"show": b(False)}}]},
            "drillFilterOtherVisuals": True}


def home_icon_button(target_page, colour=ORANGE):
    return {"visualType": "actionButton",
            "objects": {"icon": [{"properties": {"shapeType": s("back"), "lineColor": col_solid(colour),
                                                 "iconSize": n(40)}, "selector": {"id": "default"}}],
                        "fill": [{"properties": {"show": b(False)}}]},
            "visualContainerObjects": {
                "visualLink": [{"properties": {"show": b(True), "type": s("PageNavigation"),
                                               "navigationSection": s(target_page),
                                               "tooltip": s("Back to the command center")}}],
                "border": [{"properties": {"show": b(False)}}],
                "background": [{"properties": {"show": b(False)}}]},
            "drillFilterOtherVisuals": True}

BOOKMARK_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/2.1.0/schema.json"
BOOKMARKS = []  # filled by page builders, written by build.py


def bookmark(display_name, key, page_id, groups_hidden):
    """Display-only bookmark: shows/hides visual groups on one page; data and slicers untouched."""
    name = uid("bookmark", key)
    BOOKMARKS.append({
        "$schema": BOOKMARK_SCHEMA, "displayName": display_name, "name": name,
        "options": {"suppressData": True, "applyOnlyToTargetVisuals": True,
                    "targetVisualNames": list(groups_hidden)},
        "explorationState": {"version": "1.3", "activeSection": page_id,
                             "sections": {page_id: {"visualContainers": {},
                                                    "visualContainerGroups": {g: {"isHidden": h}
                                                                              for g, h in groups_hidden.items()}}}}})
    return name


def _relink(btn, props):
    btn["visualContainerObjects"]["visualLink"] = [{"properties": props}]
    return btn


def bookmark_button(text, bookmark_name, tooltip="", **kw):
    return _relink(nav_button(text, "", tooltip, **kw),
                   {"show": b(True), "type": s("Bookmark"), "bookmark": s(bookmark_name), "tooltip": s(tooltip)})


def drill_button(text, target_page, tooltip="", **kw):
    return _relink(nav_button(text, "", tooltip, **kw),
                   {"show": b(True), "type": s("Drillthrough"), "drillthroughSection": s(target_page),
                    "tooltip": s(tooltip)})



def image(item_name, display_name):
    return {"visualType": "image",
            "objects": {"image": [{"properties": {"sourceFile": {"image": {
                "name": s(display_name),
                "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                                         "ItemName": item_name}}},
                "scaling": s("Normal")}}}}]},
            "drillFilterOtherVisuals": True}


def slicer(field, label, sync=True, dark=False, group=None):
    v = {"visualType": "slicer",
         "query": {"queryState": {"Values": {"projections": [P(field, label, active=True)]}}},
         "objects": {
             "data": [{"properties": {"mode": s("Dropdown")}}],
             "header": [{"properties": {"fontFamily": s("Segoe UI Semibold"), "textSize": n(10),
                                        "fontColor": col_solid("#FFFFFF" if dark else NAVY)}}],
             "items": [{"properties": {"fontFamily": s("Segoe UI"), "textSize": n(10)}}],
             "selection": [{"properties": {"strictSingleSelect": b(False), "selectAllCheckboxEnabled": b(True)}}]},
         "visualContainerObjects": {"background": [{"properties": {"show": b(False)}}],
                                    "border": [{"properties": {"show": b(False)}}]},
         "drillFilterOtherVisuals": True}
    if sync:
        # group key = Entity.Property, so two tables with the same column name never sync by accident; pass
        # group= to keep a slicer out of the report-wide sync (e.g. the Gantt's own Year window)
        v["syncGroup"] = {"groupName": group or qref(field), "fieldChanges": True, "filterChanges": True}
    return v


def card(measure, label, value_colour=NAVY, colour_measure=None, size=24, units=0, dark=False):
    labels = {"fontSize": n(size), "color": measure_colour(colour_measure) if colour_measure else col_solid(value_colour),
              "labelDisplayUnits": n(units)}
    vco = {"title": title(label, 11, "#FFFFFF" if dark else NAVY)}
    if dark:
        vco.update(panel(8, NAVY_TILE, NAVY_LINE))
    else:
        vco.update(panel(6))
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [P(M(measure))]}}},
            "objects": {"categoryLabels": [{"properties": {"show": b(False)}}], "labels": [{"properties": labels}]},
            "visualContainerObjects": vco, "drillFilterOtherVisuals": True}


def headline(measure, bg=ORANGE_SOFT, border=ORANGE, size=13, colour=NAVY):
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [P(M(measure))]}}},
            "objects": {"categoryLabels": [{"properties": {"show": b(False)}}],
                        "labels": [{"properties": {"fontSize": n(size), "color": col_solid(colour),
                                                   "fontFamily": s("Segoe UI")}}],
                        "wordWrap": [{"properties": {"show": b(True)}}]},
            "visualContainerObjects": {"title": [{"properties": {"show": b(False)}}],
                                       "background": [{"properties": {"show": b(True), "color": col_solid(bg)}}],
                                       "border": [{"properties": {"show": b(True), "color": col_solid(border),
                                                                  "radius": n(6)}}]},
            "drillFilterOtherVisuals": True}


def chart(vtype, roles, ttl, objects=None, sort=None, extra_vco=None):
    """roles: {"Category": [proj,...], "Y": [...]}"""
    q = {"queryState": {k: {"projections": v} for k, v in roles.items()}}
    if sort:
        q["sortDefinition"] = {"sort": [{"field": f, "direction": d} for f, d in sort], "isDefaultSort": False}
    vco = {"title": title(ttl)}
    vco.update(panel(6))
    if extra_vco:
        vco.update(extra_vco)
    v = {"visualType": vtype, "query": q, "visualContainerObjects": vco, "drillFilterOtherVisuals": True}
    if objects:
        v["objects"] = objects
    return v


def legend(pos="Top", show=True):
    return [{"properties": {"show": b(show), "position": s(pos), "fontSize": n(9)}}]


def labels_on(show=True, units=0, size=9):
    return [{"properties": {"show": b(show), "labelDisplayUnits": n(units), "fontSize": n(size)}}]


def series_colours(series_field, mapping):
    return [{"properties": {"fill": col_solid(c)}, "selector": scope_selector(series_field, k)} for k, c in mapping.items()]


def measure_fill(measure_field, hexv):
    return {"properties": {"fill": col_solid(hexv)}, "selector": {"metadata": qref(measure_field)}}


def table_style(font=10, header_bg=NAVY):
    return {"columnHeaders": [{"properties": {"backColor": col_solid(header_bg), "fontColor": col_solid("#FFFFFF"),
                                              "bold": b(True), "fontSize": n(font), "wordWrap": b(True)}}],
            "values": [{"properties": {"fontSize": n(font),
                                       "fontColorPrimary": col_solid(INK), "backColorPrimary": col_solid("#FFFFFF"),
                                       "fontColorSecondary": col_solid(INK), "backColorSecondary": col_solid("#F7F8FA")}}],
            "grid": [{"properties": {"gridHorizontal": b(True), "gridHorizontalColor": col_solid(BORDER),
                                     "rowPadding": n(4)}}]}


def cf_font(field, colour_measure, matching=1):
    return {"properties": {"fontColor": measure_colour(colour_measure)}, "selector": wildcard_selector(field, matching)}


def cf_back(field, colour_measure, matching=1):
    return {"properties": {"backColor": measure_colour(colour_measure)}, "selector": wildcard_selector(field, matching)}
