"""
Script to run the ACS Data Pipeline for Hawaii Appleseed Dashboard using cenpy
"""
import os
import sys
import logging
from pathlib import Path
import time
from typing import List, Dict, Optional
import pandas as pd
import geopandas as gpd

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from data.acs_data import ACSDataFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('acs_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

def fetch_and_save_data(
    acs: ACSDataFetcher,
    variables: List[str],
    level: str,
    state: str,
    max_retries: int = 3
) -> bool:
    """Fetch data for a specific geographic level and save it to a file.
    
    Args:
        acs: Initialized ACSDataFetcher instance
        variables: List of ACS variable codes to fetch
        level: Geographic level ('county', 'tract', or 'block group')
        state: State FIPS code
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_retries} to fetch {level} data...")
            
            # Fetch the data with geometry
            gdf = acs.get_acs_data(
                variables=variables,
                level=level,
                state=state,
                geometry=True  # Get geometry with the data
            )
            
            if gdf is None or gdf.empty:
                logger.warning(f"No data returned for {level} level")
                return False
                
            logger.info(f"Fetched {len(gdf)} records for {level} level")
            
            # Calculate derived metrics
            gdf = acs.calculate_poverty_rate(gdf)
            
            # Save to GeoJSON
            filename = f"hi_acs_{level.replace(' ', '_')}"
            output_path = acs.save_to_geojson(gdf, filename)
            
            logger.info(f"Successfully saved {level} data to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching {level} data (attempt {attempt}): {str(e)}", exc_info=True)
            if attempt < max_retries:
                wait_time = attempt * 10  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch {level} data after {max_retries} attempts")
                return False

def main():
    """Run the ACS data pipeline."""
    try:
        logger.info("Starting ACS data pipeline...")
        
        # Get API key from environment variable
        api_key = os.getenv('CENSUS_API_KEY')
        if not api_key:
            logger.error("CENSUS_API_KEY environment variable not set")
            return 1
        
        # Initialize the ACS data fetcher
        acs = ACSDataFetcher(api_key=api_key, year=2019)
        
        # Define the variables we want to fetch
        variables = [
            'B17001_002E',  # Below poverty level (past 12 months)
            'B17001_001E',  # Total population for whom poverty status is determined
            'B19013_001E',  # Median household income
            'B19013_001M',  # Median household income (margin of error)
            'B15003_022E',  # Bachelor's degree or higher (population 25+)
            'B15003_001E',  # Total population 25 years and over
            'B25003_003E',  # Renter-occupied housing units
            'B25003_001E'   # Total housing units
        ]
        
        logger.info(f"Using {len(variables)} variables")
        
        # Process each geographic level
        levels = [
            'county',       # Start with county level (smallest dataset)
            'tract',        # Then tract
            'block group',  # Then block group
            'state_lower',  # State house districts
            'state_upper'   # State senate districts
        ]
        
        for level in levels:
            logger.info(f"\nProcessing {level} level...")
            success = fetch_and_save_data(
                acs=acs,
                variables=variables,
                level=level,
                state='15'  # FIPS code for Hawaii
            )
            
            if success:
                logger.info(f"Successfully processed {level} level")
            else:
                logger.error(f"Failed to process {level} level")
            
            # Add a small delay between levels to be nice to the API
            if level != levels[-1]:
                wait_time = 10 if level in ['state_lower', 'state_upper'] else 5
                logger.info(f"Waiting {wait_time} seconds before next request...")
                time.sleep(wait_time)
        
        logger.info("ACS data pipeline completed!")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error in ACS data pipeline: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
