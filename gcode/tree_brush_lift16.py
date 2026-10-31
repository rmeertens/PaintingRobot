#!/usr/bin/env python3
"""Write tree_brush.gcode: a fir tree lying on its side (tip to the right), filled with brush strokes.

Every stroke starts on the tree's centre line with the brush pressed down (thick) and lifts
gradually as it moves out, so it thins to a point at the tree's edge. Strokes are painted from
the tip of the tree down to the base, each spot first towards one edge, then the other.
Uses the measured offsets in ../data/calibration.json.
Run:   python3 tree_brush.py      then   python3 octo.py send tree_brush.gcode
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OX, OY, OZ = CAL["offset"]["x"], CAL["offset"]["y"], CAL["offset"]["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]

# ---------------- SHAPE (fixture mm) ----------------
LENGTH = 176.0       # base to tip, along the card's long side
WIDTH = 126.0        # widest point, across the card
# tiers as (start, end, half-width at start, half-width at end), in fractions of LENGTH / WIDTH/2
# Each tier narrows a lot before the next one starts, so the step back in to the trunk at each
# branch is deep and the three layers read clearly.
TIERS = [(0.00, 1.00, 1.00, 0.00)]   # one tier: a single triangle from the base to the tip
SHIFT_X = 12.0       # move the whole tree right (+) or left (-) on the card
DENT = 14.0          # the base curves in towards the tip by this much in the middle (0 = straight)
# ---------------- BRUSH ----------------
PITCH = 3.5          # spacing between strokes along the tree (about one brush width)
CENTRE_OVERLAP = 1.5 # start each stroke this far past the centre line, so the halves join
EDGE_MARGIN = 6.0    # stop this far inside the outline (strokes end before the edge)
LEAN_DEG = 8.0       # strokes sweep back towards the base as they go out, like needles (at the tip)
LEAN_BASE_DEG = 30.0 # ... increasing to this at the base, so the lowest strokes reach the corners
JITTER_DEG = 3.0     # small random variation per stroke (fixed seed)
CURVE = 10.0         # strokes bend further back as they go out: extra droop (mm) at full half-width
CURVE_JITTER = 0.3   # +/- fraction of random variation in that bend
PRESS = 1.5          # start of stroke: tip this far below the paper (full brush weight)
LIFT = 16.0          # end of stroke: tip this far above the paper
HOLD = 0.25          # fraction of the stroke kept at full pressure before lifting starts
STROKE_F = 1200
TRAVEL_F = 4000
HOVER = 19.0         # lift above the paper between strokes (above LIFT)
APPROACH = 20.0      # height above the paper for the first move after homing (clears the frame)
SEED = 3
# -------------------------------------------------------
CX = (PW["x0"] + PW["x1"]) / 2
CY = (PW["y0"] + PW["y1"]) / 2
BED = (220.0, 220.0)
U0 = CX - LENGTH / 2 + SHIFT_X # fixture X of the tree's base


def half_width(f):
    """Tree half-width at fraction f (0 = base, 1 = tip): the widest tier covering that point."""
    if f < 0 or f > 1:
        return 0.0
    w = 0.0
    for a, b, wa, wb in TIERS:
        if a <= f <= b:
            w = max(w, wa + (wb - wa) * (f - a) / (b - a))
    return w * WIDTH / 2


def base_u(v):
    """Where the (dented) base is, at distance v from the centre line."""
    h = WIDTH / 2
    return DENT * max(0.0, 1 - (v / h) ** 2)


def inside(u, v, margin):
    return u >= base_u(v) + margin * 0.5 and abs(v) <= half_width(u / LENGTH) - margin


def outline():
    n = 400
    top = [(U0 + LENGTH * i / n, CY + half_width(i / n)) for i in range(n + 1)]
    bot = [(x, 2 * CY - y) for x, y in top[::-1]]
    h = WIDTH / 2
    base = [(U0 + base_u(-h + 2 * h * i / n), CY - h + 2 * h * i / n) for i in range(n + 1)]
    return top + bot + base


def strokes():
    """(points, pressure profile) per stroke, in painting order: tip -> base, middle -> edge."""
    rng = random.Random(SEED)
    out = []
    u = LENGTH - PITCH
    while u > 0:
        hw = half_width(u / LENGTH)
        if hw > EDGE_MARGIN + 3 and u >= DENT + EDGE_MARGIN * 0.5:
            for side in (+1, -1):
                lean = LEAN_BASE_DEG + (LEAN_DEG - LEAN_BASE_DEG) * (u / LENGTH)
                ang = math.radians(lean + rng.uniform(-JITTER_DEG, JITTER_DEG))
                du_dv = -math.tan(ang)                     # sweep back towards the base
                k = CURVE / (WIDTH / 2) ** 2 * (1 + rng.uniform(-CURVE_JITTER, CURVE_JITTER))
                def off(vv):                               # how far back the stroke is at vv: lean + bend
                    vv = max(vv, 0)
                    return du_dv * vv - k * vv * vv
                # find where the stroke can start (the centre line, or just past the dented base),
                # then walk straight out until it reaches the outline
                v0 = 0.0
                while v0 < hw and not inside(u + off(v0), v0, EDGE_MARGIN):
                    v0 += 0.25
                v = v0
                while True:
                    nv = v + 0.25
                    if not inside(u + off(nv), nv, EDGE_MARGIN):
                        break
                    v = nv
                if v0 > 0 or v - v0 < 3:
                    continue                               # only strokes that start on the centre line
                start = -CENTRE_OVERLAP if v0 == 0 else v0
                n = max(6, int((v - start) / 1.0))
                pts = []
                for i in range(n + 1):
                    vv = start + (v - start) * i / n
                    pts.append((U0 + u + off(vv), CY + side * vv))
                out.append(pts)
        u -= PITCH
    return out


def z_at(t):
    """Brush tip height (fixture Z) along a stroke, t = 0 at the centre ... 1 at the edge."""
    if t <= HOLD:
        return CARD_Z - PRESS
    s = (t - HOLD) / (1 - HOLD)
    s = s * s * (3 - 2 * s)                                    # smooth lift
    return CARD_Z - PRESS + (PRESS + LIFT) * s


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


S = strokes()
for pts in S:
    for x, y in pts:
        if not (PW["x0"] + 2 <= x <= PW["x1"] - 2 and PW["y0"] + 2 <= y <= PW["y1"] - 2):
            sys.exit(f"stroke leaves the paint window at X{x:.1f} Y{y:.1f}")

hover = CARD_Z + HOVER + OZ
g = [
    "; TREE BRUSH: fir on its side (tip right), strokes from the centre line out to the edge,",
    f"; thick to thin, painted tip -> base. {len(S)} strokes.",
    f"; offsets from data/calibration.json: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}",
    "; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.",
    "; Load the brush with paint by hand at the pause (no jar dipping in this file).",
    "M104 S0", "M140 S0", "M107", "G21", "G90",
    "G28 ; home with the cartridge off",
    f"G1 Z{hover + 40:.2f} F600 ; bed down for attaching the brush",
    "M400",
    "M117 Attach loaded brush, Resume",
    "@pause ; snap the cartridge on (brush loaded with paint), then press Resume",
    f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; stay well clear of the paper and frame",
]
for k, pts in enumerate(S):
    x0, y0 = m(*pts[0])
    g += [f"; stroke {k + 1}", f"G0 X{x0:.2f} Y{y0:.2f} F{TRAVEL_F}"]
    if k == 0:
        g.append(f"G1 Z{hover:.2f} F600 ; come down to hover height only once over the card")
    g.append(f"G1 Z{z_at(0) + OZ:.2f} F400")
    for i, (x, y) in enumerate(pts[1:], 1):
        px, py = m(x, y)
        g.append(f"G1 X{px:.2f} Y{py:.2f} Z{z_at(i / (len(pts) - 1)) + OZ:.2f} F{STROKE_F}")
    g.append(f"G1 Z{hover:.2f} F600")
g += [f"G1 Z{hover + 30:.2f} F600 ; lift clear of the paper",
      f"G0 X{BED[0]:.2f} Y{BED[1]:.2f} F{TRAVEL_F} ; park top-right",
      "M400",
      "M84 X Y ; X/Y motors off (Z stays on)",
      "M117 Tree done"]
open(os.path.join(HERE, "tree_brush.gcode"), "w").write("\n".join(g) + "\n")
print(f"wrote tree_brush.gcode: {len(S)} strokes, {len(g)} lines")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig, ax = plt.subplots(figsize=(9, 6.3))
    ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                               fill=False, ec="#aaa", ls="--"))
    ox, oy = zip(*outline())
    ax.plot(ox, oy, color="#e0902a", lw=1, ls=":", label="tree outline (not painted)")
    for k, pts in enumerate(S):
        segs = [[pts[i], pts[i + 1]] for i in range(len(pts) - 1)]
        n = len(segs)
        widths = [0.6 + 5.4 * (1 - min(1, max(0, (i / n - HOLD) / (1 - HOLD)))) ** 1.5 for i in range(n)]
        shade = 0.25 + 0.5 * k / len(S)
        ax.add_collection(LineCollection(segs, linewidths=widths, capstyle="round",
                                         colors=[(0.08, 0.32 + 0.2 * shade, 0.17, 0.85)] * n))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("tree_brush.gcode - simulated brush width (thick at the centre line, thin at the edge)", fontsize=9)
    plt.savefig(os.path.join(HERE, "tree_brush_preview.png"), dpi=150, bbox_inches="tight")
    print("wrote tree_brush_preview.png")
except ImportError:
    pass
