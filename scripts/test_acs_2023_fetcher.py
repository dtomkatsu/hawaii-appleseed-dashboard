"""
Test script for the ACSDataFetcher class with 2023 ACS data.
"""
import os
import sys
import logging
import pandas as pd
from pathlib import Path
from src.data.acs_data import ACSDataFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_county_data():
    """Test fetching county-level data for Hawaii."""
    logger.info("=== Testing county data ===")
    
    try:
        # Initialize the fetcher
        logger.info("Initializing ACSDataFetcher for 2023 ACS 5-year estimates...")
        fetcher = ACSDataFetcher(year=2023)
        
        # Define variables to fetch
        variables = [
            'B01001_001E',  # Total population
            'B17001_002E',  # Income below poverty level
            'B17001_001E',  # Total population for poverty calculation
            'B19013_001E',  # Median household income
            'B19013_001M',  # Median household income margin of error
        ]
        
        # Fetch the data
        logger.info("Fetching data for Hawaii counties...")
        county_data = fetcher.get_acs_data(
            variables=variables,
            level='county',
            state='15',  # Hawaii
            geometry=False
        )
        
        # Calculate additional metrics
        county_data = fetcher.calculate_poverty_rate(county_data)
        
        # Display the results
        print("\nCounty Data:")
        print(county_data[['NAME', 'poverty_rate', 'median_income']])
        
        # Save to CSV
        output_file = fetcher.save_to_csv(county_data, 'hawaii_counties_acs_2023')
        logger.info(f"Saved county data to {output_file}")
        
        return county_data
        
    except Exception as e:
        logger.error(f"Error in test_county_data: {str(e)}", exc_info=True)
        raise

def test_state_house_data():
    """Test fetching state house district data for Hawaii."""
    logger.info("\n=== Testing state house district data ===")
    
    try:
        # Initialize the fetcher
        logger.info("Initializing ACSDataFetcher for 2023 ACS 5-year estimates...")
        fetcher = ACSDataFetcher(year=2023)
        
        # Define variables to fetch
        variables = [
            'B01001_001E',  # Total population
            'B17001_002E',  # Income below poverty level
            'B17001_001E',  # Total population for poverty calculation
            'B19013_001E',  # Median household income
        ]
        
        # Fetch the data
        logger.info("Fetching data for Hawaii state house districts...")
        house_data = fetcher.get_acs_data(
            variables=variables,
            level='state_lower',
            state='15',  # Hawaii
            geometry=False
        )
        
        # Calculate additional metrics
        house_data = fetcher.calculate_poverty_rate(house_data)
        
        # Display the results
        print("\nState House District Data:")
        print(house_data[['NAME', 'poverty_rate', 'median_income']])
        
        # Save to CSV
        output_file = fetcher.save_to_csv(house_data, 'hawaii_house_districts_acs_2023')
        logger.info(f"Saved state house district data to {output_file}")
        
        return house_data
        
    except Exception as e:
        logger.error(f"Error in test_state_house_data: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        # Test county data
        county_data = test_county_data()
        
        # Test state house district data
        house_data = test_state_house_data()
        
        logger.info("\nAll tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        sys.exit(1)
