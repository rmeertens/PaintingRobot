#!/usr/bin/env python3
"""Write garland.gcode: the spiral-garland Christmas tree (no stump), drawn dry - no paint pick-up.

One continuous line coils up a cone, then a star of three nested outlines on top.
Uses the measured offsets in ../data/calibration.json.
Run:   python3 garland.py      then   python3 octo.py send garland.gcode
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OX, OY, OZ = CAL["offset"]["x"], CAL["offset"]["y"], CAL["offset"]["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]

# ---------------- SETTINGS (fixture mm) ----------------
TIP = "right"        # which way the top of the tree points on the landscape card: "right" or "left"
HEIGHT = 158.0       # coil length from bottom loop to top (along the card's long side)
WIDTH = 124.0        # widest loop (across the card's short side)
FLAT = 0.2           # loop depth as a fraction of its width (the 3D look)
OVERLAP = 1.6        # turn spacing / loop depth: lower = loops overlap more
MIN_PITCH = 8.0      # smallest gap between turns near the tip
STAR_R = 9.0
PRESS = 0.5          # command the tip this far below the paper (the plunger floats)
HOVER = 10.0         # lift above the paper between the two strokes
DRAW_F = 1500        # mm/min while drawing
TRAVEL_F = 4000
# --------------------------------------------------------
CX = (PW["x0"] + PW["x1"]) / 2
CY = (PW["y0"] + PW["y1"]) / 2
BED = (220.0, 220.0)
# tree coordinates: u = up the tree (0 = bottom loop), v = across it (0 = centre line)
U0 = -(HEIGHT + 2 * STAR_R + 1) / 2 + WIDTH / 2 * FLAT / 2    # centre the whole tree + star on the card


def place(u, v):
    """Tree coordinates -> fixture X/Y, with the tree lying along the card's long side."""
    if TIP == "right":
        return CX + U0 + u, CY + v
    return CX - U0 - u, CY - v


def coil():
    """Cone coil: loop radius shrinks evenly towards the tip, and each turn advances by an amount
    proportional to the loop's depth (never less than MIN_PITCH), so the rings overlap evenly."""
    pts, u, th = [], 0.0, 0.0
    while u <= HEIGHT:
        r = WIDTH / 2 * (1 - u / HEIGHT) + 1
        pts.append(place(u + r * FLAT * math.sin(th), r * math.cos(th)))
        pitch = max(r * FLAT * OVERLAP, MIN_PITCH)          # advance per full turn here
        dth = 0.6 / max(r, 1)                                # ~0.6 mm per step along the line
        th += dth
        u += pitch * dth / (2 * math.pi)
    return pts


def star(r_out, rings=3, step=1.8):
    """Nested star outlines from the inside out, joined into one line, one point towards the tip."""
    c = (HEIGHT + r_out + 1, 0.0)
    out = []
    for k in range(rings - 1, -1, -1):
        r = r_out - k * step
        for i in range(11):
            a = i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            out.append(place(c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    return out


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


strokes = [("garland", coil()), ("star", star(STAR_R))]
for name, pts in strokes:
    for x, y in pts:
        if not (PW["x0"] + 2 <= x <= PW["x1"] - 2 and PW["y0"] + 2 <= y <= PW["y1"] - 2):
            sys.exit(f"{name} leaves the paint window at X{x:.1f} Y{y:.1f}")

down = CARD_Z - PRESS + OZ
hover = CARD_Z + HOVER + OZ
g = [
    f"; SPIRAL GARLAND (no stump), lying along the card, tip to the {TIP} - drawn dry, no paint pick-up",
    f"; offsets from data/calibration.json: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}",
    "; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.",
    "M104 S0", "M140 S0", "M107", "G21", "G90",
    "G28 ; home with the cartridge off",
    f"G1 Z{hover + 40:.2f} F600 ; bed down for attaching the brush",
    "M400",
    "M117 Attach brush, then Resume",
    "@pause ; snap the cartridge on, then press Resume",
]
for name, pts in strokes:
    x0, y0 = m(*pts[0])
    g += [f"; --- {name}", f"G0 Z{hover:.2f} F900", f"G0 X{x0:.2f} Y{y0:.2f} F{TRAVEL_F}",
          f"M117 Drawing {name}", f"G1 Z{down:.2f} F300"]
    for x, y in pts[1:]:
        px, py = m(x, y)
        g.append(f"G1 X{px:.2f} Y{py:.2f} F{DRAW_F}")
    g.append(f"G1 Z{hover:.2f} F600")
g += [f"G1 Z{hover + 30:.2f} F600 ; lift clear of the paper",
      f"G0 X{BED[0]:.2f} Y{BED[1]:.2f} F{TRAVEL_F} ; park top-right (back-right corner of travel)",
      "M400 ; wait until it has arrived",
      "M84 X Y ; X/Y motors off (Z stays on so the bed holds its height)",
      "M117 Garland done"]
open(os.path.join(HERE, "garland.gcode"), "w").write("\n".join(g) + "\n")
print(f"wrote garland.gcode ({len(g)} lines)")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                               fill=False, ec="#999", ls="--"))
    for name, pts in strokes:
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color="#1d6b3c" if name == "garland" else "#e0a020", lw=1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.savefig(os.path.join(HERE, "garland_preview.png"), dpi=150, bbox_inches="tight")
    print("wrote garland_preview.png")
except ImportError:
    pass
