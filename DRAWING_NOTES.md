# Drawing with pencils and brushes: what we learned

Notes from the first painting/drawing sessions on the Ender 5 rig (28–31 Oct 2026).
Numbers are what is in the files now. Things marked **(unverified)** are estimates nobody has measured yet.

---

## 1. Coordinates and calibration

### Two coordinate systems
- **Fixture coordinates** (`data/fixture_coordinates.json`, from the Fusion design): mm from the base
  plate's front-left corner, X right, Y towards the back, Z up from the glass. Layout **v2b**:
  landscape A5 card at the back, 5 jars in a row along the front.
  - Card surface: Z 5.0. Hold-down frame top: Z 9.0. Jar rims: Z 52.13.
  - Paint window (frame opening): X 16.5–218.5, Y 62.9–202.9. Stay inside it.
  - Jars J1–J5: X 32.5 / 75 / 117.5 / 160 / 202.5, all at Y 26.25.
- **Printer coordinates**: what G-code uses. Travel X 0–220, Y 0–220. Home (G28) is X 220 / Y 220
  (back-right). On the Ender 5, **Z up = bed down**.

### Offset: printer = fixture + offset
Stored in `data/calibration.json` and read by every generator script.

| | X | Y | Z |
|---|---|---|---|
| **Measured (brush)** | **−14.5** | **+7.1** | **+1.1** |
| Fusion-based guess | 0 | +18 | +36 |
| Old `touch_corners` guess | +5 | −10 | +10 |

- Measured on 31 Oct by jogging the brush tip onto the back-left calibration point
  (fixture X 19.5 / Y 199.9, just touching the paper) and reading `M114`: printer X 5.0, Y 207.0, Z 6.1.
- **One point was enough**: `calibrate.gcode` with these offsets hit all four corners perfectly.
- Both guesses were far off. The Y guess even had the wrong sign, which put the front touches on the
  jars. Lesson: **measure one point, never trust the CAD offset.**
- The Z offset of +1.1 means the brush tip hangs only ~1 mm below the old nozzle height, so the brush
  is clamped with about **10 mm stick-out (unverified)**, not the 45 mm in the design.
- **Pencil:** has no offset of its own yet; scripts fall back to the brush offset. If the pencil tip
  sits at a different height, run `pencil_calibrate.gcode`, jog until it just touches, read `M114`,
  and store it as `"pencil_offset"` in `calibration.json` (the pencil scripts pick it up automatically).

### Reach
- Printer X stops at 220, so with X −14.5 the right edge of the paint window (fixture 218.5) is at
  printer 204: fine. Every generator checks that each point is in reach and inside the paint window.
- With the old +18 Y guess the back of the card was out of reach; with the measured +7.1 it isn't.

---

## 2. Safety rules (learned the hard way or nearly)

