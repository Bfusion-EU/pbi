"""Client-facing polish over built pages: one commercial license key on every BFusion visual, no raw field-name titles.

Custom visuals are copied from the source pack with whatever Format-pane license key and title they carried there
(trial keys, 'Modeler | Priority Score', no title at all so Power BI writes 'A | B by C'). This pass runs last, so
the published story never shows a trial watermark or a measure name as a heading.
"""
from pathlib import Path

from pbir import b, i, s
from story_measures import MONEY_EUR

HERE = Path(__file__).resolve().parent
LICENSE_FILE = HERE / "assets" / "license.key"      # BFUSION premium, non-trial (license-tools/issued, v2 tier-only)
CUSTOM = ("bfusion", "portfolioRoadmap")
NO_TITLE = {"textbox", "shape", "image", "actionButton", "slicer"}


def license_key():
    if not LICENSE_FILE.exists():   # not in git: copy the BFUSION premium token from license-tools/issued
        raise FileNotFoundError(f"{LICENSE_FILE} missing: put the BFUSION commercial license token there")
    return LICENSE_FILE.read_text(encoding="utf-8").strip()


def _lit(props, key):
    return props.get(key, {}).get("expr", {}).get("Literal", {}).get("Value")


def _set_license(v, key):
    obj = v.setdefault("objects", {}).setdefault("licenseSettings", [{"properties": {}}])
    obj[0].setdefault("properties", {})["licenseKey"] = s(key)


def _clean_titles(v):
    vco = v.setdefault("visualContainerObjects", {})
    # Power BI fills an unset subtitle with the field list ('Sum of X by Y'); story pages never use one
    sub = vco.setdefault("subTitle", [{"properties": {}}])[0].setdefault("properties", {})
    if _lit(sub, "text") is None:
        sub["show"] = b(False)
    if not v.get("visualType", "").startswith(CUSTOM):
        return
    tp = vco.setdefault("title", [{"properties": {}}])[0].setdefault("properties", {})
    text = (_lit(tp, "text") or "").strip("'").strip()
    if not text or "|" in text:        # missing (auto 'A | B by C') or a measure name: the band label says it
        tp["show"] = b(False)
    elif text != (_lit(tp, "text") or "").strip("'"):
        tp["text"] = s(text)


# card measures whose model format string the report cannot change: counts stored as decimals ('Open changes 1.00')
WHOLE = {"Project | Active Changes"}


def _card_measure(v):
    pr = v.get("query", {}).get("queryState", {}).get("Values", {}).get("projections", [{}])[0].get("field", {})
    return (pr.get("Measure") or pr.get("Column") or {}).get("Property")


def _card_format(v):
    m = _card_measure(v)
    precision = 1 if m in MONEY_EUR else 0 if m in WHOLE else None
    if precision is not None:
        lab = v.setdefault("objects", {}).setdefault("labels", [{"properties": {}}])[0].setdefault("properties", {})
        lab["labelPrecision"] = i(precision)


def apply(built):
    key = license_key()
    for pg in built:
        for vc in pg.visuals:
            v = vc.get("visual")
            if not v or v.get("visualType") in NO_TITLE:
                continue
            if v.get("visualType", "").startswith(CUSTOM):
                _set_license(v, key)
            if v.get("visualType") == "card":
                _card_format(v)
            _clean_titles(v)


def errors(built):
    """Check: no trial or stale key, no visible measure-name title, no auto subtitle."""
    key, out = license_key(), []
    for pg in built:
        for vc in pg.visuals:
            v = vc.get("visual") or {}
            t = v.get("visualType", "")
            if t in NO_TITLE or not t:
                continue
            where = f"{pg.display}: {t[:40]}"
            vco = v.get("visualContainerObjects", {})
            if t.startswith(CUSTOM):
                lk = v.get("objects", {}).get("licenseSettings", [{}])[0].get("properties", {})
                if _lit(lk, "licenseKey") != f"'{key}'":
                    out.append(f"POLISH {where}: license key is not the commercial key")
                tp = vco.get("title", [{}])[0].get("properties", {})
                if _lit(tp, "show") != "false" and "|" in (_lit(tp, "text") or "|"):
                    out.append(f"POLISH {where}: visible auto or measure-name title")
            sp = vco.get("subTitle", [{}])[0].get("properties", {})
            if _lit(sp, "show") is None and _lit(sp, "text") is None:
                out.append(f"POLISH {where}: subtitle left to Power BI's field list")
    return out
