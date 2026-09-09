"""Guided Brief: explicit source scope, functional components and AW1 export."""
import json
import math
from pathlib import Path
import textwrap
import uuid
import bpy
from bpy.app.handlers import persistent
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, PointerProperty, StringProperty)
from bpy_extras.io_utils import ExportHelper, ImportHelper
from . import brief_spec as spec, source_scope as scope


def items(values):
    return [(k, label, label) for k, label in values]


def settings_for(self, context):
    scene = self.id_data if isinstance(self.id_data, bpy.types.Scene) else getattr(context, 'scene', None)
    return getattr(scene, 'fab_brief', None)


def scope_changed(self, context):
    s = settings_for(self, context)
    if s:
        s.confirmed = False
        s.measurement_dirty = True


def measure_changed(self, context):
    s = settings_for(self, context)
    if s:
        s.measurement_dirty = True


def frame_changed(self, context):
    s = settings_for(self, context)
    if s:
        s.measurement_dirty = True
        s.units_confirmed = False


def components_changed(self, context):
    ensure_parts(self)
    self.measurement_dirty = True


class FABBriefSource(bpy.types.PropertyGroup):
    key: StringProperty()
    object: PointerProperty(type=bpy.types.Object)
    decision: EnumProperty(name='Source decision', items=[('KEEP','Keep','Include physical geometry or retain references','CHECKMARK',0),('REVIEW','Review','Confirm whether this is physical geometry','QUESTION',1),('EXCLUDE','Exclude','Exclude from all measurements and assignments','X',2)], default='KEEP', update=scope_changed)
    reason: StringProperty()


class FABBriefBinding(bpy.types.PropertyGroup):
    source_key: StringProperty()


class FABBriefSelection(bpy.types.PropertyGroup):
    object: PointerProperty(type=bpy.types.Object)


class FABBriefPart(bpy.types.PropertyGroup):
    key: StringProperty()
    enabled: BoolProperty(default=True, update=measure_changed)
    custom: BoolProperty(default=False)
    importance: EnumProperty(name='Importance', items=items([('KEEP','Must keep'),('SUPPORT','Supporting'),('OMIT','Omit from brief')]), default='KEEP')
    notes: StringProperty(name='Function / features', maxlen=4000)
    placement: EnumProperty(name='Placement', items=items([('UNKNOWN','Unknown'),('FRONT','Front'),('REAR','Rear'),('LEFT','Left'),('RIGHT','Right'),('CENTER','Center'),('OPENING','Inside opening'),('ABOVE','Above'),('OTHER','Other; describe in notes')]), default='UNKNOWN')
    motion: EnumProperty(name='Motion', items=items([('UNKNOWN','Unknown'),('FIXED','Fixed'),('VERTICAL','Vertical'),('CARTESIAN','Cartesian'),('ROTARY','Rotary'),('ARTICULATED','Articulated'),('MOBILE','Mobile')]), default='UNKNOWN')
    mounted_on: StringProperty(name='Mounted on (optional)', maxlen=300)
    arm_kind: EnumProperty(name='Arm kind', items=items([('UNKNOWN','Unknown'),('ARTICULATED','Articulated'),('SCARA','SCARA'),('OTHER','Other')]), default='UNKNOWN')
    axes: IntProperty(name='Axes (0 = unknown)', min=0, max=30, default=0)
    bindings: CollectionProperty(type=FABBriefBinding)


