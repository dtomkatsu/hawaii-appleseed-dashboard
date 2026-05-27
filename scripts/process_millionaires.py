"""Process the Altrata Wealth-X high-net-worth dataset into aggregated city-level
counts for the dashboard's "Millionaires" map layer.

Reads ~/Downloads/HI HNW.xlsx, takes the first-listed town as each individual's
primary residence, aggregates count per town, and joins against an embedded
HAWAII_TOWN_COORDS lookup.

Output: data/processed/millionaires_by_city.csv with columns
    city, county, lat, lon, millionaire_count

Privacy: name, organization, age, and gender columns are dropped — they never
appear in the output CSV.

Usage:
    python scripts/process_millionaires.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SOURCE_XLSX = Path.home() / "Downloads" / "HI HNW.xlsx"
SHEET_NAME = "advanced-search-results"
HEADER_ROW = 5
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "data" / "processed" / "millionaires_by_city.csv"


# (lat, lon, county) for every primary town that appears in the source data.
# Coordinates are approximate town centers — "rough location" by design.
HAWAII_TOWN_COORDS: dict[str, tuple[float, float, str]] = {
    # Oahu — Honolulu County
    "Honolulu":   (21.307, -157.858, "Honolulu"),
    "Kailua":     (21.392, -157.740, "Honolulu"),
    "Kaneohe":    (21.402, -157.799, "Honolulu"),
    "Haleiwa":    (21.594, -158.103, "Honolulu"),
    "Kahuku":     (21.681, -157.952, "Honolulu"),
    "Kapolei":    (21.336, -158.058, "Honolulu"),
    "Laie":       (21.645, -157.928, "Honolulu"),
    "Waianae":    (21.443, -158.182, "Honolulu"),
    "Aiea":       (21.382, -157.934, "Honolulu"),
    "Waipahu":    (21.387, -158.009, "Honolulu"),
    "Waialua":    (21.577, -158.131, "Honolulu"),
    "Ewa Beach":  (21.316, -158.007, "Honolulu"),
    "Waimanalo":  (21.336, -157.722, "Honolulu"),
    "Mililani":   (21.451, -157.961, "Honolulu"),

    # Maui — Maui County
    "Kihei":      (20.762, -156.450, "Maui"),
    "Lahaina":    (20.875, -156.677, "Maui"),
    "Kula":       (20.789, -156.343, "Maui"),
    "Paia":       (20.902, -156.371, "Maui"),
    "Kahului":    (20.890, -156.475, "Maui"),
    "Wailea":     (20.687, -156.443, "Maui"),
    "Makawao":    (20.857, -156.314, "Maui"),
    "Haiku":      (20.916, -156.317, "Maui"),
    "Wailuku":    (20.890, -156.504, "Maui"),
    "Hana":       (20.760, -155.991, "Maui"),
    # Ambiguous: "Maui" as a residence isn't a town. Use central Maui (Kahului).
    "Maui":       (20.890, -156.475, "Maui"),

    # Lanai — Maui County
    "Lanai City": (20.827, -156.918, "Maui"),
    "Lanai":      (20.827, -156.918, "Maui"),

    # Molokai — Maui County (and Kalawao County for the peninsula, but listings here are mainland Molokai)
    "Kaunakakai": (21.094, -157.024, "Maui"),
    "Hoolehua":   (21.169, -157.094, "Maui"),

    # Hawaii Island — Hawaii County
    "Kailua-Kona":  (19.640, -155.996, "Hawaii"),
    "Kamuela":      (20.027, -155.668, "Hawaii"),
    "Holualoa":     (19.621, -155.948, "Hawaii"),
    "Hilo":         (19.703, -155.085, "Hawaii"),
    "Waikoloa":     (19.927, -155.789, "Hawaii"),
    "Kealakekua":   (19.522, -155.928, "Hawaii"),
    "Hawi":         (20.241, -155.834, "Hawaii"),
    "Kapaau":       (20.232, -155.799, "Hawaii"),
    "Pahoa":        (19.493, -154.946, "Hawaii"),
    "Pepeekeo":     (19.838, -155.106, "Hawaii"),
    "Kukio":        (19.832, -155.985, "Hawaii"),
    "Kaupulehu":    (19.832, -155.972, "Hawaii"),

    # Kauai — Kauai County
    "Koloa":         (21.906, -159.467, "Kauai"),
    "Kilauea":       (22.211, -159.404, "Kauai"),
    "Hanalei":       (22.207, -159.499, "Kauai"),
    "Princeville":   (22.220, -159.487, "Kauai"),
    "Kapaa":         (22.075, -159.319, "Kauai"),
    "Kalaheo":       (21.927, -159.529, "Kauai"),
    "Anahola":       (22.143, -159.314, "Kauai"),
    "Kealia":        (22.118, -159.301, "Kauai"),
    "Koolau Ranch":  (22.180, -159.380, "Kauai"),
    "Kekaha":        (21.974, -159.711, "Kauai"),
    # Ambiguous: "Waimea" exists on both Kauai (town) and Hawaii Island (Kamuela area).
    # Source rows already use "Kamuela" for the Big Island town, so plain "Waimea" → Kauai.
    "Waimea":        (21.957, -159.668, "Kauai"),
}


def main() -> int:
    if not SOURCE_XLSX.exists():
        print(f"ERROR: source file not found at {SOURCE_XLSX}", file=sys.stderr)
        return 1

    df = pd.read_excel(SOURCE_XLSX, sheet_name=SHEET_NAME, header=HEADER_ROW)

    total_rows = len(df)
    null_residence = df["Residence/Property"].isna().sum()
    df = df[df["Residence/Property"].notna()].copy()

    # First-listed town = primary residence. Multi-property individuals are
    # counted once, at their first-listed location.
    df["primary_city"] = df["Residence/Property"].astype(str).str.split(",").str[0].str.strip()

    # Normalize variant town names that refer to the same place — merges
    # them into a single marker rather than overlapping dots at the same
    # coordinates.
    CITY_ALIASES = {
        "Kona": "Kailua-Kona",
        "Kailua Kona": "Kailua-Kona",
    }
    df["primary_city"] = df["primary_city"].replace(CITY_ALIASES)

    # Rewrite town names with their ʻokina (U+02BB). Source data and the
    # HAWAII_TOWN_COORDS lookup use plain spellings (no diacritics); this
    # final pass swaps in the proper Hawaiian orthography before writing
    # the CSV that drives the map tooltips. ʻokinas only — kahakō (macrons)
    # are intentionally omitted here.
    OKINA_TOWN_NAMES = {
        "Aiea":         "ʻAiea",
        "Ewa Beach":    "ʻEwa Beach",
        "Haleiwa":      "Haleʻiwa",
        "Haiku":        "Haʻiku",
        "Hoolehua":     "Hoʻolehua",
        "Kaneohe":      "Kaneʻohe",
        "Kapaa":        "Kapaʻa",
        "Kapaau":       "Kapaʻau",
        "Kaupulehu":    "Kaʻupulehu",
        "Koolau Ranch": "Koʻolau Ranch",
        "Kukio":        "Kukiʻo",
        "Laie":         "Laʻie",
        "Lanai":        "Lanaʻi",
        "Lanai City":   "Lanaʻi City",
        "Paia":         "Paʻia",
        "Pepeekeo":     "Pepeʻekeo",
        "Waianae":      "Waiʻanae",
    }
    OKINA_COUNTY_NAMES = {
        "Hawaii": "Hawaiʻi",
        "Kauai":  "Kauaʻi",
    }

    unknown = sorted(set(df["primary_city"]) - set(HAWAII_TOWN_COORDS))
    if unknown:
        print(
            "ERROR: HAWAII_TOWN_COORDS is missing entries for these towns "
            "that appear in the source data:",
            file=sys.stderr,
        )
        for town in unknown:
            print(f"  - {town!r}", file=sys.stderr)
        print(
            "\nAdd lat/lon/county for each missing town in HAWAII_TOWN_COORDS "
            "and re-run.",
            file=sys.stderr,
        )
        return 2

    grouped = (
        df.groupby("primary_city", sort=False)
        .size()
        .reset_index(name="millionaire_count")
        .rename(columns={"primary_city": "city"})
    )

    grouped["lat"] = grouped["city"].map(lambda c: HAWAII_TOWN_COORDS[c][0])
    grouped["lon"] = grouped["city"].map(lambda c: HAWAII_TOWN_COORDS[c][1])
    grouped["county"] = grouped["city"].map(lambda c: HAWAII_TOWN_COORDS[c][2])

    out = grouped[["city", "county", "lat", "lon", "millionaire_count"]].sort_values(
        "millionaire_count", ascending=False, ignore_index=True
    )

    # Swap in the ʻokina-accurate display names for the output CSV.
    out["city"] = out["city"].replace(OKINA_TOWN_NAMES)
    out["county"] = out["county"].replace(OKINA_COUNTY_NAMES)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)

    print(f"Wrote {OUTPUT_CSV}")
    print(f"  Source rows:           {total_rows}")
    print(f"  Excluded (no town):    {null_residence}")
    print(f"  Aggregated cities:     {len(out)}")
    print(f"  Total millionaires:    {int(out['millionaire_count'].sum())}")
    print(f"  Counties represented:  {sorted(out['county'].unique().tolist())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
