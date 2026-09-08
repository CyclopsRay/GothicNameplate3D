"""Versioned, non-executable glyph cache. No third-party Python packages required.

SFNT metadata is read as data; Blender is used only when glyph geometry is missing.
"""
from pathlib import Path
import gzip
import hashlib
import json
import struct
import time

RECIPE = 2
RESOLUTION = 6
FONT_SIZE = 10.0


def sfnt_metadata(path):
    raw = Path(path).read_bytes()
    if raw[:4] not in (b'\x00\x01\x00\x00', b'OTTO', b'true'):
        raise ValueError('Provide an individual TTF/OTF file; TTC/WOFF collections are not supported.')
    u16 = lambda p: struct.unpack_from('>H', raw, p)[0]
    i16 = lambda p: struct.unpack_from('>h', raw, p)[0]
    u32 = lambda p: struct.unpack_from('>I', raw, p)[0]
    tables = {}
    for i in range(u16(4)):
        tag, _, offset, length = struct.unpack_from('>4sIII', raw, 12+16*i)
        if offset+length > len(raw):
            raise ValueError('Invalid font table bounds')
        tables[tag.decode('ascii')] = (offset, length)
    em = u16(tables['head'][0]+18)
    count = u16(tables['maxp'][0]+4)
    hcount = u16(tables['hhea'][0]+34)
    hp = tables['hmtx'][0]
    advances = [u16(hp+4*min(i, hcount-1)) for i in range(count)]
    cmap = {}
    cp = tables['cmap'][0]
    records = []
    for i in range(u16(cp+2)):
        platform, encoding, offset = struct.unpack_from('>HHI', raw, cp+4+i*8)
        if platform == 0 or (platform == 3 and encoding in (1, 10)):
            records.append(cp+offset)
    for p in sorted(set(records), key=lambda p: u16(p)):
        fmt = u16(p)
        if fmt == 4:
            segs = u16(p+6)//2
            ep = p+14; sp = ep+segs*2+2; dp = sp+segs*2; rp = dp+segs*2
            for i in range(segs):
                for ch in range(u16(sp+2*i), u16(ep+2*i)+1):
                    if ch == 65535: continue
                    delta = i16(dp+2*i); offset = u16(rp+2*i)
                    glyph = u16(rp+2*i+offset+2*(ch-u16(sp+2*i))) if offset else ch
                    if glyph: glyph = (glyph+delta) & 65535
                    if glyph and glyph < count: cmap[ch] = glyph
        elif fmt == 12:
            for i in range(u32(p+12)):
                start, end, gid = struct.unpack_from('>III', raw, p+16+i*12)
                for ch in range(start, min(end, 0x10ffff)+1):
                    if 0 < gid+ch-start < count: cmap[ch] = gid+ch-start
    if not cmap:
        raise ValueError('Font has no supported Unicode cmap (format 4 or 12).')
    kern = {}
    if 'kern' in tables:
        kp = tables['kern'][0]
        if u16(kp) == 0:
            p = kp+4
            for _ in range(u16(kp+2)):
                _, length, coverage = struct.unpack_from('>HHH', raw, p)
                if length < 6: break
                if coverage >> 8 == 0 and coverage & 1:
                    for j in range(u16(p+6)):
                        left, right, value = struct.unpack_from('>HHh', raw, p+14+j*6)
                        kern[f'{left},{right}'] = value
                p += length
    names = {}
    if 'name' in tables:
        np = tables['name'][0]; storage = np+u16(np+4)
        for i in range(u16(np+2)):
            platform, encoding, language, nid, size, off = struct.unpack_from('>HHHHHH',raw,np+6+i*12)
            if nid in (1, 2) and (nid not in names or platform == 3):
                try: names[nid] = raw[storage+off:storage+off+size].decode('utf-16-be' if platform in (0,3) else 'mac_roman')
                except UnicodeError: pass
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'family': names.get(1,Path(path).stem),
            'style': names.get(2,''), 'units_per_em': em, 'advances': advances,
            'cmap': {str(k): v for k,v in cmap.items()}, 'kern': kern}


