#!/usr/bin/env python3
"""Backfill 2024 SNAP data for state, county, house district, and senate district.

ACS systematically underreports SNAP participation, so we scale each district's
ACS-reported SNAP household count to match the authoritative USDA county totals
while preserving the district's proportional share within its county
(Ratio Leg:Island). USDA only publishes per-HH benefit dollars at the county
level, so to give districts plausible per-HH variation we weight each district's
per-HH benefit by ACS average household size — a proxy for federal SNAP
allotment, which is roughly linear in HH size.

For every legislative district::

    K        = district_ACS_snap_HH / sum(ACS_snap_HH for districts in same county)
    adj_HH   = USDA_county_snap_HH * K                           # corrected HH count
    rate     = adj_HH / district_total_HH

    # HH-size-weighted per-HH benefit, calibrated so the K-weighted
    # county sum equals the USDA county per-HH amount:
    S        = sum_d (size_d * K_d)                              # K-weighted county avg size
    monthly  = (USDA_county_issuance / USDA_county_snap_HH) * (size_d / S)
    annual   = monthly * 12
    total_$  = adj_HH * annual                                   # district SNAP $ / yr

By construction, sum_d (adj_HH_d * annual_d) = USDA county total dollars.

Inputs
------
* ACS 2024 5-year via Census API
    - B22001_001E: total households
    - B22001_002E: households that received SNAP
    - B25010_001E: average household size (occupied housing units)
* USDA bi-annual JUL 2024 county-level data
    Path: ``~/Downloads/snap-zip-fns388a-2/JUL 2024.xlsx``
* GeoJSON files in ``web/public/data`` for the district->county crosswalk
  (each feature has a ``county`` property: HAWAII / OAHU / MAUI / KAUAI).

Outputs
-------
* Augments ``data/processed/hawaii_*_acs_2024.csv`` with two new columns
  (total_households, snap_households).
* Writes 4 SNAP CSVs to ``data/processed/snap_benefits/hawaii_*_snap_2024.csv``.

See ``data/processed/snap_benefits/METHODOLOGY.md`` for the full writeup.
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / 'data' / 'processed'
SNAP_DIR = PROCESSED / 'snap_benefits'
GEOJSON_DIR = ROOT / 'web' / 'public' / 'data'

YEAR = 2024
USDA_FILE = Path.home() / 'Downloads' / 'snap-zip-fns388a-2' / 'JUL 2024.xlsx'

# ACS variables
#   B22001 — Receipt of food stamps/SNAP in past 12 months
#   B25010_001E — Average household size of occupied housing units (used to
#     vary district-level per-HH SNAP benefit; see compute_district_rows).
TOTAL_HH = 'B22001_001E'
SNAP_HH = 'B22001_002E'
AVG_HH_SIZE = 'B25010_001E'
ACS_VARS = [TOTAL_HH, SNAP_HH, AVG_HH_SIZE]

# Maps the GeoJSON `county` property (and the substate-region label in the
# JUL 2024 Excel) to the canonical county FIPS suffix used in ``geoid``.
COUNTY_FIPS = {
    'HAWAII': '001',
    'HONOLULU': '003',  # the GeoJSON labels Honolulu as "OAHU"
    'KALAWAO': '005',
    'KAUAI': '007',
    'MAUI': '009',
}

# Two names refer to the same place: GeoJSON uses OAHU, USDA uses HONOLULU.
GEOJSON_COUNTY_TO_USDA = {
    'HAWAII': 'HAWAII',
    'OAHU': 'HONOLULU',
    'KAUAI': 'KAUAI',
    'MAUI': 'MAUI',
}


# ---------------------------------------------------------------------------
# Census API
# ---------------------------------------------------------------------------

LEVELS = {
    'state':  {'for': 'state:15',                                          'in': None},
    'county': {'for': 'county:*',                                          'in': 'state:15'},
    'house':  {'for': 'state legislative district (lower chamber):*',     'in': 'state:15'},
    'senate': {'for': 'state legislative district (upper chamber):*',     'in': 'state:15'},
}

ACS_FILE = {
    'state':  'hawaii_state_acs_2024.csv',
    'county': 'hawaii_counties_acs_2024.csv',
    'house':  'hawaii_house_districts_acs_2024.csv',
    'senate': 'hawaii_senate_districts_acs_2024.csv',
}


def fetch_acs(level: str) -> list[dict]:
    cfg = LEVELS[level]
    base = f'https://api.census.gov/data/{YEAR}/acs/acs5'
    params = {'get': 'NAME,' + ','.join(ACS_VARS), 'for': cfg['for']}
    if cfg['in']:
        params['in'] = cfg['in']
    url = base + '?' + urllib.parse.urlencode(params, safe=':,')
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    headers = data[0]
    return [dict(zip(headers, row)) for row in data[1:]]


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
# Augment existing 2024 ACS CSVs in place
# ---------------------------------------------------------------------------

def augment_acs_csv(level: str, snap_by_geoid: dict[str, dict]) -> None:
    csv_path = PROCESSED / ACS_FILE[level]
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    added = []
    for col in ('total_households', 'snap_households'):
        if col not in fieldnames:
            fieldnames.append(col)
            added.append(col)

    updated = 0
    for r in rows:
        g = r.get('geoid', '')
        snap = snap_by_geoid.get(g)
        if snap is None:
            continue
        r['total_households'] = snap['total_households']
        r['snap_households'] = snap['snap_households']
        updated += 1

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'  augmented {csv_path.name}: {updated}/{len(rows)} rows, added cols {added or "(already present)"}')


# ---------------------------------------------------------------------------
# Parse JUL 2024 USDA bi-annual file
# ---------------------------------------------------------------------------

def parse_usda_county() -> dict[str, dict]:
    """Return {county_name: {'snap_households': int, 'monthly_issuance': int}}.

    JUL 2024.xlsx layout (single sheet, 'Page'):
      row 4 contains the column labels
      data rows start at row 5
      col 1 = Substate/Region (e.g. "1500101 HI EBT HAWAII")
      col 12 = Calc: SNAP Total PA and Non-PA Households
      col 14 = SNAP All Total Actual PA & Non-PA Issuance (monthly $)
    """
    wb = openpyxl.load_workbook(USDA_FILE, data_only=True)
    ws = wb.active
    out: dict[str, dict] = {}
    for row in ws.iter_rows(min_row=5, values_only=True):
        label = row[0]
        if not isinstance(label, str) or 'HI EBT' not in label:
            continue
        # "1500101 HI EBT HAWAII" -> "HAWAII"
        county = label.split('HI EBT', 1)[1].strip().upper()
        hh = row[11]
        issuance = row[13]
        if not isinstance(hh, (int, float)) or not isinstance(issuance, (int, float)):
            continue
        out[county] = {'snap_households': int(hh), 'monthly_issuance': float(issuance)}
    expected = {'HAWAII', 'HONOLULU', 'KAUAI', 'MAUI'}
    missing = expected - out.keys()
    if missing:
        sys.exit(f'JUL 2024 file is missing counties: {missing}')
    return out


# ---------------------------------------------------------------------------
# District -> county crosswalk from GeoJSON
# ---------------------------------------------------------------------------

def load_crosswalk(level: str) -> dict[str, str]:
    """Return {geoid: USDA_county_name} for house or senate districts."""
    path = GEOJSON_DIR / f'{level}.geojson'
    with open(path, 'r', encoding='utf-8') as f:
        gj = json.load(f)
    out: dict[str, str] = {}
    for feat in gj['features']:
        p = feat['properties']
        gj_county = p.get('county', '').upper()
        usda_county = GEOJSON_COUNTY_TO_USDA.get(gj_county)
        if usda_county is None:
            sys.exit(f'Unknown county in {level}.geojson: {gj_county!r}')
        # GeoJSON `geoid` is already 5-digit.
        out[p['geoid']] = usda_county
    return out


# ---------------------------------------------------------------------------
# Compute SNAP rows
# ---------------------------------------------------------------------------

def compute_district_rows(
    level: str,
    acs_rows_by_geoid: dict[str, dict],
    crosswalk: dict[str, str],
    usda_by_county: dict[str, dict],
) -> tuple[list[dict], dict[str, dict]]:
    """Per-district SNAP rows with HH-size-weighted per-HH benefit.

    Two-step calculation, applied independently within each county:

    1. **Leg:Island ratio K** distributes the USDA county SNAP HH count down
       to districts: ``snap_households_adjusted = USDA_county_HH × K``.
       (K = district_ACS_snap / county_ACS_snap_sum.)

    2. **HH-size weighting** distributes the USDA county *per-HH benefit* to
       districts using ACS avg HH size as a proxy for federal SNAP allotment
       (which scales with HH size). Calibrated so the K-weighted sum of
       per-HH benefits within a county equals the county per-HH benefit:

           per_HH_d = county_per_HH × (size_d / S)
           where S = Σ_d (size_d × K_d)

       This guarantees Σ_d (per_HH_d × adj_HH_d) = USDA county total dollars.
    """
    # Group ACS SNAP HH by county to compute Leg:Island ratios.
    acs_sum_by_county: dict[str, int] = {c: 0 for c in usda_by_county}
    for geoid, county in crosswalk.items():
        acs = acs_rows_by_geoid.get(geoid)
        if acs is None:
            sys.exit(f'No ACS data for {level} geoid {geoid}')
        acs_sum_by_county[county] += int(acs['snap_households'])

    # Pre-compute K and HH-size weighted sum S per county.
    ratio_k_by_geoid: dict[str, float] = {}
    s_by_county: dict[str, float] = {c: 0.0 for c in usda_by_county}
    for geoid, county in crosswalk.items():
        acs = acs_rows_by_geoid[geoid]
        district_acs_snap = int(acs['snap_households'])
        county_acs_sum = acs_sum_by_county[county]
        k = district_acs_snap / county_acs_sum if county_acs_sum else 0.0
        ratio_k_by_geoid[geoid] = k
        avg_size = float(acs['avg_hh_size'])
        s_by_county[county] += avg_size * k

    rows = []
    diagnostic = {c: {'sum_adjusted': 0.0, 'sum_total_$': 0.0, 'count': 0}
                  for c in usda_by_county}
    for geoid, county in sorted(crosswalk.items()):
        acs = acs_rows_by_geoid[geoid]
        usda = usda_by_county[county]
        district_acs_snap = int(acs['snap_households'])
        district_total_hh = int(acs['total_households'])
        avg_size = float(acs['avg_hh_size'])
        ratio_k = ratio_k_by_geoid[geoid]
        s = s_by_county[county]

        snap_adj = usda['snap_households'] * ratio_k
        county_monthly = (
            usda['monthly_issuance'] / usda['snap_households']
            if usda['snap_households']
            else 0.0
        )
        size_factor = avg_size / s if s > 0 else 1.0
        monthly_benefit = county_monthly * size_factor
        annual_benefit = monthly_benefit * 12
        rate = snap_adj / district_total_hh if district_total_hh else 0.0
        total_benefits = snap_adj * annual_benefit

        district_num = geoid[2:].lstrip('0') or '0'
        rows.append({
            'NAME': acs['name'],
            'state': '15',
            'district': district_num.zfill(2),
            'geoid': geoid,
            'total_households': district_total_hh,
            'snap_households': district_acs_snap,
            'snap_households_adjusted': round(snap_adj, 2),
            'ratio_leg_island': round(ratio_k, 6),
            'avg_hh_size': round(avg_size, 2),
            'size_factor': round(size_factor, 4),
            'snap_household_rate': round(rate, 4),
            'snap_participation_rate': round(rate, 4),
            'snap_benefit_monthly_per_household': round(monthly_benefit, 2),
            'snap_benefit_annual_per_household': round(annual_benefit, 2),
            'snap_benefits_annual_total': round(total_benefits, 2),
            'usda_county': county,
        })
        diagnostic[county]['sum_adjusted'] += snap_adj
        diagnostic[county]['sum_total_$'] += total_benefits
        diagnostic[county]['count'] += 1
    return rows, diagnostic


def compute_county_rows(
    counties_acs: dict[str, dict],
    usda_by_county: dict[str, dict],
) -> list[dict]:
    rows = []
    for county_name in ['HAWAII', 'HONOLULU', 'KAUAI', 'MAUI']:
        usda = usda_by_county[county_name]
        # ACS county row — find by NAME match (e.g. "Hawaii County, Hawaii")
        target_prefix = county_name.title()
        acs = None
        for r in counties_acs.values():
            if r['name'].startswith(target_prefix):
                acs = r
                break
        if acs is None:
            sys.exit(f'No ACS county row found for {county_name}')

        total_hh = int(acs['total_households'])
        district_acs_snap = int(acs['snap_households'])
        snap_adj = usda['snap_households']
        monthly = usda['monthly_issuance'] / snap_adj
        annual = monthly * 12
        rate = snap_adj / total_hh if total_hh else 0.0
        total_benefits = usda['monthly_issuance'] * 12

        # geoid: state 15 + county FIPS
        fips = COUNTY_FIPS[county_name]
        rows.append({
            'NAME': county_name,
            'state': '15',
            'geoid': '15' + fips,
            'total_households': total_hh,
            'snap_households': district_acs_snap,
            'snap_households_adjusted': snap_adj,
            'snap_household_rate': round(rate, 4),
            'snap_participation_rate': round(rate, 4),
            'snap_benefit_monthly_per_household': round(monthly, 2),
            'snap_benefit_annual_per_household': round(annual, 2),
            'snap_benefits_annual_total': round(total_benefits, 2),
        })
    return rows


def compute_state_row(
    state_acs: dict,
    usda_by_county: dict[str, dict],
) -> dict:
    total_hh = int(state_acs['total_households'])
    state_acs_snap = int(state_acs['snap_households'])
    sum_usda_hh = sum(c['snap_households'] for c in usda_by_county.values())
    sum_issuance = sum(c['monthly_issuance'] for c in usda_by_county.values())
    monthly = sum_issuance / sum_usda_hh
    annual = monthly * 12
    rate = sum_usda_hh / total_hh if total_hh else 0.0
    return {
        'NAME': 'Hawaii',
        'state': '15',
        'geoid': '15',
        'total_households': total_hh,
        'snap_households': state_acs_snap,
        'snap_households_adjusted': sum_usda_hh,
        'snap_household_rate': round(rate, 4),
        'snap_participation_rate': round(rate, 4),
        'snap_benefit_monthly_per_household': round(monthly, 2),
        'snap_benefit_annual_per_household': round(annual, 2),
        'snap_benefits_annual_total': round(sum_issuance * 12, 2),
    }


# ---------------------------------------------------------------------------
# CSV writers — one schema per geographic level
# ---------------------------------------------------------------------------

STATE_FIELDS = [
    'NAME', 'state', 'geoid',
    'snap_households_adjusted',
    'snap_household_rate', 'snap_participation_rate',
    'snap_benefit_monthly_per_household', 'snap_benefit_annual_per_household',
    'snap_benefits_annual_total',
]
COUNTY_FIELDS = STATE_FIELDS  # identical schema (no district column)
DISTRICT_FIELDS = [
    'NAME', 'state', 'district', 'geoid',
    'snap_households_adjusted',
    'ratio_leg_island',
    'avg_hh_size', 'size_factor',
    'snap_household_rate', 'snap_participation_rate',
    'snap_benefit_monthly_per_household', 'snap_benefit_annual_per_household',
    'snap_benefits_annual_total',
    'usda_county',
]


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    print(f'  wrote {path.relative_to(ROOT)} ({len(rows)} rows)')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print('[1/4] Fetching ACS 2024 5-year SNAP variables from Census API...')
    acs_by_level: dict[str, dict[str, dict]] = {}
    for level in LEVELS:
        rows = fetch_acs(level)
        by_geoid: dict[str, dict] = {}
        for r in rows:
            g = acs_geoid(level, r)
            by_geoid[g] = {
                'name': r['NAME'],
                'total_households': r[TOTAL_HH],
                'snap_households': r[SNAP_HH],
                'avg_hh_size': r[AVG_HH_SIZE],
            }
        acs_by_level[level] = by_geoid
        print(f'  {level}: {len(by_geoid)} geographies')

    print('\n[2/4] Augmenting existing 2024 ACS CSVs with total_households + snap_households...')
    for level in LEVELS:
        augment_acs_csv(level, acs_by_level[level])

    print('\n[3/4] Reading USDA JUL 2024 county-level data...')
    usda = parse_usda_county()
    for c, v in usda.items():
        print(f'  {c}: {v["snap_households"]:>6,} HH | ${v["monthly_issuance"]:>12,.0f}/mo')
    print(f'  TOTAL: {sum(v["snap_households"] for v in usda.values()):,} HH | '
          f'${sum(v["monthly_issuance"] for v in usda.values()):,.0f}/mo')

    print('\n[4/4] Computing corrected SNAP values and writing output CSVs...')

    # State row (uses sum of USDA county totals)
    state_acs = next(iter(acs_by_level['state'].values()))
    state_row = compute_state_row(state_acs, usda)
    write_csv(SNAP_DIR / 'hawaii_state_snap_2024.csv', STATE_FIELDS, [state_row])

    # County rows
    county_rows = compute_county_rows(acs_by_level['county'], usda)
    write_csv(SNAP_DIR / 'hawaii_county_snap_2024.csv', COUNTY_FIELDS, county_rows)

    # District rows — Leg:Island ratio applied per county
    for level in ('house', 'senate'):
        crosswalk = load_crosswalk(level)
        rows, diag = compute_district_rows(level, acs_by_level[level], crosswalk, usda)
        out = SNAP_DIR / f'hawaii_{level}_district_snap_2024.csv'
        write_csv(out, DISTRICT_FIELDS, rows)
        # Verify per-county sums match USDA totals (HH count and $).
        for county, d in diag.items():
            usda_hh = usda[county]['snap_households']
            usda_annual = usda[county]['monthly_issuance'] * 12
            print(f'    {level} {county}: {d["count"]} districts | '
                  f'HH adj={d["sum_adjusted"]:.1f} (USDA={usda_hh:,}, '
                  f'Δ={d["sum_adjusted"]-usda_hh:+.1f}) | '
                  f'$={d["sum_total_$"]:,.0f} (USDA=${usda_annual:,.0f}, '
                  f'Δ=${d["sum_total_$"]-usda_annual:+,.0f})')

    print('\nDone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
