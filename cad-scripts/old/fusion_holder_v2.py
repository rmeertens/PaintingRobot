import adsk.core, adsk.fusion, math

vi = adsk.core.ValueInput.createByString
OPS = adsk.fusion.FeatureOperations
POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
SK = []

# Fitted to the stock Ender 5 carriage (measured from the Endorphin CAD 'legacy-x-assem').
# Local frame: x along gantry (0 = stock nozzle x), y = 0 at the top of the hotend bosses, -y away from the
# carriage, z up from the bottom edge of the carriage plate.
PARAMS = [
    ("bh_dock_left", "41 mm", "Dock: extends this far left of the tool axis"),
    ("bh_dock_right", "22 mm", "Dock: extends this far right of the tool axis"),
    ("bh_dock_h", "63.5 mm", "Dock height (= stock carriage plate height)"),
    ("bh_dock_t", "6 mm", "Dock thickness"),
    ("bh_standoff_h", "4.5 mm", "Standoffs to the plate face (= stock hotend boss height)"),
    ("bh_standoff_d", "7 mm", "Standoff diameter"),
    ("bh_relief_depth", "2 mm", "Pockets for the wheel bolt heads"),
    ("bh_screw_d", "3.4 mm", "M3 clearance"),
    ("bh_head_d", "6.5 mm", "M3 head counterbore"),
    ("bh_head_depth", "3 mm", "Counterbore depth (M3x10 screws)"),
    ("bh_w", "44 mm", "Cartridge width"),
    ("bh_ledge_h", "4 mm", "Hanging ledge height"),
    ("bh_cart_h", "54 mm", "Cartridge height"),
    ("bh_cart_t", "4 mm", "Cartridge back thickness"),
    ("bh_mag_d", "10.2 mm", "Magnet pocket dia (10x3 magnets)"),
    ("bh_mag_t", "3.2 mm", "Magnet pocket depth"),
    ("bh_cone_d", "9 mm", "Locating cone base dia"),
    ("bh_cone_h", "4.5 mm", "Locating cone height"),
    ("bh_cone_clear", "0.3 mm", "Cone socket clearance"),
    ("bh_hex_af", "16 mm", "Plunger hex across flats"),
    ("bh_hex_clear", "0.5 mm", "Sleeve clearance on the hex"),
    ("bh_sleeve_od", "25 mm", "Sleeve outer dia"),
    ("bh_sleeve_h", "40 mm", "Sleeve height"),
    ("bh_plunger_len", "62 mm", "Plunger total length"),
    ("bh_collar_d", "24 mm", "Plunger top collar dia"),
    ("bh_collar_h", "12 mm", "Plunger top collar height"),
    ("bh_tool_d", "7 mm", "Brush handle / pen dia for this plunger"),
    ("bh_tool_clear", "0.3 mm", "Clearance around the tool"),
    ("bh_stickout", "45 mm", "Brush tip below the bottom of the holder"),
]
OLD = ["bh_mount_spacing", "bh_mount_slot"]

