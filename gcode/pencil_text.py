#!/usr/bin/env python3
"""Write pencil_text.gcode: write a line of text in cursive with a pencil (constant height, no brush lift).

Usage:   python3 pencil_text.py ["Gemmie is a puffin"]      then   python3 octo.py send pencil_text.gcode
Needs:   pip install Hershey-Fonts      (single-line 'script' font, made for plotters)
"""
import json
import math
import os
import sys

from HersheyFonts import HersheyFonts

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OFF = CAL.get("pencil_offset") or CAL["offset"]          # pencil's own offset once measured
OX, OY, OZ = OFF["x"], OFF["y"], OFF["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]

# ---------------- SETTINGS (fixture mm) ----------------
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
NO_HOME = "--no-home" in sys.argv   # printer already homed and pencil attached: skip homing and the pause
TEXT = ARGS[0] if ARGS else "Gemmie is a puffin"
FONT = "scripts"     # Hershey single-stroke cursive ("scriptc" = complex, double-line)
WIDTH = 176.0        # text width; the height follows from the font
SHIFT = (0.0, 0.0)   # move the text (+X right, +Y towards the back)
PENCIL_DOWN = 1.0    # tip commanded this far below the paper (the plunger floats: constant light pressure)
PEN_UP = 3.0         # lift between letters / strokes
APPROACH = 20.0      # height for the first move after homing
PENCIL_DZ = 0.0      # extra Z correction if the pencil tip sits higher (+) / lower (-) than the brush did
DRAW_F = 1500
TRAVEL_F = 4000
# --------------------------------------------------------
BED = (220.0, 220.0)

f = HersheyFonts()
f.load_default_font(FONT)
f.normalize_rendering(100)
def custom_G(x0, y0, x1, y1):
    """A clear cursive capital G inside the box (y1 = top): open C-shape, inward bar, one stroke."""
    w, h = x1 - x0, y1 - y0
    pts = []
    for i in range(41):                          # C from upper right, over the top, round to lower right
        a = math.radians(40 + 290 * i / 40)
        pts.append((x0 + w * (0.52 + 0.46 * math.cos(a)), y0 + h * (0.5 + 0.48 * math.sin(a))))
    ex, ey = pts[-1]
    pts += [(ex + w * 0.04, ey + h * 0.18), (x0 + w * 0.97, y0 + h * 0.42),   # up the right side
            (x0 + w * 0.60, y0 + h * 0.42)]                                     # bar inwards
    slant = 0.25                                 # lean like the rest of the script
    return [(x + (y - y0) * slant, y) for x, y in pts]


def glyph_strokes(text):
    """Strokes for the text, with any capital G replaced by custom_G at the same size and place."""
    out = []
    for i, ch in enumerate(text):
        before = len(list(f.strokes_for_text(text[:i])))
        cur = [list(st) for st in f.strokes_for_text(text[:i + 1])]
        new = cur[before:]
        if ch == "G" and new:
            gx = [p[0] for st in new for p in st]
            gy = [p[1] for st in new for p in st]
            new = [custom_G(min(gx) + (max(gx) - min(gx)) * 0.1, min(gy), max(gx), max(gy))]
        out += new
    return out


raw = glyph_strokes(TEXT)
xs = [p[0] for s in raw for p in s]
ys = [p[1] for s in raw for p in s]
scale = WIDTH / (max(xs) - min(xs))
cx = (PW["x0"] + PW["x1"]) / 2 + SHIFT[0]
cy = (PW["y0"] + PW["y1"]) / 2 + SHIFT[1]
mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
strokes = [[(cx + (x - mx) * scale, cy + (y - my) * scale) for x, y in s] for s in raw]

# join strokes that continue exactly where the last one ended (no pencil lift needed)
joined = []
for s in strokes:
    if joined and math.dist(joined[-1][-1], s[0]) < 0.05:
        joined[-1] += s[1:]
    else:
        joined.append(list(s))
strokes = joined

for s in strokes:
    for x, y in s:
        if not (PW["x0"] + 2 <= x <= PW["x1"] - 2 and PW["y0"] + 2 <= y <= PW["y1"] - 2):
            sys.exit(f"text leaves the paint window at X{x:.1f} Y{y:.1f}: lower WIDTH")


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


z_down = CARD_Z - PENCIL_DOWN + OZ + PENCIL_DZ
z_up = CARD_Z + PEN_UP + OZ + PENCIL_DZ
h = (max(y for s in strokes for _, y in s) - min(y for s in strokes for _, y in s))
g = [
    f'; PENCIL TEXT: "{TEXT}" in {FONT}, {WIDTH:.0f} x {h:.0f} mm, {len(strokes)} pencil strokes',
    "; constant height while writing (no brush pressure changes)",
    f"; offsets from data/calibration.json: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}  (+ PENCIL_DZ {PENCIL_DZ:+.1f})",
]
if NO_HOME:
    g += ["; NO HOMING: only for a printer that is already homed with the pencil attached",
          "; (e.g. straight after pencil_calibrate.gcode). Do not use after a power cycle.",
          "M104 S0", "M140 S0", "M107", "G21", "G90",
          f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; lift off the paper first, before any sideways move"]
else:
    g += ["; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.",
          "M104 S0", "M140 S0", "M107", "G21", "G90",
          "G28 ; home with the cartridge off",
          f"G1 Z{CARD_Z + 45 + OZ:.2f} F600 ; bed down for attaching the pencil",
          "M400",
          "M117 Attach pencil, then Resume",
          "@pause ; snap the pencil cartridge on, then press Resume",
          f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; stay well clear of the paper and frame"]
for k, s in enumerate(strokes):
    x0, y0 = m(*s[0])
    g += [f"; stroke {k + 1}", f"G0 X{x0:.2f} Y{y0:.2f} F{TRAVEL_F}"]
    if k == 0:
        g.append(f"G1 Z{z_up:.2f} F600")
    g.append(f"G1 Z{z_down:.2f} F600")
    for x, y in s[1:]:
        px, py = m(x, y)
        g.append(f"G1 X{px:.2f} Y{py:.2f} F{DRAW_F}")
    g.append(f"G1 Z{z_up:.2f} F600")
g += [f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; lift clear of the paper",
      f"G0 X{BED[0]:.2f} Y{BED[1]:.2f} F{TRAVEL_F} ; park top-right",
      "M400", "M84 X Y ; X/Y motors off (Z stays on)", "M117 Text done"]
OUT = "pencil_text_nohome.gcode" if NO_HOME else "pencil_text.gcode"
open(os.path.join(HERE, OUT), "w").write("\n".join(g) + "\n")
print(f"wrote {OUT}: {len(strokes)} strokes, {WIDTH:.0f} x {h:.0f} mm")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 6.3))
    ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                               fill=False, ec="#aaa", ls="--"))
    for s in strokes:
        a, b = zip(*s)
        ax.plot(a, b, color="#444", lw=1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.savefig(os.path.join(HERE, "pencil_text_preview.png"), dpi=150, bbox_inches="tight")
    print("wrote pencil_text_preview.png")
except ImportError:
    pass
