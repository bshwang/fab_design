"""FAB Author: local guided measurement, text interchange and asset registration."""
import json
import math
from pathlib import Path
import textwrap
import uuid
import zlib
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, PointerProperty, StringProperty)
from bpy_extras.io_utils import ImportHelper, ExportHelper
from mathutils import Euler, Vector
from . import author_spec as spec, author_model as model
from . import quick_spec, quick_capture

_parent_items={}


def type_changed(self,context):
    self.add_role=spec.TYPES[self.asset_type][2][0]


def parent_items(self,context):
    values=[('ROOT','Asset Root','No parent',0)]
    if context and hasattr(context.scene,'fab_author'):
        values += [(p.part_id,p.name,'Assembly relationship; transforms stay in asset space',
                    (zlib.crc32(p.part_id.encode()) & 0x7fffffff) or 1)
                   for p in context.scene.fab_author.parts if p.part_id and p!=self]
    _parent_items[self.as_pointer()]=values
    return values


class FABAuthorBinding(bpy.types.PropertyGroup):
    object:PointerProperty(type=bpy.types.Object)


class FABAuthorPart(bpy.types.PropertyGroup):
    part_id:StringProperty()
    role:EnumProperty(name='Role',items=[(k,v[0],v[0]) for k,v in spec.ROLES.items()])
    parent_key:EnumProperty(name='Parent',items=parent_items)
    enabled:BoolProperty(name='Include in model',default=True)
    configured:BoolProperty(default=False)
    source:StringProperty(default='manual')
    shape:EnumProperty(name='Shape',items=[(x,x.title(),'Primitive in component local coordinates') for x in spec.SHAPES])
    position:FloatVectorProperty(name='Position (m)',size=3,precision=5)
    rotation:FloatVectorProperty(name='Rotation',size=3,subtype='EULER')
    size:FloatVectorProperty(name='Size (m)',size=3,default=(1,1,1),min=.000001,max=10000,precision=5)
    material:EnumProperty(name='Material role',items=[(x,x.title(),'Uses the FAB palette') for x in spec.MATERIALS])
    bevel:FloatProperty(name='Bevel / smallest side',default=.025,min=0,max=.2,precision=3)
    taper:FloatProperty(name='Top / bottom width',default=.8,min=.05,max=2)
    radius:FloatProperty(name='Path radius (m)',default=.025,min=.000001,max=100,precision=5)
    points_json:StringProperty(default='[]')
    joint_enabled:BoolProperty(name='Record joint center / axis')
    joint_center:FloatVectorProperty(name='Joint center (m)',size=3,precision=5)
    joint_axis:FloatVectorProperty(name='Joint axis',size=3,default=(0,0,1),min=-1,max=1,precision=5)
    notes:StringProperty(name='Component notes',maxlen=2000)
    bindings:CollectionProperty(type=FABAuthorBinding)


class FABAuthorSettings(bpy.types.PropertyGroup):
    workflow:EnumProperty(name='Workflow',items=[('QUICK','Quick Capture','Select the whole model; describe its features'),('ADVANCED','Advanced','Detailed component authoring and local library')],default='QUICK')
    quick_type:EnumProperty(name='Type',items=[(k,v[0],v[1]) for k,v in spec.TYPES.items()],default='AMMR')
    quick_features:StringProperty(name='Key features',description='Describe the silhouette and distinctive parts, in up to 240 characters',maxlen=240)
    quick_units:EnumProperty(name='Units',items=[('SCENE','Scene units','Use the current scene scale'),('CUSTOM','Custom','Set meters per Blender unit')],default='SCENE')
    quick_scale:FloatProperty(name='Meters / unit',default=1,min=.000001,max=1000,precision=6)
    quick_rotation:FloatVectorProperty(name='Reference rotation',size=3,subtype='EULER',description='Orientation of the asset frame in world space; local -Y is front, +Z is up')
    quick_options:BoolProperty(name='Units / front direction')
    quick_receive:BoolProperty(name='Receive a result')
    quick_text:StringProperty()
    quick_result:StringProperty()
    quick_signature:StringProperty()
    quick_status:StringProperty()
    quick_preview:PointerProperty(type=bpy.types.Object)
    document_id:StringProperty()
    asset_name:StringProperty(name='Asset name',default='My Asset',maxlen=160)
    asset_type:EnumProperty(name='Asset type',items=[(k,v[0],v[1]) for k,v in spec.TYPES.items()],default='AMMR',update=type_changed)
    step:EnumProperty(name='Step',items=[('SETUP','1 Setup','Reference frame'),('PARTS','2 Parts','Assign and measure'),
        ('REVIEW','3 Review','Preview and exchange text'),('LIBRARY','4 Library','Reuse generated assets')],default='SETUP')
    parts:CollectionProperty(type=FABAuthorPart)
    active_part:IntProperty(default=0,min=0)
    add_role:EnumProperty(name='New component role',items=[(k,v[0],v[0]) for k,v in spec.ROLES.items()],default='BASE')
    meters_per_unit:FloatProperty(name='Meters / Blender unit',default=1,min=.000001,max=1000,precision=6)
    origin:FloatVectorProperty(name='Reference origin (BU)',size=3,precision=5)
    orientation:FloatVectorProperty(name='Reference rotation',size=3,subtype='EULER')
    frame_locked:BoolProperty(default=False)
    measure_axes:EnumProperty(name='Measure along',items=[('ASSET','Asset axes','Use the reference frame axes'),
        ('ACTIVE','Active object axes','Use active object rotation; mesh transforms remain evaluated')],default='ACTIVE')
    joint_axis_pick:EnumProperty(name='Active local axis',items=[('X','X',''),('Y','Y',''),('Z','Z','')],default='Z')
    features:StringProperty(name='Recognizable features',maxlen=2000)
    omit:StringProperty(name='Omit / simplify',default='Small fasteners and hidden internals',maxlen=2000)
    theme:EnumProperty(name='Preview theme',items=[('LIGHT','Light',''),('DARK','Dark','')],default='LIGHT')
    preview_offset:FloatVectorProperty(name='Preview offset (m)',size=3,default=(3,0,0),precision=3)
    preview:PointerProperty(type=bpy.types.Object)
    text:PointerProperty(type=bpy.types.Text)
    status:StringProperty()
    show_transform:BoolProperty(name='Position / rotation',default=False)
    show_details:BoolProperty(name='Shape / material details',default=False)
    show_joint:BoolProperty(name='Joint / axes',default=False)
    show_points:BoolProperty(name='Outline / path capture',default=False)


