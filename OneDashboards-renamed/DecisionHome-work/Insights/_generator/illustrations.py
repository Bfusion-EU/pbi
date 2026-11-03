"""Line-art illustrations for the chapter brief pages: one scene per chapter (the faint picture top-right) and one
spot drawing per page (the faint picture in the corner of each navigation tile).

They are drawn here as SVG and rendered once to transparent PNGs in assets/brief/ by `python illustrations.py`
(needs Microsoft Edge); the generator only copies the PNGs. White strokes at low opacity, baked into the PNG, so
the drawings sit behind the text on the navy pages instead of competing with it.

Run again after changing a drawing:  python illustrations.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "assets" / "brief"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

SCENE_W, SCENE_H = 760, 620
SPOT = 220
SCENE_OPACITY = 0.13
SPOT_OPACITY = 0.24


def _svg(w, h, view, body, opacity, width):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{view}" fill="none" '
            f'stroke="#FFFFFF" stroke-opacity="{opacity}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</svg>')


def _coins(x, y, n, rx=46, ry=14):
    out = []
    for k in range(n):
        cy = y - k * 13
        out.append(f'<path d="M{x - rx} {cy} v13 M{x + rx} {cy} v13"/><ellipse cx="{x}" cy="{cy}" rx="{rx}" ry="{ry}"/>')
    out.append(f'<path d="M{x - rx} {y + 13} A{rx} {ry} 0 0 0 {x + rx} {y + 13}"/>')
    return "".join(out)


def _person(x, y, s=1.0):
    return (f'<circle cx="{x}" cy="{y}" r="{26 * s}"/>'
            f'<path d="M{x - 48 * s} {y + 96 * s} C{x - 48 * s} {y + 40 * s} {x + 48 * s} {y + 40 * s} {x + 48 * s} {y + 96 * s}"/>')


# ---------------------------------------------------------------- chapter scenes (viewBox 0 0 640 520)
SCENES = {
    "exec": """
<path d="M120 330 A200 200 0 0 1 520 330"/><path d="M160 330 A160 160 0 0 1 480 330"/>
<path d="M320 330 L420 210"/><circle cx="320" cy="330" r="16"/>
<path d="M160 330 h-40 M520 330 h-40 M320 130 v40 M178 188 l28 28 M462 188 l-28 28"/>
<rect x="90" y="390" width="130" height="80" rx="14"/><rect x="255" y="390" width="130" height="80" rx="14"/>
<rect x="420" y="390" width="130" height="80" rx="14"/>
<path d="M110 450 l30 -24 l24 12 l38 -30 M275 440 h90 M275 418 h60 M440 452 l36 -36 l20 16 l34 -30"/>
<path d="M560 60 v150 M560 60 l60 22 l-60 22"/>""",
    "portfolio": """
<rect x="150" y="190" width="300" height="210" rx="22"/><path d="M250 190 v-40 a14 14 0 0 1 14 -14 h72 a14 14 0 0 1 14 14 v40"/>
<path d="M150 280 h300 M300 262 v36"/><rect x="284" y="262" width="32" height="36" rx="6"/>
<path d="M520 120 v250 M440 150 h160 M440 150 l-34 90 h68 z M600 150 l-34 90 h68 z M480 370 h80"/>
<rect x="40" y="90" width="150" height="100" rx="14"/><rect x="60" y="70" width="150" height="100" rx="14"/>
<path d="M80 100 h80 M80 124 h110 M80 148 h60"/>""",
    "finance": """
