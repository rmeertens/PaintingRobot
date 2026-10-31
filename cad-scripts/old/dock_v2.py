"""Brush holder v2, fitted to the stock Ender 5 carriage (geometry from the Endorphin STEP 'legacy-x-assem').
Local frame: x along gantry (0 = stock nozzle x), y = 0 at the top of the hotend bosses, -y = away from carriage,
z up from the bottom edge of the carriage plate.
Model->local: x = mX - 3.64, y = 20.8 - mZ, z = mY - 205.9
"""
import glob, json
import manifold3d as m3, trimesh, numpy as np

P = dict(
    dock_x0=-41.0, dock_x1=22.0, dock_h=63.5, dock_t=6.0,
    hot_holes=[(-7.0, 39.0), (7.0, 39.0)],                 # stock heatsink M3 threads (on 4.5 mm bosses)
    shroud_holes=[(-35.38, 31.26), (-17.38, 49.26)],       # stock fan-shroud M3 threads (on the flat face)
    standoff_d=7.0, standoff_h=4.5,
    head_relief=[(-36.5, 51.5, 6.0), (3.5, 51.5, 6.0), (-16.1, 12.6, 6.5)],  # wheel bolt heads (x, z, r)
    relief_depth=2.0,
    screw_d=3.4, head_d=6.5, head_depth=3.0,
    cw=44.0, ledge_h=4.0, cart_h=54.0, cart_t=4.0,
    mag_d=10.2, mag_t=3.2, mags=[(-15, 12), (15, 12), (-15, 30), (15, 30)],
    cone_d=9.0, cone_h=4.5, cone_clear=0.3, cones=[(0, 12), (0, 50)],
    hex_af=16.0, hex_clear=0.5, sleeve_od=25.0, sleeve_h=40.0,
    plunger_len=62.0, collar_d=24.0, collar_h=12.0, tool_d=7.0, tool_clear=0.3,
)
p = P

def box(x0, y0, z0, x1, y1, z1):
    return m3.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

def cyl_y(x, z, y0, y1, d, d2=None):   # from y0 towards y1 (y1 < y0)
    c = m3.Manifold.cylinder(y0 - y1, d / 2, (d if d2 is None else d2) / 2, 64).rotate([90, 0, 0])
    return c.translate([x, y0, z])

def cyl_z(x, y, z0, h, d):
    return m3.Manifold.cylinder(h, d / 2, d / 2, 64).translate([x, y, z0])

def hex_z(x, y, z0, h, af):
    r = af / np.sqrt(3)
    return m3.Manifold.cylinder(h, r, r, 6).rotate([0, 0, 30]).translate([x, y, z0])

DT, CT, LZ = p["dock_t"], p["cart_t"], p["ledge_h"]
# ---------------- dock
dock = box(p["dock_x0"], -DT, 0, p["dock_x1"], 0, p["dock_h"])
dock += box(-p["cw"] / 2, -DT - CT, 0, p["cw"] / 2, -DT, LZ - 0.5)          # hanging ledge
for x, z in p["shroud_holes"]:
    dock += cyl_y(x, z, p["standoff_h"], -0.01, p["standoff_d"])              # standoffs towards the plate (+y)
for x, z in p["cones"]:
    dock += cyl_y(x, LZ + z - 4, -DT + 0.01, -DT - p["cone_h"], p["cone_d"], 0.6)
cut = []
for x, z, r in p["head_relief"]:
    cut.append(cyl_y(x, z, 1, -p["relief_depth"], 2 * r))
for x, z in p["hot_holes"] + p["shroud_holes"]:
    cut.append(cyl_y(x, z, p["standoff_h"] + 1, -DT - 1, p["screw_d"]))
    cut.append(cyl_y(x, z, -DT + p["head_depth"], -DT - 1, p["head_d"]))
for x, z in p["mags"]:
    cut.append(cyl_y(x, LZ + z - 4, -DT + p["mag_t"], -DT - 1, p["mag_d"]))
dock -= m3.Manifold.batch_boolean(cut, m3.OpType.Add)