def extract_glyph(font, character):
    import bpy, bmesh
    curve = bpy.data.curves.new('Cache glyph', 'FONT')
    curve.body = character; curve.font = font; curve.size = FONT_SIZE
    curve.resolution_u = RESOLUTION; curve.fill_mode = 'BOTH'
    obj = bpy.data.objects.new('Cache glyph', curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    mesh = obj.data
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00001)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    degenerate = [f for f in bm.faces if f.calc_area() < 1e-12]
    if degenerate: bmesh.ops.delete(bm,geom=degenerate,context='FACES_ONLY')
    loose = [v for v in bm.verts if not v.link_faces]
    removed = len(loose)
    if loose: bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.verts.ensure_lookup_table(); bm.verts.index_update()
    if any(len(e.link_faces)>2 for e in bm.edges):
        raise ValueError(f'Invalid planar glyph topology: {character!r}')
    # Some punctuation contours touch at a single point. Split disconnected
    # face fans at that vertex; they remain visually identical but each swept
    # component then has a manifold boundary. Do not weld these vertices again.
    bm.faces.ensure_lookup_table(); bm.faces.index_update()
    corner_map={}; split_vertices=[]
    for v in bm.verts:
        pending=set(v.link_faces)
        while pending:
            stack=[pending.pop()]; fan=set()
            while stack:
                face=stack.pop()
                if face in fan:continue
                fan.add(face);pending.discard(face)
                for edge in face.edges:
                    if v in edge.verts and len(edge.link_faces)==2:
                        stack.extend(f for f in edge.link_faces if f not in fan)
            index=len(split_vertices);split_vertices.append(tuple(v.co))
            for f in fan:corner_map[(f.index,v.index)]=index
    split_faces=[[corner_map[(f.index,v.index)] for v in f.verts] for f in bm.faces]
    split_count=len(split_vertices)-len(bm.verts)
    if split_count:
        bm.free();bm=bmesh.new()
        vs=[bm.verts.new(p) for p in split_vertices]
        for face in split_faces:bm.faces.new([vs[i] for i in face])
        bm.verts.ensure_lookup_table();bm.verts.index_update()
    vertices = [[v.co.x, v.co.y] for v in bm.verts]
    islands = []
    unseen = set(bm.verts)
    while unseen:
        stack = [min(unseen,key=lambda v:v.index)]; island = set()
        while stack:
            v = stack.pop()
            if v in island: continue
            island.add(v); unseen.discard(v)
            stack.extend(e.other_vert(v) for e in v.link_edges if e.other_vert(v) not in island)
        faces = {f for v in island for f in v.link_faces}
        edges = {e for v in island for e in v.link_edges if e.is_boundary}
        degrees = {v: sum(e in edges for e in v.link_edges) for v in island}
        if any(n not in (0,2) for n in degrees.values()):
            raise ValueError(f'Glyph has a pinched outline: {character!r}; inspect this font before sweeping.')
        islands.append({'vertices':sorted(v.index for v in island),
                        'faces':sorted([v.index for v in f.verts] for f in faces),
                        'boundary':sorted(sorted(v.index for v in e.verts) for e in edges)})
    bm.free()
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    if curve.users == 0: bpy.data.curves.remove(curve)
    return {'vertices':vertices, 'islands':islands, 'removed_loose_vertices':removed,
            'removed_degenerate_faces':len(degenerate),'split_point_contacts':split_count}


def cache_key(metadata):
    import bpy
    return f"{metadata['sha256'][:20]}-b{bpy.app.version[0]}.{bpy.app.version[1]}-r{RECIPE}-u{RESOLUTION}"


def measure_layout_metrics(font,metadata):
    """Blender normalizes font units and adds tracking; it does not simply use em."""
    import bpy
    candidates=[c for c in 'HMNA' if str(ord(c)) in metadata['cmap']]
    if not candidates:candidates=[chr(int(cp)) for cp in metadata['cmap'] if chr(int(cp)).isalpha()]
    if not candidates:raise ValueError('Font needs an alphabetic glyph to calibrate spacing.')
    ch=candidates[0];gid=metadata['cmap'][str(ord(ch))]
    curve=bpy.data.curves.new('Font metric calibration','FONT');curve.font=font
    curve.size=FONT_SIZE;curve.resolution_u=RESOLUTION;curve.body=ch
    obj=bpy.data.objects.new('Font metric calibration',curve);bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update();single=obj.dimensions.x
    curve.body=ch+ch;bpy.context.view_layer.update();double=obj.dimensions.x
    curve.space_character=2;bpy.context.view_layer.update();tracked=obj.dimensions.x
    denominator=metadata['advances'][gid]+metadata['kern'].get(f'{gid},{gid}',0)
    factor=(double-single)/denominator
    tracking=tracked-double
    bpy.data.objects.remove(obj,do_unlink=True);bpy.data.curves.remove(curve)
    if factor<=0 or tracking<0:raise ValueError('Font spacing calibration failed.')
    return factor,tracking