<g transform="translate(170 110) rotate(-6)"><rect width="250" height="300" rx="18"/>
<path d="M26 35 h120 M26 58 h180 M26 76 h150"/>
<rect x="36" y="200" width="28" height="60" rx="5"/><rect x="80" y="170" width="28" height="90" rx="5"/>
<rect x="124" y="140" width="28" height="120" rx="5"/><rect x="168" y="110" width="28" height="150" rx="5"/>
<path d="M30 190 L94 150 L140 124 L196 92" stroke-dasharray="2 14"/><circle cx="196" cy="92" r="9"/></g>
""" + _coins(470, 400, 6) + _coins(390, 430, 3, 40, 12) + """
<circle cx="150" cy="250" r="62"/><circle cx="150" cy="250" r="48"/>
<path d="M172 226 a30 30 0 1 0 0 48 M118 242 h44 M118 260 h40"/>
<circle cx="470" cy="210" r="44"/><path d="M501 241 l40 40"/>""",
    "resources": _person(200, 170, 1.1) + _person(330, 140, 1.25) + _person(460, 170, 1.1) + """
<rect x="120" y="340" width="400" height="150" rx="18"/><path d="M120 380 h400 M200 340 v-18 M440 340 v-18"/>
<path d="M170 420 h30 M240 420 h30 M310 420 h30 M380 420 h30 M450 420 h30 M170 455 h30 M240 455 h30 M310 455 h30"/>
<circle cx="395" cy="455" r="14"/>""",
    "schedule": """
<rect x="60" y="80" width="400" height="330" rx="18"/><path d="M60 130 h400 M160 80 v330 M260 80 v330 M360 80 v330"/>
<rect x="90" y="160" width="150" height="26" rx="13"/><rect x="190" y="215" width="170" height="26" rx="13"/>
<rect x="300" y="270" width="130" height="26" rx="13"/><rect x="140" y="325" width="110" height="26" rx="13"/>
<path d="M240 173 c30 0 30 55 -50 55 M360 228 c30 0 30 55 -60 55"/>
<path d="M410 355 l18 18 l-18 18 l-18 -18 z"/>
<circle cx="520" cy="360" r="90"/><circle cx="520" cy="360" r="74"/><path d="M520 310 v50 l36 24"/>""",
    "risk": """
<path d="M250 80 L380 130 V250 C380 340 320 400 250 430 C180 400 120 340 120 250 V130 Z"/>
<path d="M250 180 v110 M250 330 v4"/>
<path d="M480 170 L580 350 H380 Z"/><path d="M480 240 v50 M480 318 v3"/>
<circle cx="480" cy="440" r="40"/><circle cx="480" cy="440" r="70"/><path d="M480 440 L540 400"/>
<path d="M60 440 h120 M60 470 h80"/>""",
    "benefits": """
<path d="M80 430 h480 M80 430 V90"/>
<path d="M110 390 L210 330 L290 350 L380 250 L470 200 L540 120"/><path d="M540 120 h-44 M540 120 v44"/>
<circle cx="210" cy="330" r="10"/><circle cx="290" cy="350" r="10"/><circle cx="380" cy="250" r="10"/><circle cx="470" cy="200" r="10"/>
<path d="M150 150 h100 v40 a50 50 0 0 1 -100 0 z M150 165 h-22 a22 22 0 0 0 22 30 M250 165 h22 a22 22 0 0 1 -22 30
M200 240 v30 M170 290 h60 M180 270 h40"/>
<path d="M480 430 v-70 M480 380 c-30 -10 -40 -40 -36 -60 c24 6 36 30 36 60 M480 400 c24 -6 40 -28 38 -50 c-22 4 -36 24 -38 50"/>""",
    "governance": """
