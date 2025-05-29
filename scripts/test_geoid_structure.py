"""
Test script to examine and standardize GEOID structure across different geographic levels.
"""
import os
import sys
import json
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('geoid_test.log')
    ]
)
logger = logging.getLogger(__name__)

class GeoIDTester:
    """Class to test and standardize GEOID structures."""
    
    def __init__(self, census_api_key: str, year: int = 2019):
        """Initialize the tester with Census API key and year."""
        self.census_api_key = census_api_key
        self.year = year
        self.load_map_geojsons()
    
    def load_map_geojsons(self) -> None:
        """Load the map GeoJSON files and examine their structure."""
        self.maps = {}
        map_files = {
            'county': 'data/Processed GeoJsons/hawaii_county_boundaries.geojson',
            'state_lower': 'data/Processed GeoJsons/Hawaii_State_House_Districts_2022.geojson',
            'state_upper': 'data/Processed GeoJsons/Hawaii_State_Senate_Districts_2022.geojson'
        }
        
        for level, filepath in map_files.items():
            try:
                gdf = gpd.read_file(filepath)
                self.maps[level] = {
                    'gdf': gdf,
                    'columns': list(gdf.columns),
                    'sample_ids': gdf.head(3).to_dict('records')
                }
                logger.info(f"Loaded {level} map with columns: {list(gdf.columns)}")
            except Exception as e:
                logger.error(f"Error loading {level} map: {str(e)}")
    
    def get_geoid_info(self) -> Dict:
        """Get information about GEOID structure for each geographic level."""
        return {
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
            },
            'tract': {
                'source_columns': ['state', 'county', 'tract'],
                'format': 'SSCCCTTTTTT',  # State (2) + County (3) + Tract (6)
                'example': '15003020100'  # Hawaii (15) + County (003) + Tract (020100)
            },
            'block group': {
                'source_columns': ['state', 'county', 'tract', 'block group'],
                'format': 'SSCCCTTTTTTB',  # State (2) + County (3) + Tract (6) + Block Group (1)
                'example': '150030201001'  # Hawaii (15) + County (003) + Tract (020100) + BG (1)
            }
        }
    
    def generate_geoid(self, row: Dict, level: str) -> str:
        """Generate a standardized GEOID based on the geographic level."""
        try:
            if level == 'county':
                # Format: SSCCC (State + County)
                state = str(row.get('state', '15')).zfill(2)
                county = str(row.get('county', '')).zfill(3)
                return f"{state}{county}"
                
            elif level == 'tract':
                # Format: SSCCCTTTTTT (State + County + Tract)
                state = str(row.get('state', '15')).zfill(2)
                county = str(row.get('county', '')).zfill(3)
                tract = str(row.get('tract', '')).replace('.', '').ljust(6, '0')[:6]
                return f"{state}{county}{tract}"
                
            elif level == 'block group':
                # Format: SSCCCTTTTTTB (State + County + Tract + Block Group)
                state = str(row.get('state', '15')).zfill(2)
                county = str(row.get('county', '')).zfill(3)
                tract = str(row.get('tract', '')).replace('.', '').ljust(6, '0')[:6]
                bg = str(row.get('block group', '0')).zfill(1)[0]
                return f"{state}{county}{tract}{bg}"
                
            elif level == 'state_lower':
                # Format: SSDDD (State + District)
                state = str(row.get('state', '15')).zfill(2)
                district = str(row.get('sldlst', '')).zfill(3)
                return f"{state}{district}"
                
            elif level == 'state_upper':
                # Format: SSDD (State + District)
                state = str(row.get('state', '15')).zfill(2)
                district = str(row.get('sldust', '')).zfill(2)
                return f"{state}{district}"
                
        except Exception as e:
            logger.error(f"Error generating GEOID for {level}: {str(e)}")
        return ""
    
    def test_geoid_generation(self) -> Dict:
        """Test GEOID generation for each geographic level."""
        results = {}
        
        # Test with sample data
        test_data = {
            'county': {'state': '15', 'county': '003'},
            'tract': {'state': '15', 'county': '003', 'tract': '020100'},
            'block group': {'state': '15', 'county': '003', 'tract': '020100', 'block group': '1'},
            'state_lower': {'state': '15', 'sldlst': '001'},
            'state_upper': {'state': '15', 'sldust': '1'}
        }
        
        for level, data in test_data.items():
            geoid = self.generate_geoid(data, level)
            results[level] = {
                'input': data,
                'geoid': geoid,
                'length': len(geoid) if geoid else 0
            }
            logger.info(f"{level.upper()} - Input: {data} -> GEOID: {geoid}")
        
        return results

def main():
    """Main function to test GEOID structure."""
    # Get API key from environment
    api_key = os.getenv('CENSUS_API_KEY')
    if not api_key:
        logger.error("CENSUS_API_KEY environment variable not set")
        return
    
    # Initialize tester
    tester = GeoIDTester(api_key)
    
    # Get GEOID info
    geoid_info = tester.get_geoid_info()
    logger.info("\nGEOID Structure Information:")
    for level, info in geoid_info.items():
        logger.info(f"\n{level.upper()}:")
        for key, value in info.items():
            logger.info(f"  {key}: {value}")
    
    # Test GEOID generation
    logger.info("\nTesting GEOID Generation:")
    test_results = tester.test_geoid_generation()
    
    # Save results (excluding geometry from samples)
    with open('geoid_test_results.json', 'w') as f:
        # Create a serializable copy of the map samples without geometry
        serializable_samples = {}
        for level, data in tester.maps.items():
            serializable_samples[level] = []
            for item in data['sample_ids']:
                # Create a copy of the item without geometry
                item_copy = {}
                for key, value in item.items():
                    # Skip geometry columns
                    if key != 'geometry' and not key.endswith('_geom'):
                        # Convert any non-serializable types to strings
                        try:
                            json.dumps({key: value})
                            item_copy[key] = value
                        except (TypeError, OverflowError):
                            item_copy[key] = str(value)
                serializable_samples[level].append(item_copy)
        
        # Save the results
        json.dump({
            'geoid_info': geoid_info,
            'test_results': test_results,
            'map_samples': serializable_samples
        }, f, indent=2)
    
    logger.info("\nTest complete. Results saved to geoid_test_results.json")

if __name__ == "__main__":
    main()
