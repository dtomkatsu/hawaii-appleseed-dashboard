"""Data loading utilities for the Hawaii Appleseed Dashboard."""
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Optional, Union, List
import datetime
import json

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
            'rent_burden_rate': 'Rent Burden (% paying 30%+ of income on rent)',
            'no_health_insurance': 'No Health Insurance (%)',
            # ALICE variables
            'alice_rate': 'ALICE Households (%)'
        }
        
        # Geographic name mapping for data joining
        self.geo_name_mapping = {
            'county': {
                'Honolulu': 'Oahu',  # ALICE data uses "Honolulu", GeoJSON uses "Oahu"
                'Hawaii': 'Hawaii',
                'Maui': 'Maui', 
                'Kauai': 'Kauai'
            }
        }
        
        # Load all data at initialization to avoid pipeline runs
        self._preload_data()
    
    def _preload_data(self) -> None:
        """Preload all data at initialization to avoid pipeline runs."""
        for geo_level in ['state', 'county', 'house', 'senate']:
            self.load_acs_data(geo_level)
            self.load_alice_data(geo_level)
            
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
    
    def load_alice_data(self, geo_level: str) -> Optional[pd.DataFrame]:
        """
        Load ALICE data for a specific geographic level from Excel file.
        
        Args:
            geo_level: One of 'state', 'county', 'house', or 'senate'
            
        Returns:
            DataFrame with the loaded ALICE data or None if loading fails
        """
        try:
            # Map geo levels to Excel sheet names
            sheet_map = {
                'state': 'State',
                'county': 'Counties', 
                'house': 'House',
                'senate': 'Senate'
            }
            
            if geo_level not in sheet_map:
                logger.error(f"Invalid geographic level for ALICE data: {geo_level}")
                return None
                
            # Look for ALICE Excel file in data directory
            alice_file_path = self.base_dir / 'data' / 'ALICE By Geography (2023).xlsx'
            if not alice_file_path.exists():
                logger.warning(f"ALICE data file not found: {alice_file_path}")
                return None
                
            # Read the specific sheet
            sheet_name = sheet_map[geo_level]
            df = pd.read_excel(alice_file_path, sheet_name=sheet_name)
            
            logger.debug(f"Loaded ALICE {geo_level} data with columns: {list(df.columns)}")
            logger.debug(f"ALICE {geo_level} data shape: {df.shape}")
            
            # Standardize column names and add geo identifier
            df = self._standardize_alice_data(df, geo_level)
            
            # Cache the loaded data with ALICE prefix
            cache_key = f"alice_{geo_level}"
            self.data_cache[cache_key] = df
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading ALICE {geo_level} data: {str(e)}")
            return None
    
    def _standardize_alice_data(self, df: pd.DataFrame, geo_level: str) -> pd.DataFrame:
        """
        Standardize ALICE data columns and add geographic identifiers.
        
        Args:
            df: Raw ALICE DataFrame
            geo_level: Geographic level
            
        Returns:
            Standardized DataFrame
        """
        df = df.copy()
        
        # Rename the ALICE percentage column to a standard name
        if 'Percentage of Households Under ALICE Threshold' in df.columns:
            df['alice_rate'] = df['Percentage of Households Under ALICE Threshold'] * 100  # Convert to percentage
            
        if geo_level == 'state':
            # For state level, add consistent naming
            df['name'] = 'Hawaii'
            df['display_name'] = 'Hawaii'
            
        elif geo_level == 'county':
            # For counties, standardize names for joining
            if 'County' in df.columns:
                df['county_raw'] = df['County']
                # Apply name mapping for consistency with GeoJSON
                df['county_name'] = df['County'].map(
                    lambda x: self.geo_name_mapping['county'].get(x, x)
                )
                df['display_name'] = df['county_name']
                df['name'] = df['County']  # Keep original for joining with ALICE data
                
        elif geo_level == 'house':
            # For house districts, ensure district numbers are integers
            if 'District' in df.columns:
                df['district'] = df['District'].astype(int)
                df['house_id'] = df['District'].astype(int)
                df['display_name'] = df['District'].apply(lambda x: f"House District {x}")
                df['name'] = df['District'].apply(lambda x: f"State House District {x} (2022); Hawaii")
                
        elif geo_level == 'senate':
            # For senate districts, ensure district numbers are integers
            if 'Senate District' in df.columns:
                df['district'] = df['Senate District'].astype(int)
                df['senate_id'] = df['Senate District'].astype(int)
                df['display_name'] = df['Senate District'].apply(lambda x: f"Senate District {x}")
                df['name'] = df['Senate District'].apply(lambda x: f"State Senate District {x} (2022); Hawaii")
        
        logger.debug(f"Standardized ALICE {geo_level} data columns: {list(df.columns)}")
        return df
    
    def get_data(self, geo_level: str) -> Optional[pd.DataFrame]:
        """
        Get combined ACS and ALICE data for a geographic level.
        
        Args:
            geo_level: One of 'state', 'county', 'house', or 'senate'
            
        Returns:
            DataFrame with merged ACS and ALICE data or None if not found
        """
        # Get ACS data
        acs_data = self.data_cache.get(geo_level)
        if acs_data is None:
            acs_data = self.load_acs_data(geo_level)
        
        # Get ALICE data
        alice_cache_key = f"alice_{geo_level}"
        alice_data = self.data_cache.get(alice_cache_key)
        if alice_data is None:
            alice_data = self.load_alice_data(geo_level)
        
        # If we have both datasets, merge them
        if acs_data is not None and alice_data is not None:
            merged_data = self._merge_datasets(acs_data, alice_data, geo_level)
            return merged_data
        elif acs_data is not None:
            logger.warning(f"Only ACS data available for {geo_level}")
            return acs_data
        elif alice_data is not None:
            logger.warning(f"Only ALICE data available for {geo_level}")
            return alice_data
        else:
            logger.error(f"No data available for {geo_level}")
            return None
    
    def _merge_datasets(self, acs_data: pd.DataFrame, alice_data: pd.DataFrame, geo_level: str) -> pd.DataFrame:
        """
        Merge ACS and ALICE datasets on appropriate join keys.
        
        Args:
            acs_data: ACS DataFrame
            alice_data: ALICE DataFrame
            geo_level: Geographic level
            
        Returns:
            Merged DataFrame
        """
        acs_df = acs_data.copy()
        alice_df = alice_data.copy()
        
        logger.debug(f"Merging {geo_level} data: ACS shape {acs_df.shape}, ALICE shape {alice_df.shape}")
        
        # Define join strategies by geographic level
        if geo_level == 'state':
            # Simple merge for state level
            merged = acs_df.copy()
            try:
                if 'alice_rate' in alice_df.columns and len(alice_df) > 0:
                    merged['alice_rate'] = alice_df['alice_rate'].iloc[0]
                else:
                    merged['alice_rate'] = None
            except Exception as e:
                logger.error(f"Error merging state ALICE data: {e}")
                merged['alice_rate'] = None
                
        elif geo_level == 'county':
            # County names need special handling due to Honolulu/Oahu mismatch
            join_key = 'NAME'
            alice_join_key = 'name'
            
            # Create mapping for county names
            county_mapping = {
                'Honolulu County, Hawaii': ['Honolulu', 'Oahu'],
                'Hawaii County, Hawaii': ['Hawaii'],
                'Maui County, Hawaii': ['Maui'],
                'Kauai County, Hawaii': ['Kauai']
            }
            
            merged = acs_df.copy()
            merged['alice_rate'] = None
            
            # Manual join based on county mapping
            try:
                for acs_idx, acs_row in acs_df.iterrows():
                    acs_county_name = acs_row[join_key]
                    
                    # Find matching ALICE data
                    for alice_idx, alice_row in alice_df.iterrows():
                        alice_county = alice_row[alice_join_key]
                        
                        # Check if this ALICE county matches the ACS county
                        if acs_county_name in county_mapping:
                            if alice_county in county_mapping[acs_county_name]:
                                merged.loc[acs_idx, 'alice_rate'] = alice_row['alice_rate']
                                logger.debug(f"Matched {acs_county_name} with ALICE {alice_county}")
                                break
            except Exception as e:
                logger.error(f"Error during county data merge: {e}")
                # If merging fails, at least return the ACS data
                pass
                            
        elif geo_level in ['house', 'senate']:
            # Districts can join on district number
            if geo_level == 'house':
                acs_join_key = 'state legislative district (lower chamber)'
                alice_join_key = 'district'
            else:  # senate
                acs_join_key = 'state legislative district (upper chamber)'
                alice_join_key = 'district'
            
            # Try different possible column names for district matching
            possible_acs_keys = [acs_join_key, 'district', 'DISTRICT']
            actual_acs_key = None
            
            for key in possible_acs_keys:
                if key in acs_df.columns:
                    actual_acs_key = key
                    break
            
            if actual_acs_key and alice_join_key in alice_df.columns:
                try:
                    merged = pd.merge(
                        acs_df, 
                        alice_df[['district', 'alice_rate']], 
                        left_on=actual_acs_key, 
                        right_on='district', 
                        how='left'
                    )
                    logger.debug(f"Merged {geo_level} on {actual_acs_key} = {alice_join_key}")
                except Exception as e:
                    logger.error(f"Error merging {geo_level} data: {e}")
                    merged = acs_df.copy()
                    merged['alice_rate'] = None
            else:
                logger.warning(f"Could not find matching columns for {geo_level} merge")
                merged = acs_df.copy()
                merged['alice_rate'] = None
                
        else:
            logger.warning(f"Unknown geo_level for merging: {geo_level}")
            merged = acs_df.copy()
            merged['alice_rate'] = None
        
        logger.debug(f"Merged data shape: {merged.shape}, columns: {list(merged.columns)}")
        return merged
        
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
                'source_field': 'county_name',
                'target_field': 'GEOID',
                'converter': lambda x: self._get_county_fips(x)  # Convert county name to FIPS
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
                    
                    # Special handling for Oahu/Honolulu County
                    if geo_level == 'county' and ('oahu' in str(source_id).lower() or 'honolulu' in str(source_id).lower()):
                        # Ensure we use the correct name and FIPS code
                        props['county_name'] = 'Honolulu County, Hawaii'
                        props['county_fips'] = '003'  # Without state prefix
                        props['state_fips'] = '15'
                        logger.debug(f"Standardized Oahu/Honolulu county name and FIPS code")
                    
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
            f.write(f"CSV IDs (first 5): {csv_ids[:5]}\n")
            
            # Create a detailed log file for debugging
            debug_dir = self.base_dir / 'logs' / 'debug'
            debug_dir.mkdir(parents=True, exist_ok=True)
            detailed_log = debug_dir / f'county_matching_debug_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            
            with open(detailed_log, 'w') as detail_f:
                detail_f.write(f"=== County Matching Debug Log ===\n")
                detail_f.write(f"Time: {datetime.datetime.now()}\n\n")
                detail_f.write(f"GeoJSON IDs: {converted_ids}\n\n")
                detail_f.write(f"CSV IDs: {csv_ids}\n\n")
                detail_f.write(f"Matches: {list(matches)}\n\n")
                
                # Log any missing matches
                missing = set(csv_ids) - set(converted_ids)
                if missing:
                    detail_f.write(f"Missing IDs (in CSV but not in GeoJSON): {list(missing)}\n\n")
                
                extra = set(converted_ids) - set(csv_ids)
                if extra:
                    detail_f.write(f"Extra IDs (in GeoJSON but not in CSV): {list(extra)}\n\n")
            
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
        
    def _get_county_fips(self, county_name: str) -> str:
        """
        Convert a county name to its FIPS code with detailed logging.
        
        Args:
            county_name: The name of the county as it appears in the GeoJSON
            
        Returns:
            The FIPS code as a string
        """
        if not county_name:
            logger.warning("Empty county name provided to _get_county_fips")
            return '15000'  # Default FIPS code for unknown county
            
        county_name = str(county_name).lower()
        logger.debug(f"Converting county name to FIPS: {county_name}")
        
        # Create a debug log file for county name conversions
        debug_dir = self.base_dir / 'logs'
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_log = debug_dir / 'county_fips_conversion.log'
        
        with open(debug_log, 'a') as f:
            f.write(f"\n[{datetime.datetime.now()}] Converting county: '{county_name}'\n")
        
        # Define county name patterns and their corresponding FIPS codes
        county_map = [
            ('oahu', '15003'),  # Oahu is Honolulu County
            ('honolulu', '15003'),
            ('hawaii', '15001'),
            ('maui', '15009'),
            ('kauai', '15007'),
            ('kalawao', '15005')
        ]
        
        # Find the first matching pattern
        for pattern, fips in county_map:
            if pattern in county_name:
                logger.debug(f"Matched county name '{county_name}' to FIPS {fips} using pattern '{pattern}'")
                with open(debug_log, 'a') as f:
                    f.write(f"  Matched to FIPS {fips} using pattern '{pattern}'\n")
                return fips
                
        # If no match found, log a warning and return a default FIPS code
        logger.warning(f"No FIPS code match found for county: {county_name}")
        with open(debug_log, 'a') as f:
            f.write(f"  WARNING: No match found for '{county_name}'\n")
        return '15000'  # Default FIPS code for unknown county
        
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
    
    def merge_geojson_with_data(self, geojson_data: dict, geo_level: str) -> dict:
        """
        Enhanced method to merge GeoJSON with both ACS and ALICE data.
        
        Args:
            geojson_data: GeoJSON data as dictionary
            geo_level: Geographic level
            
        Returns:
            GeoJSON data with merged attributes
        """
        try:
            # Get merged ACS + ALICE data
            data = self.get_data(geo_level)
            if data is None:
                logger.warning(f"No data available for merging with {geo_level} GeoJSON")
                return geojson_data
            
            logger.debug(f"Merging GeoJSON with data containing columns: {list(data.columns)}")
            
            # Process each feature in the GeoJSON
            for feature in geojson_data.get('features', []):
                properties = feature.get('properties', {})
                
                # Find matching data based on geographic level
                try:
                    matching_data = self._find_matching_data(properties, data, geo_level)
                    
                    if matching_data is not None:
                        # Add all data columns to the feature properties
                        for key, value in matching_data.items():
                            # Skip certain columns that shouldn't be in properties
                            if key not in ['index', 'level_0'] and value is not None:
                                # Handle pandas NaN values
                                if pd.isna(value):
                                    properties[key] = None
                                else:
                                    properties[key] = value
                                
                        logger.debug(f"Added {len(matching_data)} data fields to feature")
                    else:
                        logger.warning(f"No matching data found for feature in {geo_level}")
                except Exception as e:
                    logger.error(f"Error processing feature in {geo_level}: {e}")
                    continue
            
            return geojson_data
            
        except Exception as e:
            logger.error(f"Error in merge_geojson_with_data for {geo_level}: {e}")
            return geojson_data
    
    def _find_matching_data(self, properties: dict, data: pd.DataFrame, geo_level: str) -> Optional[dict]:
        """
        Find matching data row for a GeoJSON feature.
        
        Args:
            properties: Feature properties from GeoJSON
            data: Data DataFrame
            geo_level: Geographic level
            
        Returns:
            Dictionary of matching data or None
        """
        if geo_level == 'state':
            # State level - just return the first (and only) row
            if len(data) > 0:
                return data.iloc[0].to_dict()
                
        elif geo_level == 'county':
            # County matching with name variations
            county_name = properties.get('county_name', properties.get('NAME', ''))
            
            # Try multiple matching strategies
            matching_strategies = [
                ('NAME', county_name),  # Direct name match
                ('NAME', f"{county_name} County, Hawaii"),  # Add county suffix
            ]
            
            # Special case for Oahu/Honolulu
            if 'oahu' in county_name.lower():
                matching_strategies.extend([
                    ('NAME', 'Honolulu County, Hawaii'),
                    ('NAME', 'Honolulu')
                ])
            
            for col, value in matching_strategies:
                if col in data.columns:
                    matches = data[data[col] == value]
                    if len(matches) > 0:
                        logger.debug(f"Matched county using {col}={value}")
                        return matches.iloc[0].to_dict()
            
            # Try case-insensitive matching
            for col, value in matching_strategies:
                if col in data.columns:
                    matches = data[data[col].str.lower() == value.lower()]
                    if len(matches) > 0:
                        logger.debug(f"Matched county using case-insensitive {col}={value}")
                        return matches.iloc[0].to_dict()
                        
        elif geo_level in ['house', 'senate']:
            # District matching by number
            district_num = None
            
            # Try different ways to get district number
            for field in ['DISTRICT', 'house_id', 'senate_id', 'district']:
                if field in properties:
                    district_num = properties[field]
                    break
            
            if district_num is not None:
                # Try matching on different column names
                for col in ['district', 'state legislative district (lower chamber)', 
                           'state legislative district (upper chamber)']:
                    if col in data.columns:
                        matches = data[data[col] == district_num]
                        if len(matches) > 0:
                            logger.debug(f"Matched {geo_level} district {district_num} using {col}")
                            return matches.iloc[0].to_dict()
        
        return None
