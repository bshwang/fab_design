"""Selection measurement and deterministic brief-to-geometry construction."""
import json
import math
from pathlib import Path
import hashlib
import uuid
import subprocess
import bpy
from mathutils import Euler, Matrix, Vector
from . import author_spec as spec, geometry as g, core


def frame(settings):
    return Matrix.Translation(settings.origin) @ Euler(settings.orientation, 'XYZ').to_matrix().to_4x4()


def source_objects(context):
    result={}
    def visit(obj):
        if obj.type in {'MESH','CURVE','SURFACE','FONT'}:
            result[obj.as_pointer()]=obj
        elif obj.type=='EMPTY':
            if obj.instance_collection:
                raise ValueError('Make a working copy of the collection instance editable before measuring it.')
            for child in obj.children:
                visit(child)
    for obj in context.selected_objects:
        visit(obj)
    if not result:
        raise ValueError('Select mesh/curve objects, or a parent with geometry children.')
    if any(obj.get('fab_author_generated') for obj in result.values()):
        raise ValueError('Select reference geometry, not a generated preview.')
    return list(result.values())


def bounds(objects, matrix, depsgraph):
    lo=Vector((float('inf'),)*3)
    hi=Vector((-float('inf'),)*3)
    count=0
    for obj in objects:
        evaluated=obj.evaluated_get(depsgraph)
        mesh=evaluated.to_mesh()
        try:
            if mesh is None:
                continue
            transform=matrix @ evaluated.matrix_world
            for vertex in mesh.vertices:
                p=transform @ vertex.co
                if not all(math.isfinite(v) for v in p):
                    raise ValueError('Reference contains non-finite coordinates.')
                for i in range(3):
                    lo[i]=min(lo[i],p[i]); hi[i]=max(hi[i],p[i])
                count+=1
        finally:
            evaluated.to_mesh_clear()
    if not count:
        raise ValueError('Selection contains no measurable vertices.')
    return lo,hi,count


def measure(context, settings, part, use_bindings=False):
    if use_bindings:
        missing=[ref for ref in part.bindings if ref.object is None or ref.object.name not in context.scene.objects]
        if missing or not part.bindings:
            raise ValueError('Source objects are missing. Select and assign the component again.')
        objects=[ref.object for ref in part.bindings]
    else:
        objects=source_objects(context)
    # Active axes are orientation only; negative scale/shear stay in evaluated vertices.
    basis=Euler(part.rotation, 'XYZ').to_matrix()
    if not use_bindings and settings.measure_axes=='ACTIVE':
        active=context.view_layer.objects.active
        if not active:
            raise ValueError('Choose an active reference object for component axes.')
        basis=frame(settings).to_3x3().inverted() @ active.matrix_world.to_quaternion().to_matrix()
    elif not use_bindings:
        basis=Matrix.Identity(3)
    transform=basis.inverted().to_4x4() @ frame(settings).inverted()
    lo,hi,count=bounds(objects,transform,context.evaluated_depsgraph_get())
    size=(hi-lo)*settings.meters_per_unit
    if min(size)<1e-6:
        raise ValueError('Selection is flat. Enter a nonzero thickness manually or use outline capture.')
    center=basis @ ((lo+hi)/2) * settings.meters_per_unit
    part.position=center; part.size=size; part.rotation=basis.to_euler('XYZ')
    if not use_bindings:
        part.bindings.clear()
        for obj in objects:
            part.bindings.add().object=obj
    part.source='selection'; part.configured=True
    settings.frame_locked=True
    return count,len(objects)


def selection_floor(context, settings):
    objects=source_objects(context)
    rotation=Euler(settings.orientation,'XYZ').to_matrix().to_4x4()
    lo,hi,_=bounds(objects,rotation.inverted(),context.evaluated_depsgraph_get())
    settings.origin=rotation @ Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))


