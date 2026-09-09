"""AW1 semantic briefs. Standard library, no geometry or executable payload."""
import json
import math

LIMIT = 1000


def count(text):
    return len(text.encode('utf-16-le')) // 2


def number(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Non-finite measurement.')
    return float(format(value, '.5g'))


def vector(values):
    return [number(v) for v in values]


def packet(header, parts, measurement=None, hierarchy=None):
    result = {'v': 'AW1', 'type': header['type'], 'use': header['purpose'].strip(),
              'base': header['outline'], 'size': None}
    if header.get('opening') and header['outline'] in {'L', 'U', 'OTHER'}:
        result['open'] = header['opening']
    if header.get('arms') is not None:
        result['arms'] = header['arms']
    for source, target in [('features', 'keep'), ('sequence', 'flow'), ('relationship', 'move')]:
        if header.get(source):
            result[target] = header[source]
    result['parts'] = []
    for p in parts:
        if not p.get('enabled', True) or p.get('importance') == 'OMIT':
            continue
        item = {'id': p['id'], 'role': p['name']}
        if p.get('importance') == 'KEEP':
            item['keep'] = True
        for source, target in [('notes', 'note'), ('placement', 'at'), ('motion', 'motion'), ('mounted_on', 'on')]:
            value = p.get(source)
            if value and value != 'UNKNOWN':
                item[target] = value
        if measurement and p['id'] in measurement.get('parts', {}):
            measured = measurement['parts'][p['id']]
            item['d'] = vector(measured['size'])
            item['p'] = vector(measured['center'])
        result['parts'].append(item)
    if measurement:
        result['size'] = vector(measurement['size'])
        result['frame'] = 'm;center XY,floor Z;-Y front,+Z up;current pose'
    if hierarchy:
        result['roots'] = hierarchy
    return result


def dumps(data, enforce=False):
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if enforce:
        if data.get('v') != 'AW1' or not data.get('use', '').strip():
            raise ValueError('Enter the equipment purpose.')
        if count(text) > LIMIT:
            raise ValueError(f'{count(text)-LIMIT} characters over 1000. Shorten notes or turn off optional measurements/root names. Nothing was truncated.')
    return text
