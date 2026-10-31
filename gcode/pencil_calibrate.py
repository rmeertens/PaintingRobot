#!/usr/bin/env python3
"""Write pencil_calibrate.gcode: check the pencil's position and height before writing.

It homes, pauses so you can attach the pencil, touches the four corners of the paint window at
exactly the height pencil_text.gcode writes at, and then STAYS DOWN on the back-left corner with
the motors on. If the pencil isn't just touching there, jog it in OctoPrint until it is and tell
Claude the position (M114); it gets saved as the pencil offset in ../data/calibration.json.
Run:   python3 pencil_calibrate.py      then   python3 octo.py send pencil_calibrate.gcode
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "..", "data", "fixture_coordinates.json")))
CAL = json.load(open(os.path.join(HERE, "..", "data", "calibration.json")))
OFF = CAL.get("pencil_offset") or CAL["offset"]          # pencil's own offset once measured
OX, OY, OZ = OFF["x"], OFF["y"], OFF["z"]
PW = FIX["paint_window"]
CARD_Z = FIX["card_area"]["surface_z"]

# keep these the same as in pencil_text.py so the touch height is the writing height
PENCIL_DOWN = 1.0    # tip commanded this far below the paper while writing
PEN_UP = 3.0
APPROACH = 20.0
INSET = 3.0
BED = (220.0, 220.0)


def m(x, y):
    px, py = x + OX, y + OY
    if not (0 <= px <= BED[0] and 0 <= py <= BED[1]):
        sys.exit(f"Out of reach: fixture X{x:.1f} Y{y:.1f} -> printer X{px:.1f} Y{py:.1f}")
    return px, py


z_draw = CARD_Z - PENCIL_DOWN + OZ
z_up = CARD_Z + PEN_UP + OZ
corners = [("front left", PW["x0"] + INSET, PW["y0"] + INSET),
           ("front right", PW["x1"] - INSET, PW["y0"] + INSET),
           ("back right", PW["x1"] - INSET, PW["y1"] - INSET),
           ("back left", PW["x0"] + INSET, PW["y1"] - INSET)]
src = "pencil_offset" if CAL.get("pencil_offset") else "brush offset (pencil not measured yet)"
g = [
    "; PENCIL CALIBRATE: touch the corners at writing height, then stay down on back-left",
    f"; using {src}: X {OX:+.1f}  Y {OY:+.1f}  Z {OZ:+.1f};  writing height = printer Z {z_draw:.2f}",
    "; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.",
    "M104 S0", "M140 S0", "M107", "G21", "G90",
    "G28 ; home with the cartridge off",
    f"G1 Z{CARD_Z + 45 + OZ:.2f} F600 ; bed down for attaching the pencil",
    "M400",
    "M117 Attach pencil, then Resume",
    "@pause ; snap the pencil cartridge on, then press Resume",
    f"G1 Z{CARD_Z + APPROACH + OZ:.2f} F600",
]
for name, x, y in corners:
    px, py = m(x, y)
    last = name == "back left"
    g += [f"; --- {name}: fixture X{x:.1f} Y{y:.1f}",
          f"G0 X{px:.2f} Y{py:.2f} F4000",
          f"G1 Z{z_up:.2f} F600",
          f"M117 {name}",
          f"G1 Z{z_draw:.2f} F300 ; down to writing height"]
    if not last:
        g += ["G4 S3 ; hold so you can look", f"G1 Z{z_up:.2f} F600"]
g += ["M400",
      "M117 On paper at writing height",
      "; stays here, pencil down, motors ON: jog in OctoPrint if it isn't just touching"]
open(os.path.join(HERE, "pencil_calibrate.gcode"), "w").write("\n".join(g) + "\n")
print(f"wrote pencil_calibrate.gcode ({src}); ends down on back-left at printer "
      f"X{m(*corners[-1][1:])[0]:.1f} Y{m(*corners[-1][1:])[1]:.1f} Z{z_draw:.2f}")
