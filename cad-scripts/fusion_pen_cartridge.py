import adsk.core, adsk.fusion, math, os

# Pen cartridge: same dock interface as the brush "Tool cartridge" (magnets, cones, notch), but with the
# hex sleeve tilted by pen_tilt in the X-Z plane, i.e. sideways along the gantry, parallel to the carriage plate
# (top leans to +x / right, tip points to -x / left),
# plus a matching "Pen plunger" for a thicker pen. The original brush cartridge/plunger are untouched.
# Holder-local frame (same as fusion_holder_v3.py): x along the gantry (0 = old nozzle x),
# y = 0 at the carriage plate face (-y away from the carriage), z up from the bottom edge of the carriage plate.
vi = adsk.core.ValueInput.createByString
OPS = adsk.fusion.FeatureOperations
POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
SK = []
PARAMS = [
    ("pen_tilt", "30 deg", "Pen cartridge: tilt of the pen from vertical, sideways along the gantry (top leans right, +X)"),
    ("pen_d", "10 mm", "Pen plunger: pen barrel diameter (measure the widest part that goes inside)"),
    ("pen_clear", "0.3 mm", "Pen plunger: clearance around the pen"),
    ("pen_tip_below", "20 mm", "Reference pen only: how far the tip sits below the bottom of the dock"),
]
MAGS = [(1, 11), (15, 11), (15, 47), (-17, 36)]
CONES = [(8, 25), (-2, 51)]
SLEEVE_BOTTOM_Z = 20.0      # centre of the sleeve's lower end face (z from the carriage plate bottom edge)
SLEEVE_BOTTOM_X = 6.0       # x of that centre; the sleeve leans to +x from here, the tip ends up at -x
RIB_W = 14.0                # width of the rib joining the sleeve to the plate


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc.name.startswith("Acrylic card painting fixture"):
        raise Exception("Wrong document " + doc.name)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name in ("Pen cartridge", "Pen plunger", "Pen (reference)"):
            o.deleteMe()
    up = design.userParameters
    for n, e, c in PARAMS:
        p = up.itemByName(n)
        if p is None:
            up.add(n, vi(e), "deg" if n == "pen_tilt" else "mm", c)
        else:
            p.expression = e
            p.comment = c
    V = {p.name: (p.value if p.unit == "deg" else p.value * 10.0) for p in up}
    t = up.itemByName("pen_tilt").value            # radians
    num = lambda e: float(eval(e.replace(" mm", ""), {}, V))

    DT, CT, LZ = V["bh_dock_t"], V["bh_cart_t"], V["bh_ledge_h"]
    yb, yf = -DT, -DT - CT
    ZT = LZ + V["bh_cart_h"]
    R = V["bh_sleeve_od"] / 2
    L = V["bh_sleeve_h"]
    d = (math.sin(t), 0.0, math.cos(t))                        # sleeve axis, pointing up (leans to +x)
    xref = (math.cos(t), 0.0, -math.sin(t))                    # plunger's local +x after tilting (hex flat reference)
    ycb = yf + 1.5 - R                                         # axis y: sleeve overlaps the plate by 1.5 mm (= brush axis)
    Pb = (SLEEVE_BOTTOM_X, ycb, SLEEVE_BOTTOM_Z)               # sleeve bottom centre
    Pt = (Pb[0] + L * d[0], ycb, SLEEVE_BOTTOM_Z + L * d[2])   # sleeve top centre (plunger collar sits here)

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

    def sp(s, x, y, z):
        p = s.modelToSketchSpace(adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0))
        if abs(p.z) > 0.01:
            raise Exception("point (%.2f, %.2f, %.2f) is %.3f mm off sketch %s" % (x, y, z, p.z * 10, s.name))
        p.z = 0.0                      # remove round-off on tilted sketch planes
        return p

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

    def hexagon(s, mx, my, mz, af_expr, ref=(1.0, 0.0, 0.0)):
        p = sp(s, mx, my, mz)
        cp = s.sketchPoints.add(p)
        # orient the hex by a model direction (the plunger's local x), so sleeve and plunger always match
        q = s.modelToSketchSpace(adsk.core.Point3D.create(mx / 10.0 + ref[0], my / 10.0 + ref[1], mz / 10.0 + ref[2]))
        ang = math.atan2(q.y - p.y, q.x - p.x)
        s.sketchCurves.sketchLines.addScribedPolygon(cp, 6, ang, num(af_expr) / 20.0, False)

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

    # ================= PEN CARTRIDGE =================
    pc = Part("Pen cartridge")
    cb = pc.xz("-bh_dock_t", "Cartridge back")
    s = pc.sk(cb, "Cartridge plate")
    rect(s, (-V["bh_w"] / 2, yb, LZ), (V["bh_w"] / 2, yb, ZT))
    ext(pc, s, OPS.NewBodyFeatureOperation, "bh_cart_t", toward(s, "y", True), "Cartridge plate")
    pc.body.name = "Pen cartridge"
    NR, NH = V["bh_notch_right"], V["bh_notch_h"]
    s = pc.sk(cb, "Bottom bolt notch")
    rect(s, (-V["bh_w"] / 2 - 1, yb, LZ - 1), (-NR, yb, NH))
    ext(pc, s, OPS.CutFeatureOperation, "bh_cart_t", toward(s, "y", True), "Notch for bottom bolt + nut")

    # tilted plane through the origin, normal = sleeve axis
    def tilted_plane(sign):
        pi = pc.c.constructionPlanes.createInput()
        pi.setByAngle(pc.c.yConstructionAxis, vi("%s * pen_tilt" % sign), pc.c.xYConstructionPlane)
        pl = pc.c.constructionPlanes.add(pi)
        pl.isLightBulbOn = False
        return pl
    def along_d(pl):
        g = pl.geometry.normal
        return abs(g.x * d[0] + g.y * d[1] + g.z * d[2])
    tp = tilted_plane(1)
    if along_d(tp) < 0.999:
        tp.deleteMe()
        tp = tilted_plane(-1)
    if along_d(tp) < 0.999:
        g = tp.geometry.normal
        raise Exception("tilt plane normal (%.3f, %.3f, %.3f) is not along the pen axis" % (g.x, g.y, g.z))
    n = tp.geometry.normal
    tp.name = "Pen tilt (through origin)"
    nvec = (n.x, n.y, n.z)
    off = sum(a * b for a, b in zip(Pb, nvec))                  # signed distance of the sleeve bottom from tp
    sb = pc.plane_off(tp, "%.4f mm" % off, "Sleeve bottom (tilted)")
    sb_lo = pc.plane_off(tp, "%.4f mm" % (off - math.copysign(1.0, sum(a * b for a, b in zip(d, nvec)))), "Bore start")

    # rib joining the tilted sleeve to the front face of the plate (in front of the plate, so it can't fill the
    # bottom-bolt notch); its ends are square to the sleeve axis, flush with the sleeve's end faces
    cf = pc.xz("-( bh_dock_t + bh_cart_t )", "Cartridge front")
    s = pc.sk(cf, "Sleeve rib")
    px, pz_ = xref[0] * RIB_W / 2, xref[2] * RIB_W / 2
    corners = [(Pb[0] + px, yf, Pb[2] + pz_), (Pt[0] + px, yf, Pt[2] + pz_), (Pt[0] - px, yf, Pt[2] - pz_), (Pb[0] - px, yf, Pb[2] - pz_)]
    ln = s.sketchCurves.sketchLines
    pts = [sp(s, *c) for c in corners]
    for i in range(4):
        ln.addByTwoPoints(pts[i], pts[(i + 1) % 4])
    ext(pc, s, OPS.JoinFeatureOperation, "%.3f mm" % (yf - ycb), toward(s, "y", True), "Sleeve rib")
    s = pc.sk(sb, "Tilted sleeve")
    circle(s, *Pb, "bh_sleeve_od")
    ext(pc, s, OPS.JoinFeatureOperation, "bh_sleeve_h", along_dir(s, d), "Tilted sleeve")
    s = pc.sk(sb_lo, "Hex bore")
    hexagon(s, Pb[0] - d[0], Pb[1] - d[1], Pb[2] - d[2], "bh_hex_af + bh_hex_clear", xref)
    ext(pc, s, OPS.CutFeatureOperation, "bh_sleeve_h + 2 mm", along_dir(s, d), "Hex bore (tilted)",
        pick=lambda ps: [min(ps, key=lambda p: p.areaProperties().area)])
    # the collar (on top of the sleeve) overlaps the plate's front face by 1 mm near its top-right corner, and moves
    # up along the axis when the pen lifts: cut a clearance channel for it into the plate
    sgn = math.copysign(1.0, sum(a * b for a, b in zip(d, nvec)))
    st = pc.plane_off(tp, "%.4f mm" % (off + sgn * L), "Sleeve top (tilted)")
    s = pc.sk(st, "Collar clearance")
    circle(s, *Pt, "bh_collar_d + 1 mm")
    ext(pc, s, OPS.CutFeatureOperation, "40 mm", along_dir(s, d), "Collar clearance")
    s = pc.sk(cb, "Cone sockets")
    for x, z in CONES:
        circle(s, x, yb, z, "bh_cone_d + 2 * bh_cone_clear")
    ext(pc, s, OPS.CutFeatureOperation, "bh_cone_h + 0.4 mm", toward(s, "y", True), "Cone sockets", taper="-43 deg")
    s = pc.sk(cb, "Cartridge magnets")
    for x, z in MAGS:
        circle(s, x, yb, z, "bh_mag_d")
    ext(pc, s, OPS.CutFeatureOperation, "bh_mag_t", toward(s, "y", True), "Cartridge magnet pockets")

    # ================= PEN PLUNGER (built vertical; its occurrence is tilted into the sleeve) =================
    pp = Part("Pen plunger")
    hexlen = V["bh_plunger_len"] - V["bh_collar_h"]
    p1 = pp.xy("-( bh_plunger_len - bh_collar_h )", "Plunger bottom")
    s = pp.sk(p1, "Plunger hex")
    hexagon(s, 0, 0, -hexlen, "bh_hex_af")
    ext(pp, s, OPS.NewBodyFeatureOperation, "bh_plunger_len - bh_collar_h", POS, "Plunger hex")
    pp.body.name = "Pen plunger"
    s = pp.sk(pp.c.xYConstructionPlane, "Collar")
    circle(s, 0, 0, 0, "bh_collar_d")
    ext(pp, s, OPS.JoinFeatureOperation, "bh_collar_h", POS, "Collar")
    s = pp.sk(p1, "Pen bore")
    circle(s, 0, 0, -hexlen, "pen_d + pen_clear")
    ext(pp, s, OPS.CutFeatureOperation, "bh_plunger_len", POS, "Pen bore")
    zc = V["bh_collar_h"] / 2
    p3 = pp.yz("-( bh_collar_d / 2 + 1 mm )", "Set screw start")
    s = pp.sk(p3, "Set screw")
    circle(s, -(V["bh_collar_d"] / 2 + 1), 0, zc, "3.2 mm")
    ext(pp, s, OPS.CutFeatureOperation, "bh_collar_d / 2 + 1 mm", toward(s, "x", False), "Set screw hole")
    p4 = pp.xy("bh_collar_h", "Collar top")
    s = pp.sk(p4, "Nut slot")
    nx = -(V["pen_d"] / 2 + 3.2)
    rect(s, (nx - 1.4, -2.95, V["bh_collar_h"]), (nx + 1.4, 2.95, V["bh_collar_h"]))
    ext(pp, s, OPS.CutFeatureOperation, "bh_collar_h / 2 + 2.95 mm", NEG, "M3 nut slot")

    # ================= REFERENCE PEN (same tilted frame as the plunger) =================
    pr = Part("Pen (reference)")
    s_tip = (Pt[2] + V["pen_tip_below"]) / math.cos(t)          # along the axis from the sleeve top centre
    pz = pr.xy("%.3f mm" % (-s_tip + 15), "Pen cone start")
    s = pr.sk(pz, "Pen barrel")
    circle(s, 0, 0, -s_tip + 15, "pen_d")
    ext(pr, s, OPS.NewBodyFeatureOperation, "%.3f mm" % (s_tip - 15 + 90), POS, "Pen barrel")
    pr.body.name = "Pen (reference)"
    s = pr.sk(pz, "Pen tip")
    circle(s, 0, 0, -s_tip + 15, "pen_d")
    ext(pr, s, OPS.JoinFeatureOperation, "15 mm", NEG, "Pen tip", taper="-15 deg")

    # ================= placement =================
    jx, jy = num("jar_x0"), num("jar_y")
    SY = -(V["bh_dock_t"] + V["bh_cart_t"]) - V["bh_sleeve_od"] / 2 + 1.5
    tip_z = num("mod_z + base_t + jar_h") + 5
    place = (jx, jy - SY, tip_z + V["bh_stickout"])            # same as the brush holder parts

    def set_tf(occ, m):
        try:
            occ.transform2 = m
        except Exception:
            occ.transform = m

    def placed(rot):
        m = adsk.core.Matrix3D.create()
        if rot:
            m.setToRotation(t, adsk.core.Vector3D.create(0, 1, 0), adsk.core.Point3D.create(0, 0, 0))
            # check the rotation direction: local +z must map onto the sleeve axis d
            v = adsk.core.Vector3D.create(0, 0, 1)
            v.transformBy(m)
            if v.x * d[0] < 0:
                m.setToRotation(-t, adsk.core.Vector3D.create(0, 1, 0), adsk.core.Point3D.create(0, 0, 0))
            m.translation = adsk.core.Vector3D.create((place[0] + Pt[0]) / 10, (place[1] + Pt[1]) / 10, (place[2] + Pt[2]) / 10)
        else:
            m.translation = adsk.core.Vector3D.create(place[0] / 10, place[1] / 10, place[2] / 10)
        return m

    set_tf(pc.occ, placed(False))
    set_tf(pp.occ, placed(True))
    set_tf(pr.occ, placed(True))
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    design.computeAll()

    # ================= checks (mounted on the dock) =================
    occ = {o.component.name: o for o in root.occurrences}
    col = adsk.core.ObjectCollection.create()
    for nme in ("Brush dock", "Ender 5 carriage (reference)", "Pen cartridge", "Pen plunger", "Pen (reference)"):
        col.add(occ[nme])
    ir = design.analyzeInterference(design.createInterferenceInput(col))
    print("INTERFERENCE", [(r.entityOne.name, r.entityTwo.name, round(r.interferenceBody.volume * 1000, 2)) for r in ir])
    for nme in ("Pen cartridge", "Pen plunger", "Pen (reference)"):
        b = occ[nme].bRepBodies.item(0)
        x = b.boundingBox
        print(nme, [round(v * 10, 1) for v in (x.minPoint.x, x.minPoint.y, x.minPoint.z, x.maxPoint.x, x.maxPoint.y, x.maxPoint.z)], "vol", round(b.volume, 2))
    tl = design.timeline
    print("UNHEALTHY", [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState])
    print("SKIPPED", SK)
    tipL = (Pt[0] - s_tip * d[0], Pt[1], Pt[2] - s_tip * d[2])
    print("pen tip (holder-local): x %.1f  y %.1f  z %.1f   brush axis x 0.0 y %.1f" % (tipL[0], tipL[1], tipL[2], SY))
    print("sleeve bottom centre", [round(v, 2) for v in Pb], "top centre", [round(v, 2) for v in Pt])
    # after the check, park the pen tool set 80 mm to the right so the brush set stays visible on the dock
    for nme in ("Pen cartridge", "Pen plunger", "Pen (reference)"):
        m = occ[nme].transform2 if hasattr(occ[nme], "transform2") else occ[nme].transform
        tr = m.translation
        tr.x += 8.0
        m.translation = tr
        set_tf(occ[nme], m)
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
