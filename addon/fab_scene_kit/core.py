"""FAB Scene Kit data operations. Callable from UI and Blender CLI tests."""
from pathlib import Path
import json
import math
import uuid
import bpy
from mathutils import Vector, Matrix
from . import geometry as g

VERSION = '0.4.1'
LIGHT = dict(navy='193747', mint='48BFA7', ice='DAE9E5', ivory='F0E8D7',
             gold='E6AD53', blue='6B93AB', white='FCF8EF', steel='A0B4B7',
             joint='C4D4D2', pad='DFE2D9', foup='B29256', display='325D70',
             wafer='344F71', water='548C97', red='BA6C59', skin='C5A389',
             ground='F0E8D7', floor='F0E8D7', label='193747', label_plate='193747', label_ink='FCF8EF')
DARK = dict(LIGHT, ground='121E2B', floor='263D4B', pad='34515D',
            navy='152D3D', label='DBEDE8', joint='52717A')
_index_cache = {}
library_errors = []


def data_dir():
    addon = bpy.context.preferences.addons.get(__package__)
    custom = addon.preferences.library_path if addon else ''
    return Path(bpy.path.abspath(custom)).resolve() if custom else Path(__file__).parent / 'data'


def catalog():
    path = data_dir() / 'library/index.json'
    if not path.is_file():
        raise FileNotFoundError('Asset library missing. Choose the data folder in FAB Kit preferences.')
    addon = bpy.context.preferences.addons.get(__package__)
    local = addon.preferences.local_library_path if addon else ''
    extra = Path(bpy.path.abspath(local)).resolve() / 'index.json' if local else None
    key = (str(path), path.stat().st_mtime_ns, str(extra), extra.stat().st_mtime_ns if extra and extra.is_file() else None)
    if key not in _index_cache:
        _index_cache.clear()
        library_errors.clear()
        assets = json.loads(path.read_text(encoding='utf-8'))['assets']
        assets = {aid:dict(item,_library_root=str(path.parent)) for aid,item in assets.items()}
        if extra and extra.is_file():
            try:
                local_assets=json.loads(extra.read_text(encoding='utf-8'))['assets']
                if not isinstance(local_assets,dict):
                    raise ValueError('Invalid asset index')
                for aid,item in local_assets.items():
                    if not aid.startswith('local.') or aid in assets:
                        raise ValueError('Local assets need unique local.* IDs')
                    if not isinstance(item,dict) or not all(k in item for k in ('name','category','file','collection','size','version')):
                        raise ValueError('Incomplete local asset metadata')
                    asset_path=(extra.parent/item['file']).resolve()
                    if not asset_path.is_relative_to(extra.parent) or not asset_path.is_file() or asset_path.suffix!='.blend':
                        raise ValueError('Local asset file is missing or outside its library')
                assets.update({aid:dict(item,_library_root=str(extra.parent)) for aid,item in local_assets.items()})
            except (OSError,ValueError,KeyError,TypeError) as exc:
                library_errors.append('Local library: '+str(exc))
        _index_cache[key] = assets
    return _index_cache[key]


def collection(scene, name):
    for col in scene.collection.children:
        if col.get('fab_group') == name:
            return col
    col = bpy.data.collections.new('FAB · ' + name)
    col['fab_group'] = name
    scene.collection.children.link(col)
    return col


def owner(scene):
    if not scene.get('fab_owner'):
        scene['fab_owner'] = uuid.uuid4().hex
    return scene['fab_owner']


def scene_material(scene, role, highlight=False):
    uid = owner(scene)
    for mat in bpy.data.materials:
        if (mat.get('fab_owner') == uid and mat.get('fab_role') == role
                and bool(mat.get('fab_highlight')) == highlight):
            return mat
    colors = DARK if scene.fab.theme == 'DARK' else LIGHT
    color = 'F2B54D' if highlight and role in {'mint','blue','ice'} else colors.get(role, 'FCF8EF')
    mat = g.material('FAB_' + role, color, .45 if role in {'steel','gold','wafer'} else .03)
    mat['fab_role'], mat['fab_owner'], mat['fab_highlight'] = role, uid, highlight
    return mat


def local_materials(scene, col, highlight=False):
    for obj in col.all_objects:
        if obj.type not in {'MESH','CURVE','FONT'}:
            continue
        # Each private master owns its mesh/curve datablocks.
        for i, mat in enumerate(obj.data.materials):
            if mat:
                role = mat.get('fab_role', mat.name.split('.')[0])
                obj.data.materials[i] = scene_material(scene, role, highlight)


