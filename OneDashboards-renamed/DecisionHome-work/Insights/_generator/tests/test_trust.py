import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401
from story_measures import MEASURES  # noqa: E402

NAMES = {m["name"]: m for m in MEASURES}
WRAPPED = {"Story | Finance Headline": "Finance", "Story | Pareto PnL Headline": "Finance",
           "Story | Resource Headline": "Resources", "Story | Schedule Headline": "Schedule",
           "Story | Benefits Headline": "Benefits"}


def test_headlines_wrapped_with_their_note():
    for name, area in WRAPPED.items():
        expr = NAMES[name]["expression"]
        assert f"[{name} · Core]" in expr and f"[Story | Trust · Note {area}]" in expr, name
        assert f"{name} · Core" in NAMES, name


def test_notes_only_below_threshold():
    import trust
    for area in ("Finance", "Resources", "Schedule", "Benefits"):
        expr = NAMES[f"Story | Trust · Note {area}"]["expression"]
        assert f"< {trust.TRUST_MIN}" in expr and "_m > 0" in expr, area


def test_exec_ends_with_trust_score():
    expr = NAMES["Story | Exec Headline"]["expression"]
    assert "[Story | Exec Headline · Core]" in expr and "[Story | Trust · Exec Score]" in expr
    assert "[PMO | Governance Score]" in NAMES["Story | Trust · Exec Score"]["expression"]


def test_each_measure_registered_once():
    names = [m["name"] for m in MEASURES]
    assert len(names) == len(set(names))
