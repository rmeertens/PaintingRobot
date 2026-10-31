; CALIBRATE: touch the four corners of the paint window
; offsets (printer = fixture + offset): X -14.5  Y +7.1  Z +1.1
; corners are the paint window inset 3.0 mm; touch = card surface (fixture Z 5.0)
; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). No card or paint needed.
M104 S0
M140 S0
M107
G21
G90
G28 ; home X, Y, Z with the cartridge off
G1 Z61.20 F600 ; bed down to a safe height
M400
M117 Attach brush, then Resume
@pause ; OctoPrint pauses here: snap the cartridge on, then press Resume
; --- front left: fixture X19.5 Y65.9
G0 Z16.10 F900
G0 X5.00 Y73.00 F4000
M117 front left
G1 Z6.10 F300 ; lower until the tip touches
G4 S3 ; hold 3 s so you can look
G1 Z16.10 F600
; --- front right: fixture X215.5 Y65.9
G0 Z16.10 F900
G0 X201.00 Y73.00 F4000
M117 front right
G1 Z6.10 F300 ; lower until the tip touches
G4 S3 ; hold 3 s so you can look
G1 Z16.10 F600
; --- back right: fixture X215.5 Y199.9
G0 Z16.10 F900
G0 X201.00 Y207.00 F4000
M117 back right
G1 Z6.10 F300 ; lower until the tip touches
G4 S3 ; hold 3 s so you can look
G1 Z16.10 F600
; --- back left: fixture X19.5 Y199.9
G0 Z16.10 F900
G0 X5.00 Y207.00 F4000
M117 back left
G1 Z6.10 F300 ; lower until the tip touches
G4 S3 ; hold 3 s so you can look
G1 Z16.10 F600
; park over the centre, lifted clear
G1 Z61.20 F600
G0 X103.00 Y140.00 F4000
M400
M117 Calibration done
