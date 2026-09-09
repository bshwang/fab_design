"""FAB Scene Kit: offline asset assembly for Blender 4.3."""
import math
import textwrap
from pathlib import Path
import bpy
from bpy.app.handlers import persistent
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty,
                       IntProperty, PointerProperty, StringProperty)
from . import core, author

bl_info = {'name':'FAB Scene Kit','author':'FAB Scene Kit','version':(0,4,2),
           'blender':(4,3,0),'location':'3D View > Sidebar > FAB Kit',
           'description':'Offline isometric FAB assembly','category':'3D View'}
_enum_items=[]
_busy=False


def label_changed(self, context):
    if _busy or not context.scene or not context.scene.fab.enabled:
        return
    obj=self.id_data
    if isinstance(obj,bpy.types.Object) and obj.name in context.scene.objects:
        core.update_label(context.scene,obj)


def items(self, context):
    global _enum_items
    try:
        values=core.catalog()
        cat=self.category
        term=self.search.casefold()
        found=[(key,item) for key,item in values.items()
               if (cat=='ALL' or item['category']==cat) and
               (not term or term in (key+' '+item['name']+' '+item.get('tags','')).casefold())]
        numbers={key:i for i,key in enumerate(values)}
        _enum_items=[(key,item['name'],item.get('description',item['name']),numbers[key])
                     for key,item in found]
    except (OSError,ValueError):
        _enum_items=[]
    if not _enum_items:
        _enum_items=[('NONE','No matching assets','Change category/search or choose a valid library',2147483647)]
    return _enum_items


def filter_changed(self,context):
    choices=items(self,context)
    if self.get('asset_id',0) not in {item[3] for item in choices}:
        self.asset_id=choices[0][0]


def scene_labels_changed(self,context):
    if not _busy and self.enabled:
        core.sync_labels(self.id_data)


def overhead_changed(self,context):
    if not _busy and self.enabled:
        core.set_overhead_visibility(self.id_data)


def room_poll(self,obj):
    return obj.get('fab_asset')=='cleanroom' and obj.name in self.id_data.objects


def dimension_get(axis):
    return lambda self: abs(self.id_data.scale[axis])*core.asset_size(self.id_data)[axis]


def dimension_set(axis):
    def setter(self,value):
        self.id_data.scale[axis]=value/max(.001,core.asset_size(self.id_data)[axis])
    return setter


class FABPreferences(bpy.types.AddonPreferences):
    bl_idname=__package__
    library_path:StringProperty(name='Data folder (optional override)',subtype='DIR_PATH',
                                description='Folder containing library and templates; empty uses bundled data')
    local_library_path:StringProperty(name='Local Asset Library',subtype='DIR_PATH',
                                description='Additional authored assets; separate from the installed add-on')
    def draw(self,context):
        self.layout.label(text='Works offline. Bundled assets are used by default.')
        self.layout.prop(self,'library_path')
        self.layout.prop(self,'local_library_path')
        self.layout.operator('fab.action',text='Register Asset Browser library',icon='ASSET_MANAGER').action='REGISTER_LIBRARY'


class FABInstance(bpy.types.PropertyGroup):
    label:StringProperty(name='Name',update=label_changed)
    code:StringProperty(name='ID',update=label_changed)
    label_mode:EnumProperty(name='Label',items=[('FLOOR','Floor',''),
        ('SIGN','Above',''),('FRONT','Front',''),('HIDDEN','Hidden','')],default='FLOOR',update=label_changed)
    size:FloatProperty(name='Text size',default=.24,min=.05,max=2,update=label_changed)
    offset:FloatVectorProperty(name='Label offset',size=3,default=(0,0,0),update=label_changed)
    highlighted:BoolProperty(name='Highlighted',default=False)
    width:FloatProperty(name='Width (m)',min=.1,max=1000,get=dimension_get(0),set=dimension_set(0),
        description='Scale this assembly in local X; equipment placed inside is independent')
    depth:FloatProperty(name='Depth (m)',min=.1,max=1000,get=dimension_get(1),set=dimension_set(1),
        description='Scale this assembly in local Y; equipment placed inside is independent')


