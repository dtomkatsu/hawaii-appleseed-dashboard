"""Debug logging utility for Hawaii Appleseed Dashboard."""
import logging
import os
import json
import pandas as pd
from pathlib import Path

def setup_debug_logging():
    """Set up debug logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure the logger
    logger = logging.getLogger('debug')
    logger.setLevel(logging.DEBUG)
    
    # Create file handler
    log_file = log_dir / 'data_debug.log'
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

def debug_data_join():
    """Debug the data joining process between GeoJSON and CSV data."""
    logger = setup_debug_logging()
    logger.info("Starting data join debugging...")
    
    # Base directory
    base_dir = Path(__file__).parent.parent
    
    # Load GeoJSON files
    geojson_dir = base_dir / 'data' / 'Processed GeoJsons'
    geojson_files = {
        'state': 'hawaii_state_boundary.geojson',
        'county': 'hawaii_county_boundaries.geojson',
        'house': 'Hawaii_State_House_Districts_2022.geojson',
        'senate': 'Hawaii_State_Senate_Districts_2022.geojson'
    }
    
    # Load CSV files
    csv_dir = base_dir / 'data' / 'processed'
    csv_files = {
        'state': 'hawaii_state_acs_2023.csv',
        'county': 'hawaii_counties_acs_2023.csv',
        'house': 'hawaii_house_districts_acs_2023.csv',
        'senate': 'hawaii_senate_districts_acs_2023.csv'
    }
    
    # ID field mapping
    id_field_map = {
        'state': 'state_fips',
        'county': 'county_fips',
        'house': 'house_id',
        'senate': 'senate_id'
    }
    
    # Check each geographic level
    for geo_level, geojson_file in geojson_files.items():
        logger.info(f"Checking {geo_level} level...")
        
        # Load GeoJSON
        try:
            geojson_path = geojson_dir / geojson_file
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            # Get the ID field for this level
            id_field = id_field_map.get(geo_level)
            
            # Extract IDs from GeoJSON
            geojson_ids = []
            for feature in geojson_data.get('features', []):
                feature_id = feature.get('properties', {}).get(id_field)
                if feature_id:
                    geojson_ids.append(str(feature_id))
            
            logger.info(f"GeoJSON {geo_level} IDs: {geojson_ids[:5]}...")
            logger.info(f"GeoJSON {geo_level} properties: {list(geojson_data['features'][0]['properties'].keys())}")
            
            # Load CSV
            csv_path = csv_dir / csv_files.get(geo_level)
            df = pd.read_csv(csv_path)
            
            # Extract IDs from CSV
            csv_ids = df['geoid'].astype(str).tolist()
            
            logger.info(f"CSV {geo_level} IDs: {csv_ids[:5]}...")
            logger.info(f"CSV {geo_level} columns: {df.columns.tolist()}")
            
            # Check for matches
            matches = set(geojson_ids).intersection(set(csv_ids))
            logger.info(f"Matching IDs: {len(matches)} out of {len(geojson_ids)} GeoJSON features and {len(csv_ids)} CSV rows")
            
            if len(matches) == 0:
                # Try different formats
                logger.info("No direct matches found. Trying different formats...")
                
                # Try without leading zeros
                geojson_ids_no_zeros = [id.lstrip('0') for id in geojson_ids]
                matches = set(geojson_ids_no_zeros).intersection(set(csv_ids))
                logger.info(f"Matches without leading zeros: {len(matches)}")
                
                # Try last 5 digits
                geojson_ids_last5 = [id[-5:] if len(id) > 5 else id for id in geojson_ids]
                matches = set(geojson_ids_last5).intersection(set(csv_ids))
                logger.info(f"Matches with last 5 digits: {len(matches)}")
                
                # Log sample values for debugging
                logger.info(f"Sample GeoJSON IDs: {geojson_ids[:5]}")
                logger.info(f"Sample GeoJSON IDs (no zeros): {geojson_ids_no_zeros[:5]}")
                logger.info(f"Sample GeoJSON IDs (last 5): {geojson_ids_last5[:5]}")
                logger.info(f"Sample CSV IDs: {csv_ids[:5]}")
            
        except Exception as e:
            logger.error(f"Error processing {geo_level}: {str(e)}")
    
    logger.info("Data join debugging complete.")

if __name__ == "__main__":
    debug_data_join()
