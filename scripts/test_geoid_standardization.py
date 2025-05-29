"""
Test script for GEOID standardization in the ACS data pipeline.
"""
import sys
import os
import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from data.acs_data import ACSDataFetcher
from data.geoid_utils import GeoIDStandardizer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_geoid_standardization.log')
    ]
)
logger = logging.getLogger(__name__)

def test_geoid_standardization():
    """Test GEOID standardization with sample data."""
    # Create a test DataFrame with sample data
    test_data = [
        # County
        {'state': '15', 'county': '001', 'name': 'Hawaii County'},
        {'state': '15', 'county': '003', 'name': 'Honolulu County'},
        
        # Tract
        {'state': '15', 'county': '001', 'tract': '020100', 'name': 'Hawaii Tract 201'},
        {'state': '15', 'county': '003', 'tract': '040200', 'name': 'Honolulu Tract 402'},
        
        # Block Group
        {'state': '15', 'county': '001', 'tract': '020100', 'block group': '1', 'name': 'Hawaii BG 1'},
        {'state': '15', 'county': '003', 'tract': '040200', 'block group': '2', 'name': 'Honolulu BG 2'},
        
        # State Lower
        {'state': '15', 'sldlst': '001', 'name': 'House District 1'},
        {'state': '15', 'sldlst': '002', 'name': 'House District 2'},
        
        # State Upper
        {'state': '15', 'sldust': '1', 'name': 'Senate District 1'},
        {'state': '15', 'sldust': '2', 'name': 'Senate District 2'},
    ]
    
    # Convert to DataFrame
    df = pd.DataFrame(test_data)
    
    # Test standardization for each level
    for level in ['county', 'tract', 'block group', 'state_lower', 'state_upper']:
        logger.info(f"\nTesting GEOID standardization for level: {level}")
        
        # Filter rows that have the required columns for this level
        required_cols = GeoIDStandardizer.get_geoid_info(level).get('source_columns', [])
        if not required_cols:
            logger.warning(f"No source columns defined for level: {level}")
            continue
            
        level_df = df.dropna(subset=required_cols).copy()
        
        if level_df.empty:
            logger.warning(f"No test data for level: {level}")
            continue
        
        # Generate GEOIDs
        records = level_df.to_dict('records')
        geoids = [GeoIDStandardizer.standardize_geoid(record, level) for record in records]
        
        # Add to DataFrame for display
        level_df['geoid'] = geoids
        
        # Validate GEOIDs
        valid = [str(GeoIDStandardizer.validate_geoid(geoid, level)) for geoid in geoids]
        level_df['valid'] = valid
        
        # Display results
        logger.info(f"Generated {len(geoids)} GEOIDs for {level}:")
        logger.info(level_df[['name', 'geoid', 'valid']].to_string())
        
        # Check if any GEOIDs are invalid
        if 'False' in valid:
            logger.warning(f"Found invalid GEOIDs for level {level}")
        else:
            logger.info(f"All GEOIDs are valid for level {level}")

if __name__ == "__main__":
    test_geoid_standardization()
