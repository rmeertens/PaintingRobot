; Home the printer, drop the bed 50 mm, park the brush over the card centre.
; BEFORE STARTING: brush cartridge OFF (G28 raises the bed to nozzle height).
; Run with: python3 octo.py start home_and_center.gcode
M104 S0
M140 S0
G21
G90
G28 ; home X, Y, Z
G1 Z50 F600 ; bed 50 mm down (Z up = bed down)
G1 X86.6 Y110 F6000 ; card / paint window centre
M400
M117 Parked over card centre
