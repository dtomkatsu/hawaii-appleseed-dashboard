"""Data loading utilities for the Hawaii Appleseed Dashboard."""
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)

class DataLoader:
    """Load and manage data for the dashboard."""
    
    def __init__(self, data_dir: str = 'data/processed'):
        """Initialize the data loader with the data directory."""
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / data_dir
        self.data_cache = {}
    
    def load_acs_data(self, geo_level: str) -> Optional[pd.DataFrame]:
        """
        Load ACS data for a specific geographic level.
        
        Args:
            geo_level: One of 'state', 'county', 'house', or 'senate'
            
        Returns:
            DataFrame with the loaded data or None if loading fails
        """
        try:
            file_map = {
                'state': 'hawaii_state_acs_2023.csv',
                'county': 'hawaii_counties_acs_2023.csv',
                'house': 'hawaii_house_districts_acs_2023.csv',
                'senate': 'hawaii_senate_districts_acs_2023.csv'
            }
            
            if geo_level not in file_map:
                logger.error(f"Invalid geographic level: {geo_level}")
                return None
                
            file_path = self.data_dir / file_map[geo_level]
            if not file_path.exists():
                logger.error(f"Data file not found: {file_path}")
                return None
                
            # Read CSV and ensure geoid is string
            df = pd.read_csv(file_path, dtype={'geoid': str})
            
            # Cache the loaded data
            self.data_cache[geo_level] = df
            return df
            
        except Exception as e:
            logger.error(f"Error loading {geo_level} data: {str(e)}")
            return None
    
    def get_data(self, geo_level: str) -> Optional[pd.DataFrame]:
        """
        Get data for a geographic level, using cache if available.
        
        Args:
            geo_level: One of 'state', 'county', 'house', or 'senate'
            
        Returns:
            DataFrame with the data or None if not found
        """
        if geo_level in self.data_cache:
            return self.data_cache[geo_level]
        return self.load_acs_data(geo_level)
    
    def get_geojson_path(self, geo_level: str) -> Optional[Path]:
        """
        Get the path to the GeoJSON file for a geographic level.
        
        Args:
            geo_level: One of 'state', 'county', 'house', or 'senate'
            
        Returns:
            Path to the GeoJSON file or None if not found
        """
        file_map = {
            'state': 'hawaii_state_boundary.geojson',
            'county': 'hawaii_county_boundaries.geojson',
            'house': 'Hawaii_State_House_Districts_2022.geojson',
            'senate': 'Hawaii_State_Senate_Districts_2022.geojson'
        }
        
        if geo_level not in file_map:
            logger.error(f"Invalid geographic level for GeoJSON: {geo_level}")
            return None
        
        # Create a debug log file to track file access issues
        debug_log_path = self.base_dir / 'logs' / 'data_debug.log'
        debug_log_path.parent.mkdir(exist_ok=True)
        
        with open(debug_log_path, 'a') as debug_file:
            debug_file.write(f"\n[{geo_level}] Looking for GeoJSON: {file_map[geo_level]}\n")
            
            # Check if the Processed GeoJsons directory exists
            geojson_dir = self.base_dir / 'data' / 'Processed GeoJsons'
            if not geojson_dir.exists():
                error_msg = f"GeoJSON directory not found: {geojson_dir}"
                logger.error(error_msg)
                debug_file.write(f"ERROR: {error_msg}\n")
                return None
            
            # List all files in the directory for debugging
            debug_file.write(f"Files in {geojson_dir}:\n")
            for file in geojson_dir.iterdir():
                debug_file.write(f"  - {file.name}\n")
            
            # Check for the specific file
            geojson_path = geojson_dir / file_map[geo_level]
            if not geojson_path.exists():
                error_msg = f"GeoJSON file not found: {geojson_path}"
                logger.error(error_msg)
                debug_file.write(f"ERROR: {error_msg}\n")
                return None
            
            debug_file.write(f"SUCCESS: Found GeoJSON at {geojson_path}\n")
            
        return geojson_path
