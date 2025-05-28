import os
import sys
import logging
from pathlib import Path
import folium
import geopandas as gpd
from folium.plugins import Fullscreen
import json

# Set up logging with proper encoding for Windows
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Replace checkmark with [OK] for Windows console
            msg = msg.replace('✓', '[OK]').replace('✗', '[ERROR]')
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('map_debug.log', encoding='utf-8'),
        UnicodeStreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_geojson_files():
    """Check if all required GeoJSON files exist."""
    data_dir = Path("data/Processed GeoJsons")
    required_files = [
        'hawaii_state_boundary.geojson',
        'hawaii_county_boundaries.geojson',
        'Hawaii_State_House_Districts_2022.geojson',
        'Hawaii_State_Senate_Districts_2022.geojson'
    ]
    
    missing_files = []
    for file in required_files:
        path = data_dir / file
        if not path.exists():
            missing_files.append(str(path))
    
    if missing_files:
        logger.error(f"Missing GeoJSON files: {', '.join(missing_files)}")
        return False
    return True

def load_geojson(file_path):
    """Load and validate a GeoJSON file."""
    try:
        logger.info(f"Loading GeoJSON: {file_path}")
        gdf = gpd.read_file(file_path)
        
        if gdf.empty:
            logger.error(f"Empty GeoDataFrame in {file_path}")
            return None
            
        # Check and convert CRS to WGS84 (EPSG:4326)
        if gdf.crs is None:
            logger.warning(f"No CRS found in {file_path}, assuming WGS84")
            gdf.crs = 'EPSG:4326'
        elif gdf.crs.to_epsg() != 4326:
            logger.info(f"Converting CRS from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs(epsg=4326)
            
        logger.info(f"Successfully loaded {file_path} with {len(gdf)} features")
        return gdf
        
    except Exception as e:
        logger.error(f"Error loading {file_path}: {str(e)}", exc_info=True)
        return None

def create_simple_map():
    """Create a simple map to test if Folium is working."""
    try:
        logger.info("Creating simple test map...")
        m = folium.Map(location=[20.7984, -156.3319], zoom_start=7)
        folium.Marker(
            location=[21.3069, -157.8583],
            popup='Honolulu',
            tooltip='Click me!'
        ).add_to(m)
        
        # Save to a file
        map_path = 'test_map.html'
        m.save(map_path)
        logger.info(f"Test map saved to {os.path.abspath(map_path)}")
        return True
    except Exception as e:
        logger.error(f"Error creating test map: {str(e)}", exc_info=True)
        return False

def debug_map_loading():
    """Debug map loading issues."""
    logger.info("Starting map debugger...")
    
    # 1. Check Python and package versions
    logger.info("\n=== Python Environment ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Folium version: {folium.__version__}")
    logger.info(f"GeoPandas version: {gpd.__version__}")
    
    # 2. Check GeoJSON files
    logger.info("\n=== Checking GeoJSON Files ===")
    if not check_geojson_files():
        logger.error("Missing required GeoJSON files")
    
    # 3. Try loading each GeoJSON file
    data_dir = Path("data/Processed GeoJsons")
    test_files = {
        'State': data_dir / 'hawaii_state_boundary.geojson',
        'Counties': data_dir / 'hawaii_county_boundaries.geojson',
        'House Districts': data_dir / 'Hawaii_State_House_Districts_2022.geojson',
        'Senate Districts': data_dir / 'Hawaii_State_Senate_Districts_2022.geojson'
    }
    
    for name, file_path in test_files.items():
        logger.info(f"\n--- Testing {name} ---")
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            continue
            
        gdf = load_geojson(file_path)
        if gdf is not None:
            logger.info(f"CRS: {gdf.crs}")
            logger.info(f"Columns: {list(gdf.columns)}")
            logger.info(f"Features: {len(gdf)}")
    
    # 4. Create a simple map to test Folium
    logger.info("\n=== Testing Basic Map Creation ===")
    if create_simple_map():
        logger.info("✓ Basic map creation successful")
    else:
        logger.error("✗ Basic map creation failed")
    
    logger.info("\nDebugging complete. Check map_debug.log for details.")

if __name__ == "__main__":
    debug_map_loading()
