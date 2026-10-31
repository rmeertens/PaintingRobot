#!/usr/bin/env python3
"""Turn an SVG drawing into single-line pencil paths for the plotter.

Two modes:
  outline   - for coloured/filled art: trace the silhouette plus the boundaries between dark,
              light and coloured areas (each boundary drawn once).
  centre    - for line art drawn with thick strokes: reduce every stroke to its centre line,
              so the pencil draws each line once instead of both edges.

Output: JSON with a list of polylines in mm (y up, origin bottom-left of the drawing),
scaled so the drawing is HEIGHT_MM tall.

Usage: python3 svg2plot.py drawing.svg outline|centre out.json [height_mm]
"""
import json
import sys

import cairosvg
import cv2
import numpy as np
from skimage.morphology import skeletonize

SRC, MODE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HEIGHT_MM = float(sys.argv[4]) if len(sys.argv) > 4 else 40.0
RES = 1400                     # raster height used for tracing (px)
SIMPLIFY_MM = 0.07             # drop detail smaller than this
MIN_LEN_MM = 1.2               # drop lines shorter than this


def render(path):
    png = cairosvg.svg2png(url=path, output_height=RES)
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    if img.shape[2] == 3:
        img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
    return img                  # BGRA


def contours_of(mask, smooth=3):
    smooth = smooth if mask.sum() > RES * RES * 0.002 else 1        # keep small spots (eyes) round
    m = mask.astype(np.uint8) * 255
    if smooth:
        m = cv2.GaussianBlur(m, (0, 0), smooth)
        m = (m > 127).astype(np.uint8) * 255
    cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    return [c[:, 0, :].astype(float) for c in cs]


def outline_mode(img):
    a = img[:, :, 3] > 40
    bgr = img[:, :, :3].astype(float)
    lum = (0.114 * bgr[:, :, 0] + 0.587 * bgr[:, :, 1] + 0.299 * bgr[:, :, 2])
    lum = cv2.GaussianBlur(lum, (0, 0), 4)            # blur away paint texture before splitting
    b, g, r = [cv2.GaussianBlur(bgr[:, :, i], (0, 0), 4) for i in range(3)]
    dark = a & (lum < 105)
    orange = a & (r > 150) & (r - b > 70) & (r - g > 25)
    lines = []
    sil = contours_of(a, smooth=2)                      # silhouette
    lines += sil
    # distance to the silhouette edge, so inner boundaries that run along it aren't drawn twice
    edge = np.full(a.shape, 255, np.uint8)
    for c in sil:
        cv2.polylines(edge, [c.astype(np.int32)], True, 0, 1)
    dist = cv2.distanceTransform(edge, cv2.DIST_L2, 3)
    inner = []
    for mask in (dark, orange):
        # keep only blobs of a reasonable size, then trace their edges
        n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
        keep = np.zeros_like(mask)
        ys_a = np.nonzero(a)[0]
        head_line = ys_a.min() + 0.28 * (ys_a.max() - ys_a.min())    # top 28% of the bird = the head
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            cy = stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2
            if area > RES * RES * 0.0025 or (area > RES * RES * 0.00006 and cy < head_line):
                keep |= lab == i                                       # big areas, plus eye-sized spots on the head
        inner += contours_of(keep, smooth=3)
    for c in inner:                                     # keep only the parts away from the silhouette
        c = np.vstack([c, c[:1]])
        far = dist[c[:, 1].astype(int).clip(0, a.shape[0] - 1), c[:, 0].astype(int).clip(0, a.shape[1] - 1)] > 4
        run = []
        for pt, ok in zip(c, far):
            if ok:
                run.append(pt)
            elif run:
                lines.append(np.array(run)); run = []
        if run:
            lines.append(np.array(run))
    return lines


def centre_mode(img):
    a = img[:, :, 3] > 40
    lum = img[:, :, :3].mean(axis=2)
    ink = a & (lum < 128)
    ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    sk = skeletonize(ink)
    # walk the 1-px skeleton into polylines, breaking at junctions
    ys, xs = np.nonzero(sk)
    pix = set(zip(ys.tolist(), xs.tolist()))
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def neigh(p):
        return [(p[0] + dy, p[1] + dx) for dy, dx in nb if (p[0] + dy, p[1] + dx) in pix]

    deg = {p: len(neigh(p)) for p in pix}
    seen_edges = set()
    lines = []
    starts = [p for p in pix if deg[p] != 2] + list(pix)
    for s in starts:
        for n in neigh(s):
            e = frozenset((s, n))
            if e in seen_edges:
                continue
            path = [s, n]
            seen_edges.add(e)
            prev, cur = s, n
            while deg[cur] == 2:
                nxt = [q for q in neigh(cur) if q != prev]
                if not nxt:
                    break
                e = frozenset((cur, nxt[0]))
                if e in seen_edges:
                    break
                seen_edges.add(e)
                prev, cur = cur, nxt[0]
                path.append(cur)
            lines.append(np.array([(x, y) for y, x in path], float))
    return lines


def simplify(pl, eps):
    if len(pl) < 3:
        return pl
    c = cv2.approxPolyDP(pl.astype(np.float32).reshape(-1, 1, 2), eps, False)
    return c[:, 0, :].astype(float)


img = render(SRC)
raw = outline_mode(img) if MODE == "outline" else centre_mode(img)
h_px = img.shape[0]
ys = np.nonzero(img[:, :, 3] > 40)[0]
top, bot = ys.min(), ys.max()
scale = HEIGHT_MM / (bot - top)
out = []
for pl in raw:
    pl = simplify(pl, SIMPLIFY_MM / scale)
    mm = [(float(x * scale), float((bot - y) * scale)) for x, y in pl]
    length = sum(np.hypot(mm[i + 1][0] - mm[i][0], mm[i + 1][1] - mm[i][1]) for i in range(len(mm) - 1))
    if length >= MIN_LEN_MM:
        out.append(mm)
xs = [p[0] for pl in out for p in pl]
x0 = min(xs)
out = [[(x - x0, y) for x, y in pl] for pl in out]
json.dump({"source": SRC, "mode": MODE, "height_mm": HEIGHT_MM, "lines": out}, open(OUT, "w"))
total = sum(sum(np.hypot(pl[i + 1][0] - pl[i][0], pl[i + 1][1] - pl[i][1]) for i in range(len(pl) - 1)) for pl in out)
print(f"{OUT}: {len(out)} lines, {total / 1000:.2f} m of pencil, {max(xs) - x0:.0f} x {HEIGHT_MM:.0f} mm")
