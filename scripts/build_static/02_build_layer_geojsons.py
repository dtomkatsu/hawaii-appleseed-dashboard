#!/usr/bin/env python3
"""Build per-layer enriched GeoJSON files for the static JS dashboard.

Reuses src.data.data_loader.DataLoader to merge ACS + ALICE + SNAP + CEP data
into the corresponding GeoJSON boundary file for each of the 4 geography levels,
then writes the result to web/public/data/<level>.geojson.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src.*` imports resolve when this
# script is run directly via `python scripts/build_static/02_build_layer_geojsons.py`.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from src.data.data_loader import DataLoader, GeoLevel, GeoJSONProcessor


LEVELS = [GeoLevel.STATE, GeoLevel.COUNTY, GeoLevel.HOUSE, GeoLevel.SENATE]
OUTPUT_DIR = ROOT / 'web' / 'public' / 'data'

GEOJSON_DIR = ROOT / 'data' / 'Processed GeoJsons'
GEOJSON_FILES = {
    GeoLevel.STATE: 'hawaii_state_boundary.geojson',
    GeoLevel.COUNTY: 'hawaii_county_boundaries.geojson',
    GeoLevel.HOUSE: 'Hawaii_State_House_Districts_2022.geojson',
    GeoLevel.SENATE: 'Hawaii_State_Senate_Districts_2022.geojson',
}


def load_geojson_for(level: GeoLevel) -> dict | None:
    base = GEOJSON_DIR / GEOJSON_FILES[level]
    gz_path = base.with_suffix(base.suffix + '.gz')
    if gz_path.exists():
        with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
            return json.load(f)
    if base.exists():
        with open(base, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    loader = DataLoader()
    geo_processor: GeoJSONProcessor = loader.geojson_processor

    for level in LEVELS:
        print(f'[build-geojson] Processing {level.value}...')
        geojson = load_geojson_for(level)
        if geojson is None:
            print(f'  ! No GeoJSON found for {level.value}, skipping')
            continue
        df = loader.get_data(level.value)
        if df is None or df.empty:
            print(f'  ! No tabular data for {level.value}; writing geometry only')
            enriched = geojson
        else:
            enriched = geo_processor.merge_geojson_with_data(geojson, df, level)

        out_path = OUTPUT_DIR / f'{level.value}.geojson'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(enriched, f, ensure_ascii=False, separators=(',', ':'))
        print(f'  -> {out_path.relative_to(ROOT)} ({out_path.stat().st_size // 1024} KB)')

    print('[build-geojson] Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
