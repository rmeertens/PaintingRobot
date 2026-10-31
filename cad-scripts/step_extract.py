"""Extract the stock Ender 5 printhead parts from the Endorphin STEP and measure them."""
import sys, json
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_Label
from OCP.OCP.collections import Sequence_TDF_Label as TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopLoc import TopLoc_Location
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.TopoDS import TopoDS

path = sys.argv[1]
WANT = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
r = STEPCAFControl_Reader()
r.SetNameMode(True)
assert r.ReadFile(path) == IFSelect_RetDone
r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

def name(lab):
    a = TDataStd_Name()
    if lab.FindAttribute(TDataStd_Name.GetID_s(), a):
        return a.Get().ToExtString()
    return "?"

found = []

def walk(lab, loc, pth, depth):
    nm = name(lab)
    ref = TDF_Label()
    if st.IsReference_s(lab) and st.GetReferredShape_s(lab, ref):
        loc2 = loc.Multiplied(st.GetLocation_s(lab))
        walk(ref, loc2, pth, depth)
        return
    p2 = pth + [nm]
    if WANT is None and depth < 4:
        print("  " * depth + nm)
    if WANT and nm in WANT:
        shp = st.GetShape_s(lab).Moved(loc)
        found.append(("/".join(p2), nm, shp))
    if st.IsAssembly_s(lab):
        kids = TDF_LabelSequence()
        st.GetComponents_s(lab, kids)
        for i in range(1, kids.Length() + 1):
            walk(kids.Value(i), loc, p2, depth + 1)

tops = TDF_LabelSequence()
st.GetFreeShapes(tops)
for i in range(1, tops.Length() + 1):
    walk(tops.Value(i), TopLoc_Location(), [], 0)

out = []
for k, (pth, nm, shp) in enumerate(found):
    b = Bnd_Box(); BRepBndLib.Add_s(shp, b)
    pmin, pmax = b.CornerMin(), b.CornerMax()
    x0, y0, z0, x1, y1, z1 = pmin.X(), pmin.Y(), pmin.Z(), pmax.X(), pmax.Y(), pmax.Z()
    holes = []
    ex = TopExp_Explorer(shp, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face(ex.Current())
        s = BRepAdaptor_Surface(f)
        if s.GetType() == GeomAbs_Cylinder:
            c = s.Cylinder()
            rr = c.Radius()
            if rr < 6:
                ax = c.Axis()
                o, d = ax.Location(), ax.Direction()
                holes.append(dict(r=round(rr, 3), o=[round(o.X(), 2), round(o.Y(), 2), round(o.Z(), 2)],
                                  d=[round(d.X(), 3), round(d.Y(), 3), round(d.Z(), 3)]))
        ex.Next()
    fn = f"part_{k}_{nm.replace(' ', '_')}.stl"
    BRepMesh_IncrementalMesh(shp, 0.05, False, 0.3, True)
    w = StlAPI_Writer(); w.Write(shp, fn)
    out.append(dict(path=pth, name=nm, bbox=[round(v, 2) for v in (x0, y0, z0, x1, y1, z1)], holes=holes, stl=fn))
    print(pth, [round(v, 2) for v in (x0, y0, z0, x1, y1, z1)], "cyl faces", len(holes))
json.dump(out, open("stock_parts.json", "w"), indent=1)
