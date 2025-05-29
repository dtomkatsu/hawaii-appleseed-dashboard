"""Debug logging utility for Hawaii Appleseed Dashboard."""
import logging
import os
import json
import pandas as pd
import traceback
from datetime import datetime
from pathlib import Path

# Global loggers
data_logger = None
layer_logger = None
app_logger = None

def setup_debug_logging():
    """Set up debug logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure the data logger
    global data_logger
    data_logger = logging.getLogger('data_debug')
    data_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid duplicates
    for handler in data_logger.handlers[:]: 
        data_logger.removeHandler(handler)
    
    # Create file handler for data debugging
    data_log_file = log_dir / 'data_debug.log'
    data_handler = logging.FileHandler(data_log_file, mode='a')
    data_handler.setLevel(logging.DEBUG)
    data_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    data_logger.addHandler(data_handler)
    
    # Configure the layer selection logger
    global layer_logger
    layer_logger = logging.getLogger('layer_debug')
    layer_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid duplicates
    for handler in layer_logger.handlers[:]: 
        layer_logger.removeHandler(handler)
    
    # Create file handler for layer debugging
    layer_log_file = log_dir / 'layer_debug.log'
    layer_handler = logging.FileHandler(layer_log_file, mode='a')
    layer_handler.setLevel(logging.DEBUG)
    layer_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    layer_logger.addHandler(layer_handler)
    
    # Configure the application logger
    global app_logger
    app_logger = logging.getLogger('app_debug')
    app_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid duplicates
    for handler in app_logger.handlers[:]: 
        app_logger.removeHandler(handler)
    
    # Create file handler for application debugging
    app_log_file = log_dir / 'app_debug.log'
    app_handler = logging.FileHandler(app_log_file, mode='a')
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    app_logger.addHandler(app_handler)
    
    return data_logger, layer_logger, app_logger

def log_layer_selection(layer_name, source='unknown'):
    """Log layer selection events to help track which layer is being selected."""
    _, layer_logger, _ = setup_debug_logging()
    layer_logger.info(f"[{source}] Layer selected: {layer_name}")
    
    # Create a timestamp for the log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    # Log to a separate file for easier tracking
    log_dir = Path(__file__).parent.parent / 'logs'
    log_file = log_dir / 'layer_selection_events.log'
    
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] [{source}] Layer selected: {layer_name}\n")

def log_geojson_loading(geo_level, file_path, success=True, error=None):
    """Log GeoJSON loading events to track file loading issues."""
    data_logger, _, _ = setup_debug_logging()
    
    if success:
        data_logger.info(f"Successfully loaded GeoJSON for {geo_level} from {file_path}")
    else:
        data_logger.error(f"Failed to load GeoJSON for {geo_level} from {file_path}: {error}")
    
    # Log to a separate file for easier tracking
    log_dir = Path(__file__).parent.parent / 'logs'
    log_file = log_dir / 'geojson_loading.log'
    
    with open(log_file, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if success:
            f.write(f"[{timestamp}] SUCCESS: Loaded GeoJSON for {geo_level} from {file_path}\n")
        else:
            f.write(f"[{timestamp}] ERROR: Failed to load GeoJSON for {geo_level} from {file_path}: {error}\n")

def log_error(message, exception=None, source='unknown'):
    """Log error events with detailed information."""
    _, _, app_logger = setup_debug_logging()
    app_logger.error(f"[{source}] {message}")
    
    if exception:
        app_logger.error(f"[{source}] Exception: {str(exception)}")
        app_logger.error(f"[{source}] Traceback: {traceback.format_exc()}")
    
    # Log to a separate file for easier tracking
    log_dir = Path(__file__).parent.parent / 'logs'
    log_file = log_dir / 'error_events.log'
    
    with open(log_file, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        f.write(f"[{timestamp}] [{source}] {message}\n")
        if exception:
            f.write(f"[{timestamp}] [{source}] Exception: {str(exception)}\n")
            f.write(f"[{timestamp}] [{source}] Traceback: {traceback.format_exc()}\n")

def debug_data_join():
    """Debug the data joining process between GeoJSON and CSV data."""
    data_logger, _, _ = setup_debug_logging()
    data_logger.info("Starting data join debugging...")
    
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