<rect x="130" y="90" width="260" height="350" rx="20"/><rect x="200" y="70" width="120" height="44" rx="12"/>
<path d="M170 170 l16 16 l30 -32 M240 172 h110 M170 240 l16 16 l30 -32 M240 242 h110 M170 310 l16 16 l30 -32 M240 312 h110
M176 380 h40 M240 382 h80"/>
<path d="M490 150 L580 186 V270 C580 330 540 370 490 390 C440 370 400 330 400 270 V186 Z"/>
<path d="M450 270 l28 28 l52 -58"/><circle cx="520" cy="440" r="36"/><path d="M546 466 l34 34"/>""",
}

# ---------------------------------------------------------------- spot drawings (viewBox 0 0 120 120)
SPOTS = {
    "gauge": '<path d="M20 80 A40 40 0 0 1 100 80"/><path d="M60 80 L84 54"/><circle cx="60" cy="80" r="6"/><path d="M28 96 h64"/>',
    "health": '<path d="M60 96 C20 70 16 46 30 34 C42 24 56 30 60 42 C64 30 78 24 90 34 C104 46 100 70 60 96 Z"/>'
              '<path d="M26 62 h18 l8 -14 l10 26 l8 -12 h24"/>',
    "roadmap": '<path d="M30 104 C40 70 80 70 70 46 C62 28 76 18 90 16"/><path d="M90 16 v-0"/>'
               '<path d="M86 16 v36 M86 16 l20 8 l-20 8"/><circle cx="30" cy="104" r="5"/>',
    "drift": '<circle cx="60" cy="62" r="38"/><path d="M60 38 v24 l18 12"/><path d="M18 40 a46 46 0 0 1 22 -24 M14 30 l4 12 l12 -4"/>',
    "grid": '<rect x="18" y="24" width="84" height="72" rx="8"/><path d="M18 48 h84 M18 72 h84 M46 24 v72 M74 24 v72"/>',
    "briefcase": '<rect x="18" y="40" width="84" height="58" rx="8"/><path d="M44 40 v-10 a6 6 0 0 1 6 -6 h20 a6 6 0 0 1 6 6 v10 M18 64 h84"/>',
    "funnel": '<path d="M16 24 h88 l-34 40 v30 l-20 10 v-40 z"/><path d="M30 40 h60"/>',
    "scales": '<path d="M60 18 v80 M28 30 h64 M28 30 l-16 38 h32 z M92 30 l-16 38 h32 z M40 98 h40"/>',
    "lock": '<rect x="28" y="54" width="64" height="48" rx="8"/><path d="M40 54 v-14 a20 20 0 0 1 40 0 v14 M60 72 v12"/>',
    "euro": '<circle cx="60" cy="60" r="40"/><path d="M76 42 a22 22 0 1 0 0 36 M38 54 h32 M38 68 h28"/>',
    "drivers": '<path d="M24 98 v-22 M44 98 v-38 M64 98 v-54"/><circle cx="76" cy="48" r="22"/><path d="M92 64 l18 18"/>',
    "landing": '<circle cx="54" cy="66" r="36"/><circle cx="54" cy="66" r="22"/><circle cx="54" cy="66" r="7"/>'
               '<path d="M56 64 L102 18 M102 18 h-16 M102 18 v16"/>',
    "people": '<circle cx="42" cy="44" r="14"/><path d="M14 98 c0 -30 56 -30 56 0"/><circle cx="82" cy="40" r="12"/>'
              '<path d="M70 66 c22 -10 42 4 42 30"/>',
    "fte": '<circle cx="48" cy="42" r="16"/><path d="M16 100 c0 -34 64 -34 64 0"/><path d="M92 30 v28 M78 44 h28 M80 80 h24"/>',
    "org": '<rect x="44" y="14" width="32" height="24" rx="5"/><rect x="12" y="78" width="32" height="24" rx="5"/>'
           '<rect x="76" y="78" width="32" height="24" rx="5"/><path d="M60 38 v20 M28 78 v-20 h64 v20"/>',
    "timesheet": '<rect x="18" y="16" width="62" height="84" rx="8"/><path d="M32 38 h34 M32 54 h34 M32 70 h20"/>'
                 '<circle cx="84" cy="82" r="22"/><path d="M84 70 v12 l9 6"/>',
    "checklist": '<rect x="24" y="16" width="72" height="90" rx="8"/><path d="M36 40 l6 6 l12 -12 M62 42 h24 M36 66 l6 6 l12 -12 M62 68 h24 M36 92 h16 M62 92 h24"/>',
    "calendar": '<rect x="16" y="26" width="88" height="76" rx="8"/><path d="M16 46 h88 M38 18 v16 M82 18 v16 M32 64 h12 M54 64 h12 M76 64 h12 M32 84 h12 M54 84 h12"/>',
    "critical": '<circle cx="22" cy="86" r="10"/><circle cx="60" cy="40" r="10"/><circle cx="98" cy="78" r="10"/>'
                '<path d="M30 78 L52 48 M68 46 L90 70"/><path d="M14 30 h28 M78 16 h28"/>',
    "status": '<rect x="22" y="14" width="76" height="92" rx="8"/><circle cx="42" cy="40" r="7"/><circle cx="42" cy="62" r="7"/>'
              '<circle cx="42" cy="84" r="7"/><path d="M58 40 h26 M58 62 h26 M58 84 h18"/>',
    "shield": '<path d="M60 12 L98 26 V58 C98 84 80 100 60 108 C40 100 22 84 22 58 V26 Z"/><path d="M60 40 v30 M60 84 v2"/>',
    "trophy": '<path d="M36 20 h48 v20 a24 24 0 0 1 -48 0 z M36 28 h-14 a14 14 0 0 0 16 22 M84 28 h14 a14 14 0 0 1 -16 22 M60 64 v18 M42 100 h36 M48 88 h24"/>',
    "clipboard": '<rect x="24" y="22" width="72" height="86" rx="8"/><rect x="42" y="14" width="36" height="16" rx="5"/>'
                 '<path d="M38 56 l8 8 l16 -18 M38 86 l8 8 l16 -18 M70 58 h14 M70 88 h14"/>',
}
PAGE_SPOT = {"exec": "gauge", "health": "health", "roadmap": "roadmap", "drift": "drift", "kpigrid": "grid",
             "portfolio": "briefcase", "selection": "funnel", "scenarios": "scales", "constraints": "lock",
             "finance": "euro", "fintree": "drivers", "budgetrisk": "landing",
             "resources": "people", "fte": "fte", "org": "org", "timesheets": "timesheet", "mywork": "checklist",
             "schedule": "calendar", "critical": "critical", "psr": "status",
             "risk": "shield", "benefits": "trophy", "governance": "clipboard",
             # Insights pack deep dives
             "lifecycle": "funnel", "onepager": "status", "finance2": "drivers", "tsstatus": "checklist",
             "resource": "fte", "gantt": "roadmap", "status": "drift", "baseline": "critical"}


HOME_FILE = "brief-home.png"   # white house on the orange home button, full strength
HOME = '<path d="M14 54 L60 16 L106 54 M26 44 V104 H50 V74 H70 V104 H94 V44"/>'


def scene_file(chapter):
    return f"brief-scene-{chapter}.png"


def spot_file(page):
    return f"brief-spot-{PAGE_SPOT[page]}.png"


def files():
    return sorted({scene_file(c) for c in SCENES} | {f"brief-spot-{k}.png" for k in SPOTS} | {HOME_FILE})


def _render(svg, w, h, png):
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "x.html"
        page.write_text(f'<html><body style="margin:0;background:transparent">{svg}</body></html>', encoding="utf-8")
        subprocess.run([str(EDGE), "--headless", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                        f"--window-size={w},{h}", f"--screenshot={png}", page.as_uri()],
                       check=True, capture_output=True, timeout=60)


def render():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for c, body in SCENES.items():
        _render(_svg(SCENE_W, SCENE_H, "0 0 640 520", body, SCENE_OPACITY, 3), SCENE_W, SCENE_H, OUT / scene_file(c))
    for k, body in SPOTS.items():
        _render(_svg(SPOT, SPOT, "0 0 120 120", body, SPOT_OPACITY, 3.5), SPOT, SPOT, OUT / f"brief-spot-{k}.png")
    _render(_svg(64, 64, "0 0 120 120", HOME, 1, 9), 64, 64, OUT / HOME_FILE)
    print(f"rendered {len(SCENES)} scenes and {len(SPOTS)} spots -> {OUT}")


if __name__ == "__main__":
    render()
    sys.exit(0)
