"""
ACS Data Pipeline for Hawaii Appleseed Dashboard
"""
import os
import pandas as pd
import geopandas as gpd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Any
import cenpy
import logging
from pathlib import Path
import time
import json

# Import the GeoIDStandardizer
from .geoid_utils import GeoIDStandardizer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ACSDataFetcher:
    """Class to fetch and process ACS data using cenpy."""
    
    def __init__(self, api_key: str = None, year: int = 2019):
        """Initialize the ACS data fetcher.
        
        Args:
            api_key: Census API key (required for cenpy)
            year: ACS year (default: 2019)
        """
        if not api_key:
            raise ValueError("API key is required for cenpy")
            
        self.api_key = api_key
        self.year = year
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir.parent / 'data'
        self.processed_dir = self.data_dir / 'processed'
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.acs = None
        
        # Set up the connection
        self._setup_connection()
    
    def _setup_connection(self) -> None:
        """Set up the connection to the ACS API.
        
        Raises:
            ConnectionError: If the connection cannot be established
        """
        try:
            # Initialize the ACS connection with the 5-year dataset
            self.acs = cenpy.products.ACS(year=self.year)
            # Set the dataset to 5-year ACS
            self.acs.set_source(f'ACSDT{self.year}Y{str(self.year)[-2:]}')
            logger.info(f"Successfully connected to ACS {self.year} 5-year estimates")
        except Exception as e:
            error_msg = f"Failed to connect to ACS API: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e
    
    def get_acs_data(
        self, 
        variables: List[str],
        level: str = 'tract',
        state: str = '15',  # FIPS code for Hawaii
        county: Optional[Union[str, List[str]]] = None,
        geometry: bool = True,
        survey: str = 'acs5',  # Default to 5-year ACS data
        standardize_geoids: bool = True  # Whether to standardize GEOIDs
    ) -> gpd.GeoDataFrame:
        """Fetch ACS data for specified variables using cenpy.
        
        Args:
            variables: List of ACS variable codes
            level: Geographic level ('tract', 'block group', 'county', 'state_lower', 'state_upper')
            state: State FIPS code (default: '15' for Hawaii)
            county: Optional county FIPS code(s), not used for state legislative districts
            geometry: Whether to include geometry
            survey: ACS survey type ('acs5', 'acs3', 'acs1')
            
        Returns:
            GeoDataFrame with ACS data
        """
        if not self.acs:
            raise ConnectionError("ACS connection not established. Call _setup_connection() first.")
            
        try:
            # Convert level to the format expected by cenpy
            level_map = {
                'tract': 'tract',
                'block group': 'block group',
                'county': 'county',
                'state_lower': 'state legislative district (lower chamber)',
                'state_upper': 'state legislative district (upper chamber)'
            }
            
            if level not in level_map:
                raise ValueError(f"Unsupported level: {level}. Must be one of {list(level_map.keys())}")
            
            # Convert state to string if it's a number
            state = str(state).zfill(2)
            
            logger.info(f"Fetching ACS data for {len(variables)} variables at {level} level")
            
            # Fetch the data using cenpy
            try:
                if level == 'county':
                    # For county level
                    gdf = self.acs.from_acs(
                        variables=variables,
                        level=level,
                        state=state,
                        county=county if county else '*',
                        geometry=geometry
                    )
                    
                elif level == 'tract':
                    # For tract level
                    gdf = self.acs.from_acs(
                        variables=variables,
                        level='tract',
                        state=state,
                        county=county if county else '*',
                        geometry=geometry
                    )
                    
                elif level == 'block group':
                    # For block group level
                    gdf = self.acs.from_acs(
                        variables=variables,
                        level='block group',
                        state=state,
                        county=county if county else '*',
                        geometry=geometry
                    )
                    
                elif level in ['state_lower', 'state_upper']:
                    # For state legislative districts
                    place_type = 'sldl' if level == 'state_lower' else 'sldu'
                    gdf = self.acs.from_acs(
                        variables=variables,
                        level=place_type,
                        state=state,
                        geometry=geometry
                    )
                    
            except Exception as e:
                logger.error(f"Error in from_acs: {str(e)}")
                raise
            
            # Clean up column names and standardize GEOIDs
            if not gdf.empty:
                # Remove any duplicate columns
                gdf = gdf.loc[:, ~gdf.columns.duplicated()]
                
                # Convert all column names to lowercase for consistency
                gdf.columns = [col.lower() for col in gdf.columns]
                
                # Standardize GEOIDs if requested
                if standardize_geoids:
                    try:
                        # Convert the GeoDataFrame to a list of dictionaries
                        records = gdf.to_dict('records')
                        
                        # Generate standardized GEOIDs
                        geoids = [GeoIDStandardizer.standardize_geoid(record, level) for record in records]
                        
                        # Add the GEOID column
                        gdf['geoid'] = geoids
                        
                        # Log any invalid GEOIDs
                        invalid_geoids = [geoid for geoid in geoids if not GeoIDStandardizer.validate_geoid(geoid, level)]
                        if invalid_geoids:
                            logger.warning(f"Found {len(invalid_geoids)} invalid GEOIDs for level {level}")
                        
                        # Reorder columns to put GEOID first
                        cols = ['geoid'] + [col for col in gdf.columns if col != 'geoid']
                        gdf = gdf[cols]
                    except Exception as e:
                        logger.error(f"Error standardizing GEOIDs: {str(e)}", exc_info=True)
                        # Fall back to simple GEOID generation if standardization fails
                        self._add_simple_geoid(gdf, level)
                else:
                    # Use simple GEOID generation if standardization is disabled
                    self._add_simple_geoid(gdf, level)
                
                # Rename variables to be more readable (after GEOID standardization)
                rename_cols = {
                    'b17001_002e': 'below_poverty',
                    'b17001_001e': 'total_population',
                    'b19013_001e': 'median_income',
                    'b19013_001m': 'median_income_moe',
                    'b15003_022e': 'bachelors_plus',
                    'b15003_001e': 'pop_25_plus',
                    'b25003_003e': 'renter_occupied',
                    'b25003_001e': 'total_housing_units'
                }
                
                # Only rename columns that exist in the dataframe
                rename_cols = {k: v for k, v in rename_cols.items() if k in gdf.columns}
                gdf = gdf.rename(columns=rename_cols)
            
            return gdf
            
        except Exception as e:
            logger.error(f"Error fetching ACS data: {str(e)}", exc_info=True)
            raise
            
        except Exception as e:
            logger.error(f"Error fetching ACS data: {str(e)}")
            raise
    
    @staticmethod
    def get_common_variables() -> Dict[str, str]:
        """Get a dictionary of common ACS variables."""
        return {
            'poverty': {
                'B17001_002E': 'Below poverty level',
                'B17001_001E': 'Total population for poverty status'
            },
            'income': {
                'B19013_001E': 'Median household income (dollars)',
                'B19013_001M': 'Median household income (margin of error)'
            },
            'education': {
                'B15003_022E': 'Bachelor\'s degree or higher',
                'B15003_001E': 'Total population 25+ years'
            },
            'housing': {
                'B25003_003E': 'Renter-occupied housing units',
                'B25003_001E': 'Total housing units'
            }
        }
    
    def calculate_poverty_rate(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Calculate poverty rate and other metrics from ACS data.
        
        Args:
            gdf: GeoDataFrame with ACS data
            
        Returns:
            GeoDataFrame with calculated metrics
        """
        try:
            # Make a copy to avoid modifying the original
            result = gdf.copy()
            
            # Calculate poverty rate if we have the required columns
            if 'below_poverty' in result.columns and 'total_population' in result.columns:
                result['poverty_rate'] = (
                    result['below_poverty'].astype(float) / 
                    result['total_population'].replace(0, np.nan)
                ) * 100
                result['poverty_rate'] = result['poverty_rate'].round(2)
            
            # Calculate renter percentage
            if 'renter_occupied' in result.columns and 'total_housing_units' in result.columns:
                result['renter_percent'] = (
                    result['renter_occupied'].astype(float) / 
                    result['total_housing_units'].replace(0, np.nan) * 100
                ).round(2)
            
            # Calculate education attainment
            if 'bachelors_plus' in result.columns and 'pop_25_plus' in result.columns:
                result['bachelors_percent'] = (
                    result['bachelors_plus'].astype(float) / 
                    result['pop_25_plus'].replace(0, np.nan) * 100
                ).round(2)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}", exc_info=True)
            return gdf
    
    def _add_simple_geoid(self, gdf: gpd.GeoDataFrame, level: str) -> None:
        """Add a simple GEOID column to the GeoDataFrame based on the geographic level.
        
        Args:
            gdf: GeoDataFrame to add GEOID to
            level: Geographic level ('tract', 'block group', 'county', 'state_lower', 'state_upper')
        """
        if 'geoid' in gdf.columns:
            return
            
        try:
            if level == 'county' and 'state' in gdf.columns and 'county' in gdf.columns:
                gdf['geoid'] = gdf['state'].astype(str).str.zfill(2) + gdf['county'].astype(str).str.zfill(3)
            elif level == 'tract' and 'state' in gdf.columns and 'county' in gdf.columns and 'tract' in gdf.columns:
                gdf['geoid'] = (
                    gdf['state'].astype(str).str.zfill(2) + 
                    gdf['county'].astype(str).str.zfill(3) + 
                    gdf['tract'].astype(str).str.replace('.', '').str.zfill(6)
                )
            elif level == 'block group' and 'state' in gdf.columns and 'county' in gdf.columns and 'tract' in gdf.columns and 'block group' in gdf.columns:
                gdf['geoid'] = (
                    gdf['state'].astype(str).str.zfill(2) + 
                    gdf['county'].astype(str).str.zfill(3) + 
                    gdf['tract'].astype(str).str.replace('.', '').str.zfill(6) + 
                    gdf['block group'].astype(str).str.zfill(1)
                )
            elif level == 'state_lower' and 'state' in gdf.columns and 'sldlst' in gdf.columns:
                gdf['geoid'] = gdf['state'].astype(str).str.zfill(2) + gdf['sldlst'].astype(str).str.zfill(3)
            elif level == 'state_upper' and 'state' in gdf.columns and 'sldust' in gdf.columns:
                gdf['geoid'] = gdf['state'].astype(str).str.zfill(2) + gdf['sldust'].astype(str).str.zfill(2)
                
            # Reorder columns to put GEOID first if it was added
            if 'geoid' in gdf.columns:
                cols = ['geoid'] + [col for col in gdf.columns if col != 'geoid']
                gdf = gdf[cols]
                
        except Exception as e:
            logger.error(f"Error adding simple GEOID: {str(e)}", exc_info=True)
    
    def save_to_geojson(self, gdf: gpd.GeoDataFrame, filename: str) -> str:
        """Save GeoDataFrame to a GeoJSON file.
        
        Args:
            gdf: GeoDataFrame to save
            filename: Output filename (without extension)
            
        Returns:
            Path to the saved file
        """
        try:
            # Ensure the output directory exists
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            
            # Create the output path
            output_path = self.processed_dir / f"{filename}.geojson"
            
            # Save to GeoJSON
            gdf.to_file(output_path, driver='GeoJSON')
            
            logger.info(f"Saved data to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error saving GeoJSON: {str(e)}", exc_info=True)
            raise

def main():
    """Example usage."""
    # Initialize with your API key
    api_key = '2104852dd7bfd83fbc9e320d650eb57decc11817'
    acs = ACSDataFetcher(api_key=api_key)
    
    # Get common variables
    variables = []
    for var_dict in acs.get_common_variables().values():
        variables.extend(list(var_dict.keys()))
    
    # Fetch data
    gdf = acs.get_acs_data(
        variables=variables,
        level='tract',
        state='15'  # Hawaii
    )
    
    # Calculate derived metrics
    gdf = acs.calculate_poverty_rate(gdf)
    
    # Save to file
    acs.save_to_geojson(gdf, 'hi_acs_data')

if __name__ == "__main__":
    main()
