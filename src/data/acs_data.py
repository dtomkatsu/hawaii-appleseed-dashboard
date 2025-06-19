"""
ACS Data Pipeline for Hawaii Appleseed Dashboard
Uses direct Census API calls to fetch ACS data
"""
import os
import pandas as pd
import geopandas as gpd
import logging
import requests
import json
import time
from typing import List, Dict, Optional, Union
from .geoid_utils import GeoIDStandardizer
from pathlib import Path
import numpy as np
import warnings
import traceback
from urllib.parse import urlencode, quote

warnings.filterwarnings('ignore', category=UserWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ACSDataFetcher:
    """Fetches ACS data from the Census API directly."""
    
    def __init__(self, api_key: str = None, year: int = 2023):
        """Initialize the ACS data fetcher.
        
        Args:
            api_key: Census API key
            year: ACS year (default: 2023)
        """
        # Set up API URL and year
        self.year = year
        self.base_url = f"https://api.census.gov/data/{self.year}/acs/acs5"
        
        # Set up directories
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir.parent / 'data'
        self.processed_dir = self.data_dir / 'processed'
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a debug log file
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True, parents=True)
        self.debug_log_file = self.logs_dir / "census_api_debug.log"
        
        # Log initialization
        with open(self.debug_log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Initializing ACSDataFetcher for {self.year} ACS 5-year estimates ---\n")
            f.write(f"Base URL: {self.base_url}\n")
        
        # Set and validate the API key
        self.api_key = api_key or "2104852dd7bfd83fbc9e320d650eb57decc11817"  # Using provided key or default
        self.api_key = self._validate_api_key(self.api_key)
        
        # Test the connection
        self._test_connection()
        
        # Log initialization
        with open(self.debug_log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Initializing ACSDataFetcher for {self.year} ACS 5-year estimates ---\n")
            f.write(f"Base URL: {self.base_url}\n")
        
        # Test the connection
        self._test_connection()
    
    def _validate_api_key(self, api_key: str) -> str:
        """Validate and format the Census API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            The validated and formatted API key
            
        Raises:
            ValueError: If the API key is invalid
        """
        # Remove any whitespace
        api_key = api_key.strip()
        
        # Check if the API key is empty
        if not api_key:
            raise ValueError("Census API key cannot be empty")
            
        # Log that we're using a valid API key (without showing the key)
        logger.info(f"Using Census API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
        
        return api_key
    
    def _test_connection(self) -> None:
        """Test the connection to the Census API.
        
        Raises:
            ConnectionError: If the connection cannot be established
        """
        try:
            # Make a simple request to test the API key
            params = {
                'get': 'NAME',
                'for': 'state:*',
                'key': self.api_key
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse the response to ensure it's valid
            data = response.json()
            
            # Log successful connection
            logger.info(f"Successfully connected to ACS {self.year} 5-year estimates API")
            logger.info(f"Found {len(data)-1} states in the response")  # -1 for header row
            
            # Log the response to debug file
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write("Test connection successful\n")
                f.write(f"Found {len(data)-1} states in the response\n")
                f.write(f"First state: {data[1] if len(data) > 1 else 'No data'}\n")
                
        except Exception as e:
            error_msg = f"Failed to connect to Census API: {str(e)}"
            logger.error(error_msg)
            
            # Log the error to debug file
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"Connection error: {error_msg}\n")
                
            raise ConnectionError(error_msg) from e
    
    def get_acs_data(
        self, 
        variables: List[str],
        level: str = 'tract',
        state: str = '15',
        county: str = None,
        geometry: bool = False,
        standardize_geoids: bool = True
    ) -> pd.DataFrame:
        """Fetch ACS data for specified variables using the Census API directly.
        
        Args:
            variables: List of ACS variable codes
            level: Geographic level ('tract', 'block group', 'county', 'state_lower', 'state_upper')
            state: State FIPS code (default: '15' for Hawaii)
            county: County FIPS code (required for tract and block group levels)
            geometry: Whether to include geometry in the output (not supported in direct API)
            standardize_geoids: Whether to standardize GEOIDs to match existing map files
            
        Returns:
            DataFrame with the requested ACS data
            
        Raises:
            ValueError: If required parameters are missing or invalid
            ConnectionError: If there's an error connecting to the Census API
        """
        try:
            # Ensure state is a 2-digit string
            state = str(state).zfill(2)
            
            # Map our level names to Census API geography names
            level_map = {
                'tract': 'tract',
                'block group': 'block group',
                'county': 'county',
                'state_lower': 'state legislative district (lower chamber)',
                'state_upper': 'state legislative district (upper chamber)'
            }
            
            if level not in level_map:
                raise ValueError(f"Unsupported level: {level}. Must be one of {list(level_map.keys())}")
            
            # Start building the API request
            get_params = ['NAME'] + variables
            get_str = ','.join(get_params)
            
            # Build the URL parameters based on level
            params = {
                'get': get_str,
                'key': self.api_key
            }
            
            if level == 'county':
                # For county level
                if county:
                    # If specific county is requested
                    params['for'] = f"county:{county}"
                else:
                    params['for'] = "county:*"
                params['in'] = f"state:{state}"
            
            elif level == 'tract':
                # For tract level
                params['for'] = "tract:*"
                if county:
                    params['in'] = f"state:{state} county:{county}"
                else:
                    params['in'] = f"state:{state}"
            
            elif level == 'block group':
                # For block group level
                params['for'] = "block group:*"
                if county:
                    params['in'] = f"state:{state} county:{county} tract:*"
                else:
                    params['in'] = f"state:{state} tract:*"
            
            elif level == 'state_lower':
                # For state house districts
                params['for'] = "legislative district (lower chamber):*"
                params['in'] = f"state:{state}"
            
            elif level == 'state_upper':
                # For state senate districts
                params['for'] = "legislative district (upper chamber):*"
                params['in'] = f"state:{state}"
            
            # Make the API request with parameters
            # The requests library will handle URL encoding automatically
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Log the request URL (with key redacted) for debugging
            safe_params = params.copy()
            if 'key' in safe_params:
                safe_params['key'] = 'REDACTED'
            logger.debug(f"API request: {self.base_url}?{urlencode(safe_params, safe=':,')}")
            
            # Parse the JSON response
            data = response.json()
            
            # Log the response to debug file
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"API request successful. Response has {len(data)} rows.\n")
                f.write(f"First row: {data[0] if data else 'No data'}\n")
            
            # Log the request (without API key for security)
            logger.info(f"Fetching ACS data for {len(variables)} variables at {level} level")
            
            # Construct the URL for the request
            url = f"{self.base_url}?{urlencode(params, safe=':,')}"
            safe_url = url.split('&key=')[0] + '&key=HIDDEN'
            logger.debug(f"API URL: {safe_url}")
            
            # Log to debug file
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"API request: {safe_url}\n")
            
            # Make the request
            response = requests.get(url)
            response.raise_for_status()
            
            # Log the raw response content for debugging
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"Raw API response status code: {response.status_code}\n")
                f.write(f"Raw API response headers: {response.headers}\n")
                f.write(f"Raw API response content (first 500 chars): {response.text[:500]}\n")
                
                # Check if median_rent variable is in the response
                if 'b25064_001e' in response.text.lower():
                    f.write("Found b25064_001e (median_rent) in raw API response\n")
                else:
                    f.write("WARNING: b25064_001e (median_rent) NOT FOUND in raw API response\n")
            
            # Check if the response is valid JSON
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Error parsing JSON response: {str(e)}")
                with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"Error parsing JSON: {str(e)}\n")
                    
                # The API key might be invalid or the request might be malformed
                # Let's check if there's an error message in the response
                if "Invalid API key" in response.text:
                    raise ValueError("Invalid Census API key provided")
                elif "error" in response.text.lower():
                    raise ValueError(f"Census API error: {response.text}")
                else:
                    raise ValueError(f"Failed to parse Census API response: {str(e)}. Check the debug log for details.")
            
            # Log response to debug file (first few rows)
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"API response (first 2 rows): {data[:2]}\n")
            
            # First row contains headers
            headers = [h.lower() for h in data[0]]
            rows = data[1:]
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=headers)
            
            # Log the columns before conversion
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"Columns in raw DataFrame: {df.columns.tolist()}\n")
                f.write(f"Looking for b25064_001e in columns: {'b25064_001e' in [col.lower() for col in df.columns]}\n")
            
            # Convert numeric columns to appropriate types
            for var in variables:
                var_lower = var.lower()
                if var_lower in df.columns:
                    df[var_lower] = pd.to_numeric(df[var_lower], errors='coerce')
                    
                    # Log median_rent values for debugging
                    if var_lower == 'b25064_001e':
                        with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                            f.write(f"Found b25064_001e in DataFrame. First 5 values: {df[var_lower].head().tolist()}\n")
            
            # Add GEOID column based on geographic level
            if standardize_geoids:
                try:
                    # Convert DataFrame to list of dictionaries for standardization
                    records = df.to_dict('records')
                    
                    # Generate standardized GEOIDs
                    geoids = [GeoIDStandardizer.standardize_geoid(record, level) for record in records]
                    
                    # Add the GEOID column
                    df['geoid'] = geoids
                    
                    # Log any invalid GEOIDs
                    invalid_geoids = [geoid for geoid in geoids if not GeoIDStandardizer.validate_geoid(geoid, level)]
                    if invalid_geoids:
                        logger.warning(f"Found {len(invalid_geoids)} invalid GEOIDs for level {level}")
                    
                    # Reorder columns to put GEOID first
                    cols = ['geoid'] + [col for col in df.columns if col != 'geoid']
                    df = df[cols]
                except Exception as e:
                    logger.error(f"Error standardizing GEOIDs: {str(e)}", exc_info=True)
                    # Fall back to simple GEOID generation
                    self._add_simple_geoid(df, level)
            else:
                # Use simple GEOID generation if standardization is disabled
                self._add_simple_geoid(df, level)
            
            # Rename variables to be more readable (after GEOID standardization)
            rename_cols = {
                'b17001_002e': 'below_poverty',
                'b17001_001e': 'total_population',
                'b19013_001e': 'median_income',
                'b19013_001m': 'median_income_moe',
                'b15003_022e': 'bachelors_plus',
                'b15003_001e': 'pop_25_plus',
                'b25003_003e': 'renter_occupied',
                'b25003_001e': 'total_housing_units',
                'b25064_001e': 'median_rent'  # Added median rent variable
            }
            
            # Only rename columns that exist in the dataframe
            rename_cols = {k.lower(): v for k, v in rename_cols.items() if k.lower() in df.columns}
            df = df.rename(columns=rename_cols)
            
            # Log to debug file
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"Final DataFrame columns: {df.columns.tolist()}\n")
                f.write(f"DataFrame shape: {df.shape}\n")
                if not df.empty:
                    f.write(f"First row: {df.iloc[0].to_dict()}\n")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching ACS data: {str(e)}", exc_info=True)
            
            # Log detailed error to debug file
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"Error in get_acs_data: {str(e)}\n")
                f.write(traceback.format_exc())
                
            raise
    
    def _add_simple_geoid(self, df: pd.DataFrame, level: str) -> None:
        """Add a simple GEOID column to the DataFrame based on the geographic level.
        
        Args:
            df: DataFrame to add GEOID to
            level: Geographic level ('tract', 'block group', 'county', 'state_lower', 'state_upper')
        """
        logger.info(f"Adding simple GEOID for level: {level}")
        
        try:
            if level == 'county':
                # For counties, GEOID is STATE + COUNTY
                if 'state' in df.columns and 'county' in df.columns:
                    df['geoid'] = df['state'] + df['county']
                    
            elif level == 'tract':
                # For tracts, GEOID is STATE + COUNTY + TRACT
                if 'state' in df.columns and 'county' in df.columns and 'tract' in df.columns:
                    df['geoid'] = df['state'] + df['county'] + df['tract']
                    
            elif level == 'block group':
                # For block groups, GEOID is STATE + COUNTY + TRACT + BLOCK GROUP
                if all(col in df.columns for col in ['state', 'county', 'tract', 'block group']):
                    df['geoid'] = df['state'] + df['county'] + df['tract'] + df['block group']
                    
            elif level == 'state_lower':
                # For state house districts, GEOID is STATE + SLDL (state legislative district lower)
                if 'state' in df.columns and 'legislative district (lower chamber)' in df.columns:
                    df['geoid'] = df['state'] + df['legislative district (lower chamber)'].str.zfill(3)
                    
            elif level == 'state_upper':
                # For state senate districts, GEOID is STATE + SLDU (state legislative district upper)
                if 'state' in df.columns and 'legislative district (upper chamber)' in df.columns:
                    df['geoid'] = df['state'] + df['legislative district (upper chamber)'].str.zfill(3)
                    
            # Reorder columns to put GEOID first if it was successfully added
            if 'geoid' in df.columns:
                cols = ['geoid'] + [col for col in df.columns if col != 'geoid']
                df = df[cols]
                logger.info("Successfully added simple GEOID column")
            else:
                logger.warning(f"Could not add simple GEOID for level {level} due to missing columns")
                
        except Exception as e:
            logger.error(f"Error adding simple GEOID: {str(e)}")
            
            # Log to debug file
            with open(self.debug_log_file, 'a', encoding='utf-8') as f:
                f.write(f"Error adding simple GEOID: {str(e)}\n")
                f.write(f"DataFrame columns: {df.columns.tolist()}\n")
                f.write(traceback.format_exc())
    
    @staticmethod
    def get_common_variables() -> Dict[str, str]:
        """Get a dictionary of common ACS variables.
        
        Returns:
            Dictionary mapping variable codes to descriptions
        """
        return {
            'B01001_001E': 'Total Population',
            'B17001_002E': 'Income below poverty level',
            'B17001_001E': 'Total population for poverty calculation',
            'B19013_001E': 'Median household income',
            'B19013_001M': 'Median household income margin of error',
            'B15003_022E': 'Bachelor\'s degree or higher',
            'B15003_001E': 'Population 25 years and over',
            'B25003_003E': 'Renter-occupied housing units',
            'B25003_001E': 'Total housing units',
            'B25064_001E': 'Median gross rent',
            'B25070_001E': 'Gross rent as percentage of household income',
            'B25070_007E': '30.0 to 34.9 percent',
            'B25070_008E': '35.0 to 39.9 percent',
            'B25070_009E': '40.0 to 49.9 percent',
            'B25070_010E': '50.0 percent or more'
        }
    
    def calculate_poverty_rate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate poverty rate and other metrics from ACS data.
        
        Args:
            df: DataFrame with ACS data
            
        Returns:
            DataFrame with calculated metrics
        """
        try:
            # Create a copy to avoid modifying the original
            result = df.copy()
            
            # Calculate poverty rate
            if 'below_poverty' in result.columns and 'total_population' in result.columns:
                result['poverty_rate'] = (result['below_poverty'] / result['total_population'] * 100).round(2)
            
            # Calculate percentage with bachelor's degree or higher
            if 'bachelors_plus' in result.columns and 'pop_25_plus' in result.columns:
                result['bachelors_rate'] = (result['bachelors_plus'] / result['pop_25_plus'] * 100).round(2)
            
            # Calculate percentage of renter-occupied housing
            if 'renter_occupied' in result.columns and 'total_housing_units' in result.columns:
                result['renter_rate'] = (result['renter_occupied'] / result['total_housing_units'] * 100).round(2)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}", exc_info=True)
            return df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str) -> str:
        """Save DataFrame to a CSV file.
        
        Args:
            df: DataFrame to save
            filename: Output filename (without extension)
            
        Returns:
            Path to the saved file
        """
        try:
            # Ensure the filename has .csv extension
            if not filename.endswith('.csv'):
                filename = f"{filename}.csv"
                
            # Create the full path
            output_path = self.processed_dir / filename
            
            # Save to CSV
            df.to_csv(output_path, index=False)
            logger.info(f"Saved data to {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}", exc_info=True)
            raise

def main():
    """Example usage."""
    try:
        # Initialize the ACS data fetcher
        fetcher = ACSDataFetcher()
        
        # Get common variables
        variables = list(fetcher.get_common_variables().keys())
        
        print("Fetching ACS data for Hawaii counties...")
        
        # Fetch data for Hawaii counties
        county_data = fetcher.get_acs_data(
            variables=variables,
            level='county',
            state='15',  # Hawaii
            geometry=False
        )
        
        if county_data is not None:
            print(f"Successfully fetched data with {len(county_data)} rows")
            print(f"Columns: {county_data.columns.tolist()}")
            
            # Calculate metrics
            county_data = fetcher.calculate_poverty_rate(county_data)
            
            # Save to CSV
            output_file = fetcher.save_to_csv(county_data, 'hawaii_counties_acs')
            print(f"Data saved to: {output_file}")
            
            # Verify median_rent is in the saved file
            if os.path.exists(output_file):
                df = pd.read_csv(output_file)
                if 'median_rent' in df.columns:
                    print("✓ median_rent column found in output file")
                    print(f"Sample median rent values:\n{df[['name', 'median_rent']].head()}")
                else:
                    print("✗ median_rent column NOT found in output file")
                    print(f"Available columns: {df.columns.tolist()}")
            
            print("Done!")
        else:
            print("Failed to fetch county data")
            
    except Exception as e:
        print(f"Error in main: {str(e)}")
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        logger.error(f"Error in main: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
