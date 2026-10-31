"""Base plate, card module and hold-down frame - same parameters as the Fusion design (v14)."""
import manifold3d as m3, trimesh, numpy as np

V = dict(plate_x=220, plate_y=220, plate_t=4.5, rec_d=1.5, rec_clear=0.3, corner_r=12, bed_w=235,
         ear_w=30, lift_d=18, base_t=3, magnet_d=6.2, magnet_t=2.2,
         card_w=148, card_h=210, card_clear=0.6, card_recess=1, card_x=12, notch_d=18,
         cm_x0=3, cm_y0=2.5, pm_y0=15, pm_y1=205, pmag_y0=103,
         card_t=0.35, frame_t=3, frame_overlap=4, frame_clear=0.3, frame_band=8, tab_w=24, tab_l=7)
v = V
v["mod_z"] = v["plate_t"] - v["rec_d"]
v["ear_reach"] = (v["bed_w"] - v["plate_x"]) / 2
v["ear_y1"] = v["plate_y"] / 4 - v["ear_w"] / 2
v["ear_y2"] = 3 * v["plate_y"] / 4 - v["ear_w"] / 2
v["card_y"] = (v["plate_y"] - v["card_h"] - 2 * v["card_clear"]) / 2
v["cm_x1"] = v["card_x"] + v["card_w"] + 2 * v["card_clear"] + 8.1
v["cm_y1"] = v["plate_y"] - 2.5
v["cm_corner"] = v["corner_r"] + 2
v["cmag_xl"] = v["card_x"] - 4.5
v["cmag_xr"] = v["card_x"] + v["card_w"] + 2 * v["card_clear"] + 4
v["cmag_y1"] = v["plate_y"] * 0.27
v["cmag_y2"] = v["plate_y"] * 0.73
v["pm_x0"] = v["cm_x1"] + 3
v["pm_x1"] = v["plate_x"] - 2
v["lip_h"] = v["card_recess"] - v["card_t"] + 0.15

def box(x0, y0, z0, x1, y1, z1):
    return m3.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
def cyl(x, y, z0, h, d):
    return m3.Manifold.cylinder(h, d / 2, d / 2, 64).translate([x, y, z0])
def union(ms):
    return m3.Manifold.batch_boolean(ms, m3.OpType.Add)

PX, PY, PT, MZ, BT = v["plate_x"], v["plate_y"], v["plate_t"], v["mod_z"], v["base_t"]
C, RC = v["corner_r"], v["rec_clear"]
MAGS_C = [(v["cmag_xl"], v["cmag_y1"]), (v["cmag_xl"], v["cmag_y2"]), (v["cmag_xr"], v["cmag_y1"]), (v["cmag_xr"], v["cmag_y2"])]
pcx = (v["pm_x0"] + v["pm_x1"]) / 2
MAGS_P = [(pcx, v["pmag_y0"] + d) for d in (15, 50, 85)]

# ---------------- base plate
base = box(0, 0, 0, PX, PY, PT)
r = v["ear_reach"]
for y in (v["ear_y1"], v["ear_y2"]):
    base += box(-r, y, 0, 0.5, y + v["ear_w"], PT)
    base += box(PX - 0.5, y, 0, PX + r, y + v["ear_w"], PT)
cut = [box(x, y, -1, x + C, y + C, PT + 1) for x in (0, PX - C) for y in (0, PY - C)]
cut += [box(v["cm_x0"] - RC, v["cm_y0"] - RC, MZ, v["cm_x1"] + RC, v["cm_y1"] + RC, PT + 1),
        box(v["pm_x0"] - RC, v["pm_y0"] - RC, MZ, v["pm_x1"] + RC, v["pm_y1"] + RC, PT + 1),
        cyl((v["cm_x0"] + v["cm_x1"]) / 2, v["cm_y0"] - RC, MZ, 5, v["lift_d"]),
        cyl(v["pm_x1"] + RC, (v["pm_y0"] + v["pm_y1"]) / 2, MZ, 5, v["lift_d"])]
