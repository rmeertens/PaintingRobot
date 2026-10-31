import manifold3d as m3, trimesh, numpy as np
bed_stack=7.5; plate_t=4.5; squeeze=0.4; jaw=3.5; spine=4.0; clear=0.5; reach_top=6.0; reach_bot=10.0; w=20.0; r=1.5
gap=bed_stack+plate_t-squeeze
xs_in=-clear; xs_out=xs_in-spine
pts=[(xs_out,-jaw),(reach_bot,-jaw),(reach_bot,0),(xs_in,0),(xs_in,gap),(reach_top,gap),(reach_top,gap+jaw),(xs_out,gap+jaw)]
cs=m3.CrossSection([pts])
# inner corner fillets, done in 2D so the outline stays one clean profile
for zc,sgn in ((0,1),(gap,-1)):
    sq=m3.CrossSection.square([r,r]).translate([xs_in, zc if sgn>0 else zc-r])
    circ=m3.CrossSection.circle(r,48).translate([xs_in+r,zc+sgn*r])
    cs=cs+(sq-circ)
body=m3.Manifold.extrude(cs,w)
# lead-in chamfer on the upper jaw tip so it slides onto the ear
t=trimesh.Trimesh(*(lambda m:(m.vert_properties[:,:3],m.tri_verts))(body.to_mesh()))
t.export("bed_clip_7p5mm.stl")
print("watertight",t.is_watertight,"extents",np.round(t.extents,2).tolist(),"jaw gap",round(gap,2))
