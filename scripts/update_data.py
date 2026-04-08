#!/usr/bin/env python3
"""
Unified data update script for the Hawaii Appleseed Dashboard.

Usage examples:
  # Fetch new ACS data for 2024 and update the config year
  python scripts/update_data.py --year 2024 --sources acs

  # Just validate that all expected files exist (no fetching)
  python scripts/update_data.py --check

  # Update ACS to 2024 and show instructions for manual sources
  python scripts/update_data.py --year 2024

Environment variables:
  CENSUS_API_KEY  — Census Bureau API key (required for ACS fetch).
                    Get a free key at https://api.census.gov/data/key_signup.html
                    Can also be passed with --api-key.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.data_source_registry import (
    validate_all_sources,
    get_source_info,
    get_file_path,
    get_instructions,
    get_missing_files,
    set_year,
    get_year,
    get_census_variables,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── ANSI colour helpers ──────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _ok(msg):  return f"{GREEN}✓{RESET}  {msg}"
def _warn(msg): return f"{YELLOW}⚠{RESET}  {msg}"
def _err(msg):  return f"{RED}✗{RESET}  {msg}"
def _info(msg): return f"   {msg}"


# ── Status check ─────────────────────────────────────────────────────────────

def cmd_check():
    """Print a status table showing which data files exist."""
    print(f"\n{BOLD}Data Source Status{RESET}\n{'─'*60}")
    report = validate_all_sources()
    all_ok = True
    for key, info in report.items():
        icon = _ok if info["status"] == "ok" else (_warn if info["status"] == "partial" else _err)
        status_label = {"ok": "OK", "partial": "PARTIAL", "missing": "MISSING"}[info["status"]]
        print(f"  {info['label']}")
        print(f"    Year:   {info['year']}")
        print(f"    Status: {icon(status_label)}")
        if info["missing"]:
            all_ok = False
            for level, path in info["missing"]:
                rel = path.relative_to(PROJECT_ROOT) if path.is_absolute() else path
                print(_warn(f"      Missing [{level}]: {rel}"))
        print()

    if all_ok:
        print(_ok("All data files are present.\n"))
    else:
        print(_warn("Some files are missing. Run with --year to update, or see --help.\n"))


# ── ACS fetch ────────────────────────────────────────────────────────────────

def cmd_fetch_acs(year: int, api_key: str):
    """Fetch ACS data from the Census API and save CSVs."""
    try:
        from src.data.acs_data import ACSDataFetcher
    except ImportError as e:
        logger.error(f"Could not import ACSDataFetcher: {e}")
        logger.error("Make sure dependencies are installed: pip install -r requirements.txt")
        return False

    print(f"\n{BOLD}Fetching ACS {year} data from Census API…{RESET}\n")

    acs = ACSDataFetcher(api_key=api_key, year=year)
    census_vars = list(get_census_variables("acs").keys())

    geo_levels = ["state", "county", "house", "senate"]
    # Map our level keys to what ACSDataFetcher expects
    api_level_map = {
        "state":  "state",
        "county": "county",
        "house":  "state_lower",
        "senate": "state_upper",
    }

    success_count = 0
    for level in geo_levels:
        output_path = get_file_path("acs", level)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        api_level = api_level_map[level]
        print(f"  Fetching {level} ({api_level})…", end=" ", flush=True)
        try:
            df = acs.get_acs_data(
                variables=census_vars,
                level=api_level,
                state="15",   # Hawaii FIPS
                geometry=False,
            )
            if df is None or df.empty:
                print(_err("No data returned"))
                continue

            # Calculate derived metrics
            if hasattr(acs, "calculate_poverty_rate"):
                df = acs.calculate_poverty_rate(df)

            df.to_csv(output_path, index=False)
            print(_ok(f"Saved → {output_path.relative_to(PROJECT_ROOT)}"))
            success_count += 1
        except Exception as e:
            print(_err(str(e)))
            logger.debug("ACS fetch error", exc_info=True)

    if success_count == len(geo_levels):
        set_year("acs", year)
        print(f"\n{_ok(f'ACS year updated to {year} in data_sources.json')}\n")
        return True
    elif success_count > 0:
        print(f"\n{_warn(f'{success_count}/{len(geo_levels)} levels fetched successfully.')}")
        print(_warn("Partial update — year NOT changed in data_sources.json. Fix errors and retry.\n"))
        return False
    else:
        print(f"\n{_err('All ACS fetches failed. Year not updated.')}\n")
        return False


# ── Manual source guidance ────────────────────────────────────────────────────

def cmd_manual_source(source: str, year: int):
    """Print instructions and file status for a manual data source."""
    info = get_source_info(source)
    missing = get_missing_files(source)

    print(f"\n{BOLD}{info['label']}{RESET}")
    print(f"  Current year in config: {get_year(source)}")
    print(f"  Target year:            {year}")
    print(f"\n  {BOLD}Instructions:{RESET}")
    for line in get_instructions(source).split(". "):
        if line.strip():
            print(f"  • {line.strip()}.")

    print(f"\n  {BOLD}Expected files:{RESET}")
    if source == "alice":
        from src.data.data_source_registry import get_alice_excel_path
        path = get_alice_excel_path()
        exists = path.exists()
        status = _ok("found") if exists else _err("not found")
        print(f"  {status}  {path.relative_to(PROJECT_ROOT)}")
    else:
        for level, path in zip(
            info.get("file_patterns", {}).keys(),
            [get_file_path(source, lvl) for lvl in info.get("file_patterns", {}).keys()]
        ):
            exists = path.exists()
            rel = path.relative_to(PROJECT_ROOT)
            status = _ok("found") if exists else _err("not found")
            print(f"  {status}  [{level}]  {rel}")

    if not missing:
        response = input(f"\n  All files present. Update year to {year}? [y/N] ").strip().lower()
        if response == "y":
            set_year(source, year)
            print(_ok(f"Updated {source} year to {year} in data_sources.json\n"))
        else:
            print("  Year not updated.\n")
    else:
        print(f"\n  {_warn(f'{len(missing)} file(s) missing. Place files and re-run to confirm.')}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Update census and program data for the Hawaii Appleseed Dashboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--year", type=int,
        help="Target data year (e.g. 2024). Required unless --check is used.",
    )
    parser.add_argument(
        "--sources", default="all",
        help="Comma-separated list of sources to update: acs,snap,cep,alice,tax_credits. "
             "Default: all. ACS is the only source that can be fetched automatically.",
    )
    parser.add_argument(
        "--api-key",
        help="Census API key (overrides CENSUS_API_KEY env var).",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Just validate which data files exist. No fetching or updating.",
    )
    args = parser.parse_args()

    if args.check:
        cmd_check()
        return

    if not args.year:
        parser.error("--year is required unless --check is used.")

    all_sources = ["acs", "snap", "cep", "alice", "tax_credits"]
    if args.sources == "all":
        sources = all_sources
    else:
        sources = [s.strip() for s in args.sources.split(",")]
        unknown = [s for s in sources if s not in all_sources]
        if unknown:
            parser.error(f"Unknown sources: {', '.join(unknown)}. Valid: {', '.join(all_sources)}")

    print(f"\n{BOLD}Hawaii Appleseed Dashboard — Data Update{RESET}")
    print(f"Target year: {BOLD}{args.year}{RESET}")
    print(f"Sources:     {', '.join(sources)}\n")

    for source in sources:
        info = get_source_info(source)
        if info["fetch_method"] == "api":
            api_key = args.api_key or os.environ.get("CENSUS_API_KEY")
            if not api_key:
                print(_err(
                    f"No Census API key found for '{source}'. "
                    "Set CENSUS_API_KEY env var or use --api-key. "
                    "Get a free key at https://api.census.gov/data/key_signup.html"
                ))
                continue
            cmd_fetch_acs(args.year, api_key)
        else:
            cmd_manual_source(source, args.year)

    print(f"\n{BOLD}Done.{RESET} Run  python scripts/update_data.py --check  to verify.\n")


if __name__ == "__main__":
    main()
