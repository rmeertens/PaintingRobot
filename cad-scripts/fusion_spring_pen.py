import adsk.core, adsk.fusion, math

# Spring pen cartridge v2: SWING ARM (like a car's trailing arm).
# The pen is clamped in a ring at the end of an arm. The arm pivots on an M3 screw (on a printed spigot) on the
# front of the cartridge, in the plane of the carriage plate. A tiny compression spring (e.g. a ballpoint-pen
# click spring) sits close to the pivot, between the arm and a fixed tab above it, and pushes the arm down onto
# a stop. When the pen touches the card the arm swings up; because the spring is close to the pivot it only
# moves ~1/3 as far as the pen tip, so a tiny spring is enough.
# The pen is tilted spr_tilt sideways (top leans +X); its tip lands under the brush position at the default stick-out.
# Holder-local frame (as fusion_holder_v3.py): x along the gantry (0 = old nozzle x), y = 0 at the carriage plate
# face (-y away from it), z up from the bottom edge of the carriage plate.
vi = adsk.core.ValueInput.createByString
OPS = adsk.fusion.FeatureOperations
POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
SK = []
PARAMS = [
    ("spr_tilt", "30 deg", "Spring pen: tilt of the pen from vertical, sideways along the gantry (top leans right, +X). 0 = vertical"),
    ("spr_pocket_d", "5 mm", "Spring pen: diameter of the two spring pockets (spring OD must be smaller)"),
    ("spr_pocket_depth", "3 mm", "Spring pen: depth of each spring pocket"),
    ("spr_gap", "4 mm", "Spring pen: gap between arm and spring tab at rest (installed spring length = gap + 2 x pocket depth)"),
]
OLD_PARAMS = ("spr_hex_af", "spr_hex_clear", "spr_guide_od", "spr_guide_len", "spr_carrier_len", "spr_collar_d",
              "spr_collar_h", "spr_spring_od", "spr_spring_id", "spr_spring_len")
