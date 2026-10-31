; PENCIL CALIBRATE: touch the corners at writing height, then stay down on back-left
; using brush offset (pencil not measured yet): X -14.5  Y +7.1  Z +1.1;  writing height = printer Z 5.10
; BEFORE STARTING: cartridge OFF (G28 raises the bed to nozzle height). Card in the frame.
M104 S0
M140 S0
M107
G21
G90
G28 ; home with the cartridge off
G1 Z51.10 F600 ; bed down for attaching the pencil
M400
M117 Attach pencil, then Resume
@pause ; snap the pencil cartridge on, then press Resume
G1 Z26.10 F600
; --- front left: fixture X19.5 Y65.9
G0 X5.00 Y73.00 F4000
G1 Z9.10 F600
M117 front left
G1 Z5.10 F300 ; down to writing height
G4 S3 ; hold so you can look
G1 Z9.10 F600
; --- front right: fixture X215.5 Y65.9
G0 X201.00 Y73.00 F4000
G1 Z9.10 F600
M117 front right
G1 Z5.10 F300 ; down to writing height
G4 S3 ; hold so you can look
G1 Z9.10 F600
; --- back right: fixture X215.5 Y199.9
G0 X201.00 Y207.00 F4000
G1 Z9.10 F600
M117 back right
G1 Z5.10 F300 ; down to writing height
G4 S3 ; hold so you can look
G1 Z9.10 F600
; --- back left: fixture X19.5 Y199.9
G0 X5.00 Y207.00 F4000
G1 Z9.10 F600
M117 back left
G1 Z5.10 F300 ; down to writing height
M400
M117 On paper at writing height
; stays here, pencil down, motors ON: jog in OctoPrint if it isn't just touching