class FABBriefSettings(bpy.types.PropertyGroup):
    step: IntProperty(default=0, min=0, max=4)
    asset_type: EnumProperty(name='Type', items=items([('AMMR','AMMR'),('AMR','AMR'),('ARM','Robot arm'),('EQUIPMENT','Equipment'),('HUMANOID','Humanoid'),('OHT','OHT')]), default='AMMR', update=components_changed)
    purpose: StringProperty(name='Purpose', maxlen=5000)
    outline: EnumProperty(name='Base outline', items=items([('UNKNOWN','Unknown'),('RECT','Rectangular'),('L','L-shaped'),('U','U-shaped'),('OTHER','Other')]), default='UNKNOWN')
    opening: StringProperty(name='Open area / outline details', maxlen=2000)
    features: StringProperty(name='Must-keep features', maxlen=5000)
    arm_count: IntProperty(name='Arm count', min=1, max=8, default=1, update=components_changed)
    arms_unknown: BoolProperty(name='Arm count unknown', update=components_changed)
    handler: BoolProperty(name='Cartesian handler', update=components_changed)
    lift: BoolProperty(name='Lift mechanism', update=components_changed)
    rotary: BoolProperty(name='Rotary mechanism', update=components_changed)
    storage: BoolProperty(name='Tool storage', update=components_changed)
    holder: BoolProperty(name='Holder / fixture', update=components_changed)
    sequence: StringProperty(name='Work sequence', maxlen=4000)
    relation_a: StringProperty(name='Component A', default='Arm 1', maxlen=150)
    relation_b: StringProperty(name='Component B', default='Cartesian handler', maxlen=150)
    relation: EnumProperty(name='Relationship', items=items([('UNKNOWN','Unknown'),('INDEPENDENT_Z','Independent vertical travel'),('TOGETHER_Z','Move vertically together'),('OTHER','Other')]), default='UNKNOWN')
    relation_note: StringProperty(name='Relationship details', maxlen=2000)
    sources: CollectionProperty(type=FABBriefSource)
    source_index: IntProperty(default=0, min=0)
    collection: PointerProperty(name='Collection', type=bpy.types.Collection)
    scope_mode: EnumProperty(name='Scope selection', items=items([('SELF','Selected Only'),('CHILDREN','Include Children')]), default='CHILDREN')
    confirmed: BoolProperty()
    scope_signature: StringProperty()
    parts: CollectionProperty(type=FABBriefPart)
    part_index: IntProperty(default=0, min=0)
    assign_mode: EnumProperty(name='Part selection', items=items([('SELF','Selected Only'),('CHILDREN','Include Children')]), default='SELF')
    previous_selection: CollectionProperty(type=FABBriefSelection)
    previous_active: PointerProperty(type=bpy.types.Object)
    selection_saved: BoolProperty()
    units: EnumProperty(name='Units', items=items([('SCENE','Scene scale'),('CUSTOM','Custom scale')]), default='SCENE', update=frame_changed)
    meters_per_unit: FloatProperty(name='Meters / Blender unit', default=1, min=.000001, max=1000, precision=6, update=frame_changed)
    front: EnumProperty(name='Source front', items=items([('NEG_Y','World -Y'),('POS_Y','World +Y'),('NEG_X','World -X'),('POS_X','World +X'),('CUSTOM','Custom orientation')]), default='NEG_Y', update=frame_changed)
    rotation: FloatVectorProperty(name='Asset frame rotation', size=3, subtype='EULER', update=frame_changed)
    units_confirmed: BoolProperty(name='I checked units and front direction')
    measurement_json: StringProperty()
    measurement_dirty: BoolProperty(default=True)
    include_measurements: BoolProperty(name='Include measurements')
    include_hierarchy: BoolProperty(name='Include root names')
    hierarchy_depth: IntProperty(name='Hierarchy depth (0 = all)', min=0, max=20, default=2)
    show_drafts: BoolProperty(name='Local draft files')
    status: StringProperty()


def ensure_parts(s):
    desired = [('base', 'Mobile base')] if s.asset_type in {'AMMR','AMR'} else [('body','Body')] if s.asset_type in {'EQUIPMENT','HUMANOID','OHT'} else []
    if s.asset_type in {'AMMR','ARM','HUMANOID'} and not s.arms_unknown:
        desired += [('arm_'+str(i), 'Arm '+str(i)) for i in range(1, s.arm_count+1)]
    desired += [(key, name) for key, name in [('handler','Cartesian handler'),('lift','Lift mechanism'),('rotary','Rotary mechanism'),('storage','Tool storage'),('holder','Holder / fixture')] if getattr(s,key)]
    keys = {k for k, _ in desired}
    existing = {p.key:p for p in s.parts}
    for p in s.parts:
        enabled = p.custom or p.key in keys
        if p.enabled != enabled:
            p.enabled = enabled
    for key, name in desired:
        if key not in existing:
            p = s.parts.add(); p.key=key; p.name=name; p.enabled=True
    if s.part_index >= len(s.parts):
        s.part_index = max(0,len(s.parts)-1)


def current(s):
    return s.parts[s.part_index] if s.part_index < len(s.parts) else None


def source_current(s):
    return s.sources[s.source_index] if s.source_index < len(s.sources) else None


def header(s):
    arms = None
    if s.asset_type in {'AMMR','ARM','HUMANOID'}:
        arms = 'unknown' if s.arms_unknown else [[p.arm_kind, p.axes or None] for p in s.parts if p.enabled and p.key.startswith('arm_')]
    relation = ''
    if s.relation != 'UNKNOWN':
        detail = {'INDEPENDENT_Z':'independent vertical travel','TOGETHER_Z':'move vertically together','OTHER':s.relation_note}[s.relation]
        relation = f'{s.relation_a} / {s.relation_b}: {detail}'
    return {'type':s.asset_type,'purpose':s.purpose,'outline':s.outline,'opening':s.opening,
            'arms':arms,'features':s.features,'sequence':s.sequence,'relationship':relation}


def payload(context,s):
    parts=[dict(id=p.key,name=p.name,enabled=p.enabled,importance=p.importance,
                notes=p.notes,placement=p.placement,motion=p.motion,mounted_on=p.mounted_on) for p in s.parts]
    measured=json.loads(s.measurement_json) if s.include_measurements and s.measurement_json else None
    roots=None
    if s.include_hierarchy:
        pointers={r.object.as_pointer() for r in s.sources if r.object}
        roots=[r.object.name for r in s.sources if scope.alive(r,context.scene) and r.decision!='EXCLUDE' and (not r.object.parent or r.object.parent.as_pointer() not in pointers)]
    return spec.packet(header(s),parts,measured,roots)