def current(settings):
    return settings.parts[settings.active_part] if settings.active_part<len(settings.parts) else None


def document(settings):
    if not settings.document_id:
        # Pure reads (panel draw) must not mutate RNA.
        identifier='asset_draft'
    else:
        identifier=settings.document_id
    doc=spec.new_document(settings.asset_type,settings.asset_name)
    doc.update(id=identifier,features=settings.features,omit=settings.omit)
    doc['style']['theme']=settings.theme
    for p in settings.parts:
        data=spec.new_part(p.role,p.name)
        data.update(id=p.part_id,parent='' if p.parent_key in {'ROOT',''} else p.parent_key,
                    enabled=p.enabled,configured=p.configured,source=p.source,shape=p.shape,
                    position=list(p.position),rotation=[math.degrees(x) for x in p.rotation],size=list(p.size),
                    material=p.material,bevel=p.bevel,taper=p.taper,radius=p.radius,
                    points=json.loads(p.points_json),notes=p.notes)
        data['joint']={'enabled':p.joint_enabled,'center':list(p.joint_center),'axis':list(p.joint_axis)}
        doc['parts'].append(data)
    return spec.validate(doc)


def ensure_id(settings):
    if not settings.document_id:
        settings.document_id='asset_'+uuid.uuid4().hex[:12]


def assign_part(part,data):
    part.name=data['name']; part.part_id=data['id']
    for key in ('role','enabled','configured','source','shape','position','size','material','bevel','taper','radius','notes'):
        setattr(part,key,data[key])
    part.rotation=[math.radians(v) for v in data['rotation']]
    part.points_json=json.dumps(data['points'])
    part.joint_enabled=data['joint']['enabled']; part.joint_center=data['joint']['center']; part.joint_axis=data['joint']['axis']


def read_document(settings,text):
    doc=spec.loads(text)  # Full validation before changing the existing draft.
    same=settings.document_id==doc['id']
    bindings={p.part_id:[r.object for r in p.bindings if r.object] for p in settings.parts} if same else {}
    if settings.parts:
        archive=bpy.data.texts.new('FAB Previous Brief')
        try:
            archive.write(spec.dumps(document(settings)))
        except ValueError:
            archive.write('Previous draft could not be serialized. Use Undo to restore it.')
    settings.parts.clear()
    settings.document_id=doc['id']; settings.asset_name=doc['name']; settings.asset_type=doc['type']
    settings.features=doc['features']; settings.omit=doc['omit']; settings.theme=doc['style']['theme']
    for data in doc['parts']:
        p=settings.parts.add(); assign_part(p,data)
        for obj in bindings.get(p.part_id,[]):
            p.bindings.add().object=obj
    for p,data in zip(settings.parts,doc['parts']):
        p.parent_key=data['parent'] or 'ROOT'
    if not same:
        settings.origin=(0,0,0); settings.orientation=(0,0,0); settings.meters_per_unit=1
        settings.frame_locked=False
        settings.preview=None
    settings.active_part=0; settings.step='REVIEW'
    return doc


def local_directory(context):
    addon=context.preferences.addons.get(__package__)
    return bpy.path.abspath(addon.preferences.local_library_path) if addon and addon.preferences.local_library_path else ''


