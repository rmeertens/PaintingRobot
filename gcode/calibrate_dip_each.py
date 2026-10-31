#!/usr/bin/env python3
"""Write calibrate_dip_each.gcode: dip the brush into each jar once, touch the bottom, draw a tiny circle.

No paint needed. Watch that the brush goes into the middle of each jar, reaches the bottom,
and that the cartridge never touches a jar rim.
Run:   python3 calibrate_dip_each.py      then   python3 octo.py send calibrate_dip_each.gcode
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OX, OY, OZ = CAL["offset"]["x"], CAL["offset"]["y"], CAL["offset"]["z"]

# ---------------- SETTINGS (fixture mm: Z is height above the glass) ----------------
JAR_GLASS = 4.0      # thickness of the jar's glass bottom (guess); touch target = floor_z + this
CIRCLE_R = 2.5       # radius of the tiny circle drawn on the jar bottom
STICKOUT = None      # brush tip below the bottom of the cartridge, mm. None = estimate from calibration
RIM_MARGIN = 3.0     # keep the cartridge at least this far above the jar rims
# -------------------------------------------------------------------------------------
BED = (220.0, 220.0)
if STICKOUT is None:
    # Fusion: 45 mm stick-out puts the tip 36 mm below the old nozzle (printer Z = fixture Z + 36),
    # so every mm less stick-out raises the tip 1 mm: stick-out = 45 - (36 - OZ)
    STICKOUT = 45 - (36 - OZ)

jars = FIX["jars"]
rim = max(j["rim_z"] for j in jars)
safe_tip = max(FIX["safe_travel_tip_z"], rim + 5)           # travel height for the brush tip
lowest_tip = rim + RIM_MARGIN - STICKOUT                     # cartridge bottom stays above the rims


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


def mz(z):
    return z + OZ


g = [
    "; CALIBRATE DIP EACH: dip into each jar once, touch the bottom, draw a tiny circle",
    f"; offsets from data/calibration.json: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f}",
    f"; brush stick-out below the cartridge: {STICKOUT:.1f} mm",
    "; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Jars in, no paint needed.",
    "M104 S0", "M140 S0", "M107", "G21", "G90",
    "G28 ; home X, Y, Z with the cartridge off",
    f"G1 Z{mz(safe_tip):.2f} F600 ; bed down: brush tip {safe_tip:.1f} mm above the glass, clear of the rims",
    "M400",
    "M117 Attach brush, then Resume",
    "@pause ; snap the cartridge on, then press Resume",
]
warnings = []
for j in jars:
    bottom = j["floor_z"] + JAR_GLASS
    target = max(bottom, lowest_tip)
    if target > bottom:
        warnings.append(f"{j['id']}: can only reach {target - j['floor_z']:.1f} mm above the jar floor, "
                        f"not the bottom (cartridge would hit the rim)")
    cx, cy = m(j["cx"], j["cy"])
    g += [f"; --- {j['id']}: fixture X{j['cx']:.1f} Y{j['cy']:.1f}, bottom at Z {bottom:.1f}, going to Z {target:.1f}",
          f"G0 Z{mz(safe_tip):.2f} F900",
          f"G0 X{cx:.2f} Y{cy:.2f} F4000",
          f"M117 Dip {j['id']}",
          f"G1 Z{mz(target + 8):.2f} F900",
          f"G1 Z{mz(target):.2f} F300 ; down to the bottom",
          f"G1 X{cx + CIRCLE_R:.2f} Y{cy:.2f} F600"]
    for k in range(1, 25):
        a = 2 * math.pi * k / 24
        g.append(f"G1 X{cx + CIRCLE_R * math.cos(a):.2f} Y{cy + CIRCLE_R * math.sin(a):.2f} F600")
    g += [f"G1 X{cx:.2f} Y{cy:.2f} F600",
          "G4 S2 ; hold so you can look",
          f"G1 Z{mz(safe_tip):.2f} F600 ; lift out"]
park = m((FIX["paint_window"]["x0"] + FIX["paint_window"]["x1"]) / 2, FIX["paint_window"]["y0"] + 20)
g += [f"G0 X{park[0]:.2f} Y{park[1]:.2f} F4000", "M400", "M117 Dip test done"]
for w in warnings:
    g.insert(4, "; WARNING " + w)
open(os.path.join(HERE, "calibrate_dip_each.gcode"), "w").write("\n".join(g) + "\n")
print("wrote calibrate_dip_each.gcode")
for w in warnings:
    print("WARNING", w)