def copy_collection(source):
    dest = bpy.data.collections.new(source.name)
    dest.instance_offset = source.instance_offset
    for key in source.keys():
        dest[key] = source[key]
    mapping = {}
    # Assets are deliberately flat; preserve parent relationships if a user edited them.
    for obj in source.all_objects:
        dup = obj.copy()
        if obj.data:
            dup.data = obj.data.copy()
        dest.objects.link(dup)
        mapping[obj] = dup
    for src, dup in mapping.items():
        dup.parent = mapping.get(src.parent)
    return dest


def master(scene, asset_id, highlight=False):
    uid = owner(scene)
    item = catalog().get(asset_id)
    if not item:
        raise ValueError('Unknown asset: ' + asset_id)
    for col in bpy.data.collections:
        if (col.get('fab_owner') == uid and col.get('fab_asset') == asset_id
                and bool(col.get('fab_highlight')) == highlight
                and col.get('fab_version') == item.get('version')):
            return col
    library = Path(item['_library_root'])
    path = (library / item['file']).resolve()
    if not path.is_relative_to(library):
        raise ValueError('Invalid asset path')
    if bpy.data.filepath and Path(bpy.data.filepath).resolve()==path:
        source=bpy.data.collections.get(item['collection'])
        if not source:
            raise ValueError('Asset collection missing: '+item['collection'])
        col=copy_collection(source)
    else:
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            if item['collection'] not in src.collections:
                raise ValueError('Asset collection missing: ' + item['collection'])
            dst.collections = [item['collection']]
        col = dst.collections[0]
    col['fab_owner'], col['fab_asset'], col['fab_highlight'] = uid, asset_id, highlight
    col.asset_clear()
    local_materials(scene, col, highlight)
    return col


def roots(scene):
    return [o for o in scene.objects if o.get('fab_asset') and o.get('fab_id')]


def root_of(obj):
    while obj:
        if obj.get('fab_asset') or (obj.instance_collection and obj.instance_collection.get('fab_asset')):
            return obj
        obj = obj.parent
    return None


def selected_roots(context):
    result = []
    for obj in context.selected_objects:
        root = root_of(obj)
        if root and root not in result:
            result.append(root)
    return result


def select(context, obj):
    for other in context.selected_objects:
        other.select_set(False)
    obj.hide_select = False
    obj.select_set(True)
    context.view_layer.objects.active = obj


def add_asset(scene, asset_id, location=(0,0,0), rotation=0, label=True):
    col = master(scene, asset_id)
    root = bpy.data.objects.new(col.get('fab_name', asset_id), None)
    collection(scene, 'Assets').objects.link(root)
    root.instance_type = 'COLLECTION'
    root.instance_collection = col
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = .30
    root['fab_asset'], root['fab_id'], root['fab_version'] = asset_id, uuid.uuid4().hex, VERSION
    root.location, root.rotation_euler.z = location, rotation
    root.fab.label = col.get('fab_name', asset_id)
    root.fab.label_mode = 'FLOOR' if label else 'HIDDEN'
    root.fab.size = .24
    update_label(scene, root)
    return root


