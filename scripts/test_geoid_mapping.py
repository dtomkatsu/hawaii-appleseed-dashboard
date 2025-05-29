"""
Test script to examine GEOID structure from cenpy and match with existing map files.
"""
import os
import sys
import json
import geopandas as gpd
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from data.acs_data import ACSDataFetcher

def test_geoid_structure():
    """Test the structure of GEOIDs from cenpy and compare with map files."""
    api_key = os.getenv('CENSUS_API_KEY')
    if not api_key:
        print("Error: CENSUS_API_KEY environment variable not set")
        return

    # Initialize the ACS fetcher
    acs = ACSDataFetcher(api_key=api_key, year=2019)
    
    # Test with a minimal set of variables
    test_vars = ['B01001_001E']  # Total population
    
    # Test different geographic levels
    test_levels = [
        ('county', '15'),
        ('state_lower', '15'),
        ('state_upper', '15')
    ]
    
    results = {}
    
    for level, state in test_levels:
        print(f"\nTesting {level} level...")
        try:
            # Get data from cenpy
            gdf = acs.get_acs_data(
                variables=test_vars,
                level=level,
                state=state,
                geometry=False  # Don't need geometry for this test
            )
            
            if gdf is not None and not gdf.empty:
                # Get sample of GEOIDs and column names
                sample = gdf.head(3).copy()
                sample_geoids = sample['GEOID'].tolist() if 'GEOID' in sample.columns else "No GEOID column"
                
                results[level] = {
                    'columns': list(gdf.columns),
                    'sample_geoids': sample_geoids,
                    'row_count': len(gdf)
                }
                
                print(f"Columns: {list(gdf.columns)}")
                print(f"Sample GEOIDs: {sample_geoids}")
                print(f"Total rows: {len(gdf)}")
            else:
                print(f"No data returned for {level}")
                
        except Exception as e:
            print(f"Error testing {level}: {str(e)}")
    
    # Save results for reference
    with open('geoid_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nTest complete. Results saved to geoid_test_results.json")
    return results

def map_geoid_requirements():
    """Document the GEOID requirements for each geographic level."""
    requirements = {
        'county': {
            'source_columns': ['state', 'county'],
            'target_columns': ['state_fips', 'county_fips'],
            'format': 'SSCCC',  # State (2) + County (3)
            'example': '15003'   # Hawaii (15) + County (003)
        },
        'state_lower': {
            'source_columns': ['sldlst'],
            'target_columns': ['house_id'],
            'format': 'SSDDD',  # State (2) + District (3)
            'example': '15001'   # Hawaii (15) + District (001)
        },
        'state_upper': {
            'source_columns': ['sldust'],
            'target_columns': ['senate_id'],
            'format': 'SSDD',    # State (2) + District (2)
            'example': '151'     # Hawaii (15) + District (1)
        }
    }
    
    print("\nGEOID Requirements by Level:")
    for level, req in requirements.items():
        print(f"\n{level.upper()}:")
        print(f"  Source columns: {req['source_columns']}")
        print(f"  Target columns: {req['target_columns']}")
        print(f"  Format: {req['format']}")
        print(f"  Example: {req['example']}")
    
    return requirements

if __name__ == "__main__":
    print("Testing GEOID structure from cenpy...")
    test_geoid_structure()
    
    print("\nDocumenting GEOID requirements...")
    map_geoid_requirements()
