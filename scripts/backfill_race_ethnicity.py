#!/usr/bin/env python3
"""One-off: backfill race/ethnicity rates into the 2024 ACS CSVs.

Adds five percentage columns to data/processed/hawaii_*_acs_2024.csv:
    nhpi_pct       — Native Hawaiian / Pacific Islander (alone or in combination)
    asian_pct      — Asian (alone or in combination)
    white_pct      — White (alone or in combination)
    black_pct      — Black / African American (alone or in combination)
    hispanic_pct   — Hispanic or Latino, any race

"Alone or in combination" (B02008–B02012) is used for races so multi-racial
Hawaii residents are counted in every group they identify with — this matches
how policy data on Native Hawaiian populations is normally reported.
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

# Census variables to fetch
RACE_VARS = {
    'B02001_001E': 'race_total',
    'B02008_001E': 'white',
    'B02009_001E': 'black',
    'B02011_001E': 'asian',
    'B02012_001E': 'nhpi',
    'B03002_001E': 'hispanic_total_pop',
    'B03002_012E': 'hispanic',
}
NEEDED = list(RACE_VARS.keys())

OUT_COLS = ['white_pct', 'black_pct', 'asian_pct', 'nhpi_pct', 'hispanic_pct']

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


def compute_rates(row: dict) -> dict[str, float | None]:
    def _pct(num_var, denom_var):
        try:
            n = float(row[num_var])
            d = float(row[denom_var])
            if d <= 0:
                return None
            return round((n / d) * 100, 2)
        except (KeyError, ValueError, TypeError):
            return None
    return {
        'white_pct':    _pct('B02008_001E', 'B02001_001E'),
        'black_pct':    _pct('B02009_001E', 'B02001_001E'),
        'asian_pct':    _pct('B02011_001E', 'B02001_001E'),
        'nhpi_pct':     _pct('B02012_001E', 'B02001_001E'),
        'hispanic_pct': _pct('B03002_012E', 'B03002_001E'),
    }


def update_csv(csv_path: Path, rates_by_geoid: dict[str, dict]) -> int:
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for col in OUT_COLS:
        if col not in fieldnames:
            fieldnames.append(col)
    matched = 0
    for r in rows:
        gid = (r.get('geoid') or '').strip()
        rates = rates_by_geoid.get(gid)
        if rates:
            matched += 1
            for col in OUT_COLS:
                v = rates.get(col)
                r[col] = '' if v is None else v
        else:
            for col in OUT_COLS:
                r.setdefault(col, '')
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
        rates_by_geoid: dict[str, dict] = {}
        for r in rows:
            gid = make_geoid(level, r)
            if gid:
                rates_by_geoid[gid] = compute_rates(r)
        matched = update_csv(csv_path, rates_by_geoid)
        print(f'  -> updated {csv_path.name}: matched {matched} / {len(rows)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