def update_label(scene, root):
    if not root or not root.get('fab_id'):
        return
    col = collection(scene, 'Labels')
    labels = [o for o in root.children if o.get('fab_kind') == 'label']
    obj = labels[0] if labels else g.text('FAB Label', '', (0,0,0), .24, col, scene_material(scene,'label'))
    obj['fab_kind'] = 'label'
    obj.parent = root
    obj.hide_select = True
    obj.hide_render = root.fab.label_mode == 'HIDDEN' or not scene.fab.labels_visible
    obj.hide_viewport = obj.hide_render
    # Native Shift-D may share Text data; editing labels must never change siblings.
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.body = ' / '.join(s for s in (root.fab.code, root.fab.label) if s)
    obj.data.size = root.fab.size
    obj.data.materials.clear()
    obj.data.materials.append(scene_material(scene, 'label_ink'))
    if scene.fab.font_path:
        path = Path(bpy.path.abspath(scene.fab.font_path))
        if path.is_file():
            obj.data.font = bpy.data.fonts.load(str(path), check_existing=True)
    dims = root.instance_collection.get('fab_size', (1,1,1)) if root.instance_collection else root.get('fab_size',(1,1,1))
    offset = Vector(root.fab.offset)
    if root.fab.label_mode == 'SIGN' and scene.camera:
        obj.location = Vector((0,0,dims[2]+.35)) + offset
        obj.rotation_euler = (root.rotation_euler.to_matrix().inverted() @ scene.camera.rotation_euler.to_matrix()).to_euler()
    elif root.fab.label_mode == 'FRONT':
        obj.location = Vector((0,-dims[1]/2-.04,dims[2]-.20)) + offset
        obj.rotation_euler = (math.pi/2,0,0)
    else:
        obj.location = Vector((0,-dims[1]/2-.35,.028)) + offset
        obj.rotation_euler = (0,0,0)
    plates = [o for o in root.children if o.get('fab_kind') == 'label_plate']
    width = max(.7,sum(1.0 if ord(c)>0x2fff else .62 for c in obj.data.body)*root.fab.size+.22)
    height = root.fab.size*1.6
    plate = plates[0] if plates else g.box('Label plate',(0,0,0),(1,1,.018),col,scene_material(scene,'label_plate'),.022)
    plate['fab_kind']='label_plate'
    plate.parent=root
    plate.hide_select=True
    # Object scale is acceptable for this decorative plaque; it is not equipment geometry.
    plate.scale=(width,height,1)
    plate.rotation_euler=obj.rotation_euler
    plate.location=obj.location - obj.rotation_euler.to_matrix() @ Vector((0,0,.014))
    plate.hide_render=obj.hide_render
    plate.hide_viewport=obj.hide_viewport


def sync_labels(scene):
    seen = set()
    for root in roots(scene):
        if root['fab_id'] in seen:
            root['fab_id'] = uuid.uuid4().hex
        seen.add(root['fab_id'])
        update_label(scene, root)
    for obj in scene.objects:
        if obj.get('fab_kind') in {'heading','heading_plate'} and scene.camera:
            obj.rotation_euler=scene.camera.rotation_euler
            obj.location=obj.get('fab_heading_origin',(0,4.5,10.7))
            if obj.get('fab_kind')=='heading':
                obj.location+=scene.camera.rotation_euler.to_matrix() @ Vector((0,0,.045))
        if obj.get('fab_kind') == 'title':
            obj.data.body = scene.fab.title
            if scene.fab.font_path:
                path = Path(bpy.path.abspath(scene.fab.font_path))
                if path.is_file():
                    obj.data.font = bpy.data.fonts.load(str(path), check_existing=True)


def apply_theme(scene):
    colors = DARK if scene.fab.theme == 'DARK' else LIGHT
    for mat in bpy.data.materials:
        if mat.get('fab_owner') != owner(scene):
            continue
        role = mat.get('fab_role','white')
        color = 'F2B54D' if mat.get('fab_highlight') and role in {'mint','blue','ice'} else colors.get(role,'FCF8EF')
        mat.diffuse_color = g.linear(color)
        node = mat.node_tree.nodes.get('Principled BSDF')
        if node:
            node.inputs['Base Color'].default_value = mat.diffuse_color
    if scene.world:
        scene.world.color = (.05,.05,.05)
        node = scene.world.node_tree.nodes.get('Background')
        if node:
            node.inputs[0].default_value = g.linear(colors['ground'])
            node.inputs[1].default_value = .5 if scene.fab.theme == 'LIGHT' else .35
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.get('fab_power'):
            obj.data.energy = obj['fab_power'] * (1 if scene.fab.theme == 'LIGHT' else 1.15)
    sync_labels(scene)


def adopt(scene, root):
    aid = root.get('fab_asset') or (root.instance_collection.get('fab_asset') if root.instance_collection else None)
    if not aid:
        raise ValueError('Select a FAB collection instance from the library.')
    if not root.get('fab_id'):
        root['fab_asset'], root['fab_id'], root['fab_version'] = aid, uuid.uuid4().hex, VERSION
        root.instance_collection = master(scene, aid)
        root.fab.label = root.instance_collection.get('fab_name',aid)
    seen = [o for o in roots(scene) if o != root and o['fab_id'] == root['fab_id']]
    if seen:
        root['fab_id'] = uuid.uuid4().hex
    snap(scene, root)
    update_label(scene, root)


def snap(scene, root):
    step = float(scene.fab.grid)
    if step:
        root.location.x = round(root.location.x/step)*step
        root.location.y = round(root.location.y/step)*step
    kind = root.instance_collection.get('fab_mount','FLOOR') if root.instance_collection else root.get('fab_mount','FLOOR')
    # A room cannot be placed on top of its own walking surface.
    if kind != 'OVERHEAD' and scene.fab.placement == 'CLEANROOM' and root == room_for(scene):
        return
    root.location.z = scene.fab.oht_height if kind == 'OVERHEAD' else placement_height(scene)


