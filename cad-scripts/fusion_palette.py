import adsk.core, adsk.fusion, math, os

# Palette module (drop-in alternative to the jar "Paint module") + magnetic "Palette frame".
# A throw-away sticker (palette paper / label paper, 205 x 43.5 mm) goes in a 0.3 mm pocket on the module.
# The frame snaps on with 4 magnets and divides the sticker into 6 colour cells; a round wipe bar along the back
# with a discard lane behind it lets the brush scrape off excess paint. Fixture coordinates (mm): origin = base
# plate front-left corner, X right, Y towards the back, Z up from the glass.
vi = adsk.core.ValueInput.createByString
OPS = adsk.fusion.FeatureOperations
POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
PARAMS = [
    ("pal_frame_t", "4 mm", "Palette frame thickness (= depth of the colour cells)"),
    ("pal_sticker_depth", "0.3 mm", "Depth of the sticker pocket in the palette module"),
    ("pal_bar_d", "4 mm", "Diameter of the round wipe bar on the palette frame"),
]
STICKER = (15.0, 4.5, 220.0, 48.0)              # x0, y0, x1, y1 (205 x 43.5), clear of the front corner cut-outs
N_CELLS, WALL = 6, 3.0
CELL_X0, CELL_X1 = 17.0, 218.0
CELL_Y = (7.0, 32.0)
LANE_Y = (38.0, 46.0)
BAR_Y = 35.0
FRAME_MAGS = [(8.5, 24.0), (8.5, 42.0), (226.5, 24.0), (226.5, 42.0)]
TAB = (107.5, -2.0, 127.5, 3.5)
TAB_T = 2.0
PEEL = (117.5, 4.5, 6.0)                          # finger/nail notch to peel the sticker (x, y, r)
PARK_DY = -7.0                                    # cm: parked 70 mm in front of the fixture after the check
NAMES = ("Palette module", "Palette frame")


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc.name.startswith("Acrylic card painting fixture"):
        raise Exception("Wrong document " + doc.name)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name in NAMES:
            o.deleteMe()
    up = design.userParameters
    for n, e, c in PARAMS:
        p = up.itemByName(n)
        if p is None:
            up.add(n, vi(e), "mm", c)
        else:
            p.expression = e
            p.comment = c
    V = {p.name: p.value * 10.0 for p in up if p.unit != "deg"}
    num = lambda e: float(eval(e.replace(" mm", ""), {"atan": math.atan}, V))
    MZ, BT = V["mod_z"], V["base_t"]
    TOP = MZ + BT
    FT = V["pal_frame_t"]
    PX = V["plate_x"]
    PMX0, PMY0, PMX1, PMY1, PMC = V["pm_x0"], V["pm_y0"], V["pm_x1"], V["pm_y1"], V["pm_corner"]
    JX0, JP, JY = V["jar_x0"], V["jar_pitch"], V["jar_y"]
    MOD_MAGS = [((JX0 + JX0 + JP) / 2, JY), (PX / 2, JY), ((JX0 + 3 * JP + JX0 + 4 * JP) / 2, JY)]

    class Part:
        def __init__(self, name):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = name
            self.occ, self.c, self.body = occ, occ.component, None

        def plane(self, base, mm, name):
            pi = self.c.constructionPlanes.createInput()
            pi.setByOffset(base, vi("%.4f mm" % mm))
            pl = self.c.constructionPlanes.add(pi)
            pl.name = name
            pl.isLightBulbOn = False
            return pl

        def xy(self, z, name):
            return self.plane(self.c.xYConstructionPlane, z, name)

        def yz(self, x, name):
            n = self.c.yZConstructionPlane.geometry.normal
            return self.plane(self.c.yZConstructionPlane, x if n.x > 0 else -x, name)

        def sk(self, pl, name):
            s = self.c.sketches.add(pl)
            s.name = name
            return s

    def sp(s, x, y, z):
        p = s.modelToSketchSpace(adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0))
        if abs(p.z) > 0.01:
            raise Exception("point off sketch " + s.name)
        p.z = 0.0
        return p

    def rect(s, x0, y0, x1, y1, z):
        s.sketchCurves.sketchLines.addTwoPointRectangle(sp(s, x0, y0, z), sp(s, x1, y1, z))

    def circle(s, x, y, z, d):
        s.sketchCurves.sketchCircles.addByCenterRadius(sp(s, x, y, z), d / 20.0)

    def up_dir(s, positive=True):
        n = s.xDirection.crossProduct(s.yDirection)
        along = n.z > 0 if abs(n.z) > 0.5 else n.x > 0
        return (POS if along else NEG) if positive else (NEG if along else POS)

    def ext(part, s, op, dist, direction, name, pick=None):
        col = adsk.core.ObjectCollection.create()
        profs = [p for p in s.profiles]
        if pick:
            profs = pick(profs)
        for p in profs:
            col.add(p)
        ef = part.c.features.extrudeFeatures
        inp = ef.createInput(col, op)
        inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(vi(dist)), direction)
        if op != OPS.NewBodyFeatureOperation:
            inp.participantBodies = [part.body]
        f = ef.add(inp)
        f.name = name
        if op == OPS.NewBodyFeatureOperation:
            part.body = f.bodies.item(0)
        s.isLightBulbOn = False
        return f

    largest = lambda ps: [max(ps, key=lambda p: p.areaProperties().area)]

    # ================= PALETTE MODULE (same footprint, height and magnets as the Paint module) =================
    pm = Part("Palette module")
    bot = pm.xy(MZ, "Module bottom")
    s = pm.sk(bot, "Palette module outline")
    rect(s, PMX0, PMY0, PMX1, PMY1, MZ)
    ext(pm, s, OPS.NewBodyFeatureOperation, "base_t", up_dir(s), "Palette module plate")
    pm.body.name = "Palette module"
    s = pm.sk(bot, "Corner cut-outs")
    rect(s, PMX0 - 1, PMY0 - 1, PMC, PMC, MZ)
    rect(s, PX - PMC, PMY0 - 1, PMX1 + 1, PMC, MZ)
    ext(pm, s, OPS.CutFeatureOperation, "base_t", up_dir(s), "Corner cut-outs (glass clips)")
    s = pm.sk(bot, "Module magnets")
    for x, y in MOD_MAGS:
        circle(s, x, y, MZ, V["magnet_d"])
    ext(pm, s, OPS.CutFeatureOperation, "magnet_t", up_dir(s), "Module magnet pockets (same as Paint module)")
    top = pm.xy(TOP, "Module top")
    s = pm.sk(top, "Sticker pocket")
    rect(s, *STICKER, TOP)
    ext(pm, s, OPS.CutFeatureOperation, "pal_sticker_depth", up_dir(s, False), "Sticker pocket")
    s = pm.sk(top, "Peel notch")
    circle(s, PEEL[0], PEEL[1], TOP, 2 * PEEL[2])
    ext(pm, s, OPS.CutFeatureOperation, "1 mm", up_dir(s, False), "Peel notch")
    s = pm.sk(top, "Frame magnets")
    for x, y in FRAME_MAGS:
        circle(s, x, y, TOP, V["magnet_d"])
    ext(pm, s, OPS.CutFeatureOperation, "magnet_t", up_dir(s, False), "Frame magnet pockets (top)")

    # ================= PALETTE FRAME =================
    pf = Part("Palette frame")
    fb = pf.xy(TOP, "Frame bottom")
    s = pf.sk(fb, "Frame outline")
    rect(s, PMX0 + 0.5, PMY0 + 0.5, PMX1 - 0.5, PMY1 - 0.5, TOP)
    ext(pf, s, OPS.NewBodyFeatureOperation, "pal_frame_t", up_dir(s), "Frame plate")
    pf.body.name = "Palette frame"
    s = pf.sk(fb, "Frame corner cut-outs")
    rect(s, PMX0 - 1, PMY0 - 1, PMC + 0.5, PMC + 0.5, TOP)
    rect(s, PX - PMC - 0.5, PMY0 - 1, PMX1 + 1, PMC + 0.5, TOP)
    ext(pf, s, OPS.CutFeatureOperation, "pal_frame_t", up_dir(s), "Frame corner cut-outs")
    s = pf.sk(fb, "Lift tab")
    rect(s, *TAB, TOP)
    ext(pf, s, OPS.JoinFeatureOperation, "%.2f mm" % TAB_T, up_dir(s), "Lift tab")
    cw = (CELL_X1 - CELL_X0 - (N_CELLS - 1) * WALL) / N_CELLS
    cells = []
    s = pf.sk(fb, "Cells and discard lane")
    for i in range(N_CELLS):
        x0 = CELL_X0 + i * (cw + WALL)
        rect(s, x0, CELL_Y[0], x0 + cw, CELL_Y[1], TOP)
        cells.append((round(x0 + cw / 2, 2), round((CELL_Y[0] + CELL_Y[1]) / 2, 2)))
    rect(s, CELL_X0, LANE_Y[0], CELL_X1, LANE_Y[1], TOP)
    ext(pf, s, OPS.CutFeatureOperation, "pal_frame_t", up_dir(s), "Colour cells + discard lane")
    s = pf.sk(fb, "Frame magnets")
    for x, y in FRAME_MAGS:
        circle(s, x, y, TOP, V["magnet_d"])
    ext(pf, s, OPS.CutFeatureOperation, "magnet_t", up_dir(s), "Frame magnet pockets (bottom)")
    bz = TOP + FT + V["pal_bar_d"] / 2 - 0.6           # rod sunk 0.6 mm into the frame so it joins
    s = pf.sk(pf.yz(CELL_X0, "Bar start"), "Wipe bar")
    circle(s, CELL_X0, BAR_Y, bz, V["pal_bar_d"])
    ext(pf, s, OPS.JoinFeatureOperation, "%.2f mm" % (CELL_X1 - CELL_X0), up_dir(s), "Wipe bar")

    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    design.computeAll()

    # ================= checks =================
    occ = {}
    for o in root.occurrences:
        occ.setdefault(o.component.name, []).append(o)
    col = adsk.core.ObjectCollection.create()
    for nme in ("Base plate", "Card module", "Hold-down frame", "Bed clip") + NAMES:
        for o in occ.get(nme, []):
            col.add(o)
    ir = design.analyzeInterference(design.createInterferenceInput(col))
    print("INTERFERENCE", [(r.entityOne.name, r.entityTwo.name, round(r.interferenceBody.volume * 1000, 3)) for r in ir])
    # footprint check against the jar Paint module: compare the bottom faces
    def bottom_area(body):
        low = min(f.boundingBox.minPoint.z for f in body.faces)
        return sum(f.area for f in body.faces if abs(f.boundingBox.maxPoint.z - low) < 1e-6 and abs(f.boundingBox.minPoint.z - low) < 1e-6)
    paint = occ["Paint module"][0].bRepBodies.item(0)
    pal = occ["Palette module"][0].bRepBodies.item(0)
    print("bottom face area cm2: paint module %.3f, palette module %.3f" % (bottom_area(paint), bottom_area(pal)))
    pb, qb = paint.boundingBox, pal.boundingBox
    print("bbox xy paint", [round(v * 10, 2) for v in (pb.minPoint.x, pb.minPoint.y, pb.maxPoint.x, pb.maxPoint.y)],
          "palette", [round(v * 10, 2) for v in (qb.minPoint.x, qb.minPoint.y, qb.maxPoint.x, qb.maxPoint.y, qb.minPoint.z, qb.maxPoint.z)])
    fbb = occ["Palette frame"][0].bRepBodies.item(0).boundingBox
    print("frame bbox", [round(v * 10, 2) for v in (fbb.minPoint.x, fbb.minPoint.y, fbb.minPoint.z, fbb.maxPoint.x, fbb.maxPoint.y, fbb.maxPoint.z)])
    tl = design.timeline
    print("UNHEALTHY", [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState])
    print("cell width %.2f, cells %s, lane x %.0f-%.0f y %.0f-%.0f, bar top z %.2f at y %.1f, cell floor z %.2f" % (
        cw, cells, CELL_X0, CELL_X1, LANE_Y[0], LANE_Y[1], bz + V["pal_bar_d"] / 2, BAR_Y, TOP - V["pal_sticker_depth"]))
    for nme in NAMES:
        o = occ[nme][0]
        m = o.transform2
        tr = m.translation
        tr.y += PARK_DY
        m.translation = tr
        o.transform2 = m
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
