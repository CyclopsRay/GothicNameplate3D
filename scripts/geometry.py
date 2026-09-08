"""Blender geometry and studio helpers; coordinates are millimeters."""
import bpy,bmesh,math
from mathutils import Vector

parts=None
purple=None
def move(obj, col):
    for old in list(obj.users_collection): old.objects.unlink(obj)
    col.objects.link(obj)
    return obj

def material(name, rgb, roughness):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = roughness
    return m

def mesh_obj(name, verts, faces, col=None):
    col = col or parts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.data.materials.append(purple)
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free()
    return obj

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def bevel(obj, width, segments=3, angle=.5):
    activate(obj)
    mod = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
    mod.width = width; mod.segments = segments
    mod.limit_method = 'ANGLE'; mod.angle_limit = angle
    bpy.ops.object.modifier_apply(modifier=mod.name)

def prism(name, points, z0, z1):
    n = len(points)
    verts = [(x,y,z) for z in (z0,z1) for x,y in points]
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh_obj(name, verts, faces)

def rounded_rect(x0,x1,y0,y1,r):
    points=[]
    for cx,cy,start in ((x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)):
        for i in range(17):
            a=math.radians(start+i*90/16)
            points.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return points


def lathe(name, cx,cy,profile,segments=192):
    # Profile describes a closed radial/height cross-section, with zero radius at its ends.
    verts=[]; rings=[]
    for r,z in profile:
        if r == 0:
            rings.append([len(verts)])
            verts.append((cx,cy,z))
        else:
            ring=[]
            for i in range(segments):
                a=2*math.pi*i/segments
                ring.append(len(verts)); verts.append((cx+r*math.cos(a),cy+r*math.sin(a),z))
            rings.append(ring)
    faces=[]
    for a,b in zip(rings,rings[1:]):
        for i in range(segments):
            j=(i+1)%segments
            if len(a)==1: faces.append((a[0],b[i],b[j]))
            elif len(b)==1: faces.append((a[i],b[0],a[j]))
            else: faces.append((a[i],b[i],b[j],a[j]))
    return mesh_obj(name,verts,faces)
