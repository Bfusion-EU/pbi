"""App links between the Story reports. Fill app_links.json once after the first app publish:

    app_id      the id after /apps/ in the app's address
    reports.*   the WORKSPACE report id (the id after /reports/ when the report is open in its workspace). App URLs
                take the workspace id: an app-side copy id (Power BI REST apps/{id}/reports .id) gives "couldn't
                find that report"; that API lists the workspace id as originalReportObjectId.

Then rebuild (python story_all.py) and republish the launcher and the role reports. BFSTORY_APP_LINKS points to
another file (tests)."""
import json
import os
from pathlib import Path

FILE = Path(__file__).resolve().parent / "app_links.json"
KEYS = ["launcher", "full", "ppm", "modeller", "pm", "resources", "pmo"]
# ctid = the BFusion tenant: a web link opens in a new tab, and without the tenant hint a guest account (Hassan's
# gmail) lands on its home tenant and is asked to sign in again (seen 2026-11-12).
TENANT = "7c42405b-10a1-45bf-925d-24ee2b295653"
BASE = "https://app.powerbi.com/groups/me/apps/{app}/reports/{report}/{page}?ctid=" + TENANT


def load():
    data = json.loads(Path(os.environ.get("BFSTORY_APP_LINKS", FILE)).read_text(encoding="utf-8"))
    return data.get("app_id", ""), data.get("reports", {})


def url(report, page_id):
    """App URL of one page of one report, or "" while its ids are not filled in."""
    app, reports = load()
    rid = reports.get(report, "")
    return BASE.format(app=app, report=rid, page=page_id) if app and rid else ""


def missing():
    app, reports = load()
    return ([] if app else ["app_id"]) + [k for k in KEYS if not reports.get(k)]
