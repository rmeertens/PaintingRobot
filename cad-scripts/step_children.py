import sys
sys.argv=[sys.argv[0], sys.argv[1], "hot-end-carriage-assem"]
exec(open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "step_extract.py")).read().split("out = []")[0])
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
# walk children of hot-end-carriage-assem with locations
def leaves(lab, loc, pth, res):
    ref = TDF_Label()
    if st.IsReference_s(lab) and st.GetReferredShape_s(lab, ref):
        leaves(ref, loc.Multiplied(st.GetLocation_s(lab)), pth + [name(lab)], res); return
    if st.IsAssembly_s(lab):
        kids = TDF_LabelSequence(); st.GetComponents_s(lab, kids)
        for i in range(1, kids.Length() + 1):
            leaves(kids.Value(i), loc, pth, res)
    else:
        res.append(("/".join(pth[-3:]), st.GetShape_s(lab).Moved(loc)))
# find the assembly label again by walking
target=[]
def find(lab, loc):
    ref = TDF_Label()
    if st.IsReference_s(lab) and st.GetReferredShape_s(lab, ref):
        l2=loc.Multiplied(st.GetLocation_s(lab))
        if name(ref)=="hot-end-carriage-assem": target.append((ref,l2)); return
        find(ref,l2); return
    if st.IsAssembly_s(lab):
        kids = TDF_LabelSequence(); st.GetComponents_s(lab, kids)
        for i in range(1, kids.Length() + 1): find(kids.Value(i), loc)
for i in range(1, tops.Length()+1): find(tops.Value(i), TopLoc_Location())
lab, loc = target[0]
res=[]; leaves(lab, loc, ["hot-end-carriage-assem"], res)
for p, s in res:
    b=Bnd_Box(); BRepBndLib.Add_s(s,b); a,c=b.CornerMin(),b.CornerMax()
    bb=[round(v,1) for v in (a.X(),a.Y(),a.Z(),c.X(),c.Y(),c.Z())]
    if "hot-end-assem" in p or "fan-shroud" in p: continue
    print(p, bb)
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
for k,(p,s) in enumerate(res):
    if "hot-end-assem" in p or "fan-shroud" in p: continue
    BRepMesh_IncrementalMesh(s,0.05,False,0.3,True)
    w=StlAPI_Writer(); w.Write(s, "carr_%02d_%s.stl"%(k,p.split('/')[-1].split(':')[0]))
