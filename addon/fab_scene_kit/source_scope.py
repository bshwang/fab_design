"""Explicit source snapshots and evaluated measurements; never edits source models."""
import hashlib
import json
import math
import uuid
import bpy
import numpy as np
from mathutils import Euler

GEOMETRY = {'MESH', 'CURVE', 'SURFACE', 'FONT'}
MAX_OBJECTS = 20000
MAX_VERTICES = 5_000_000


def walk(objects, children=True):
    found = {}
    stack = list(objects)
    while stack:
        obj = stack.pop()
        if obj.as_pointer() in found:
            continue
        if len(found) >= MAX_OBJECTS:
            raise ValueError('More than 20,000 source objects. Use a smaller selection.')
        found[obj.as_pointer()] = obj
        if children:
            stack.extend(obj.children)
    return sorted(found.values(), key=lambda o: o.name)


def instance(obj):
    return obj.instance_type == 'COLLECTION' and bool(obj.instance_collection)


def helper(obj):
    name = obj.name.casefold()
    return obj.type in GEOMETRY and (any(x in name for x in ('workspace', 'work_space', 'workarea', 'envelope', 'reach_area')) or obj.display_type in {'BOUNDS', 'WIRE'})


def alive(row, scene):
    return row.object is not None and row.object.name in scene.objects


def add(settings, objects, children=True):
    objects = walk(objects, children)
    if not objects:
        raise ValueError('Select source objects in Object Mode, or choose a Collection.')
    if any(o.get('fab_author_generated') or o.get('fab_author_guide') or o.get('fab_brief_guide') for o in objects):
        raise ValueError('Select original source objects, not generated guides/assets.')
    existing = {r.object.as_pointer() for r in settings.sources if r.object}
    if len(settings.sources) + sum(o.as_pointer() not in existing for o in objects) > MAX_OBJECTS:
        raise ValueError('Source snapshot exceeds 20,000 objects.')
    count = 0
    for obj in objects:
        if obj.as_pointer() in existing:
            continue
        row = settings.sources.add()
        row.object = obj
        row.name = obj.name
        row.key = uuid.uuid4().hex[:12]
        row.decision = 'REVIEW' if helper(obj) or instance(obj) else 'KEEP'
        row.reason = ('Collection instance: measurement unavailable; exclude and describe it.' if instance(obj)
                      else 'Possible helper: review its physical meaning.' if helper(obj)
                      else 'Reference only' if obj.type not in GEOMETRY else '')
        count += 1
    settings.confirmed = False
    settings.measurement_dirty = True
    return count


def included(settings, scene):
    return [r for r in settings.sources if alive(r, scene) and r.decision == 'KEEP' and r.object.type in GEOMETRY and not instance(r.object)]


def signature(settings, scene):
    # Pointer identity survives renames during this session; stored keys survive .blend saves.
    data = [(r.key, r.object.name if alive(r, scene) else None, r.object.type if r.object else None, r.decision)
            for r in settings.sources]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()


def issues(settings, scene):
    errors = []
    if not settings.sources:
        errors.append('Add the source model first.')
    missing = sum(not alive(r, scene) and r.decision != 'EXCLUDE' for r in settings.sources)
    if missing:
        errors.append(f'{missing} source objects are missing; exclude or replace them.')
    review = sum(r.decision == 'REVIEW' for r in settings.sources)
    if review:
        errors.append(f'Review {review} possible helper/instance objects: Keep or Exclude.')
    if any(r.decision == 'KEEP' and r.object and instance(r.object) for r in settings.sources):
        errors.append('Collection instance measurement is unavailable. Exclude it and use Describe Only.')
    return errors


def confirm(settings, scene):
    errors = issues(settings, scene)
    if errors:
        raise ValueError(errors[0])
    settings.scope_signature = signature(settings, scene)
    settings.confirmed = True


def confirmed(settings, scene):
    return settings.confirmed and settings.scope_signature == signature(settings, scene) and not issues(settings, scene)


def set_decision(settings, objects, decision, children=True):
    selected = {o.as_pointer() for o in walk(objects, children)}
    found = 0
    for row in settings.sources:
        if row.object and row.object.as_pointer() in selected:
            row.decision = decision
            found += 1
    if not found:
        raise ValueError('The selection is outside the source snapshot. Add Selection first.')
    settings.confirmed = False
    settings.measurement_dirty = True
    return found


def assign(settings, scene, part, objects, children=False, append=False):
    if not confirmed(settings, scene):
        raise ValueError('Confirm Scope before assigning components.')
    selected = {o.as_pointer() for o in walk(objects, children)}
    rows = [r for r in included(settings, scene) if r.object.as_pointer() in selected]
    if not rows:
        raise ValueError('No included geometry in this selection. Use Include Children for a parent, or Describe Only.')
    keys = {r.key for r in rows}
    for other in settings.parts:
        if other != part and other.enabled and keys.intersection(b.source_key for b in other.bindings):
            raise ValueError(f'Selection overlaps {other.name}. Use a smaller selection or remove that binding first.')
    if not append:
        part.bindings.clear()
    existing = {b.source_key for b in part.bindings}
    for row in rows:
        if row.key not in existing:
            part.bindings.add().source_key = row.key
    settings.measurement_dirty = True
    return len(rows)


