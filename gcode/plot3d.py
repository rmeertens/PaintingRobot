#!/usr/bin/env python3
"""3D view of a G-code file's brush path. Usage: python3 plot3d.py tree_brush.gcode"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d.art3d import Line3DCollection

path = sys.argv[1] if len(sys.argv) > 1 else "tree_brush.gcode"
PAPER_Z = 6.1                     # printer Z where the brush touches the paper (calibration)
x = y = z = None
paint, travel = [], []
started = False
for line in open(path):
    code = line.split(";")[0].split()
    if not code or code[0] not in ("G0", "G1"):
        if line.startswith("@pause"):
            started = True
        continue
    nx, ny, nz = x, y, z
    for w in code[1:]:
        if w[0] == "X": nx = float(w[1:])
        if w[0] == "Y": ny = float(w[1:])
        if w[0] == "Z": nz = float(w[1:])
    if started and None not in (x, y, z, nx, ny, nz):
        seg = ((x, y, z), (nx, ny, nz))
        (paint if code[0] == "G1" and (x, y) != (nx, ny) else travel).append(seg)
    x, y, z = nx, ny, nz

fig = plt.figure(figsize=(15, 7))
for k, (elev, azim, title) in enumerate([(28, -60, "Overview"), (8, -88, "Low side view (Z exaggerated)")]):
    ax = fig.add_subplot(1, 2, k + 1, projection="3d")
    zs = [(a[2] + b[2]) / 2 for a, b in paint]
    norm = plt.Normalize(min(zs), max(zs))
    lc = Line3DCollection(paint, colors=cm.viridis_r(norm(zs)), linewidths=1.6)
    ax.add_collection3d(lc)
    ax.add_collection3d(Line3DCollection([s for s in travel if max(s[0][2], s[1][2]) < 30],
                                         colors="#bbbbbb", linewidths=0.4))
    xs = [p[0] for s in paint for p in s]
    ys = [p[1] for s in paint for p in s]
    X0, X1, Y0, Y1 = min(xs) - 5, max(xs) + 5, min(ys) - 5, max(ys) + 5
    import numpy as np
    gx, gy = np.meshgrid([X0, X1], [Y0, Y1])
    ax.plot_surface(gx, gy, np.full_like(gx, PAPER_Z), color="#f3e9d2", alpha=0.35)
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_zlim(PAPER_Z - 2, PAPER_Z + 21)
    ax.set_box_aspect((X1 - X0, Y1 - Y0, 45))
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("printer X"); ax.set_ylabel("printer Y"); ax.set_zlabel("Z")
    ax.set_title(title)
    if k == 0:
        m = cm.ScalarMappable(norm=norm, cmap="viridis_r")
        cb = fig.colorbar(m, ax=ax, shrink=0.5, pad=0.08)
        cb.set_label("brush tip Z (paper = %.1f)" % PAPER_Z)
fig.suptitle(f"{os.path.basename(path)}: brush strokes (yellow = pressed into the paper, purple = lifted off), "
             "grey = moves between strokes. Z is stretched ~4x.", fontsize=11)
out = os.path.splitext(path)[0] + "_3d.png"
plt.savefig(out, dpi=130, bbox_inches="tight")
print("wrote", out, len(paint), "paint segments", len(travel), "travel segments")
