"""Small context-free Blender geometry helpers; no external modules."""
import math
import bpy
from mathutils import Vector


def linear(hex_color):
    values = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values) + (1,)


def material(name, color, metallic=0, roughness=.46):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = linear(color)
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = mat.diffuse_color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    mat['fab_role'] = name
    return mat


def mesh(name, vertices, faces, col, mat=None, bevel=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    if mat:
        data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod = obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return obj


def box(name, pos, dims, col, mat, bevel=.04):
    x, y, z = [v / 2 for v in dims]
    vertices = [(-x,-y,-z), (x,-y,-z), (x,y,-z), (-x,y,-z),
                (-x,-y,z), (x,-y,z), (x,y,z), (-x,y,z)]
    obj = mesh(name, vertices, [(0,3,2,1),(4,5,6,7),(0,1,5,4),
                               (1,2,6,5),(2,3,7,6),(3,0,4,7)], col, mat, bevel)
    obj.location = pos
    return obj


def cylinder(name, pos, r, depth, col, mat, n=32, bevel=.018):
    vertices = [(r*math.cos(2*math.pi*i/n), r*math.sin(2*math.pi*i/n), z)
                for z in (-depth/2, depth/2) for i in range(n)]
    faces = [tuple(reversed(range(n))), tuple(range(n, n*2))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    obj = mesh(name, vertices, faces, col, mat, bevel)
    obj.location = pos
    for poly in obj.data.polygons[2:]:
        poly.use_smooth = True
    return obj


def rod(name, a, b, r, col, mat):
    a, b = Vector(a), Vector(b)
    obj = cylinder(name, (a+b)/2, r, (b-a).length, col, mat, 24)
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return obj


def sphere(name, pos, scale, col, mat):
    n, rings = 24, 12
    vertices = [(scale[0]*math.sin(math.pi*j/rings)*math.cos(2*math.pi*i/n),
                 scale[1]*math.sin(math.pi*j/rings)*math.sin(2*math.pi*i/n),
                 scale[2]*math.cos(math.pi*j/rings))
                for j in range(rings+1) for i in range(n)]
    faces = [(j*n+i, j*n+(i+1)%n, (j+1)*n+(i+1)%n, (j+1)*n+i)
             for j in range(rings) for i in range(n)]
    obj = mesh(name, vertices, faces, col, mat)
    obj.location = pos
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def curve(name, points, radius, col, mat):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    return obj


def text(name, body, pos, size, col, mat):
    data = bpy.data.curves.new(name, 'FONT')
    data.body = body
    data.align_x = 'CENTER'
    data.align_y = 'CENTER'
    data.size = size
    data.extrude = .001
    data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    obj.location = pos
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()