def transfer_issues(context,s):
    errors=scope.issues(s,context.scene)
    if not scope.confirmed(s,context.scene): errors.append('Confirm Scope in step 1.')
    if not s.purpose.strip(): errors.append('Enter the equipment purpose in step 2.')
    if s.include_measurements:
        if not s.measurement_json: errors.append('Measure first, or turn off Include measurements.')
        elif s.measurement_dirty or not s.units_confirmed: errors.append('Measurements need refresh, or turn off Include measurements.')
    return errors


def outgoing(context,s):
    errors=transfer_issues(context,s)
    if errors: raise ValueError(errors[0])
    if s.include_measurements:
        result=scope.evaluate(context,s)
        if result['stamp']!=json.loads(s.measurement_json)['stamp']:
            s.measurement_dirty=True
            raise ValueError('Source geometry, pose or frame changed. Refresh measurements or export without them.')
    return spec.dumps(payload(context,s),enforce=True)


def show(context,s,objects):
    if context.mode!='OBJECT': raise ValueError('Switch to Object Mode.')
    if not s.selection_saved:
        s.previous_selection.clear()
        for obj in context.selected_objects: s.previous_selection.add().object=obj
        s.previous_active=context.view_layer.objects.active
        s.selection_saved=True
    for obj in context.selected_objects: obj.select_set(False)
    visible=[]
    for obj in objects:
        if obj and obj.name in context.view_layer.objects and obj.visible_get(view_layer=context.view_layer) and not obj.hide_select:
            obj.select_set(True);visible.append(obj)
    if visible:
        context.view_layer.objects.active=visible[0]
        if context.area and context.area.type=='VIEW_3D':
            bpy.ops.view3d.view_selected(use_all_regions=False)
    return len(visible)


def restore(context,s):
    if not s.selection_saved: return
    for obj in context.selected_objects: obj.select_set(False)
    for ref in s.previous_selection:
        if ref.object and ref.object.name in context.view_layer.objects:
            ref.object.select_set(True)
    if s.previous_active and s.previous_active.name in context.view_layer.objects:
        context.view_layer.objects.active=s.previous_active
    s.previous_selection.clear();s.previous_active=None;s.selection_saved=False


SETTINGS_FIELDS=('step','asset_type','purpose','outline','opening','features','arm_count','arms_unknown','handler','lift','rotary','storage','holder','sequence','relation_a','relation_b','relation','relation_note','scope_mode','assign_mode','units','meters_per_unit','front','rotation','include_measurements','include_hierarchy','hierarchy_depth')
PART_FIELDS=('key','name','enabled','custom','importance','notes','placement','motion','mounted_on','arm_kind','axes')


def values(obj,fields):
    return {key:list(getattr(obj,key)) if key=='rotation' else getattr(obj,key) for key in fields}


def draft(s):
    sources=[]
    for r in s.sources:
        o=r.object
        sources.append({'key':r.key,'name':o.name if o else r.name,'type':o.type if o else '',
                        'data':o.data.name if o and o.data else '', 'library':o.library.filepath if o and o.library else '',
                        'decision':r.decision,'reason':r.reason})
    return {'v':'FAB_GUIDED_DRAFT1','blend':bpy.data.filepath,'fields':values(s,SETTINGS_FIELDS),
            'sources':sources,'parts':[dict(values(p,PART_FIELDS),bindings=[b.source_key for b in p.bindings]) for p in s.parts],
            'measurement':json.loads(s.measurement_json) if s.measurement_json else None}


def archive(s):
    if s.sources or s.purpose or s.parts:
        text=bpy.data.texts.new('FAB Previous Guided Draft')
        text.write(json.dumps(draft(s),ensure_ascii=False,indent=2,allow_nan=False))


def validate_fields(cls,data,fields):
    if not isinstance(data,dict) or set(data)!=set(fields): raise ValueError('Unexpected draft fields.')
    for key,value in data.items():
        prop=cls.bl_rna.properties[key]
        if prop.type=='STRING':
            maximum=prop.length_max-1 if prop.length_max else 100000
            if not isinstance(value,str) or len(value)>maximum or '\x00' in value: raise ValueError('Invalid text: '+key)
        elif prop.type=='BOOLEAN':
            if type(value)!=bool: raise ValueError('Invalid boolean: '+key)
        elif prop.type=='ENUM':
            if value not in {i.identifier for i in prop.enum_items}: raise ValueError('Invalid option: '+key)
        elif prop.type in {'INT','FLOAT'}:
            vv=value if prop.is_array else [value]
            if prop.is_array and (not isinstance(vv,list) or len(vv)!=prop.array_length): raise ValueError('Invalid vector: '+key)
            for v in vv:
                if type(v) not in (int,float) or not math.isfinite(v) or not prop.hard_min<=v<=prop.hard_max or (prop.type=='INT' and type(v)!=int): raise ValueError('Invalid number: '+key)


