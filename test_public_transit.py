#!/usr/bin/env python3
"""
Test script for the new public transit variable in ACS data loader.
Tests the variable across all geographic levels (state, county, districts).
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.data.acs_data import ACSDataFetcher
import pandas as pd

def test_public_transit_variable():
    """Test the public transit variable across different geographic levels."""
    
    print("Testing Public Transit Variable Calculation")
    print("=" * 50)
    
    try:
        # Initialize the ACS data fetcher
        fetcher = ACSDataFetcher()
        
        # Get the transportation variables
        transport_variables = ['B08301_001E', 'B08301_010E']  # Total workers, Public transit workers
        
        # Test levels to check
        test_levels = [
            ('county', 'Hawaii Counties'),
            ('state_lower', 'Hawaii House Districts'), 
            ('state_upper', 'Hawaii Senate Districts')
        ]
        
        for level, description in test_levels:
            print(f"\n{description} ({level}):")
            print("-" * 30)
            
            try:
                # Fetch data for this level
                data = fetcher.get_acs_data(
                    variables=transport_variables,
                    level=level,
                    state='15',  # Hawaii
                    geometry=False
                )
                
                if data is not None and not data.empty:
                    # Calculate metrics including public transit rate
                    data = fetcher.calculate_poverty_rate(data)
                    
                    # Check if our new columns exist
                    required_cols = ['total_workers', 'public_transit_workers', 'public_transit_rate']
                    missing_cols = [col for col in required_cols if col not in data.columns]
                    
                    if missing_cols:
                        print(f"  ❌ Missing columns: {missing_cols}")
                    else:
                        print(f"  ✅ All required columns present")
                        print(f"  📊 Records: {len(data)}")
                        
                        # Show sample data
                        if 'name' in data.columns:
                            sample = data[['name', 'total_workers', 'public_transit_workers', 'public_transit_rate']].head(3)
                            print(f"  📋 Sample data:")
                            for _, row in sample.iterrows():
                                name = row['name'][:30] + "..." if len(str(row['name'])) > 30 else row['name']
                                print(f"    {name}: {row['public_transit_rate']:.1f}% ({row['public_transit_workers']}/{row['total_workers']})")
                        
                        # Show summary statistics
                        transit_stats = data['public_transit_rate'].describe()
                        print(f"  📈 Public Transit Rate Stats:")
                        print(f"    Mean: {transit_stats['mean']:.2f}%")
                        print(f"    Min: {transit_stats['min']:.2f}%")
                        print(f"    Max: {transit_stats['max']:.2f}%")
                        
                else:
                    print(f"  ❌ No data returned for {level}")
                    
            except Exception as e:
                print(f"  ❌ Error testing {level}: {str(e)}")
        
        print(f"\n{'='*50}")
        print("✅ Public Transit Variable Test Complete!")
        
    except Exception as e:
        print(f"❌ Error in test: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_public_transit_variable()
    sys.exit(0 if success else 1)
