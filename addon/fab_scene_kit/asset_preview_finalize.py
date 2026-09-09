"""Blender subprocess: embed a thumbnail in an already isolated asset file."""
import sys
import bpy

name,thumbnail=sys.argv[sys.argv.index('--')+1:]
collection=bpy.data.collections.get(name)
if not collection or not collection.asset_data:
    raise ValueError('Expected the exported asset collection.')
with bpy.context.temp_override(id=collection):
    bpy.ops.ed.lib_id_load_custom_preview(filepath=thumbnail)
assert tuple(collection.preview.image_size)==(256,256)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
