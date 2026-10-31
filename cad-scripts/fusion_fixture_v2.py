import adsk.core, adsk.fusion, math, json

# Fixture v2: landscape A5 card at the back, a row of 5 Bonne Maman jars along the front,
# base plate as wide as the Ender 5 bed (235 mm) and gripped on its left/right edges by the printed clips.
# Fixture coordinates: origin = front-left corner of the base plate, X right, Y to the back, Z up from the glass.
vi = adsk.core.ValueInput.createByString
OPS = adsk.fusion.FeatureOperations
POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
H_ = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
V_ = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
P3 = lambda x, y: adsk.core.Point3D.create(x / 10.0, y / 10.0, 0)
SK = []
NJ = 5

PARAMS = [
    ("plate_x", "235 mm", "Base plate width (X) = Ender 5 bed width, so the clips grip its edges"),
    ("plate_y", "220 mm", "Base plate depth (Y)"),
    ("card_w", "210 mm", "Card width along X (A5 landscape)"),
    ("card_h", "148 mm", "Card depth along Y (A5 landscape)"),
    ("pm_x0", "3 mm", "Paint module left edge"),
    ("pm_x1", "plate_x - 3 mm", "Paint module right edge"),
    ("pm_y0", "2.5 mm", "Paint module front edge"),
    ("pm_y1", "50 mm", "Paint module back edge (paint area kept as large as possible)"),
    ("pm_corner", "corner_r + 2 mm", "Paint module front-corner cut-outs (glass clips)"),
    ("cm_x0", "3 mm", "Card module left edge"),
    ("cm_x1", "plate_x - 3 mm", "Card module right edge"),
    ("cm_y0", "53 mm", "Card module front edge"),
    ("cm_y1", "plate_y - 2.5 mm", "Card module back edge"),
    ("cm_corner", "corner_r + 0.5 mm", "Card module back-corner cut-outs (glass clips)"),
    ("card_x", "( plate_x - card_w - 2 * card_clear ) / 2", "Card pocket left edge (centred)"),
    ("card_y", "plate_y - cm_corner - card_h - 2 * card_clear", "Card pocket front edge (back edge clears the corner cut-outs)"),
    ("clip_y1", "75 mm", "Front pair of bed clips: centre Y (beside the card, not the paint area)"),
    ("clip_y2", "195 mm", "Back pair of bed clips: centre Y (beside the card)"),
    ("frame_band_front", "5 mm", "Frame border in front of the card (narrow, to leave room for the paint area)"),
    ("clip_notch_d", "7 mm", "Notch in modules/frame where the clip jaw sits (from the side edge)"),
    ("clip_notch_l", "clip_w + 1 mm", "Length of those notches"),
    ("jar_y", "( pm_y0 + pm_y1 ) / 2", "Jar row centre Y"),
    ("jar_pitch", "jar_top + jar_gap", "Jar spacing along X"),
    ("jar_x0", "( plate_x - 4 * jar_pitch ) / 2", "First (left) jar centre X; 5 jars"),
]
OBSOLETE = ["water_x", "water_w", "rinse_x", "rinse_w", "back_y", "back_d", "sponge_x", "sponge_y", "sponge_w",
            "sponge_d", "sponge_h", "cmag_xl", "cmag_xr", "cmag_y1", "cmag_y2", "pmag_y0", "ear_w", "ear_y1", "ear_y2",
            "lift_d"]


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc.name.startswith("Acrylic card painting fixture"):
        raise Exception("Wrong document " + doc.name)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name in ("Base plate", "Card module", "Paint module", "Hold-down frame"):
            o.deleteMe()
    up = design.userParameters
    for n, e, c in PARAMS:
        p = up.itemByName(n)
        if p is None:
            up.add(n, vi(e), "mm", c)
        else:
            p.expression = e
            p.comment = c
    if up.itemByName("lift_d") is None:
        up.add("lift_d", vi("18 mm"), "mm", "Finger notch for lifting modules out")
    for n in OBSOLETE:
        p = up.itemByName(n)
        if p is not None and n != "lift_d":
            try:
                p.deleteMe()
            except Exception:
                SK.append("kept param " + n)
    V = {p.name: p.value * 10.0 for p in up}
    num = lambda e: float(eval(e.replace(" mm", ""), {}, V))

    class B:
        def __init__(self, name):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = name
            self.occ, self.c, self.body = occ, occ.component, None

        def plane(self, expr, name):
            pi = self.c.constructionPlanes.createInput()
            pi.setByOffset(self.c.xYConstructionPlane, vi(expr))
            pl = self.c.constructionPlanes.add(pi)
            pl.name = name
            pl.isLightBulbOn = False
            return pl

        def sk(self, plane, name):
            s = self.c.sketches.add(plane if plane is not None else self.c.xYConstructionPlane)
            s.name = name
            return s

        def ext(self, s, op, expr, direction=POS, name=None, taper=None):
            col = adsk.core.ObjectCollection.create()
            for p in s.profiles:
                col.add(p)
            ef = self.c.features.extrudeFeatures
            inp = ef.createInput(col, op)
            de = adsk.fusion.DistanceExtentDefinition.create(vi(expr))
            if taper:
                inp.setOneSideExtent(de, direction, vi(taper))
            else:
                inp.setOneSideExtent(de, direction)
            if op != OPS.NewBodyFeatureOperation:
                inp.participantBodies = [self.body]
            f = ef.add(inp)
            if name:
                f.name = name
            if op == OPS.NewBodyFeatureOperation:
                self.body = f.bodies.item(0)
            s.isLightBulbOn = False
            return f

    def dim(s, a, b, o, e, tx, ty):
        if abs(num(e)) < 1e-6:
            return
        try:
            d = s.sketchDimensions.addDistanceDimension(a, b, o, P3(tx, ty))
            d.parameter.expression = e
        except Exception:
            SK.append(s.name + ": " + e)

    def rect(s, xe, ye, we, he):
        x, y, w, h = num(xe), num(ye), num(we), num(he)
        lines = s.sketchCurves.sketchLines.addTwoPointRectangle(P3(x, y), P3(x + w, y + h))
        pts = {}
        for ln in lines:
            for p in (ln.startSketchPoint, ln.endSketchPoint):
                g = p.geometry
                pts[(round(g.x * 10, 3), round(g.y * 10, 3))] = p
        k = lambda a, b: pts[(round(a, 3), round(b, 3))]
        p00, p10, p01 = k(x, y), k(x + w, y), k(x, y + h)
        o = s.originPoint
        dim(s, p00, p10, H_, we, x + w / 2, y - 3)
        dim(s, p00, p01, V_, he, x - 3, y + h / 2)
        dim(s, o, p00, H_, xe, x / 2, y - 6)
        dim(s, o, p00, V_, ye, x - 6, y / 2)

    def circle(s, cxe, cye, de):
        cx, cy, d = num(cxe), num(cye), num(de)
        c = s.sketchCurves.sketchCircles.addByCenterRadius(P3(cx, cy), d / 20.0)
        try:
            dd = s.sketchDimensions.addDiameterDimension(c, P3(cx + d, cy + d))
            dd.parameter.expression = de
        except Exception:
            SK.append(s.name + ": dia")
        o = s.originPoint
        dim(s, o, c.centerSketchPoint, H_, cxe, cx / 2, cy + 2)
        dim(s, o, c.centerSketchPoint, V_, cye, cx + 2, cy / 2)

    def octo(s, cxe, cye, afe):
        cx, cy, af = num(cxe), num(cye), num(afe)
        cp = s.sketchPoints.add(P3(cx, cy))
        lines = s.sketchCurves.sketchLines.addScribedPolygon(cp, 8, 0, af / 20.0, False)
        def ang(l):
            a, b = l.startSketchPoint.geometry, l.endSketchPoint.geometry
            return math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 180
        horiz = [l for l in lines if abs(ang(l)) < 1 or abs(ang(l) - 180) < 1]
        try:
            s.geometricConstraints.addHorizontal(horiz[0])
            d = s.sketchDimensions.addOffsetDimension(horiz[0], horiz[1], P3(cx + af, cy))
            d.parameter.expression = afe
        except Exception:
            SK.append(s.name + ": AF")
        o = s.originPoint
        dim(s, o, cp, H_, cxe, cx / 2, cy + 2)
        dim(s, o, cp, V_, cye, cx + 2, cy / 2)

    CC = "card_clear"
    PKW, PKH = "card_w + 2 * card_clear", "card_h + 2 * card_clear"
    JX = ["jar_x0 + %d * jar_pitch" % i for i in range(NJ)]
    SIDE_FR = ("60.5 mm", "95 mm", "135 mm", "175 mm")      # kept clear of the clip notches
    FR_MAGS = ([("card_x - 4 mm", y) for y in SIDE_FR] +
               [("card_x + %s + 4 mm" % PKW, y) for y in SIDE_FR] +
               [(x, "card_y + %s + 4 mm" % PKH) for x in ("60 mm", "plate_x / 2", "plate_x - 60 mm")])
    CM_MAGS = [(x, y) for x in ("7.5 mm", "plate_x - 7.5 mm") for y in ("115 mm", "155 mm")]
    PM_MAGS = [("( jar_x0 + jar_x0 + jar_pitch ) / 2", "jar_y"), ("plate_x / 2", "jar_y"),
               ("( jar_x0 + 3 * jar_pitch + jar_x0 + 4 * jar_pitch ) / 2", "jar_y")]

    def clip_notches(b, s, y_expr):
        for xe in ("0 mm", "plate_x - clip_notch_d"):
            rect(s, xe, "%s - clip_notch_l / 2" % y_expr, "clip_notch_d", "clip_notch_l")

    # ================= BASE PLATE =================
    b = B("Base plate")
    s = b.sk(None, "Base outline")
    rect(s, "0 mm", "0 mm", "plate_x", "plate_y")
    b.ext(s, OPS.NewBodyFeatureOperation, "plate_t", name="Base plate")
    b.body.name = "Base plate"
    s = b.sk(None, "Corner notches")
    for xe in ("0 mm", "plate_x - corner_r"):
        for ye in ("0 mm", "plate_y - corner_r"):
            rect(s, xe, ye, "corner_r", "corner_r")
    b.ext(s, OPS.CutFeatureOperation, "plate_t", name="Corner notches (glass clips)")
    btop = b.plane("plate_t", "Base top")
    bfloor = b.plane("mod_z", "Recess floor")
    s = b.sk(btop, "Module recesses")
    rect(s, "pm_x0 - rec_clear", "pm_y0 - rec_clear", "pm_x1 - pm_x0 + 2 * rec_clear", "pm_y1 - pm_y0 + 2 * rec_clear")
    rect(s, "cm_x0 - rec_clear", "cm_y0 - rec_clear", "cm_x1 - cm_x0 + 2 * rec_clear", "cm_y1 - cm_y0 + 2 * rec_clear")
    b.ext(s, OPS.CutFeatureOperation, "rec_d", NEG, name="Module recesses")
    s = b.sk(btop, "Lift notches")
    circle(s, "plate_x / 2", "pm_y0 - rec_clear", "lift_d")
    circle(s, "plate_x / 2", "cm_y1 + rec_clear", "lift_d")
    b.ext(s, OPS.CutFeatureOperation, "rec_d", NEG, name="Lift notches")
    s = b.sk(bfloor, "Base magnets")
    for xe, ye in CM_MAGS + PM_MAGS:
        circle(s, xe, ye, "magnet_d")
    b.ext(s, OPS.CutFeatureOperation, "magnet_t", NEG, name="Base magnet pockets")

    # ================= PAINT MODULE =================
    p = B("Paint module")
    pbot = p.plane("mod_z", "Paint module underside")
    ptop = p.plane("mod_z + base_t", "Paint module top")
    s = p.sk(pbot, "Paint module outline")
    rect(s, "pm_x0", "pm_y0", "pm_x1 - pm_x0", "pm_y1 - pm_y0")
    p.ext(s, OPS.NewBodyFeatureOperation, "base_t", name="Paint module plate")
    p.body.name = "Paint module"
    s = p.sk(ptop, "Jar collars")
    for xe in JX:
        octo(s, xe, "jar_y", "jar_bot + jar_clear + 2 * collar_wall")
    p.ext(s, OPS.JoinFeatureOperation, "collar_h", name="Jar collars", taper="jar_draft")
    s = p.sk(ptop, "Jar pockets")
    for xe in JX:
        octo(s, xe, "jar_y", "jar_bot + jar_clear")
    p.ext(s, OPS.CutFeatureOperation, "collar_h + 1 mm", name="Jar pockets", taper="jar_draft")
    tp = p.plane("mod_z + base_t + 2 mm", "Thumb slot floor")
    s = p.sk(tp, "Thumb slots")
    for xe in JX:
        rect(s, xe + " - 6 mm", "jar_y - ( jar_bot + jar_clear ) / 2 - 6 mm", "12 mm", "8 mm")
    p.ext(s, OPS.CutFeatureOperation, "collar_h", name="Thumb slots")
    s = p.sk(pbot, "Corner cut-outs")
    for xe in ("0 mm", "plate_x - pm_corner"):
        rect(s, xe, "0 mm", "pm_corner", "pm_corner")
    p.ext(s, OPS.CutFeatureOperation, "base_t", name="Corner cut-outs")
    s = p.sk(pbot, "Module magnets")
    for xe, ye in PM_MAGS:
        circle(s, xe, ye, "magnet_d")
    p.ext(s, OPS.CutFeatureOperation, "magnet_t", POS, name="Module magnet pockets")

    # ================= CARD MODULE =================
    c = B("Card module")
    cbot = c.plane("mod_z", "Card module underside")
    ctop = c.plane("mod_z + base_t", "Card module top")
    s = c.sk(cbot, "Card module outline")
    rect(s, "cm_x0", "cm_y0", "cm_x1 - cm_x0", "cm_y1 - cm_y0")
    c.ext(s, OPS.NewBodyFeatureOperation, "base_t", name="Card module plate")
    c.body.name = "Card module"
    s = c.sk(cbot, "Corner and clip cut-outs")
    for xe in ("0 mm", "plate_x - cm_corner"):
        rect(s, xe, "plate_y - cm_corner", "cm_corner", "cm_corner")
    clip_notches(c, s, "clip_y1")
    clip_notches(c, s, "clip_y2")
    c.ext(s, OPS.CutFeatureOperation, "base_t", name="Corner + clip cut-outs")
    s = c.sk(ctop, "Card pocket")
    rect(s, "card_x", "card_y", PKW, PKH)
    circle(s, "card_x + card_clear + card_w / 2", "card_y", "notch_d")
    c.ext(s, OPS.CutFeatureOperation, "card_recess", NEG, name="Card pocket (A5 landscape)")
    s = c.sk(ctop, "Frame magnets")
    for xe, ye in FR_MAGS:
        circle(s, xe, ye, "magnet_d")
    c.ext(s, OPS.CutFeatureOperation, "magnet_t", NEG, name="Frame magnet pockets")
    s = c.sk(cbot, "Module magnets")
    for xe, ye in CM_MAGS:
        circle(s, xe, ye, "magnet_d")
    c.ext(s, OPS.CutFeatureOperation, "magnet_t", POS, name="Module magnet pockets")

    # ================= HOLD-DOWN FRAME =================
    f = B("Hold-down frame")
    seat = f.plane("mod_z + base_t", "Frame seat (card module top)")
    lipb = f.plane("mod_z + base_t - lip_h", "Lip bottom")
    s = f.sk(seat, "Frame outline")
    rect(s, "card_x - frame_band", "card_y - frame_band_front", PKW + " + 2 * frame_band", PKH + " + frame_band + frame_band_front")
    f.ext(s, OPS.NewBodyFeatureOperation, "frame_t", name="Frame plate")
    f.body.name = "Hold-down frame"
    s = f.sk(seat, "Lift tab (back)")
    rect(s, "card_x + card_clear + card_w / 2 - tab_w / 2", "card_y + %s + frame_band - 3 mm" % PKH, "tab_w", "tab_l + 3 mm")
    f.ext(s, OPS.JoinFeatureOperation, "frame_t", name="Lift tab")
    s = f.sk(seat, "Lip")
    rect(s, "card_x + frame_clear", "card_y + frame_clear", PKW + " - 2 * frame_clear", PKH + " - 2 * frame_clear")
    f.ext(s, OPS.JoinFeatureOperation, "lip_h", NEG, name="Lip into pocket")
    s = f.sk(lipb, "Window")
    rect(s, "card_x + card_clear + frame_overlap", "card_y + card_clear + frame_overlap",
         "card_w - 2 * frame_overlap", "card_h - 2 * frame_overlap")
    f.ext(s, OPS.CutFeatureOperation, "lip_h + frame_t + 1 mm", name="Paint window")
    s = f.sk(seat, "Corner and clip cut-outs")
    for xe in ("0 mm", "plate_x - corner_r"):
        rect(s, xe, "plate_y - corner_r", "corner_r", "corner_r")
    clip_notches(f, s, "clip_y1")
    clip_notches(f, s, "clip_y2")
    f.ext(s, OPS.CutFeatureOperation, "frame_t + 1 mm", name="Corner + clip cut-outs")
    s = f.sk(seat, "Frame magnets")
    for xe, ye in FR_MAGS:
        circle(s, xe, ye, "magnet_d")
    f.ext(s, OPS.CutFeatureOperation, "magnet_t", name="Frame magnet pockets")

    # ================= move the clips to the new edges =================
    occs = [o for o in root.occurrences if o.component.name == "Bed clip"]
    wanted = [(False, V["clip_y1"]), (False, V["clip_y2"]), (True, V["clip_y1"]), (True, V["clip_y2"])]
    for o, (right, y) in zip(occs, wanted):
        m = adsk.core.Matrix3D.create()
        if right:
            m.setToRotation(math.pi, adsk.core.Vector3D.create(0, 0, 1), adsk.core.Point3D.create(0, 0, 0))
        m.translation = adsk.core.Vector3D.create((V["plate_x"] if right else 0) / 10.0, y / 10.0, 0)
        try:
            o.transform2 = m
        except Exception:
            o.transform = m

    # ================= brush holder over jar 1 =================
    jx, jy = num(JX[0]), num("jar_y")
    SY = -(V["bh_dock_t"] + V["bh_cart_t"]) - V["bh_sleeve_od"] / 2 + 1.5
    tip_z = num("mod_z + base_t + jar_h") + 5
    for o in root.occurrences:
        if o.component.name in ("Brush dock", "Tool cartridge", "Plunger", "Brush (reference)", "Ender 5 carriage (reference)"):
            m = adsk.core.Matrix3D.create()
            m.translation = adsk.core.Vector3D.create(jx / 10, (jy - SY) / 10, (tip_z + V["bh_stickout"]) / 10)
            try:
                o.transform2 = m
            except Exception:
                o.transform = m
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    design.computeAll()

    # ================= checks =================
    def bb(o):
        x = o.boundingBox
        return [round(v * 10, 2) for v in (x.minPoint.x, x.minPoint.y, x.minPoint.z, x.maxPoint.x, x.maxPoint.y, x.maxPoint.z)]
    for o in root.occurrences:
        print("OCC", o.name, bb(o))
    col = adsk.core.ObjectCollection.create()
    for o in (b.occ, p.occ, c.occ, f.occ):
        col.add(o)
    for o in occs:
        col.add(o)
    ir = design.analyzeInterference(design.createInterferenceInput(col))
    print("INTERFERENCE", [(r.entityOne.name, r.entityTwo.name, round(r.interferenceBody.volume * 1000, 2)) for r in ir])
    tl = design.timeline
    print("UNHEALTHY", [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState])
    print("SKIPPED", len(SK), SK[:8])
    top = V["mod_z"] + V["base_t"]
    coords = dict(
        layout="v2b: landscape A5 card at the back, 5 jars along the front, base 235 x 220, clips only beside the card",
        module_top_z=round(top, 2),
        card_area=dict(x0=round(V["card_x"] + V["card_clear"], 2), y0=round(V["card_y"] + V["card_clear"], 2),
                       x1=round(V["card_x"] + V["card_clear"] + V["card_w"], 2), y1=round(V["card_y"] + V["card_clear"] + V["card_h"], 2),
                       surface_z=round(top - V["card_recess"], 2)),
        paint_window=dict(x0=round(V["card_x"] + V["card_clear"] + V["frame_overlap"], 2),
                          y0=round(V["card_y"] + V["card_clear"] + V["frame_overlap"], 2),
                          x1=round(V["card_x"] + V["card_clear"] + V["card_w"] - V["frame_overlap"], 2),
                          y1=round(V["card_y"] + V["card_clear"] + V["card_h"] - V["frame_overlap"], 2),
                          frame_top_z=round(top + V["frame_t"], 2)),
        jars=[dict(id="J%d" % (i + 1), cx=round(num(xe), 2), cy=round(jy, 2), floor_z=round(top, 2),
                   rim_z=round(top + V["jar_h"], 2)) for i, xe in enumerate(JX)],
        jar_height=round(V["jar_h"], 2),
        safe_travel_tip_z=round(top + V["jar_h"] + 5, 1),
        min_tool_stickout_below_holder=45,
    )
    print("COORDS", json.dumps(coords))