def room_for(scene):
    chosen = scene.fab.room
    if chosen and chosen.name in scene.objects and chosen.get('fab_asset') == 'cleanroom':
        return chosen
    return next((obj for obj in roots(scene) if obj.get('fab_asset') == 'cleanroom'), None)


def asset_size(root):
    return root.instance_collection.get('fab_size',(1,1,1)) if root.instance_collection else root.get('fab_size',(1,1,1))


def placement_height(scene):
    mode = scene.fab.placement
    if mode == 'CURSOR':
        return scene.cursor.location.z
    if mode == 'STAGE':
        top = next((obj for obj in scene.objects if obj.get('fab_kind') == 'stage_top'), None)
        return max((top.matrix_world @ Vector(v)).z for v in top.bound_box) if top else .39
    if mode == 'CLEANROOM':
        room = room_for(scene)
        if not room:
            raise ValueError('No cleanroom in this scene. Choose Stage, Cursor or Custom height.')
        # Authored cleanroom walking surface is 0.40 m above its assembly origin.
        return (room.matrix_world @ Vector((0,0,.40))).z
    return scene.fab.floor_z


def migrate_scene(scene):
    """Unlock legacy space assets once; later user locks remain intentional."""
    if not scene.fab.enabled or scene.get('fab_ui_version',0) >= 2:
        return
    for root in roots(scene):
        if root.get('fab_asset') in {'cleanroom','utility_pad'}:
            root.hide_select = False
    scene['fab_ui_version'] = 2


def set_overhead_visibility(scene):
    for obj in scene.objects:
        ancestor = obj
        overhead = False
        while ancestor:
            col = ancestor.instance_collection
            if (ancestor.get('fab_kind') == 'oht_loop' or
                (col and col.get('fab_mount') == 'OVERHEAD') or
                ancestor.get('fab_mount') == 'OVERHEAD'):
                overhead = True
                break
            ancestor = ancestor.parent
        if overhead:
            obj.hide_render = obj.hide_viewport = not scene.fab.overhead_visible


def duplicate(scene, root, delta):
    if not root.get('fab_id'):
        adopt(scene,root)
    dup = root.copy()
    collection(scene,'Assets').objects.link(dup)
    dup['fab_id'] = uuid.uuid4().hex
    dup.location += Vector(delta)
    if root.instance_type != 'COLLECTION':
        for child in root.children:
            if child.get('fab_kind') in {'label','label_plate'}:
                continue
            obj = child.copy()
            if child.data:
                obj.data = child.data.copy()
            collection(scene,'Assets').objects.link(obj)
            obj.parent = dup
    update_label(scene,dup)
    return dup


def highlight(scene, root, enabled):
    if root.instance_collection:
        root.instance_collection = master(scene, root['fab_asset'], enabled)
    else:
        for obj in root.children:
            if obj.type not in {'MESH','CURVE'}:
                continue
            for i,mat in enumerate(obj.data.materials):
                if mat:
                    obj.data.materials[i] = scene_material(scene,mat.get('fab_role','white'),enabled)


def make_editable(scene, root):
    src = root.instance_collection
    if not src:
        return
    root['fab_size'] = src.get('fab_size', (1,1,1))
    root['fab_mount'] = src.get('fab_mount','FLOOR')
    root.hide_select = False
    target = collection(scene, 'Assets')
    offset = Matrix.Translation(-src.instance_offset)
    # Linking copies invalidates Blender's live all_objects iterator.
    for obj in list(src.all_objects):
        dup = obj.copy()
        if obj.data:
            dup.data = obj.data.copy()
        target.objects.link(dup)
        dup.parent = root
        dup.matrix_parent_inverse = Matrix.Identity(4)
        dup.matrix_basis = offset @ obj.matrix_world
        dup.hide_select = False
    root.instance_type = 'NONE'
    root.instance_collection = None


def world_bounds(scene, only=None):
    points = []
    for obj in scene.objects:
        if obj.hide_render or obj.type in {'CAMERA','LIGHT'} or obj.get('fab_kind') == 'ground':
            continue
        if only and obj not in only and obj.parent not in only:
            continue
        if obj.instance_collection:
            for child in obj.instance_collection.all_objects:
                if child.type in {'MESH','CURVE','FONT'} and not child.hide_render:
                    transform = obj.matrix_world @ Matrix.Translation(-obj.instance_collection.instance_offset) @ child.matrix_world
                    points.extend(transform @ Vector(v) for v in child.bound_box)
        elif obj.type in {'MESH','CURVE','FONT'}:
            points.extend(obj.matrix_world @ Vector(v) for v in obj.bound_box)
    return points


