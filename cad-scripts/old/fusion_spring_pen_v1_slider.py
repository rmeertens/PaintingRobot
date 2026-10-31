import adsk.core, adsk.fusion, math

# Spring-loaded pen cartridge (third tool option; brush cartridge and tilted pen cartridge are untouched).
# A small hex "carrier" holds the pen (M3 set screw in its collar). The carrier slides in a short hex guide;
# its collar rests on top of the guide (lowest position). A compression spring sits on the collar and is
# held down by a screw-on "Spring cap", so the pen is pushed down onto the card with the spring force and
# can give way upwards by up to ~8 mm. Axis tilted by spr_tilt sideways along the gantry (top leans +X).
# Holder-local frame (as fusion_holder_v3.py): x along the gantry (0 = old nozzle x), y = 0 at the carriage
# plate face (-y away from it), z up from the bottom edge of the carriage plate. s = distance along the axis
# from the bottom of the guide.
vi = adsk.core.ValueInput.createByString
OPS = adsk.fusion.FeatureOperations
POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
SK = []
PARAMS = [
    ("spr_tilt", "30 deg", "Spring pen: tilt from vertical, sideways along the gantry (top leans right, +X). 0 = vertical"),
    ("spr_hex_af", "14 mm", "Spring pen: carrier hex across flats"),
    ("spr_hex_clear", "0.4 mm", "Spring pen: clearance of the carrier in the guide"),
    ("spr_guide_od", "22 mm", "Spring pen: guide tube outside diameter"),
    ("spr_guide_len", "24 mm", "Spring pen: guide tube length"),
    ("spr_carrier_len", "36 mm", "Spring pen: carrier hex length (below the collar)"),
    ("spr_collar_d", "20 mm", "Spring pen: carrier collar diameter (spring sits on it)"),
    ("spr_collar_h", "8 mm", "Spring pen: carrier collar height"),
    ("spr_spring_od", "18 mm", "Spring pen: max spring outside diameter (cap recess = this + 1.5)"),
    ("spr_spring_id", "13 mm", "Spring pen: min spring inside diameter (pen and cap hole pass through)"),
    ("spr_spring_len", "16.5 mm", "Spring pen: spring length when installed (carrier down). Use a spring with ~25 mm free length"),
]
MAGS = [(1, 11), (15, 11), (15, 47), (-17, 36)]
CONES = [(8, 25), (-2, 51)]
GUIDE_BOTTOM_X = 4.0      # axis point at the bottom of the guide (holder-local)
GUIDE_BOTTOM_Z = 14.0
SPINE_W = 14.0            # spine width (perpendicular to the axis, in the plate plane)
SPINE_T = 8.0             # spine thickness in front of the plate
CAP_T = 6.0               # cap thickness along the axis
CAP_FRONT = 12.0          # cap reaches this far in front of the axis
CAP_HALF_W = 12.0
RECESS_D = 1.5            # spring-centring recess under the cap
SCREW_XP = 4.0            # cap screws: +-4 mm across the spine
PARK_DX = 16.0            # cm: the set is parked 160 mm to the right after the check


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc.name.startswith("Acrylic card painting fixture"):
        raise Exception("Wrong document " + doc.name)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    NAMES = ("Spring pen cartridge", "Spring cap", "Spring pen carrier", "Spring (reference)", "Pen (reference, spring)")
    for o in list(root.occurrences):
        if o.component.name in NAMES:
            o.deleteMe()
    up = design.userParameters
    for n, e, c in PARAMS:
        p = up.itemByName(n)
        if p is None:
            up.add(n, vi(e), "deg" if n.endswith("tilt") else "mm", c)
        else:
            p.expression = e
            p.comment = c
    V = {p.name: (p.value if p.unit == "deg" else p.value * 10.0) for p in up}
    t = up.itemByName("spr_tilt").value
    num = lambda e: float(eval(e.replace(" mm", ""), {}, V))

    DT, CT, LZ = V["bh_dock_t"], V["bh_cart_t"], V["bh_ledge_h"]
    yb, yf = -DT, -DT - CT
    ZT = LZ + V["bh_cart_h"]
    d = (math.sin(t), 0.0, math.cos(t))
    xr = (math.cos(t), 0.0, -math.sin(t))
    ya = yf - SPINE_T - V["spr_collar_d"] / 2 - 1.5            # axis y: collar clears the spine by 1.5 mm
    GL, CH = V["spr_guide_len"], V["spr_collar_h"]
    S_CAP = GL + CH + V["spr_spring_len"] + RECESS_D            # underside of the cap
    S_COL = GL                                                  # collar bottom when the carrier is down

    def P(s, xp=0.0, y=None):
        return (GUIDE_BOTTOM_X + s * d[0] + xp * xr[0], ya if y is None else y, GUIDE_BOTTOM_Z + s * d[2] + xp * xr[2])

    class Part:
        def __init__(self, name):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = name
            self.occ, self.c, self.body = occ, occ.component, None

        def plane_off(self, base, expr, name):
            pi = self.c.constructionPlanes.createInput()
            pi.setByOffset(base, vi(expr))
            pl = self.c.constructionPlanes.add(pi)
            pl.name = name
            pl.isLightBulbOn = False
            return pl

        def xz(self, y_expr, name):
            n = self.c.xZConstructionPlane.geometry.normal
            return self.plane_off(self.c.xZConstructionPlane, "%s * ( %s )" % (1 if n.y > 0 else -1, y_expr), name)

        def yz(self, x_expr, name):
            n = self.c.yZConstructionPlane.geometry.normal
            return self.plane_off(self.c.yZConstructionPlane, "%s * ( %s )" % (1 if n.x > 0 else -1, x_expr), name)

        def xy(self, z_expr, name):
            return self.plane_off(self.c.xYConstructionPlane, z_expr, name)

        def sk(self, plane, name):
            s = self.c.sketches.add(plane)
            s.name = name
            return s

        def tilt(self):
            def mk(sign):
                pi = self.c.constructionPlanes.createInput()
                pi.setByAngle(self.c.yConstructionAxis, vi("%s * spr_tilt" % sign), self.c.xYConstructionPlane)
                pl = self.c.constructionPlanes.add(pi)
                pl.isLightBulbOn = False
                return pl
            def along(pl):
                g = pl.geometry.normal
                return abs(g.x * d[0] + g.y * d[1] + g.z * d[2])
            pl = mk(1)
            if along(pl) < 0.999:
                pl.deleteMe()
                pl = mk(-1)
            if along(pl) < 0.999:
                raise Exception("tilt plane is not square to the axis")
            pl.name = "Spring pen tilt (through origin)"
            g = pl.geometry.normal
            self.tp, self.nv = pl, (g.x, g.y, g.z)
            self.sgn = math.copysign(1.0, sum(a * b for a, b in zip(d, self.nv)))
            self.off0 = sum(a * b for a, b in zip(P(0), self.nv))

        def at_s(self, s, name):
            return self.plane_off(self.tp, "%.4f mm" % (self.off0 + self.sgn * s), name)

    def sp(s, x, y, z):
        p = s.modelToSketchSpace(adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0))
        if abs(p.z) > 0.01:
            raise Exception("point (%.2f, %.2f, %.2f) is %.3f mm off sketch %s" % (x, y, z, p.z * 10, s.name))
        p.z = 0.0
        return p

    def circle(s, pt, d_expr):
        p = sp(s, *pt)
        c = s.sketchCurves.sketchCircles.addByCenterRadius(p, num(d_expr) / 20.0)
        try:
            dd = s.sketchDimensions.addDiameterDimension(c, adsk.core.Point3D.create(p.x + 0.6, p.y + 0.6, 0))
            dd.parameter.expression = d_expr
        except Exception:
            SK.append(s.name + " dia")
        return c

    def poly(s, pts):
        q = [sp(s, *p) for p in pts]
        for i in range(len(q)):
            s.sketchCurves.sketchLines.addByTwoPoints(q[i], q[(i + 1) % len(q)])

    def rect(s, a, b):
        return s.sketchCurves.sketchLines.addTwoPointRectangle(sp(s, *a), sp(s, *b))

    def hexagon(s, pt, af_expr, ref=(1.0, 0.0, 0.0)):
        p = sp(s, *pt)
        cp = s.sketchPoints.add(p)
        q = s.modelToSketchSpace(adsk.core.Point3D.create(pt[0] / 10.0 + ref[0], pt[1] / 10.0 + ref[1], pt[2] / 10.0 + ref[2]))
        s.sketchCurves.sketchLines.addScribedPolygon(cp, 6, math.atan2(q.y - p.y, q.x - p.x), num(af_expr) / 20.0, False)

    def toward(s, axis, negative):
        n = s.xDirection.crossProduct(s.yDirection)
        along = {"x": n.x, "y": n.y, "z": n.z}[axis] > 0
        if negative:
            return NEG if along else POS
        return POS if along else NEG

    def along_dir(s, vec):
        n = s.xDirection.crossProduct(s.yDirection)
        return POS if (n.x * vec[0] + n.y * vec[1] + n.z * vec[2]) > 0 else NEG

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

    smallest = lambda ps: [min(ps, key=lambda p: p.areaProperties().area)]
    neg_d = (-d[0], -d[1], -d[2])

    # ================= SPRING PEN CARTRIDGE =================
    pc = Part("Spring pen cartridge")
    cb = pc.xz("-bh_dock_t", "Cartridge back")
    s = pc.sk(cb, "Cartridge plate")
    rect(s, (-V["bh_w"] / 2, yb, LZ), (V["bh_w"] / 2, yb, ZT))
    ext(pc, s, OPS.NewBodyFeatureOperation, "bh_cart_t", toward(s, "y", True), "Cartridge plate")
    pc.body.name = "Spring pen cartridge"
    s = pc.sk(cb, "Bottom bolt notch")
    rect(s, (-V["bh_w"] / 2 - 1, yb, LZ - 1), (-V["bh_notch_right"], yb, V["bh_notch_h"]))
    ext(pc, s, OPS.CutFeatureOperation, "bh_cart_t", toward(s, "y", True), "Notch for bottom bolt + nut")
    pc.tilt()
    cf = pc.xz("-( bh_dock_t + bh_cart_t )", "Cartridge front")
    hw = SPINE_W / 2
    s = pc.sk(cf, "Spine")
    poly(s, [P(0, hw, yf), P(S_CAP, hw, yf), P(S_CAP, -hw, yf), P(0, -hw, yf)])
    ext(pc, s, OPS.JoinFeatureOperation, "%.3f mm" % SPINE_T, toward(s, "y", True), "Spine (guide to cap)")
    s = pc.sk(cf, "Guide web")
    poly(s, [P(0, hw, yf), P(GL, hw, yf), P(GL, -hw, yf), P(0, -hw, yf)])
    ext(pc, s, OPS.JoinFeatureOperation, "%.3f mm" % (yf - ya), toward(s, "y", True), "Guide web")
    s = pc.sk(pc.at_s(0, "Guide bottom"), "Guide tube")
    circle(s, P(0), "spr_guide_od")
    ext(pc, s, OPS.JoinFeatureOperation, "spr_guide_len", along_dir(s, d), "Guide tube")
    s = pc.sk(pc.at_s(-1, "Guide bore start"), "Guide hex bore")
    hexagon(s, P(-1), "spr_hex_af + spr_hex_clear", xr)
    ext(pc, s, OPS.CutFeatureOperation, "spr_guide_len + 2 mm", along_dir(s, d), "Guide hex bore", pick=smallest)
    s = pc.sk(pc.at_s(S_CAP, "Cap seat"), "Cap screw pilots")
    ys = yf - SPINE_T / 2
    for xp in (-SCREW_XP, SCREW_XP):
        circle(s, P(S_CAP, xp, ys), "2.5 mm")
    ext(pc, s, OPS.CutFeatureOperation, "12 mm", along_dir(s, neg_d), "Cap screw pilot holes (M3 self-tapping)")
    s = pc.sk(cb, "Cone sockets")
    for x, z in CONES:
        circle(s, (x, yb, z), "bh_cone_d + 2 * bh_cone_clear")
    ext(pc, s, OPS.CutFeatureOperation, "bh_cone_h + 0.4 mm", toward(s, "y", True), "Cone sockets", taper="-43 deg")
    s = pc.sk(cb, "Cartridge magnets")
    for x, z in MAGS:
        circle(s, (x, yb, z), "bh_mag_d")
    ext(pc, s, OPS.CutFeatureOperation, "bh_mag_t", toward(s, "y", True), "Cartridge magnet pockets")

    # ================= SPRING CAP (separate part, 2 x M3x16 into the spine) =================
    cp = Part("Spring cap")
    cp.tilt()
    seat = cp.at_s(S_CAP, "Cap underside")
    s = cp.sk(seat, "Cap outline")
    poly(s, [P(S_CAP, CAP_HALF_W, yf), P(S_CAP, CAP_HALF_W, ya - CAP_FRONT), P(S_CAP, -CAP_HALF_W, ya - CAP_FRONT), P(S_CAP, -CAP_HALF_W, yf)])
    ext(cp, s, OPS.NewBodyFeatureOperation, "%.1f mm" % CAP_T, along_dir(s, d), "Cap")
    cp.body.name = "Spring cap"
    s = cp.sk(seat, "Pen hole")
    circle(s, P(S_CAP), "spr_spring_id - 1 mm")
    ext(cp, s, OPS.CutFeatureOperation, "%.1f mm" % CAP_T, along_dir(s, d), "Pen hole")
    s = cp.sk(seat, "Spring recess")
    circle(s, P(S_CAP), "spr_spring_od + 1.5 mm")
    ext(cp, s, OPS.CutFeatureOperation, "%.1f mm" % RECESS_D, along_dir(s, d), "Spring recess")
    s = cp.sk(seat, "Screw holes")
    for xp in (-SCREW_XP, SCREW_XP):
        circle(s, P(S_CAP, xp, ys), "3.4 mm")
    ext(cp, s, OPS.CutFeatureOperation, "%.1f mm" % CAP_T, along_dir(s, d), "Screw holes")
    s = cp.sk(cp.at_s(S_CAP + CAP_T, "Cap top"), "Counterbores")
    for xp in (-SCREW_XP, SCREW_XP):
        circle(s, P(S_CAP + CAP_T, xp, ys), "6 mm")
    ext(cp, s, OPS.CutFeatureOperation, "2.5 mm", along_dir(s, neg_d), "Counterbores")

    # ================= CARRIER (built vertical: local z = 0 at the collar bottom) =================
    pp = Part("Spring pen carrier")
    CL = V["spr_carrier_len"]
    p1 = pp.xy("-spr_carrier_len", "Carrier bottom")
    s = pp.sk(p1, "Carrier hex")
    hexagon(s, (0, 0, -CL), "spr_hex_af")
    ext(pp, s, OPS.NewBodyFeatureOperation, "spr_carrier_len", POS, "Carrier hex")
    pp.body.name = "Spring pen carrier"
    s = pp.sk(pp.c.xYConstructionPlane, "Collar")
    circle(s, (0, 0, 0), "spr_collar_d")
    ext(pp, s, OPS.JoinFeatureOperation, "spr_collar_h", POS, "Collar")
    s = pp.sk(p1, "Pen bore")
    circle(s, (0, 0, -CL), "pen_d + pen_clear")
    ext(pp, s, OPS.CutFeatureOperation, "spr_carrier_len + spr_collar_h", POS, "Pen bore")
    s = pp.sk(pp.yz("-( spr_collar_d / 2 + 1 mm )", "Set screw start"), "Set screw")
    circle(s, (-(V["spr_collar_d"] / 2 + 1), 0, CH / 2), "3.2 mm")
    ext(pp, s, OPS.CutFeatureOperation, "spr_collar_d / 2 + 1 mm", toward(s, "x", False), "Set screw hole")
    s = pp.sk(pp.xy("spr_collar_h", "Collar top"), "Nut slot")
    nx = -((V["pen_d"] + V["pen_clear"]) / 2 + 2.4)
    rect(s, (nx - 1.4, -2.95, CH), (nx + 1.4, 2.95, CH))
    ext(pp, s, OPS.CutFeatureOperation, "spr_collar_h / 2 + 2.95 mm", NEG, "M3 nut slot")

    # ================= SPRING + PEN (reference, same local frame as the carrier) =================
    spg = Part("Spring (reference)")
    s = spg.sk(spg.xy("spr_collar_h", "Spring bottom"), "Spring")
    circle(s, (0, 0, CH), "spr_spring_od")
    circle(s, (0, 0, CH), "spr_spring_id")
    ext(spg, s, OPS.NewBodyFeatureOperation, "spr_spring_len", POS, "Spring (installed length)",
        pick=lambda ps: [max(ps, key=lambda p: -abs(p.areaProperties().area - math.pi * (V["spr_spring_od"] ** 2 - V["spr_spring_id"] ** 2) / 400))])
    spg.body.name = "Spring (reference)"
    pr = Part("Pen (reference, spring)")
    s_tip = (-V["pen_tip_below"] - GUIDE_BOTTOM_Z) / math.cos(t)        # axis s where the tip is
    lz_tip = s_tip - S_COL
    pz = pr.xy("%.3f mm" % (lz_tip + 15), "Pen cone start")
    s = pr.sk(pz, "Pen barrel")
    circle(s, (0, 0, lz_tip + 15), "pen_d")
    ext(pr, s, OPS.NewBodyFeatureOperation, "%.3f mm" % (90 - lz_tip - 15), POS, "Pen barrel")
    pr.body.name = "Pen (reference, spring)"
    s = pr.sk(pz, "Pen tip")
    circle(s, (0, 0, lz_tip + 15), "pen_d")
    ext(pr, s, OPS.JoinFeatureOperation, "15 mm", NEG, "Pen tip", taper="-15 deg")

    # ================= placement (same place as the brush holder parts) =================
    jx, jy = num("jar_x0"), num("jar_y")
    SY = -(V["bh_dock_t"] + V["bh_cart_t"]) - V["bh_sleeve_od"] / 2 + 1.5
    place = (jx, jy - SY, num("mod_z + base_t + jar_h") + 5 + V["bh_stickout"])

    def set_tf(occ, m):
        try:
            occ.transform2 = m
        except Exception:
            occ.transform = m

    def placed(rot):
        m = adsk.core.Matrix3D.create()
        if rot:
            if t > 1e-6:
                m.setToRotation(t, adsk.core.Vector3D.create(0, 1, 0), adsk.core.Point3D.create(0, 0, 0))
                v = adsk.core.Vector3D.create(0, 0, 1)
                v.transformBy(m)
                if v.x * d[0] < 0:
                    m.setToRotation(-t, adsk.core.Vector3D.create(0, 1, 0), adsk.core.Point3D.create(0, 0, 0))
            o = P(S_COL)
            m.translation = adsk.core.Vector3D.create((place[0] + o[0]) / 10, (place[1] + o[1]) / 10, (place[2] + o[2]) / 10)
        else:
            m.translation = adsk.core.Vector3D.create(place[0] / 10, place[1] / 10, place[2] / 10)
        return m

    for part, rot in ((pc, False), (cp, False), (pp, True), (spg, True), (pr, True)):
        set_tf(part.occ, placed(rot))
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    design.computeAll()

    # ================= checks (mounted on the dock) =================
    occ = {o.component.name: o for o in root.occurrences}
    col = adsk.core.ObjectCollection.create()
    for nme in ("Brush dock", "Ender 5 carriage (reference)") + NAMES:
        col.add(occ[nme])
    ir = design.analyzeInterference(design.createInterferenceInput(col))
    print("INTERFERENCE", [(r.entityOne.name, r.entityTwo.name, round(r.interferenceBody.volume * 1000, 3)) for r in ir])
    for nme in NAMES:
        b = occ[nme].bRepBodies.item(0)
        x = b.boundingBox
        print(nme, [round(v * 10, 1) for v in (x.minPoint.x, x.minPoint.y, x.minPoint.z, x.maxPoint.x, x.maxPoint.y, x.maxPoint.z)], "vol", round(b.volume, 2))
    tl = design.timeline
    print("UNHEALTHY", [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState])
    print("SKIPPED", SK)
    tip = P(s_tip)
    print("pen tip (holder-local): x %.1f y %.1f z %.1f | brush axis x 0 y %.1f | cap underside s %.1f, axis y %.1f" % (tip[0], tip[1], tip[2], SY, S_CAP, ya))
    for nme in NAMES:
        m = occ[nme].transform2
        tr = m.translation
        tr.x += PARK_DX
        m.translation = tr
        set_tf(occ[nme], m)
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