def load_draft(s,data):
    if not isinstance(data,dict) or set(data)!={'v','blend','fields','sources','parts','measurement'} or data['v']!='FAB_GUIDED_DRAFT1': raise ValueError('Expected a local Guided Draft JSON, not AW1/FQ1 transfer text.')
    if not isinstance(data['blend'],str) or not isinstance(data['sources'],list) or len(data['sources'])>scope.MAX_OBJECTS or not isinstance(data['parts'],list) or len(data['parts'])>100: raise ValueError('Invalid draft structure.')
    validate_fields(FABBriefSettings,data['fields'],SETTINGS_FIELDS)
    keys=set();partkeys=set()
    for r in data['sources']:
        if not isinstance(r,dict) or set(r)!={'key','name','type','data','library','decision','reason'} or any(not isinstance(v,str) or len(v)>10000 for v in r.values()): raise ValueError('Invalid source record.')
        if not r['key'] or r['key'] in keys or r['decision'] not in {'KEEP','REVIEW','EXCLUDE'}: raise ValueError('Invalid source identity.')
        keys.add(r['key'])
    for p in data['parts']:
        if not isinstance(p,dict) or set(p)!=set(PART_FIELDS)|{'bindings'}: raise ValueError('Invalid part record.')
        validate_fields(FABBriefPart,{k:p[k] for k in PART_FIELDS},PART_FIELDS)
        if not p['key'] or p['key'] in partkeys or not isinstance(p['bindings'],list) or len(p['bindings'])!=len(set(p['bindings'])) or any(k not in keys for k in p['bindings']): raise ValueError('Invalid component binding.')
        partkeys.add(p['key'])
    # Cached measurements are deliberately discarded; imported source scope must be reconfirmed.
    archive(s)
    s.sources.clear();s.parts.clear()
    for key,value in data['fields'].items(): setattr(s,key,value)
    s.parts.clear()  # callbacks may create default functional cards
    same_blend=bool(bpy.data.filepath) and data['blend']==bpy.data.filepath
    for record in data['sources']:
        r=s.sources.add();r.key=record['key'];r.name=record['name'];r.decision=record['decision'];r.reason=record['reason']
        obj=bpy.data.objects.get(record['name']) if same_blend else None
        if obj and obj.type==record['type'] and (obj.data.name if obj.data else '')==record['data'] and (obj.library.filepath if obj.library else '')==record['library']: r.object=obj
    for record in data['parts']:
        p=s.parts.add()
        for key in PART_FIELDS: setattr(p,key,record[key])
        for key in record['bindings']: p.bindings.add().source_key=key
    s.measurement_json='';s.measurement_dirty=True;s.confirmed=False;s.units_confirmed=False
    s.source_index=0;s.part_index=0;s.step=0
    s.status='Local draft loaded. Reconfirm Scope and refresh measurements. Unresolved source names require reconnecting.'


