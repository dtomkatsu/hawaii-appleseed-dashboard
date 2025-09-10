#!/usr/bin/env python3
"""
Test B08006 variables for district-level transportation data.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.data.acs_data import ACSDataFetcher

def test_b08006_districts():
    """Test B08006 variables for legislative districts."""
    
    print("Testing B08006 Variables for Legislative Districts")
    print("=" * 50)
    
    try:
        fetcher = ACSDataFetcher()
        
        # B08006 variables for public transportation
        # B08006_001E = Total workers
        # B08006_008E = Public transportation (excluding taxicab) - Total
        b08006_variables = ['B08006_001E', 'B08006_008E']
        
        levels_to_test = [
            ('county', 'Counties'),
            ('state_lower', 'House Districts'),
            ('state_upper', 'Senate Districts')
        ]
        
        for level, description in levels_to_test:
            print(f"\n{description} ({level}):")
            print("-" * 30)
            
            try:
                data = fetcher.get_acs_data(
                    variables=b08006_variables,
                    level=level,
                    state='15',
                    geometry=False
                )
                
                if data is not None and not data.empty:
                    print(f"  ✅ B08006 variables work - {len(data)} records found")
                    
                    # Check if columns were renamed properly
                    print(f"  📋 Columns: {data.columns.tolist()}")
                    
                    # Show sample data if available
                    if len(data) > 0:
                        first_row = data.iloc[0]
                        if 'name' in data.columns:
                            print(f"  📊 Sample: {first_row.get('name', 'Unknown')}")
                        
                        # Check for the raw variable columns
                        for var in ['b08006_001e', 'b08006_008e']:
                            if var in data.columns:
                                print(f"    {var}: {first_row[var]}")
                else:
                    print(f"  ❌ No data returned")
                    
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                
                # Check if it's a 400 error
                if "400 Client Error" in str(e):
                    print(f"  ℹ️  B08006 not available at {level} level")
        
        print(f"\n{'='*50}")
        print("B08006 Test Complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_b08006_districts()