def show_guides(context,settings,part=None):
    """Non-rendering, nonselectable visual guides; never edits source geometry."""
    key=settings.document_id
    def guide(name,kind):
        obj=next((o for o in context.scene.objects if o.get('fab_author_guide')==key and o.get('fab_guide_kind')==kind),None)
        if not obj:
            obj=bpy.data.objects.new(name,None); context.scene.collection.objects.link(obj)
            obj['fab_author_guide']=key; obj['fab_guide_kind']=kind
        obj.hide_render=True; obj.hide_select=True; obj.show_in_front=True; obj.show_name=True
        return obj
    for name,direction,color in [('+X RIGHT',(1,0,0),(1,.3,.2,1)),('-Y FRONT',(0,-1,0),(.2,1,.3,1)),('+Z UP',(0,0,1),(.2,.5,1,1))]:
        obj=guide(name,name); obj.empty_display_type='SINGLE_ARROW'; obj.empty_display_size=.35/settings.meters_per_unit
        obj.matrix_world=frame(settings) @ Vector(direction).to_track_quat('Z','Y').to_matrix().to_4x4()
        obj.color=color
    if part:
        obj=guide('Component bounds','bounds'); obj.empty_display_type='CUBE'; obj.empty_display_size=.5
        obj.matrix_world=frame(settings) @ Matrix.Scale(1/settings.meters_per_unit,4) @ component_matrix(part) @ Matrix.Diagonal((*part.size,1))
        if part.joint_enabled:
            joint=guide('Joint axis','joint'); joint.empty_display_type='SINGLE_ARROW'; joint.empty_display_size=.25/settings.meters_per_unit
            axis=Vector(part.joint_axis)
            if axis.length<1e-8:
                raise ValueError('Joint axis cannot be zero.')
            joint.matrix_world=frame(settings) @ Matrix.Translation(Vector(part.joint_center)/settings.meters_per_unit) @ axis.to_track_quat('Z','Y').to_matrix().to_4x4()


def component_matrix(part):
    return Matrix.Translation(part.position) @ Euler(part.rotation,'XYZ').to_matrix().to_4x4()


def capture_points(context, settings, part):
    import bmesh
    if context.mode!='EDIT_MESH' or not context.active_object:
        raise ValueError('In Edit Mode, select one connected edge chain or closed outline.')
    obj=context.active_object
    bm=bmesh.from_edit_mesh(obj.data)
    edges=[edge for edge in bm.edges if edge.select]
    vertices={v for edge in edges for v in edge.verts}
    if not 2<=len(vertices)<=spec.MAX_POINTS:
        raise ValueError('Select 2–256 connected outline/path vertices.')
    adjacency={v:[] for v in vertices}
    for edge in edges:
        a,b=edge.verts; adjacency[a].append(b); adjacency[b].append(a)
    if any(len(adj)>2 for adj in adjacency.values()):
        raise ValueError('Selection branches. Select only one boundary or path.')
    ends=[v for v,adj in adjacency.items() if len(adj)==1]
    closed=not ends
    if (part.shape=='PROFILE' and not closed) or (part.shape=='PATH' and len(ends) not in (0,2)):
        raise ValueError('Profiles need a closed outline; paths need a connected chain.')
    start=min(ends or list(vertices),key=lambda v:v.index)
    ordered=[start]; previous=None; current=start
    while True:
        choices=[v for v in adjacency[current] if v!=previous]
        nxt=next((v for v in choices if v not in ordered),None)
        if nxt is None:
            break
        ordered.append(nxt); previous,current=current,nxt
    if len(ordered)!=len(vertices):
        raise ValueError('Selection contains disconnected outlines.')
    asset=frame(settings).inverted()
    local=component_matrix(part).inverted()
    points=[local @ ((asset @ (obj.matrix_world @ v.co))*settings.meters_per_unit) for v in ordered]
    if part.shape=='PROFILE':
        z=sum(p.z for p in points)/len(points)
        if max(abs(p.z-z) for p in points)>max(1e-6,max(part.size)*1e-5):
            raise ValueError('Outline must lie in the component local XY plane. Adjust component rotation first.')
        points=[Vector((p.x,p.y,0)) for p in points]
        if not spec._profile_ok([list(p) for p in points]):
            raise ValueError('Outline crosses itself or has no area.')
    elif closed:
        if len(points)>=spec.MAX_POINTS:
            raise ValueError('A closed path supports at most 255 vertices plus its closing point.')
        points.append(points[0].copy())
    part.points_json=json.dumps([list(p) for p in points])
    part.source='profile' if part.shape=='PROFILE' else 'path'
    part.configured=True
    settings.frame_locked=True
    return len(points)


