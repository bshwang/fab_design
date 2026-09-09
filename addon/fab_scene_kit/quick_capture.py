"""Local evaluated geometry -> major oriented envelopes. Uses Blender's NumPy."""
import math
import time
import numpy as np
import bpy
from mathutils import Euler, Matrix, Vector
from . import author_model as model, quick_spec as codec

MAX_VERTICES = 5_000_000


def sources(context):
    if context.mode != 'OBJECT':
        raise ValueError('Switch to Object Mode and select the whole model.')
    result = {}; visited = set()
    def visit(obj):
        if obj.as_pointer() in visited:
            return
        visited.add(obj.as_pointer())
        if obj.get('fab_author_generated') or obj.get('fab_quick_preview'):
            raise ValueError('Select the original model, not its shape guide.')
        if obj.instance_type == 'COLLECTION' and obj.instance_collection:
            raise ValueError('Make a working copy of the collection instance editable first.')
        if obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}:
            result[obj.as_pointer()] = obj
        for child in obj.children:
            visit(child)
    for obj in context.selected_objects:
        visit(obj)
    if not result:
        raise ValueError('Select the model objects or their parent in Object Mode.')
    return list(result.values())


def islands(mesh):
    """Connected vertex islands also work when CAD objects were joined into one mesh."""
    n = len(mesh.vertices)
    parent = np.arange(n, dtype=np.int32)
    edges = np.empty(len(mesh.edges)*2, dtype=np.int32)
    mesh.edges.foreach_get('vertices', edges)
    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    # FBX often duplicates vertices along surface/normal seams. Weld only coincident
    # coordinates in this analysis graph; never change the source mesh.
    coordinates=np.empty(n*3,dtype=np.float64)
    mesh.vertices.foreach_get('co',coordinates)
    coordinates=coordinates.reshape(-1,3)
    tolerance=max(float(np.ptp(coordinates,axis=0).max())*1e-7,1e-10)
    quantized=np.rint((coordinates-coordinates.min(0))/tolerance).astype(np.int64)
    _,first,inverse=np.unique(quantized,axis=0,return_index=True,return_inverse=True)
    parent=first[inverse].astype(np.int32)
    for a, b in edges.reshape(-1, 2):
        a, b = root(a), root(b)
        if a != b:
            parent[max(a,b)] = min(a,b)
    for _ in range(32):
        updated = parent[parent]
        if np.array_equal(parent, updated):
            break
        parent = updated
    order = np.argsort(parent, kind='stable')
    return np.split(order, np.flatnonzero(np.diff(parent[order]))+1)


def envelope(points):
    """Prefer stable world axes unless PCA makes a materially tighter envelope."""
    basis = np.eye(3)
    lo, hi = points.min(0), points.max(0)
    size = np.maximum(hi-lo, 1e-9)
    centered = points-points.mean(0)
    if len(points) > 3:
        _, candidate = np.linalg.eigh(centered.T @ centered)
        if np.linalg.det(candidate) < 0:
            candidate[:,0] *= -1
        local = points @ candidate
        clo, chi = local.min(0), local.max(0)
        csize = np.maximum(chi-clo, 1e-9)
        if np.prod(csize) < np.prod(size)*.86:
            basis, lo, hi, size = candidate, clo, chi, csize
    return {'center': basis @ ((lo+hi)/2), 'size': size, 'basis': basis,
            'volume': float(np.prod(size))}


def split_envelopes(points, depth=0):
    box = envelope(points)
    if depth >= 4 or len(points) < 30:
        return [box]
    local = points @ box['basis']
    best = None
    # Only split if it removes substantial empty bounding volume, e.g. a connected L.
    for axis in range(3):
        for fraction in (.3, .5, .7):
            threshold = local[:,axis].min()+box['size'][axis]*fraction
            mask = local[:,axis] < threshold
            if min(mask.sum(), (~mask).sum()) < 12:
                continue
            left, right = envelope(points[mask]), envelope(points[~mask])
            ratio = (left['volume']+right['volume']) / max(box['volume'], 1e-20)
            if ratio < .64 and (best is None or ratio < best[0]):
                best = (ratio, mask)
    if best:
        return split_envelopes(points[best[1]], depth+1)+split_envelopes(points[~best[1]], depth+1)
    return [box]


def shape(box, vertices, offset, span):
    center, size, basis = box['center'].copy(), box['size'].copy(), box['basis'].copy()
    kind = 'BOX'
    local = (vertices-center) @ basis
    # Recognize simple round envelopes without pretending to identify wheels/joints.
    for axis in range(3):
        other = [i for i in range(3) if i != axis]
        if min(size[other]) / max(size[other]) < .82:
            continue
        radial = local[:,other] / np.maximum(size[other]/2, span*1e-7)
        r = np.linalg.norm(radial, axis=1)
        angles = np.arctan2(radial[:,1], radial[:,0])
        bins = len(np.unique(np.floor((angles+math.pi)/math.pi*8).astype(int)))
        if bins >= 10 and np.mean(np.abs(r-1) < .07) > .78:
            basis = basis[:,other+[axis]]
            if np.linalg.det(basis) < 0:
                basis[:,0] *= -1
            size = size[other+[axis]]
            kind = 'CYLINDER'
            break
    rotation = Matrix(basis.tolist()).to_euler('XYZ')
    return {'shape': kind, 'position': (center-offset).tolist(),
            'size': np.maximum(size, span/1295).tolist(),
            'rotation': [math.degrees(v) for v in rotation],
            '_volume': box['volume']}


