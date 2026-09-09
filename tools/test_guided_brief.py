"""Exercise Guided Brief on synthetic multi-root CAD and actual evaluated armature poses."""
from pathlib import Path
import hashlib
import importlib
import json
import math
import sys
import uuid
import bpy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/testing/guided_042'/uuid.uuid4().hex[:8];OUT.mkdir(parents=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
installed='--installed' in args
if installed:
    assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(ROOT/'docs/testing')
    repo_dir=OUT/'extensions';repo_dir.mkdir()
    bpy.ops.preferences.extension_repo_add(name='FAB Guided Offline Test',type='LOCAL',use_custom_directory=True,custom_directory=str(repo_dir))
    repo=next(r for r in bpy.context.preferences.extensions.repos if Path(r.directory)==repo_dir)
    package=ROOT/'dist/fab_scene_kit-0.4.2.zip'
    bpy.ops.extensions.package_install_files(filepath=str(package),repo=repo.module,enable_on_install=True)
    kit=importlib.import_module('bl_ext.'+repo.module+'.fab_scene_kit')
    assert Path(kit.__file__).is_relative_to(repo_dir)
else:
    sys.path.insert(0,str(ROOT/'addon'));import fab_scene_kit as kit;kit.register()
ui=kit.author.brief_ui;scope=ui.scope;spec=ui.spec
checks=[]
def check(name,test):
    assert test,name
    checks.append(name);print('PASS',name,flush=True)
def rejects(name,fn):
    try:fn()
    except (ValueError,RuntimeError,TypeError,KeyError):check(name,True)
    else:raise AssertionError(name+' did not reject')
def select(*objects):
    for o in bpy.context.selected_objects:o.select_set(False)
    for o in objects:o.select_set(True)
    if objects:bpy.context.view_layer.objects.active=objects[0]
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;return o
def box(name,center,size,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    o=bpy.context.object;o.name=name;o.scale=size;o.parent=parent;return o
def fingerprint(objects):
    raw=[(o.name,list(map(list,o.matrix_world)),[(tuple(v.co)) for v in o.data.vertices] if o.type=='MESH' else []) for o in objects]
    return hashlib.sha256(json.dumps(raw).encode()).hexdigest()

scene=bpy.data.scenes.new('Guided Brief / Synthetic AMMR');bpy.context.window.scene=scene
root=empty('RobotRoot')
bpy.ops.object.armature_add();rig=bpy.context.object;rig.name='RobotRig';rig.parent=root
bone=rig.data.bones[0].name
arm1=box('ArmUpper',(-.45,0,.75),(.15,.2,.7),rig)
arm2=box('ArmForearm',(-.15,0,1.35),(.5,.2,.16),rig)
for o in (arm1,arm2):
    group=o.vertex_groups.new(name=bone);group.add(list(range(len(o.data.vertices))),1,'REPLACE')
    mod=o.modifiers.new('Pose','ARMATURE');mod.object=rig
helper=box('WorkspaceGuide',(0,0,1),(8,8,4),rig);helper.display_type='WIRE';helper.hide_render=True
poly=[(-1,-.7),(1,-.7),(1,-.25),(-.55,-.25),(-.55,.7),(-1,.7)]
verts=[(x,y,z) for z in (0,.35) for x,y in poly]
faces=[tuple(reversed(range(6))),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)]
mesh=bpy.data.meshes.new('SyntheticLBase');mesh.from_pydata(verts,[],faces);mesh.update()
base=bpy.data.objects.new('MobileBase',mesh);scene.collection.objects.link(base)
rack=empty('ToolShelf',base);tool=box('SpareTool',(.6,.4,.72),(.12,.12,.25),rack)
stage=box('FixtureStage',(.3,0,.5),(.4,.5,.3))
bottle=box('Container',(.3,0,.8),(.15,.15,.25),stage)
source=[root,rig,arm1,arm2,helper,base,rack,tool,stage,bottle]
bpy.context.view_layer.update();original=fingerprint(source)
s=scene.fab_brief
check('Version 0.4.2 and Guided entry point',kit.core.VERSION=='0.4.2' and scene.fab_author.workflow=='GUIDED')
select(root,base,stage,arm1)
check('Add multiple roots through actual operator',bpy.ops.fab_brief.action(action='ADD')=={'FINISHED'})
check('Overlapping selections deduplicate',len(s.sources)==len(source))
helper_row=next(r for r in s.sources if r.object==helper)
check('Workspace is a review candidate, not silently excluded',helper_row.decision=='REVIEW')
rejects('Unreviewed helper blocks confirmation',lambda:scope.confirm(s,scene))
helper_row.decision='KEEP';scope.confirm(s,scene);s.units_confirmed=True
check('Kept workspace measurably changes overall extent',scope.evaluate(bpy.context,s)['size'][0]>7.9)
select(helper);s.scope_mode='SELF';bpy.ops.fab_brief.action(action='EXCLUDE')
check('Exclusion invalidates scope confirmation',not scope.confirmed(s,scene))
bpy.ops.fab_brief.action(action='CONFIRM')
check('Reference objects are retained but not measured',len(scope.included(s,scene))==6)
s.purpose='Synthetic container transfer AMMR';s.outline='L';s.opening='Inner opening';s.features='Open base and two work mechanisms';s.handler=True
arm=next(p for p in s.parts if p.key=='arm_1');arm.arm_kind='ARTICULATED';arm.axes=7
basepart=next(p for p in s.parts if p.key=='base');handlerpart=next(p for p in s.parts if p.key=='handler')
scope.assign(s,scene,basepart,[base],False)
check('Base self assignment excludes child tools',len(basepart.bindings)==1)
scope.assign(s,scene,arm,[root],True)
check('Arm branch assignment retains workspace exclusion',len(arm.bindings)==2 and helper_row.key not in {b.source_key for b in arm.bindings})
scope.assign(s,scene,handlerpart,[stage],True)
check('Component across physical meshes',len(handlerpart.bindings)==2)
rejects('Duplicate physical ownership rejected',lambda:scope.assign(s,scene,handlerpart,[base],True))
rejects('Empty Selected Only does not inflate geometry',lambda:scope.assign(s,scene,handlerpart,[root],False))
s.relation='INDEPENDENT_Z';s.relation_a='Arm 1';s.relation_b='Cartesian handler';s.sequence='Holder > arm > equipment'
s.units_confirmed=True
check('Measure operator evaluates geometry',bpy.ops.fab_brief.action(action='MEASURE')=={'FINISHED'})
result=json.loads(s.measurement_json)
check('Overall world-scale size correct',all(abs(a-b)<1e-5 for a,b in zip(result['size'],[2,1.4,1.43])))
check('L-shaped base own height is not child rack height',all(abs(a-b)<1e-5 for a,b in zip(result['parts']['base']['size'],[2,1.4,.35])))
check('Position is overall-center XY and floor Z',abs(result['parts']['base']['center'][2]-.175)<1e-5)
check('Capture and measurement preserve source models',original==fingerprint(source))
check('Unchanged measured brief exports',bool(ui.outgoing(bpy.context,s)))
text=ui.outgoing(bpy.context,s)
check('AW1 includes function and independent motion',json.loads(text)['v']=='AW1' and 'independent vertical travel' in json.loads(text)['move'])
check('No source mesh or names by default','WorkspaceGuide' not in text and 'vertices' not in text)
check('Current brief under 1000',spec.count(text)<=1000)
file=OUT/'brief.txt';check('Actual export operator',bpy.ops.fab_brief.export_text(filepath=str(file))=={'FINISHED'})
check('File exact text with no BOM/newline',file.read_bytes()==text.encode('utf-8'))
if bpy.app.background:
    try:
        copied=bpy.ops.fab_brief.action(action='COPY')
        check('Clipboard reports success only after matching readback',copied=={'FINISHED'} and bpy.context.window_manager.clipboard==text)
    except RuntimeError as exc:
        check('Unavailable background clipboard explicitly reported','Clipboard verification failed' in str(exc))