class FABSettings(bpy.types.PropertyGroup):
    enabled:BoolProperty(default=False)
    template:EnumProperty(name='Template',items=[('BLANK','Blank Stage',''),('OVERVIEW','FAB Overview',''),
        ('EXAMPLE','FAB Example','')],default='OVERVIEW')
    theme:EnumProperty(name='Theme',items=[('LIGHT','Light',''),('DARK','Dark','')],default='LIGHT')
    title:StringProperty(name='Title',default='FAB / MANUFACTURING ECOSYSTEM',update=scene_labels_changed)
    width:FloatProperty(name='Width (m)',default=30,min=4,max=100)
    depth:FloatProperty(name='Depth (m)',default=25,min=4,max=100)
    floor_z:FloatProperty(name='Floor Z (m)',default=.79,min=-100,max=100)
    placement:EnumProperty(name='Place on',items=[('CLEANROOM','Cleanroom','Walking surface of the selected cleanroom'),
        ('STAGE','Stage','Top of the outer base'),('CURSOR','3D Cursor','Use the cursor height, for example on a utility pad'),
        ('CUSTOM','Custom height','Enter an explicit floor height')],default='CUSTOM')
    room:PointerProperty(name='Cleanroom',type=bpy.types.Object,poll=room_poll)
    grid:EnumProperty(name='Grid',items=[('0','Off',''),('.25','0.25 m',''),('.5','0.5 m',''),('1','1 m','')],default='.5')
    category:EnumProperty(name='Category',items=[('ALL','All',''),('PROCESS','Manufacturing',''),
        ('UTILITY','Utilities',''),('ROBOT','Robots',''),('PEOPLE','People',''),
        ('LOGISTICS','Logistics',''),('SPACE','Space',''),('CONNECTION','Connections','')],update=filter_changed)
    search:StringProperty(name='Search',update=filter_changed)
    asset_id:EnumProperty(name='Asset',items=items)
    copy_count:IntProperty(name='Copies',default=3,min=1,max=100)
    spacing:FloatProperty(name='Spacing (m)',default=3,min=.1,max=50)
    axis:EnumProperty(name='Axis',items=[('X','X',''),('Y','Y','')],default='X')
    labels_visible:BoolProperty(name='Show asset labels',default=True,update=scene_labels_changed)
    overhead_visible:BoolProperty(name='Show overhead assets',default=True,update=overhead_changed)
    oht_height:FloatProperty(name='Rail height (m)',default=5.2,min=1,max=20)
    oht_width:FloatProperty(name='Loop width',default=10,min=3,max=40)
    oht_depth:FloatProperty(name='Loop depth',default=6,min=3,max=40)
    rail_next:EnumProperty(name='Next rail',items=[('rail_straight','Straight 2m',''),('rail_curve','90° corner','')])
    camera_direction:EnumProperty(name='Camera',items=[('0','Front right',''),('90','Back right',''),
        ('180','Back left',''),('270','Front left','')],default='0')
    aspect:EnumProperty(name='Aspect',items=[('4:3','4:3',''),('16:9','16:9','')],default='4:3')
    output_dir:StringProperty(name='Output folder',subtype='DIR_PATH')
    font_path:StringProperty(name='Local font',subtype='FILE_PATH',description='Optional TTF/OTF font for non-Latin labels; packed when saving with FAB Kit')
    status:StringProperty(name='Status')


def register_library(context):
    path=str((core.data_dir()/'library').resolve())
    if not Path(path,'index.json').is_file():
        raise FileNotFoundError('Library not found. Set the data folder in Add-on Preferences.')
    libs=context.preferences.filepaths.asset_libraries
    lib=next((lib for lib in libs if Path(bpy.path.abspath(lib.path)).resolve()==Path(path)),None)
    if not lib:
        lib=libs.new(name='FAB Scene Kit',directory=path)
    lib.import_method='APPEND_REUSE'
    return lib


class FAB_OT_new_scene(bpy.types.Operator):
    bl_idname='fab.new_scene'
    bl_label='Create New Scene'
    bl_description='Load a new independent scene; preserves the current scene'
    bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT'
    def execute(self,context):
        kind=context.scene.fab.template
        theme=context.scene.fab.theme
        try:
            scene=core.load_template(context,kind)
            scene.fab.theme=theme
            core.apply_theme(scene)
            core.fit_camera(scene)
            for area in context.screen.areas if context.screen else []:
                if area.type=='VIEW_3D':
                    area.spaces.active.region_3d.view_perspective='CAMERA'
                    area.spaces.active.region_3d.view_camera_zoom=-10
                    area.spaces.active.region_3d.view_camera_offset=(0,0)
                    area.spaces.active.overlay.show_extras=False
                    area.spaces.active.overlay.show_relationship_lines=False
                    area.spaces.active.overlay.show_floor=False
                    area.spaces.active.overlay.show_axis_x=False
                    area.spaces.active.overlay.show_axis_y=False
                    area.spaces.active.shading.color_type='MATERIAL'
                    area.spaces.active.shading.show_cavity=True
            self.report({'INFO'},'Created '+scene.name)
            return {'FINISHED'}
        except (OSError,ValueError,RuntimeError) as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


