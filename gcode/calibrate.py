#!/usr/bin/env python3
"""Write calibrate.gcode: touch the brush on the four corners of the paint window.

Watch where the bristles land compared with the corners of the frame opening, then correct the
offsets below and run this again until all four touches sit just inside the corners.
Run:   python3 calibrate.py        then   python3 octo.py send calibrate.gcode
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))

# ---------------- OFFSETS: printer = fixture + offset ----------------
# Read from ../data/calibration.json (measured), falling back to the Fusion-based estimate.
_cal_file = os.path.join(HERE, "..", "data", "calibration.json")
if os.path.exists(_cal_file):
    _off = json.load(open(_cal_file))["offset"]
    OFFSET_X, OFFSET_Y, OFFSET_Z = _off["x"], _off["y"], _off["z"]
else:
    OFFSET_X, OFFSET_Y, OFFSET_Z = 0.0, 18.0, 36.0
# ----------------------------------------------------------------------
INSET = 3.0         # touch this far inside each corner, so the bristles clear the frame
HOVER = 6.0         # mm above the frame top while moving between corners
SAFE_Z = FIX["safe_travel_tip_z"] + 3
BED = (220.0, 220.0)

pw = FIX["paint_window"]
card_z = FIX["card_area"]["surface_z"]
hover_z = pw["frame_top_z"] + HOVER


def mz(z):
    return z + OFFSET_Z


def mxy(x, y):
    px, py = x + OFFSET_X, y + OFFSET_Y
    cx, cy = min(max(px, 0), BED[0]), min(max(py, 0), BED[1])
    note = "" if (cx, cy) == (px, py) else f"  ; OUT OF TRAVEL, clamped from X{px:.1f} Y{py:.1f}"
    return cx, cy, note


corners = [("front left", pw["x0"] + INSET, pw["y0"] + INSET),
           ("front right", pw["x1"] - INSET, pw["y0"] + INSET),
           ("back right", pw["x1"] - INSET, pw["y1"] - INSET),
           ("back left", pw["x0"] + INSET, pw["y1"] - INSET)]

g = [
    "; CALIBRATE: touch the four corners of the paint window",
    f"; offsets (printer = fixture + offset): X {OFFSET_X:+.1f}  Y {OFFSET_Y:+.1f}  Z {OFFSET_Z:+.1f}",
    f"; corners are the paint window inset {INSET} mm; touch = card surface (fixture Z {card_z})",
    "; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). No card or paint needed.",
    "M104 S0", "M140 S0", "M107", "G21", "G90",
    "G28 ; home X, Y, Z with the cartridge off",
    f"G1 Z{mz(SAFE_Z):.2f} F600 ; bed down to a safe height",
    "M400",
    "M117 Attach brush, then Resume",
    "@pause ; OctoPrint pauses here: snap the cartridge on, then press Resume",
]
for name, x, y in corners:
    px, py, note = mxy(x, y)
    g += [
        f"; --- {name}: fixture X{x:.1f} Y{y:.1f}",
        f"G0 Z{mz(hover_z):.2f} F900",
        f"G0 X{px:.2f} Y{py:.2f} F4000{note}",
        f"M117 {name}",
        f"G1 Z{mz(card_z):.2f} F300 ; lower until the tip touches",
        "G4 S3 ; hold 3 s so you can look",
        f"G1 Z{mz(hover_z):.2f} F600",
    ]
cx, cy, note = mxy((pw["x0"] + pw["x1"]) / 2, (pw["y0"] + pw["y1"]) / 2)
g += [
    "; park over the centre, lifted clear",
    f"G1 Z{mz(SAFE_Z):.2f} F600",
    f"G0 X{cx:.2f} Y{cy:.2f} F4000{note}",
    "M400",
    "M117 Calibration done",
]
open(os.path.join(HERE, "calibrate.gcode"), "w").write("\n".join(g) + "\n")
print("wrote calibrate.gcode")
for line in g:
    if "OUT OF TRAVEL" in line:
        print("warning:", line.split(";", 1)[1].strip(), "->", line.split()[1:3])
