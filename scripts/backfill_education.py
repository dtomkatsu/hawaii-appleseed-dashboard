#!/usr/bin/env python3
"""One-off: backfill high-school-or-higher attainment into the 2024 ACS CSVs.

The original 2024 fetch only pulled B15003_022E (bachelor's) + B15003_001E
(pop 25+). To support a "High School or Higher" educational-attainment layer
we additionally need B15003_017E … _025E so we can compute the rate as
sum(_017E … _025E) / _001E.

This script hits the public Census ACS5 API (no key required for small
state-15 queries), computes the rate, and merges it into the existing CSVs
in data/processed/.
"""
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
HS_VARS = [f'B15003_{i:03d}E' for i in range(17, 26)]  # 017..025
DENOM = 'B15003_001E'
NEEDED = [DENOM] + HS_VARS

LEVELS = {
    'state':  {'csv': f'hawaii_state_acs_{YEAR}.csv',            'for': 'state:15',                                              'in': None},
    'county': {'csv': f'hawaii_counties_acs_{YEAR}.csv',         'for': 'county:*',                                              'in': 'state:15'},
    'house':  {'csv': f'hawaii_house_districts_acs_{YEAR}.csv',  'for': 'state legislative district (lower chamber):*',         'in': 'state:15'},
    'senate': {'csv': f'hawaii_senate_districts_acs_{YEAR}.csv', 'for': 'state legislative district (upper chamber):*',         'in': 'state:15'},
}


def fetch(level_cfg: dict) -> list[dict]:
    base = f'https://api.census.gov/data/{YEAR}/acs/acs5'
    params = {'get': 'NAME,' + ','.join(NEEDED), 'for': level_cfg['for']}
    if level_cfg['in']:
        params['in'] = level_cfg['in']
    url = base + '?' + urllib.parse.urlencode(params, safe=':,')
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    headers = data[0]
    rows = data[1:]
    return [dict(zip(headers, r)) for r in rows]


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


def hs_rate(row: dict) -> float | None:
    try:
        denom = float(row[DENOM])
        if denom <= 0:
            return None
        num = sum(float(row[v]) for v in HS_VARS)
        return round((num / denom) * 100, 2)
    except (KeyError, ValueError, TypeError):
        return None


def update_csv(csv_path: Path, rate_by_geoid: dict[str, float]) -> int:
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if 'high_school_or_higher_pct' not in fieldnames:
        fieldnames.append('high_school_or_higher_pct')
    matched = 0
    for r in rows:
        gid = (r.get('geoid') or '').strip()
        if gid in rate_by_geoid:
            r['high_school_or_higher_pct'] = rate_by_geoid[gid]
            matched += 1
        else:
            r.setdefault('high_school_or_higher_pct', '')
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
        rate_by_geoid: dict[str, float] = {}
        for r in rows:
            gid = make_geoid(level, r)
            v = hs_rate(r)
            if gid and v is not None:
                rate_by_geoid[gid] = v
        matched = update_csv(csv_path, rate_by_geoid)
        print(f'  -> updated {csv_path.name}: matched {matched} / {len(rows)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
