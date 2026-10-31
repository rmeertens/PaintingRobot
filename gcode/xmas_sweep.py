"""Sweeping-brush Christmas tree for the automatic painting printer.

Brush-plot style: every branch is one long curved stroke from a single dip, painted from the
spine outwards, so it starts heavy and fades towards the tip. Colours mix on the brush
(green -> green+yellow -> yellow going up the tree), and a red garland and yellow star go on top.

Shares calibration and Z settings with xmas_tree.py (edit them there).
Run:  python3 gcode/xmas_sweep.py
Writes next to this script:
  xmas_sweep_PEN.gcode     optional first pass with a pen: line drawing of the same paths
  xmas_sweep_DRYRUN.gcode  brush route hovering above the frame
  xmas_sweep_PAINT.gcode   the painting run
  xmas_sweep_preview.png   rough simulation of how it should look

Jars (front to back):  J1 water | J2 green | J3 yellow | J4 red   (no jar swap needed)
"""
import math
import os
import random

from xmas_tree import (FIX, JARS, PW, CARD_Z, SAFE_Z, PAINT_Z, DRY_Z, DIP_Z, WIPE_Z, WIPE_R,
                       TRAVEL_F, Z_F, to_machine)

HERE = os.path.dirname(os.path.abspath(__file__))
WATER, GREEN, YELLOW, RED = "J1", "J2", "J3", "J4"

# ---------------- LOOK ----------------
SEED = 7            # change for a different (but similar) tree
LEVELS = 15         # branch levels per side
BASE_Y = 46.0       # bottom branch root (fixture Y)
TOP_Y = 176.0       # tree tip
MAX_HALF_W = 58.0   # half-width of the bottom branches
STROKE_F = 1200     # slower than travel so the brush lays paint down evenly
DRY_WAIT_S = 90     # pause before the garland so the red doesn't mud into wet green
PEN_Z = CARD_Z - 0.5          # pen pass: plunger floats, light contact
PEN_TRAVEL_Z = PW["frame_top_z"] + 6

cx = (PW["x0"] + PW["x1"]) / 2


def bezier(p0, p1, p2, p3, step=1.5):
    approx = sum(math.dist(a, b) for a, b in ((p0, p1), (p1, p2), (p2, p3)))
    n = max(4, int(approx / step))
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return pts


