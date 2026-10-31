#!/usr/bin/env python3
"""Delicate pencil line art: a puffin above and a puffin below the "Gemmie is a puffin" text.

Writes puffins.gcode (homes first, pause to attach the pencil) and puffins_nohome.gcode (for a
printer that is already homed with the pencil on, e.g. right after the text), plus a preview that
also shows the text so you can judge the layout.
Run:   python3 puffins.py      then   python3 octo.py send puffins.gcode
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OFF = CAL.get("pencil_offset") or CAL["offset"]
OX, OY, OZ = OFF["x"], OFF["y"], OFF["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]
PENCIL_DOWN, PEN_UP, APPROACH = 1.0, 3.0, 20.0     # same as pencil_text.py
DRAW_F, TRAVEL_F = 1200, 4000
BED = (220.0, 220.0)
CX = (PW["x0"] + PW["x1"]) / 2
TEXT_Y = (PW["y0"] + PW["y1"]) / 2                  # the text is centred here, about 23 mm tall


# ---------------------------------------------------------------- drawing helpers
def bez(*p, n=None):
    """Cubic (4 points) or quadratic (3 points) Bezier, sampled about every 0.6 mm."""
    length = sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))
    n = n or max(4, int(length / 0.6))
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        if len(p) == 4:
            c = (u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3)
        else:
            c = (u * u, 2 * u * t, t * t)
        out.append((sum(ci * q[0] for ci, q in zip(c, p)), sum(ci * q[1] for ci, q in zip(c, p))))
    return out


def chain(*segs):
    out = []
    for s in segs:
        out += s if not out else s[1:]
    return out


def circle(c, r, n=24):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def place(strokes, x, y, s=1.0, flip=False):
    return [[(x + (-px if flip else px) * s, y + py * s) for px, py in st] for st in strokes]


# ---------------------------------------------------------------- the puffin (local mm, feet at y=0, facing right)
def puffin_standing():
    S = []
    # head + back + tail: crown over the nape, down the back to the tail tip
    S.append(chain(bez((10.5, 33.5), (8.5, 38.5), (2.0, 39.5), (-2.5, 35.5)),
                   bez((-2.5, 35.5), (-6.5, 31.5), (-8.0, 25.0), (-10.5, 18.0)),
                   bez((-10.5, 18.0), (-12.5, 12.5), (-15.0, 9.0), (-17.0, 6.5))))
    # beak: big triangular bill with two stripes
    S.append(chain(bez((10.5, 33.5), (14.5, 33.0), (18.5, 30.5), (20.5, 28.0)),
                   bez((20.5, 28.0), (17.0, 26.5), (13.5, 26.0), (10.5, 25.8))))
    S.append(bez((13.0, 32.6), (12.6, 29.5), (12.8, 27.5), (13.2, 26.1)))
    S.append(bez((15.6, 31.6), (15.2, 29.5), (15.3, 28.0), (15.8, 26.5)))
    S.append([(10.5, 29.6), (20.0, 28.2)])                                   # mouth line
    # throat, chest and belly, round to the tail underside
    S.append(chain(bez((10.5, 25.8), (9.0, 22.5), (10.0, 18.0), (9.6, 13.0)),
                   bez((9.6, 13.0), (9.0, 7.5), (5.5, 3.8), (0.5, 3.6)),
                   bez((0.5, 3.6), (-5.5, 3.4), (-11.5, 4.8), (-17.0, 6.5))))
    # white face patch edge (cheek) and the dark collar
    S.append(bez((0.8, 37.8), (-2.5, 32.0), (-1.0, 26.5), (5.0, 23.8)))
    S.append(bez((5.0, 23.8), (7.5, 23.0), (9.0, 24.0), (10.2, 25.6)))
    # eye with the little grey eye-mark above and the line behind it
    S.append(circle((6.2, 32.2), 1.05, 16))
    S.append([(5.2, 33.9), (6.4, 35.2), (7.4, 34.0)])
    S.append(bez((5.1, 31.8), (3.5, 31.2), (2.2, 30.4), (1.0, 29.2)))
    # folded wing
    S.append(chain(bez((-3.2, 27.5), (-1.0, 21.0), (-3.0, 13.5), (-8.5, 8.8)),
                   bez((-8.5, 8.8), (-11.5, 7.6), (-14.0, 7.2), (-16.0, 6.9))))
    # delicate hatching on the dark back, between the back line and the wing
    for k in range(5):
        t = 0.18 + k * 0.15
        a = (-4.6 - 6.0 * t, 31.0 - 22.0 * t)
        S.append(bez(a, (a[0] + 1.6, a[1] - 1.8), (a[0] + 2.4, a[1] - 3.8)))
    # legs and webbed orange feet
    for lx in (-1.5, 2.5):
        S.append([(lx, 3.8), (lx - 0.4, 0.0)])
        S.append([(lx - 1.6, 0.0), (lx - 0.4, 0.0), (lx + 4.2, -0.3), (lx + 3.0, 1.0), (lx - 0.4, 0.0)])
    return S


def puffin_swimming():
    """Floating on the water: same head and bill, body low and long, waterline under it."""
    S = []
    S.append(chain(bez((10.5, 21.5), (8.5, 26.5), (2.0, 27.5), (-2.5, 23.5)),
                   bez((-2.5, 23.5), (-7.5, 18.5), (-14.0, 15.0), (-22.0, 12.5)),
                   bez((-22.0, 12.5), (-24.5, 11.8), (-26.0, 11.2), (-27.5, 11.0))))
    S.append(chain(bez((10.5, 21.5), (14.5, 21.0), (18.5, 18.5), (20.5, 16.0)),
                   bez((20.5, 16.0), (17.0, 14.5), (13.5, 14.0), (10.5, 13.8))))
    S.append(bez((13.0, 20.6), (12.6, 17.5), (12.8, 15.5), (13.2, 14.1)))
    S.append(bez((15.6, 19.6), (15.2, 17.5), (15.3, 16.0), (15.8, 14.5)))
    S.append([(10.5, 17.6), (20.0, 16.2)])
    S.append(chain(bez((10.5, 13.8), (9.5, 10.5), (9.0, 7.0), (6.5, 5.0)),
                   bez((6.5, 5.0), (-3.0, 4.6), (-15.0, 6.0), (-27.5, 11.0))))
    S.append(bez((0.8, 25.8), (-2.5, 20.0), (-1.0, 14.5), (5.0, 11.8)))
    S.append(bez((5.0, 11.8), (7.5, 11.0), (9.0, 12.0), (10.2, 13.6)))
    S.append(circle((6.2, 20.2), 1.05, 16))
    S.append([(5.2, 21.9), (6.4, 23.2), (7.4, 22.0)])
    S.append(bez((5.1, 19.8), (3.5, 19.2), (2.2, 18.4), (1.0, 17.2)))
    S.append(bez((-4.0, 15.5), (-9.0, 13.0), (-16.0, 10.5), (-24.0, 10.4)))      # wing along the side
    for k in range(5):
        x = -6.5 - k * 3.4
        S.append(bez((x, 17.5 - k * 1.0), (x - 1.0, 16.2 - k * 1.0), (x - 2.2, 15.4 - k * 1.0)))
    return S


def waves(x0, x1, y, amp=1.2, period=11.0, phase=0.0):
    n = int((x1 - x0) / 0.6)
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin(2 * math.pi * ((x1 - x0) * i / n) / period + phase))
            for i in range(n + 1)]


# ---------------------------------------------------------------- composition
def design():
    S = []
    # TOP: puffin standing on a clifftop, grass and two far-off birds
    top_y = TEXT_Y + 26                       # feet / clifftop height
    S += place(puffin_standing(), CX - 52, top_y, 1.0)
    cliff = chain(bez((CX - 95, top_y - 1.5), (CX - 80, top_y + 1.0), (CX - 65, top_y - 0.5), (CX - 48, top_y)),
                  bez((CX - 48, top_y), (CX - 35, top_y + 0.4), (CX - 25, top_y - 1.0), (CX - 12, top_y - 3.0)),
                  bez((CX - 12, top_y - 3.0), (CX - 8, top_y - 4.5), (CX - 6.5, top_y - 6.5), (CX - 7, top_y - 8.5)))
    S.append(cliff)
    for gx, h, lean in [(-88, 4.5, -1), (-84, 6.0, 1), (-79, 3.5, 0.5), (-70, 5.0, -0.5), (-66, 3.0, 1),
                        (-40, 4.0, 1), (-34, 5.5, -1), (-29, 3.0, 0.5), (-21, 4.5, 1)]:
        bx = CX + gx
        by = top_y + 0.3
        S.append(bez((bx, by), (bx + lean * 0.6, by + h * 0.6), (bx + lean * 1.8, by + h)))
    S.append(waves(CX + 10, CX + 98, top_y - 6, amp=0.8, period=14))        # distant sea line
    for bx, by, s in [(CX + 40, top_y + 30, 1.0), (CX + 58, top_y + 36, 0.7)]:   # far-off birds
        S.append(chain(bez((bx - 4 * s, by + 1.5 * s), (bx - 2 * s, by + 2 * s), (bx - 0.6 * s, by + 0.8 * s), (bx, by)),
                       bez((bx, by), (bx + 0.6 * s, by + 0.8 * s), (bx + 2 * s, by + 2 * s), (bx + 4 * s, by + 1.5 * s))))
    # BOTTOM: puffin floating on gentle waves, facing the other way
    bot_y = TEXT_Y - 50                       # waterline
    S += place(puffin_swimming(), CX + 48, bot_y - 5, 1.0, flip=True)
    S.append(waves(PW["x0"] + 12, CX + 18, bot_y, amp=1.0, period=12))
    S.append(waves(CX + 80, PW["x1"] - 12, bot_y, amp=1.0, period=12, phase=1.0))
    S.append(waves(PW["x0"] + 30, PW["x1"] - 30, bot_y - 5, amp=0.8, period=15, phase=2.0))
    S.append(waves(PW["x0"] + 55, PW["x1"] - 55, bot_y - 9, amp=0.6, period=18, phase=0.5))
    return S


def text_strokes():
    """The already-written text, for the preview only (re-generated from pencil_text.py)."""
    try:
        sys.argv = ["pencil_text.py"]
        ns = {"__name__": "pencil_text_preview_only", "__file__": os.path.join(HERE, "pencil_text.py")}
        src = open(os.path.join(HERE, "pencil_text.py")).read()
        src = src.split("def m(x, y):")[0]           # stop before it writes any files
        exec(compile(src, "pencil_text.py", "exec"), ns)
        return ns["strokes"]
    except Exception as e:
        print("(preview without text:", e, ")")
        return []


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


S = design()
for st in S:
    for x, y in st:
        if not (PW["x0"] + 2 <= x <= PW["x1"] - 2 and PW["y0"] + 2 <= y <= PW["y1"] - 2):
            sys.exit(f"drawing leaves the paint window at X{x:.1f} Y{y:.1f}")

z_down = CARD_Z - PENCIL_DOWN + OZ
z_up = CARD_Z + PEN_UP + OZ


def gcode(no_home):
    g = [f"; PUFFINS: delicate pencil line art above and below the text, {len(S)} strokes",
         f"; offsets: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}"]
    if no_home:
        g += ["; NO HOMING: only for a printer that is already homed with the pencil attached",
              "M104 S0", "M140 S0", "M107", "G21", "G90",
              f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600 ; lift off the paper first"]
    else:
        g += ["; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.",
              "M104 S0", "M140 S0", "M107", "G21", "G90", "G28 ; home with the cartridge off",
              f"G1 Z{CARD_Z + 45 + OZ:.2f} F600", "M400", "M117 Attach pencil, then Resume",
              "@pause ; snap the pencil cartridge on, then press Resume",
              f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600"]
    for k, st in enumerate(S):
        x0, y0 = m(*st[0])
        g += [f"; stroke {k + 1}", f"G0 X{x0:.2f} Y{y0:.2f} F{TRAVEL_F}"]
        if k == 0:
            g.append(f"G1 Z{z_up:.2f} F600")
        g.append(f"G1 Z{z_down:.2f} F600")
        for x, y in st[1:]:
            px, py = m(x, y)
            g.append(f"G1 X{px:.2f} Y{py:.2f} F{DRAW_F}")
        g.append(f"G1 Z{z_up:.2f} F600")
    g += [f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600", f"G0 X{BED[0]:.2f} Y{BED[1]:.2f} F{TRAVEL_F} ; park top-right",
          "M400", "M84 X Y ; X/Y motors off (Z stays on)", "M117 Puffins done"]
    return "\n".join(g) + "\n"


open(os.path.join(HERE, "puffins.gcode"), "w").write(gcode(False))
open(os.path.join(HERE, "puffins_nohome.gcode"), "w").write(gcode(True))
print(f"wrote puffins.gcode and puffins_nohome.gcode: {len(S)} strokes")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                               fill=False, ec="#bbb", ls="--"))
    for st in text_strokes():
        a, b = zip(*st)
        ax.plot(a, b, color="#999", lw=0.9)
    for st in S:
        a, b = zip(*st)
        ax.plot(a, b, color="#333", lw=0.7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("puffins (dark) around the text already on the card (grey)", fontsize=9)
    plt.savefig(os.path.join(HERE, "puffins_preview.png"), dpi=170, bbox_inches="tight")
    print("wrote puffins_preview.png")
except ImportError:
    pass
