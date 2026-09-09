"""Versioned text interchange. Pure Python; never evaluates imported text."""
import copy
import json
import math
import re
import uuid

SCHEMA = 'fab.asset-brief'
SCHEMA_VERSION = 1
MAX_BYTES = 2_000_000
MAX_PARTS = 256
MAX_POINTS = 256
TYPES = {
    'EQUIPMENT': ('Equipment', 'Housing, chambers, load ports and operator controls.', ['HOUSING']),
    'AMR': ('AMR', 'Base, wheels, sensors and payload deck.', ['BASE', 'WHEEL']),
    'AMMR': ('AMMR', 'Mobile base, arm links, joints and end effector.', ['BASE', 'LINK', 'JOINT', 'TOOL']),
    'ARM': ('Robot Arm / Cobot', 'Base, links, joint centers and end effector.', ['BASE', 'LINK', 'JOINT', 'TOOL']),
    'HUMANOID': ('Humanoid', 'Torso, head, pelvis, limbs, hands and feet.', ['TORSO', 'HEAD', 'LINK']),
    'OHT': ('OHT', 'Vehicle body, hoist, gripper and rail interface.', ['BODY', 'TOOL']),
}
ROLES = {
    'BASE': ('Base', 'BOX', 'navy'), 'HOUSING': ('Housing', 'BOX', 'ice'),
    'BODY': ('Body', 'BOX', 'ice'), 'CHAMBER': ('Chamber', 'CYLINDER', 'steel'),
    'WHEEL': ('Wheel', 'CYLINDER', 'navy'), 'LINK': ('Link', 'TAPER', 'ice'),
    'JOINT': ('Joint', 'CYLINDER', 'joint'), 'TOOL': ('Tool / Gripper', 'BOX', 'steel'),
    'SENSOR': ('Sensor', 'CYLINDER', 'navy'), 'DISPLAY': ('Display', 'BOX', 'display'),
    'PORT': ('Load Port', 'BOX', 'navy'), 'PANEL': ('Panel', 'BOX', 'mint'),
    'VENT': ('Vent', 'BOX', 'navy'), 'PIPE': ('Pipe / Cable', 'PATH', 'blue'),
    'TORSO': ('Torso', 'TAPER', 'ice'), 'HEAD': ('Head', 'ELLIPSOID', 'ice'),
    'PELVIS': ('Pelvis', 'BOX', 'navy'), 'HAND': ('Hand', 'BOX', 'steel'),
    'FOOT': ('Foot', 'BOX', 'navy'), 'OTHER': ('Other', 'BOX', 'ice'),
}
SHAPES = ['BOX', 'CYLINDER', 'ELLIPSOID', 'TAPER', 'PROFILE', 'PATH']
MATERIALS = ['navy', 'mint', 'ice', 'ivory', 'gold', 'blue', 'white', 'steel', 'joint', 'display', 'red']


def new_document(kind='AMMR', name='My Asset'):
    if kind not in TYPES:
        raise ValueError('Unknown asset type')
    return {'schema': SCHEMA, 'schema_version': SCHEMA_VERSION, 'id': 'asset_' + uuid.uuid4().hex[:12],
            'name': name, 'type': kind, 'units': 'm',
            'coordinates': {'up': '+Z', 'front': '-Y', 'rotations': 'XYZ degrees', 'part_transforms': 'asset_absolute'},
            'style': {'profile': 'fab_scene_kit', 'theme': 'LIGHT'},
            'features': '', 'omit': 'Small fasteners and hidden internals', 'parts': []}


def new_part(role='BODY', name=None):
    label, shape, material = ROLES[role]
    return {'id': 'part_' + uuid.uuid4().hex[:10], 'name': name or label, 'role': role,
            'parent': '', 'enabled': True, 'configured': False, 'source': 'manual',
            'shape': shape, 'position': [0., 0., .5], 'rotation': [0., 0., 0.], 'size': [1., 1., 1.],
            'material': material, 'bevel': .025, 'taper': .8, 'radius': .025, 'points': [],
            'joint': {'enabled': False, 'center': [0., 0., 0.], 'axis': [0., 0., 1.]}, 'notes': ''}


def _keys(value, expected, label):
    if not isinstance(value, dict):
        raise ValueError(label + ' must be an object')
    extra = set(value) - set(expected)
    missing = set(expected) - set(value)
    if extra or missing:
        raise ValueError(f'{label}: unexpected {sorted(extra)} / missing {sorted(missing)} fields')


def _text(value, label, limit=2000):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError(label + ' must be bounded text')


def _number(value, label, lower=-1e6, upper=1e6):
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(label + ' must be a finite number in range')


def _vector(value, label, count=3, lower=-1e6, upper=1e6):
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(label + f' must contain {count} numbers')
    for item in value:
        _number(item, label, lower, upper)


def _enum(value, choices, label):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(label + ' has an unsupported value')