def design():
    """List of (load, points). load is a tuple of jars dipped in order (rinse first if it changes)."""
    rng = random.Random(SEED)   # re-seeded so every file gets the identical tree
    parts = []
    H = TOP_Y - BASE_Y

    # spine: one stroke from bottom to tip, green
    parts.append(((GREEN,), bezier((cx, BASE_Y - 6), (cx + 1.5, BASE_Y + H * 0.35),
                                   (cx - 1.5, BASE_Y + H * 0.7), (cx, TOP_Y))))

    # trunk: red + green on the brush mixes to brown
    parts.append(((RED, GREEN), bezier((cx - 2, BASE_Y - 4), (cx - 2.5, BASE_Y - 10),
                                       (cx - 2, BASE_Y - 16), (cx - 1.5, BASE_Y - 22))))
    parts.append(((RED, GREEN), bezier((cx + 2, BASE_Y - 4), (cx + 2.5, BASE_Y - 10),
                                       (cx + 2, BASE_Y - 16), (cx + 1.5, BASE_Y - 22))))

    # branches, bottom to top, alternating sides; painted from the spine outwards
    for i in range(LEVELS):
        t = i / (LEVELS - 1)
        if t < 0.4:
            load = (GREEN,)
        elif t < 0.75:
            load = (YELLOW, GREEN)          # yellow first, green on the tip: light green that shifts
        else:
            load = (YELLOW,)
        y0 = BASE_Y + t * H * 0.93
        w = (MAX_HALF_W * (1 - t) ** 0.85 + 5) * rng.uniform(0.92, 1.05)
        drop = (9 + 20 * (1 - t)) * rng.uniform(0.85, 1.15)
        for side in (-1, 1) if i % 2 == 0 else (1, -1):
            jit = rng.uniform(-1.5, 1.5)
            p0 = (cx + side * 1.0, y0 + jit)
            p1 = (cx + side * w * 0.30, y0 + 3 + jit)             # leaves the spine slightly upwards
            p2 = (cx + side * w * 0.75, y0 - drop * 0.35 + jit)
            p3 = (cx + side * w, y0 - drop + jit)                  # droops at the tip
            pts = bezier(p0, p1, p2, p3)
            ex, ey = pts[-1]
            pts += bezier((ex, ey), (ex + side * 1.5, ey - 0.3),
                          (ex + side * 2.8, ey + 0.2), (ex + side * 3.5, ey + 1.2), step=1)[1:]  # small lift-off flick
            parts.append((load, pts))

    parts.append(("WAIT", None))

    # garland: three sagging red arcs that swing down the tree
    for k, (ya, yb) in enumerate([(150, 132), (120, 98), (88, 62)]):
        def half_w(y):
            tt = (y - BASE_Y) / H
            return (MAX_HALF_W * (1 - tt) ** 0.85 + 5) * 0.82
        a = (cx - half_w(ya), ya) if k % 2 == 0 else (cx + half_w(ya), ya)
        b = (cx + half_w(yb), yb) if k % 2 == 0 else (cx - half_w(yb), yb)
        sag = 9 + 3 * k
        m1 = (a[0] + (b[0] - a[0]) * 0.33, a[1] + (b[1] - a[1]) * 0.33 - sag)
        m2 = (a[0] + (b[0] - a[0]) * 0.66, a[1] + (b[1] - a[1]) * 0.66 - sag)
        parts.append(((RED,), bezier(a, m1, m2, b)))

    # star: a yellow burst of short strokes flicked out from one point
    sy = TOP_Y + 9
    for k in range(8):
        a = math.pi / 2 + k * math.pi / 4
        r = 9 if k % 2 == 0 else 5.5
        p0 = (cx + 1.2 * math.cos(a), sy + 1.2 * math.sin(a))
        p3 = (cx + r * math.cos(a), sy + r * math.sin(a))
        parts.append(((YELLOW,), bezier(p0, p0, p3, p3, step=1)))

    m = 3
    for load, pts in parts:
        for x, y in pts or []:
            assert PW["x0"] + m <= x <= PW["x1"] - m and PW["y0"] + m <= y <= PW["y1"] - m, (x, y)
    return parts


