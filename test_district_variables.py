#!/usr/bin/env python3
"""
Test what variables are available for legislative districts.
"""

import sys
from pathlib import Path
import requests

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.data.acs_data import ACSDataFetcher

def test_district_variables():
    """Test what variables work for legislative districts."""
    
    print("Testing Available Variables for Legislative Districts")
    print("=" * 55)
    
    try:
        fetcher = ACSDataFetcher()
        
        # Test with basic population variables first
        basic_variables = ['B01001_001E']  # Total population
        
        levels_to_test = [
            ('state_lower', 'House Districts'),
            ('state_upper', 'Senate Districts')
        ]
        
        for level, description in levels_to_test:
            print(f"\n{description} ({level}):")
            print("-" * 30)
            
            try:
                # Test with basic population variable
                data = fetcher.get_acs_data(
                    variables=basic_variables,
                    level=level,
                    state='15',
                    geometry=False
                )
                
                if data is not None and not data.empty:
                    print(f"  ✅ Basic variables work - {len(data)} districts found")
                    
                    # Now test transportation variables
                    try:
                        transport_data = fetcher.get_acs_data(
                            variables=['B08301_001E', 'B08301_010E'],
                            level=level,
                            state='15',
                            geometry=False
                        )
                        
                        if transport_data is not None and not transport_data.empty:
                            print(f"  ✅ Transportation variables work!")
                        else:
                            print(f"  ❌ Transportation variables not available")
                            
                    except Exception as e:
                        print(f"  ❌ Transportation variables failed: {str(e)}")
                        
                        # Check if it's a 400 error (variable not available)
                        if "400 Client Error" in str(e):
                            print(f"  ℹ️  Transportation data not available at {level} level in 2023 ACS")
                else:
                    print(f"  ❌ No data returned")
                    
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
        
        print(f"\n{'='*55}")
        print("Test complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_district_variables()
