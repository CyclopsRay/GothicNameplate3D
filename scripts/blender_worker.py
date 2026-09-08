"""Run through nameplate.py; Blender Python worker for cached swept lettering."""
from pathlib import Path
import sys,json,math,time,traceback
import bpy,bmesh
from mathutils import Vector

SCRIPTS=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPTS))
import geometry as geo
from font_cache import load_glyph_cache,layout_row,sfnt_metadata
from mesh_checks import verify_stl,verify_glb_units


def clean_shell(obj):
    mesh=obj.data;mesh.calc_loop_triangles()
    groups={}
    for triangle in mesh.loop_triangles:
        ids=tuple(triangle.vertices)
        groups.setdefault(tuple(sorted(ids)),[]).append(ids)
    faces=[];removed=0
    for triangles in groups.values():
        if len(triangles)==1:faces.extend(triangles)
        else:
            assert len(triangles)==2,'Unexpected repeated triangle'
            a,b=triangles;permutation=[b.index(v) for v in a]
            assert sum(permutation[i]>permutation[j] for i in range(3) for j in range(i+1,3))%2==1,'Same-facing duplicate triangles'
            removed+=1
    new=bpy.data.meshes.new('Validated triangular shell')
    new.from_pydata([v.co[:] for v in mesh.vertices],[],faces);new.update()
    bm=bmesh.new();bm.from_mesh(new)
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges),'Triangulated shell is not manifold'
    bm.to_mesh(new);bm.free()
    for mat in mesh.materials:new.materials.append(mat)
    obj.data=new
    return removed


def add_row(cache,text,height,radius0,config,source,font):
    glyphs,bounds=layout_row(cache,text,config['spacing'])
    x0,y0,x1,y1=bounds
    sx=87/(x1-x0);sy=height/(y1-y0)
    fit=config['fit']
    # Respect the requested mode for every row. Per-row automatic fallback
    # made NAME HERE much shorter than PUT YOUR in the same nameplate.
    if fit=='preserve':
        sx=sy=min(sx,sy)
    xmin=4+(87-(x1-x0)*sx)/2
    angle=math.radians(config['angle']);steps=config['steps']
    # Hidden live source preserves the supplied font for later edits; the mesh
    # is rebuilt from cached glyphs, not driven by editing this object in-place.
    curve=bpy.data.curves.new('Source text','FONT');curve.body=text;curve.font=font
    curve.size=10;curve.space_character=config['spacing']
    live=bpy.data.objects.new('Source • '+text,curve);source.objects.link(live)
    live.scale=(sx,sy,1);live.rotation_euler.x=angle
    live.location=(xmin-x0*sx,(radius0-y0*sy)*math.cos(angle),2.7+(radius0-y0*sy)*math.sin(angle))
    for char,xoffset,glyph in glyphs:
        for number,island in enumerate(glyph['islands']):
            points=glyph['vertices'];boundary=sorted({v for edge in island['boundary'] for v in edge})
            vertices=[];rings=[]
            for step in range(steps+1):
                a=angle*step/steps;ring={}
                for i in island['vertices'] if step in (0,steps) else boundary:
                    x=xmin+(points[i][0]+xoffset-x0)*sx
                    radius=radius0+(points[i][1]-y0)*sy
                    ring[i]=len(vertices)
                    vertices.append((x,radius*math.cos(a),2.7+radius*math.sin(a)))
                rings.append(ring)
            faces=[]
            for face in island['faces']:
                faces.append(tuple(rings[0][i] for i in reversed(face)))
                faces.append(tuple(rings[-1][i] for i in face))
            for s in range(steps):
                for a,b in island['boundary']:
                    faces.append((rings[s][a],rings[s][b],rings[s+1][b],rings[s+1][a]))
            obj=geo.mesh_obj(f'{text} • {char} • component {number+1}',vertices,faces)
            obj['text_face_angle']=config['angle']
            geo.bevel(obj,.12,3,math.radians(32))
    return {'text':text,'fit':fit,'width_mm_at_150':(x1-x0)*sx,'height_mm_at_150':(y1-y0)*sy}