# ---------------- cartridge
yb, yf = -DT, -DT - CT
cart = box(-p["cw"] / 2, yf, LZ, p["cw"] / 2, yb, LZ + p["cart_h"])
SY = yf - p["sleeve_od"] / 2 + 1.5
ZT = LZ + p["cart_h"]
SZ0 = ZT - p["sleeve_h"]
cart += cyl_z(0, SY, SZ0, p["sleeve_h"], p["sleeve_od"])
cart += box(-8, SY, SZ0, 8, yf + 0.01, ZT)
cut = [hex_z(0, SY, SZ0 - 1, p["sleeve_h"] + 2, p["hex_af"] + p["hex_clear"])]
for x, z in p["cones"]:
    cut.append(cyl_y(x, LZ + z - 4, yb + 0.01, yb - p["cone_h"] - 0.4, p["cone_d"] + 2 * p["cone_clear"], 0.6))
for x, z in p["mags"]:
    cut.append(cyl_y(x, LZ + z - 4, yb + 1, yb - p["mag_t"], p["mag_d"]))
cart -= m3.Manifold.batch_boolean(cut, m3.OpType.Add)

# ---------------- plunger
pl = hex_z(0, SY, ZT - p["plunger_len"] + p["collar_h"], p["plunger_len"] - p["collar_h"] + 0.01, p["hex_af"])
pl += cyl_z(0, SY, ZT, p["collar_h"], p["collar_d"])
zc = ZT + p["collar_h"] / 2
nx = -(p["tool_d"] / 2 + 3.2)
cut = [cyl_z(0, SY, ZT - p["plunger_len"], p["plunger_len"] + p["collar_h"] + 2, p["tool_d"] + p["tool_clear"]),
       box(-p["collar_d"], SY - 1.6, zc - 1.6, 0, SY + 1.6, zc + 1.6),
       box(nx - 1.4, SY - 2.95, zc - 2.95, nx + 1.4, SY + 2.95, ZT + p["collar_h"] + 1)]
pl -= m3.Manifold.batch_boolean(cut, m3.OpType.Add)

def to_tm(m):
    t = m.to_mesh(); return trimesh.Trimesh(t.vert_properties[:, :3], t.tri_verts)

# ---------------- stock parts into the local frame
def stock_local(fn):
    t = trimesh.load(fn)
    v = t.vertices.copy()
    t.vertices = np.c_[v[:, 0] - 3.64, 20.8 - v[:, 2], v[:, 1] - 205.9]
    t.invert() if np.linalg.det(np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])) < 0 else None
    return t
stock = {fn: stock_local(fn) for fn in sorted(glob.glob("stock/carr_*.stl"))}

parts = {"dock": to_tm(dock), "cartridge": to_tm(cart), "plunger": to_tm(pl)}
for k, t in parts.items():
    print(k, "watertight", t.is_watertight, "extents", np.round(t.extents, 1).tolist(), "vol", round(t.volume / 1000, 2))

# clearance check: sample points of each stock part against our parts (signed distance via manifold)
print("--- clash check vs stock carriage (min clearance mm, negative = overlap)")
for fn, s in stock.items():
    if not s.is_watertight:
        s.fill_holes(); s.merge_vertices()
    try:
        sm = m3.Manifold(m3.Mesh(np.asarray(s.vertices, np.float32), np.asarray(s.faces, np.uint32)))
    except Exception as e:
        sm = None
    for k, t in parts.items():
        pq = trimesh.proximity.ProximityQuery(t)
        pts = s.sample(4000) if len(s.faces) else s.vertices
        pts = np.vstack([pts, s.vertices])
        dist = pq.signed_distance(pts)   # positive = inside our part
        mn = -dist.max()
        if mn < 1.0:
            print(f"  {fn.split('/')[-1]:40s} vs {k:9s}: min clearance {mn:6.2f}")
print("tool axis local (x, y):", 0.0, round(SY, 2), "-> model X", 3.64, "model Z", round(20.8 - SY, 2), "(stock nozzle Z 26.8)")
for k, t in parts.items():
    t.export(f"brush_{k}_v2.stl")
json.dump({k: [list(map(float, t.bounds[0])), list(map(float, t.bounds[1]))] for k, t in parts.items()}, open("dock_v2_bounds.json", "w"))
# stock reference mesh in local frame for Fusion
ref = trimesh.util.concatenate(list(stock.values()))
ref.export("stock_carriage_local.stl")
print("stock ref faces", len(ref.faces))
