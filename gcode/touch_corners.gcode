; Touch the four corners of the paint window with the brush.
; Brush offset from the old nozzle (working estimate, not measured):
;   10 mm below  -> printer Z = fixture Z + 10
;   5 mm left    -> printer X = fixture X + 5
;   10 mm back   -> printer Y = fixture Y - 10
; Corners are the paint window (X 16.6-156.6, Y 9.0-211.0) inset 3 mm so the brush clears the frame:
;   fixture X 19.6 / 153.6, Y 12.0 / 208.0  ->  printer X 24.6 / 158.6, Y 2.0 / 198.0
;   touch  Z 15.0 = fixture Z 5.0 (card surface)
;   hover  Z 25.0 = fixture Z 15.0 (6 mm above the frame top)
;   safe   Z 88.0 = fixture Z 78.0 (well above the jar rims, safe_travel_tip_z 57.1)
; BEFORE STARTING: brush cartridge OFF (G28 raises the bed to nozzle height).
; After homing it waits 5 s, then carries on by itself: snap the brush on during the wait.
; Run with: python3 octo.py start touch_corners.gcode
M104 S0
M140 S0
G21
G90
G28 ; home X, Y, Z (cartridge off!)
G1 Z88 F600 ; bed down to safe height
M400
M117 Attach brush - 5 s
G4 S5 ; time to attach the brush, then continue automatically
; bottom left (front left)
G1 X24.6 Y2.0 F6000
G1 Z25 F600
G1 Z15 F300
G4 P1000
G1 Z25 F600
; bottom right (front right)
G1 X158.6 Y2.0 F6000
G1 Z15 F300
G4 P1000
G1 Z25 F600
; top left (back left)
G1 X24.6 Y198.0 F6000
G1 Z15 F300
G4 P1000
G1 Z25 F600
; top right (back right)
G1 X158.6 Y198.0 F6000
G1 Z15 F300
G4 P1000
G1 Z25 F600
; lift clear and park the brush over the card centre (fixture X 86.6, Y 110)
G1 Z88 F600
G1 X91.6 Y100.0 F6000
M400
M117 Corners done