def register_local_library(context,path):
    resolved=Path(path).resolve()
    libraries=context.preferences.filepaths.asset_libraries
    lib=next((l for l in libraries if Path(bpy.path.abspath(l.path)).resolve()==resolved),None)
    if not lib:
        lib=libraries.new(name='FAB Local Assets',directory=str(resolved))
    lib.import_method='APPEND_REUSE'
    return lib


class FABAUTHOR_OT_action(bpy.types.Operator):
    bl_idname='fab_author.action'
    bl_label='FAB Author'
    bl_options={'REGISTER','UNDO'}
    action:StringProperty()
    role:StringProperty()
    def execute(self,context):
        s=context.scene.fab_author; p=current(s)
        try:
            ensure_id(s)
            if self.action=='NEW':
                read_document(s,spec.dumps(spec.new_document(s.asset_type,'My Asset')))
                s.step='SETUP'; s.status='New draft ready. Previous brief is archived in Text blocks; source objects and previews are preserved.'
            elif self.action=='ADD':
                if len(s.parts)>=spec.MAX_PARTS:
                    raise ValueError('Component limit reached.')
                data=spec.new_part(self.role if self.role in spec.ROLES else s.add_role)
                base=data['name']; names={x.name for x in s.parts}; n=2
                while data['name'] in names:
                    data['name']=base+' '+str(n); n+=1
                p=s.parts.add(); assign_part(p,data); p.parent_key='ROOT'; s.active_part=len(s.parts)-1
                s.status='Select the reference objects, then Measure Selection.'
            elif self.action=='REMOVE':
                if not p:
                    raise ValueError('Select a component row first.')
                pid=p.part_id
                for child in s.parts:
                    if child!=p and child.parent_key==pid:
                        child.parent_key='ROOT'
                s.parts.remove(s.active_part); s.active_part=max(0,s.active_part-1)
                s.status='Component removed from this draft. Source geometry is unchanged.'
            elif self.action in {'MEASURE','REMEASURE','CONFIRM','SHOW','UNBIND','JOINT_CENTER','JOINT_AXIS','POINTS'}:
                if not p:
                    raise ValueError('Add or select a component first.')
                if self.action in {'MEASURE','REMEASURE'}:
                    if context.mode!='OBJECT':
                        raise ValueError('Return to Object Mode to measure components.')
                    vertices,objects=model.measure(context,s,p,self.action=='REMEASURE')
                    s.status=f'Measured {objects} objects / {vertices:,} evaluated vertices.'
                elif self.action=='CONFIRM':
                    p.configured=True; p.source='manual'; s.status='Entered dimensions confirmed.'
                elif self.action=='SHOW':
                    objects=[r.object for r in p.bindings if r.object and r.object.name in context.scene.objects]
                    if not objects:
                        raise ValueError('No local source bindings. Select objects and Measure Selection.')
                    for obj in context.selected_objects:
                        obj.select_set(False)
                    for obj in objects:
                        obj.hide_set(False); obj.select_set(True)
                    context.view_layer.objects.active=objects[0]
                    s.status=f'Selected {len(objects)} assigned source objects.'
                elif self.action=='UNBIND':
                    p.bindings.clear(); s.status='Source links cleared; measured values kept.'
                elif self.action=='JOINT_CENTER':
                    p.joint_center=(model.frame(s).inverted() @ context.scene.cursor.location)*s.meters_per_unit
                    p.joint_enabled=True; s.status='Joint center captured from the 3D Cursor.'
                    s.frame_locked=True
                elif self.action=='JOINT_AXIS':
                    obj=context.active_object
                    if not obj:
                        raise ValueError('Select a reference object for its local axis.')
                    axis=Vector(tuple(1 if i=='XYZ'.index(s.joint_axis_pick) else 0 for i in range(3)))
                    p.joint_axis=(model.frame(s).to_3x3().inverted() @ (obj.matrix_world.to_quaternion() @ axis)).normalized()
                    p.joint_enabled=True; s.status='Joint axis captured; verify its direction in the viewport.'
                    s.frame_locked=True
                elif self.action=='POINTS':
                    count=model.capture_points(context,s,p); s.status=f'Captured {count} ordered points. Return to Object Mode to preview.'
            elif self.action in {'UNITS','ORIGIN_CURSOR','ORIGIN_FLOOR','FRAME_ACTIVE'}:
                if s.frame_locked:
                    raise ValueError('Reference frame is locked after measuring. Use a new scene/draft for a different frame.')
                if self.action=='UNITS':
                    s.meters_per_unit=context.scene.unit_settings.scale_length
                elif self.action=='ORIGIN_CURSOR':
                    s.origin=context.scene.cursor.location
                elif self.action=='ORIGIN_FLOOR':
                    model.selection_floor(context,s)
                else:
                    if not context.active_object:
                        raise ValueError('Select a reference object for orientation.')
                    s.orientation=context.active_object.matrix_world.to_quaternion().to_euler('XYZ')
                s.status='Reference frame updated. +Z is up; -Y is front in the exported asset.'
            elif self.action=='PREVIEW':
                if context.mode!='OBJECT':
                    raise ValueError('Return to Object Mode to generate a preview.')
                model.preview(context,s,document(s))
                s.status='New preview created beside the reference. Older previews are preserved.'
            elif self.action=='SELECT_PREVIEW':
                if not s.preview or s.preview.name not in context.scene.objects:
                    raise ValueError('Generate a preview first.')
                from . import core
                core.select(context,s.preview)
            elif self.action=='GUIDES':
                model.show_guides(context,s,p if s.step=='PARTS' else None)
                s.status='Reference axes and selected component guides updated. Guides do not render.'
            elif self.action in {'TEXT','COPY'}:
                doc=document(s); text=spec.dumps(doc)
                if self.action=='COPY':
                    context.window_manager.clipboard=text
                    if context.window_manager.clipboard!=text:
                        raise ValueError('Clipboard unavailable. Use Export JSON or Create Text Block.')
                    s.status='JSON copied. Transfer it manually when ready.'
                else:
                    block=bpy.data.texts.new('FAB Brief / '+s.asset_name+'.json'); block.write(text); s.text=block
                    s.status='JSON created in a new Blender Text block. Choose it in the Text Editor.'
            elif self.action=='PASTE':
                read_document(s,context.window_manager.clipboard)
                s.status='Imported JSON from clipboard. Review components and generate a preview.'
            elif self.action=='IMPORT_TEXT':
                if not s.text:
                    raise ValueError('Choose a Blender Text block first.')
                read_document(s,s.text.as_string()); s.status='Imported the selected Text block.'
            elif self.action=='EXAMPLE':
                if s.parts:
                    raise ValueError('Open a new Blender Scene to load the example without replacing your draft.')
                example=Path(__file__).parent/'data/author_examples/ammr_example.json'
                read_document(s,example.read_text(encoding='utf-8'))
                s.status='Synthetic AMMR example loaded. Generate New Preview to try the text workflow.'
            elif self.action=='SAVE_LIBRARY':
                path=local_directory(context)
                if not path:
                    raise ValueError('Choose a Local Library folder first.')
                aid,filename=model.save_library(document(s),path)
                register_local_library(context,path)
                s.status='Registered '+s.asset_name+'. Find it in FAB Kit / Add Assets.'
            else:
                raise ValueError('Unknown Author action')
        except (ValueError,OSError,RuntimeError,TypeError,KeyError) as exc:
            s.status=str(exc)[:400]; self.report({'ERROR'},s.status); return {'CANCELLED'}
        return {'FINISHED'}