def create_collection(document):
    doc=spec.validate(document)
    errors,_=spec.issues(doc)
    if errors:
        raise ValueError(errors[0])
    col=bpy.data.collections.new('FAB Author / '+doc['name'])
    materials={}
    palette=core.LIGHT if doc['style']['theme']=='LIGHT' else core.DARK
    try:
        for p in doc['parts']:
            if not p['enabled']:
                continue
            role=p['material']
            if role not in materials:
                mat=g.material('FAB '+role,palette[role],.4 if role=='steel' else .03)
                mat['fab_role']=role
                materials[role]=mat
            mat=materials[role]
            size=p['size']; bevel=min(size)*p['bevel']
            name=p['name']; shape=p['shape']
            if shape=='BOX':
                obj=g.box(name,(0,0,0),size,col,mat,bevel)
            elif shape=='CYLINDER':
                obj=g.cylinder(name,(0,0,0),.5,1,col,mat,32,0)
                for v in obj.data.vertices:
                    v.co.x*=size[0]; v.co.y*=size[1]; v.co.z*=size[2]
                if bevel:
                    mod=obj.modifiers.new('Soft edges','BEVEL'); mod.width=bevel; mod.segments=3
                    obj.modifiers.new('Corner normals','WEIGHTED_NORMAL')
            elif shape=='ELLIPSOID':
                obj=g.sphere(name,(0,0,0),[s/2 for s in size],col,mat)
            elif shape=='TAPER':
                obj=g.box(name,(0,0,0),size,col,mat,bevel)
                for v in obj.data.vertices:
                    if v.co.z>0:
                        v.co.x*=p['taper']; v.co.y*=p['taper']
            elif shape=='PROFILE':
                points=p['points']; n=len(points)
                if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))<0:
                    points=list(reversed(points))
                verts=[(q[0],q[1],z) for z in (-size[2]/2,size[2]/2) for q in points]
                faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
                faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
                obj=g.mesh(name,verts,faces,col,mat,bevel)
            elif shape=='PATH':
                obj=g.curve(name,p['points'],p['radius'],col,mat)
            obj.location=p['position']
            obj.rotation_euler=[math.radians(v) for v in p['rotation']]
            obj['fab_author_generated']=True
            obj['fab_component_id']=p['id']; obj['fab_component_role']=p['role']
            obj['fab_parent_id']=p['parent']
            obj['fab_joint_json']=json.dumps(p['joint'])
        col['fab_author_brief']=spec.dumps(doc)
        col['fab_name']=doc['name']
        col['fab_mount']='FLOOR'
        bpy.context.view_layer.update()
        # Objects need not be linked to a scene to calculate mesh/curve bounds.
        points=[]
        for p in doc['parts']:
            if not p['enabled']:
                continue
            rot=Euler([math.radians(v) for v in p['rotation']],'XYZ').to_matrix()
            if p['shape'] in {'PROFILE','PATH'}:
                qs=[Vector(q) for q in p['points']]
                margin=p['radius'] if p['shape']=='PATH' else p['size'][2]/2
                qs=[q+Vector((x*margin,y*margin,z*margin)) for q in qs for x in (-1,1) for y in (-1,1) for z in (-1,1)] if p['shape']=='PATH' else [Vector((q.x,q.y,z*margin)) for q in qs for z in (-1,1)]
            else:
                factor=max(1,p['taper']) if p['shape']=='TAPER' else 1
                qs=[Vector((x*p['size'][0]*factor/2,y*p['size'][1]*factor/2,z*p['size'][2]/2)) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
            points += [Vector(p['position'])+rot @ q for q in qs]
        lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
        hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        col['fab_size']=list(hi-lo)
        col['fab_author_min']=list(lo); col['fab_author_max']=list(hi)
        return col
    except Exception:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(col)
        raise


def preview(context,settings,document):
    col=create_collection(document)
    root=bpy.data.objects.new('Preview / '+document['name'],None)
    context.scene.collection.objects.link(root)
    root.instance_type='COLLECTION'; root.instance_collection=col
    offset=Vector(settings.preview_offset)
    root.matrix_world=frame(settings) @ Matrix.Scale(1/settings.meters_per_unit,4) @ Matrix.Translation(offset)
    root.empty_display_size=.15/settings.meters_per_unit
    root['fab_author_generated']=True
    settings.preview=root
    core.select(context,root)
    return root


def render_thumbnail(col,path):
    previous=bpy.context.window.scene if bpy.context.window else None
    scene=core.construct_scene('FAB Author thumbnail',False)
    root=bpy.data.objects.new('Asset thumbnail',None)
    scene.collection.objects.link(root)
    root.instance_type='COLLECTION'; root.instance_collection=col; root.location.z=-.3
    for obj in scene.objects:
        if obj.get('fab_kind') in {'stage','stage_trim','stage_top','title'}:
            obj.hide_render=True
    try:
        if bpy.context.window:
            bpy.context.window.scene=scene
        scene.render.resolution_x=scene.render.resolution_y=256
        scene.eevee.taa_render_samples=24
        scene.view_layers[0].update()
        # Use evaluated instance bounds: orphan collection datablocks can still
        # expose stale curve bounds/transforms before the first render.
        depsgraph=bpy.context.evaluated_depsgraph_get()
        points=[]
        for inst in depsgraph.object_instances:
            if not (inst.is_instance and inst.parent and inst.parent.original==root): continue
            mesh=inst.object.to_mesh()
            try:
                if mesh: points.extend(inst.matrix_world @ v.co for v in mesh.vertices)
            finally: inst.object.to_mesh_clear()
        if not points: raise ValueError('Asset has no visible geometry to preview.')
        rot=scene.camera.rotation_euler.to_matrix()
        projected=[rot.inverted() @ p for p in points]
        lo=Vector([min(p[i] for p in projected) for i in range(3)])
        hi=Vector([max(p[i] for p in projected) for i in range(3)])
        scene.camera.location=rot @ ((lo+hi)/2+Vector((0,0,65)))
        scene.camera.data.ortho_scale=max(hi.x-lo.x,hi.y-lo.y)*1.16
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True,scene=scene.name)
        with bpy.context.temp_override(id=col):
            bpy.ops.ed.lib_id_load_custom_preview(filepath=str(path))
    finally:
        if previous and bpy.context.window:
            bpy.context.window.scene=previous
        objects=list(scene.objects); collections=list(scene.collection.children); world=scene.world
        bpy.data.scenes.remove(scene)
        for obj in objects:
            data=obj.data; kind=obj.type
            bpy.data.objects.remove(obj,do_unlink=True)
            if data and data.users==0:
                container={'MESH':bpy.data.meshes,'FONT':bpy.data.curves,'LIGHT':bpy.data.lights,'CAMERA':bpy.data.cameras}.get(kind)
                if container is not None:
                    container.remove(data)
        for collection in collections:
            if collection.users==0:
                bpy.data.collections.remove(collection)
        if world and world.users==0:
            bpy.data.worlds.remove(world)