def load_glyph_cache(font_path, characters, cache_dir, bundled_dir, all_supported=False):
    import bpy
    start = time.perf_counter()
    metadata = sfnt_metadata(font_path)
    key = cache_key(metadata)
    paths = [Path(cache_dir)/(key+'.json.gz'), Path(bundled_dir)/(key+'.json.gz')]
    cache = None; cache_source = None
    for path in paths:
        if path.is_file():
            with gzip.open(path,'rt',encoding='utf-8') as f: candidate=json.load(f)
            if (candidate.get('recipe') == RECIPE and candidate.get('font',{}).get('sha256') == metadata['sha256']
                    and candidate.get('blender_version') == list(bpy.app.version[:2])):
                cache=candidate; cache_source=str(path); break
    if cache is None:
        cache={'recipe':RECIPE,'blender_version':list(bpy.app.version[:2]),'resolution_u':RESOLUTION,
               'font_size':FONT_SIZE,'font':metadata,'glyphs':{}}
    requested = sorted(set(characters))
    if all_supported:
        requested = [chr(int(cp)) for cp in metadata['cmap'] if chr(int(cp)).isprintable()]
        if len(requested)>2048:
            raise ValueError('Font has over 2048 characters. Preprocess a chosen --chars subset instead.')
    for ch in requested:
        if str(ord(ch)) not in metadata['cmap']:
            raise ValueError(f'Font {metadata["family"]} does not contain {ch!r} (U+{ord(ch):04X}); choose a covering font.')
    requested_ids = {str(metadata['cmap'][str(ord(ch))]):ch for ch in requested}
    missing = {gid:ch for gid,ch in requested_ids.items() if gid not in cache['glyphs']}
    converted = 0
    if missing:
        font = bpy.data.fonts.load(str(font_path))
        if 'advance_unit_scale' not in cache:
            cache['advance_unit_scale'],cache['tracking_unit']=measure_layout_metrics(font,metadata)
        for gid,ch in missing.items():
            cache['glyphs'][gid]=extract_glyph(font,ch)
            converted += 1
        target=paths[0]; target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_name(target.name+'.tmp')
        with gzip.open(temporary,'wt',encoding='utf-8') as f:
            json.dump(cache,f,ensure_ascii=False,separators=(',',':'))
        temporary.replace(target); cache_source=str(target)
    stats={'key':key,'cache_file':cache_source,'requested_characters':len(requested),
           'requested_unique_glyphs':len(requested_ids),'cache_hits':len(requested_ids)-converted,
           'converted_glyphs':converted,'total_cached_glyphs':len(cache['glyphs']),
           'cached_characters':sum(str(gid) in cache['glyphs'] for gid in metadata['cmap'].values()),
           'removed_loose_vertices_total':sum(g['removed_loose_vertices'] for g in cache['glyphs'].values()),
           'seconds':time.perf_counter()-start,'font_family':metadata['family']}
    return cache, stats


def layout_row(cache, text, spacing=1.08):
    font=cache['font']; cursor=0; previous=None; glyphs=[]
    factor=cache['advance_unit_scale']
    for ch in text:
        gid=font['cmap'][str(ord(ch))]
        if previous is not None: cursor += font['kern'].get(f'{previous},{gid}',0)*factor
        glyph=cache['glyphs'][str(gid)]
        if glyph['vertices']:
            glyphs.append((ch, cursor, glyph))
        cursor += font['advances'][gid]*factor+cache['tracking_unit']*(spacing-1)
        previous=gid
    points=[(v[0]+x,v[1]) for _,x,g in glyphs for v in g['vertices']]
    if not points: raise ValueError(f'Text row has no visible geometry: {text!r}')
    bounds=[min(v[0] for v in points),min(v[1] for v in points),max(v[0] for v in points),max(v[1] for v in points)]
    return glyphs,bounds
