import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyBboxPatch

INK, FIX, MOV, PEN, SPR, MET, NOTE = "#222", "#c9d3df", "#f2c27b", "#8db4e0", "#d0453c", "#7a7a7a", "#555"

def R(a, x, y, w, h, fc, hatch=None, lw=1.2, z=1):
    a.add_patch(Rectangle((x, y), w, h, fc=fc, ec=INK, lw=lw, hatch=hatch, zorder=z))

def spring(a, x, y0, y1, w, n=10, lw=2):
    ys = [y0 + (y1 - y0) * i / (2 * n) for i in range(2 * n + 1)]
    xs = [x + (w / 2 if i % 2 else -w / 2) if 0 < i < 2 * n else x for i in range(2 * n + 1)]
    a.plot(xs, ys, color=SPR, lw=lw, zorder=6, solid_capstyle="round")

def pen(a, x, tip_y, top_y, d=10, z=3):
    a.add_patch(Polygon([(x - d / 2, tip_y + 12), (x - d / 2, top_y), (x + d / 2, top_y), (x + d / 2, tip_y + 12), (x, tip_y)], fc=PEN, ec=INK, lw=1, zorder=z, alpha=0.95))

def card(a, y=0):
    a.plot([-40, 40], [y, y], color="#999", lw=1, ls="--", zorder=0)
    a.text(39, y - 4, "card", fontsize=7, color=NOTE, ha="right")

def lab(a, txt, xy, xyt, col=INK):
    a.annotate(txt, xy=xy, xytext=xyt, fontsize=8, color=col, arrowprops=dict(arrowstyle="-", color=col, lw=0.7), zorder=10)

def lift_arrow(a, x, y):
    a.annotate("", xy=(x, y + 7), xytext=(x, y), arrowprops=dict(arrowstyle="<->", color=SPR, lw=1.6), zorder=11)

def frame(a, title, sub):
    a.set_xlim(-42, 42); a.set_ylim(-8, 110); a.set_aspect("equal"); a.axis("off")
    a.set_title(title, fontsize=12, weight="bold", loc="left")
    a.text(-42, 104, sub, fontsize=8.5, color=NOTE, va="top")

fig = plt.figure(figsize=(18, 11.5))
axs = [fig.add_axes([0.01 + 0.25 * i, 0.27, 0.235, 0.66]) for i in range(4)]
txt = [fig.add_axes([0.015 + 0.25 * i, 0.01, 0.23, 0.25]) for i in range(4)]
for t in txt: t.axis("off")

# ============ 1. spring around the pen ============
a = axs[0]; frame(a, "1  Spring around the pen", "cut through the pen axis")
card(a); xc = -4
R(a, -30, 10, 4, 75, FIX)
R(a, -26, 20, 6, 52, FIX)                                        # bracket from the cartridge
R(a, xc - 10.2, 20, 3, 24, FIX); R(a, xc + 7.2, 20, 3, 24, FIX)  # guide tube walls (fixed)
R(a, -26, 20, 26 + xc - 10.2, 4, FIX)                            # guide tube joined to bracket
R(a, xc - 13, 66, 26, 5, FIX, "///"); R(a, -26, 66, 26 + xc - 13, 5, FIX)   # cap (screwed to bracket)
pen(a, xc, 2, 105)
R(a, xc - 7, 14, 2, 30, MOV); R(a, xc + 5, 14, 2, 30, MOV)      # carrier hex walls (slide in the tube)
R(a, xc - 10, 44, 5, 7, MOV); R(a, xc + 5, 44, 5, 7, MOV)       # collar
spring(a, xc - 8, 51, 66, 3.2, 6); spring(a, xc + 8, 51, 66, 3.2, 6)
R(a, xc + 10, 46, 5, 2.5, MET)                                   # set screw
lab(a, "big soft spring around the pen\n(Ø18 × ~25 mm)", (xc + 8, 58), (12, 80), SPR)
lab(a, "screw-on cap", (xc + 12, 69), (14, 92))
lab(a, "carrier + collar\n(slides, clamps the pen)", (xc + 9, 48), (14, 54))
lab(a, "guide tube", (xc + 10, 30), (16, 30))
lab(a, "cartridge", (-28, 80), (-41, 96))
lift_arrow(a, xc, -6)

# ============ 2. tiny spring beside the pen (sliding block on a rail) ============
a = axs[1]; frame(a, "2  Sliding block + tiny side spring", "front view")
card(a); R(a, -30, 10, 4, 75, FIX)
R(a, -26, 18, 8, 60, FIX, "\\\\\\")                     # dovetail rail
R(a, -18, 30, 26, 28, MOV)                              # pen block
R(a, -18, 58, 10, 4, MOV)                               # ear
pen(a, -2, 2, 105)
R(a, -6, 34, 8, 20, MOV); R(a, -2, 42, 10, 3, MET)
R(a, -26, 72, 18, 6, FIX, "///")                        # fixed tab
spring(a, -13, 62, 72, 3, 7, 1.6)
R(a, -26, 22, 18, 5, FIX, "///")                        # down stop
lab(a, "tiny spring\n(ballpoint click spring)", (-13, 67), (6, 82), SPR)
lab(a, "fixed tab", (-17, 77), (-20, 96))
lab(a, "pen block slides\non a printed rail", (-10, 40), (10, 30))
lab(a, "rail on the cartridge", (-22, 50), (-40, 4))
lab(a, "down-stop", (-12, 24), (8, 14))
lift_arrow(a, -2, -6)

