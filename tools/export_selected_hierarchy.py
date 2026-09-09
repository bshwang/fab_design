import bpy

MAX_DEPTH = None  # None: full tree. Use 2 for a shorter overview.

selected = set(bpy.context.selected_objects)
if not selected:
    raise RuntimeError("Select the robot's root object in Object Mode first.")

def has_selected_ancestor(obj):
    parent = obj.parent
    while parent:
        if parent in selected:
            return True
        parent = parent.parent
    return False

roots = sorted((o for o in selected if not has_selected_ancestor(o)),
               key=lambda o: o.name)
lines = []
stack = [(o, 0) for o in reversed(roots)]
while stack:
    obj, depth = stack.pop()
    children = sorted(obj.children, key=lambda o: o.name)
    suffix = f" (+{len(children)} children)" if children else ""
    name = obj.name.replace("\n", " ").replace("\r", " ")
    lines.append(f"{'  ' * depth}{name} [{obj.type}]{suffix}")
    if MAX_DEPTH is None or depth < MAX_DEPTH:
        stack.extend((child, depth + 1) for child in reversed(children))

report = "\n".join(lines)
block = bpy.data.texts.new("Robot_Hierarchy.txt")
block.write(report)
characters = len(report.encode("utf-16-le")) // 2
if characters <= 1000:
    bpy.context.window_manager.clipboard = report
    print(f"Hierarchy copied: {characters}/1000 characters.")
else:
    print(f"Hierarchy: {characters} characters. Not copied (1000 limit).")
    print("Use MAX_DEPTH = 2 or select a smaller assembly and run again.")
if bpy.context.space_data and bpy.context.space_data.type == 'TEXT_EDITOR':
    bpy.context.space_data.text = block
print(report)
