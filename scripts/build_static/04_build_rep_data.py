#!/usr/bin/env python3
"""Build legislator data JSON for tooltip + info-panel rendering.

Reads the two CSVs in data/processed/ that ship with the repo and emits
web/public/data/rep_data.json keyed by 'house_<n>' / 'senate_<n>'.

Mirrors src/ui/leaflet_component.py:_load_rep_data_json (note the
skiprows=1 quirk for the house file, which has a duplicate header row).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / 'web' / 'public' / 'data' / 'rep_data.json'
DATA = ROOT / 'data' / 'processed'


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rep: dict[str, dict[str, str]] = {}

    house = DATA / 'hawaii_house_districts_2025_complete.csv'
    if house.exists():
        df = pd.read_csv(house, skiprows=1)
        for _, row in df.iterrows():
            key = f"house_{int(row['District'])}"
            rep[key] = {
                'name': str(row['Representative_Name']).strip(),
                'party': str(row['Party']).strip(),
                'areas': str(row['Areas_Covered']).strip(),
            }

    senate = DATA / 'hawaii_senate_districts_2025_complete.csv'
    if senate.exists():
        df = pd.read_csv(senate)
        for _, row in df.iterrows():
            key = f"senate_{int(row['District'])}"
            rep[key] = {
                'name': str(row['Senator_Name']).strip(),
                'party': str(row['Party']).strip(),
                'areas': str(row['Areas_Covered']).strip(),
            }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f'[rep-data] -> {OUTPUT.relative_to(ROOT)} ({len(rep)} entries)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