else:
    check('Actual clipboard and readback',bpy.ops.fab_brief.action(action='COPY')=={'FINISHED'} and bpy.context.window_manager.clipboard==text)

rig.pose.bones[bone].location.y=.3;bpy.context.view_layer.update()  # bone local Y is world Z
check('Pose change marks measurement stale',s.measurement_dirty)
rejects('Stale measured export rejected',lambda:ui.outgoing(bpy.context,s))
s.measurement_dirty=False
rejects('Final export detects changed geometry even without dirty flag',lambda:ui.outgoing(bpy.context,s))
s.include_measurements=False
check('Description export can omit stale measurements',json.loads(ui.outgoing(bpy.context,s))['size'] is None)
s.units_confirmed=True;bpy.ops.fab_brief.action(action='MEASURE');posed=json.loads(s.measurement_json)
check('Actual armature deformation measured',abs(posed['size'][2]-1.73)<1e-5)
s.front='POS_X';check('Frame change invalidates confirmation of units and measurement',not s.units_confirmed and s.measurement_dirty)
s.units_confirmed=True;bpy.ops.fab_brief.action(action='MEASURE');rotated=json.loads(s.measurement_json)
check('Front frame rotates width and depth',abs(rotated['size'][0]-1.4)<1e-5 and abs(rotated['size'][1]-2)<1e-5)
s.units='CUSTOM';s.meters_per_unit=.001;s.units_confirmed=True;bpy.ops.fab_brief.action(action='MEASURE')
check('Custom millimeter scale respected',abs(json.loads(s.measurement_json)['size'][0]-.0014)<1e-8)
s.units='SCENE';s.front='NEG_Y';s.units_confirmed=True;bpy.ops.fab_brief.action(action='MEASURE')