class FAB_OT_add(bpy.types.Operator):
    bl_idname='fab.add_asset'
    bl_label='Add at 3D Cursor'
    bl_description='Add at the 3D Cursor XY and active floor/rail height; press G to move'
    bl_options={'REGISTER','UNDO'}
    asset_id:StringProperty(options={'HIDDEN','SKIP_SAVE'})
    @classmethod
    def poll(cls,context):
        return context.scene.fab.enabled and context.mode=='OBJECT'
    def execute(self,context):
        scene=context.scene
        aid=self.asset_id or scene.fab.asset_id
        if not aid or aid=='NONE':
            self.report({'WARNING'},'Choose an asset.')
            return {'CANCELLED'}
        try:
            root=core.add_asset(scene,aid,scene.cursor.location,
                                label=core.catalog()[aid]['category']!='PEOPLE')
            core.snap(scene,root)
            core.select(context,root)
            core.update_label(scene,root)
            scene.fab.status='Added '+root.fab.label+' — G to move, R Z to rotate'
            return {'FINISHED'}
        except (OSError,ValueError,RuntimeError) as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


class FAB_OT_action(bpy.types.Operator):
    bl_idname='fab.action'
    bl_label='FAB action'
    bl_options={'UNDO'}
    action:StringProperty(options={'HIDDEN','SKIP_SAVE'})
    @classmethod
    def description(cls,context,properties):
        return ACTION_HELP.get(properties.action,'Apply this change to the current FAB scene')
    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT'
    def execute(self,context):
        scene=context.scene
        settings=scene.fab
        chosen=core.selected_roots(context)
        root=core.root_of(context.active_object)
        try:
            if self.action=='REGISTER_LIBRARY':
                register_library(context)
                self.report({'INFO'},'Library registered. Save Preferences to keep this setting.')
            elif self.action=='BROWSER':
                lib=register_library(context)
                area=next((a for a in context.screen.areas
                           if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS'),None)
                viewport=next((a for a in context.screen.areas if a.type=='VIEW_3D'),None)
                if viewport and (area is None or area.height<context.window.height*.18):
                    # area_move requires the real mouse to be over an editor border.
                    # Split the viewport instead; this works from sidebar buttons too.
                    if area:
                        area.type='DOPESHEET_EDITOR'
                        area.ui_type='TIMELINE'
                    before={a.as_pointer() for a in context.screen.areas}
                    region=next(r for r in viewport.regions if r.type=='WINDOW')
                    with context.temp_override(area=viewport,region=region):
                        bpy.ops.screen.area_split(direction='HORIZONTAL',factor=.30)
                    created=[a for a in context.screen.areas if a.as_pointer() not in before]
                    area=min([viewport]+created,key=lambda a:a.y)
                if area:
                    area.type='FILE_BROWSER'
                    area.ui_type='ASSETS'
                    if area.spaces.active.params:
                        area.spaces.active.params.display_size=64
                    # Asset Browser parameters become available on the next redraw.
                    def focus_library():
                        try:
                            params=area.spaces.active.params
                            if params:
                                params.asset_library_reference=lib.name
                                # Explicit root catalog includes all seven FAB categories.
                                # A nil UUID selects an empty catalog, not "All".
                                params.catalog_id='fb8b40b8-b3b6-58ad-bbee-fec50f444dcb'
                                params.filter_search=''
                                params.display_size=64
                                area.tag_redraw()
                        except (ReferenceError,TypeError,ValueError,AttributeError):
                            pass
                        return None
                    bpy.app.timers.register(focus_library,first_interval=.15)
                else:
                    self.report({'INFO'},'Set an editor to Asset Browser, then select FAB Scene Kit.')
            elif not settings.enabled:
                raise ValueError('Create a FAB scene first.')
            elif self.action=='THEME':
                core.apply_theme(scene)
            elif self.action=='RESIZE':
                core.resize_stage(scene)
                core.fit_camera(scene)
            elif self.action=='LABELS':
                core.sync_labels(scene)
            elif self.action=='CLEAR_SEARCH':
                settings.category='ALL'
                settings.search=''
            elif self.action in {'SELECT_ROOM','EDIT_ROOM'}:
                room=core.room_for(scene)
                if not room:
                    raise ValueError('This scene has no cleanroom. Add Cleanroom cutaway from Space assets.')
                core.select(context,room)
                if self.action=='EDIT_ROOM':
                    core.make_editable(scene,room)
                    parts=[obj for obj in room.children if obj.type=='MESH']
                    if parts:
                        core.select(context,max(parts,key=lambda obj:obj.dimensions.x*obj.dimensions.y))
                    settings.status='Parts ready: select a part and use Edit Selected Mesh. Ctrl+Z undoes conversion.'
            elif self.action=='SELECT_ROOT':
                if not root:
                    raise ValueError('Select an asset or one of its parts.')
                core.select(context,root)
            elif self.action=='CAMERA':
                angle=math.radians(float(settings.camera_direction))
                direction=MatrixRotation(angle) @ core.Vector((28,-28,28))
                scene.camera.location=direction
                core.g.aim(scene.camera,(0,0,0))
                core.fit_camera(scene)
            elif self.action in {'FIT','FIT_SELECTION'}:
                if self.action=='FIT_SELECTION' and not chosen:
                    raise ValueError('Select one or more assets first.')
                core.fit_camera(scene,chosen if self.action=='FIT_SELECTION' else None)
            elif self.action=='ASPECT':
                scene.render.resolution_x=2400
                scene.render.resolution_y=1800 if settings.aspect=='4:3' else 1350
                core.fit_camera(scene)
            elif self.action=='OHT_LOOP':
                result=core.add_oht_loop(scene,scene.cursor.location.xy,settings.oht_width,settings.oht_depth,settings.oht_height)
                core.select(context,result)
            elif self.action=='OHT_VISIBILITY':
                core.set_overhead_visibility(scene)
            elif self.action=='CHECK':
                issues=core.report(scene)
                settings.status='; '.join(issues) if issues else f'OK · {len(core.roots(scene))} assets'
                self.report({'WARNING'} if issues else {'INFO'},settings.status[:240])
            elif self.action=='SAVE':
                if not settings.output_dir:
                    raise ValueError('Choose an output folder first.')
                core.sync_labels(scene)
                path=core.next_path(settings.output_dir,'fab_scene','.blend')
                # Pack only a font explicitly chosen by the user.
                if settings.font_path:
                    for font in bpy.data.fonts:
                        if font.filepath and font.filepath!='<builtin>' and Path(bpy.path.abspath(font.filepath))==Path(bpy.path.abspath(settings.font_path)):
                            font.pack()
                settings.status='Saved '+path.name
                bpy.ops.wm.save_as_mainfile(filepath=str(path))
            elif not root:
                raise ValueError('Select a FAB asset first.')
            elif self.action=='ADOPT':
                for obj in chosen:
                    core.adopt(scene,obj)
            elif self.action=='ROTATE':
                for obj in chosen:
                    obj.rotation_euler.z+=math.pi/2
                    core.update_label(scene,obj)
            elif self.action=='SNAP':
                for obj in chosen:
                    core.snap(scene,obj)
            elif self.action=='DUPLICATE':
                vec=(settings.spacing,0,0) if settings.axis=='X' else (0,settings.spacing,0)
                result=core.duplicate(scene,root,vec)
                core.select(context,result)
            elif self.action=='ARRAY':
                for i in range(1,settings.copy_count+1):
                    vec=(i*settings.spacing,0,0) if settings.axis=='X' else (0,i*settings.spacing,0)
                    core.duplicate(scene,root,vec)
            elif self.action=='ALIGN':
                axis=0 if settings.axis=='X' else 1
                ordered=sorted(chosen,key=lambda o:o.location[axis])
                if len(ordered)<2:
                    raise ValueError('Select at least two assets to align.')
                start=ordered[0].location[axis]
                transverse=ordered[0].location[1-axis]
                for i,obj in enumerate(ordered):
                    obj.location[axis]=start+i*settings.spacing
                    obj.location[1-axis]=transverse
            elif self.action=='HIGHLIGHT':
                for obj in chosen:
                    obj.fab.highlighted=not obj.fab.highlighted
                    core.highlight(scene,obj,obj.fab.highlighted)
            elif self.action=='EDITABLE':
                for obj in chosen:
                    core.make_editable(scene,obj)
                parts=[obj for obj in root.children if obj.type=='MESH']
                if parts:
                    core.select(context,max(parts,key=lambda obj:obj.dimensions.x*obj.dimensions.y))
                settings.status='Parts ready: select a part and use Edit Selected Mesh. Ctrl+Z undoes conversion.'
            elif self.action=='REPLACE':
                aid=settings.asset_id
                if not aid or aid=='NONE':
                    raise ValueError('Choose a replacement in Add Assets.')
                model=core.master(scene,aid)
                for obj in chosen:
                    if not obj.instance_collection:
                        raise ValueError('Replacement supports collection instances only.')
                for obj in chosen:
                    obj.instance_collection=model
                    obj['fab_asset']=aid
                    obj['fab_version']=core.VERSION
                    obj.fab.highlighted=False
                    core.update_label(scene,obj)
            elif self.action=='RAIL':
                result=core.connect_rail(scene,root,settings.rail_next)
                core.select(context,result)
            elif self.action=='VEHICLE':
                if not root.instance_collection or 'fab_end' not in root.instance_collection:
                    raise ValueError('Select a rail segment.')
                col=root.instance_collection
                pos=root.matrix_world @ core.Vector(col.get('fab_vehicle_pos',(1,0,0)))
                angle=root.rotation_euler.z+float(col.get('fab_vehicle_angle',0))
                result=core.add_asset(scene,'oht_vehicle',pos,angle,label=False)
                core.select(context,result)
            else:
                raise ValueError('Unknown action.')
            return {'FINISHED'}
        except (OSError,ValueError,RuntimeError,KeyError) as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


def MatrixRotation(angle):
    from mathutils import Matrix
    return Matrix.Rotation(angle,3,'Z')


class FAB_OT_render(bpy.types.Operator):
    bl_idname='fab.render'
    bl_label='Render FAB'
    quality:EnumProperty(items=[('PREVIEW','Preview',''),('FINAL','Final','')])
    @classmethod
    def poll(cls,context):
        return context.scene.fab.enabled and context.scene.camera is not None and not bpy.app.is_job_running('RENDER')
    def execute(self,context):
        scene=context.scene
        if not scene.fab.output_dir:
            self.report({'ERROR'},'Choose an output folder first.')
            return {'CANCELLED'}
        try:
            core.sync_labels(scene)
            path=core.next_path(scene.fab.output_dir,'fab_'+scene.fab.theme.lower()+'_'+self.quality.lower(),'.png')
            scene.render.filepath=str(path)
            scene.render.resolution_percentage=50 if self.quality=='PREVIEW' else 100
            scene.eevee.taa_render_samples=32 if self.quality=='PREVIEW' else 96
            scene['fab_render_pending']=True
            scene.fab.status='Rendering '+path.name+' — Esc cancels'
            if bpy.app.background:
                bpy.ops.render.render(write_still=True)
            else:
                bpy.ops.render.render('INVOKE_DEFAULT',write_still=True)
            return {'FINISHED'}
        except (OSError,RuntimeError) as exc:
            scene['fab_render_pending']=False
            scene.fab.status='Render failed: '+str(exc)
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


ACTION_HELP={
    'BROWSER':'Open the bundled FAB thumbnails below the viewport; drag a thumbnail into the scene',
    'SELECT_ROOM':'Select and unlock the cleanroom assembly. G moves it; use Width and Depth to resize it',
    'EDIT_ROOM':'Convert the cleanroom into local editable parts. Select a part and press Tab. Ctrl+Z undoes conversion',
    'EDITABLE':'Convert selected instances into independent parts. Select a part and press Tab to edit its mesh',
    'SELECT_ROOT':'Select the whole assembly to move all its parts together',
    'RESIZE':'Resize only the outer stage. The cleanroom and equipment keep their sizes and positions',
    'SNAP':'Snap selected assets to the chosen placement level and XY grid',
    'DUPLICATE':'Copy the active assembly once, offset by Axis and Spacing',
    'ARRAY':'Add Copies new assemblies in a row, starting after the active assembly',
    'ALIGN':'Line up two or more selected assemblies using Axis and Spacing',
    'REPLACE':'Replace selected instance models with the asset chosen in Add Assets; keep position and labels',
    'ADOPT':"Apply this scene's theme, labels, grid and placement level to selected library instances",
    'SAVE':'Save the entire Blender file, including all scenes, to a new numbered .blend in the output folder',
    'CHECK':'Check missing models, duplicate IDs, transforms and stage bounds. Visual inspection is still needed',
    'FIT':'Frame all visible scene content in the render camera',
    'FIT_SELECTION':'Frame selected assemblies in the render camera',
    'RAIL':'Connect a new segment at the selected rail endpoint',
    'VEHICLE':'Place a vehicle on the selected rail segment',
}


def button(layout,action,text,icon='NONE',enabled=True):
    row=layout.row(align=True)
    row.enabled=enabled
    op=row.operator('fab.action',text=text,icon=icon)
    op.action=action


class FAB_OT_edit_part(bpy.types.Operator):
    bl_idname='fab.edit_part'
    bl_label='Edit Selected Mesh'
    bl_description='Enter mesh Edit Mode for the selected part, or finish mesh editing; independent of keyboard mapping'
    bl_options={'UNDO'}
    @classmethod
    def poll(cls,context):
        return bool(context.active_object and context.active_object.type=='MESH' and context.mode in {'OBJECT','EDIT_MESH'})
    def execute(self,context):
        bpy.ops.object.mode_set(mode='OBJECT' if context.mode=='EDIT_MESH' else 'EDIT')
        return {'FINISHED'}


def message(layout,text,context,icon='NONE'):
    # Blender region coordinates include UI scaling. Wrap prose, not editable paths.
    scale=context.preferences.system.ui_scale
    width=max(18,int(context.region.width/max(scale,.5)/7)-5) if context.region else 35
    col=layout.column(align=True)
    col.scale_y=.85
    for i,line in enumerate(textwrap.wrap(text,width=width)):
        col.label(text=line,icon=icon if i==0 else 'NONE')


class FAB_PT_main(bpy.types.Panel):
    bl_label='FAB Scene Kit'
    bl_idname='FAB_PT_main'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='FAB Kit'
    def draw(self,context):
        s=context.scene.fab
        lay=self.layout
        if not s.enabled:
            message(lay,'Choose a template to start assembling your FAB scene.',context)
            lay.prop(s,'template')
            lay.prop(s,'theme',expand=True)
            lay.operator('fab.new_scene',icon='SCENE_DATA')
        else:
            lay.prop(s,'theme',expand=True)
            button(lay,'THEME','Apply Theme','SHADING_RENDERED')
            if context.mode!='OBJECT':
                message(lay,'Use Blender mesh tools to edit this part.',context,'EDITMODE_HLT')
                lay.operator('fab.edit_part',text='Finish Mesh Editing',icon='CHECKMARK')


class FABPanel:
    bl_parent_id='FAB_PT_main'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    @classmethod
    def poll(cls,context):
        return context.scene.fab.enabled and context.mode=='OBJECT'


class FAB_PT_setup(FABPanel,bpy.types.Panel):
    bl_label='New Scene'
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        lay=self.layout
        lay.prop(context.scene.fab,'template')
        lay.operator('fab.new_scene',icon='SCENE_DATA')
        message(lay,'Creates another scene using the theme above. Current scenes are kept.',context)


class FAB_PT_assets(FABPanel,bpy.types.Panel):
    bl_label='Add Assets'
    def draw(self,context):
        s=context.scene.fab
        lay=self.layout
        lay.use_property_split=True
        lay.use_property_decorate=False
        button(lay,'BROWSER','Browse Thumbnails','ASSET_MANAGER')
        lay.prop(s,'category')
        row=lay.row(align=True)
        row.prop(s,'search',icon='VIEWZOOM')
        if s.search or s.category!='ALL':
            button(row,'CLEAR_SEARCH','','X')
        lay.prop(s,'asset_id')
        lay.prop(s,'placement')
        if s.placement=='CUSTOM':
            lay.prop(s,'floor_z',text='Height (m)')
        lay.prop(s,'grid')
        can_add=s.asset_id not in {'','NONE'} and (s.placement!='CLEANROOM' or core.room_for(context.scene) is not None)
        row=lay.row()
        row.scale_y=1.2
        row.enabled=can_add
        row.operator('fab.add_asset',icon='ADD')
        if s.asset_id=='NONE':
            message(lay,'No matches. Clear Search or change Category.',context,'INFO')
        elif s.placement=='CLEANROOM' and not core.room_for(context.scene):
            message(lay,'No cleanroom yet. Choose Stage to add one.',context,'INFO')
        else:
            message(lay,'Set the 3D Cursor, then add. G: move / R Z: rotate.',context)
        root=core.root_of(context.active_object)
        if root and not root.get('fab_id'):
            button(lay,'ADOPT','Use FAB Settings','CHECKMARK')


class FAB_PT_selection(FABPanel,bpy.types.Panel):
    bl_label='Selected Asset'
    def draw(self,context):
        root=core.root_of(context.active_object)
        lay=self.layout
        lay.use_property_split=True
        lay.use_property_decorate=False
        if not root:
            message(lay,'Select equipment in the viewport. Use Cleanroom & Stage for the floor.',context)
            return
        if root.get('fab_asset')=='cleanroom':
            message(lay,'Cleanroom selected. Use Cleanroom & Stage to move, resize or edit its parts.',context)
            return
        if not root.get('fab_id'):
            message(lay,'Library instance: apply the current theme and placement settings.',context)
            button(lay,'ADOPT','Use FAB Settings')
            return
        message(lay,root.fab.label or root.name,context,'OBJECT_DATA')
        if context.active_object!=root:
            button(lay,'SELECT_ROOT','Select Whole Asset','OUTLINER_OB_EMPTY')
        row=lay.row(align=True)
        button(row,'ROTATE','Rotate 90°')
        button(row,'SNAP','Snap to Level')
        lay.prop(root.fab,'label')
        lay.prop(root.fab,'code')
        lay.prop(root.fab,'label_mode')
        button(lay,'HIGHLIGHT','Remove Highlight' if root.fab.highlighted else 'Highlight Asset')


class FAB_PT_details(FABPanel,bpy.types.Panel):
    bl_label='Label & Geometry Details'
    bl_parent_id='FAB_PT_selection'
    bl_options={'DEFAULT_CLOSED'}
    @classmethod
    def poll(cls,context):
        root=core.root_of(context.active_object)
        return context.scene.fab.enabled and context.mode=='OBJECT' and bool(root and root.get('fab_id'))
    def draw(self,context):
        root=core.root_of(context.active_object)
        s=context.scene.fab
        lay=self.layout
        lay.use_property_split=True
        lay.use_property_decorate=False
        col=lay.column()
        col.enabled=root.fab.label_mode!='HIDDEN'
        col.prop(root.fab,'size')
        col.prop(root.fab,'offset')
        if not s.labels_visible:
            message(lay,'Labels are hidden in Scene Text.',context,'INFO')
        message(lay,'Replacement: '+dict((i[0],i[1]) for i in items(s,context)).get(s.asset_id,'None'),context)
        chosen=core.selected_roots(context)
        button(lay,'REPLACE','Replace Model / Pose',enabled=bool(chosen) and all(o.instance_collection for o in chosen) and s.asset_id not in {'','NONE'})
        button(lay,'EDITABLE','Edit Individual Parts','EDITMODE_HLT',enabled=any(o.instance_collection for o in chosen))
        if not root.instance_collection:
            lay.operator('fab.edit_part',icon='EDITMODE_HLT')
            message(lay,'Parts are editable. Click a part, then Tab. Select Whole Asset moves the assembly.',context)


class FAB_PT_arrange(FABPanel,bpy.types.Panel):
    bl_label='Duplicate & Arrange'
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        s=context.scene.fab
        lay=self.layout
        root=core.root_of(context.active_object)
        chosen=core.selected_roots(context)
        if not root:
            message(lay,'Select an asset to duplicate. Select two or more to align.',context)
        lay.prop(s,'axis',expand=True)
        lay.prop(s,'spacing')
        button(lay,'DUPLICATE','Duplicate Once','DUPLICATE',enabled=bool(root))
        lay.prop(s,'copy_count',text='Additional copies')
        button(lay,'ARRAY','Create Row',enabled=bool(root))
        button(lay,'ALIGN','Align Selected',enabled=len(chosen)>=2)


class FAB_PT_space(FABPanel,bpy.types.Panel):
    bl_label='Cleanroom & Stage'
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        s=context.scene.fab
        room=core.room_for(context.scene)
        lay=self.layout
        lay.use_property_split=True
        lay.use_property_decorate=False
        if room:
            if len([o for o in core.roots(context.scene) if o.get('fab_asset')=='cleanroom'])>1:
                lay.prop(s,'room',text='Target room')
            button(lay,'SELECT_ROOM','Select Cleanroom','RESTRICT_SELECT_OFF')
            lay.prop(room.fab,'width')
            lay.prop(room.fab,'depth')
            button(lay,'EDIT_ROOM','Edit Floor / Wall Parts','EDITMODE_HLT')
            if not room.instance_collection:
                row=lay.row()
                row.enabled=bool(context.active_object and context.active_object.parent==room)
                row.operator('fab.edit_part',icon='EDITMODE_HLT')
                message(lay,'Parts ready. Click a floor or wall part, then Edit Selected Mesh.',context,'EDITMODE_HLT')
            message(lay,'G moves the selected room. Size changes affect the room only; equipment stays in place.',context)
        else:
            message(lay,'No cleanroom. Add Cleanroom cutaway from Space assets.',context)
        lay.separator()
        lay.label(text='Outer Stage',icon='MESH_PLANE')
        lay.prop(s,'width')
        lay.prop(s,'depth')
        button(lay,'RESIZE','Resize Outer Stage')


class FAB_PT_scene(FABPanel,bpy.types.Panel):
    bl_label='Scene Text'
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        s=context.scene.fab
        lay=self.layout
        lay.prop(s,'title')
        lay.prop(s,'labels_visible')
        lay.prop(s,'font_path')
        button(lay,'LABELS','Apply Font / Refresh Labels')


class FAB_PT_oht(FABPanel,bpy.types.Panel):
    bl_label='OHT & Overhead'
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        s=context.scene.fab
        lay=self.layout
        lay.use_property_split=True
        lay.use_property_decorate=False
        lay.prop(s,'overhead_visible')
        if not s.overhead_visible:
            message(lay,'Turn on overhead visibility before adding rails or vehicles.',context)
        col=lay.column()
        col.enabled=s.overhead_visible
        col.prop(s,'oht_height')
        col.prop(s,'oht_width',text='Loop width (m)')
        col.prop(s,'oht_depth',text='Loop depth (m)')
        button(col,'OHT_LOOP','Add Loop at Cursor')
        col.separator()
        col.prop(s,'rail_next')
        root=core.root_of(context.active_object)
        is_rail=bool(root and root.instance_collection and 'fab_end' in root.instance_collection)
        button(col,'RAIL','Connect Next Rail',enabled=is_rail)
        button(col,'VEHICLE','Add Vehicle on Rail',enabled=is_rail)
        if not is_rail:
            message(col,'Select a straight or curved rail to extend it or add a vehicle.',context)


class FAB_PT_output(FABPanel,bpy.types.Panel):
    bl_label='Camera & Output'
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        s=context.scene.fab
        lay=self.layout
        lay.prop(s,'camera_direction')
        button(lay,'CAMERA','Apply Camera Direction')
        row=lay.row(align=True)
        button(row,'FIT','Frame All')
        button(row,'FIT_SELECTION','Frame Selected',enabled=bool(core.selected_roots(context)))
        lay.prop(s,'aspect',expand=True)
        button(lay,'ASPECT','Apply Aspect Ratio')
        lay.label(text='Output Folder')
        lay.prop(s,'output_dir',text='')
        if not s.output_dir:
            message(lay,'Choose an output folder to render or save.',context,'FILE_FOLDER')
        row=lay.row(align=True)
        row.enabled=bool(s.output_dir)
        row.operator('fab.render',text='Preview 50%').quality='PREVIEW'
        row.operator('fab.render',text='Render PNG').quality='FINAL'
        button(lay,'SAVE','Save New .blend','FILE_TICK',enabled=bool(s.output_dir))
        button(lay,'CHECK','Check Scene','CHECKMARK')
        if s.status:
            lay.label(text='Last Action')
            message(lay,s.status,context,'INFO')


@persistent
def load_post(_):
    for scene in bpy.data.scenes:
        core.migrate_scene(scene)


def migrate_pending():
    load_post(None)
    return None


@persistent
def render_complete(scene):
    if scene.get('fab_render_pending'):
        scene['fab_render_pending']=False
        scene.fab.status='Rendered '+Path(scene.render.filepath).name


@persistent
def render_cancel(scene):
    if scene.get('fab_render_pending'):
        scene['fab_render_pending']=False
        scene.fab.status='Render cancelled. Adjust the scene and try again.'


classes=(FABPreferences,FABInstance,FABSettings,FAB_OT_new_scene,FAB_OT_add,FAB_OT_action,FAB_OT_edit_part,
         FAB_OT_render,FAB_PT_main,FAB_PT_setup,FAB_PT_assets,FAB_PT_space,FAB_PT_selection,FAB_PT_details,
         FAB_PT_arrange,FAB_PT_scene,FAB_PT_oht,FAB_PT_output)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fab=PointerProperty(type=FABSettings)
    bpy.types.Object.fab=PointerProperty(type=FABInstance)
    author.register()
    bpy.app.handlers.load_post.append(load_post)
    bpy.app.handlers.render_complete.append(render_complete)
    bpy.app.handlers.render_cancel.append(render_cancel)
    # Extension enable runs with RestrictData; migrate only after registration.
    bpy.app.timers.register(migrate_pending,first_interval=.1)


def unregister():
    author.unregister()
    if bpy.app.timers.is_registered(migrate_pending):
        bpy.app.timers.unregister(migrate_pending)
    for handlers,callback in [(bpy.app.handlers.render_complete,render_complete),(bpy.app.handlers.render_cancel,render_cancel)]:
        if callback in handlers:
            handlers.remove(callback)
    if load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post)
    del bpy.types.Object.fab
    del bpy.types.Scene.fab
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