MAGS = [(1, 11), (15, 11), (15, 47), (-17, 36)]
CONES = [(8, 25), (-2, 51)]
PIV = (-2.0, 20.0)        # pivot (x, z); x > -6.5 keeps the boss off the bottom-bolt notch
AXIS_Y = -28.5            # pen axis y = brush axis y
TIP_X_TARGET = 0.0        # pen tip x at the default stick-out (= brush / old nozzle x)
BOSS_D, BOSS_H = 8.0, 2.7         # boss on the plate front (y -17.5 -> -20.2)
SPIGOT_D, HUB_HOLE = 5.8, 6.2     # spigot the arm turns on / hole in the arm hub
ARM_T, ARM_H = 6.0, 8.0           # arm thickness (y) and height (z)
ARM_Y0 = -20.5                    # arm back face (0.3 mm clear of the boss)
HUB_R = 5.0
RING_OD, RING_L = 19.0, 14.0      # pen ring on the end of the arm
SPRING_X = 6.0                    # spring 8 mm from the pivot
TAB_X = (2.0, 10.0)               # fixed spring tab above the arm
STOP_X = (3.0, 9.0)               # fixed stop under the arm (sets the lowest position)
BLOCK_H = 6.0
PARK_DX = 16.0                    # cm: the set is parked 160 mm to the right after the check


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc.name.startswith("Acrylic card painting fixture"):
        raise Exception("Wrong document " + doc.name)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    NAMES = ("Spring pen cartridge", "Pen swing arm", "Spring (reference)", "Pen (reference, spring)")
    for o in list(root.occurrences):
        if o.component.name in NAMES + ("Spring cap", "Spring pen carrier"):
            o.deleteMe()
    up = design.userParameters
    for n in OLD_PARAMS:
        p = up.itemByName(n)
        if p is not None:
            try:
                p.deleteMe()
            except Exception:
                pass
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
    PT = V["spr_pocket_depth"]
    GAP = V["spr_gap"]
    tip_z = -V["pen_tip_below"]
    zr = PIV[1]                                              # ring centre at pivot height: arm horizontal at rest
    xr = TIP_X_TARGET + (zr - tip_z) * math.tan(t)           # so the tip lands on TIP_X_TARGET
    R = (xr, AXIS_Y, zr)
    arm_top, arm_bot = zr + ARM_H / 2, zr - ARM_H / 2
    arm_ymid = ARM_Y0 - ARM_T / 2
    tab_bot = arm_top + GAP

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

        def xz(self, y, name):
            n = self.c.xZConstructionPlane.geometry.normal
            return self.plane_off(self.c.xZConstructionPlane, "%.4f mm" % (y if n.y > 0 else -y), name)

        def xy(self, z, name):
            return self.plane_off(self.c.xYConstructionPlane, "%.4f mm" % z, name)

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
                raise Exception("tilt plane is not square to the pen axis")
            pl.name = "Pen tilt (through origin)"
            g = pl.geometry.normal
            self.tp, self.nv = pl, (g.x, g.y, g.z)
            self.sgn = math.copysign(1.0, sum(a * b for a, b in zip(d, self.nv)))

        def at(self, pt, name):
            return self.plane_off(self.tp, "%.4f mm" % sum(a * b for a, b in zip(pt, self.nv)), name)

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

    def rect(s, a, b):
        return s.sketchCurves.sketchLines.addTwoPointRectangle(sp(s, *a), sp(s, *b))

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

    def mm(v):
        return "%.4f mm" % v

    # ================= CARTRIDGE =================
    pc = Part("Spring pen cartridge")
    cb = pc.xz(yb, "Cartridge back")
    s = pc.sk(cb, "Cartridge plate")
    rect(s, (-V["bh_w"] / 2, yb, LZ), (V["bh_w"] / 2, yb, ZT))
    ext(pc, s, OPS.NewBodyFeatureOperation, "bh_cart_t", toward(s, "y", True), "Cartridge plate")
    pc.body.name = "Spring pen cartridge"
    s = pc.sk(cb, "Bottom bolt notch")
    rect(s, (-V["bh_w"] / 2 - 1, yb, LZ - 1), (-V["bh_notch_right"], yb, V["bh_notch_h"]))
    ext(pc, s, OPS.CutFeatureOperation, "bh_cart_t", toward(s, "y", True), "Notch for bottom bolt + nut")
    cf = pc.xz(yf, "Cartridge front")
    s = pc.sk(cf, "Pivot boss")
    circle(s, (PIV[0], yf, PIV[1]), "%.1f mm" % BOSS_D)
    ext(pc, s, OPS.JoinFeatureOperation, mm(BOSS_H), toward(s, "y", True), "Pivot boss")
    ysp0 = yf - BOSS_H
    s = pc.sk(pc.xz(ysp0, "Boss face"), "Pivot spigot")
    circle(s, (PIV[0], ysp0, PIV[1]), "%.1f mm" % SPIGOT_D)
    spig_len = (ysp0 - (ARM_Y0 - ARM_T)) + 0.3
    ext(pc, s, OPS.JoinFeatureOperation, mm(spig_len), toward(s, "y", True), "Pivot spigot")
    yse = ysp0 - spig_len
    s = pc.sk(pc.xz(yse, "Spigot end"), "Pivot screw pilot")
    circle(s, (PIV[0], yse, PIV[1]), "2.5 mm")
    ext(pc, s, OPS.CutFeatureOperation, mm(spig_len + BOSS_H + CT - 0.6), toward(s, "y", False), "Pivot screw pilot (M3 x 12)")
    blk_d = yf - (ARM_Y0 - ARM_T)                    # tab/stop reach as far forward as the arm's front face
    s = pc.sk(cf, "Spring tab + stop")
    rect(s, (TAB_X[0], yf, tab_bot), (TAB_X[1], yf, tab_bot + BLOCK_H))
    rect(s, (STOP_X[0], yf, arm_bot - BLOCK_H), (STOP_X[1], yf, arm_bot))
    ext(pc, s, OPS.JoinFeatureOperation, mm(blk_d), toward(s, "y", True), "Spring tab + down stop")
    s = pc.sk(pc.xy(tab_bot, "Tab underside"), "Tab spring pocket")
    circle(s, (SPRING_X, arm_ymid, tab_bot), "spr_pocket_d")
    ext(pc, s, OPS.CutFeatureOperation, "spr_pocket_depth", toward(s, "z", False), "Spring pocket (tab)")
    s = pc.sk(cb, "Cone sockets")
    for x, z in CONES:
        circle(s, (x, yb, z), "bh_cone_d + 2 * bh_cone_clear")
    ext(pc, s, OPS.CutFeatureOperation, "bh_cone_h + 0.4 mm", toward(s, "y", True), "Cone sockets", taper="-43 deg")
    s = pc.sk(cb, "Cartridge magnets")
    for x, z in MAGS:
        circle(s, (x, yb, z), "bh_mag_d")
    ext(pc, s, OPS.CutFeatureOperation, "bh_mag_t", toward(s, "y", True), "Cartridge magnet pockets")

    # ================= SWING ARM =================
    pa = Part("Pen swing arm")
    pa.tilt()
    s = pa.sk(pa.xz(ARM_Y0, "Arm back"), "Arm")
    rect(s, (PIV[0], ARM_Y0, arm_bot), (xr, ARM_Y0, arm_top))
    circle(s, (PIV[0], ARM_Y0, PIV[1]), "%.1f mm" % (2 * HUB_R))
    ext(pa, s, OPS.NewBodyFeatureOperation, mm(ARM_T), toward(s, "y", True), "Arm")
    pa.body.name = "Pen swing arm"
    rs = (R[0] - d[0] * RING_L / 2, R[1], R[2] - d[2] * RING_L / 2)
    s = pa.sk(pa.at(rs, "Ring bottom"), "Pen ring")
    circle(s, rs, "%.1f mm" % RING_OD)
    ext(pa, s, OPS.JoinFeatureOperation, mm(RING_L), along_dir(s, d), "Pen ring")
    bs = (R[0] - d[0] * 20, R[1], R[2] - d[2] * 20)
    s = pa.sk(pa.at(bs, "Bore start"), "Pen bore")
    circle(s, bs, "pen_d + pen_clear")
    ext(pa, s, OPS.CutFeatureOperation, "40 mm", along_dir(s, d), "Pen bore (through ring and arm)")
    # trim the ring flush with the arm's back face, so the arm prints flat on its back without supports
    s = pa.sk(pa.xz(ARM_Y0, "Arm back 3"), "Back trim")
    rect(s, (PIV[0] - 10, ARM_Y0, arm_bot - 20), (xr + 20, ARM_Y0, arm_top + 20))
    ext(pa, s, OPS.CutFeatureOperation, "5 mm", toward(s, "y", False), "Trim ring flush with arm back")
    s = pa.sk(pa.xz(ARM_Y0, "Arm back 2"), "Hub hole")
    circle(s, (PIV[0], ARM_Y0, PIV[1]), "%.1f mm" % HUB_HOLE)
    ext(pa, s, OPS.CutFeatureOperation, mm(ARM_T), toward(s, "y", True), "Hub hole")
    s = pa.sk(pa.xy(arm_top, "Arm top"), "Arm spring pocket")
    circle(s, (SPRING_X, arm_ymid, arm_top), "spr_pocket_d")
    ext(pa, s, OPS.CutFeatureOperation, "spr_pocket_depth", toward(s, "z", True), "Spring pocket (arm)")
    yss = AXIS_Y - RING_OD / 2 - 1
    s = pa.sk(pa.xz(yss, "Set screw start"), "Pen set screw")
    circle(s, (R[0], yss, R[2]), "2.5 mm")
    ext(pa, s, OPS.CutFeatureOperation, mm(RING_OD / 2 + 1), toward(s, "y", False), "Pen clamp screw pilot (M3 x 8, from the front)")

    # ================= SPRING + PEN (reference) =================
    spg = Part("Spring (reference)")
    s = spg.sk(spg.xy(arm_top - PT, "Spring bottom"), "Spring")
    circle(s, (SPRING_X, arm_ymid, arm_top - PT), "4 mm")
    circle(s, (SPRING_X, arm_ymid, arm_top - PT), "3 mm")
    ext(spg, s, OPS.NewBodyFeatureOperation, mm(GAP + 2 * PT), POS, "Spring 4 mm OD (installed)",
        pick=lambda ps: [min(ps, key=lambda p: abs(p.areaProperties().area - math.pi * (16 - 9) / 400))])
    spg.body.name = "Spring (reference)"
    pr = Part("Pen (reference, spring)")
    lz_tip = -(zr - tip_z) / math.cos(t)                    # local z of the tip (local origin = ring centre)
    pz = pr.xy(lz_tip + 15, "Pen cone start")
    s = pr.sk(pz, "Pen barrel")
    circle(s, (0, 0, lz_tip + 15), "pen_d")
    ext(pr, s, OPS.NewBodyFeatureOperation, mm(90 - lz_tip - 15), POS, "Pen barrel")
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
            m.translation = adsk.core.Vector3D.create((place[0] + R[0]) / 10, (place[1] + R[1]) / 10, (place[2] + R[2]) / 10)
        else:
            m.translation = adsk.core.Vector3D.create(place[0] / 10, place[1] / 10, place[2] / 10)
        return m

    for part, rot in ((pc, False), (pa, False), (spg, False), (pr, True)):
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
    arm_len = math.hypot(xr - PIV[0], zr - PIV[1])
    print("ring centre", [round(v, 2) for v in R], "arm length %.1f, spring lever %.1f, ratio %.2f" % (arm_len, SPRING_X - PIV[0], (SPRING_X - PIV[0]) / arm_len))
    print("pen tip (holder-local) x %.1f y %.1f z %.1f" % (TIP_X_TARGET, AXIS_Y, tip_z))
    for nme in NAMES:
        m = occ[nme].transform2
        tr = m.translation
        tr.x += PARK_DX
        m.translation = tr
        set_tf(occ[nme], m)
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