def validate(document):
    """Strict syntax/data validation; incomplete drafts are allowed, build checks are separate."""
    _keys(document, new_document(), 'Document')
    if document['schema'] != SCHEMA or type(document['schema_version']) is not int or document['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Unsupported brief schema/version')
    for key in ('id', 'name', 'features', 'omit'):
        _text(document[key], key)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,79}', document['id']):
        raise ValueError('Asset ID must use letters, digits, underscore, dot or hyphen')
    if not document['name'].strip():
        raise ValueError('Asset name is empty')
    _enum(document['type'], TYPES, 'Type')
    if document['units'] != 'm' or document['coordinates'] != new_document()['coordinates']:
        raise ValueError('Expected meters, +Z up, -Y front, absolute asset transforms and XYZ degrees')
    _keys(document['style'], ('profile', 'theme'), 'Style')
    if document['style']['profile'] != 'fab_scene_kit':
        raise ValueError('Unsupported style profile')
    _enum(document['style']['theme'], ('LIGHT', 'DARK'), 'Theme')
    parts = document['parts']
    if not isinstance(parts, list) or len(parts) > MAX_PARTS:
        raise ValueError(f'At most {MAX_PARTS} components are supported')
    ids = set()
    for part in parts:
        _keys(part, new_part(), 'Component')
        for key in ('id', 'name', 'parent', 'notes'):
            _text(part[key], 'Component ' + key)
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,79}', part['id']) or part['id'] in ids:
            raise ValueError('Component IDs must be unique identifiers')
        ids.add(part['id'])
        if not part['name'].strip():
            raise ValueError('Component name is empty')
        for key in ('enabled', 'configured'):
            if type(part[key]) is not bool:
                raise ValueError(key + ' must be boolean')
        _enum(part['role'], ROLES, 'Component role')
        _enum(part['shape'], SHAPES, 'Shape')
        _enum(part['material'], MATERIALS, 'Material')
        _enum(part['source'], ('manual', 'selection', 'profile', 'path'), 'Source')
        for key in ('position', 'rotation'):
            _vector(part[key], key)
        _vector(part['size'], 'Size', lower=.000001, upper=10000)
        _number(part['bevel'], 'Bevel fraction', 0, .2)
        _number(part['taper'], 'Taper', .05, 2)
        _number(part['radius'], 'Path radius', .000001, 100)
        if not isinstance(part['points'], list) or len(part['points']) > MAX_POINTS:
            raise ValueError('Too many profile/path points')
        for point in part['points']:
            _vector(point, 'Point')
        joint = part['joint']
        _keys(joint, ('enabled', 'center', 'axis'), 'Joint')
        if type(joint['enabled']) is not bool:
            raise ValueError('Joint enabled must be boolean')
        _vector(joint['center'], 'Joint center')
        _vector(joint['axis'], 'Joint axis', lower=-1, upper=1)
        if joint['enabled'] and abs(sum(v*v for v in joint['axis']) - 1) > 1e-4:
            raise ValueError('Joint axis must have unit length')
    lookup = {p['id']: p for p in parts}
    for part in parts:
        seen = {part['id']}
        parent = part['parent']
        while parent:
            if parent not in lookup or parent in seen:
                raise ValueError('Missing parent or cyclic component hierarchy')
            seen.add(parent)
            parent = lookup[parent]['parent']
    return copy.deepcopy(document)


def _profile_ok(points):
    if len(points) < 3 or max(abs(p[2]) for p in points) > 1e-5:
        return False
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]+points[:1]))
    if abs(area) < 1e-10:
        return False
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for i,a in enumerate(points):
        b=points[(i+1)%len(points)]
        if sum((a[k]-b[k])**2 for k in range(2)) < 1e-12:
            return False
        for j in range(i+1,len(points)):
            if j in {i,(i+1)%len(points)} or (j+1)%len(points)==i:
                continue
            c,d=points[j],points[(j+1)%len(points)]
            if cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0:
                # Bounding boxes also overlap; handles collinear segment extensions.
                if all(max(min(a[k],b[k]),min(c[k],d[k]))<=min(max(a[k],b[k]),max(c[k],d[k])) for k in (0,1)):
                    return False
    return True


def issues(document):
    validate(document)
    errors, warnings = [], []
    visible = [p for p in document['parts'] if p['enabled']]
    if not visible:
        errors.append('Add at least one included component.')
    for part in visible:
        if not part['configured']:
            errors.append(part['name'] + ': measure selection or confirm entered values.')
        if part['shape']=='PROFILE' and not _profile_ok(part['points']):
            errors.append(part['name'] + ': capture a simple closed planar outline (local XY).')
        if part['shape']=='PATH' and (len(part['points'])<2 or any(sum((a[k]-b[k])**2 for k in range(3))<1e-12 for a,b in zip(part['points'],part['points'][1:]))):
            errors.append(part['name'] + ': capture a connected path with distinct points.')
    for role in TYPES[document['type']][2]:
        if not any(p['role']==role for p in visible):
            warnings.append('Suggested component missing: ' + ROLES[role][0])
    if not document['features'].strip():
        warnings.append('Describe the features that make this asset recognizable.')
    return errors, warnings


def dumps(document):
    return json.dumps(validate(document), ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def loads(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Brief exceeds the 2 MB text limit')
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key]=value
        return result
    try:
        return validate(json.loads(text.lstrip('\ufeff'), object_pairs_hook=pairs,
                                   parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON value'))))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON brief: ' + str(exc)[:160]) from None


def summary(document):
    doc=validate(document)
    errors,warnings=issues(doc)
    lines=[f"{doc['name']} | {TYPES[doc['type']][0]}", f"ID: {doc['id']}",
           'Meters | +Z up | -Y front | XYZ degrees | component transforms are absolute in asset space.',
           'Parent IDs describe assembly relationships; do not multiply transforms again.',
           'Style: FAB Scene Kit; restrained palette, matte materials and soft bevels.',
           'Features: '+doc['features'], 'Omit: '+doc['omit'], '', 'Components:']
    for p in doc['parts']:
        lines.append(f"- {p['id']} | {p['name']} | {p['role']} | {p['shape']} | {'included' if p['enabled'] else 'omitted'}")
        lines.append(f"  size={p['size']} position={p['position']} rotation={p['rotation']} material={p['material']}")
        if p['notes']:
            lines.append('  '+p['notes'])
    lines += ['', 'Review:'] + errors + warnings
    if not errors and not warnings:
        lines.append('Ready.')
    return '\n'.join(lines)+'\n'