base.name='RenamedMobileBase';check('Rename retains source binding identity',next(r for r in s.sources if r.key==basepart.bindings[0].source_key).object==base)
scope.confirm(s,scene)
s.arm_count=2;armtwo=next(p for p in s.parts if p.key=='arm_2');armtwo.notes='Preserve this note'
s.arm_count=1;check('Removed arm card archived, not deleted',not armtwo.enabled and armtwo.notes=='Preserve this note')
s.arm_count=2;check('Second arm restored',armtwo.enabled and armtwo.notes=='Preserve this note')
s.arm_count=1
s.include_measurements=False;s.features='x'
n=spec.count(ui.outgoing(bpy.context,s))-1;s.features='x'*(1000-n)
check('Exactly 1000 characters allowed',spec.count(ui.outgoing(bpy.context,s))==1000)
s.features+='x';rejects('1001 characters blocked, not truncated',lambda:ui.outgoing(bpy.context,s))
check('Original over-budget note preserved',len(s.features)==1001-n)
s.features='가😀';check('Unicode budget uses UTF16 units',spec.count('가😀')==3)
s.features='Open base and two work mechanisms'
tree=scope.hierarchy(s,scene,2);check('Hierarchy distinguishes source/reference and exclusion','WorkspaceGuide [MESH/EXCLUDE]' in tree and 'RobotRig [ARMATURE/KEEP]' in tree)
select(base);ui.show(bpy.context,s,[arm1,arm2]);ui.restore(bpy.context,s);check('Selection inspection restores original selection',set(bpy.context.selected_objects)=={base})
save=OUT/'guided_scene.blend';bpy.ops.wm.save_as_mainfile(filepath=str(save),compress=True)
saved=ui.draft(s);draftfile=OUT/'local_draft.json'
check('Full local draft saves',bpy.ops.fab_brief.save_draft(filepath=str(draftfile))=={'FINISHED'})
check('Full draft has local sources',len(json.loads(draftfile.read_text())['sources'])==len(source))
bad=json.loads(json.dumps(saved));bad['parts'][0]['importance']='BOGUS'
before=ui.draft(s);rejects('Invalid import rejected before mutation',lambda:ui.load_draft(s,bad));check('Invalid import leaves draft intact',ui.draft(s)==before)
long=json.loads(json.dumps(saved));long['fields']['purpose']='x'*6000
rejects('Overlong imported field rejected without silent clipping',lambda:ui.load_draft(s,long))
check('Local draft loads through actual operator',bpy.ops.fab_brief.load_draft(filepath=str(draftfile))=={'FINISHED'})
s=scene.fab_brief
check('Bindings reconnect in matching blend',all(r.object for r in s.sources) and len(next(p for p in s.parts if p.key=='base').bindings)==1)
check('Import requires scope/measurement review',not s.confirmed and not s.measurement_json)
scope.confirm(s,scene);s.include_measurements=False
bpy.ops.wm.save_as_mainfile(filepath=str(save),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(save));scene=bpy.context.scene;s=scene.fab_brief
check('Blend reopens with full wizard state',s.purpose=='Synthetic container transfer AMMR' and len(s.sources)==len(source))
check('Reopened source bindings usable',json.loads(ui.outgoing(bpy.context,s))['type']=='AMMR')
check('Exactly two sidebar categories',{kit.FAB_PT_main.bl_category,kit.author.FABAUTHOR_PT_main.bl_category}=={'FAB Kit','FAB Author'})
check('Finished asset workflow accessible',bpy.ops.fab_brief.action(action='LIBRARY')=={'FINISHED'} and scene.fab_author.workflow=='ADVANCED' and scene.fab_author.step=='LIBRARY')
scene.fab_author.workflow='GUIDED'
check('All 52 existing assets retained',len(kit.core.catalog())==52)

# Collection capture and missing source behavior use a separate draft scene.
second=bpy.data.scenes.new('Guided / Collection test');bpy.context.window.scene=second
c=bpy.data.collections.new('Nested collection');second.collection.children.link(c)
e=bpy.data.objects.new('ReferenceOnly',None);c.objects.link(e)
second.fab_brief.collection=c
check('Collection operator captures references',bpy.ops.fab_brief.action(action='COLLECTION')=={'FINISHED'} and len(second.fab_brief.sources)==1)
second.fab_brief.sources[0].object=None
check('Missing sources reported',bool(scope.issues(second.fab_brief,second)))
select(e)
check('Missing source reconnects through actual operator',bpy.ops.fab_brief.action(action='RECONNECT')=={'FINISHED'} and second.fab_brief.sources[0].object==e)
bpy.context.window.scene=scene
s.step=0;scene.fab_author.workflow='GUIDED'
bpy.ops.wm.save_as_mainfile(filepath=str(save),compress=True)
report={'version':kit.core.VERSION,'installed':installed,'passed':True,'checks':checks,'output':str(OUT.relative_to(ROOT)),
        'blend':str(save.relative_to(ROOT)),'source_objects':len(source),'brief_characters':spec.count(ui.outgoing(bpy.context,s))}
if installed:report['zip_sha256']=hashlib.sha256(package.read_bytes()).hexdigest()
(ROOT/'docs/testing'/('guided_installed_042.json' if installed else 'guided_042.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GUIDED PASSED',len(checks),flush=True)
