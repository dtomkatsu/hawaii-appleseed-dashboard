#!/usr/bin/env python3
"""Build calibrated Medicaid enrollment % for state, county, house, senate.

MedQuest publishes administrative Medicaid (managed-care) enrollment only by
ISLAND. The dashboard needs all four geographies, including legislative
districts. We therefore combine MedQuest's accuracy with ACS's granularity:

  * State / County: rate = MedQuest enrollment / ACS population. Islands map
    cleanly to counties, so these are pure administrative figures.
  * House / Senate district d in county c: take the ACS Medicaid-coverage
    *shape* (table C27007) and rake it to the MedQuest county control total,
    preserving each district's share within its county:

        K_d        = acs_medicaid(d) / sum(acs_medicaid(d') for d' in c)
        enroll(d)  = MedQuest_county_total(c) * K_d
        rate(d)    = 100 * enroll(d) / population(d)

    By construction sum(enroll(d) for d in c) == MedQuest_county_total(c), so
    the population-weighted district aggregate equals the county rate while ACS
    between-district variation is preserved.

Island -> county mapping (Hawaii legislative districts never cross county
lines, since counties are whole islands):
    Oahu->Honolulu, Hawaii->Hawaii, Kauai->Kauai, Maui+Molokai+Lanai->Maui.
    Kalawao County (pop ~67) has no MedQuest figure -> medicaid_rate left null.

Island counts come from data/raw/medquest_enrollment_2025.csv (12 monthly
managed-care counts per island, transcribed from the 2025 MedQuest report). We
use the 12-month average for stability -- the report footnote warns counts
fluctuate up to 6 months from retroactive adjustments.

Population denominators are read (read-only) from the existing processed ACS
CSVs (total_population), so the rate is consistent with every other dashboard
metric.

Outputs
-------
* Writes per-level CSVs to data/processed/medicaid/ :
      medicaid_enrollment   (calibrated count)
      medicaid_rate         (percentage, 0-100 scale -- like poverty_rate)
  These are the canonical source for the metric. They are merged into the
  layer GeoJSON by an independent MedicaidDataLoader (DataType.MEDICAID), so an
  ACS refresh can no longer silently drop the medicaid columns -- the two data
  sources are decoupled.

Re-run this annually when a new MedQuest report posts (update
data/raw/medquest_enrollment_<year>.csv and MEDQUEST_YEAR), and after any ACS
refresh if you want the population denominators to track the new ACS vintage.
Then run scripts/build_static/02_build_layer_geojsons.py to rebuild the GeoJSON.
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
MEDICAID_DIR = PROCESSED / 'medicaid'
GEOJSON_DIR = ROOT / 'web' / 'public' / 'data'
RAW = ROOT / 'data' / 'raw'

ACS_YEAR = 2024
MEDQUEST_YEAR = 2025
MEDQUEST_CSV = RAW / f'medquest_enrollment_{MEDQUEST_YEAR}.csv'

# Census API now requires a key for data queries; reuse the project default
# (same key hardcoded in src/data/acs_data.py).
API_KEY = '2104852dd7bfd83fbc9e320d650eb57decc11817'

# C27007 = Medicaid/Means-Tested Public Coverage by Sex by Age. The six
# "With Medicaid coverage" leaf cells (male/female x <19 / 19-64 / 65+).
WITH_COV = [
    'C27007_004E', 'C27007_007E', 'C27007_010E',
    'C27007_014E', 'C27007_017E', 'C27007_020E',
]

# MedQuest island label -> canonical USDA-style county name (matches the
# `county` property in web/public/data/<level>.geojson via load_crosswalk).
ISLAND_TO_COUNTY = {
    'OAHU': 'HONOLULU',
    'HAWAII': 'HAWAII',
    'KAUAI': 'KAUAI',
    'MAUI': 'MAUI',
    'MOLOKAI': 'MAUI',
    'LANAI': 'MAUI',
}

COUNTY_FIPS = {
    'HAWAII': '001',
    'HONOLULU': '003',
    'KAUAI': '007',
    'MAUI': '009',
    # KALAWAO (005) intentionally omitted -- no MedQuest figure.
}

# GeoJSON labels Honolulu county as "OAHU".
GEOJSON_COUNTY_TO_USDA = {
    'HAWAII': 'HAWAII',
    'OAHU': 'HONOLULU',
    'KAUAI': 'KAUAI',
    'MAUI': 'MAUI',
}

LEVELS = {
    'state':  {'for': 'state:15',                                       'in': None},
    'county': {'for': 'county:*',                                       'in': 'state:15'},
    'house':  {'for': 'state legislative district (lower chamber):*',   'in': 'state:15'},
    'senate': {'for': 'state legislative district (upper chamber):*',   'in': 'state:15'},
}

ACS_FILE = {
    'state':  'hawaii_state_acs_2024.csv',
    'county': 'hawaii_counties_acs_2024.csv',
    'house':  'hawaii_house_districts_acs_2024.csv',
    'senate': 'hawaii_senate_districts_acs_2024.csv',
}


# ---------------------------------------------------------------------------
# Census API (keyed) -- ACS Medicaid coverage "shape"
# ---------------------------------------------------------------------------

def fetch_acs_medicaid(level: str) -> dict[str, int]:
    """Return {geoid: medicaid_coverage_count} from C27007 for a level."""
    cfg = LEVELS[level]
    base = f'https://api.census.gov/data/{ACS_YEAR}/acs/acs5'
    params = {'get': 'NAME,' + ','.join(WITH_COV), 'for': cfg['for'], 'key': API_KEY}
    if cfg['in']:
        params['in'] = cfg['in']
    url = base + '?' + urllib.parse.urlencode(params, safe=':,')
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    headers = data[0]
    out: dict[str, int] = {}
    for row in data[1:]:
        r = dict(zip(headers, row))
        count = sum(int(r[c]) for c in WITH_COV if r[c] not in (None, '', '-'))
        out[acs_geoid(level, r)] = count
    return out


def acs_geoid(level: str, row: dict) -> str:
    s = row['state'].zfill(2)
    if level == 'state':
        return s
    if level == 'county':
        return s + row['county'].zfill(3)
    if level == 'house':
        return s + row['state legislative district (lower chamber)'].zfill(3)
    if level == 'senate':
        return s + row['state legislative district (upper chamber)'].zfill(3)
    raise ValueError(level)


# ---------------------------------------------------------------------------
# MedQuest island counts -> county control totals (12-month average)
# ---------------------------------------------------------------------------

def load_medquest_county_totals() -> dict[str, float]:
    """Return {county_name: annual_avg_managed_care_enrollment}."""
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    totals: dict[str, float] = {c: 0.0 for c in COUNTY_FIPS}
    with open(MEDQUEST_CSV, 'r', encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            island = row['island'].strip().upper()
            county = ISLAND_TO_COUNTY.get(island)
            if county is None:
                sys.exit(f'Unknown MedQuest island: {island!r}')
            annual_avg = sum(int(row[m]) for m in months) / 12.0
            totals[county] += annual_avg
    return totals


# ---------------------------------------------------------------------------
# Read existing ACS CSV (population denominator + names)
# ---------------------------------------------------------------------------

def read_acs_csv(level: str) -> tuple[list[str], list[dict]]:
    path = PROCESSED / ACS_FILE[level]
    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


# ---------------------------------------------------------------------------
# District -> county crosswalk from GeoJSON
# ---------------------------------------------------------------------------

def load_crosswalk(level: str) -> dict[str, str]:
    """Return {geoid: county_name} for house or senate districts."""
    path = GEOJSON_DIR / f'{level}.geojson'
    with open(path, 'r', encoding='utf-8') as f:
        gj = json.load(f)
    out: dict[str, str] = {}
    for feat in gj['features']:
        p = feat['properties']
        gj_county = (p.get('county') or '').upper()
        county = GEOJSON_COUNTY_TO_USDA.get(gj_county)
        if county is None:
            sys.exit(f'Unknown county in {level}.geojson: {gj_county!r}')
        out[p['geoid']] = county
    return out


# ---------------------------------------------------------------------------
# Write per-level detail CSVs (the canonical medicaid source)
# ---------------------------------------------------------------------------

def write_detail_csv(level: str, rows: list[dict], fields: list[str]) -> None:
    MEDICAID_DIR.mkdir(parents=True, exist_ok=True)
    name = {
        'state': 'hawaii_state_medicaid_2025.csv',
        'county': 'hawaii_county_medicaid_2025.csv',
        'house': 'hawaii_house_district_medicaid_2025.csv',
        'senate': 'hawaii_senate_district_medicaid_2025.csv',
    }[level]
    path = MEDICAID_DIR / name
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print(f'  wrote {path.relative_to(ROOT)} ({len(rows)} rows)')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f'[1/5] Loading MedQuest {MEDQUEST_YEAR} island counts -> county totals...')
    medquest = load_medquest_county_totals()
    state_total = sum(medquest.values())
    for c in sorted(medquest):
        print(f'  {c:9s}: {medquest[c]:>11,.1f}')
    print(f'  STATE    : {state_total:>11,.1f}')

    print('\n[2/5] Fetching ACS C27007 Medicaid coverage shape (house + senate)...')
    acs_medicaid = {lvl: fetch_acs_medicaid(lvl) for lvl in ('house', 'senate')}
    for lvl in ('house', 'senate'):
        print(f'  {lvl}: {len(acs_medicaid[lvl])} districts, '
              f'sum coverage={sum(acs_medicaid[lvl].values()):,}')

    print('\n[3/5] Computing state + county rates (pure MedQuest / ACS pop)...')
    detail = {lvl: [] for lvl in LEVELS}

    # State
    _, state_rows = read_acs_csv('state')
    srow = state_rows[0]
    spop = int(srow['total_population'])
    srate = round(100.0 * state_total / spop, 2)
    detail['state'].append({
        'geoid': srow['geoid'], 'name': srow['name'],
        'medquest_enrollment': round(state_total, 1), 'population': spop,
        'medicaid_enrollment': round(state_total), 'medicaid_rate': srate})
    print(f'  STATE: {srate}% ({round(state_total):,} / {spop:,})')

    # County
    _, county_rows = read_acs_csv('county')
    fips_to_county = {'15' + f: c for c, f in COUNTY_FIPS.items()}
    for r in county_rows:
        g = r['geoid']
        pop = int(r['total_population'])
        county = fips_to_county.get(g)
        if county is None:  # Kalawao -> leave null
            print(f'  {r["name"]}: (no MedQuest figure -> null)')
            continue
        enroll = medquest[county]
        rate = round(100.0 * enroll / pop, 2)
        detail['county'].append({
            'geoid': g, 'name': r['name'], 'county': county,
            'medquest_enrollment': round(enroll, 1), 'population': pop,
            'medicaid_enrollment': round(enroll), 'medicaid_rate': rate})
        print(f'  {county:9s} ({g}): {rate}% ({round(enroll):,} / {pop:,})')

    print('\n[4/5] Raking ACS shape to MedQuest county totals (house + senate)...')
    for level in ('house', 'senate'):
        crosswalk = load_crosswalk(level)
        _, rows = read_acs_csv(level)
        pop_by_geoid = {r['geoid']: int(r['total_population']) for r in rows}
        name_by_geoid = {r['geoid']: r['name'] for r in rows}
        med = acs_medicaid[level]

        # Sum ACS coverage per county for the K denominator.
        acs_sum: dict[str, int] = {c: 0 for c in COUNTY_FIPS}
        for g, county in crosswalk.items():
            acs_sum[county] += med.get(g, 0)

        check = {c: 0.0 for c in COUNTY_FIPS}
        for g in sorted(crosswalk):
            county = crosswalk[g]
            k = (med.get(g, 0) / acs_sum[county]) if acs_sum[county] else 0.0
            enroll = medquest[county] * k
            pop = pop_by_geoid[g]
            rate = round(100.0 * enroll / pop, 2) if pop else 0.0
            detail[level].append({
                'geoid': g, 'name': name_by_geoid[g], 'county': county,
                'acs_medicaid_coverage': med.get(g, 0),
                'ratio_leg_county': round(k, 6),
                'medquest_county_total': round(medquest[county], 1),
                'population': pop,
                'medicaid_enrollment': round(enroll), 'medicaid_rate': rate})
            check[county] += enroll
        for c in sorted(check):
            delta = check[c] - medquest[c]
            print(f'    {level} {c:9s}: sum enroll={check[c]:>11,.1f} '
                  f'(MedQuest={medquest[c]:>11,.1f}, delta={delta:+.1f})')

    print('\n[5/5] Writing per-level medicaid CSVs (data/processed/medicaid/)...')
    write_detail_csv('state', detail['state'],
                     ['geoid', 'name', 'medquest_enrollment', 'population',
                      'medicaid_enrollment', 'medicaid_rate'])
    write_detail_csv('county', detail['county'],
                     ['geoid', 'name', 'county', 'medquest_enrollment',
                      'population', 'medicaid_enrollment', 'medicaid_rate'])
    for level in ('house', 'senate'):
        write_detail_csv(level, detail[level],
                         ['geoid', 'name', 'county', 'acs_medicaid_coverage',
                          'ratio_leg_county', 'medquest_county_total',
                          'population', 'medicaid_enrollment', 'medicaid_rate'])

    print('\nDone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
