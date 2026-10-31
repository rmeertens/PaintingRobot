#!/usr/bin/env python3
"""A bat in flight made of lots of little bats, drawn in two pencil layers:
   bats_big.gcode   - thick-tip pencil: the big bats (outline + dense fill)
   bats_small.gcode - thin-tip pencil: small bats filling the gaps
Original design (bat outline and the little bat shape are drawn here, not traced).

Each file homes with the pencil on (fine on this rig: the tip sits ~1 mm below nozzle height and the
plunger floats), lifts clear of the frame straight away, draws, and parks top-right.
Run:   python3 bat_swarm.py      then send bats_big.gcode, swap pencils, send bats_small.gcode
"""
import json
import math
import os
import random
import sys

from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OFF = CAL.get("pencil_offset") or CAL["offset"]
OX, OY, OZ = OFF["x"], OFF["y"], OFF["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]
CX, CY = (PW["x0"] + PW["x1"]) / 2, (PW["y0"] + PW["y1"]) / 2

# ---------------- SETTINGS ----------------
SPAN = 184.0          # wingspan of the big bat outline (mm)
SEED = 11
BIG = dict(name="big", w=(9.0, 15.0), gap=1.3, tries=20000, hatch=0.9, dz=0.0, inside=0.55)   # thick-tip pencil
SMALL = dict(name="small", w=(2.6, 5.5), gap=0.6, tries=120000, hatch=0.45, dz=0.0, inside=0.4) # thin-tip pencil
# dz: extra Z for that pencil if its tip sits higher (+) or lower (-) than the calibrated one
PENCIL_DOWN, PEN_UP, APPROACH = 1.0, 3.0, 20.0
DRAW_F, TRAVEL_F = 1500, 4000
BED = (220.0, 220.0)
# ------------------------------------------


def qbez(a, c, b, n=10):
    return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]) for t in (i / n for i in range(n + 1))]


def wing(shoulder, wrist, tips, leg, side):
    """Membrane wing: leading edge to the wrist and first finger, then scalloped (concave) edges
    between the finger tips, back to the leg."""
    pts = [shoulder] + qbez(shoulder, ((shoulder[0] + wrist[0]) / 2, wrist[1] + 4), wrist, 8)[1:]
    pts += qbez(wrist, ((wrist[0] + tips[0][0]) / 2, (wrist[1] + tips[0][1]) / 2 + 3), tips[0], 8)[1:]
    chain = tips + [leg]
    for a, b in zip(chain[:-1], chain[1:]):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        c = (mid[0] + (wrist[0] - mid[0]) * 0.28, mid[1] + (wrist[1] - mid[1]) * 0.28)  # pull towards the wrist
        pts += qbez(a, c, b, 12)[1:]
    return Polygon(pts).buffer(0)


def big_bat():
    """Original outline: a bat in flight seen a little from below and tilted, wings at different
    points of the beat (left wing up, right wing down), fingered membrane, round head and face."""
    body = affinity.rotate(Point(0, -6).buffer(1).pipe if False else affinity.scale(Point(0, 0).buffer(1), 8.5, 19), 8)
    body = affinity.translate(body, 0, -6)
    head = Point(2, 16).buffer(7.5)
    ears = Polygon([(-3, 20), (-7.5, 30), (1, 22.5)]).buffer(1.2).union(Polygon([(4, 22.5), (9.5, 29), (8.5, 18.5)]).buffer(1.2))
    left = wing((-6, 9), (-36, 30), [(-90, 42), (-95, 14), (-80, -12), (-52, -27)], (-7, -22), -1)
    right = wing((6, 6), (35, 13), [(88, 18), (90, -10), (72, -32), (44, -40)], (8, -24), 1)
    tail = Polygon(qbez((-7, -22), (0, -26), (0, -38), 6) + qbez((0, -38), (2, -27), (8, -24), 6)[1:])
    shape = unary_union([body, head, ears, left, right, tail.buffer(0.5)]).buffer(1.5).buffer(-1.5)
    minx, miny, maxx, maxy = shape.bounds
    s = SPAN / (maxx - minx)
    shape = affinity.scale(shape, s, s, origin=(0, 0))
    minx, miny, maxx, maxy = shape.bounds
    return affinity.translate(shape, CX - (minx + maxx) / 2, CY - (miny + maxy) / 2)