def fit_camera(scene, only=None):
    camera = scene.camera
    if not camera:
        raise ValueError('The scene has no camera.')
    sync_labels(scene)
    bpy.context.view_layer.update()
    points = world_bounds(scene, only)
    if not points:
        return
    rot = camera.rotation_euler.to_matrix()
    local = [rot.inverted() @ p for p in points]
    lo = Vector([min(p[i] for p in local) for i in range(3)])
    hi = Vector([max(p[i] for p in local) for i in range(3)])
    center = (lo+hi)/2
    camera.location = rot @ (center + Vector((0,0,65)))
    aspect = scene.render.resolution_x / scene.render.resolution_y
    # Ortho scale is the horizontal width for landscape renders.
    camera.data.ortho_scale = max(hi.x-lo.x, (hi.y-lo.y)*aspect) * 1.16
    camera.data.clip_end = 500
    sync_labels(scene)


def resize_stage(scene):
    for obj in scene.objects:
        role = obj.get('fab_kind')
        if role in {'stage','stage_trim','stage_top'}:
            w = scene.fab.width - (.16 if role == 'stage_top' else 0)
            d = scene.fab.depth - (.16 if role == 'stage_top' else 0)
            # Change mesh coordinates so the bevel width stays physical.
            xs = [v.co.x for v in obj.data.vertices]
            ys = [v.co.y for v in obj.data.vertices]
            sx, sy = w/(max(xs)-min(xs)), d/(max(ys)-min(ys))
            for vert in obj.data.vertices:
                vert.co.x *= sx
                vert.co.y *= sy
        elif role == 'title':
            obj.location.y = -scene.fab.depth/2 + .65


def construct_scene(name='FAB Overview', overview=True):
    """Build-time template authoring, never resets the current scene."""
    scene = bpy.data.scenes.new(name)
    scene.fab.enabled = True
    scene.fab.width, scene.fab.depth = 30, 25
    scene.fab.floor_z = .39
    stage, rig = collection(scene,'Stage'), collection(scene,'Rig')
    for role,z,dims,mat,bevel in [
        ('stage',.0,(30,25,.58),'navy',.25),
        ('stage_trim',.24,(30,25,.07),'mint',.025),
        ('stage_top',.30,(29.84,24.84,.18),'floor',.16),
        ('ground',-.50,(200,200,.4),'ground',0)]:
        obj=g.box('FAB '+role,(0,0,z),dims,stage,scene_material(scene,mat),bevel)
        obj['fab_kind']=role
        obj.hide_select=True
    title=g.text('FAB Title',scene.fab.title,(0,-11.85,.405),.44,stage,scene_material(scene,'label'))
    title['fab_kind']='title'
    title.hide_select=True
    camdata=bpy.data.cameras.new('FAB Isometric')
    camera=bpy.data.objects.new('FAB Isometric',camdata)
    rig.objects.link(camera)
    camera.location=(28,-28,28.6)
    g.aim(camera,(0,0,.6))
    camera.data.type='ORTHO'
    camera.data.ortho_scale=43
    scene.camera=camera
    for name,pos,power,size in [('Key',(-9,-10,22),4400,14),('Fill',(13,-3,18),3000,12),('Rim',(0,15,21),4000,12)]:
        data=bpy.data.lights.new('FAB '+name,'AREA')
        data.energy,data.size,data.shape=power,size,'DISK'
        obj=bpy.data.objects.new('FAB '+name,data)
        rig.objects.link(obj)
        obj.location=pos
        obj['fab_power']=power
        g.aim(obj,(0,0,0))
    scene.world=bpy.data.worlds.new('FAB World')
    scene.world.use_nodes=True
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples=64
    scene.render.resolution_x,scene.render.resolution_y=2400,1800
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.unit_settings.system='METRIC'
    if overview:
        room=add_asset(scene,'cleanroom',(0,0,.39),label=False)
        room['fab_template']=True
        scene.fab.floor_z=.79
    scene.fab.placement='CLEANROOM' if overview else 'STAGE'
    scene['fab_ui_version']=2
    apply_theme(scene)
    return scene


