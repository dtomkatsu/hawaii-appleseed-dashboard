#!/usr/bin/env python3
"""Build state-level summary JSON for fact-sheet comparisons.

Replaces the hardcoded state_avg_income / state_avg_rent / etc. values
in pages/geo_detail.py:268-272 with real values pulled from the state
ACS data via DataLoader.get_all_data_for_geo('15').
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from src.data.data_loader import DataLoader


OUTPUT = ROOT / 'web' / 'public' / 'data' / 'state_summary.json'


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    loader = DataLoader()
    state = loader.get_all_data_for_geo('15')
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)
    print(f'[state-summary] -> {OUTPUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