def little_bat(w, ang, x, y):
    """Small flying bat (original icon), width w, facing up, rotated ang degrees."""
    half = [(0.0, 0.10), (0.035, 0.20), (0.06, 0.12), (0.12, 0.15), (0.21, 0.26), (0.34, 0.31),
            (0.50, 0.25), (0.44, 0.15), (0.38, 0.17), (0.32, 0.08), (0.24, 0.10), (0.17, 0.0),
            (0.07, -0.035), (0.0, -0.15)]          # wings raised mid-beat
    pts = half + [(-px, py) for px, py in half[::-1]][1:-1]
    p = Polygon(pts)
    p = affinity.scale(p, w, w, origin=(0, 0))
    p = affinity.rotate(p, ang, origin=(0, 0))
    return affinity.translate(p, x, y)


def place(region, cfg, placed, rng):
    """Random packing: keep a bat if enough of it is inside the big bat and it clears the others.
    Bats hanging over the edge are clipped later, which makes the wing edge crisp."""
    cell = 8.0
    grid = {}

    def add(p):
        x0, y0, x1, y1 = p.bounds
        for i in range(int(x0 // cell), int(x1 // cell) + 1):
            for j in range(int(y0 // cell), int(y1 // cell) + 1):
                grid.setdefault((i, j), []).append(p)

    for p in placed:
        add(p)
    out = []
    minx, miny, maxx, maxy = region.bounds
    from shapely.prepared import prep
    grown = prep(region.buffer(cfg["w"][1] * 0.3))       # centres may sit a little outside the edge
    core = prep(region.buffer(-cfg["w"][1] * 0.6))       # bats well inside need no area check
    for _ in range(cfg["tries"]):
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        pt = Point(x, y)
        if not grown.contains(pt):
            continue
        b = little_bat(rng.uniform(*cfg["w"]), rng.gauss(0, 12), x, y)
        if not core.contains(pt) and b.intersection(region).area < cfg["inside"] * b.area:
            continue
        bb = b.buffer(cfg["gap"])
        x0, y0, x1, y1 = bb.bounds
        clash = False
        for i in range(int(x0 // cell), int(x1 // cell) + 1):
            for j in range(int(y0 // cell), int(y1 // cell) + 1):
                if any(q.intersects(bb) for q in grid.get((i, j), [])):
                    clash = True
                    break
            if clash:
                break
        if clash:
            continue
        out.append(b)
        add(b)
    return out, placed + out


def lines_of(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [list(geom.coords)]
    if isinstance(geom, MultiLineString) or hasattr(geom, "geoms"):
        return [l for g in geom.geoms for l in lines_of(g)]
    return []


def hatch(poly, spacing, ang):
    """Parallel fill lines across the polygon."""
    c = poly.centroid
    r = max(poly.bounds[2] - poly.bounds[0], poly.bounds[3] - poly.bounds[1])
    ls = []
    k = -r
    while k <= r:
        ls.append(LineString([(-r, k), (r, k)]))
        k += spacing
    g = affinity.rotate(MultiLineString(ls), ang, origin=(0, 0))
    g = affinity.translate(g, c.x, c.y)
    return [l for l in lines_of(g.intersection(poly.buffer(-spacing * 0.35))) if LineString(l).length > 0.4]


def bat_lines(bats, region, cfg, rng):
    out = []
    for b in bats:
        b = b.intersection(region)                 # clip at the big bat's edge, so the edge reads
        if b.is_empty or b.area < 0.5:
            continue
        polys = [b] if isinstance(b, Polygon) else [g for g in getattr(b, "geoms", []) if isinstance(g, Polygon)]
        for p in polys:
            out.append(list(p.exterior.coords))
            out += hatch(p, cfg["hatch"], rng.uniform(-35, 35))
    return out


def order(lines):
    res, cur, todo = [], (PW["x0"], PW["y1"]), list(lines)
    while todo:
        i = min(range(len(todo)), key=lambda j: min(math.dist(todo[j][0], cur), math.dist(todo[j][-1], cur)))
        l = todo.pop(i)
        if math.dist(l[-1], cur) < math.dist(l[0], cur):
            l = l[::-1]
        res.append(l)
        cur = l[-1]
    return res


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


def gcode(lines, cfg):
    dz = cfg["dz"]
    z_down, z_up = CARD_Z - PENCIL_DOWN + OZ + dz, CARD_Z + PEN_UP + OZ + dz
    g = [f"; BAT SWARM - {cfg['name']} bats ({'thick' if cfg['name'] == 'big' else 'thin'}-tip pencil), {len(lines)} lines",
         f"; offsets: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}  (+ pencil dz {dz:+.1f})",
         "; Homes WITH the pencil on, then lifts clear of the frame straight away. No pause.",
         "M104 S0", "M140 S0", "M107", "G21", "G90",
         "G28 ; home with the pencil attached",
         f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; straight back up, clear of the frame"]
    for k, l in enumerate(lines):
        x0, y0 = m(*l[0])
        g += [f"G0 X{x0:.2f} Y{y0:.2f} F{TRAVEL_F}"]
        if k == 0:
            g.append(f"G1 Z{z_up:.2f} F600")
        g.append(f"G1 Z{z_down:.2f} F600")
        g += [f"G1 X{m(x, y)[0]:.2f} Y{m(x, y)[1]:.2f} F{DRAW_F}" for x, y in l[1:]]
        g.append(f"G1 Z{z_up:.2f} F600")
    g += [f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600", f"G0 X{BED[0]:.2f} Y{BED[1]:.2f} F{TRAVEL_F} ; park top-right",
          "M400", "M84 X Y ; X/Y motors off (Z stays on)", f"M117 {cfg['name']} bats done"]
    return "\n".join(g) + "\n"


rng = random.Random(SEED)
outline = big_bat()
for x, y in outline.exterior.coords:
    if not (PW["x0"] + 2 <= x <= PW["x1"] - 2 and PW["y0"] + 2 <= y <= PW["y1"] - 2):
        sys.exit(f"bat leaves the paint window at X{x:.1f} Y{y:.1f}: lower SPAN")
big, taken = place(outline, BIG, [], rng)
small, _ = place(outline, SMALL, taken, rng)
L_big = order(bat_lines(big, outline, BIG, rng))
L_small = order(bat_lines(small, outline, SMALL, rng) + [list(outline.exterior.coords)])  # fine outline too
open(os.path.join(HERE, "bats_big.gcode"), "w").write(gcode(L_big, BIG))
open(os.path.join(HERE, "bats_small.gcode"), "w").write(gcode(L_small, SMALL))
print(f"big bats: {len(big)} ({len(L_big)} lines)   small bats: {len(small)} ({len(L_small)} lines)")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(18, 5.2))
    for ax, (title, layers) in zip(axs, [("1. thick pencil: big bats", [(L_big, "#111", 0.9)]),
                                          ("2. thin pencil: small bats", [(L_small, "#444", 0.35)]),
                                          ("both layers on the card", [(L_big, "#111", 0.9), (L_small, "#333", 0.35)])]):
        ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                                   fill=False, ec="#bbb", ls="--"))
        for L, col, lw in layers:
            for l in L:
                a, b = zip(*l)
                ax.plot(a, b, color=col, lw=lw)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title)
    plt.savefig(os.path.join(HERE, "bats_preview.png"), dpi=150, bbox_inches="tight")
    print("wrote bats_preview.png")
except ImportError:
    pass