cut += [cyl(x, y, MZ - v["magnet_t"], v["magnet_t"] + 0.01, v["magnet_d"]) for x, y in MAGS_C + MAGS_P]
base -= union(cut)

# ---------------- card module
top = MZ + BT
card = box(v["cm_x0"], v["cm_y0"], MZ, v["cm_x1"], v["cm_y1"], top)
K = v["cm_corner"]
cut = [box(0, 0, MZ - 1, K, K, top + 1), box(0, PY - K, MZ - 1, K, PY, top + 1)]
cut += [box(v["card_x"], v["card_y"], top - v["card_recess"], v["card_x"] + v["card_w"] + 2 * v["card_clear"],
            v["card_y"] + v["card_h"] + 2 * v["card_clear"], top + 1),
        cyl(v["card_x"] + v["card_clear"] + v["card_w"] / 2, v["card_y"], top - v["card_recess"], 2, v["notch_d"])]
FR_X = (v["card_x"] - 4, v["card_x"] + v["card_w"] + 2 * v["card_clear"] + 4)
FR_Y = (v["card_y"] + 20, PY / 2, PY - v["card_y"] - 20)
cut += [cyl(x, y, top - v["magnet_t"], v["magnet_t"] + 1, v["magnet_d"]) for x in FR_X for y in FR_Y]
cut += [cyl(x, y, MZ - 1, v["magnet_t"] + 1, v["magnet_d"]) for x, y in MAGS_C]
card -= union(cut)

# ---------------- hold-down frame (as assembled)
cx0 = v["card_x"] - v["frame_band"]
frame = box(cx0, 1, top, cx0 + v["card_w"] + 2 * v["card_clear"] + 2 * v["frame_band"], PY - 1, top + v["frame_t"])
tx0 = v["card_x"] + v["card_clear"] + v["card_w"] / 2 - v["tab_w"] / 2
frame += box(tx0, -v["tab_l"], top, tx0 + v["tab_w"], 3, top + v["frame_t"])
frame += box(v["card_x"] + v["frame_clear"], v["card_y"] + v["frame_clear"], top - v["lip_h"],
             v["card_x"] + v["card_w"] + 2 * v["card_clear"] - v["frame_clear"],
             v["card_y"] + v["card_h"] + 2 * v["card_clear"] - v["frame_clear"], top + 0.01)
wx0, wy0 = v["card_x"] + v["card_clear"] + v["frame_overlap"], v["card_y"] + v["card_clear"] + v["frame_overlap"]
cut = [box(wx0, wy0, top - 2, wx0 + v["card_w"] - 2 * v["frame_overlap"], wy0 + v["card_h"] - 2 * v["frame_overlap"], top + v["frame_t"] + 1),
       box(0, 0, top - 2, C, C, top + v["frame_t"] + 1), box(0, PY - C, top - 2, C, PY, top + v["frame_t"] + 1)]
cut += [cyl(x, y, top - 0.01, v["magnet_t"], v["magnet_d"]) for x in FR_X for y in FR_Y]
frame -= union(cut)

def tm(m):
    t = m.to_mesh(); return trimesh.Trimesh(t.vert_properties[:, :3], t.tri_verts)

out = {"base_plate": tm(base), "card_module": tm(card), "hold_down_frame": tm(frame)}
# sanity: no overlaps when assembled
print("base/card overlap", round((base ^ card).volume(), 3), " card/frame overlap", round((card ^ frame).volume(), 3))
for k, t in out.items():
    b = t.bounds
    print(k, "watertight", t.is_watertight, "bbox", np.round(b, 2).ravel().tolist(), "vol cm3", round(t.volume / 1000, 2))
    t.export(f"{k}.stl")
# frame flipped for printing (top face down, lip up)
f = out["hold_down_frame"].copy(); f.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
f.apply_translation(-f.bounds[0]); f.export("hold_down_frame_print_orientation.stl")
