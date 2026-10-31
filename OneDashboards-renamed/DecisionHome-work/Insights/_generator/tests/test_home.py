import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
from story_measures import MEASURES  # noqa: E402

NAMES = {m["name"] for m in MEASURES}
HOME = ["Greeting", "Briefing", "Act Score", "Act Reason", "Act Colour", "Act Count", "EAC Var % (reports)",
        "On Track % (reports)", "EAC Change", "On Track Change", "Util Remainder", "Trust Remainder",
        "Line Portfolio", "Line Financials", "Line Resources", "Line Schedule", "Line Risk", "Line Benefits",
        "Line Timesheets", "Line Governance", "Colour Portfolio", "Colour Schedule", "Colour Risk",
        "Colour Benefits", "Colour Timesheets", "Answer Finance", "Answer Schedule", "Answer Resources",
        "Answer Benefits", "Due In 30d"]


def test_home_measures_registered():
    missing = [n for n in HOME if f"Story | Home · {n}" not in NAMES]
    assert missing == []