def orientation(settings):
    if settings.front == 'CUSTOM':
        return Euler(settings.rotation, 'XYZ').to_matrix()
    return Euler((0, 0, {'NEG_Y': 0, 'POS_Y': math.pi, 'POS_X': math.pi/2, 'NEG_X': -math.pi/2}[settings.front]), 'XYZ').to_matrix()


def scale(settings, scene):
    return scene.unit_settings.scale_length if settings.units == 'SCENE' else settings.meters_per_unit


def evaluate(context, settings):
    """Hash actual current-pose evaluated vertices as well as their frame-space bounds."""
    rows = included(settings, context.scene)
    if not rows:
        raise ValueError('No included geometry to measure. Keep Describe Only or review Scope.')
    unit = scale(settings, context.scene)
    basis = np.asarray(orientation(settings).transposed(), dtype=np.float64)
    digest = hashlib.sha256(json.dumps([unit, basis.tolist(), context.scene.frame_current]).encode())
    depsgraph = context.evaluated_depsgraph_get()
    bounds = {}
    total = 0
    for row in sorted(rows, key=lambda r: r.key):
        obj = row.object.evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        try:
            if mesh is None or not len(mesh.vertices):
                raise ValueError(f'{row.object.name}: no measurable vertices. Exclude it or describe it.')
            total += len(mesh.vertices)
            if total > MAX_VERTICES:
                raise ValueError('More than 5 million evaluated vertices. Use a smaller physical scope or export without measurements.')
            vertices = np.empty(len(mesh.vertices)*3, dtype=np.float64)
            mesh.vertices.foreach_get('co', vertices)
            vertices = vertices.reshape(-1, 3)
            matrix = np.asarray(obj.matrix_world, dtype=np.float64)
            points = ((vertices @ matrix[:3, :3].T + matrix[:3, 3]) @ basis.T) * unit
            if not np.isfinite(points).all():
                raise ValueError('Source contains non-finite coordinates.')
            digest.update(row.key.encode()); digest.update(points.tobytes())
            bounds[row.key] = (points.min(axis=0), points.max(axis=0))
        finally:
            obj.to_mesh_clear()
    lo = np.min([v[0] for v in bounds.values()], axis=0)
    hi = np.max([v[1] for v in bounds.values()], axis=0)
    if np.max(hi-lo) <= 1e-9:
        raise ValueError('Included geometry has no measurable extent.')
    origin = np.array([(lo[0]+hi[0])/2, (lo[1]+hi[1])/2, lo[2]])
    parts = {}
    for part in settings.parts:
        if not part.enabled or not part.bindings:
            continue
        keys = [b.source_key for b in part.bindings]
        if any(k not in bounds for k in keys):
            raise ValueError(f'{part.name}: assigned sources are now excluded or missing. Reassign or use Describe Only.')
        a = np.min([bounds[k][0] for k in keys], axis=0)
        b = np.max([bounds[k][1] for k in keys], axis=0)
        parts[part.key] = {'size': (b-a).tolist(), 'center': ((a+b)/2-origin).tolist()}
    digest.update(json.dumps({p.key: sorted(b.source_key for b in p.bindings) for p in settings.parts if p.enabled}, sort_keys=True).encode())
    return {'size': (hi-lo).tolist(), 'origin_frame_m': origin.tolist(), 'parts': parts,
            'stamp': digest.hexdigest(), 'vertices': total, 'unit': unit,
            'rotation': list(orientation(settings).to_euler()), 'frame': context.scene.frame_current}


def hierarchy(settings, scene, max_depth=2):
    rows = {r.object.as_pointer(): r for r in settings.sources if alive(r, scene)}
    roots = [r for r in rows.values() if not r.object.parent or r.object.parent.as_pointer() not in rows]
    lines = []
    stack = [(r, 0) for r in reversed(sorted(roots, key=lambda r: r.object.name))]
    while stack:
        row, depth = stack.pop()
        children = [rows[o.as_pointer()] for o in row.object.children if o.as_pointer() in rows]
        suffix = f' (+{len(children)} children)' if children else ''
        name = row.object.name.replace('\n', ' ').replace('\r', ' ')
        lines.append(f'{"  "*depth}{name} [{row.object.type}/{row.decision}]{suffix}')
        if max_depth == 0 or depth < max_depth:
            stack.extend((r, depth+1) for r in reversed(sorted(children, key=lambda r: r.object.name)))
    return '\n'.join(lines)
