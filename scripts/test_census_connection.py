import os
import requests

def test_connection():
    api_key = os.environ.get('CENSUS_API_KEY')
    if not api_key:
        print("Error: CENSUS_API_KEY environment variable is not set"); return
    base_url = "https://api.census.gov/data/2023/acs/acs5"
    
    # Test query for Hawaii counties
    params = {
        'get': 'NAME,B01001_001E',  # Total population
        'for': 'county:*',
        'in': 'state:15',  # Hawaii
        'key': api_key
    }
    
    try:
        print(f"Testing connection to Census API...")
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an error for bad responses
        
        # Print the first few rows of data
        data = response.json()
        print("\nSuccess! First few rows of data:")
        for i, row in enumerate(data[:5]):  # Print first 5 rows
            print(row)
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text[:500]}...")

if __name__ == "__main__":
    test_connection()
