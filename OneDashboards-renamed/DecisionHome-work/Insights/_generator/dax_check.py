"""Evaluate every report-level story measure against a local copy of the model.

Open SemanticModel/OneModel360Star.pbix in Power BI Desktop first, then:

    python dax_check.py              # finds the local port itself
    python dax_check.py --port 65523 --show Headline

Each measure runs as a grand total and grouped by project, resource and month, with all
report measures defined in the query, so it catches errors that only show inside visuals.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from story_measures import MEASURES  # noqa: E402
import pages  # noqa: E402,F401
import extensions  # noqa: E402,F401  (registers extension measures)

GROUPINGS = {
    "total": None,
    "project": "DimProject[Name]",
    "resource": "DimResource[Name]",
    "month": "DimDate[MonthStart]",
}


def find_port():
    root = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Power BI Desktop" / "AnalysisServicesWorkspaces"
    ports = sorted(root.rglob("msmdsrv.port.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not ports:
        sys.exit("No local model found: open OneModel360Star.pbix in Power BI Desktop first.")
    return int(ports[0].read_text(encoding="utf-16-le").strip())


BY_NAME = {m["name"]: m for m in MEASURES}


def deps(name, seen=None):
    """The measure plus every report measure it references, dependencies first."""
    seen = seen if seen is not None else []
    expr = re.sub(r'"[^"]*"', '""', BY_NAME[name]["expression"])
    for ref in re.findall(r"(?<![\w\]'])\[([^\]@][^\]]*)\]", expr):
        if ref in BY_NAME and ref not in seen and ref != name:
            deps(ref, seen)
    if name not in seen:
        seen.append(name)
    return seen


def define_block(name):
    lines = ["DEFINE"]
    for d in deps(name):
        lines.append(f"    MEASURE '_Measures'[{d.replace(']', ']]')}] = {BY_NAME[d]['expression']}")
    return "\n".join(lines)


def run(queries, port):
    with tempfile.TemporaryDirectory() as tmp:
        qin, qout = Path(tmp) / "q.json", Path(tmp) / "r.json"
        qin.write_text(json.dumps(queries), encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "run_dax.ps1"),
                        "-Port", str(port), "-In", str(qin), "-Out", str(qout)], check=True)
        res = json.loads(qout.read_text(encoding="utf-8-sig"))
    return res if isinstance(res, list) else [res]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int)
    ap.add_argument("--show", help="print values of measures whose name contains this text")
    ap.add_argument("--only", help="only check measures whose name contains this text")
    a = ap.parse_args()
    port = a.port or find_port()
    todo = [m for m in MEASURES if not a.only or a.only in m["name"]]
    queries = []
    for m in todo:
        ref = "[" + m["name"].replace("]", "]]") + "]"
        for g, col in GROUPINGS.items():
            body = (f'EVALUATE ROW ( "v", {ref} )' if col is None
                    else f'EVALUATE TOPN ( 5, SUMMARIZECOLUMNS ( {col}, "v", {ref} ) )')
            queries.append({"id": f"{m['name']}||{g}", "dax": define_block(m["name"]) + "\n" + body})
    res = run(queries, port)
    errors = {}
    for r in res:
        name, g = r["id"].split("||")
        if not r["ok"]:
            errors.setdefault(name, []).append((g, r["error"].splitlines()[0][:400]))
        elif a.show and a.show in name and g == "total":
            print(f"VALUE {name}: {r['rows'][0]['[v]'] if r['rows'] else None}")
    for name, errs in errors.items():
        print(f"ERROR {name}")
        for g, e in errs:
            print(f"    [{g}] {e}")
    print(f"checked {len(todo)} measures x {len(GROUPINGS)} contexts on localhost:{port}: "
          f"{len(errors)} measure(s) with errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
