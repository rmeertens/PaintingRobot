#!/usr/bin/env python3
"""Place one or more traced drawings (art/*_paths.json, made by svg2plot.py) on the card and write
pencil G-code for them, plus a preview that also shows the text already on the card.

Each --place is  FILE:X:Y:HEIGHT[:flip]   (fixture mm; X = centre of the drawing, Y = its bottom)
Example (puffin A above the text on the left, puffin C below it on the right, facing left):
  python3 draw_art.py --place ../art/puffin_A_paths.json:55:150:44 \\
                      --place ../art/puffin_C_paths.json:175:66:44:flip   [--no-home]
Writes draw_art.gcode (or draw_art_nohome.gcode with --no-home) and draw_art_preview.png.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OFF = CAL.get("pencil_offset") or CAL["offset"]
OX, OY, OZ = OFF["x"], OFF["y"], OFF["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]
PENCIL_DOWN, PEN_UP, APPROACH = 1.0, 3.0, 20.0      # same as pencil_text.py
DRAW_F, TRAVEL_F = 1200, 4000
BED = (220.0, 220.0)

ap = argparse.ArgumentParser()
ap.add_argument("--place", action="append", required=True)
ap.add_argument("--no-home", action="store_true")
args = ap.parse_args()

S = []
for spec in args.place:
    parts = spec.split(":")
    f, x, y, h = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
    flip = len(parts) > 4 and parts[4] == "flip"
    d = json.load(open(f if os.path.isabs(f) else os.path.join(os.getcwd(), f)))
    s = h / d["height_mm"]
    xs = [p[0] for pl in d["lines"] for p in pl]
    cx0 = (min(xs) + max(xs)) / 2
    for pl in d["lines"]:
        S.append([(x + ((cx0 - px) if flip else (px - cx0)) * s, y + py * s) for px, py in pl])

# shortest-ish drawing order: always go to the nearest unfinished line next (either end)
order, cur, todo = [], (PW["x0"], PW["y1"]), list(S)
while todo:
    best = min(range(len(todo)), key=lambda i: min(abs(todo[i][0][0] - cur[0]) + abs(todo[i][0][1] - cur[1]),
                                                   abs(todo[i][-1][0] - cur[0]) + abs(todo[i][-1][1] - cur[1])))
    pl = todo.pop(best)
    if abs(pl[-1][0] - cur[0]) + abs(pl[-1][1] - cur[1]) < abs(pl[0][0] - cur[0]) + abs(pl[0][1] - cur[1]):
        pl = pl[::-1]
    order.append(pl)
    cur = pl[-1]
S = order

for pl in S:
    for x, y in pl:
        if not (PW["x0"] + 2 <= x <= PW["x1"] - 2 and PW["y0"] + 2 <= y <= PW["y1"] - 2):
            sys.exit(f"drawing leaves the paint window at X{x:.1f} Y{y:.1f}: move it or make it smaller")


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


z_down, z_up = CARD_Z - PENCIL_DOWN + OZ, CARD_Z + PEN_UP + OZ
g = [f"; DRAW ART: {', '.join(args.place)}  ({len(S)} pencil lines)",
     f"; offsets: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}"]
if args.no_home:
    g += ["; NO HOMING: only for a printer that is already homed with the pencil attached",
          "M104 S0", "M140 S0", "M107", "G21", "G90", f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; lift off the paper first",
          "G28 X Y ; re-home X/Y only (safe with the pencil on: Z is not touched), in case the X/Y motors were off"]
else:
    g += ["; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.",
          "M104 S0", "M140 S0", "M107", "G21", "G90", "G28 ; home with the cartridge off",
          f"G1 Z{CARD_Z + 45 + OZ:.2f} F600", "M400", "M117 Attach pencil, then Resume",
          "@pause ; snap the pencil cartridge on, then press Resume", f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600"]
for k, pl in enumerate(S):
    x0, y0 = m(*pl[0])
    g += [f"; line {k + 1}", f"G0 X{x0:.2f} Y{y0:.2f} F{TRAVEL_F}"]
    if k == 0:
        g.append(f"G1 Z{z_up:.2f} F600")
    g.append(f"G1 Z{z_down:.2f} F600")
    g += [f"G1 X{m(x, y)[0]:.2f} Y{m(x, y)[1]:.2f} F{DRAW_F}" for x, y in pl[1:]]
    g.append(f"G1 Z{z_up:.2f} F600")
g += [f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600", f"G0 X{BED[0]:.2f} Y{BED[1]:.2f} F{TRAVEL_F} ; park top-right",
      "M400", "M84 X Y ; X/Y motors off (Z stays on)", "M117 Drawing done"]
out = "draw_art_nohome.gcode" if args.no_home else "draw_art.gcode"
open(os.path.join(HERE, out), "w").write("\n".join(g) + "\n")
print(f"wrote {out}: {len(S)} lines")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                               fill=False, ec="#bbb", ls="--"))
    try:
        src = open(os.path.join(HERE, "pencil_text.py")).read().split("def m(x, y):")[0]
        ns = {"__name__": "preview", "__file__": os.path.join(HERE, "pencil_text.py")}
        saved = sys.argv
        sys.argv = ["pencil_text.py"]
        exec(compile(src, "pencil_text.py", "exec"), ns)
        sys.argv = saved
        for st in ns["strokes"]:
            a, b = zip(*st)
            ax.plot(a, b, color="#aaa", lw=0.9)
    except Exception as e:
        print("(preview without the text:", e, ")")
    for pl in S:
        a, b = zip(*pl)
        ax.plot(a, b, color="#333", lw=0.8)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.savefig(os.path.join(HERE, "draw_art_preview.png"), dpi=160, bbox_inches="tight")
    print("wrote draw_art_preview.png")
except ImportError:
    pass
