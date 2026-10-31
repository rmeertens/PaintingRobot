"""Christmas tree painting G-code for the automatic painting printer (Ender 5 + brush cartridge).

Reads ../data/fixture_coordinates.json, so it follows the fixture design.
Run from anywhere:  python3 gcode/xmas_tree.py
Writes next to this script:
  xmas_tree_DRYRUN.gcode  - same moves, but the brush hovers above the hold-down frame
  xmas_tree_PAINT.gcode   - the real painting run
  xmas_tree_preview.png   - top view of the fixture and brush paths (needs matplotlib)

Jars (front to back):  J1 water | J2 green | J3 brown, swapped to yellow at the pause | J4 red
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))

# ---------------- CALIBRATION (not measured yet, see README section 6/7) ----------------
FIXTURE_OFFSET = (0.0, 0.0)   # printer X/Y of the base plate's front-left corner
BRUSH_OFFSET = (0.0, -18.0)   # brush tip relative to the old nozzle (README: ~18 mm towards the front)
BED_MAX = (220.0, 220.0)      # Ender 5 travel

# ---------------- JARS ----------------
JARS = {j["id"]: j for j in FIX["jars"]}
WATER, GREEN, BROWN, RED = "J1", "J2", "J3", "J4"
YELLOW = "J3"                 # J3 is swapped from brown to yellow during the pause

# ---------------- Z (fixture coordinates: mm above the glass, brush TIP) ----------------
CARD_Z = FIX["card_area"]["surface_z"]                  # 5.0, where you zero the brush
SAFE_Z = FIX["safe_travel_tip_z"] + 3                   # travel height, clears jar rims
PAINT_Z = CARD_Z - 1.5        # commanded slightly below the card; the plunger floats up, so
                              # pressure is just its own weight
DRY_Z = FIX["paint_window"]["frame_top_z"] + 3          # dry run: hover above the frame
DIP_Z = JARS["J1"]["floor_z"] + 6                       # tip 6 mm above the jar floor
WIPE_Z = JARS["J1"]["rim_z"] - 4                        # tip just below the rim for wiping
WIPE_R = 12                   # sideways move from jar centre to drag the bristles on the rim

# ---------------- STROKES ----------------
STROKE_F = 1500   # mm/min while painting
TRAVEL_F = 4000
Z_F = 900
RELOAD_MM = 70    # re-dip after this much painted stroke
LINE_GAP = 3.0    # spacing of the fill strokes

PW = FIX["paint_window"]
cx = (PW["x0"] + PW["x1"]) / 2
base_y = 60.0     # bottom of the foliage, fixture Y


def to_machine(x, y):
    mx = x + FIXTURE_OFFSET[0] - BRUSH_OFFSET[0]
    my = y + FIXTURE_OFFSET[1] - BRUSH_OFFSET[1]
    if not (0 <= mx <= BED_MAX[0] and 0 <= my <= BED_MAX[1]):
        raise SystemExit(f"Out of reach: fixture ({x:.1f}, {y:.1f}) -> printer ({mx:.1f}, {my:.1f})")
    return mx, my


def tri_fill(y0, y1, hw0, hw1):
    strokes, y, flip = [], y0, False
    while y <= y1 + 1e-6:
        hw = hw0 + (hw1 - hw0) * (y - y0) / (y1 - y0)
        if hw > 1:
            a, b = (cx - hw, y), (cx + hw, y)
            strokes.append([b, a] if flip else [a, b])
            flip = not flip
        y += LINE_GAP
    return strokes


def design():
    """List of (colour_jar, [stroke points...]) in painting order, fixture coordinates."""
    parts = []
    for i in range(4):                                       # trunk
        x = cx - 6 + i * 4
        parts.append((BROWN, [(x, base_y - 25), (x, base_y + 4)]))
    for y0, y1, w0, w1 in [(0, 40, 48, 16), (28, 68, 38, 11), (56, 98, 28, 0)]:
        for s in tri_fill(base_y + y0, base_y + y1, w0, w1):  # three foliage tiers
            parts.append((GREEN, s))
    for bx, by in [(-25, 15), (18, 25), (-8, 45), (20, 60), (-15, 75), (6, 85)]:
        x, y = cx + bx, base_y + by                           # baubles
        parts.append((RED, [(x - 1.5, y), (x + 1.5, y), (x, y + 1.5), (x - 1.5, y)]))
    sy, star = base_y + 106, []
    for k in range(6):                                        # star
        a = math.pi / 2 + k * 4 * math.pi / 5
        star.append((cx + 8 * math.cos(a), sy + 8 * math.sin(a)))
    parts.append(("PAUSE", None))
    parts.append((YELLOW, star))
    m = 3  # keep strokes this far inside the frame opening
    for c, pts in parts:
        for x, y in pts or []:
            assert PW["x0"] + m <= x <= PW["x1"] - m and PW["y0"] + m <= y <= PW["y1"] - m, (x, y)
    return parts


def build(dry):
    pz = DRY_Z if dry else PAINT_Z
    g = []
    out = g.append
    st = {"since": 0.0, "jar": None, "pos": None}

    def travel(x, y):
        mx, my = to_machine(x, y)
        out(f"G0 Z{SAFE_Z:.2f} F{Z_F}")
        out(f"G0 X{mx:.2f} Y{my:.2f} F{TRAVEL_F}")
        st["pos"] = (x, y)

    def lin(x, y, f):
        mx, my = to_machine(x, y)
        out(f"G1 X{mx:.2f} Y{my:.2f} F{f}")

    def wipe(j):
        out(f"G1 Z{WIPE_Z:.2f} F{Z_F}")
        lin(j["cx"] + WIPE_R, j["cy"], 1200)          # bristles against the rim
        out(f"G1 Z{SAFE_Z:.2f} F{Z_F}")                # drag up over the edge

    def dip(jid, swirl):
        j = JARS[jid]
        travel(j["cx"], j["cy"])
        out(f"G1 Z{DIP_Z:.2f} F{Z_F}")
        for k in range(swirl):
            a = k * math.pi / 2
            lin(j["cx"] + 5 * math.cos(a), j["cy"] + 5 * math.sin(a), 2000)
        lin(j["cx"], j["cy"], 2000)
        out("G4 P500")
        wipe(j)

    def load(jid):
        if st["jar"] not in (None, jid):
            out(f"; rinse in {WATER}")
            dip(WATER, swirl=12)
        out(f"; load paint from {jid}")
        dip(jid, swirl=5)
        st["jar"], st["since"] = jid, 0.0

    out("; Christmas tree - automatic painting printer" + (" - DRY RUN (hovering)" if dry else ""))
    out("; BEFORE STARTING: X/Y homed with the cartridge OFF, cartridge on,")
    out(f"; brush tip jogged down until it just touches the card (= fixture Z {CARD_Z}).")
    out("; Jars: J1 water, J2 green, J3 brown (swap to yellow at the pause), J4 red")
    out("M104 S0\nM140 S0\nM107")
    out("G21\nG90")
    out(f"G92 Z{CARD_Z:.2f} ; brush tip is touching the card now")
    out(f"G1 Z{SAFE_Z:.2f} F600")

    for jid, pts in design():
        if jid == "PAUSE":
            out(f"; rinse before swapping jars")
            dip(WATER, swirl=12)
            st["jar"] = None
            travel(cx, PW["y0"] + 10)
            out("M117 Swap J3 for yellow, then Resume")
            out("@pause")
            continue
        if st["jar"] != jid:
            load(jid)
        travel(*pts[0])
        out(f"G1 Z{pz:.2f} F{Z_F}")
        for x, y in pts[1:]:
            px, py = st["pos"]
            d = math.hypot(x - px, y - py)
            if st["since"] + d > RELOAD_MM:
                load(jid)
                travel(px, py)
                out(f"G1 Z{pz:.2f} F{Z_F}")
            lin(x, y, STROKE_F)
            st["since"] += d
            st["pos"] = (x, y)
        out(f"G1 Z{SAFE_Z:.2f} F{Z_F}")

    out("; final rinse and park")
    dip(WATER, swirl=12)
    travel(cx, PW["y0"] + 10)
    out("M117 Done - let the card dry")
    out("M84")
    return "\n".join(g) + "\n"


def preview(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {GREEN: "green", BROWN: "saddlebrown", RED: "red", "Y": "gold"}
    fig, ax = plt.subplots(figsize=(5.5, 6))
    ax.add_patch(plt.Rectangle((0, 0), 220, 220, fill=False, ls=":"))
    ca = FIX["card_area"]
    ax.add_patch(plt.Rectangle((ca["x0"], ca["y0"]), ca["x1"] - ca["x0"], ca["y1"] - ca["y0"], fill=False))
    ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                               fill=False, ls="--", ec="grey"))
    reach = 220 - FIXTURE_OFFSET[1] + BRUSH_OFFSET[1]
    ax.axhline(reach, color="orange", lw=1)
    ax.text(2, reach + 2, "brush Y reach limit (uncalibrated)", fontsize=6, color="orange")
    after_pause = False
    for jid, pts in design():
        if jid == "PAUSE":
            after_pause = True
            continue
        c = "gold" if after_pause else col[jid]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=c, lw=3, solid_capstyle="round")
    labels = {"J1": "J1 water", "J2": "J2 green", "J3": "J3 brown\n→ yellow", "J4": "J4 red"}
    for jid, j in JARS.items():
        ax.add_patch(plt.Circle((j["cx"], j["cy"]), 20.5, fill=False))
        ax.text(j["cx"], j["cy"], labels[jid], ha="center", va="center", fontsize=6)
    ax.set_aspect("equal")
    ax.set_xlim(-5, 225)
    ax.set_ylim(-5, 225)
    ax.set_title("Fixture top view (front of printer at the bottom)", fontsize=9)
    plt.savefig(path, dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    for name, dry in (("xmas_tree_DRYRUN.gcode", True), ("xmas_tree_PAINT.gcode", False)):
        open(os.path.join(HERE, name), "w").write(build(dry))
    try:
        preview(os.path.join(HERE, "xmas_tree_preview.png"))
    except ImportError:
        print("matplotlib not installed: skipped the preview")
    print("written to", HERE)
