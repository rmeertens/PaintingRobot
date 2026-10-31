import manifold3d as m3, trimesh, numpy as np, json
# paint module footprint & heights (same as the Fusion design, so it fits the existing base plate)
X0,X1,Y0,Y1 = 172.3, 218.0, 15.0, 205.0
MOD_Z, BASE_T = 3.0, 3.0                 # module underside z, module plate thickness
JAR_BOT, JAR_TOP = 34.0, 41.0            # Bonne Maman mini: across flats, base / top
JAR_H = 46.13
DRAFT = np.arctan((JAR_TOP - JAR_BOT) / 2 / JAR_H)   # jar side taper; pockets and collars follow it
CLEAR, WALL, COLLAR_H = 0.8, 2.2, 20.0
PITCH = JAR_TOP + 1.5
N = 4
MAG_D, MAG_T = 6.2, 2.2
cx = (X0 + X1) / 2
ys = [Y0 + 1 + JAR_TOP / 2 + i * PITCH for i in range(N)]
mags = [(cx, 103 + d) for d in (15, 50, 85)]   # must match the base-plate magnet pockets

def octo(af, h, x, y, z):
    """octagon (across flats af) extruded h, widening upward at the jar's taper"""
    r = af / 2 / np.cos(np.pi / 8)
    a = np.pi / 8 + np.arange(8) * np.pi / 4
    cs = m3.CrossSection([list(zip(r * np.cos(a), r * np.sin(a)))])
    s = (af + 2 * h * np.tan(DRAFT)) / af
    return m3.Manifold.extrude(cs, h, 0, 0, [s, s]).translate([x, y, z])

top = MOD_Z + BASE_T
body = m3.Manifold.cube([X1 - X0, Y1 - Y0, BASE_T]).translate([X0, Y0, MOD_Z])
for y in ys:
    body += octo(JAR_BOT + CLEAR + 2 * WALL, COLLAR_H, cx, y, top - 0.01)
cut = [octo(JAR_BOT + CLEAR, COLLAR_H + 1, cx, y, top) for y in ys]
for x, y in mags:
    cut.append(m3.Manifold.cylinder(MAG_T, MAG_D / 2, MAG_D / 2, 48).translate([x, y, MOD_Z - 0.01]))
# thumb slots in each collar (front side) so a stuck jar can be pushed out
for y in ys:
    cut.append(m3.Manifold.cube([12, 8, COLLAR_H + 1]).translate([cx - 6, y - (JAR_BOT + CLEAR) / 2 - 6, top + 2]))
body -= m3.Manifold.batch_boolean(cut, m3.OpType.Add)
t = body.to_mesh(); tm = trimesh.Trimesh(t.vert_properties[:, :3], t.tri_verts)
tm.export("paint_module_4_jars.stl")
print("watertight", tm.is_watertight, "extents", np.round(tm.extents, 1).tolist())
print("jar top edges y:", [(round(y - JAR_TOP / 2, 1), round(y + JAR_TOP / 2, 1)) for y in ys], "module y", Y0, Y1)
print("collar gap mm:", round(PITCH - (JAR_BOT + CLEAR + 2 * WALL), 2))
c = json.load(open("fixture_coordinates.json"))
for k in ("water_well", "wipe_bar", "rinse_well", "paint_wells"):
    c.pop(k, None)
c["jars"] = [dict(id=f"J{i+1}", cx=round(cx, 2), cy=round(y, 2), floor_z=top) for i, y in enumerate(ys)]
c["_note"] = c.get("_note", "") + " Jars: Bonne Maman mini, base sits at floor_z; measure jar height for the dip depth."
json.dump(c, open("fixture_coordinates.json", "w"), indent=2)
print(json.dumps(c["jars"]))
