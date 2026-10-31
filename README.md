# Automatic painting printer

This project turns an **old Creality Ender 5** into a machine that paints **A5 Christmas cards** with a
real brush (or draws with a pen), using **acrylic paint in Bonne Maman mini jam jars**.
The hotend comes off and a magnetic quick-swap brush holder goes on in its place. A modular fixture on
the bed holds the card and the paint jars.

All the printed parts are designed to be printed on a **Prusa CORE One+**. The Ender 5 itself only does
the painting.

> **Status (29 Oct 2026):** the mechanical design is complete and checked in CAD, including an
> alternative **tilted pen cartridge** (30°, sideways) and a **spring-loaded pen cartridge** next to the brush cartridge. The first fixture and dock
> were printed and test-fitted, which led to the current **layout v2** and **dock v3**. **The current parts
> haven't been printed yet**, and there is no painting G-code yet. See
> [What's not done yet](#7-whats-not-done-yet).

---

## Contents

1. [How it works (overview)](#1-how-it-works-overview)
2. [Folder contents](#2-folder-contents)
3. [Parts to print and hardware to buy](#3-parts-to-print-and-hardware-to-buy)
4. [Assumptions and where each number came from](#4-assumptions-and-where-each-number-came-from)
5. [Check these before printing](#5-check-these-before-printing)
6. [Coordinate systems and the coordinates file](#6-coordinate-systems-and-the-coordinates-file)
7. [What's not done yet](#7-whats-not-done-yet)
8. [How to change the design](#8-how-to-change-the-design)
9. [Design decisions and history](#9-design-decisions-and-history)

---

## 1. How it works (overview)

```
                Ender 5 X-carriage (stock steel plate)
                ┌──────────────────────────────┐
                │  BRUSH DOCK (bolted, 3×M3)   │  ← stays on the printer
                │   ┌──────────────┐           │
                │   │ TOOL         │ magnets + │  ← snaps on/off; one per tool
                │   │ CARTRIDGE    │ 2 cones   │
                │   │   ┌─PLUNGER─┐│           │  ← floats up/down in a hex sleeve,
                │   │   │ brush   ││           │    holds the brush with a set screw
                └───┴───┴────┬────┴┴───────────┘
                             │ brush tip
   ══════════════════════════╪══════════════════════  bed (glass on aluminium, 7.5 mm)
   [clip]  BASE PLATE (235 × 220, clipped on its left/right edges)  [clip]
           ├─ CARD MODULE   (A5 card, landscape, in a 1 mm pocket) + HOLD-DOWN FRAME (magnetic)
           └─ PAINT MODULE  (5 Bonne Maman mini jars in a row, octagonal collars)

   Seen from above (layout v2):        BACK of printer
                     ┌──────────────────────────────────────┐
                     │   ┌──────────────────────────────┐   │
                     │   │      A5 card, landscape      │   │
              [clip] │   │       210 × 148 mm           │   │ [clip]   ← Y 145 (clear of the bed heater)
              [clip] │   └──────────────────────────────┘   │ [clip]   ← Y 75
                     │ ┌──────────────────────────────────┐ │
                     │ │ (J1) (J2) (J3) (J4) (J5)  jars   │ │  ← paint module: full width, no clips
                     │ └──────────────────────────────────┘ │
                     └──────────────────────────────────────┘
                                   FRONT of printer
```

**Bed side (fixture)**
- **Base plate** (**235 × 220 mm**, as wide as the Ender 5's bed, so its left and right edges line up
  with the bed's edges): held by **4 printed C-clips** that hook under the aluminium bed and press down
  on the plate's edge, two on each side, **all beside the card** (at Y = 75 and 145 mm), so the paint
  area stays free and the back of the bed (heater wiring) is avoided. It never comes off. The card module and frame have small notches where the clip jaws
  sit.
- **Card module** and **paint module**: each drops into its own 1.5 mm-deep recess in the base plate
  and is held by **6 × 2 mm magnets**. The recess walls locate them to within about 0.3 mm, so they go
  back in the same place every time and the painting coordinates stay valid.
- **Hold-down frame**: a magnetic frame that sits on the card module and clamps the card's edges
  (4 mm overlap), so the card can't lift when it gets wet.

**Printer side (brush holder)**
- **Brush dock** (engraved **FRONT** and **BACK**): replaces the hotend. Its back sits flat on the
  carriage plate, and **two hex sockets slip over the carriage's two hex standoffs** (where the hotend
  was screwed on). That locates it. It's held by **3 × M3×10**: 2 into the standoffs and 1 into the upper
  fan-shroud thread. A large **open notch in the lower-left corner** clears the bottom eccentric
  bolt + nut. The dock is **narrowed** (24 mm each side of the brush axis) so it stays clear of
  the brass belt clamps and the belts. A pocket on the back clears the top-right wheel-bolt head.
- **Tool cartridge**: one per tool. **4 × 12×3 mm magnets** (12 mm diameter, 3 mm thick) pull it onto the dock and **2 conical
  locators** line it up. A small ledge at the bottom lets you hang it on one-handed.
- **Pen cartridge** (alternative, optional): the same back plate, magnets, cones and notch as the
  brush cartridge, so it snaps onto the same dock, but its sleeve is **tilted 30° sideways, along the
  gantry (X)** (`pen_tilt`), so the pen meets the paper at an angle, which most fineliners, felt-tips and ballpoints draw better with. It
  takes its own **Pen plunger** for a **10 mm** pen (`pen_d`). See [The pen cartridge](#the-pen-cartridge).
- **Spring pen cartridge** (third option, optional): same dock interface again, but the pen is clamped
  in a small ring on a **swing arm** that pivots on the cartridge, like a car's trailing arm. A **tiny
  spring** (a ballpoint-pen click spring) close to the pivot pushes the arm down. Pen tilted 30° sideways
  (`spr_tilt`), with its tip right under the brush position. See
  [The spring pen cartridge](#the-spring-pen-cartridge).
- **Plunger**: a hex rod that slides freely in the cartridge's sleeve. The tool is clamped in it with
  an M3 set screw. The brush presses on the card with **only the weight of the plunger and brush**, and
  can lift if it hits something, so Z doesn't need to be perfect. For more pressure, drop M8 nuts on the
  collar.

---

## 2. Folder contents

```
automatic-painting-printer/
├── README.md                  ← this file
├── prints/                    ← STLs to print (see section 3)
│   └── old_v1_layout/         ← superseded parts from the first (portrait, 4-jar) layout: don't print
├── cad-scripts/               ← Fusion + Python scripts (see section 8); old/ holds superseded ones
├── data/
│   └── fixture_coordinates.json   ← where the card / jars are, for writing G-code (see section 6)
├── fusion/
│   ├── Acrylic card painting fixture.f3d   ← full parametric Fusion design (import via File → Open → Open from my computer)
│   └── Acrylic card painting fixture.step  ← same assembly for any other CAD program
└── images/                    ← screenshots of the Fusion model
```

**Master design:** the Fusion 360 design **"Acrylic card painting fixture"** in the Fusion project
**"Admin Project"** (owner: Roland). It's version **v24** or later (layout v2b + dock v3 + pen cartridge). A copy is in `fusion/` as `.f3d` and `.step`.
- It's parametric: change sizes under *Modify → Change Parameters*.
- **All the STLs in `prints/` were exported directly from this Fusion design.** The bed clip is the only
  part that can also be regenerated in Python (`clip75.py`).
- If Fusion and an STL ever disagree, **Fusion is the source of truth**.

The Fusion design also contains two **reference-only** bodies. Don't print these:
- **"Ender 5 carriage (reference)"**: a simplified stock carriage plate, there to show the dock fits.
- **"Brush (reference)"**: a dummy 7 mm brush, there to check clearances.
- **"Pen (reference)"**: a dummy 10 mm pen in the pen cartridge.

The **pen set** (Pen cartridge, Pen plunger, Pen (reference)) is shown **parked 80 mm to the right**
of the brush set, and the **spring pen set** (Spring pen cartridge, Pen swing arm, Spring (reference),
Pen (reference, spring)) **160 mm to the right**, so all three are visible. In reality it goes on the same dock *instead of* the brush
cartridge. Its clearance check was done in the mounted position.

---

## 3. Parts to print and hardware to buy

| # | File in `prints/` | Qty | Material | Orientation on the print bed | Notes |
|---|---|---|---|---|---|
| 1 | `01_base_plate.stl` | 1 | PETG or PLA | flat, as exported | **235 × 220 × 4.5 mm**. Fits the CORE One+ (250 × 220 × 270) only with the **skirt off**, 235 mm along X. |
| 2 | `02_card_module.stl` | 1 | PLA/PETG | flat | 229 × 164.5 mm. A5 **landscape** pocket 211.2 × 149.2 mm × 1 mm deep, finger notch at the front, clip notches on both sides. |
| 3 | `03_hold_down_frame.stl` | 1 | PLA/PETG | **flip it in the slicer** so the flat top face is on the bed and the 0.8 mm lip points up (it's exported as assembled) | 227 × 169 mm, 3 mm thick. Narrow 5 mm border at the front (next to the jars), 8 mm elsewhere, lift tab at the **back**. |
| 4 | `04_paint_module_5_jars.stl` | 1 | **PETG** | flat | **229 × 47.5 mm**, full width with no notches, so it's the largest free area for jars now and other inserts later. **5** octagonal collars in a row, **20 mm tall**, tapered to follow the jar's shape. |
| 5 | `05_bed_clip_print_4x.stl` | **4** | **PETG** (not PLA: too stiff, cracks) | on its side, C-shape flat on the bed, so the jaws bend along the layers | Opening 11.6 mm (7.5 mm bed + 4.5 mm base plate − 0.4 mm squeeze). |
| 6 | `06_brush_dock.stl` | 1 | PETG | lying on its **BACK** (engraving down): sockets and notch print without support, cones point up | 48 × 63.5 × 13.5 mm (+ cones). Version 3, refitted from photos of the real carriage. |
| 7 | `07_tool_cartridge.stl` | 1 per tool | PETG/PLA | upright, so the hex sleeve prints vertically | |
| 8 | `08_plunger_7mm_tool.stl` | 1 per tool | PETG/PLA | collar down | For a **7 mm** brush handle. Make another for each tool diameter (section 8). |
| 8b | `08b_plunger_7.25mm_brush.stl` | 1 per brush | PETG/PLA | collar down (flip it: exported collar up) | Same plunger as #8 for a **7.25 mm** brush handle (bore 7.55 mm). Fits the brush cartridge (#7). |
| 8c | `08c_plunger_10.5mm_brush.stl` | 1 per brush | PETG/PLA | collar down (flip it: exported collar up) | Same plunger as #8 for a **10.5 mm** brush handle (bore 10.8 mm). The M3 nut slot is moved 1.75 mm outwards so it doesn't break into the bigger bore. Fits #7 (and #9). |
| 9 | `09_pen_cartridge.stl` | optional, 1 | PETG/PLA | upright (as exported, back plate standing). Turn on **supports from the build plate only**: the lower end of the tilted sleeve and the rib overhang. | Alternative cartridge with the sleeve tilted **30° sideways (X)**; same magnets and cones as #7. The top-right corner of the plate has a scallop so the plunger collar can slide. |
| 10 | `10_pen_plunger_10mm.stl` | optional, 1 per pen | PETG/PLA | **flip it** so the collar is down (it's exported collar up) | For a **10 mm** pen. Same hex as #8, so it also fits the brush cartridge. |
| 11 | `11_spring_pen_cartridge.stl` | optional, 1 | PETG | lying on its **back** (the face with the magnet pockets down): pivot spigot, spring tab and stop all point up, no supports | Back plate with a pivot boss + spigot (M3 pilot hole), a spring tab with a spring pocket, and a down-stop. |
| 12 | `12_pen_swing_arm.stl` | optional, 1 per pen | PETG | lying on its **back** (flat side down), no supports | Arm 25 mm from pivot to pen, with a 19 mm ring for a **10 mm** pen and a spring pocket 8 mm from the pivot. |

Suggested settings: 0.2 mm layers, 4+ walls, 15–20 % infill. Use 5+ top/bottom layers on the paint
module.

**Hardware**

| Item | Qty | Where |
|---|---|---|
| Disc magnets **6 × 2 mm** | **36** | base plate ↔ card module (4 pairs), base plate ↔ paint module (3 pairs), card module ↔ hold-down frame (11 pairs: 4 on each side, 3 at the back) |
| Disc magnets **12 × 3 mm** (12 mm diameter, 3 mm thick) | 4 + 4 per cartridge (the pen cartridge also needs 4) | dock ↔ cartridge |
| **M3 × 10** socket/button head screws | 3 | dock → carriage (2 into the hex standoffs, 1 into the upper fan-shroud thread) |
| M3 set screw (or M3 × 8) + M3 nut | 1 + 1 per plunger | clamps the tool in the plunger |
| **Tiny compression spring**, OD ≤ 4.5 mm, free length 12–20 mm, e.g. the click spring from a retractable ballpoint pen | 1 (spring pen only) | pushes the swing arm down; sits in a 5 mm pocket in the arm and one in the tab. Installed length 10 mm. |
| M3 × 12 screw + M3 washer | 1 (spring pen only) | pivot: self-taps into the 2.5 mm hole in the spigot; the washer (7 mm) retains the arm, which turns on the printed spigot |
| M3 × 8 screw | 1 per arm (spring pen only) | clamps the pen in the ring (self-tapping, from the front) |
| Bonne Maman mini jars | 5 | paint (one can be rinse water) |
| Superglue or epoxy | – | if the magnets are loose in their pockets |

**Magnet polarity:** for every pair, glue one side first, then let the second magnet snap onto it before
gluing it in. A flipped magnet will push the part out of its recess.

---

## 4. Assumptions and where each number came from

"Measured" means Roland measured it on the real object. "Researched" means from a source. "Assumed"
means a reasonable default that **has not been checked**.

### The printer (Ender 5, original, not Pro/Plus/S1)

| Value | Used | Source | Confidence | What depends on it |
|---|---|---|---|---|
| Bed thickness: aluminium bed + glass | **7.5 mm** | measured | high | Bed clip opening (`bed_stack`). |
| Printable area | 220 × 220 mm | Ender 5 spec | high | Fixture footprint. |
| Physical bed plate width | 235 mm | researched (235 × 235 replacement beds for Ender 3/5); Roland's photo shows the bed is wider than the old 220 mm base | medium | The base plate is **235 mm wide** so its left/right edges line up with the bed edges, where the clips grip both. **If the bed is wider or narrower, change `plate_x`.** |
| Glass held by clips at the 4 corners | 12 mm corner notches | assumed | medium | Notches in the base plate and frame. Can be removed (`corner_r`) if not needed. |
| Stock X-carriage geometry | see below | **researched**: the Endorphin open-source Ender 5 CAD (github.com/endorphin3d/endorphin, STEP file, assembly `legacy-x-assem` = original Ender 5 printhead) | medium-high | The whole brush dock. |

**Stock carriage, as measured from that CAD** (frame: X along the gantry, Y up, Z out of the plate's front):
- Steel plate **2.5 mm** thick, flat front face, about 89 × 63.5 mm.
- **Hotend:** 2 × M3 threaded holes, **14.0 mm apart, side by side**, on round bosses 5.3 mm across and
  **4.5 mm tall**. The heatsink sat on these bosses.
- **Fan shroud:** 2 × M3 threaded holes in the flat face, 18 mm apart horizontally and 18 mm vertically.
- **Wheel bolts:** 3 × M5 button heads stick out 3.3 mm (top two) and 4.3 mm (lower eccentric one, with
  washer).
- **Nozzle tip:** 6 mm in front of the boss tops, **9 mm below the plate's bottom edge**, centred
  7 mm from each hotend hole.
- **Checked against Roland's photos of his own carriage** (27 Oct 2026; in `images/carriage_photo_*.jpg`),
  using the two top wheel bolts (40 mm apart in the CAD) as the scale. The hex standoffs (14 mm apart),
  the small fan-shroud holes and the top bolts all land within ~1 mm of the CAD positions. The real
  carriage differs from the CAD in two ways, which caused problems with the first printed dock:
  - The "bosses" are really **black hex standoffs** (M3 female). Their height and size aren't measured:
    the dock's sockets fit standoffs up to **7.5 mm tall and 5–5.5 mm across flats**.
  - The **bottom eccentric wheel bolt has a nut and protruding bolt end on the front**, much bigger than
    the CAD's bolt head. Its centre is about (−15.5, 12–19) mm from the brush axis / plate bottom. The
    dock and cartridge have an open notch there (x < −6.5 mm, z < 29 mm), so any length fits.
  - **Brass belt-end clamps** stick out at both plate edges, about 43 mm left and 34 mm right of the
    brush axis, at ~32 mm height. The narrowed dock clears them by > 15 mm.
- The Fusion reference body "Ender 5 carriage (reference)" includes these (bolt + nut modelled 12 mm
  long, belt clamps 8 mm). The interference check is clean.

### The card

| Value | Used | Source | Confidence |
|---|---|---|---|
| Card size | A5 **landscape**: 210 mm along X × 148 mm along Y, painted on directly | Roland asked for "an A5 card", then turned the layout so the card is landscape and the jars are at the front (28 Oct 2026 photo) | high (but see note) |
| Card thickness | 0.35 mm (≈ 300 gsm) | assumed | medium. Sets how far the frame's lip presses (`card_t`, `lip_h`). |

Note: we assumed the A5 card face is painted. If it's an A5 sheet that folds down to A6, the design still
works; only the painted area changes.

### Paint and jars

| Value | Used | Source |
|---|---|---|
| Paint | acrylic (originally watercolour; changed) | Roland |
| Jar | Bonne Maman mini jar, **octagonal** | Roland |
| Jar base across flats | **34 mm** | measured |
| Jar top across flats | **41 mm** | measured |
| Jar height | **46.13 mm** | measured |
| Clearance around jar base in its collar | 0.8 mm (kept the same all the way up) | assumed |
| Jar side taper | **4.34°** = atan((41 − 34) / 2 / 46.13), i.e. the jar assumed to widen evenly from base to top | derived from the measurements. The collar pockets follow it (Fusion parameter `jar_draft`), so a jar can't jam part-way down. If your jars have straight sides low down, the pockets are just slightly looser near the top. |
| Jar collar height | 20 mm | Roland |
| Gap between neighbouring jar tops | 1.5 mm | assumed |

**5 jars in one row** along the front: at 41 mm tops plus 1.5 mm gaps, 5 jars need 211 mm, and 6 would
need 254 mm, more than the 235 mm bed. A second row doesn't fit in front of the landscape card (the plate
is 220 mm deep). The jars are centred on X 32.5 / 75 / 117.5 / 160 / 202.5 mm, all inside the Ender 5's
220 mm X travel. There are no separate water wells, so use one jar for rinse water.

### Brush and pen

| Value | Used | Source | Confidence |
|---|---|---|---|
| Brush handle diameter | **7 mm** | assumed | low. Measure your brushes. |
| Pen diameter | **10 mm** (`pen_d`, + 0.3 mm clearance `pen_clear`) | assumed | low. Measure the widest part of the pen that goes inside the plunger (62 mm long). |
| Pen angle | **30° from vertical, tilted sideways along the gantry (X)**, top leaning right | Roland (first 15° front/back, then "make it 30 and angle in a different axis") | high. Change `pen_tilt` and re-run `fusion_pen_cartridge.py` (the rib and the collar clearance follow), then re-export #9. The plunger doesn't change. |
| Brush stick-out below the holder | **≥ 45 mm** (set when clamping) | derived: the jars are 46 mm tall and the holder must stay above the rims | high |

### Magnets, screws, clips

| Value | Used | Confidence |
|---|---|---|
| Fixture magnets 6 × 2 mm (pockets 6.2 / 2.2 mm): assumed. Brush-holder magnets **12 × 3 mm (pockets 12.2 / 3.2 mm): chosen by Roland**. | | Adjust `magnet_d`/`magnet_t` (fixture) or `bh_mag_d`/`bh_mag_t` (brush holder) to suit the magnets you actually have. If the holder magnets change, recheck the layout (`MAGS`/`CONES` in `fusion_holder_v3.py`): the minimum wall is now 0.9 mm. |
| Clip squeeze (interference) | 0.4 mm | assumed. Tune after a test print (section 8). |
| Fit clearances (recesses 0.3 mm, cones 0.3 mm, hex sleeve 0.5 mm) | assumed for a well-tuned CORE One+ | medium |

---

## 5. Check these before printing

- [ ] **Hex standoffs:** 14.0 mm apart (confirmed from the photo), **≤ 7.5 mm tall** and **5–5.5 mm
  across flats**, so they fit the dock's sockets (`bh_sock_depth`, `bh_sock_af`). If they're taller,
  raise `bh_sock_depth`; the dock gets thicker automatically.
- [ ] **Upper fan-shroud thread** (small hole up and to the left of the standoffs) is free, for the third
  screw. If not, leave that screw out; the two standoff screws plus the sockets are enough.
- [ ] **Bed stack = 7.5 mm** (already measured) and the **bed plate is 235 mm wide**, so the base plate's
  edges line up with the bed's edges. Measure the bed width.
- [ ] **Under the bed** where the clips go (on the left and right edges, 75 mm and 145 mm from the front
  of the base plate, beside the card), the lower jaw needs about 10 mm of clear space, with no cables or thermistor in
  the way. To move them, change `clip_y1`/`clip_y2`.
- [ ] **Brush handle diameter.** Set `bh_tool_d` and re-export the plunger.
- [ ] **Magnet sizes** you actually bought.
- [ ] **Pen diameter** (if you'll use a pen cartridge). Set `pen_d` and re-export the Pen plunger and/or the Pen swing arm.
- [ ] **Spring** (spring pen): OD under 4.5 mm (e.g. from a ballpoint pen). For a bigger one, raise `spr_pocket_d` and re-run `fusion_spring_pen.py`.

---

## 6. Coordinate systems and the coordinates file

### Fixture coordinates (used in `data/fixture_coordinates.json`)
- **Origin:** front-left corner of the **base plate** (not the ears).
- **X:** to the right, along the bed. **Y:** towards the back of the printer. **Z:** up from the top of
  the glass.
- The base plate is 235 × 220 mm. Its left and right edges line up with the bed's edges, which fixes X.
  **Y depends on where you clip it:** push it against the same reference every time (e.g. its back
  edge flush with the bed's back edge). **This has not been calibrated:** jog the brush to a known point
  (e.g. the card's front-left corner, X 12.5 / Y 58.9) to find the real offset.

### What's in `fixture_coordinates.json` (all mm, fixture coordinates)

| Key | Meaning |
|---|---|
| `module_top_z` | Top surface of the card and paint modules (6.0). |
| `card_area` | The card itself (landscape): X 12.5–222.5, Y 58.9–206.9, card surface at **Z 5.0** (bottom of the 1 mm pocket). |
| `paint_window` | The opening in the hold-down frame, where the brush can actually paint: X 16.5–218.5, Y 62.9–202.9; frame top at Z 9.0. **Stay inside this.** |
| `paint_module_area` | The whole paint module (free space for jars or future inserts): X 3–232, Y 2.5–50. |
| `jars` | J1–J5, from left to right: centres X 32.5 / 75 / 117.5 / 160 / 202.5, all at Y 26.25; `floor_z` 6.0 (where the jar base sits); `rim_z` 52.13. |
| `jar_height` | 46.13 |
| `safe_travel_tip_z` | **57.1**: the brush tip must be at least this high when moving between jars and card. |
| `min_tool_stickout_below_holder` | 45 |

### Brush vs the old nozzle (needed for G-code offsets)
- **X:** same as the old nozzle (the brush axis is centred between the two hotend holes, as the nozzle was).
- **Y (front/back):** the brush axis is **28.5 mm in front of the carriage plate's face**. The stock
  nozzle was about 10.5 mm in front (6 mm in front of 4.5 mm bosses), so the brush is about **18 mm
  further forward** than the nozzle was. We assume the carriage plate faces the **front** of the
  printer, as on the stock Ender 5. **Check this on the machine.** It may cost up to about 18 mm of
  reach at the back of the card.
- **Z:** with 45 mm stick-out, the brush tip hangs about **36 mm below where the nozzle tip was**. So
  the printer's Z=0 (bed touching nozzle height) would drive the bed **through** the brush.

### The pen cartridge
The pen's axis is tilted **30° sideways, in the X (gantry) plane**, parallel to the carriage plate: the
top of the pen leans **right (+X)** and the tip points **left (−X)**. Front/back (Y) the pen is on the
same line as the brush (28.5 mm in front of the carriage plate).

Because the pen is tilted, where the tip ends up in X depends on how far you slide the pen out. In the
holder frame (x from the old nozzle position; z from the bottom edge of the carriage plate, negative =
below it):

  **pen tip x = 6 − (20 − z_tip) × tan(30°)** mm, i.e. the tip moves 0.58 mm left per mm of extra stick-out.

With the default reference pen (tip **20 mm below the carriage plate's bottom edge**, `pen_tip_below`),
the tip is at **x = −17.1 mm**: the pen tool is about **17 mm to the left of the brush**, same Y, plus
whatever Z difference you set when clamping. **Calibrate it the same way as the brush** (jog to a card
corner) rather than trusting this number. That offset costs about 17 mm of reach on one side of the card;
if it can't reach the right-hand edge, the lean can be mirrored (top leaning left) by changing the sign of
`SLEEVE_BOTTOM_X` and of the tilt in the script.

A tilted pen draws best when it's **dragged** (tip trailing the motion), which here means strokes
**to the right (+X)**. Strokes in other directions still work for felt-tips and fineliners; if a pen
skips on strokes to the left, reduce `pen_tilt`.

### The spring pen cartridge
How it works (swing arm, like a car's trailing-arm suspension):
- The pen is clamped (M3 × 8 from the front) in a **ring at the end of the Pen swing arm**.
- The arm **pivots** on a printed spigot on the cartridge's front face (8 mm in from the left of the
  brush axis, 20 mm up), held on by an M3 × 12 screw and washer. The arm swings in the plane of the
  carriage plate, so the pen tip moves up and down (along a slight arc).
- A **tiny spring** sits in two pockets, between the top of the arm and a fixed tab above it, **8 mm
  from the pivot**. The pen ring is **25 mm** from the pivot. So the spring moves only **0.32 ×** as far as
  the pen tip (8/25), which is why a ballpoint-pen spring is enough: ~6 mm of pen lift compresses it
  ~2 mm. The pen force is about 0.32 × the spring force (plus the arm's own weight).
- At rest the arm sits on a **down-stop** under it (arm horizontal), with the spring slightly
  pre-compressed (installed 10 mm). The arm can swing up ~18° (≈ 8 mm at the pen) before it touches the tab.
  CAD-checked: no collisions at rest or with the pen lifted 14°.
- Assembly: put the spring in the tab pocket, slide the arm onto the spigot under it (spring into the arm
  pocket), fit the washer and screw.

Using it: lower Z until the pen touches, then **2–3 mm further**; the spring sets the pressure.
More pressure: a stiffer spring, or move `SPRING_X` further from the pivot in the script.

Geometry (holder frame): at the default stick-out (tip **20 mm below the carriage plate**), the pen tip
is at **x = 0, y = −28.5**, i.e. **exactly under the brush position**, so the brush and this pen share
the same X/Y offset (only Z differs). Because of the 30° tilt, each extra mm of stick-out moves the tip
0.58 mm left. When the arm lifts, the tip also moves very slightly in X (< 0.5 mm for 2–3 mm of lift).
Set `spr_tilt` to 0 for a vertical pen (re-run `fusion_spring_pen.py`; the ring moves so the tip stays at x = 0).

### Very important when running
- **Home the printer with the cartridge OFF**, then snap the cartridge on. The Ender 5 homes Z by
  raising the bed, and the brush tip plus the 52 mm jars would crash.
- **Keep the hotend's thermistor plugged in.** Tie the removed hotend out of the way, or Marlin stops
  with a **MINTEMP** error. Don't heat the hotend.

---

## 7. What's not done yet

1. **Print and test-fit everything.** Check the clip grip, magnet strength and how freely the plunger
   slides. Adjust the clearances if needed.
2. **Calibrate:** find the fixture origin and the brush X/Y/Z offset relative to the printer's
   coordinates. Jog to the card corners and to each jar.
3. **Check reach:** confirm the brush reaches the whole `paint_window` and all five jars within the
   Ender 5's travel, given the ~18 mm forward offset. With the jars at the front, they're the part most
   likely to be affected.
4. **Painting G-code:** dip routine (move to a jar → lower into the paint → lift → wipe on the jar rim
   → travel at Z ≥ 57 → paint strokes), rinse routine in the water jar, and a converter from a drawing
   (SVG) to G-code.
5. **Brush pressure:** test whether the plunger's own weight gives good strokes; add M8 nuts on the
   collar if needed.
6. **Optional:** a lid for the jars so the acrylic doesn't skin over (it starts within 15–30 min; a
   drop of acrylic retarder helps).

---

## 8. How to change the design

### In Fusion (preferred)
Open **"Acrylic card painting fixture"** and go to *Modify → Change Parameters*. The useful user parameters:

| Area | Parameters |
|---|---|
| Bed and clips | `bed_stack` (7.5), `bed_w` (235), `plate_x` (235) / `plate_y` (220), `plate_t` (4.5), `clip_squeeze` (0.4: higher grips harder), `clip_w`, `clip_jaw_t`, `clip_reach_top`, `clip_reach_bottom`, `clip_y1`/`clip_y2` (clip positions, 75 / 145: keep them beside the card and away from the bed heater at the back), `clip_notch_d`/`clip_notch_l` (notches for the clip jaws) |
| Card and layout | `card_w` (210, along X), `card_h` (148, along Y), `card_clear`, `card_recess`, `card_t`, `card_x`/`card_y` (calculated), module outlines `pm_*` and `cm_*`, `frame_band_front` (5 mm frame border next to the paint area), `corner_r`/`pm_corner`/`cm_corner` (glass-clip corner cut-outs) |
| Hold-down frame | `frame_t`, `frame_overlap`, `frame_band`, `lip_h` |
| Jars | `jar_bot`, `jar_top`, `jar_h`, `jar_clear`, `jar_gap`, `collar_wall`, `collar_h` (20), `jar_draft` (calculated taper), `jar_y`, `jar_pitch`, `jar_x0` (calculated row position) |
| Magnets (fixture) | `magnet_d`, `magnet_t` |
| Module fit | `rec_d`, `rec_clear` |
| Pen cartridge (prefix `pen_`) | `pen_tilt` (30°, sideways in X), `pen_d` (10), `pen_clear` (0.3), `pen_tip_below` (20, only moves the reference pen). It reuses the `bh_` sizes for the plate, sleeve, hex, collar, magnets and cones, so it always fits the same dock. |
| Spring pen (prefix `spr_`) | `spr_tilt` (30°), `spr_pocket_d` (5: spring pockets), `spr_pocket_depth` (3), `spr_gap` (4: arm-to-tab gap at rest). Pivot, spring and arm positions are constants at the top of `fusion_spring_pen.py` (`PIV`, `SPRING_X`, `TAB_X`, `STOP_X`, `RING_OD`). Uses `pen_d`/`pen_clear` for the pen bore. |
| Brush holder (prefix `bh_`) | `bh_tool_d` (brush/pen diameter), `bh_tool_d_725` / `bh_tool_d_105` (bores of the 7.25 and 10.5 mm brush plungers), `bh_tool_clear`, `bh_stickout` (only moves the reference brush), `bh_mag_d`/`bh_mag_t`, `bh_hex_af`/`bh_hex_clear`, `bh_cone_*`, `bh_dock_*` (`bh_dock_t` = `bh_sock_depth` + `bh_floor`), `bh_sock_af`/`bh_sock_depth` (standoff sockets), `bh_notch_right`/`bh_notch_h` (bottom-bolt notch), `bh_relief_depth`, `bh_head_depth`, `bh_label_depth` |

Things that are **not** parameters (they need a script change):
- The number of jars (5), and the magnet positions in the fixture (`NJ`, `FR_MAGS`, `CM_MAGS`, `PM_MAGS` in `cad-scripts/fusion_fixture_v2.py`).
- The positions of the carriage standoffs, screw hole and bolt relief (fixed to the Ender 5 geometry
  above: `HOT`, `SHROUD_USED`, `HEAD_TR` in `cad-scripts/fusion_holder_v3.py`).
- The magnet and cone layout on the dock (`MAGS`, `CONES`), arranged to avoid the notch.

To export a part: right-click its component, then *Save as Mesh* (STL or 3MF).

**Ready-made plungers:** besides the 7 mm **Plunger** there are **"Plunger 7.25 mm brush"** and **"Plunger 10.5 mm brush"** (independent copies of the Plunger with their own bore parameters `bh_tool_d_725` / `bh_tool_d_105`; shown parked 6 and 12 mm in front of the original).

**A new tool:** set `bh_tool_d` to the handle diameter, export the **Plunger**, then print one plunger
plus one cartridge per tool.

### Scripts (`cad-scripts/`)
The Fusion scripts rebuild parts of the design from scratch. Run them inside Fusion (*Utilities → Scripts*)
with "Acrylic card painting fixture" open. Each one deletes and recreates its own components, so
hand-made edits to those components are lost.

| Script | Makes | Notes |
|---|---|---|
| `fusion_fixture_v2.py` | **current**: base plate, card module, paint module, hold-down frame (layout v2b). It also moves the clips and places the brush holder over jar 1, runs an interference check and prints the coordinates. | Layout parameters at the top (`PARAMS`), magnet positions further down. |
| `clip75.py` | bed clip as an STL, in Python (`pip install manifold3d trimesh numpy`) | `bed_stack`, `plate_t`, `squeeze`. The clip in Fusion is the same shape. |
| `step_extract.py` / `step_children.py` | pull named parts (and the individual carriage hardware) out of the Endorphin STEP file; run them from inside a `stock/` folder: `python3 ../step_children.py endorphin.step` | needs `pip install cadquery-ocp` and the STEP file from github.com/endorphin3d/endorphin (`CAD/endorphin.step`) |
| `fusion_holder_v3.py` | **current**: brush dock (v3), cartridge, plunger, reference brush and reference carriage, plus an interference check. | The "BACK" engraving sometimes fails on the first build; delete that one extrude and recreate it (cut 0.6 mm into the back face). |
| `fusion_pen_cartridge.py` | **current**: the alternative tilted **Pen cartridge**, **Pen plunger** and **Pen (reference)**. Leaves the brush parts untouched. Places the set on the dock, runs an interference check against the dock and carriage, prints the pen tip position, then parks the set 80 mm to the right. | Run it after `fusion_holder_v3.py` (it needs the `bh_` parameters, the dock and the reference carriage). `SLEEVE_BOTTOM_X` (6) / `SLEEVE_BOTTOM_Z` (20) set where the bottom of the tilted sleeve sits; `RIB_W` (14) the rib joining it to the plate. |
| `fusion_spring_pen.py` | **current**: the **swing-arm spring pen** (Spring pen cartridge, Pen swing arm, plus reference spring and pen). Leaves the other tools untouched. Interference check in the mounted position, then parks the set 160 mm to the right. | Run after `fusion_holder_v3.py`. `old/fusion_spring_pen_v1_slider.py` is the earlier sliding version. |
| `old/` | superseded scripts for the first (portrait) layout and the v2 dock | kept for reference only |

---

## 9. Design decisions and history

In order, so you can see why things are the way they are:

1. **First version:** one-piece watercolour fixture for an A6 card, with half-pan paint holders, water
   wells and a sponge.
2. **Printer for parts:** the Prusa CORE One+ (250 × 220 × 270 mm), so no part needed splitting.
3. **Paint:** switched to **acrylic**, so the half-pans became round paint wells.
4. **Card:** switched to **A5 portrait**, and the sponge was removed to make room. The fixture became
   the full 220 × 220 bed.
5. **Card hold-down:** recess plus a magnetic frame. This was chosen over tape or adhesive because cards
   are swapped often, and the frame also gives a clean white border.
6. **Holding the fixture to the bed:** clamp ears on the base plate, first with binder clips, then
   **printed C-clips** that grip ear + glass + aluminium bed. The clip opening was corrected as
   measurements came in. The final value is **bed 7.5 mm + ear 4.5 mm**.
7. **Modular:** split into base plate + card module + paint module, located by recesses and held by
   magnets, so either module can be swapped without losing calibration.
8. **Jars:** the printed paint wells and water wells were replaced by **4 Bonne Maman mini jars** in
   octagonal collars (Roland's choice of layout "C: jars only"). The collars were later raised from 6 mm to
   **20 mm**. Because the jar widens towards the top, the pockets and collar walls were tapered at the
   jar's angle (4.34°), so the jar still sits fully down.
9. **Brush holder:** a magnetic **quick-swap cartridge** system with a **gravity-floating plunger**,
   chosen for easy tool changes, constant gentle pressure and crash tolerance. It was then **refitted to
   the real stock Ender 5 carriage**, using geometry extracted from the open-source Endorphin CAD:
   mounted on the hotend bosses plus the fan-shroud holes, with reliefs for the wheel-bolt heads, and the
   brush on the old nozzle's X position.
10. **Dock v3 (after the first test fit, 27 Oct 2026):** Roland mounted the printed dock and sent photos.
    The bottom eccentric bolt (with a nut on the front) was much bigger than in the CAD, the belt clamps
    at the plate edges got in the way, and the hex standoffs could be used to locate the part. Changes:
    hex sockets over the standoffs (back now flat on the plate), an open lower-left notch through dock
    and cartridge, the dock narrowed to clear the belt clamps, the left fan-shroud screw dropped (3 screws
    now), the magnets and cones moved away from the notch, and **FRONT/BACK** engraved. The brush moved
    3 mm further forward as a result.
11. **Bigger holder magnets (27 Oct 2026):** the dock ↔ cartridge magnets changed from 10 × 3 mm to
    **12 × 3 mm** (Roland's choice). The 4 magnets and 2 cones were re-laid out at (1, 11), (15, 11),
    (15, 47), (−17, 36) and (8, 25), (−2, 51) mm (x from the brush axis, z from the plate bottom), keeping
    ≥ 0.9 mm walls to the notch, screw counterbores and edges. The dock and cartridge became 48 mm wide
    (24 mm each side), still > 6 mm clear of the right belt clamp.
12. **Layout v2 (28 Oct 2026):** Roland test-placed the printed fixture and turned it 90°, so the jars run
    along the **front** and the card is **landscape** behind them, to keep the printhead from hitting the
    paint area. The design followed: the card is still A5 but now landscape (210 × 148 mm). The base plate
    is **235 mm wide** (the bed's width) and the clips grip its left/right edges directly, so the ears
    are gone. The modules and frame have notches where the clip jaws sit. The wider front row fits
    **5 jars** instead of 4, and the frame's lift tab moved to the back.
13. **Layout v2b (28 Oct 2026):** at Roland's request, all four clips moved **beside the card** (Y 75 and
    195), so the paint module has no clip notches. To make the paint module as large as possible for
    future use, the frame's front border was narrowed to 5 mm (its front magnets moved to the sides) and
    the module grew to **229 × 47.5 mm**.
14. **Back clips moved forward (28 Oct 2026):** the back pair of clips (Y 195) hit the **bed heater**
    under the back of the bed, so they moved 50 mm forward to **Y 145**. The side frame magnets moved to
    Y 60.5 / 100 / 170 / 195 and the card-module magnets to Y 120 / 182, to stay clear of the new notches.
15. **Pen cartridge (29 Oct 2026):** Roland asked for an alternative cartridge that holds a **pen at a
    small angle**, with the original brush cartridge kept. Added **Pen cartridge** + **Pen plunger** (10 mm
    pen) as new components: same back plate, magnets, cones and bolt notch as the brush cartridge, so it
    snaps onto the same dock; the hex sleeve is tilted **15°** in the front/back plane (top away from the
    carriage), set 4 mm further from the plate so the pen and plunger clear the dock ledge, and joined to
    the plate by a rib that stays out of the bolt notch. The plunger uses the same hex, so either plunger
    fits either cartridge. Interference check clean; Fusion version v24.
16. **Pen at 30°, tilted sideways (29 Oct 2026):** Roland asked for **30°** and a **different axis**. The
    sleeve now tilts in the **X (gantry) plane**, parallel to the carriage plate (top leans right), on the
    same Y line as the brush, joined to the plate by a 14 mm rib along its length. The collar overlapped
    the plate's top-right corner by 1 mm, so a clearance channel (24 + 1 mm) is cut there along the axis,
    which also lets the plunger lift. The pen tip ends up about 17 mm left of the brush. Interference check
    clean.
17. **Spring-loaded pen cartridge (29 Oct 2026):** Roland asked for a third design: the same pen in a
    **smaller holder pushed down by a spring**. Added as separate components (the brush and tilted-pen
    tools stay): a cartridge with a short hex guide and a spine, a small hex **carrier** (14 mm hex instead
    of the 16 mm plunger, 44 mm long instead of 62, 20 mm collar instead of 24), a compression spring
    (OD ≤ 18, ID ≥ 13, ~25 mm free) and a screw-on **Spring cap**. The cap is a separate part so the carrier
    can be dropped in from the top. Kept the 30° sideways tilt from entry 16 (parameter `spr_tilt`, 0 =
    vertical). Interference check clean apart from the intended collar-on-guide contact.
18. **Spring pen v2: swing arm (29 Oct 2026):** Roland asked to move the pen a bit, use a **tiny spring**,
    and have the pen **pivot about a point on the holder** so the spring pushes it down like a car wheel.
    The sliding carrier/cap design (entry 17) was replaced (its STLs are in `prints/old_spring_pen_v1/`):
    the pen is now in a ring on a 25 mm arm that pivots on a printed spigot + M3 screw; a ballpoint-pen
    spring 8 mm from the pivot pushes it down onto a stop (motion ratio 0.32). "Move it a bit" was read
    as: put the pen tip under the brush position (x 0, y −28.5) instead of 16 mm left and 8.5 mm forward.
    Both parts print flat on their backs without supports. Interference check clean (at rest and lifted).
19. **Plungers for two more brushes (31 Oct 2026):** Roland measured brush handles of **7.25 mm** and
    **10.5 mm**. Added two copies of the original Plunger (same hex, collar, length and M3 clamp), with bores
    7.25 + 0.3 and 10.5 + 0.3 mm. On the 10.5 mm one the nut slot moved 1.75 mm outwards (1.65 mm wall to
    the bore, 2.15 mm to the outside). Exported as `08b_…` and `08c_…`. The 7 mm Plunger is unchanged.
