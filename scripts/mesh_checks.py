"""Independent binary STL round-trip validation (NumPy ships with Blender)."""
from pathlib import Path
import numpy as np
import struct
import json


def verify_stl(path, length, angle):
    raw=Path(path).read_bytes()
    count=struct.unpack('<I',raw[80:84])[0]
    assert len(raw)==84+50*count,'Unexpected STL length'
    dtype=np.dtype([('normal','<f4',(3,)),('v','<f4',(3,3)),('attribute','<u2')])
    a=np.frombuffer(raw,dtype=dtype,offset=84,count=count)['v'].astype('float64')
    assert np.isfinite(a).all(),'Non-finite STL vertices'
    v,ids=np.unique(a.reshape(-1,3),axis=0,return_inverse=True)
    t=ids.reshape(-1,3)
    directed=np.concatenate([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]])
    edges,occurrences=np.unique(np.sort(directed,axis=1),axis=0,return_counts=True)
    cross=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0])
    area2=np.linalg.norm(cross,axis=1)
    normals=cross/np.maximum(area2[:,None],1e-30)
    expected=np.array([0,-np.sin(np.deg2rad(angle)),np.cos(np.deg2rad(angle))])
    cap=(normals@expected>1-1e-7)&(area2>.002*(length/150)**2)&(a.mean(1)[:,2]>7*(length/150))
    assert cap.any(),'No terminal text face found'
    angles=np.degrees(np.arccos(np.clip(normals[cap,2],-1,1)))
    parent=np.arange(len(v))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for x,y in edges:
        x,y=find(x),find(y)
        if x!=y:parent[x]=y
    volume=float(np.einsum('ij,ij->i',a[:,0],np.cross(a[:,1],a[:,2])).sum()/6)
    report={'triangles':count,'vertices':len(v),'dimensions_mm':np.ptp(v,axis=0).tolist(),
            'nonmanifold_edges':int((occurrences!=2).sum()),'boundary_edges':int((occurrences==1).sum()),
            'zero_area_triangles':int((area2<1e-12).sum()),
            'connected_components':len({find(i) for i in range(len(v))}),
            'measured_text_angle_degrees':float(np.average(angles,weights=area2[cap])),
            'volume_mm3':volume,'minimum_z_mm':float(v[:,2].min())}
    assert report['nonmanifold_edges']==0,report
    assert report['zero_area_triangles']==0,report
    assert report['connected_components']==1,report
    assert volume>0,report
    assert abs(report['dimensions_mm'][0]-length)<.01,report
    assert abs(report['minimum_z_mm'])<.0001,report
    assert abs(report['measured_text_angle_degrees']-angle)<.001,report
    report['status']='PASS'
    return report


def verify_glb_units(path):
    raw=Path(path).read_bytes()
    assert raw[:4]==b'glTF','Not a GLB file'
    size=struct.unpack_from('<I',raw,12)[0]
    metadata=json.loads(raw[20:20+size])
    meshes=[n for n in metadata.get('nodes',[]) if 'mesh' in n]
    assert len(meshes)==1,'Expected exactly one exported mesh'
    assert np.allclose(meshes[0].get('scale',[1,1,1]),[.001]*3),'GLB millimeter-to-meter scale is missing'
    return {'status':'PASS','mesh_nodes':1,'millimeter_to_meter_scale':.001}
