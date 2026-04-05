#!/usr/bin/env python3
"""
Test S0802 table for Means of Transportation to Work by Selected Characteristics.
"""

import os
import sys
import requests
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.data.acs_data import ACSDataFetcher

def get_acs_subject_data(variables, level='county', state='15', year=2023):
    """Fetch data from ACS Subject Tables API."""
    base_url = f"https://api.census.gov/data/{year}/acs/acs5/subject"
    
    # Map level to Census geography
    geo_mapping = {
        'state': ('state', '15'),  # 15 is Hawaii's FIPS code
        'county': ('county', '*'),
        'state_lower': ('state legislative district (lower chamber)', '*'),
        'state_upper': ('state legislative district (upper chamber)', '*')
    }
    
    if level not in geo_mapping:
        raise ValueError(f"Unsupported geographic level: {level}")
    
    # Special handling for state level
    api_key = os.environ.get('CENSUS_API_KEY')
    if not api_key:
        raise RuntimeError("CENSUS_API_KEY environment variable is not set")

    if level == 'state':
        params = {
            'get': 'NAME,' + ','.join(variables),
            'for': 'state:15',
            'key': api_key
        }
    else:
        geo_type, geo_value = geo_mapping[level]
        params = {
            'get': 'NAME,' + ','.join(variables),
            'for': f'{geo_type}:{geo_value}',
            'in': f'state:{state}',
            'key': api_key
        }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def test_s0802_data():
    """Test S0802 transportation variables across different geographic levels."""
    
    print("Testing S0802 - Means of Transportation to Work (ACS Subject Tables)")
    print("=" * 80)
    
    # S0802 variables for transportation to work
    # S0802_C01_001E = Total workers 16 years and over
    # S0802_C01_002E = Car, truck, or van - drove alone
    # S0802_C01_003E = Car, truck, or van - carpooled
    # S0802_C01_010E = Public transportation (excluding taxicab)
    transport_vars = [
        'S0802_C01_001E',  # Total workers
        'S0802_C01_002E',  # Drove alone
        'S0802_C01_003E',  # Carpooled
        'S0802_C01_010E',  # Public transportation
        'S0802_C01_014E'   # Worked at home
    ]
    
    levels_to_test = [
        ('state', 'State'),
        ('county', 'Counties'),
        ('state_lower', 'House Districts'),
        ('state_upper', 'Senate Districts')
    ]
    
    for level, description in levels_to_test:
        print(f"\n{description} ({level}):")
        print("-" * 80)
        
        try:
            # Use the ACS Subject Tables endpoint
            data = get_acs_subject_data(
                variables=transport_vars,
                level=level,
                state='15'  # Hawaii
            )
            
            if data and len(data) > 1:  # First row is header
                print(f"  ✅ S0802 data retrieved - {len(data)-1} records found")
                print(f"  📋 Variables: {data[0]}")
                
                # Display first data row
                print(f"  📊 Sample: {data[1][0]}")  # NAME is first column
                
                # Find indices of our variables
                headers = [h.lower() for h in data[0]]
                var_indices = {}
                for var in [v.lower() for v in transport_vars]:
                    if var in headers:
                        var_indices[var] = headers.index(var)
                
                # Show values for our variables
                for var, idx in var_indices.items():
                    print(f"    {var}: {data[1][idx]}")
                
                # Calculate public transit percentage if we have the data
                if 's0802_c01_001e' in var_indices and 's0802_c01_010e' in var_indices:
                    total_idx = var_indices['s0802_c01_001e']
                    transit_idx = var_indices['s0802_c01_010e']
                    
                    total_workers = sum(float(row[total_idx]) for row in data[1:] if row[total_idx] is not None)
                    transit_workers = sum(float(row[transit_idx]) for row in data[1:] if row[transit_idx] is not None)
                    
                    if total_workers > 0:
                        pct_transit = (transit_workers / total_workers) * 100
                        print(f"  🚌 {pct_transit:.1f}% of workers use public transportation")
                    
                    # Check work from home if available
                    if 's0802_c01_014e' in var_indices:
                        wfh_idx = var_indices['s0802_c01_014e']
                        wfh_workers = sum(float(row[wfh_idx]) for row in data[1:] if row[wfh_idx] is not None)
                        if total_workers > 0:
                            pct_wfh = (wfh_workers / total_workers) * 100
                            print(f"  🏠 {pct_wfh:.1f}% of workers work from home")
            else:
                print(f"  ❌ No data returned or empty response")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            if "400 Client Error" in str(e):
                print(f"  ℹ️  S0802 not available at {level} level")
    
    print(f"\n{'='*80}")
    print("S0802 Transportation Test Complete!")

if __name__ == "__main__":
    test_s0802_data()