1. **Homing with the tool on is fine** (Roland, 31 Oct): there's no need to take the cartridge off
   or to pause for attaching it. Home with the tool on, then **go straight back up** so the tool clears
   the frame (frame top is 9 mm above the glass) before any sideways move. This works because the
   tip only hangs ~1 mm below the old nozzle height and the plunger floats.
   *Caveat:* if the brush is re-clamped with a long stick-out (e.g. ≥ 45 mm for jar dipping), the tip
   would sit far below the nozzle height and homing Z with it on would push it into the bed. Re-check
   before homing in that case. (The current generator files still home with the cartridge off and
   use an `@pause`; that's more cautious than needed and can be simplified.)
2. **X/Y homing is safe with the tool on** if Z is lifted first: `G1 Z…` up, then `G28 X Y`.
   Used by the `*_nohome` files.
3. After `M84 X Y` (X/Y motors off at the end of every job) the head can be pushed by hand, so the
   next no-home job re-homes X/Y first.
4. **Lift before any sideways move.** Travelling at frame height dragged the brush over the frame
   and paper. Now: first approach at **20 mm above the paper**, hover between strokes always above
   the frame top (9 mm) *and* above the highest point of a stroke.
5. Jar rims are 52 mm above the glass. With ~10 mm stick-out the cartridge would hit a rim long
   before the brush reaches the paint, so **jar dipping needs ≥ 45 mm stick-out** (re-clamp, then
   re-measure Z). `calibrate_dip_each.py` refuses to go lower than the rims allow and warns.
6. Keep `python3 octo.py cancel` (or OctoPrint's Cancel) ready for every first run.
7. Don't heat anything: every file starts with `M104 S0`, `M140 S0`, `M107`.

---

## 3. Brush technique

### How pressure works
The plunger **floats**: the brush rests on the paper with only the plunger's own weight, and it lifts
if pushed. So:
- Commanding Z **below** the paper doesn't press harder; it just guarantees full plunger weight.
- **Stroke width is controlled by lifting**: full weight = wide stroke; raising Z gradually lets fewer
  bristles touch, so the stroke thins to a point.

### Brush stroke profile (current values in `tree_brush.py`)
| Setting | Value | Meaning |
|---|---|---|
| `PRESS` | 1.0 mm | start of stroke: tip commanded this far **below** the paper (full weight) |
| `HOLD_MM` | 12 mm | first part of the stroke stays at full pressure |
| `LIFT` | 7 mm | max tip height **above** the paper (smooth S-curve lift) |
| `ATTACK_MM` | 45 mm | length of the lift (slow attack); shorter strokes get the profile shrunk to fit |
| `HOVER` | 19 mm | between strokes; must be above `LIFT` |
| `APPROACH` | 20 mm | first move after homing |
| `STROKE_F` | 1200 mm/min | painting speed |

How we got there: started at −1.5 → +0.6; "don't go that far down" → −0.5; lighter → 0 / +1;
then back to −1.5 at the start with an ever higher finish: +3, +6, +11, **+16 mm**.
Then `calib_strokes.gcode` (15 strokes: max height 3/6/9/12/16 mm × attack 10/25/45 mm): Roland
liked **line 9 (9 mm, 45 mm attack)** best, and the tree now uses it with the max height lowered to 7 mm and only 1 mm pressed (old version: `tree_brush_lift16.py`). The brush
leaves the paper well before the end of the move; the tail of the stroke is the lift-off.

### Composition rules Roland asked for
- **Always paint from the middle to the edge** (start on the centre line, thick, finish thin at the edge).
- **Work from the top to the bottom** (for the sideways tree: from the tip to the base), both
  halves at each spot.
- Start each stroke **1.5 mm past the centre line** so the two halves join into a darker spine.
- **Stop short of the outline** (`EDGE_MARGIN` 6 mm): the brush tail looks better than hitting the edge.
- **Slightly curved strokes** look painted, not plotted: lean back towards the base
  (8° at the tip → 30° at the base, like drooping branches) plus a bend of ~10 mm at the end,
  with ±30 % random variation per stroke and ±3° angle jitter.
- Stroke spacing about one brush width (`PITCH` 3.5 mm).
- Tree shape that worked: one triangle (not three tiers), 176 × 126 mm, lying along the card,
  tip to the right, base **dented in by 20 mm**, shifted **12 mm right** (`SHIFT_X`).
  When we tried three tiers, the steps between tiers had to be **deep** (≈25 / 15 mm) to read.

### Paint
- Acrylic (not watercolour). It skins over in 15–30 min; a drop of retarder helps (README).
- One hand-loaded brush doesn't last 75–100 strokes: strokes fade towards the end of the job.
  Options: re-clamp for jar dipping, or add a pause every ~10 strokes to reload by hand.
- Planned dip routine (in the earlier generators, not yet tested): travel above the rims → lower into
  the jar → swirl → wipe on the rim → lift. Rinse in J1 (water) between colours. One dip per stroke
  gives a natural fade along each stroke. Dipping a second colour only on the tip gives streaky mixes.

---

## 4. Pencil technique

- **No Z curves**: constant height while drawing, tip commanded **1 mm below** the paper (the
  floating plunger keeps light even pressure), **3 mm** lift between lines, 20 mm approach.
- Speed 1200–1500 mm/min.
- `pencil_calibrate.gcode` touches the four corners **at exactly the writing height** and ends
  *down* on the back-left corner with the motors on, so you can jog and measure.
- **No-home versions** (`pencil_text_nohome.gcode`, `draw_art_nohome.gcode`) are for when the pencil
  is still attached right after a calibration or drawing run: lift, re-home X/Y, draw, park.
- **The card must not move** between jobs that add to the same drawing.

### Text
- Cursive in a single line per stroke: Hershey font `scripts` (`pip install Hershey-Fonts`).
- Its capital **G looks like a J**, so `pencil_text.py` draws its own G (open C + inward bar, same
  slant). Other letters may need the same treatment.
- Consecutive strokes that start where the last one ended are joined, so the pencil doesn't lift.
- "Gemmie is a puffin": 176 × 23 mm, 20 strokes, ~30 s.

---

## 5. Turning artwork into plotter paths (`gcode/svg2plot.py`)

- **Licences first.** Use public domain/CC0 art when possible (no credit needed). CC BY-SA art needs
  a credit line and derived work stays CC BY-SA. Credits are in `art/SOURCES.md`.
- **Two conversions:**
  - `outline` for filled/coloured art: trace the silhouette plus the boundaries between dark, light
    and orange areas.
  - `centre` for line art drawn with thick strokes: skeletonise so each line is drawn once
    (tracing both edges of a thick stroke makes double lines).
- Tricks that made the traced drawings look good:
  - **Blur the dark mask hard** (σ≈9 px at 1400 px) before splitting light/dark, or painted texture
    turns into ragged edges and blotchy islands.
  - **Drop inner boundaries that run along the silhouette** (within ~4 px), or those edges get
    drawn twice.
  - Throw away small dark islands, **except eye-sized spots in the top ~28 %** (the head), or the eyes
    disappear.
  - Simplify lightly (0.07 mm) then **round corners (Chaikin, 2 passes)**: looks hand-drawn.
  - **Pencil shading:** parallel hatching inside the dark areas, 1.3 mm apart at 58°, kept off the
    edges, with slightly varied ends and spacing. It's what makes a puffin read as black and white.
  - Drop lines shorter than 2 mm.
  - Draw the **nearest line next** (either end) to cut travel.
- `draw_art.py --place FILE:X:Y:HEIGHT[:flip]` places converted drawings on the card.

---

## 6. Design lessons

- **Line spacing ≥ brush (or pencil) line width**, or parallel lines merge into a band.
- Line length sets the time and the number of reloads: the spiral garland is ~1.6 m, the ribbon
  tree ~5.7 m.
- A cone coil (spiral garland) lying sideways must space its turns **in proportion to the loop
  depth** (`OVERLAP` 1.6, `MIN_PITCH` 8 mm), or it turns into a wavy line instead of overlapping rings.
- Landscape card: a tree lying along the long side gets ~60 % more space than an upright one.
- Always **preview offline first** (each generator writes a `*_preview.png`; `plot3d.py FILE.gcode`
  shows the brush height in 3D) before sending anything.

---

## 7. Workflow and tools

| Task | Command (in `gcode/`) |
|---|---|
| Printer status | `python3 octo.py status` |
| Home all, bed down 20 mm | `python3 octo.py home` (asks if the cartridge is off; `-no-brush` skips that) |
| Send a job (checks idle, shows summary, asks) | `python3 octo.py send FILE.gcode` |
| Regenerate and send | `python3 tree_brush.py && python3 octo.py send tree_brush.gcode` |
| Resume after the attach pause / cancel | `python3 octo.py resume` / `python3 octo.py cancel` |
| Camera snapshots | `python3 octo.py snap [N] [SEC]` → `gcode/snapshots/` |
| 3D view of a job | `python3 plot3d.py FILE.gcode` |

- The OctoPrint API key lives in `.secrets.env` (git-ignored, readable only by you).
- G-code files: `calibrate`, `calibrate_dip_each`, `garland`, `tree_brush`, `pencil_calibrate`,
  `pencil_text` (+ `_nohome`), `puffins`, `draw_art` (+ `_nohome`).
- Every job ends lifted, parked top-right (X 220 / Y 220), with the X/Y motors off and Z still on.

---

## 8. Open points

- The **camera** has been knocked and points at the side of the printer; it needs to look down at the bed.
- **Pencil offset** not measured separately yet.
- **Brush stick-out**: ~10 mm now (unverified); re-clamp to ≥ 45 mm before any jar dipping.
- **Jar dipping** and rinsing not tried on the machine yet.
- Is the base plate always clipped in the same place? If it moves, re-measure the back-left point.
- OctoPrint is running in safe mode on Python 2 (doesn't affect the jobs, but worth fixing).
