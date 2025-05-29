"""
Test script to fetch and verify ACS data for Hawaii state house districts.
"""
import os
import sys
import logging
from pathlib import Path
import pandas as pd

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from data.acs_data import ACSDataFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_house_districts.log')
    ]
)
logger = logging.getLogger(__name__)

def test_house_districts():
    """Test fetching ACS data for Hawaii state house districts."""
    try:
        # Get API key from environment variable
        api_key = os.getenv('CENSUS_API_KEY')
        if not api_key:
            logger.error("CENSUS_API_KEY environment variable not set")
            return
            
        # Initialize the ACS data fetcher
        logger.info("Initializing ACSDataFetcher...")
        fetcher = ACSDataFetcher(api_key=api_key, year=2019)
        
        # Define variables to fetch (example: population and poverty data)
        variables = [
            'B01001_001E',  # Total population
            'B17001_002E',  # Below poverty level (past 12 months)
            'B17001_001E',  # Total population for poverty status
            'B19013_001E',  # Median household income
            'B19013_001M'   # Median household income (margin of error)
        ]
        
        # Fetch data for counties (since state legislative districts aren't directly supported)
        logger.info("Fetching data for Hawaii counties...")
        county_data = fetcher.get_acs_data(
            variables=variables,
            level='county',
            state='15',  # Hawaii
            geometry=False  # We'll join with our own geometry later
        )
        
        if county_data is not None and not county_data.empty:
            # Display basic info
            logger.info(f"Retrieved data for {len(county_data)} counties")
            logger.info("Columns in the data:")
            for col in county_data.columns:
                logger.info(f"- {col}")
                
            # Show first few rows of data
            logger.info("\nSample data (first 5 rows):")
            
            # Find the population and income columns
            pop_col = next((col for col in county_data.columns if 'b01001_001e' in col.lower()), None)
            income_col = next((col for col in county_data.columns if 'b19013_001e' in col.lower()), None)
            
            # Select columns to display
            display_cols = ['name', 'state', 'county']
            if pop_col:
                display_cols.append(pop_col)
            if income_col:
                display_cols.append(income_col)
                
            logger.info(county_data[display_cols].head().to_string())
            
            # Save to CSV for inspection
            output_file = 'data/processed/hawaii_counties_acs.csv'
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            county_data.to_csv(output_file, index=False)
            logger.info(f"\nData saved to {output_file}")
            
            return county_data
        else:
            logger.warning("No data was returned for Hawaii counties")
            return None
        
        return house_data
        
    except Exception as e:
        logger.error(f"Error in test_house_districts: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    test_house_districts()
