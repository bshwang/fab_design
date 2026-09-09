"""FQ1: bounded, lossy geometric notes. Standard library only; no mesh payload."""
import hashlib
import json
import math
from . import author_spec as spec

LIMIT = 1000
DIGITS = '0123456789abcdefghijklmnopqrstuvwxyz'
RECORD = 19


def count(text):
    # Conservative for applications that count UTF-16 code units (including emoji).
    return len(text.encode('utf-16-le')) // 2


def _pair(value):
    value = int(value)
    if not 0 <= value <= 1295:
        raise ValueError('Shape lies outside the FQ1 coordinate range.')
    return DIGITS[value // 36] + DIGITS[value % 36]


def encode_shape(shape, dimensions):
    span = max(dimensions)
    center = [shape['position'][i] + (dimensions[i]/2 if i < 2 else 0) for i in range(3)]
    values = [round((v / span + .5) * 1295 / 2) for v in center]
    values += [max(1, round(v / span * 1295 / 2)) for v in shape['size']]
    values += [round(v % 360 * 2) % 720 for v in shape['rotation']]
    return ('C' if shape['shape'] == 'CYLINDER' else 'B') + ''.join(_pair(v) for v in values)


def pack(kind, features, dimensions, shapes):
    if kind not in spec.TYPES:
        raise ValueError('Choose an asset type.')
    if not features.strip():
        raise ValueError('Add a short description of the recognizable features.')
    if count(features) > 240:
        raise ValueError('Keep features within 240 characters to leave room for geometry.')
    packet = {'v': 'FQ1', 't': kind, 'f': features.strip(),
              'd': [float(format(v, '.6g')) for v in dimensions], 'g': ''}
    serialize = lambda: json.dumps(packet, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    kept = 0
    for shape in shapes:
        record = encode_shape(shape, packet['d'])
        packet['g'] += record
        if count(serialize()) > LIMIT:
            packet['g'] = packet['g'][:-RECORD]
            break
        kept += 1
    if not kept:
        raise ValueError('No measurable shapes fit in the text budget.')
    text = serialize()
    unpack(text)
    return text, kept


def unpack(text):
    if not isinstance(text, str) or count(text) > LIMIT:
        raise ValueError('Quick Capture text must be at most 1000 characters.')
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('Duplicate Quick Capture key: ' + k)
            result[k] = v
        return result
    try:
        p = json.loads(text, object_pairs_hook=unique)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError('Invalid Quick Capture JSON: ' + str(exc)) from None
    if not isinstance(p, dict) or set(p) != {'v', 't', 'f', 'd', 'g'} or p['v'] != 'FQ1':
        raise ValueError('Expected an FQ1 Quick Capture packet.')
    if not isinstance(p['t'], str) or p['t'] not in spec.TYPES:
        raise ValueError('Unknown Quick Capture type.')
    if not isinstance(p['f'], str) or not p['f'].strip() or count(p['f']) > 240 or '\x00' in p['f']:
        raise ValueError('Invalid feature description.')
    d = p['d']
    if not isinstance(d, list) or len(d) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) or not 1e-6 <= x <= 10000 for x in d):
        raise ValueError('Invalid dimensions in meters.')
    g = p['g']
    if not isinstance(g, str) or not g or len(g) % RECORD:
        raise ValueError('Incomplete Quick Capture shape record.')
    shapes = []
    for start in range(0, len(g), RECORD):
        record = g[start:start+RECORD]
        if record[0] not in 'BC' or any(c not in DIGITS for c in record[1:]):
            raise ValueError('Unknown Quick Capture shape code.')
        values = [int(record[i:i+2], 36) for i in range(1, RECORD, 2)]
        if any(v == 0 for v in values[3:6]) or any(v >= 720 for v in values[6:]):
            raise ValueError('Invalid Quick Capture size or rotation.')
        span = max(d)
        shapes.append({'shape': 'CYLINDER' if record[0] == 'C' else 'BOX',
                       'position': [(values[i]*2/1295-.5)*span - (d[i]/2 if i < 2 else 0) for i in range(3)],
                       'size': [v*2/1295*span for v in values[3:6]],
                       'rotation': [v/2 for v in values[6:]]})
    return p, shapes


def recipe(text):
    packet, shapes = unpack(text)
    doc = spec.new_document(packet['t'], 'Quick ' + spec.TYPES[packet['t']][0])
    doc['id'] = 'asset_quick_' + hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
    doc['features'] = packet['f']
    doc['omit'] = 'Lossy shape guide, not a finished asset. Infer semantic parts from features; verify uncertain details.'
    for i, shape in enumerate(shapes):
        p = spec.new_part('OTHER', 'Shape %02d' % (i+1))
        p.update(shape, id='shape_%02d' % (i+1), configured=True, source='manual',
                 material='blue', bevel=.018,
                 notes='Measured geometric approximation; no semantic role or joint inferred.')
        doc['parts'].append(p)
    return spec.validate(doc)
