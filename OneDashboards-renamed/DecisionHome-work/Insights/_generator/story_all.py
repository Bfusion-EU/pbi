"""Build every Story report, each in its own process (the generator keeps module-level state per report):

    python story_all.py            # full pack, the five role reports, the launcher
    python story_all.py --check    # same, with each report's checks; exit 1 if any report fails
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import roles  # noqa: E402

STEPS = ([("Bfusion Story", ["bfstory.py"])] + [(r.report, ["bfstory.py", "--role", r.key]) for r in roles.ROLES.values()]
         + [("Story Launcher", ["launcher.py"])])

if __name__ == "__main__":
    extra = sys.argv[1:]
    failed = []
    for name, cmd in STEPS:
        print(f"===== {name}", flush=True)
        if subprocess.run([sys.executable, *cmd, *extra], cwd=HERE).returncode:
            failed.append(name)
    print("ALL OK" if not failed else f"FAILED: {', '.join(failed)}")
    sys.exit(1 if failed else 0)
