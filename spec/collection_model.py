"""Small executable review model. No device collection, database or production executor."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import re


def compare_inventory(expected, rows, complete_snapshot=False):
    """Quantity is an identity-set comparison; validity is independent of row count."""
    expected = set(expected)
    counts = Counter(r['id'] for r in rows)
    received = set(counts)
    valid = {r['id'] for r in rows if r.get('quality') == 'known' and r.get('fresh') is True and r.get('identity_verified') is True}
    duplicate = {k for k, n in counts.items() if n > 1}
    valid -= duplicate
    missing, unexpected = expected - received, received - expected
    matched = expected & valid
    if not expected or duplicate or received - valid or (missing and not complete_snapshot):
        result = 'BLOCKED'
    elif missing or unexpected:
        result = 'FAIL'
    else:
        result = 'PASS'
    return dict(received=len(rows), unique=len(received), valid=len(valid), matched=len(matched),
                expected=len(expected), missing=sorted(missing), unexpected=sorted(unexpected),
                duplicate=sorted(duplicate), verdict=result)


def compare_wiring(expected, host, switch):
    if not expected or not host or not switch:
        return 'BLOCKED'
    # Endpoints are stable IDs; orientation of a physical cable is irrelevant.
    pair = lambda x: frozenset(x) if len(x) == 2 and len(set(x)) == 2 else None
    if not all(pair(p) for p in (expected, host, switch)):
        return 'BLOCKED'
    return 'PASS' if pair(expected) == pair(host) == pair(switch) else 'FAIL'


EVENT_KEYS = {'schema_version', 'event_id', 'project_id', 'subject_refs', 'source_kind', 'source_ref',
              'source_sequence', 'source_hash', 'source_quality', 'collected_at', 'received_at'}
KINDS = {'project', 'machine', 'component', 'physical_port', 'cable', 'fabric', 'rack', 'execution', 'group_run', 'issue'}
QUALITIES = {'known', 'unknown', 'degraded', 'approximation', 'estimated'}


def identifier(value):
    return isinstance(value, str) and bool(value.strip()) and value != 'latest'


def envelope_valid(event, allowed_sources):
    """Only this finite envelope is checked, not a general JSON Schema engine."""
    if set(event) != EVENT_KEYS or event.get('schema_version') != '1':
        return False
    if not all(identifier(event[k]) for k in ['event_id', 'project_id']):
        return False
    if event['source_kind'] not in allowed_sources or event['source_quality'] not in QUALITIES:
        return False
    if type(event['source_sequence']) is not int or event['source_sequence'] < 1:
        return False
    if not isinstance(event['source_hash'], str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', event['source_hash']):
        return False
    ref = event['source_ref']
    if not isinstance(ref, dict) or set(ref) != {'record_id', 'revision'} or not all(identifier(x) for x in ref.values()):
        return False
    subjects = event['subject_refs']
    if not isinstance(subjects, list) or not subjects:
        return False
    if any(not isinstance(s, dict) or set(s) != {'kind', 'id'} or s['kind'] not in KINDS or not identifier(s['id']) for s in subjects):
        return False
    if len({(s['kind'], s['id']) for s in subjects}) != len(subjects):
        return False
    try:
        for key in ['collected_at', 'received_at']:
            value = event[key]
            if not isinstance(value, str) or not value.endswith('Z') or 'T' not in value:
                return False
            datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return False
    return True


class CMDBReview:
    """Federated pointers only, with immutable-source and current-quality checks."""
    def __init__(self, project, objects, allowed_sources, source_records):
        self.project, self.objects, self.allowed_sources = project, set(objects), set(allowed_sources)
        self.source_records = source_records
        self.events, self.history, self.current, self.last_known = {}, {}, {}, {}
        self.receipts = []

    def ingest(self, event):
        def finish(status):
            self.receipts.append(status)
            return status
        if not envelope_valid(event, self.allowed_sources):
            return finish('quarantined')
        if event['project_id'] != self.project or any((s['kind'], s['id']) not in self.objects for s in event['subject_refs']):
            return finish('quarantined')
        # Reception time is delivery metadata. A redelivery can have a new time;
        # every immutable source property still has to match.
        content = {k: v for k, v in event.items() if k not in {'received_at', 'event_id'}}
        prior = self.events.get(event['event_id'])
        if prior is not None and prior != content:
            return finish('quarantined')
        ref = event['source_ref']
        chain = (event['project_id'], event['source_kind'], ref['record_id'])
        key = chain + (ref['revision'],)
        old = self.history.get(key)
        if old is not None:
            if old != content:
                return finish('quarantined')
            self.events[event['event_id']] = deepcopy(content)
            return finish('duplicate')
        if any(k[:3] == chain and v['source_sequence'] == event['source_sequence'] for k, v in self.history.items()):
            return finish('quarantined')
        # The fixture source table is independent of an arriving event. A
        # syntactically valid reference or digest does not establish existence.
        authoritative = self.source_records.get(key)
        if authoritative is None or content != authoritative:
            return finish('quarantined')
        self.history[key] = deepcopy(content)
        self.events[event['event_id']] = deepcopy(content)
        current = self.current.get(chain)
        if current is None or event['source_sequence'] > current['source_sequence']:
            self.current[chain] = deepcopy(content)  # Unknown must supersede old green.
        known = self.last_known.get(chain)
        if event['source_quality'] == 'known' and (known is None or event['source_sequence'] > known['source_sequence']):
            self.last_known[chain] = deepcopy(content)
        return finish('indexed')

    def totals(self):
        return dict(received=len(self.receipts), indexed=self.receipts.count('indexed'),
                    duplicate=self.receipts.count('duplicate'), quarantined=self.receipts.count('quarantined'))
