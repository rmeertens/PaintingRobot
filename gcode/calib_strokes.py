#!/usr/bin/env python3
"""Write calib_strokes.gcode: a brush calibration sheet of 15 strokes in a row.

Every stroke is painted like a tree branch: it starts in the middle of the card pressed down
(full brush weight, thick) and runs straight down to the bottom (front) edge, lifting as it goes.
What changes from stroke to stroke:
  - MAX HEIGHT: how high the tip ends up above the paper (like LIFT in tree_brush.py)
  - ATTACK:     how quickly it gets there, i.e. over how many mm of the stroke the lift happens
                (short = fast attack, the stroke breaks off quickly; long = slow, a long taper)
Layout, left to right: 5 groups of 3. Each group is one max height (lowest on the left);
inside a group the attack goes fast -> medium -> slow. The groups have a slightly wider gap.
Uses the measured offsets in ../data/calibration.json.
Run:   python3 calib_strokes.py      then   python3 octo.py send calib_strokes.gcode
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OX, OY, OZ = CAL["offset"]["x"], CAL["offset"]["y"], CAL["offset"]["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]

# ---------------- TEST MATRIX ----------------
HEIGHTS = [3.0, 6.0, 9.0, 12.0, 16.0]   # max tip height above the paper (mm), one group each
ATTACKS = [10.0, 25.0, 45.0]           # mm of stroke over which the brush lifts to max height
# ---------------- BRUSH (same as tree_brush.py) ----------------
PRESS = 1.5          # start of stroke: tip this far below the paper (full brush weight)
HOLD_MM = 12.0       # first part of every stroke at full pressure, before the lift starts
STROKE_F = 1200
TRAVEL_F = 4000
HOVER = 19.0         # between strokes; kept above the highest stroke
APPROACH = 20.0      # first move after homing (clears the frame)
RELOAD_EVERY = 0     # pause to re-load the brush every N strokes (0 = never; 3 = fresh paint per group)
# ---------------- LAYOUT (fixture mm) ----------------
MARGIN = 8.0         # keep this far inside the paint window at the sides
BOTTOM_MARGIN = 6.0  # stop this far above the bottom (front) edge of the paint window
GROUP_GAP = 8.0      # extra space between height groups
STEP = 1.0           # point spacing along a stroke
# ---------------------------------------------------------------
BED = (220.0, 220.0)
Y_START = (PW["y0"] + PW["y1"]) / 2      # middle of the card
Y_END = PW["y0"] + BOTTOM_MARGIN         # bottom of the card
LENGTH = Y_START - Y_END
HOVER = max(HOVER, max(HEIGHTS) + 3)

if HOLD_MM + max(ATTACKS) > LENGTH:
    sys.exit(f"HOLD_MM + longest attack ({HOLD_MM + max(ATTACKS):.0f} mm) is longer than the stroke ({LENGTH:.0f} mm)")


def z_at(d, height, attack):
    """Tip height above the paper at distance d (mm) along the stroke."""
    if d <= HOLD_MM:
        return -PRESS
    s = min(1.0, (d - HOLD_MM) / attack)
    s = s * s * (3 - 2 * s)                               # same smooth S-curve lift as the tree
    return -PRESS + (PRESS + height) * s


def layout():
    n = len(HEIGHTS) * len(ATTACKS)
    span = (PW["x1"] - PW["x0"]) - 2 * MARGIN - GROUP_GAP * (len(HEIGHTS) - 1)
    pitch = span / (n - 1)
    out = []
    for gi, h in enumerate(HEIGHTS):
        for ai, a in enumerate(ATTACKS):
            i = gi * len(ATTACKS) + ai
            out.append((PW["x0"] + MARGIN + i * pitch + gi * GROUP_GAP, h, a))
    return out, pitch


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    if not (PW["x0"] + 2 <= x <= PW["x1"] - 2 and PW["y0"] + 2 <= y <= PW["y1"] - 2):
        sys.exit(f"stroke leaves the paint window at X{x:.1f} Y{y:.1f}")
    return px, py


S, PITCH = layout()
n_pts = int(round(LENGTH / STEP))
hover = CARD_Z + HOVER + OZ
names = {ATTACKS[0]: "fast", ATTACKS[-1]: "slow"}
g = [
    f"; CALIBRATION STROKES: {len(S)} strokes, middle of the card -> bottom edge, {LENGTH:.0f} mm long.",
    f"; Left to right: max height {', '.join(f'{h:g}' for h in HEIGHTS)} mm (groups of {len(ATTACKS)}),",
    f"; attack inside each group: lift over {', '.join(f'{a:g}' for a in ATTACKS)} mm (fast -> slow).",
    f"; Every stroke: {PRESS:g} mm pressed for the first {HOLD_MM:g} mm, then smooth lift.",
    f"; offsets from data/calibration.json: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}",
    "; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.",
    "; Load the brush with paint by hand at the pause.",
    "M104 S0", "M140 S0", "M107", "G21", "G90",
    "G28 ; home with the cartridge off",
    f"G1 Z{hover + 40:.2f} F600 ; bed down for attaching the brush",
    "M400",
    "M117 Attach loaded brush, Resume",
    "@pause ; snap the cartridge on (brush loaded with paint), then press Resume",
    f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; stay well clear of the paper and frame",
]
for k, (x, h, a) in enumerate(S):
    if RELOAD_EVERY and k and k % RELOAD_EVERY == 0:
        g += [f"G1 Z{hover + 30:.2f} F600 ; lift for re-loading", "M400",
              "M117 Re-load brush, Resume", "@pause ; load the brush, then press Resume",
              f"G1 Z{hover:.2f} F600"]
    x0, y0 = m(x, Y_START)
    label = names.get(a, "medium")
    g += [f"; stroke {k + 1}: max height {h:g} mm, attack {a:g} mm ({label})",
          f"M117 Stroke {k + 1}/{len(S)} H{h:g} A{a:g}",
          f"G0 X{x0:.2f} Y{y0:.2f} F{TRAVEL_F}"]
    if k == 0:
        g.append(f"G1 Z{hover:.2f} F600 ; come down to hover height only once over the card")
    g.append(f"G1 Z{CARD_Z + z_at(0, h, a) + OZ:.2f} F400")
    for i in range(1, n_pts + 1):
        d = LENGTH * i / n_pts
        px, py = m(x, Y_START - d)
        g.append(f"G1 X{px:.2f} Y{py:.2f} Z{CARD_Z + z_at(d, h, a) + OZ:.2f} F{STROKE_F}")
    g.append(f"G1 Z{hover:.2f} F600")
g += [f"G1 Z{hover + 30:.2f} F600 ; lift clear of the paper",
      f"G0 X{BED[0]:.2f} Y{BED[1]:.2f} F{TRAVEL_F} ; park top-right",
      "M400",
      "M84 X Y ; X/Y motors off (Z stays on)",
      "M117 Calibration done"]
open(os.path.join(HERE, "calib_strokes.gcode"), "w").write("\n".join(g) + "\n")
print(f"wrote calib_strokes.gcode: {len(S)} strokes, {LENGTH:.0f} mm long, pitch {PITCH:.1f} mm, {len(g)} lines")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig, (ax, az) = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [1.45, 1]})
    ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                               fill=False, ec="#aaa", ls="--"))
    ax.axhline(Y_START, color="#ddd", lw=0.8)
    TOUCH = 4.0   # assumed: bristles leave the paper about this far above it (unverified)
    cols = plt.cm.viridis([i / (len(ATTACKS) - 1) for i in range(len(ATTACKS))])
    for k, (x, h, a) in enumerate(S):
        ds = [LENGTH * i / n_pts for i in range(n_pts + 1)]
        segs, widths = [], []
        for i in range(n_pts):
            z = z_at(ds[i], h, a)
            w = max(0.0, 1 - (z + PRESS) / (PRESS + TOUCH))
            if w > 0:
                segs.append([(x, Y_START - ds[i]), (x, Y_START - ds[i + 1])])
                widths.append(0.4 + 6 * w ** 1.3)
        ax.add_collection(LineCollection(segs, linewidths=widths, capstyle="round",
                                         colors=[(0.08, 0.35, 0.2, 0.85)] * len(segs)))
        ax.text(x, Y_START + 4, f"{k + 1}", ha="center", fontsize=7)
        ax.text(x, PW["y0"] - 4, f"A{a:g}", ha="center", va="top", fontsize=6, color="#555")
        if k % len(ATTACKS) == 1:
            ax.text(x, Y_START + 12, f"max {h:g} mm", ha="center", fontsize=8, weight="bold")
    ax.set_xlim(PW["x0"] - 5, PW["x1"] + 5)
    ax.set_ylim(PW["y0"] - 12, PW["y1"] + 3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"calib_strokes.gcode - card view (simulated width; assumes contact ends ~{TOUCH:g} mm up)", fontsize=9)
    for ai, a in enumerate(ATTACKS):
        for h in HEIGHTS:
            ds = [LENGTH * i / n_pts for i in range(n_pts + 1)]
            az.plot(ds, [z_at(d, h, a) for d in ds], color=cols[ai], lw=1.2,
                    label=f"attack {a:g} mm" if h == HEIGHTS[0] else None)
    az.axhline(0, color="k", lw=0.8)
    az.text(1, 0.3, "paper", fontsize=7)
    az.set_xlabel("distance along stroke from the middle of the card (mm)")
    az.set_ylabel("brush tip above paper (mm)")
    az.set_title("Z profiles: 5 max heights x 3 attacks", fontsize=9)
    az.legend(fontsize=8)
    az.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "calib_strokes_preview.png"), dpi=150, bbox_inches="tight")
    print("wrote calib_strokes_preview.png")
except ImportError:
    pass
