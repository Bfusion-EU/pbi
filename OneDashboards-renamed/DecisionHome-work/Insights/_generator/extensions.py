"""Extension pages. Each ext_*.py module registers its story measures at import
(story_measures.add) and exposes build() -> list[pbir.Page]."""
import importlib
from pathlib import Path

MODULES = ["ext_project", "ext_lifecycle", "ext_scenarios", "ext_timesheets", "ext_status",
           "ext_tsstatus", "ext_resource", "ext_gantt", "ext_baseline"]
BUILDERS = []
for _name in MODULES:
    if (Path(__file__).parent / f"{_name}.py").exists():
        BUILDERS.append(importlib.import_module(_name).build)
