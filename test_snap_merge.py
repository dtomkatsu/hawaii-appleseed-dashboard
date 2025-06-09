"""Test script to verify SNAP data merging."""
import sys
import pandas as pd
from pathlib import Path

# Add the parent directory to the path so we can import the data_loader
sys.path.append(str(Path(__file__).parent))

from src.data.data_loader import DataLoader

def test_snap_merging():
    print("=== Testing SNAP Data Merging ===")
    
    # Initialize the data loader
    data_loader = DataLoader()
    
    # Test with county level data
    print("\nLoading county data...")
    county_data = data_loader.get_data('county')
    
    if county_data is None:
        print("❌ Failed to load county data")
        return False
    
    # Check if SNAP columns exist in the merged data
    snap_columns = [
        'snap_household_rate',
        'snap_benefit_annual_per_household',
        'snap_benefits_annual_total'
    ]
    
    print("\nChecking for SNAP columns in merged data:")
    all_columns_found = True
    for col in snap_columns:
        if col in county_data.columns:
            print(f"✅ Found column: {col}")
            # Print sample values
            print(f"   Sample values:\n{county_data[['NAME', col]].head()}\n")
        else:
            print(f"❌ Missing column: {col}")
            all_columns_found = False
    
    # Check for Kauai data specifically
    print("\nChecking Kauai data:")
    if 'NAME' in county_data.columns:
        kauai_data = county_data[county_data['NAME'].str.contains('Kauai', case=False, na=False)]
        if not kauai_data.empty:
            print("✅ Found Kauai data:")
            print(kauai_data[['NAME'] + [c for c in snap_columns if c in county_data.columns]].to_string())
        else:
            print("❌ Could not find Kauai data in merged dataset")
            all_columns_found = False
    else:
        print("❌ 'NAME' column not found in merged data")
        all_columns_found = False
    
    return all_columns_found

if __name__ == "__main__":
    success = test_snap_merging()
    if success:
        print("\n✅ SNAP data merging test completed successfully!")
    else:
        print("\n❌ SNAP data merging test found issues.")
        sys.exit(1)
