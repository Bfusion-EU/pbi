import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build  # noqa: E402
import pages  # noqa: E402


def test_write_report_makes_a_standalone_pack(tmp_path):
    built = pages.build_all()[:2]
    rep = build.write_report("Test Pack", built, [], tmp_path)
    assert rep == tmp_path / "Test Pack.Report"
    assert (tmp_path / "Test Pack.pbip").exists()
    assert (rep / "definition" / "report.json").exists()
    assert (rep / "definition" / "reportExtensions.json").exists()
    assert len(list(rep.glob("definition/pages/*/page.json"))) == 2
    plat = json.loads((rep / ".platform").read_text(encoding="utf-8"))
    assert plat["metadata"]["displayName"] == "Test Pack"
    assert not (rep / "definition" / "bookmarks").exists()