# ============ 3. twin steel rods ============
a = axs[2]; frame(a, "3  Twin rods + tiny springs", "front view")
card(a); R(a, -30, 10, 4, 75, FIX)
R(a, -26, 70, 50, 6, FIX); R(a, -26, 16, 50, 6, FIX)    # top and bottom rod holders
for x in (-18, 14):
    R(a, x - 1.5, 22, 3, 48, MET)                       # rods
R(a, -24, 30, 44, 14, MOV)                              # sliding block
for x in (-18, 14):
    spring(a, x, 44, 70, 5.5, 9, 1.6)
pen(a, -2, 2, 105, z=4)
R(a, -2, 44, 6, 3, MET)
lab(a, "2 × Ø3 mm steel rods\n(drill blanks / pins)", (14, 26), (16, 6))
lab(a, "tiny springs over the rods", (14, 58), (10, 92), SPR)
lab(a, "pen block slides on the rods\n(rest: sits on the bottom holder)", (-20, 37), (-42, 96))
lift_arrow(a, -2, -6)

# ============ 4. printed flexure ============
a = axs[3]; frame(a, "4  Printed flexure (no spring)", "front view")
card(a); R(a, -30, 10, 4, 75, FIX)
R(a, -26, 24, 8, 50, FIX)                               # fixed post
R(a, -18, 66, 30, 0.8, MOV); R(a, -18, 30, 30, 0.8, MOV)  # thin blades
R(a, 12, 26, 12, 46, MOV)                               # pen block
pen(a, 18, 2, 105, z=4)
R(a, 21, 44, 5, 3, MET)
a.plot([-18, 12], [66.4, 69.5], color=MOV, lw=1, ls=":"); a.plot([-18, 12], [30.4, 33.5], color=MOV, lw=1, ls=":")
lab(a, "2 thin PETG blades (0.6 × 10 × 30)\nbend like a parallelogram:\nthey ARE the spring", (-2, 66.4), (-40, 92), SPR)
lab(a, "fixed post on the cartridge", (-22, 50), (-41, 10))
lab(a, "pen block\n(printed in one piece\nwith blades and post)", (18, 30), (4, 14))
lab(a, "lifted position (dotted)", (6, 69), (-10, 80), NOTE)
lift_arrow(a, 18, -6)

T = [
 ("Simplest direct push", "+ one moving part, one spring, easy to print\n+ spring force straight down the pen\n− needs a bigger spring (Ø18 mm, ~25 mm)\n− sliding fit: can wobble or stick, more so at 30°\n\nParts: cartridge, carrier, cap\nHardware: 1 spring, 1 M3 set screw + nut, 2 M3 × 12"),
 ("Direct push, tiny spring", "+ ballpoint-pen spring\n+ rail is long, so less wobble than a tube\n+ adjustable force (swap spring)\n− spring travel = pen travel (fine: 5–8 mm)\n− printed rail needs a good fit (test print)\n\nParts: cartridge + rail, pen block\nHardware: 1 tiny spring, 1 M3 × 8"),
 ("Smoothest sliding  ★", "+ steel rods: very low friction, no wobble\n+ two tiny springs, force splits evenly\n+ classic pen-plotter design\n− needs 2 × Ø3 mm rods (~45 mm)\n− 4 rod holes must line up (print the holder in one piece)\n\nParts: cartridge with rod holders, pen block\nHardware: 2 rods, 2 tiny springs, 1 M3 × 8"),
 ("No hardware, no friction  ★", "+ nothing slides, nothing to stick or wobble\n+ one printed part, no spring to buy\n+ force set by blade thickness (~1 N at 3 mm)\n− only ~4 mm of travel\n− PETG blades can slowly creep; reprint if weak\n\nParts: cartridge + flexure (one piece)\nHardware: 1 M3 × 8"),
]
for t, (h, b) in zip(txt, T):
    t.text(0, 1, h, fontsize=11, weight="bold", va="top")
    t.text(0, 0.86, b, fontsize=9.3, va="top", linespacing=1.5, family="DejaVu Sans")

fig.suptitle("Spring pen holder – 4 options  (all shown with the pen vertical for clarity; each can be mounted at 30° like now)",
             fontsize=14, weight="bold", x=0.01, ha="left", y=0.985)
fig.text(0.01, 0.945, "Grey = fixed to the cartridge (which snaps onto the brush dock), orange = moves with the pen, blue = pen, red = spring / force, dark grey = metal.  "
         "Red arrow = how the pen gives way when it touches the card. Rough scale: grid-free, sizes in mm.", fontsize=9, color=NOTE)
fig.savefig("spring_pen_options.png", dpi=110)
