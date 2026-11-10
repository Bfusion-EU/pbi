"""The five role reports of the Story pack: which chapters and deep dives each role gets, renumbered per role.

A page keeps its key and its page id in every report; only its display name changes ("2c · Scenarios" in the full
pack is "2 · Scenarios & Trade-offs" for the Modeller), so the code-based chapter logic of bfstory / entry / chrome
works on a role report unchanged.
"""
from dataclasses import dataclass

import layout
from pbir import uid

MAP_PAGE_ID = uid("bfstory-page", "map")          # every Story report opens on its Map (the Launcher links here)
LAUNCHER_PAGE_ID = uid("bfstory-launcher", "launcher")

@dataclass
class Role:
    key: str                  # ppm | modeller | pm | resources | pmo (also the app_links.json key)
    report: str               # file name, <= 15 characters (path limit)
    title: str                # launcher tile title and Questions page title
    purpose: str              # one line on the launcher tile
    headline: str             # live headline measure on the launcher tile
    chapters: list            # [(chapter key, [deep-dive keys])]
    home: bool = False        # True: the report also has the Decision center (KPI ticker + PMO command center)


ROLES = {r.key: r for r in [
    Role("ppm", "Story PPM", "Portfolio & Program", "Health, money, value and risk across the portfolio",
         "Story | Exec Headline",
         [("exec", ["health", "roadmap", "drift", "trend"]), ("portfolio", ["selection", "benefits", "realised", "strategy"]),
          ("finance", ["fintree", "budgetrisk", "projfin"]), ("schedule", ["critical", "timeline"]), ("risk", ["riskmap"])]),
    Role("modeller", "Story Modeller", "Modeller", "Compare scenarios and funding choices before you decide",
         "Story | Scenario · Headline",
         [("portfolio", ["strategy"]), ("selection", []), ("scenarios", []), ("constraints", []), ("resources", ["capacity"])]),
    Role("pm", "Story PM", "Project Manager", "Schedule, status, money, tasks and risks of your projects",
         "Story | Schedule Headline",
         [("schedule", ["critical", "psr", "roadmap", "timeline"]), ("finance", ["projfin"]), ("mywork", []),
          ("risk", ["riskmap"]), ("kpigrid", [])]),
    Role("resources", "Story Resources", "Resource Manager", "Capacity, demand, people and timesheets",
         "Story | Resource Headline",
         [("resources", ["fte", "org", "timesheets", "mywork", "capacity"]), ("selection", []), ("constraints", [])]),
    Role("pmo", "Story PMO", "PMO", "Data quality, compliance and what needs a decision now",
         "PMO | Governance Headline",
         [("exec", ["roadmap", "trend"]), ("schedule", ["psr", "timeline"]), ("risk", ["riskmap"]),
          ("governance", ["recon", "hygiene"]), ("timesheets", [])], home=True),
]}

# A page promoted to a chapter has its own rail / Questions icon (rail-<key>-white|grey.png, one icon per meaning in
# every pack) but borrows the brief scene illustration and the data-confidence strip of the chapter it belongs to in
# the full pack: there is no scene or confidence check of its own.
SCENE_OF = {"selection": "portfolio", "scenarios": "portfolio", "constraints": "schedule", "kpigrid": "exec",
       "mywork": "schedule", "psr": "schedule", "timesheets": "resources"}

RAIL_LABEL = {"exec": "Executive", "portfolio": "Portfolio", "finance": "Financials", "resources": "Resources",
              "schedule": "Schedule", "risk": "Risk", "benefits": "Benefits", "governance": "Governance",
              "selection": "Selection", "scenarios": "Scenarios", "constraints": "Limits", "mywork": "My work",
              "kpigrid": "KPI grid", "psr": "Status", "timesheets": "Hours"}


def role_pages(role, full_names):
    """[(key, display)] in story order: Map, (Home), then per chapter the chapter and its deep dives."""
    out = [("map", full_names["map"])]
    if role.home:
        out.append(("home", full_names["home"]))
    for n, (ch, deep) in enumerate(role.chapters, 1):
        label = layout._code(full_names[ch])[2]
        out += [(ch, f"{n} · {label}")]
        out += [(k, f"{n}{letter} · {layout._code(full_names[k])[2]}") for letter, k in zip("bcdefg"[:len(deep)], deep, strict=True)]
    return out


def rail(role):
    """Chapter rail of a role report: the Map first, the Decision center where the role has it, then its chapters."""
    first = [("questions", "map", "Map")] + ([("cc", "home", "Decision")] if role.home else [])
    return first + [(ch, ch, RAIL_LABEL[ch]) for ch, _ in role.chapters]