class FABBRIEF_OT_action(bpy.types.Operator):
    bl_idname='fab_brief.action'
    bl_label='Guided Brief'
    bl_options={'UNDO'}
    action:StringProperty()
    value:IntProperty()
    def execute(self,context):
        s=context.scene.fab_brief
        try:
            key=self.action
            if key not in {'STEP','VIEW','HIERARCHY','COPY','LIBRARY','NEW'} and context.mode!='OBJECT': raise ValueError('Switch to Object Mode to select, assign or measure sources.')
            if key=='STEP': ensure_parts(s);s.step=self.value
            elif key=='ADD':
                s.status=f'Added {scope.add(s,context.selected_objects,s.scope_mode=="CHILDREN")} sources. Review helpers, then Confirm Scope.';ensure_parts(s)
                s.source_index=next((i for i,r in enumerate(s.sources) if r.decision=='REVIEW'),0)
            elif key=='COLLECTION':
                if not s.collection: raise ValueError('Choose a Collection.')
                s.status=f'Added {scope.add(s,s.collection.all_objects,False)} sources from the Collection and child Collections.';ensure_parts(s)
            elif key in {'KEEP','EXCLUDE'}: s.status=f'{scope.set_decision(s,context.selected_objects,key,s.scope_mode=="CHILDREN")} source decisions updated. Confirm Scope again.'
            elif key=='CONFIRM': scope.confirm(s,context.scene);s.status='Scope confirmed. Exclusions apply to every component assignment.'
            elif key=='NEXT_REVIEW':
                pending=[i for i,r in enumerate(s.sources) if r.decision=='REVIEW']
                if not pending: raise ValueError('No pending source candidates.')
                s.source_index=next((i for i in pending if i>s.source_index),pending[0])
            elif key=='REMOVE_SOURCE':
                if not source_current(s): raise ValueError('Choose a source row.')
                s.sources.remove(s.source_index);s.source_index=max(0,min(s.source_index,len(s.sources)-1));scope_changed(s,context);s.status='Source removed. Reassign affected components before measuring.'
            elif key=='RECONNECT':
                row=source_current(s);obj=context.active_object
                if not row or not obj: raise ValueError('Choose a source row and select its replacement object.')
                if any(r!=row and r.object==obj for r in s.sources): raise ValueError('That object already has a source row. Use the existing row when reassigning components.')
                if obj.get('fab_author_generated') or obj.get('fab_author_guide') or obj.get('fab_brief_guide'): raise ValueError('Choose original source geometry.')
                row.object=obj;row.name=obj.name;row.decision='REVIEW' if scope.helper(obj) or scope.instance(obj) else 'KEEP'
                scope_changed(s,context);s.status='Source row reconnected. Existing component links retain their source ID. Review Scope again.'
            elif key in {'SHOW_INCLUDED','SHOW_EXCLUDED','SHOW_SOURCE','SHOW_PART'}:
                if key=='SHOW_INCLUDED': objects=[r.object for r in scope.included(s,context.scene)]
                elif key=='SHOW_EXCLUDED': objects=[r.object for r in s.sources if r.object and r.decision=='EXCLUDE']
                elif key=='SHOW_SOURCE': objects=[source_current(s).object] if source_current(s) else []
                else:
                    p=current(s);wanted={b.source_key for b in p.bindings} if p else set();objects=[r.object for r in s.sources if r.key in wanted and r.object]
                n=show(context,s,objects);s.status=f'Selected {n} of {len(objects)} objects. Hidden/locked objects are unchanged. Restore Selection returns your previous selection.'
            elif key=='RESTORE': restore(context,s);s.status='Previous selection restored.'
            elif key in {'ASSIGN','APPEND'}:
                p=current(s)
                if not p or not p.enabled: raise ValueError('Select an active component.')
                n=scope.assign(s,context.scene,p,context.selected_objects,s.assign_mode=='CHILDREN',key=='APPEND');s.status=f'{p.name}: {n} included mesh/curve sources assigned. Excluded sources stay excluded.'
            elif key=='UNBIND':
                p=current(s)
                if not p: raise ValueError('Choose a component.')
                p.bindings.clear();s.measurement_dirty=True;s.status='Describe Only: this component has no measured source binding.'
            elif key=='ADD_PART':
                if len(s.parts)>=100: raise ValueError('At most 100 component cards.')
                p=s.parts.add();p.key='other_'+uuid.uuid4().hex[:6];p.name='Other component';p.custom=True;p.enabled=True;s.part_index=len(s.parts)-1;s.measurement_dirty=True
            elif key=='REMOVE_PART':
                p=current(s)
                if not p: raise ValueError('Choose a component.')
                if not p.custom: raise ValueError('Change the equipment configuration in step 2, or set Importance to Omit.')
                s.parts.remove(s.part_index);s.part_index=max(0,min(s.part_index,len(s.parts)-1));s.measurement_dirty=True
            elif key=='ACTIVE_FRAME':
                if not context.active_object: raise ValueError('Select an object with the desired orientation.')
                s.front='CUSTOM';s.rotation=context.active_object.matrix_world.to_quaternion().to_euler();s.status='Reference orientation copied. Verify +Z up and -Y front before measuring.'
            elif key=='MEASURE':
                if not scope.confirmed(s,context.scene): raise ValueError('Confirm Scope first.')
                if not s.units_confirmed: raise ValueError('Check units/front and tick the confirmation before measuring.')
                context.view_layer.update()
                result=scope.evaluate(context,s);s.measurement_json=json.dumps(result,allow_nan=False);s.measurement_dirty=False;s.include_measurements=True
                s.status=f'Measured {result["vertices"]:,} evaluated vertices in the current pose. Distances are meters.'
            elif key in {'VIEW','COPY'}:
                text=outgoing(context,s) if key=='COPY' else spec.dumps(payload(context,s))
                if key=='COPY':
                    context.window_manager.clipboard=text
                    if context.window_manager.clipboard!=text: raise ValueError('Clipboard verification failed. Use Export Text.')
                    s.status=f'Copied the complete AW1 brief: {spec.count(text)}/1000 characters.'
                else:
                    block=bpy.data.texts.new('FAB Guided Brief AW1');block.write(text);s.status=f'Created Text block {block.name}: {spec.count(text)} characters. No transfer performed.'
            elif key=='HIERARCHY':
                text=scope.hierarchy(s,context.scene,s.hierarchy_depth);block=bpy.data.texts.new('FAB Source Hierarchy');block.write(text)
                if spec.count(text)<=1000: context.window_manager.clipboard=text;s.status=f'Hierarchy saved to Text and copied ({spec.count(text)} characters).'
                else: s.status=f'Hierarchy saved to Text ({spec.count(text)} characters); not copied. Reduce depth or use the compact brief.'
            elif key=='LIBRARY': context.scene.fab_author.workflow='ADVANCED';context.scene.fab_author.step='LIBRARY'
            elif key=='NEW':
                archive(s);restore(context,s)
                context.scene.property_unset('fab_brief');s=context.scene.fab_brief;s.status='New Guided Brief. Previous draft archived in a Text block.'
            else: raise ValueError('Unknown Guided Brief action.')
            return {'FINISHED'}
        except (ValueError,RuntimeError,TypeError,KeyError,OverflowError) as exc:
            s.status=str(exc);self.report({'ERROR'},str(exc));return {'CANCELLED'}


