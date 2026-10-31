# A4 sheet with 4 palette stickers (205 x 43.5 mm) for the Palette module. Print at 100 % (no scaling).
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
MM = 1 / 25.4
SX0, SY0, SW, SH = 15.0, 4.5, 205.0, 43.5          # sticker position in fixture coords
CELL_X0, CELL_X1, WALL, N = 17.0, 218.0, 3.0, 6
CW = (CELL_X1 - CELL_X0 - (N - 1) * WALL) / N
CELL_Y, LANE_Y, BAR_Y = (7.0, 32.0), (38.0, 46.0), 35.0
fig = plt.figure(figsize=(210 * MM, 297 * MM))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 210); ax.set_ylim(0, 297); ax.axis("off")
ax.text(105, 288, "Palette stickers – print at 100 % (actual size) on full-sheet label paper or palette paper", ha="center", fontsize=8)
ax.text(105, 283, "Cut on the dashed lines. Front edge (towards the front of the printer) at the bottom of each strip. Check: the strip is 205 mm wide.", ha="center", fontsize=6.5, color="#555")
for k in range(4):
    ox, oy = 2.5, 222 - k * 58                      # sticker lower-left on the page
    X = lambda x: ox + (x - SX0); Y = lambda y: oy + (y - SY0)
    ax.add_patch(Rectangle((ox, oy), SW, SH, fill=False, ls=(0, (4, 3)), lw=0.6, ec="#444"))
    for i in range(N):
        x0 = CELL_X0 + i * (CW + WALL)
        ax.add_patch(FancyBboxPatch((X(x0) + 1, Y(CELL_Y[0]) + 1), CW - 2, CELL_Y[1] - CELL_Y[0] - 2, boxstyle="round,pad=0,rounding_size=2", fill=False, lw=0.4, ec="#bbb"))
        cx, cy = X(x0 + CW / 2), Y((CELL_Y[0] + CELL_Y[1]) / 2)
        ax.add_patch(Circle((cx, cy), 7, fill=False, lw=0.5, ec="#999", ls=":"))
        ax.text(cx, cy, str(i + 1), ha="center", va="center", fontsize=9, color="#888")
        ax.text(cx, Y(CELL_Y[0]) + 2.2, "colour ______", ha="center", fontsize=4.5, color="#aaa")
    ax.add_patch(Rectangle((X(CELL_X0) + 1, Y(LANE_Y[0]) + 0.8), CELL_X1 - CELL_X0 - 2, LANE_Y[1] - LANE_Y[0] - 1.6, fill=False, hatch="////", lw=0.3, ec="#ccc"))
    ax.text(X((CELL_X0 + CELL_X1) / 2), Y((LANE_Y[0] + LANE_Y[1]) / 2), "DISCARD / WIPE LANE", ha="center", va="center", fontsize=6, color="#888",
            bbox=dict(fc="white", ec="none", pad=0.6))
    ax.plot([X(CELL_X0), X(CELL_X1)], [Y(BAR_Y)] * 2, color="#ccc", lw=0.6)
    ax.text(X(CELL_X1) - 1, Y(BAR_Y) + 0.6, "wipe bar", ha="right", fontsize=4, color="#aaa")
    ax.text(ox + 1, oy + 1, "FRONT ↓", fontsize=4.5, color="#999")
    ax.plot([ox + SW / 2 - 6, ox + SW / 2 + 6], [oy, oy], color="#e88", lw=1.2)   # peel notch marker
ax.text(105, 8, "Strip: 205 × 43.5 mm. The red mark on the front edge sits over the peel notch.", ha="center", fontsize=6, color="#555")
ax.add_patch(Rectangle((10, 12), 50, 0.01, ec="k", lw=0.5)); ax.text(35, 13.5, "50 mm (check your print)", ha="center", fontsize=5)
fig.savefig("palette_stickers_A4.pdf"); fig.savefig("palette_stickers_A4.png", dpi=120)