def build(mode):
    """mode: 'paint', 'dry' or 'pen'."""
    g = []
    out = g.append
    st = {"load": None}
    travel_z = PEN_TRAVEL_Z if mode == "pen" else SAFE_Z
    down_z = {"paint": PAINT_Z, "dry": DRY_Z, "pen": PEN_Z}[mode]

    def travel(x, y):
        mx, my = to_machine(x, y)
        out(f"G0 Z{travel_z:.2f} F{Z_F}")
        out(f"G0 X{mx:.2f} Y{my:.2f} F{TRAVEL_F}")

    def lin(x, y, f):
        mx, my = to_machine(x, y)
        out(f"G1 X{mx:.2f} Y{my:.2f} F{f}")

    def dip(jid, swirl, depth=DIP_Z):
        j = JARS[jid]
        travel(j["cx"], j["cy"])
        out(f"G1 Z{depth:.2f} F{Z_F}")
        for k in range(swirl):
            a = k * math.pi / 2
            lin(j["cx"] + 5 * math.cos(a), j["cy"] + 5 * math.sin(a), 2000)
        lin(j["cx"], j["cy"], 2000)
        out("G4 P400")
        out(f"G1 Z{WIPE_Z:.2f} F{Z_F}")
        lin(j["cx"] + WIPE_R, j["cy"], 1200)
        out(f"G1 Z{SAFE_Z:.2f} F{Z_F}")

    def load(seq):
        same_family = st["load"] is not None and st["load"] == seq
        if not same_family and st["load"] is not None:
            out(f"; rinse in {WATER}")
            dip(WATER, 12)
        out(f"; load {'+'.join(seq)}")
        for n, jid in enumerate(seq):
            # second colour is only touched on the tip, so it streaks rather than fully mixes
            dip(jid, 5 if n == 0 else 1, DIP_Z if n == 0 else DIP_Z + 8)
        st["load"] = seq

    title = {"paint": "", "dry": " - DRY RUN (hovering)", "pen": " - PEN UNDERDRAWING (pen in plunger)"}
    out("; Sweeping-brush Christmas tree - automatic painting printer" + title[mode])
    out("; BEFORE STARTING: X/Y homed with the cartridge OFF, cartridge on,")
    out(f"; tool tip jogged down until it just touches the card (= fixture Z {CARD_Z}).")
    if mode != "pen":
        out("; Jars: J1 water, J2 green, J3 yellow, J4 red")
    out("M104 S0\nM140 S0\nM107\nG21\nG90")
    out(f"G92 Z{CARD_Z:.2f} ; tool tip is touching the card now")
    out(f"G1 Z{travel_z:.2f} F600")

    for seq, pts in design():
        if seq == "WAIT":
            if mode == "paint":
                out("; let the branches set before the garland")
                dip(WATER, 12)
                st["load"] = None
                travel(cx, PW["y0"] + 10)
                out(f"M117 Drying {DRY_WAIT_S}s")
                out(f"G4 S{DRY_WAIT_S}")
            continue
        if mode != "pen":
            load(seq)            # one dip per stroke: the stroke fades as the brush empties
        travel(*pts[0])
        out(f"G1 Z{down_z:.2f} F{Z_F}")
        for x, y in pts[1:]:
            lin(x, y, STROKE_F)
        out(f"G1 Z{travel_z:.2f} F{Z_F}")

    if mode != "pen":
        out("; final rinse")
        dip(WATER, 12)
    out(f"G0 Z{SAFE_Z:.2f} F{Z_F}")
    travel(cx, PW["y0"] + 10)
    out("M117 Done - let the card dry")
    out("M84")
    return "\n".join(g) + "\n"


def preview(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.colors import to_rgb

    base = {GREEN: "#1d6b3c", YELLOW: "#f1c232", RED: "#c41f30"}

    def mix(seq):
        if len(seq) == 1:
            return to_rgb(base[seq[0]])
        a, b = to_rgb(base[seq[0]]), to_rgb(base[seq[1]])
        return tuple(0.6 * x + 0.4 * y for x, y in zip(a, b))

    fig, ax = plt.subplots(figsize=(5, 7))
    ax.set_facecolor("#fbf8f1")
    for seq, pts in design():
        if seq == "WAIT":
            continue
        c = mix(seq)
        segs = [[pts[i], pts[i + 1]] for i in range(len(pts) - 1)]
        n = max(1, len(segs) - 1)
        widths = [5.5 - 3.5 * (i / n) ** 0.8 for i in range(len(segs))]          # brush lifts/thins
        alphas = [0.95 - 0.6 * (i / n) ** 1.3 for i in range(len(segs))]         # paint runs out
        ax.add_collection(LineCollection(segs, linewidths=widths,
                                         colors=[(*c, a) for a in alphas], capstyle="round"))
    ax.set_xlim(PW["x0"], PW["x1"])
    ax.set_ylim(PW["y0"], PW["y1"])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Simulated brush plot (approximate)", fontsize=9)
    plt.savefig(path, dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    for name, mode in (("xmas_sweep_PEN.gcode", "pen"), ("xmas_sweep_DRYRUN.gcode", "dry"),
                       ("xmas_sweep_PAINT.gcode", "paint")):
        open(os.path.join(HERE, name), "w").write(build(mode))
    try:
        preview(os.path.join(HERE, "xmas_sweep_preview.png"))
    except ImportError:
        print("matplotlib not installed: skipped the preview")
    print("written to", HERE)