def studio(scene,collection,scale):
    def target(obj,point):obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
    cameras={}
    for name,pos,point,ortho in [
        ('beauty',(215,-255,180),(73,26,26),184),
        ('front',(75,-300,31),(75,20,31),174),
        ('side',(320,20,31),(75,20,31),103),
        ('top',(75,29.5,340),(75,29.5,0),173),
        ('back',(-100,255,140),(73,23,25),188)]:
        data=bpy.data.cameras.new(name);data.type='ORTHO';data.ortho_scale=ortho*scale
        ob=bpy.data.objects.new('Camera • '+name,data);collection.objects.link(ob)
        ob.location=Vector(pos)*scale;target(ob,Vector(point)*scale)
        data.clip_start=.05*scale;data.clip_end=2000*scale;cameras[name]=ob
    bpy.ops.mesh.primitive_plane_add(size=2000*scale,location=(75*scale,20*scale,-.13*scale))
    plane=geo.move(bpy.context.object,collection);plane.name='Studio floor'
    plane.data.materials.append(geo.material('Charcoal',(.045,.053,.065),.6))
    for name,pos,power,size in [('Key',(30,-120,190),800000,130),('Rim',(110,130,200),1050000,110),('Fill',(230,-30,100),520000,100)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power*scale*scale;light.shape='DISK';light.size=size*scale
        ob=bpy.data.objects.new(name,light);collection.objects.link(ob)
        ob.location=Vector(pos)*scale;target(ob,Vector((75,20,20))*scale)
    scene.world=bpy.data.worlds.new('Studio world');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.2,.25,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=1280;scene.render.resolution_y=934;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    scene.camera=cameras['beauty']
    for ob in collection.objects:ob.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_location=Vector((75,22,25))*scale
                space.region_3d.view_distance=230*scale
                space.region_3d.view_rotation=cameras['beauty'].rotation_euler.to_quaternion()
                space.clip_end=3000*scale;space.shading.type='MATERIAL';space.overlay.show_overlays=False
    return cameras


def build(config):
    start=time.perf_counter();out=Path(config['output'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.name='Swept nameplate'
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
    scene.unit_settings.length_unit='MILLIMETERS'
    metadata=sfnt_metadata(config['font'])
    substitutions=[]
    rows=[]
    for text in config['rows']:
        for original,replacement in [('’',"'"),('‘',"'"),('“','"'),('”','"')]:
            if original in text and str(ord(original)) not in metadata['cmap'] and str(ord(replacement)) in metadata['cmap']:
                text=text.replace(original,replacement);substitutions.append({'from':original,'to':replacement})
        rows.append(text)
    cache,cache_stats=load_glyph_cache(config['font'],''.join(rows),config['cache_dir'],config['bundled_cache'])
    print('FONT_CACHE '+json.dumps(cache_stats),flush=True)
    parts=bpy.data.collections.new('01 • Editable construction')
    source=bpy.data.collections.new('02 • Editable text sources')
    printable=bpy.data.collections.new('03 • Print mesh')
    lights=bpy.data.collections.new('04 • Studio')
    for col in (parts,source,printable,lights):scene.collection.children.link(col)
    geo.parts=parts;geo.purple=geo.material('Violet polymer',(.24,.065,.64),.31)
    base=geo.prism('Name deck',geo.rounded_rect(0,105,-3,62,4),0,3.2);geo.bevel(base,.45,3)
    geo.lathe('Circular base extension',120,29.5,[(0,0),(29.6,0),(30,.4),(30,2.6),(29.85,2.95),(29.5,3.2),(0,3.2)])
    geo.lathe('Display platform',120,29.5,[(0,2.9),(27.6,2.9),(28,3.3),(28,6),(27.8,6.35),(27.45,6.5),
              (26.5,6.5),(26.15,6.35),(26,6),(26,5.1),(25.8,4.9),(0,4.9)])
    font=bpy.data.fonts.load(config['font'])
    if len(rows)==2:
        row_stats=[add_row(cache,rows[1],27,2.2,config,source,font),add_row(cache,rows[0],26,30.8,config,source,font)]
    else:row_stats=[add_row(cache,rows[0],45,2.2,config,source,font)]
    source.hide_render=True;source.hide_viewport=True
    # Scale construction before Boolean intersection/tessellation. Scaling the
    # final float32 triangles can collapse nearly coincident intersection points.
    scale=config['length']/150
    for part in parts.objects:
        for v in part.data.vertices:v.co*=scale
    for part in source.objects:part.location*=scale;part.scale*=scale
    obj=base.copy();obj.data=base.data.copy();printable.objects.link(obj);obj.name='NAMEPLATE_PRINT'
    geo.activate(obj)
    solver='MANIFOLD' if 'MANIFOLD' in bpy.types.BooleanModifier.bl_rna.properties['solver'].enum_items.keys() else 'EXACT'
    for part in list(parts.objects):
        if part==base:continue
        bm=bmesh.new();bm.from_mesh(part.data)
        assert bm.faces and all(e.is_manifold for e in bm.edges) and all(v.link_faces for v in bm.verts),part.name
        bm.free()
        mod=obj.modifiers.new('Fuse '+part.name,'BOOLEAN');mod.operation='UNION';mod.solver=solver;mod.object=part
        name=mod.name;bpy.ops.object.modifier_apply(modifier=name)
        assert name not in obj.modifiers,'Boolean failed: '+part.name
    removed=clean_shell(obj)
    parts.hide_render=True;parts.hide_viewport=True
    for face in obj.data.polygons:face.use_smooth=True
    geo.activate(obj)
    weighted=obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL');weighted.keep_sharp=True
    stl=out/'nameplate.stl'
    bpy.ops.wm.stl_export(filepath=str(stl),export_selected_objects=True,apply_modifiers=True,use_scene_unit=False)
    check=verify_stl(stl,config['length'],config['angle'])
    (out/'stl_check.json').write_text(json.dumps(check,indent=2))
    obj.scale=(.001,.001,.001)
    bpy.ops.export_scene.gltf(filepath=str(out/'nameplate.glb'),export_format='GLB',use_selection=True,export_apply=True)
    obj.scale=(1,1,1)
    glb_check=verify_glb_units(out/'nameplate.glb')
    cameras=studio(scene,lights,scale)
    note={'rows':rows,'font':metadata['family']+' '+metadata['style'],'parameters':config,
          'character_substitutions':substitutions,'layout':row_stats,
          'display_clear_diameter_mm':52*scale,'display_center_xy_mm':[120*scale,29.5*scale],
          'cache':cache_stats,'stl':check,'glb':glb_check,'removed_opposite_triangle_pairs':removed,'slicer_verified':False}
    text=bpy.data.texts.new('Model parameters and checks');text.write(json.dumps(note,indent=2,ensure_ascii=False))
    geo.activate(obj);bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'nameplate.blend'))
    note['build_and_export_seconds']=time.perf_counter()-start
    (out/'renders').mkdir(exist_ok=True)
    for view in config['views']:
        print('RENDER '+view,flush=True);scene.camera=cameras[view]
        scene.render.filepath=str(out/'renders'/f'{view}.png');bpy.ops.render.render(write_still=True)
    note['total_seconds']=time.perf_counter()-start;note['status']='PASS'
    (out/'report.json').write_text(json.dumps(note,indent=2,ensure_ascii=False))
    print('COMPLETE '+str(out/'nameplate.stl'),flush=True)


if __name__=='__main__':
    config_path=Path(sys.argv[sys.argv.index('--')+1])
    config=json.loads(config_path.read_text())
    if config['command']=='preprocess':
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _,stats=load_glyph_cache(config['font'],config['characters'],config['cache_dir'],config['bundled_cache'],config['all_supported'])
        Path(config['result']).write_text(json.dumps(stats,indent=2))
        print(json.dumps(stats,indent=2))
    else:build(config)
