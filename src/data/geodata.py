"""GeoData handling for the Hawaii Appleseed Dashboard."""
import geopandas as gpd
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

from config import GEOJSON_FILES

logger = logging.getLogger(__name__)

def load_geojson(file_path: Path) -> Optional[gpd.GeoDataFrame]:
    """Load a GeoJSON file into a GeoDataFrame."""
    try:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
            
        logger.info(f"Loading GeoJSON file: {file_path}")
        gdf = gpd.read_file(file_path)
        
        if gdf.empty:
            logger.warning(f"Empty GeoDataFrame: {file_path}")
            return None
            
        # Ensure the CRS is EPSG:4326 (WGS84)
        if gdf.crs is None:
            logger.warning(f"No CRS found in {file_path}, assuming WGS84")
            gdf.crs = 'EPSG:4326'
        elif gdf.crs.to_epsg() != 4326:
            logger.info(f"Converting CRS from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs(epsg=4326)
            
        logger.info(f"Loaded {len(gdf)} features from {file_path}")
        logger.debug(f"Columns: {list(gdf.columns)}")
            
        return gdf
        
    except Exception as e:
        logger.error(f"Error loading {file_path}: {str(e)}", exc_info=True)
        return None

def get_geojson_bounds(gdf: gpd.GeoDataFrame) -> Tuple[float, float, float, float]:
    """Get the bounds of a GeoDataFrame."""
    return gdf.total_bounds  # Returns (min_x, min_y, max_x, max_y)

def get_geojson_files() -> Dict[str, Path]:
    """Get the mapping of layer names to GeoJSON file paths."""
    return GEOJSON_FILES