class FABAUTHOR_OT_export(bpy.types.Operator,ExportHelper):
    bl_idname='fab_author.export_brief'
    bl_label='Export Brief JSON'
    filename_ext='.json'
    filter_glob:StringProperty(default='*.json',options={'HIDDEN'})
    def execute(self,context):
        s=context.scene.fab_author
        try:
            ensure_id(s); doc=document(s)
            target=Path(self.filepath)
            target.write_text(spec.dumps(doc),encoding='utf-8')
            # Companion has a unique extension so no unrelated .txt file is overwritten.
            target.with_suffix('.summary.txt').write_text(spec.summary(doc),encoding='utf-8')
            errors,_=spec.issues(doc)
            s.status='Exported '+('draft (review incomplete components).' if errors else 'JSON and readable summary.')
            self.report({'INFO'},s.status)
            return {'FINISHED'}
        except (ValueError,OSError) as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class FABAUTHOR_OT_import(bpy.types.Operator,ImportHelper):
    bl_idname='fab_author.import_brief'
    bl_label='Import Brief / Recipe JSON'
    bl_options={'REGISTER','UNDO'}
    filename_ext='.json'
    filter_glob:StringProperty(default='*.json;*.txt',options={'HIDDEN'})
    def execute(self,context):
        try:
            path=Path(self.filepath)
            if path.stat().st_size>spec.MAX_BYTES:
                raise ValueError('Brief exceeds 2 MB')
            read_document(context.scene.fab_author,path.read_text(encoding='utf-8-sig'))
            context.scene.fab_author.status='Imported. Source bindings stay local; verify the reference frame when measuring again.'
            return {'FINISHED'}
        except (ValueError,OSError,UnicodeError) as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class FABAUTHOR_OT_import_asset(bpy.types.Operator,ImportHelper):
    bl_idname='fab_author.import_asset'
    bl_label='Import FAB Author Asset'
    filename_ext='.blend'
    filter_glob:StringProperty(default='*.blend',options={'HIDDEN'})
    def execute(self,context):
        directory=local_directory(context)
        try:
            if not directory:
                raise ValueError('Choose a Local Library folder first.')
            aid,filename=model.import_asset_file(self.filepath,directory)
            register_local_library(context,directory)
            context.scene.fab_author.status='Imported Author asset. Find it in FAB Kit / Add Assets.'
            return {'FINISHED'}
        except (OSError,ValueError,RuntimeError,TypeError,KeyError) as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class FABAUTHOR_UL_parts(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        row=layout.row(align=True)
        row.prop(item,'enabled',text='')
        row.label(text=item.name,icon='CHECKMARK' if item.configured else 'RADIOBUT_OFF')


def message(layout,text,context,icon=None):
    scale=max(context.preferences.system.ui_scale,.5)
    width=max(18,int(context.region.width/scale/7)-7) if context.region else 35
    layout=layout.column(align=True); layout.scale_y=.85
    for i,line in enumerate(textwrap.wrap(text,width)):
        layout.label(text=line,icon=icon if i==0 and icon else 'NONE')


def button(layout,action,text,icon='NONE',enabled=True):
    row=layout.row(); row.enabled=enabled
    row.operator('fab_author.action',text=text,icon=icon).action=action


def quick_signature(context,s):
    scale=context.scene.unit_settings.scale_length if s.quick_units=='SCENE' else s.quick_scale
    return json.dumps([s.quick_type,s.quick_features,scale,list(s.quick_rotation)],ensure_ascii=False)


def quick_ready(context,s):
    return bool(s.quick_text) and s.quick_signature==quick_signature(context,s)


def store_quick(context,s,result):
    # Preserve previous captures in .blend Text blocks; no automatic file/network export.
    if s.quick_text:
        archive=bpy.data.texts.new('FAB Previous Quick Capture'); archive.write(s.quick_text)
    previous=s.quick_preview
    quick_capture.preview(context,s,result)
    if previous and previous.name in context.scene.objects:
        previous.hide_set(True); previous.hide_render=True
    s.quick_text=result['text']; s.quick_result=json.dumps(result)
    s.quick_signature=quick_signature(context,s)


def receive_quick(context,s,text):
    packet,shapes=quick_spec.unpack(text)
    previous=json.loads(s.quick_result) if s.quick_result and s.quick_text==text else None
    if previous:
        unit,origin,rotation=previous['unit'],previous['origin'],previous['rotation']
    else:
        unit=context.scene.unit_settings.scale_length
        origin=list(context.scene.cursor.location); rotation=[0,0,0]
        if context.scene.fab.enabled: origin[2]=max(origin[2],context.scene.fab.floor_z)
    s.quick_type=packet['t']; s.quick_features=packet['f']
    s.quick_units='CUSTOM'; s.quick_scale=unit; s.quick_rotation=rotation
    result={'text':text,'dimensions':packet['d'],'objects':0,'vertices':0,'candidates':len(shapes),
            'kept':len(shapes),'small':0,'seconds':0,'unit':unit,'origin':origin,'rotation':rotation}
    store_quick(context,s,result)
    s.workflow='QUICK'
    s.quick_status='Received shape guide in meters. This is a geometric summary, not a finished asset.'


class FABAUTHOR_OT_quick(bpy.types.Operator):
    bl_idname='fab_author.quick'
    bl_label='Quick Capture'
    bl_options={'UNDO'}
    action:StringProperty()
    def execute(self,context):
        s=context.scene.fab_author
        try:
            if self.action=='CAPTURE':
                result=quick_capture.capture(context,s)
                store_quick(context,s,result)
                s.quick_status=f"Captured {result['objects']} objects in {result['seconds']} s. Shape guide is beside the source; check proportions before copying."
            elif self.action=='COPY':
                if not quick_ready(context,s):
                    raise ValueError('Settings changed. Capture Selection again before copying.')
                quick_spec.unpack(s.quick_text)
                context.window_manager.clipboard=s.quick_text
                if context.window_manager.clipboard!=s.quick_text:
                    raise ValueError('Clipboard is unavailable. Use Save Text instead.')
                s.quick_status=f'Copied {quick_spec.count(s.quick_text)} / 1000 characters. Geometry edits require a new capture.'
            elif self.action=='PASTE':
                receive_quick(context,s,context.window_manager.clipboard)
            elif self.action=='ADVANCED':
                if not s.quick_text:
                    raise ValueError('Capture or paste Quick text first.')
                read_document(s,spec.dumps(quick_spec.recipe(s.quick_text)))
                s.workflow='ADVANCED'
                s.status='Quick shapes loaded as an editable draft. Roles and functional details still need interpretation.'
            elif self.action=='LIBRARY':
                s.workflow='ADVANCED'; s.step='LIBRARY'
            elif self.action=='SELECT':
                if not s.quick_preview or s.quick_preview.name not in context.scene.objects:
                    raise ValueError('The shape guide was removed. Capture again.')
                s.quick_preview.hide_set(False)
                from . import core
                core.select(context,s.quick_preview)
                s.quick_status='Shape guide selected. Reselect the original model before capturing again.'
            else:
                raise ValueError('Unknown Quick Capture action.')
            return {'FINISHED'}
        except (ValueError,RuntimeError,OSError,TypeError,KeyError,UnicodeError) as exc:
            s.quick_status=str(exc); self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class FABAUTHOR_OT_quick_export(bpy.types.Operator,ExportHelper):
    bl_idname='fab_author.quick_export'
    bl_label='Save Quick Capture Text'
    filename_ext='.txt'
    filter_glob:StringProperty(default='*.txt',options={'HIDDEN'})
    def execute(self,context):
        s=context.scene.fab_author
        try:
            if not quick_ready(context,s):
                raise ValueError('Capture Selection again before exporting changed settings.')
            quick_spec.unpack(s.quick_text)
            Path(self.filepath).write_text(s.quick_text,encoding='utf-8')
            s.quick_status=f'Saved {quick_spec.count(s.quick_text)} characters as UTF-8 text, without a trailing newline.'
            return {'FINISHED'}
        except (OSError,ValueError) as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class FABAUTHOR_OT_quick_import(bpy.types.Operator,ImportHelper):
    bl_idname='fab_author.quick_import'
    bl_label='Import Quick Capture Text'
    bl_options={'UNDO'}
    filename_ext='.txt'
    filter_glob:StringProperty(default='*.txt;*.json',options={'HIDDEN'})
    def execute(self,context):
        try:
            if context.mode!='OBJECT': raise ValueError('Return to Object Mode first.')
            path=Path(self.filepath)
            if path.stat().st_size>4000: raise ValueError('Quick Capture file exceeds the 1000-character format.')
            receive_quick(context,context.scene.fab_author,path.read_text(encoding='utf-8-sig'))
            return {'FINISHED'}
        except (ValueError,RuntimeError,OSError,UnicodeError) as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


def draw_quick(lay,context,s):
    message(lay,'1 Select the whole model in Object Mode.',context)
    message(lay,'2 Choose a type and describe what makes it recognizable.',context)
    lay.prop(s,'quick_type')
    lay.label(text='Key features (up to 240 characters)')
    lay.prop(s,'quick_features',text='')
    message(lay,'Example: Low base, rear arm, two-finger gripper, front scanner.',context)
    lay.prop(s,'quick_options',icon='TRIA_DOWN' if s.quick_options else 'TRIA_RIGHT',emboss=False)
    if s.quick_options:
        box=lay.box(); box.prop(s,'quick_units')
        if s.quick_units=='CUSTOM': box.prop(s,'quick_scale')
        box.prop(s,'quick_rotation')
        message(box,'Default: world +Z up, -Y front. Rotate this frame only if your source faces another direction. For millimeter-sized CAD coordinates, use Custom 0.001.',context)
    def action(layout,key,label,icon='NONE',enabled=True):
        row=layout.row(); row.enabled=enabled
        row.operator('fab_author.quick',text=label,icon=icon).action=key
    row=lay.row(); row.scale_y=1.35
    action(row,'CAPTURE','Capture Selection','OUTLINER_OB_MESH',context.mode=='OBJECT' and bool(context.selected_objects) and bool(s.quick_features.strip()))
    if s.quick_text:
        ready=quick_ready(context,s)
        result=json.loads(s.quick_result)
        box=lay.box(); box.label(text=f'{quick_spec.count(s.quick_text)} / 1000 characters',icon='CHECKMARK' if ready else 'ERROR')
        d=result['dimensions']
        message(box,'Size: '+ ' x '.join(f'{v:.3f}' for v in d)+' m',context)
        message(box,f"{result['kept']} shape envelopes / {result['candidates']} candidates; {result['small']} tiny islands omitted.",context)
        if max(d)>20 or max(d)<.05:
            message(box,'Unusual asset size. Check Units before sending.',context,'ERROR')
        if not ready:
            message(box,'Settings changed. Capture again to update the text.',context,'ERROR')
        message(box,'3 Compare the shape guide beside the source. Check size, front and key protrusions.',context)
        action(box,'SELECT','Select Shape Guide','RESTRICT_SELECT_OFF',bool(s.quick_preview))
        action(lay,'COPY','Copy Text (1000 max)','COPYDOWN',ready)
        row=lay.row(); row.enabled=ready; row.operator('fab_author.quick_export',text='Save Text...',icon='EXPORT')
        message(lay,'Snapshot only: capture again after editing geometry. The text summarizes envelopes; it does not contain the original mesh.',context)
    lay.prop(s,'quick_receive',icon='TRIA_DOWN' if s.quick_receive else 'TRIA_RIGHT',emboss=False)
    if s.quick_receive:
        box=lay.box()
        action(box,'PASTE','Paste Quick Text + Preview','PASTEDOWN',context.mode=='OBJECT')
        row=box.row(); row.enabled=context.mode=='OBJECT'; row.operator('fab_author.quick_import',text='Import Quick Text...',icon='IMPORT')
        action(box,'ADVANCED','Edit Summary in Advanced','EDITMODE_HLT',bool(s.quick_text))
        action(box,'LIBRARY','Import Finished Asset...','ASSET_MANAGER')
        message(box,'Paste reproduces the geometric guide. Import the returned Author .blend through Local Library to use the finished FAB asset.',context)
    if s.quick_status:
        message(lay.box(),s.quick_status,context,'INFO')


class FABAUTHOR_PT_main(bpy.types.Panel):
    bl_label='FAB Asset Author'
    bl_idname='FABAUTHOR_PT_main'
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='FAB Author'
    def draw(self,context):
        s=context.scene.fab_author; p=current(s); lay=self.layout
        lay.prop(s,'workflow',expand=True)
        if s.workflow=='QUICK':
            draw_quick(lay,context,s)
            return
        lay.prop(s,'step',expand=True)
        if s.step=='SETUP':
            lay.label(text='Asset name'); lay.prop(s,'asset_name',text='')
            lay.label(text='Asset type'); lay.prop(s,'asset_type',text='')
            message(lay,spec.TYPES[s.asset_type][1],context)
            box=lay.box(); box.label(text='Reference frame',icon='ORIENTATION_GLOBAL')
            message(box,'Set this before measuring. Exported values use meters, +Z up and -Y front.',context)
            editable=not s.frame_locked
            col=box.column(); col.enabled=editable
            col.prop(s,'meters_per_unit')
            button(col,'UNITS','Use Scene Unit Scale')
            col.prop(s,'orientation')
            button(col,'FRAME_ACTIVE','Use Active Object Orientation')
            col.prop(s,'origin')
            button(col,'ORIGIN_FLOOR','Origin at Selection Floor')
            button(col,'ORIGIN_CURSOR','Origin at 3D Cursor')
            if not editable:
                message(box,'Frame locked after measurement. Start a new asset draft for another reference frame.',context,'LOCKED')
            button(box,'GUIDES','Show Frame Axes','ORIENTATION_GLOBAL')
            message(lay,'Next: 2 Parts. Select source objects, add a component, then measure it.',context,'FORWARD')
            button(lay,'EXAMPLE','Try AMMR Example','FILE_BLEND',not s.parts)
            button(lay,'NEW','New Asset Draft','FILE_NEW',bool(s.parts))
        elif s.step=='PARTS':
            message(lay,'Suggested roles: '+', '.join(spec.ROLES[r][0] for r in spec.TYPES[s.asset_type][2]),context)
            quick=lay.grid_flow(columns=2,align=True)
            for role in spec.TYPES[s.asset_type][2]:
                op=quick.operator('fab_author.action',text='Add '+{'TOOL':'Tool','PORT':'Port'}.get(role,spec.ROLES[role][0]),icon='ADD')
                op.action='ADD'; op.role=role
            lay.prop(s,'add_role',text='Add role')
            row=lay.row(align=True)
            button(row,'ADD','Add Component','ADD')
            button(row,'REMOVE','Remove','REMOVE',bool(p))
            lay.template_list('FABAUTHOR_UL_parts','',s,'parts',s,'active_part',rows=5)
            if p:
                lay.prop(p,'name',text='Name'); lay.prop(p,'role'); lay.prop(p,'parent_key')
                lay.prop(s,'measure_axes',text='Axes')
                button(lay,'MEASURE','Measure Selection','DRIVER_DISTANCE',context.mode=='OBJECT')
                row=lay.row(align=True)
                button(row,'REMEASURE','Refresh','FILE_REFRESH',bool(p.bindings) and context.mode=='OBJECT')
                button(row,'SHOW','Show Assigned','RESTRICT_SELECT_OFF',bool(p.bindings) and context.mode=='OBJECT')
                message(lay,f'{len(p.bindings)} local source objects | '+('Measured / confirmed' if p.configured else 'Needs measurement or manual confirmation'),context)
                lay.prop(p,'size')
                button(lay,'CONFIRM','Use Entered Values','CHECKMARK')
                lay.prop(p,'shape')
                lay.prop(s,'show_transform',icon='TRIA_DOWN' if s.show_transform else 'TRIA_RIGHT',emboss=False)
                if s.show_transform:
                    box=lay.box(); box.prop(p,'position'); box.prop(p,'rotation')
                    button(box,'GUIDES','Show Component Bounds','CUBE')
                    message(box,'Absolute asset-space transform. Parent records the assembly relationship.',context)
                lay.prop(s,'show_details',icon='TRIA_DOWN' if s.show_details else 'TRIA_RIGHT',emboss=False)
                if s.show_details:
                    box=lay.box(); box.prop(p,'material'); box.prop(p,'bevel')
                    button(box,'UNBIND','Clear Source Links','UNLINKED',bool(p.bindings))
                    if p.shape=='TAPER': box.prop(p,'taper')
                    if p.shape=='PATH': box.prop(p,'radius')
                    box.prop(p,'notes')
                lay.prop(s,'show_joint',icon='TRIA_DOWN' if s.show_joint else 'TRIA_RIGHT',emboss=False)
                if s.show_joint:
                    box=lay.box(); box.prop(p,'joint_enabled'); box.prop(p,'joint_center')
                    button(box,'JOINT_CENTER','Joint Center from Cursor')
                    box.prop(p,'joint_axis'); box.prop(s,'joint_axis_pick',expand=True)
                    button(box,'JOINT_AXIS','Read Active Local Axis')
                    button(box,'GUIDES','Show Joint Axis','ORIENTATION_GIMBAL')
                    message(box,'Joint data describes the current pose. It does not create a rig.',context)
                if p.shape in {'PROFILE','PATH'}:
                    box=lay.box(); box.label(text='Outline / path points')
                    message(box,'Edit Mode: select one connected edge chain. Profile requires a closed local-XY outline; Size Z sets thickness.',context)
                    button(box,'POINTS','Capture Selected Edges','CURVE_DATA',context.mode=='EDIT_MESH')
                    try: count=len(json.loads(p.points_json))
                    except ValueError: count=0
                    box.label(text=f'{count} points recorded')
            else:
                message(lay,'Select a role and click Add Component. You can assign many CAD objects to one component.',context)
        elif s.step=='REVIEW':
            for key,label in [('asset_name','Asset name'),('features','Recognizable features'),('omit','Omit / simplify')]:
                lay.label(text=label); lay.prop(s,key,text='')
            try:
                doc=document(s); errors,warnings=spec.issues(doc)
                box=lay.box(); box.label(text=f'{len(doc["parts"])} components | {len(errors)} blocking issues',icon='ERROR' if errors else 'CHECKMARK')
                for text in (errors+warnings)[:5]:
                    message(box,text,context)
                if len(errors)+len(warnings)>5:
                    box.label(text='Full details in the exported summary.')
            except (ValueError,TypeError) as exc:
                errors=[str(exc)]; message(lay,errors[0],context,'ERROR')
            lay.prop(s,'theme',expand=True); lay.prop(s,'preview_offset')
            button(lay,'PREVIEW','Generate New Preview','SHADING_RENDERED',not errors and context.mode=='OBJECT')
            button(lay,'SELECT_PREVIEW','Select Latest Preview','RESTRICT_SELECT_OFF',bool(s.preview))
            message(lay,'Preview uses only the exported brief. Original source objects are not copied.',context)
            row=lay.row(align=True); row.operator('fab_author.export_brief',text='Export JSON',icon='EXPORT'); row.operator('fab_author.import_brief',text='Import JSON',icon='IMPORT')
            row=lay.row(align=True); button(row,'COPY','Copy JSON','COPYDOWN'); button(row,'PASTE','Paste JSON','PASTEDOWN')
            button(lay,'TEXT','Create Text Block','TEXT')
            lay.prop(s,'text',text='Text block')
            button(lay,'IMPORT_TEXT','Import Text Block','IMPORT',bool(s.text))
            message(lay,'Imports replace the draft; Undo is available. Previous valid drafts are archived in Text blocks.',context)
        else:
            message(lay,'Save the current generated model to a separate local library. Built-in assets stay available.',context)
            addon=context.preferences.addons.get(__package__)
            if addon:
                lay.prop(addon.preferences,'local_library_path',text='Local Library')
            else:
                message(lay,'Install and enable the add-on to configure its Local Library folder.',context)
            button(lay,'SAVE_LIBRARY','Save Asset + Thumbnail','ASSET_MANAGER',bool(local_directory(context)) and context.mode=='OBJECT')
            row=lay.row(); row.enabled=bool(local_directory(context)) and context.mode=='OBJECT'
            row.operator('fab_author.import_asset',text='Import Author .blend',icon='IMPORT')
            message(lay,'Save builds the current brief. To use a returned finished model, import its individual FAB Author .blend asset.',context)
            message(lay,'Each save creates a new asset file. Its catalog entry points to the newest revision; existing scene instances keep their model.',context)
            message(lay,'Use FAB Kit > Add Assets, or FAB Local Assets in the Asset Browser.',context)
            from . import core
            try:
                core.catalog()
                for text in core.library_errors:
                    message(lay,text,context,'ERROR')
            except (OSError,ValueError) as exc:
                message(lay,str(exc),context,'ERROR')
        if s.status:
            box=lay.box(); message(box,s.status,context,'INFO')


classes=(FABAuthorBinding,FABAuthorPart,FABAuthorSettings,FABAUTHOR_OT_quick,FABAUTHOR_OT_quick_export,FABAUTHOR_OT_quick_import,FABAUTHOR_OT_action,FABAUTHOR_OT_export,
         FABAUTHOR_OT_import,FABAUTHOR_OT_import_asset,FABAUTHOR_UL_parts,FABAUTHOR_PT_main)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fab_author=PointerProperty(type=FABAuthorSettings)


def unregister():
    del bpy.types.Scene.fab_author
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    _parent_items.clear()
