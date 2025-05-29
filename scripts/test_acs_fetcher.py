"""
Test script for the ACSDataFetcher class.
"""
import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from data.acs_data import ACSDataFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_acs_fetcher.log')
    ]
)
logger = logging.getLogger(__name__)

def test_acs_fetcher():
    """Test the ACSDataFetcher class with a small dataset."""
    try:
        logger.info("Starting ACSDataFetcher test...")
        
        # Get API key from environment variable
        api_key = os.getenv('CENSUS_API_KEY')
        if not api_key:
            logger.error("CENSUS_API_KEY environment variable not set")
            return False
        
        # Initialize the ACS data fetcher
        logger.info("Initializing ACSDataFetcher...")
        acs = ACSDataFetcher(api_key=api_key, year=2019)
        
        # Test with a small set of variables
        test_variables = [
            'B17001_001E',  # Total population for whom poverty status is determined
            'B17001_002E'   # Below poverty level
        ]
        
        # Test county level (smallest dataset)
        logger.info("Testing county level data fetch...")
        gdf_county = acs.get_acs_data(
            variables=test_variables,
            level='county',
            state='15',  # Hawaii
            geometry=True
        )
        
        if gdf_county is None or gdf_county.empty:
            logger.error("Failed to fetch county level data")
            return False
            
        logger.info(f"Successfully fetched {len(gdf_county)} county records")
        logger.info("Sample data:")
        print(gdf_county.head())
        
        # Calculate poverty rate
        logger.info("Calculating poverty rate...")
        gdf_county = acs.calculate_poverty_rate(gdf_county)
        
        if 'poverty_rate' not in gdf_county.columns:
            logger.error("Failed to calculate poverty rate")
            return False
            
        logger.info("Poverty rate calculation successful")
        print(gdf_county[['NAME', 'total_population', 'below_poverty', 'poverty_rate']].head())
        
        # Save to file
        logger.info("Saving test data to file...")
        output_path = acs.save_to_geojson(gdf_county, 'test_acs_county')
        logger.info(f"Test data saved to {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    if test_acs_fetcher():
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed. Check the log file for details.")
        sys.exit(1)