class FABBRIEF_OT_export(bpy.types.Operator,ExportHelper):
    bl_idname='fab_brief.export_text';bl_label='Export AW1 Text (1000 max)'
    filename_ext='.txt'
    filter_glob:StringProperty(default='*.txt',options={'HIDDEN'})
    def execute(self,context):
        try:
            text=outgoing(context,context.scene.fab_brief)
            Path(self.filepath).write_text(text,encoding='utf-8',newline='')
            context.scene.fab_brief.status=f'Saved {spec.count(text)}/1000 characters as AW1 text.'
            return {'FINISHED'}
        except (OSError,ValueError,RuntimeError) as exc: self.report({'ERROR'},str(exc));return {'CANCELLED'}


class FABBRIEF_OT_save_draft(bpy.types.Operator,ExportHelper):
    bl_idname='fab_brief.save_draft';bl_label='Save Local Guided Draft'
    filename_ext='.json'
    filter_glob:StringProperty(default='*.json',options={'HIDDEN'})
    def execute(self,context):
        try:
            text=json.dumps(draft(context.scene.fab_brief),ensure_ascii=False,indent=2,allow_nan=False)
            Path(self.filepath).write_text(text,encoding='utf-8')
            context.scene.fab_brief.status='Full local draft saved. Use Export AW1 Text for the 1000-character transfer.'
            return {'FINISHED'}
        except (OSError,ValueError) as exc: self.report({'ERROR'},str(exc));return {'CANCELLED'}


class FABBRIEF_OT_load_draft(bpy.types.Operator,ImportHelper):
    bl_idname='fab_brief.load_draft';bl_label='Load Local Guided Draft';bl_options={'UNDO'}
    filename_ext='.json'
    filter_glob:StringProperty(default='*.json',options={'HIDDEN'})
    def execute(self,context):
        try:
            path=Path(self.filepath)
            if path.stat().st_size>2_000_000: raise ValueError('Local draft exceeds 2 MB.')
            def invalid(value): raise ValueError('Invalid JSON number: '+value)
            def unique(pairs):
                result={}
                for k,v in pairs:
                    if k in result: raise ValueError('Duplicate JSON key: '+k)
                    result[k]=v
                return result
            data=json.loads(path.read_text(encoding='utf-8-sig'),parse_constant=invalid,object_pairs_hook=unique)
            load_draft(context.scene.fab_brief,data)
            context.scene.fab_author.workflow='GUIDED'
            return {'FINISHED'}
        except (OSError,ValueError,TypeError,KeyError) as exc: self.report({'ERROR'},str(exc));return {'CANCELLED'}


class FABBRIEF_UL_sources(bpy.types.UIList):
    review_only:BoolProperty(name='Review only')
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        row=layout.row(align=True);row.prop(item,'decision',text='',icon_only=True)
        obj=item.object
        row.label(text=obj.name if obj else item.name+' (missing)',icon={'MESH':'OUTLINER_OB_MESH','EMPTY':'OUTLINER_OB_EMPTY','ARMATURE':'OUTLINER_OB_ARMATURE'}.get(obj.type if obj else '', 'OBJECT_DATA'))
    def draw_filter(self,context,layout):
        layout.prop(self,'filter_name',text='',icon='VIEWZOOM');layout.prop(self,'review_only')
    def filter_items(self,context,data,propname):
        flags=[]
        for item in getattr(data,propname):
            name=item.object.name if item.object else item.name
            visible=self.filter_name.casefold() in name.casefold() and (not self.review_only or item.decision=='REVIEW')
            flags.append(self.bitflag_filter_item if visible else 0)
        return flags,[]