def write_asset_file(path,col,thumbnail):
    # libraries.write omits custom ID previews in Blender 4.3. Finalize only this
    # isolated geometry file in a separate Blender; the user's scene is never saved into it.
    bpy.data.libraries.write(str(path),{col},fake_user=True,compress=True)
    args=[bpy.app.binary_path,'--background','--factory-startup','--disable-autoexec',str(path),
          '--python-exit-code','1','--python',str(Path(__file__).with_name('asset_preview_finalize.py')),
          '--',col.name,str(thumbnail)]
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    try:
        result=subprocess.run(args,capture_output=True,timeout=120,creationflags=flags)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Thumbnail finalization timed out; library index was not changed.') from exc
    if result.returncode:
        raise RuntimeError('Could not finalize the asset thumbnail. Library index was not changed.')


def save_library(document, directory):
    """Write a fresh asset revision and atomically update its local catalog."""
    doc=spec.validate(document)
    directory=Path(directory).expanduser().resolve()
    directory.mkdir(parents=True,exist_ok=True)
    index_path=directory/'index.json'
    index=json.loads(index_path.read_text(encoding='utf-8')) if index_path.exists() else {'version':'0.4.0','assets':{}}
    if not isinstance(index,dict) or not isinstance(index.get('assets'),dict):
        raise ValueError('Local library index is invalid')
    col=create_collection(doc)
    aid='local.'+doc['id']
    revision='0.4.0+'+hashlib.sha256(spec.dumps(doc).encode()).hexdigest()[:12]
    filename=doc['id']+'_'+uuid.uuid4().hex[:8]+'.blend'
    col.name='FAB_'+doc['id']
    col['fab_asset']=aid; col['fab_version']=revision
    # Library origin is floor-center. Asset-space coordinates remain in the saved brief.
    lo,hi=Vector(col['fab_author_min']),Vector(col['fab_author_max'])
    col.instance_offset=((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z)
    col.asset_mark(); col.asset_data.description=doc['features'][:1024]
    col.asset_data.tags.new('FAB Author')
    col.asset_data.tags.new(doc['type'])
    try:
        previews=directory/'previews'; previews.mkdir(exist_ok=True)
        thumbnail=previews/(Path(filename).stem+'.png')
        render_thumbnail(col,thumbnail)
        write_asset_file(directory/filename,col,thumbnail)
        category='ROBOT' if doc['type'] in {'AMR','AMMR','ARM','HUMANOID'} else ('LOGISTICS' if doc['type']=='OHT' else 'PROCESS')
        index['assets'][aid]={'name':doc['name'],'category':category,'collection':col.name,'file':filename,
                              'size':list(col['fab_size']),'mount':'FLOOR','version':revision,'preview':'previews/'+thumbnail.name,'tags':doc['type']+' '+doc['features']}
        temporary=directory/('index_'+uuid.uuid4().hex+'.tmp')
        temporary.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(index_path)
    finally:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(col)
    core._index_cache.clear()
    return aid,filename


def import_asset_file(filepath,directory):
    """Import one FAB Author asset, preserving its mesh rather than rebuilding the recipe."""
    source=Path(filepath).resolve()
    if source.suffix.lower()!='.blend' or source.stat().st_size>100_000_000:
        raise ValueError('Choose a FAB Author .blend asset smaller than 100 MB.')
    with bpy.data.libraries.load(str(source),link=False) as (src,dst):
        names=[name for name in src.collections if name.startswith('FAB_asset_')]
        if len(names)!=1:
            raise ValueError('Expected one FAB Author asset collection. Use its individual library .blend file.')
        dst.collections=names
    col=dst.collections[0]
    try:
        doc=spec.loads(col.get('fab_author_brief',''))
        if len(col.all_objects)>1024 or any(o.type not in {'MESH','CURVE','FONT'} for o in col.all_objects):
            raise ValueError('Unsupported asset contents.')
        for obj in col.all_objects:
            if obj.constraints or (obj.animation_data and obj.animation_data.drivers):
                raise ValueError('Author asset imports support static geometry without constraints or drivers.')
            if obj.library or (obj.data and obj.data.library):
                raise ValueError('Author asset must contain its geometry locally.')
            if any(mod.type not in {'BEVEL','WEIGHTED_NORMAL','SUBSURF','SOLIDIFY','TRIANGULATE'} for mod in obj.modifiers):
                raise ValueError('Unsupported modifier in Author asset.')
        size=col.get('fab_size')
        if size is None or len(size)!=3 or any(not math.isfinite(v) or not 0<v<=10000 for v in size):
            raise ValueError('Missing or invalid asset dimensions.')
        directory=Path(directory).resolve(); directory.mkdir(parents=True,exist_ok=True)
        index_path=directory/'index.json'
        index=json.loads(index_path.read_text(encoding='utf-8')) if index_path.exists() else {'version':'0.4.0','assets':{}}
        if not isinstance(index,dict) or not isinstance(index.get('assets'),dict):
            raise ValueError('Invalid local library index.')
        aid='local.'+doc['id']; filename=doc['id']+'_'+uuid.uuid4().hex[:8]+'.blend'
        revision='0.4.0+'+hashlib.sha256(source.read_bytes()).hexdigest()[:12]
        col['fab_asset']=aid; col['fab_version']=revision; col['fab_name']=doc['name']; col['fab_mount']='FLOOR'
        col.asset_mark()
        previews=directory/'previews'; previews.mkdir(exist_ok=True)
        thumbnail=previews/(Path(filename).stem+'.png')
        render_thumbnail(col,thumbnail)
        write_asset_file(directory/filename,col,thumbnail)
        category='ROBOT' if doc['type'] in {'AMR','AMMR','ARM','HUMANOID'} else ('LOGISTICS' if doc['type']=='OHT' else 'PROCESS')
        index['assets'][aid]={'name':doc['name'],'category':category,'collection':col.name,'file':filename,
                              'size':list(size),'mount':'FLOOR','version':revision,
                              'preview':'previews/'+thumbnail.name,'tags':doc['type']+' '+doc['features']}
        temporary=directory/('index_'+uuid.uuid4().hex+'.tmp')
        temporary.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8'); temporary.replace(index_path)
        core._index_cache.clear()
        return aid,filename
    finally:
        # Only the freshly appended asset datablocks are unlinked; source files are untouched.
        children=list(col.children)
        for obj in list(col.all_objects):
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(col)
        for child in children:
            if child.users==0:
                bpy.data.collections.remove(child)
