"""Data loading utilities for the Hawaii Appleseed Dashboard."""
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Optional, Union
import datetime

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
        
        # Create logs directory if it doesn't exist
        logs_dir = Path(self.base_dir) / 'logs'
        logs_dir.mkdir(exist_ok=True)
        debug_log = logs_dir / 'id_conversion.log'
        
        # Write header to debug log
        with open(debug_log, 'a') as f:
            f.write(f"\n\n==== ID Conversion for {geo_level} at {datetime.datetime.now()} ====\n")
        
        # Load the CSV data to check against
        csv_data = self.load_acs_data(geo_level)
        if csv_data is not None:
            csv_ids = csv_data['geoid'].astype(str).tolist()
            with open(debug_log, 'a') as f:
                f.write(f"CSV IDs (first 5): {csv_ids[:5]}\n")
                f.write(f"CSV columns: {list(csv_data.columns)}\n")
        else:
            csv_ids = []
            with open(debug_log, 'a') as f:
                f.write(f"No CSV data found for {geo_level}\n")
        
        # Map of geo levels to their ID fields and conversion functions
        id_config = {
            'state': {
                'source_field': 'state_fips',
                'target_field': 'GEOID',
                'converter': lambda x: '15'  # Hawaii state FIPS code
            },
            'county': {
                'source_field': 'county',
                'target_field': 'GEOID',
                'converter': lambda x: '15' + str(x).zfill(3)  # 15 + 3-digit county FIPS
            },
            'house': {
                'source_field': 'state_house',
                'target_field': 'GEOID',
                'converter': lambda x: '15' + str(x).replace('H', '').zfill(3)  # Convert H01 to 15001
            },
            'senate': {
                'source_field': 'state_senate',
                'target_field': 'GEOID',
                'converter': lambda x: '15' + str(x).replace('S', '').zfill(3)  # Convert S01 to 15001
            }
        }
        
        # Special case handling for each geo level
        if geo_level == 'house':
            # Try to find the right source field by checking what's available
            features = geojson_data.get('features', [])
            if features:
                props = features[0].get('properties', {})
                with open(debug_log, 'a') as f:
                    f.write(f"House district properties: {list(props.keys())}\n")
                
                # Check for different possible field names
                for field in ['state_house', 'STATE_HOUSE', 'house_id', 'HOUSE_ID', 'DISTRICT', 'district']:
                    if field in props:
                        id_config['house']['source_field'] = field
                        with open(debug_log, 'a') as f:
                            f.write(f"Using source field '{field}' for house districts\n")
                        break
        
        elif geo_level == 'senate':
            # Try to find the right source field by checking what's available
            features = geojson_data.get('features', [])
            if features:
                props = features[0].get('properties', {})
                with open(debug_log, 'a') as f:
                    f.write(f"Senate district properties: {list(props.keys())}\n")
                
                # Check for different possible field names
                for field in ['state_senate', 'STATE_SENATE', 'senate_id', 'SENATE_ID', 'DISTRICT', 'district']:
                    if field in props:
                        id_config['senate']['source_field'] = field
                        with open(debug_log, 'a') as f:
                            f.write(f"Using source field '{field}' for senate districts\n")
                        break
        
        config = id_config.get(geo_level)
        if not config:
            logger.warning(f"No ID configuration found for geo_level: {geo_level}")
            return geojson_data
            
        source_field = config['source_field']
        target_field = config['target_field']
        converter = config['converter']
        
        logger.debug(f"Mapping {source_field} -> {target_field} for {geo_level}")
        
        # Log the first few features' properties for debugging
        features = geojson_data.get('features', [])
        if features:
            sample_props = features[0].get('properties', {})
            logger.debug(f"Sample feature properties: {list(sample_props.keys())}")
            with open(debug_log, 'a') as f:
                f.write(f"Sample feature properties: {list(sample_props.keys())}\n")
            
        # Track if we found and modified any features
        modified_count = 0
        converted_ids = []
        
        # Update each feature's properties with the standardized ID
        for feature in features:
            props = feature.get('properties', {})
            if source_field in props:
                try:
                    # Convert the source ID to the target format
                    source_id = props[source_field]
                    target_id = converter(source_id)
                    props[target_field] = target_id
                    
                    # Also add a 'geoid' field to match CSV directly
                    props['geoid'] = target_id
                    
                    modified_count += 1
                    converted_ids.append(target_id)
                    
                    # Log the first few conversions for debugging
                    if modified_count <= 5:
                        logger.debug(f"Converted {source_field}={source_id} -> {target_field}={target_id}")
                        with open(debug_log, 'a') as f:
                            f.write(f"Converted {source_field}={source_id} -> {target_field}={target_id}\n")
                except Exception as e:
                    logger.error(f"Error converting ID for {geo_level} with {source_field}={props.get(source_field)}: {str(e)}")
                    with open(debug_log, 'a') as f:
                        f.write(f"ERROR: {str(e)} when converting {source_field}={props.get(source_field)}\n")
        
        logger.debug(f"Standardized {modified_count} features by adding {target_field}")
        with open(debug_log, 'a') as f:
            f.write(f"Standardized {modified_count} features by adding {target_field}\n")
        
        # Check for matches between converted IDs and CSV IDs
        matches = set(converted_ids).intersection(set(csv_ids))
        with open(debug_log, 'a') as f:
            f.write(f"Matches between GeoJSON and CSV: {len(matches)} out of {len(converted_ids)} features\n")
            f.write(f"Converted IDs (first 5): {converted_ids[:5]}\n")
            if len(matches) > 0:
                f.write(f"Matching IDs (first 5): {list(matches)[:5]}\n")
            else:
                f.write("NO MATCHES FOUND!\n")
        
        # Verify the first feature has the new field
        if features and modified_count > 0:
            sample_props = features[0].get('properties', {})
            logger.debug(f"First feature now has properties: {list(sample_props.keys())}")
            with open(debug_log, 'a') as f:
                f.write(f"First feature now has properties: {list(sample_props.keys())}\n")
                f.write(f"First feature GEOID: {sample_props.get(target_field, 'Not found')}\n")
                f.write(f"First feature geoid: {sample_props.get('geoid', 'Not found')}\n")
        
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