class FABBRIEF_UL_parts(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        row=layout.row();row.enabled=item.enabled
        row.label(text=item.name+(' (inactive)' if not item.enabled else ''),icon='LINKED' if item.bindings else 'OUTLINER_OB_EMPTY')


def message(layout,text,context,icon=None):
    scale=max(context.preferences.system.ui_scale,.5)
    width=max(18,int((context.region.width if context.region else 350)/scale/7)-9)
    layout=layout.column(align=True);layout.scale_y=.85
    for i,line in enumerate(textwrap.wrap(text,width=width) or ['']):
        layout.label(text=line,icon=icon if i==0 and icon else 'NONE')


def button(layout,key,label,enabled=True,icon='NONE'):
    row=layout.row();row.enabled=enabled
    op=row.operator('fab_brief.action',text=label,icon=icon);op.action=key
    return op


def draw(layout,context):
    s=context.scene.fab_brief;p=current(s);scene=context.scene
    nav=layout.row(align=True)
    for i in range(5):
        op=nav.operator('fab_brief.action',text=str(i+1),depress=s.step==i);op.action='STEP';op.value=i
    layout.label(text=f'{s.step+1} / 5  '+['Scope','Describe','Parts','Measure & Relations','Review'][s.step])
    object_mode=context.mode=='OBJECT'
    if not object_mode: message(layout,'Switch to Object Mode for source selection and measurement.',context,'INFO')
    if s.step==0:
        message(layout,'Select the model roots or objects, then add them to the source snapshot.',context)
        layout.prop(s,'scope_mode',expand=True)
        button(layout,'ADD','Add Selection',object_mode and bool(context.selected_objects),'ADD')
        layout.prop(s,'collection',text='Collection')
        button(layout,'COLLECTION','Add Collection + Child Collections',object_mode and bool(s.collection))
        if s.sources:
            layout.template_list('FABBRIEF_UL_sources','',s,'sources',s,'source_index',rows=5)
            if any(r.decision=='REVIEW' for r in s.sources): button(layout,'NEXT_REVIEW','Review Next Helper',object_mode,'QUESTION')
            r=source_current(s)
            if r:
                box=layout.box();message(box,r.object.name if r.object else r.name+' (missing)',context)
                box.prop(r,'decision',text='Decision')
                if r.reason: message(box,r.reason,context)
                row=box.row(align=True);button(row,'SHOW_SOURCE','Select Source',object_mode and bool(r.object));button(row,'REMOVE_SOURCE','Remove Row',object_mode)
                if not scope.alive(r,scene): button(box,'RECONNECT','Reconnect to Active Object',object_mode and bool(context.active_object))
            row=layout.row(align=True);button(row,'KEEP','Keep Selection',object_mode);button(row,'EXCLUDE','Exclude Selection',object_mode)
            row=layout.row(align=True);button(row,'SHOW_INCLUDED','Show Included',object_mode);button(row,'SHOW_EXCLUDED','Show Excluded',object_mode)
            inc=scope.included(s,scene);pending=sum(r.decision=='REVIEW' for r in s.sources)
            message(layout,f'{len(s.sources)} source objects / {len(inc)} included geometry / {pending} to review',context)
            errors=scope.issues(s,scene)
            button(layout,'CONFIRM','Scope Confirmed' if scope.confirmed(s,scene) else 'Confirm Scope',object_mode and not errors,'CHECKMARK')
            if errors: message(layout,errors[0],context,'ERROR')
            layout.prop(s,'hierarchy_depth');button(layout,'HIERARCHY','Hierarchy to Text / Copy if <= 1000')
        message(layout,'Snapshot only. Add Selection again to include newly added source objects. Original hierarchy stays unchanged.',context)
    elif s.step==1:
        layout.prop(s,'asset_type');layout.prop(s,'purpose')
        if s.asset_type not in {'ARM','HUMANOID'}:
            layout.prop(s,'outline')
            if s.outline in {'L','U','OTHER'}: layout.prop(s,'opening')
        if s.asset_type in {'AMMR','ARM','HUMANOID'}:
            layout.prop(s,'arms_unknown')
            if not s.arms_unknown:
                layout.prop(s,'arm_count')
                for part in s.parts:
                    if part.enabled and part.key.startswith('arm_'):
                        box=layout.box();box.label(text=part.name);box.prop(part,'arm_kind');box.prop(part,'axes')
        layout.label(text='Additional mechanisms')
        for key in ('handler','lift','rotary','storage','holder'): layout.prop(s,key)
        layout.prop(s,'features')
        message(layout,'Choose Unknown when unsure. No primitive, material or topology input is required.',context)
    elif s.step==2:
        layout.template_list('FABBRIEF_UL_parts','',s,'parts',s,'part_index',rows=4)
        row=layout.row(align=True);button(row,'ADD_PART','Add Other');button(row,'REMOVE_PART','Remove Other',bool(p and p.custom))
        if p:
            box=layout.box();box.enabled=p.enabled;box.prop(p,'name',text='Component');box.prop(p,'importance');box.prop(p,'notes')
            box.prop(p,'placement');box.prop(p,'motion');box.prop(p,'mounted_on')
            box.prop(s,'assign_mode',expand=True)
            ready=object_mode and bool(context.selected_objects) and p.enabled and scope.confirmed(s,scene)
            row=box.row(align=True);button(row,'ASSIGN','Assign / Replace',ready);button(row,'APPEND','Add Selection',ready)
            row=box.row(align=True);button(row,'SHOW_PART','Show Assigned',object_mode and bool(p.bindings));button(row,'UNBIND','Describe Only',object_mode and bool(p.bindings))
            message(box,f'{len(p.bindings)} source objects assigned' if p.bindings else 'Describe Only: no measurement binding',context)
            if not scope.confirmed(s,scene): message(box,'Confirm Scope in step 1 to enable assignment.',context,'INFO')
        message(layout,'Select the source in the viewport or Outliner. Selected Only measures a base mesh without its child tools. Exclusions always apply.',context)
    elif s.step==3:
        layout.prop(s,'units')
        if s.units=='CUSTOM': layout.prop(s,'meters_per_unit')
        message(layout,f'1 Blender unit = {scope.scale(s,scene):.6g} m',context)
        layout.prop(s,'front')
        if s.front=='CUSTOM': layout.prop(s,'rotation')
        button(layout,'ACTIVE_FRAME','Use Active Object Orientation',object_mode and bool(context.active_object))
        message(layout,'Export frame: -Y front, +Z up; origin at overall XY center and floor. Check source orientation.',context)
        layout.prop(s,'units_confirmed')
        button(layout,'MEASURE','Measure / Refresh All',object_mode and scope.confirmed(s,scene) and s.units_confirmed,'DRIVER_DISTANCE')
        if s.measurement_json:
            result=json.loads(s.measurement_json)
            message(layout,'Overall: '+' x '.join(f'{v:.4g}' for v in result['size'])+' m',context)
            if s.measurement_dirty: message(layout,'Needs refresh before measured values can be exported.',context,'ERROR')
            for key,value in result.get('parts',{}).items():
                part=next((p for p in s.parts if p.key==key),None)
                if part: message(layout,part.name+': '+' x '.join(f'{v:.3g}' for v in value['size'])+' m',context)
        else: message(layout,'Unmeasured. You can continue and export a description without dimensions.',context)
        layout.separator();layout.label(text='Motion relationship (optional)')
        layout.prop(s,'relation_a');layout.prop(s,'relation_b');layout.prop(s,'relation')
        if s.relation=='OTHER': layout.prop(s,'relation_note')
        layout.prop(s,'sequence')
    else:
        layout.prop(s,'include_measurements');layout.prop(s,'include_hierarchy')
        text=spec.dumps(payload(context,s));n=spec.count(text)
        layout.label(text=f'{n} / 1000 characters',icon='ERROR' if n>1000 else 'INFO')
        errors=transfer_issues(context,s)
        if n>1000: errors.append(f'{n-1000} over limit. Shorten notes or disable optional fields; nothing is truncated.')
        for error in errors[:3]: message(layout,error,context,'ERROR')
        button(layout,'VIEW','View Brief in Text Block')
        button(layout,'COPY','Copy AW1 Text (1000 max)',not errors,'COPYDOWN')
        row=layout.row();row.enabled=not errors;row.operator('fab_brief.export_text',text='Export AW1 Text...',icon='EXPORT')
        message(layout,'Semantic brief for modeling. No source mesh or full hierarchy is included by default. Missing dimensions remain null.',context)
        button(layout,'LIBRARY','Import Finished Author Asset...',True,'ASSET_MANAGER')
    if s.selection_saved: button(layout,'RESTORE','Restore Previous Selection',object_mode,'LOOP_BACK')
    nav=layout.row(align=True)
    if s.step>0: button(nav,'STEP','Back').value=s.step-1
    if s.step<4: button(nav,'STEP','Next').value=s.step+1
    layout.prop(s,'show_drafts',icon='TRIA_DOWN' if s.show_drafts else 'TRIA_RIGHT',emboss=False)
    if s.show_drafts:
        message(layout,'Full local draft files can exceed 1000 characters. Use AW1 Text for transfer. Saving your .blend also saves this wizard.',context)
        row=layout.row(align=True);row.operator('fab_brief.save_draft',text='Save Draft...');row.operator('fab_brief.load_draft',text='Load Draft...')
        button(layout,'NEW','New Draft (Archive Current)')
    if s.status: message(layout.box(),s.status,context)


@persistent
def mark_geometry_dirty(scene,depsgraph):
    s=getattr(scene,'fab_brief',None)
    if not s or not s.measurement_json or s.measurement_dirty: return
    watched=set()
    for r in s.sources:
        if r.object and r.decision=='KEEP':
            watched.add(r.object.as_pointer())
            if r.object.data: watched.add(r.object.data.as_pointer())
    for update in depsgraph.updates:
        original=getattr(update.id,'original',update.id)
        if original.as_pointer() in watched and (update.is_updated_geometry or update.is_updated_transform):
            s.measurement_dirty=True;return


@persistent
def on_load(_):
    for scene in bpy.data.scenes:
        s=getattr(scene,'fab_brief',None)
        if s and s.measurement_json: s.measurement_dirty=True


classes=(FABBriefSource,FABBriefBinding,FABBriefSelection,FABBriefPart,FABBriefSettings,
         FABBRIEF_OT_action,FABBRIEF_OT_export,FABBRIEF_OT_save_draft,FABBRIEF_OT_load_draft,
         FABBRIEF_UL_sources,FABBRIEF_UL_parts)


def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.Scene.fab_brief=PointerProperty(type=FABBriefSettings)
    bpy.app.handlers.depsgraph_update_post.append(mark_geometry_dirty)
    bpy.app.handlers.load_post.append(on_load)


def unregister():
    if mark_geometry_dirty in bpy.app.handlers.depsgraph_update_post: bpy.app.handlers.depsgraph_update_post.remove(mark_geometry_dirty)
    if on_load in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(on_load)
    if hasattr(bpy.types.Scene,'fab_brief'): del bpy.types.Scene.fab_brief
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
