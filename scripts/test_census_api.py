"""
Test script for the ACS data fetcher using direct Census API calls
"""
import os
import sys
import logging
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the ACSDataFetcher
from src.data.acs_data import ACSDataFetcher

def test_state_house_districts(api_key=None):
    """Test fetching data for state house districts."""
    try:
        # Initialize the ACS data fetcher
        logger.info("Initializing ACSDataFetcher...")
        fetcher = ACSDataFetcher(api_key=api_key)
        
        # Define the variables we want to fetch
        variables = [
            'B01001_001E',  # Total population
            'B17001_002E',  # Income below poverty level
            'B17001_001E',  # Total population for poverty calculation
            'B19013_001E',  # Median household income
            'B19013_001M'   # Median household income margin of error
        ]
        
        # Fetch data for state house districts
        logger.info("Fetching data for Hawaii state house districts...")
        house_data = fetcher.get_acs_data(
            variables=variables,
            level='state_lower',
            state='15',  # Hawaii
            geometry=False
        )
        
        if house_data is not None and not house_data.empty:
            # Display basic info
            logger.info(f"Retrieved data for {len(house_data)} house districts")
            logger.info("Columns in the data:")
            for col in house_data.columns:
                logger.info(f"- {col}")
                
            # Show first few rows of data
            logger.info("\nSample data (first 5 rows):")
            logger.info(house_data.head().to_string())
            
            # Calculate poverty rate
            house_data = fetcher.calculate_poverty_rate(house_data)
            
            # Save to CSV for inspection
            output_file = fetcher.save_to_csv(house_data, 'hawaii_house_districts_acs')
            logger.info(f"\nData saved to {output_file}")
            
            return house_data
        else:
            logger.warning("No data was returned for state house districts")
            return None
            
    except Exception as e:
        logger.error(f"Error in test_state_house_districts: {str(e)}", exc_info=True)
        raise

def test_county_data(api_key=None):
    """Test fetching data for counties."""
    try:
        # Initialize the ACS data fetcher
        logger.info("Initializing ACSDataFetcher...")
        fetcher = ACSDataFetcher(api_key=api_key)
        
        # Define the variables we want to fetch
        variables = [
            'B01001_001E',  # Total population
            'B17001_002E',  # Income below poverty level
            'B17001_001E',  # Total population for poverty calculation
            'B19013_001E',  # Median household income
            'B19013_001M'   # Median household income margin of error
        ]
        
        # Fetch data for counties
        logger.info("Fetching data for Hawaii counties...")
        county_data = fetcher.get_acs_data(
            variables=variables,
            level='county',
            state='15',  # Hawaii
            geometry=False
        )
        
        if county_data is not None and not county_data.empty:
            # Display basic info
            logger.info(f"Retrieved data for {len(county_data)} counties")
            logger.info("Columns in the data:")
            for col in county_data.columns:
                logger.info(f"- {col}")
                
            # Show first few rows of data
            logger.info("\nSample data:")
            logger.info(county_data.to_string())
            
            # Calculate poverty rate
            county_data = fetcher.calculate_poverty_rate(county_data)
            
            # Save to CSV for inspection
            output_file = fetcher.save_to_csv(county_data, 'hawaii_counties_acs')
            logger.info(f"\nData saved to {output_file}")
            
            return county_data
        else:
            logger.warning("No data was returned for counties")
            return None
            
    except Exception as e:
        logger.error(f"Error in test_county_data: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test ACS data fetching with Census API')
    parser.add_argument('--api-key', help='Census API key (if not provided, will check CENSUS_API_KEY environment variable)')
    parser.add_argument('--test', choices=['county', 'house', 'all'], default='all',
                        help='Which test to run (default: all)')
    args = parser.parse_args()
    
    # Get API key from command-line argument or environment variable
    api_key = args.api_key or os.environ.get('CENSUS_API_KEY')
    
    if not api_key:
        print("Error: Census API key is required. Provide it using --api-key or set the CENSUS_API_KEY environment variable.")
        sys.exit(1)
    
    # Create a debug log file
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True, parents=True)
    debug_log_file = logs_dir / "test_census_api_debug.log"
    
    # Add file handler to logger
    file_handler = logging.FileHandler(debug_log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Run the tests
    try:
        if args.test in ['county', 'all']:
            # Test county data first (simpler)
            logger.info("=== Testing county data ===")
            test_county_data(api_key=api_key)
        
        if args.test in ['house', 'all']:
            # Then test state house districts
            logger.info("\n=== Testing state house districts ===")
            test_state_house_districts(api_key=api_key)
        
        logger.info("All tests completed successfully!")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
