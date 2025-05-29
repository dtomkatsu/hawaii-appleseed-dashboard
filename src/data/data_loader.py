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
        
        # Define common ACS variables and their display names
        self.available_variables = {
            'poverty_rate': 'Poverty Rate (%)',
            'median_income': 'Median Household Income ($)',
            'population': 'Total Population',
            'median_age': 'Median Age',
            'bachelors_degree': 'Bachelor\'s Degree or Higher (%)',
            'unemployment_rate': 'Unemployment Rate (%)',
            'median_rent': 'Median Rent ($)',
            'median_home_value': 'Median Home Value ($)',
            'renter_occupied': 'Renter-Occupied Housing (%)',
            'no_health_insurance': 'No Health Insurance (%)'
        }
        
        # Load all data at initialization to avoid pipeline runs
        self._preload_data()
    
    def _preload_data(self) -> None:
        """Preload all data at initialization to avoid pipeline runs."""
        for geo_level in ['state', 'county', 'house', 'senate']:
            self.load_acs_data(geo_level)
            
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
            
            # Add log entry for debugging
            logger.debug(f"Loaded {geo_level} data with columns: {list(df.columns)}")
            
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
        
    def get_available_variables(self) -> Dict[str, str]:
        """
        Get a dictionary of available variables and their display names.
        
        Returns:
            Dictionary mapping variable names to display names
        """
        return self.available_variables
        
    def get_variable_values(self, geo_level: str, variable: str) -> Optional[pd.Series]:
        """
        Get the values for a specific variable at a geographic level.
        
        Args:
            geo_level: One of 'state', 'county', 'house', or 'senate'
            variable: The variable name to retrieve
            
        Returns:
            Series with the variable values or None if not found
        """
        df = self.get_data(geo_level)
        if df is None or variable not in df.columns:
            if df is not None:
                logger.error(f"Variable {variable} not found in {geo_level} data. Available columns: {list(df.columns)}")
            return None
        return df[variable]
    
    def _standardize_geojson_ids(self, geojson_data: dict, geo_level: str) -> dict:
        """
        Standardize ID fields in GeoJSON data to match CSV data.
        
        Args:
            geojson_data: The GeoJSON data as a dictionary
            geo_level: The geographic level ('state', 'county', 'house', 'senate')
            
        Returns:
            The GeoJSON data with standardized ID fields
        """
        logger.debug(f"Standardizing GeoJSON IDs for {geo_level} level")
        
        # Map of geo levels to their ID fields
        id_field_map = {
            'state': ('state_fips', 'GEOID'),
            'county': ('county_fips', 'GEOID'),
            'house': ('house_id', 'GEOID'),
            'senate': ('senate_id', 'GEOID')
        }
        
        source_field, target_field = id_field_map.get(geo_level, (None, None))
        if not source_field or not target_field:
            logger.warning(f"No ID field mapping found for geo_level: {geo_level}")
            return geojson_data
        
        logger.debug(f"Mapping {source_field} -> {target_field} for {geo_level}")
        
        # Log the first few features' properties for debugging
        features = geojson_data.get('features', [])
        if features:
            sample_props = features[0].get('properties', {})
            logger.debug(f"Sample feature properties: {list(sample_props.keys())}")
            
        # Track if we found and modified any features
        modified_count = 0
        
        # Update each feature's properties
        for feature in features:
            props = feature.get('properties', {})
            if source_field in props:
                props[target_field] = str(props[source_field])
                modified_count += 1
                
        logger.debug(f"Standardized {modified_count} features by adding {target_field}")
        
        # Verify the first feature has the new field
        if features and modified_count > 0:
            sample_props = features[0].get('properties', {})
            logger.debug(f"First feature now has properties: {list(sample_props.keys())}")
                
        return geojson_data
        
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