HOT = [(-7.0, 39.0), (7.0, 39.0)]              # stock hotend M3 threads, on 4.5 mm bosses
SHROUD = [(-35.38, 31.26), (-17.38, 49.26)]    # stock fan-shroud M3 threads, on the flat face
HEADS = [(-36.5, 51.5, 12.0), (3.5, 51.5, 12.0), (-16.1, 12.6, 13.0)]   # wheel bolt heads (x, z, relief dia)
MAGS = [(-15, 12), (15, 12), (-15, 30), (15, 30)]
CONES = [(0, 12), (0, 50)]


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc.name.startswith("Acrylic card painting fixture"):
        raise Exception("Wrong document " + doc.name)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name in ("Brush dock", "Tool cartridge", "Plunger", "Brush (reference)", "Ender 5 carriage (reference)"):
            o.deleteMe()
    up = design.userParameters
    for n in OLD:
        p = up.itemByName(n)
        if p is not None:
            try:
                p.deleteMe()
            except Exception:
                SK.append("param kept " + n)
    for n, e, c in PARAMS:
        p = up.itemByName(n)
        if p is None:
            up.add(n, vi(e), "mm", c)
        else:
            p.expression = e
            p.comment = c
    V = {p.name: p.value * 10.0 for p in up}
    num = lambda e: float(eval(e.replace(" mm", ""), {}, V))

    DT, CT, LZ = V["bh_dock_t"], V["bh_cart_t"], V["bh_ledge_h"]
    yb, yf = -DT, -DT - CT
    SY = yf - V["bh_sleeve_od"] / 2 + 1.5
    ZT = LZ + V["bh_cart_h"]
    SZ0 = ZT - V["bh_sleeve_h"]

    class Part:
        def __init__(self, name):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = name
            self.occ, self.c, self.body = occ, occ.component, None

        def plane(self, base, expr, name):
            pi = self.c.constructionPlanes.createInput()
            pi.setByOffset(base, vi(expr))
            pl = self.c.constructionPlanes.add(pi)
            pl.name = name
            pl.isLightBulbOn = False
            return pl

        def xz(self, y_expr, name):
            n = self.c.xZConstructionPlane.geometry.normal
            return self.plane(self.c.xZConstructionPlane, "%s * ( %s )" % (1 if n.y > 0 else -1, y_expr), name)

        def yz(self, x_expr, name):
            n = self.c.yZConstructionPlane.geometry.normal
            return self.plane(self.c.yZConstructionPlane, "%s * ( %s )" % (1 if n.x > 0 else -1, x_expr), name)

        def xy(self, z_expr, name):
            return self.plane(self.c.xYConstructionPlane, z_expr, name)

        def sk(self, plane, name):
            s = self.c.sketches.add(plane)
            s.name = name
            return s

    def sp(s, x, y, z):
        return s.modelToSketchSpace(adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0))

    def circle(s, mx, my, mz, d_expr):
        p = sp(s, mx, my, mz)
        c = s.sketchCurves.sketchCircles.addByCenterRadius(p, num(d_expr) / 20.0)
        try:
            dd = s.sketchDimensions.addDiameterDimension(c, adsk.core.Point3D.create(p.x + 0.6, p.y + 0.6, p.z))
            dd.parameter.expression = d_expr
        except Exception:
            SK.append(s.name + " dia")
        return c

    def rect(s, a, b):
        return s.sketchCurves.sketchLines.addTwoPointRectangle(sp(s, *a), sp(s, *b))

    def hexagon(s, mx, my, mz, af_expr):
        p = sp(s, mx, my, mz)
        cp = s.sketchPoints.add(p)
        lines = s.sketchCurves.sketchLines.addScribedPolygon(cp, 6, 0, num(af_expr) / 20.0, False)
        vert = [l for l in lines if abs(l.startSketchPoint.geometry.x - l.endSketchPoint.geometry.x) < 1e-6]
        try:
            s.geometricConstraints.addVertical(vert[0])
            d = s.sketchDimensions.addOffsetDimension(vert[0], vert[1], adsk.core.Point3D.create(p.x, p.y + 1.2, p.z))
            d.parameter.expression = af_expr
        except Exception:
            SK.append(s.name + " hex AF")

    def toward(s, axis, negative):
        n = s.xDirection.crossProduct(s.yDirection)
        along = {"x": n.x, "y": n.y, "z": n.z}[axis] > 0
        if negative:
            return NEG if along else POS
        return POS if along else NEG

    def ext(part, s, op, dist, direction, name, taper=None, pick=None):
        col = adsk.core.ObjectCollection.create()
        profs = [p for p in s.profiles]
        if pick:
            profs = pick(profs)
        for p in profs:
            col.add(p)
        ef = part.c.features.extrudeFeatures
        inp = ef.createInput(col, op)
        de = adsk.fusion.DistanceExtentDefinition.create(vi(dist))
        if taper:
            inp.setOneSideExtent(de, direction, vi(taper))
        else:
            inp.setOneSideExtent(de, direction)
        if op != OPS.NewBodyFeatureOperation:
            inp.participantBodies = [part.body]
        f = ef.add(inp)
        f.name = name
        if op == OPS.NewBodyFeatureOperation:
            part.body = f.bodies.item(0)
        s.isLightBulbOn = False
        return f

    # ================= DOCK =================
    dk = Part("Brush dock")
    back = dk.xz("0 mm", "Dock back (on hotend bosses)")
    front = dk.xz("-bh_dock_t", "Dock front")
    s = dk.sk(back, "Dock plate")
    rect(s, (-V["bh_dock_left"], 0, 0), (V["bh_dock_right"], 0, V["bh_dock_h"]))
    ext(dk, s, OPS.NewBodyFeatureOperation, "bh_dock_t", toward(s, "y", True), "Dock plate")
    dk.body.name = "Brush dock"
    s = dk.sk(back, "Standoffs")
    for x, z in SHROUD:
        circle(s, x, 0, z, "bh_standoff_d")
    ext(dk, s, OPS.JoinFeatureOperation, "bh_standoff_h", toward(s, "y", False), "Standoffs to plate face")
    s = dk.sk(front, "Ledge")
    rect(s, (-V["bh_w"] / 2, yb, 0), (V["bh_w"] / 2, yb, LZ - 0.5))
    ext(dk, s, OPS.JoinFeatureOperation, "bh_cart_t", toward(s, "y", True), "Hanging ledge")
    s = dk.sk(front, "Locating cones")
    for x, z in CONES:
        circle(s, x, yb, z, "bh_cone_d")
    ext(dk, s, OPS.JoinFeatureOperation, "bh_cone_h", toward(s, "y", True), "Locating cones", taper="-43 deg")
    s = dk.sk(back, "Bolt head reliefs")
    for x, z, d in HEADS:
        circle(s, x, 0, z, "%s mm" % d)
    ext(dk, s, OPS.CutFeatureOperation, "bh_relief_depth", toward(s, "y", True), "Bolt head reliefs")
    s = dk.sk(front, "Screw holes")
    for x, z in HOT + SHROUD:
        circle(s, x, yb, z, "bh_screw_d")
    ext(dk, s, OPS.CutFeatureOperation, "bh_dock_t + bh_standoff_h", toward(s, "y", False), "M3 holes")
    s = dk.sk(front, "Counterbores")
    for x, z in HOT + SHROUD:
        circle(s, x, yb, z, "bh_head_d")
    ext(dk, s, OPS.CutFeatureOperation, "bh_head_depth", toward(s, "y", False), "Counterbores")
    s = dk.sk(front, "Dock magnets")
    for x, z in MAGS:
        circle(s, x, yb, z, "bh_mag_d")
    ext(dk, s, OPS.CutFeatureOperation, "bh_mag_t", toward(s, "y", False), "Dock magnet pockets")

    # ================= CARTRIDGE =================
    ct = Part("Tool cartridge")
    cb = ct.xz("-bh_dock_t", "Cartridge back")
    s = ct.sk(cb, "Cartridge plate")
    rect(s, (-V["bh_w"] / 2, yb, LZ), (V["bh_w"] / 2, yb, ZT))
    ext(ct, s, OPS.NewBodyFeatureOperation, "bh_cart_t", toward(s, "y", True), "Cartridge plate")
    ct.body.name = "Tool cartridge"
    sb = ct.xy("bh_ledge_h + bh_cart_h - bh_sleeve_h", "Sleeve bottom")
    s = ct.sk(sb, "Sleeve")
    circle(s, 0, SY, SZ0, "bh_sleeve_od")
    rect(s, (-8, SY, SZ0), (8, yf + 0.01, SZ0))
    ext(ct, s, OPS.JoinFeatureOperation, "bh_sleeve_h", POS, "Sleeve")
    s = ct.sk(sb, "Hex bore")
    hexagon(s, 0, SY, SZ0, "bh_hex_af + bh_hex_clear")
    ext(ct, s, OPS.CutFeatureOperation, "bh_sleeve_h", POS, "Hex bore",
        pick=lambda ps: [min(ps, key=lambda p: p.areaProperties().area)])
    s = ct.sk(cb, "Cone sockets")
    for x, z in CONES:
        circle(s, x, yb, z, "bh_cone_d + 2 * bh_cone_clear")
    ext(ct, s, OPS.CutFeatureOperation, "bh_cone_h + 0.4 mm", toward(s, "y", True), "Cone sockets", taper="-43 deg")
    s = ct.sk(cb, "Cartridge magnets")
    for x, z in MAGS:
        circle(s, x, yb, z, "bh_mag_d")
    ext(ct, s, OPS.CutFeatureOperation, "bh_mag_t", toward(s, "y", True), "Cartridge magnet pockets")

    # ================= PLUNGER =================
    pg = Part("Plunger")
    zb = ZT - V["bh_plunger_len"] + V["bh_collar_h"]
    p1 = pg.xy("bh_ledge_h + bh_cart_h - bh_plunger_len + bh_collar_h", "Plunger bottom")
    s = pg.sk(p1, "Plunger hex")
    hexagon(s, 0, SY, zb, "bh_hex_af")
    ext(pg, s, OPS.NewBodyFeatureOperation, "bh_plunger_len - bh_collar_h", POS, "Plunger hex")
    pg.body.name = "Plunger"
    p2 = pg.xy("bh_ledge_h + bh_cart_h", "Collar bottom")
    s = pg.sk(p2, "Collar")
    circle(s, 0, SY, ZT, "bh_collar_d")
    ext(pg, s, OPS.JoinFeatureOperation, "bh_collar_h", POS, "Collar")
    s = pg.sk(p1, "Tool bore")
    circle(s, 0, SY, zb, "bh_tool_d + bh_tool_clear")
    ext(pg, s, OPS.CutFeatureOperation, "bh_plunger_len", POS, "Tool bore")
    zc = ZT + V["bh_collar_h"] / 2
    p3 = pg.yz("-( bh_collar_d / 2 + 1 mm )", "Set screw start")
    s = pg.sk(p3, "Set screw")
    circle(s, -(V["bh_collar_d"] / 2 + 1), SY, zc, "3.2 mm")
    ext(pg, s, OPS.CutFeatureOperation, "bh_collar_d / 2 + 1 mm", toward(s, "x", False), "Set screw hole")
    p4 = pg.xy("bh_ledge_h + bh_cart_h + bh_collar_h", "Collar top")
    s = pg.sk(p4, "Nut slot")
    nx = -(V["bh_tool_d"] / 2 + 3.2)
    rect(s, (nx - 1.4, SY - 2.95, ZT + V["bh_collar_h"]), (nx + 1.4, SY + 2.95, ZT + V["bh_collar_h"]))
    ext(pg, s, OPS.CutFeatureOperation, "bh_collar_h / 2 + 2.95 mm", NEG, "M3 nut slot")

    # ================= REFERENCE BRUSH =================
    br = Part("Brush (reference)")
    tip = -V["bh_stickout"]
    p5 = br.xy("-bh_stickout + 15 mm", "Ferrule start")
    s = br.sk(p5, "Handle")
    circle(s, 0, SY, tip + 15, "bh_tool_d")
    ext(br, s, OPS.NewBodyFeatureOperation, "bh_stickout - 15 mm + 70 mm", POS, "Handle")
    br.body.name = "Brush (reference)"
    s = br.sk(p5, "Tip")
    circle(s, 0, SY, tip + 15, "bh_tool_d")
    ext(br, s, OPS.JoinFeatureOperation, "15 mm", NEG, "Tip", taper="-11 deg")

    # ================= STOCK ENDER 5 CARRIAGE (simplified reference, measured) =================
    rf = Part("Ender 5 carriage (reference)")
    pf = rf.xz("bh_standoff_h", "Stock plate front face")
    s = rf.sk(pf, "Stock plate")
    rect(s, (-48.5, 4.5, 0), (40.5, 4.5, 63.5))
    ext(rf, s, OPS.NewBodyFeatureOperation, "2.5 mm", toward(s, "y", False), "Stock plate (2.5 mm steel)")
    rf.body.name = "Ender 5 carriage (reference)"
    s = rf.sk(pf, "Hotend bosses")
    for x, z in HOT:
        circle(s, x, 4.5, z, "5.3 mm")
    ext(rf, s, OPS.JoinFeatureOperation, "4.5 mm", toward(s, "y", True), "Hotend bosses")
    s = rf.sk(pf, "Wheel bolt heads")
    for x, z, d in HEADS[:2]:
        circle(s, x, 4.5, z, "9.5 mm")
    ext(rf, s, OPS.JoinFeatureOperation, "3.3 mm", toward(s, "y", True), "Wheel bolt heads")
    s = rf.sk(pf, "Eccentric bolt head")
    circle(s, HEADS[2][0], 4.5, HEADS[2][1], "10 mm")
    ext(rf, s, OPS.JoinFeatureOperation, "4.3 mm", toward(s, "y", True), "Eccentric bolt head + washer")
    s = rf.sk(pf, "Stock M3 threads")
    for x, z in HOT + SHROUD:
        circle(s, x, 4.5, z, "2.5 mm")
    ext(rf, s, OPS.CutFeatureOperation, "8 mm", toward(s, "y", False), "Stock M3 threads")

    # ================= place over jar 1 at safe travel height =================
    jx, jy = num("( pm_x0 + pm_x1 ) / 2"), num("pm_y0 + 1 mm + jar_top / 2")
    tip_z = num("mod_z + base_t + jar_h") + 5
    t = adsk.core.Vector3D.create(jx / 10, (jy - SY) / 10, (tip_z + V["bh_stickout"]) / 10)
    for part in (dk, ct, pg, br, rf):
        m = adsk.core.Matrix3D.create()
        m.translation = t
        try:
            part.occ.transform2 = m
        except Exception:
            part.occ.transform = m
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    design.computeAll()

    for part in (dk, ct, pg, br, rf):
        b = part.body.boundingBox
        print(part.c.name, [round(v * 10, 2) for v in (b.minPoint.x, b.minPoint.y, b.minPoint.z, b.maxPoint.x, b.maxPoint.y, b.maxPoint.z)],
              "vol_cm3", round(part.body.volume, 2))
    col = adsk.core.ObjectCollection.create()
    for o in (dk.occ, ct.occ, pg.occ, rf.occ):
        col.add(o)
    ir = design.analyzeInterference(design.createInterferenceInput(col))
    print("INTERFERENCE", [(r.entityOne.name, r.entityTwo.name, round(r.interferenceBody.volume * 1000, 3)) for r in ir])
    tl = design.timeline
    print("UNHEALTHY", [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState])
    print("SKIPPED", SK)
    print("tool axis y", SY, "tip z", round(tip_z, 2))