def load_template(context, kind):
    path=data_dir()/'templates'/f'{kind.lower()}.blend'
    if not path.is_file():
        raise FileNotFoundError('Template missing: '+path.name)
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):
        dst.scenes=[src.scenes[0]]
    scene=dst.scenes[0]
    scene.name='FAB '+kind.title()
    scene.fab.template=kind
    scene['fab_owner']=uuid.uuid4().hex
    # Appended scenes must own instance data too: Blender may reuse dependencies.
    replacements={}
    for root in roots(scene):
        if root.instance_collection:
            src=root.instance_collection
            if src not in replacements:
                col=copy_collection(src)
                col['fab_owner']=owner(scene)
                replacements[src]=col
                local_materials(scene,col,bool(col.get('fab_highlight')))
            root.instance_collection=replacements[src]
        root['fab_id']=uuid.uuid4().hex
    for obj in scene.objects:
        if obj.type in {'MESH','CURVE','FONT'}:
            obj.data=obj.data.copy()
            for i,mat in enumerate(obj.data.materials):
                if mat:
                    obj.data.materials[i]=scene_material(scene,mat.get('fab_role','white'))
        elif obj.type in {'LIGHT','CAMERA'}:
            obj.data=obj.data.copy()
    scene.world=scene.world.copy()
    migrate_scene(scene)
    if context.window:
        context.window.scene=scene
    apply_theme(scene)
    return scene


def add_oht_loop(scene, center=(0,0), width=10, depth=6, height=4.7, radius=1.1):
    if min(width,depth) <= 2*radius:
        raise ValueError('Loop dimensions must exceed two corner radii.')
    col=collection(scene,'Assets')
    pts=[]
    # Clockwise rounded rectangle, all rails use a single continuous centerline.
    for cx,cy,start in [(width/2-radius,depth/2-radius,0),(-width/2+radius,depth/2-radius,90),
                        (-width/2+radius,-depth/2+radius,180),(width/2-radius,-depth/2+radius,270)]:
        for i in range(17):
            a=math.radians(start+i*90/16)
            pts.append((center[0]+cx+radius*math.cos(a),center[1]+cy+radius*math.sin(a),height))
    pts.append(pts[0])
    root=bpy.data.objects.new('OHT loop',None)
    col.objects.link(root)
    root['fab_kind']='oht_loop'
    rail=g.curve('OHT closed rail',pts,.075,col,scene_material(scene,'steel'))
    rail.parent=root
    strip=g.curve('OHT mint guide',[(x,y,z-.05) for x,y,z in pts],.024,col,scene_material(scene,'mint'))
    strip.parent=root
    for x,y in [(-width/2+radius,-depth/2),(width/2-radius,depth/2)]:
        support=add_asset(scene,'oht_support',(center[0]+x,center[1]+y,height),label=False)
        support.parent=root
    carrier=add_asset(scene,'oht_vehicle',(center[0],center[1]-depth/2,height),label=False)
    carrier.parent=root
    return root


def connect_rail(scene, source, next_asset):
    if not source.instance_collection:
        raise ValueError('Select a rail instance.')
    src=source.instance_collection
    if 'fab_end' not in src:
        raise ValueError('Selected asset is not a rail segment.')
    pos=source.matrix_world @ Vector(src['fab_end'])
    angle=source.rotation_euler.z + float(src.get('fab_end_angle',0))
    return add_asset(scene,next_asset,pos,angle,label=False)


def report(scene):
    issues=[]
    ids=set()
    for root in roots(scene):
        if root['fab_id'] in ids:
            issues.append('Duplicate identifier: '+root.name)
        ids.add(root['fab_id'])
        if root.instance_type=='COLLECTION' and not root.instance_collection:
            issues.append('Missing model: '+root.name)
        if not all(math.isfinite(v) for v in (*root.location,*root.rotation_euler,*root.scale)):
            issues.append('Non-finite transform: '+root.name)
        if abs(root.location.x)>scene.fab.width/2 or abs(root.location.y)>scene.fab.depth/2:
            issues.append('Outside stage center bounds: '+root.name)
    if not scene.camera:
        issues.append('Missing camera')
    if scene.fab.font_path and not Path(bpy.path.abspath(scene.fab.font_path)).is_file():
        issues.append('Selected font path is missing')
    return issues


def next_path(folder, stem, suffix):
    folder=Path(bpy.path.abspath(str(folder))).resolve()
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(stem+suffix)
    i=1
    while path.exists():
        path=folder/f'{stem}_{i:03d}{suffix}'
        i+=1
    return path