def surface_samples(tri):
    """Area-weighted deterministic samples remove tessellation-density bias."""
    if not len(tri):
        return np.empty((0,3))
    area = np.linalg.norm(np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0]), axis=1)/2
    total = area.sum()
    if not total:
        return np.empty((0,3))
    n=2000
    indices=np.arange(n,dtype=float)+.5
    chosen=np.searchsorted(np.cumsum(area),(indices/n)*total)
    t=tri[np.minimum(chosen,len(tri)-1)]
    u=np.sqrt((indices*.7548776662466927)%1)
    v=(indices*.5698402909980532)%1
    return (1-u[:,None])*t[:,0]+(u*(1-v))[:,None]*t[:,1]+(u*v)[:,None]*t[:,2]


def capture(context, settings):
    start = time.monotonic()
    objects = sources(context)
    rotation = Euler(settings.quick_rotation, 'XYZ').to_matrix().to_4x4()
    unit = context.scene.unit_settings.scale_length if settings.quick_units == 'SCENE' else settings.quick_scale
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('Set a positive unit scale.')
    depsgraph = context.evaluated_depsgraph_get()
    groups = []; all_lo = []; all_hi = []; count = 0; tiny = 0
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            if mesh is None or not len(mesh.vertices):
                continue
            count += len(mesh.vertices)
            if count > MAX_VERTICES:
                raise ValueError('Selection exceeds 5 million evaluated vertices. Hide/exclude internal assemblies or capture a smaller selection.')
            xyz = np.empty(len(mesh.vertices)*3, dtype=np.float64)
            mesh.vertices.foreach_get('co', xyz)
            transform = np.array(rotation.inverted() @ evaluated.matrix_world)
            points = (xyz.reshape(-1,3) @ transform[:3,:3].T + transform[:3,3])*unit
            if not np.isfinite(points).all():
                raise ValueError('Source contains non-finite coordinates.')
            all_lo.append(points.min(0)); all_hi.append(points.max(0))
            connected = islands(mesh)
            mesh.calc_loop_triangles()
            tri_ids=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32)
            mesh.loop_triangles.foreach_get('vertices',tri_ids)
            tri_ids=tri_ids.reshape(-1,3)
            labels=np.empty(len(points),dtype=np.int32)
            for number,group in enumerate(connected): labels[group]=number
            tri_labels=labels[tri_ids[:,0]]
            order=np.argsort(tri_labels,kind='stable')
            starts=np.searchsorted(tri_labels[order],np.arange(len(connected)+1))
            for number,group in enumerate(connected):
                if len(group) < 4:
                    tiny += 1; continue
                original = points[group]
                triangles=points[tri_ids[order[starts[number]:starts[number+1]]]]
                groups.append((original,triangles))
        finally:
            evaluated.to_mesh_clear()
    if not all_lo:
        raise ValueError('Selection has no evaluated geometry.')
    lo, hi = np.min(all_lo,0), np.max(all_hi,0)
    dimensions = hi-lo; span = max(dimensions)
    if min(dimensions) < 1e-6 or max(dimensions) > 10000:
        raise ValueError('Selection is flat or has unsupported dimensions. Check units and selection.')
    offset = np.array(((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, lo[2]))
    shapes = []
    for original, triangles in groups:
        extent = original.max(0)-original.min(0)
        if max(extent) < span*.022:
            tiny += 1; continue
        extra=surface_samples(triangles)
        vertices=original if len(original)<=512 else original[np.linspace(0,len(original)-1,512,dtype=int)]
        sample=np.concatenate((vertices,extra,original[np.concatenate((original.argmin(0),original.argmax(0)))]))
        # Without area samples do not split a low-vertex closed primitive into flat faces.
        boxes = split_envelopes(sample) if len(sample) >= 30 else [envelope(original)]
        for box in boxes:
            if max(box['size']) < span*.022:
                tiny += 1; continue
            shapes.append(shape(box, original, offset, span))
    # Geometry, not names or CAD tessellation density, determines priority.
    shapes.sort(key=lambda p: (-p['_volume'], tuple(round(v,8) for v in p['position']), tuple(p['size'])))
    # Remove duplicate tessellation shells; keep genuinely separate thin panels.
    unique = []; seen = set()
    for p in shapes:
        key = tuple(round(v/(span*.0015)) for v in p['position']+p['size'])
        if key not in seen:
            unique.append(p); seen.add(key)
    text, kept = codec.pack(settings.quick_type, settings.quick_features, dimensions, unique)
    return {'text': text, 'dimensions': dimensions.tolist(), 'objects': len(objects), 'vertices': count,
            'candidates': len(unique), 'kept': kept, 'small': tiny,
            'seconds': round(time.monotonic()-start,2), 'unit': unit,
            'origin': list(rotation @ Vector(offset/unit)), 'rotation': list(settings.quick_rotation)}


def preview(context, settings, result):
    doc = codec.recipe(result['text'])
    col = model.create_collection(doc)
    root = bpy.data.objects.new('Quick Capture / shape guide', None)
    context.scene.collection.objects.link(root)
    root.instance_type = 'COLLECTION'; root.instance_collection = col
    offset = (result['dimensions'][0]*1.3+.15,0,0)
    root.matrix_world = (Matrix.Translation(result['origin']) @ Euler(result['rotation'],'XYZ').to_matrix().to_4x4()
                         @ Matrix.Scale(1/result['unit'],4) @ Matrix.Translation(offset))
    root['fab_author_generated'] = True; root['fab_quick_preview'] = True
    root['fab_quick_text'] = result['text']; root.empty_display_size = max(result['dimensions'])*.06/result['unit']
    # Original selection remains selected, so Capture Again uses the same model.
    settings.quick_preview = root
    return root
