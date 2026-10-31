#!/usr/bin/env python3
"""Draw the painting plan for tree_brush.py: stroke order on the card + the brush height profile."""
import io, os, contextlib, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

HERE = os.path.dirname(os.path.abspath(__file__))
with contextlib.redirect_stdout(io.StringIO()):
    import tree_brush as T

order = T.ROW_ORDER
skipped = {r for k, r in enumerate(order) if k > 0 and r < order[k - 1]}

fig, (ax, az) = plt.subplots(1, 2, figsize=(15, 6.2), gridspec_kw={"width_ratios": [1.5, 1]})
PW = T.PW
ax.add_patch(plt.Rectangle((PW["x0"], PW["y0"]), PW["x1"] - PW["x0"], PW["y1"] - PW["y0"],
                           fill=False, ec="#aaa", ls="--"))
ox, oy = zip(*T.outline())
ax.plot(ox, oy, color="#e0902a", lw=1, ls=":")
cmap = plt.cm.viridis
n = len(T.S)
for k, pts in enumerate(T.S):
    L = T.stroke_len(pts)
    segs = [[pts[i], pts[i + 1]] for i in range(len(pts) - 1)]
    m = len(segs)
    w = [0.5 + 4.5 * max(0, 1 - (T.PRESS + T.LIFT) * T.lift_frac(i / m, L) / (T.PRESS + 4)) ** 1.5
         for i in range(m)]
    ax.add_collection(LineCollection(segs, linewidths=w, colors=[cmap(k / (n - 1))] * m, capstyle="round"))
# label rows in paint order along the spine
k = 0
for step, r in enumerate(order):
    pts = T.S[k]
    x = pts[0][0]
    late = r in skipped
    ax.annotate(str(step + 1), (x, T.CY), xytext=(x, T.CY + (-9 if step % 2 else 9) - (0 if not late else 0)),
                ha="center", va="center", fontsize=6.5,
                color="#c41f30" if late else "#222", weight="bold" if late else "normal",
                arrowprops=dict(arrowstyle="-", lw=0.4, color="#999"))
    k += 2 if k + 1 < n and abs(T.S[k + 1][0][0] - x) < 0.01 else 1
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(1, n))
cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.01)
cb.set_label("stroke number (paint order)")
ax.set_aspect("equal"); ax.axis("off")
ax.set_title(f"Paint order: {len(order)} rows, {n} strokes, tip → base.  "
             f"Red numbers = skipped rows, painted two rows later ({len(skipped)})", fontsize=9)

for Ls, c in ((60, "#1d6b3c"), (40, "#3c8f5a"), (20, "#7cbf8e"), (8, "#b9dcc2")):
    ts = [i / 200 for i in range(201)]
    az.plot([t * Ls for t in ts], [-T.PRESS + (T.PRESS + T.LIFT) * T.lift_frac(t, Ls) for t in ts],
            color=c, lw=1.6, label=f"{Ls} mm stroke")
az.axhline(0, color="k", lw=0.8); az.text(1, 0.25, "paper", fontsize=7)
az.axvline(T.HOLD_MM, color="#999", ls=":", lw=0.8)
az.text(T.HOLD_MM + 0.5, T.LIFT - 0.5, f"lift starts\n({T.HOLD_MM:g} mm)", fontsize=7, color="#666")
az.set_xlabel("distance from the centre line (mm)"); az.set_ylabel("brush tip above paper (mm)")
az.set_title(f"Brush height: {T.PRESS:g} mm pressed, lift to {T.LIFT:g} mm over {T.ATTACK_MM:g} mm\n"
             "(short strokes near the tip get the same curve shrunk)", fontsize=9)
az.legend(fontsize=8, loc="lower right"); az.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(HERE, "tree_plan.png"), dpi=150, bbox_inches="tight")
print("wrote tree_plan.png")
