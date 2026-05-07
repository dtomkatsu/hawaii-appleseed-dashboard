#!/usr/bin/env python3
"""One-off: backfill vacancy_rate (B25002_003E / B25002_001E) into the 2024 ACS CSVs."""
from __future__ import annotations

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / 'data' / 'processed'
YEAR = 2024
NEEDED = ['B25002_001E', 'B25002_003E']

LEVELS = {
    'state':  {'csv': f'hawaii_state_acs_{YEAR}.csv',            'for': 'state:15',                                       'in': None},
    'county': {'csv': f'hawaii_counties_acs_{YEAR}.csv',         'for': 'county:*',                                       'in': 'state:15'},
    'house':  {'csv': f'hawaii_house_districts_acs_{YEAR}.csv',  'for': 'state legislative district (lower chamber):*',  'in': 'state:15'},
    'senate': {'csv': f'hawaii_senate_districts_acs_{YEAR}.csv', 'for': 'state legislative district (upper chamber):*',  'in': 'state:15'},
}


def fetch(level_cfg: dict) -> list[dict]:
    base = f'https://api.census.gov/data/{YEAR}/acs/acs5'
    params = {'get': 'NAME,' + ','.join(NEEDED), 'for': level_cfg['for']}
    if level_cfg['in']:
        params['in'] = level_cfg['in']
    url = base + '?' + urllib.parse.urlencode(params, safe=':,')
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    return [dict(zip(data[0], r)) for r in data[1:]]


def make_geoid(level: str, row: dict) -> str:
    s = row.get('state', '')
    if level == 'state':
        return s.zfill(2)
    if level == 'county':
        return s.zfill(2) + row.get('county', '').zfill(3)
    if level == 'house':
        return s.zfill(2) + row.get('state legislative district (lower chamber)', '').zfill(3)
    if level == 'senate':
        return s.zfill(2) + row.get('state legislative district (upper chamber)', '').zfill(3)
    return ''


def vac_rate(row: dict) -> float | None:
    try:
        denom = float(row['B25002_001E'])
        if denom <= 0:
            return None
        return round((float(row['B25002_003E']) / denom) * 100, 2)
    except (KeyError, ValueError, TypeError):
        return None


def update_csv(csv_path: Path, by_geoid: dict[str, float]) -> int:
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if 'vacancy_rate' not in fieldnames:
        fieldnames.append('vacancy_rate')
    matched = 0
    for r in rows:
        gid = (r.get('geoid') or '').strip()
        if gid in by_geoid:
            r['vacancy_rate'] = by_geoid[gid]
            matched += 1
        else:
            r.setdefault('vacancy_rate', '')
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return matched


def main() -> int:
    for level, cfg in LEVELS.items():
        csv_path = PROCESSED / cfg['csv']
        if not csv_path.exists():
            print(f'[skip] {csv_path} not found')
            continue
        print(f'[fetch] {level}: ', end='', flush=True)
        rows = fetch(cfg)
        print(f'{len(rows)} rows')
        by_geoid: dict[str, float] = {}
        for r in rows:
            gid = make_geoid(level, r)
            v = vac_rate(r)
            if gid and v is not None:
                by_geoid[gid] = v
        matched = update_csv(csv_path, by_geoid)
        print(f'  -> updated {csv_path.name}: matched {matched} / {len(rows)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
