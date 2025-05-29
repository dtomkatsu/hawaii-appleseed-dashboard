"""
Test script to verify Census API connection and data fetching.
"""
import os
import sys
import json
import requests
from pathlib import Path

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_census_api():
    """Test the Census API connection and fetch some data."""
    # API key and base URL
    api_key = "2104852dd7bfd83fbc9e320d650eb57decc11817"
    year = 2023
    base_url = f"https://api.census.gov/data/{year}/acs/acs5"
    
    # Test query for Hawaii counties
    params = {
        'get': 'NAME,B01001_001E',  # Total population
        'for': 'county:*',
        'in': 'state:15',  # Hawaii
        'key': api_key
    }
    
    try:
        logger.info("Testing connection to Census API...")
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Print the results
        print("\nSuccess! First few rows of data:")
        for i, row in enumerate(data[:5]):  # Print first 5 rows
            print(row)
            
        # Save the full response to a file for inspection
        output_file = Path("census_api_response.json")
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Full response saved to {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text[:500]}...")
        return False

if __name__ == "__main__":
    success = test_census_api()
    sys.exit(0 if success else 1)
