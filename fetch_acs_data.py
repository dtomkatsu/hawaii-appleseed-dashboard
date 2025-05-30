"""
Fetch ACS data for Hawaii and save to CSV files.
"""
import os
import json
import pandas as pd
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ACSScraper:
    """Simple scraper for ACS data using direct API calls."""
    
    def __init__(self, api_key: str, year: int = 2023):
        """Initialize the scraper with API key and year."""
        self.api_key = api_key
        self.year = year
        self.base_url = f"https://api.census.gov/data/{year}/acs/acs5"
        
        # Set up output directory
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Common variables to fetch
        self.variables = {
            'B01001_001E': 'total_population',
            'B17001_002E': 'below_poverty',
            'B17001_001E': 'total_population_poverty',
            'B19013_001E': 'median_income',
            'B19013_001M': 'median_income_moe',
            'B15003_022E': 'bachelors_plus',
            'B15003_001E': 'pop_25_plus',
            'B25003_003E': 'renter_occupied',
            'B25003_001E': 'total_housing_units',
            # Gross rent as percentage of household income (GRAPI)
            'B25070_007E': 'rent_30_34_pct',    # 30.0 to 34.9 percent
            'B25070_008E': 'rent_35_39_pct',    # 35.0 to 39.9 percent
            'B25070_009E': 'rent_40_49_pct',    # 40.0 to 49.9 percent
            'B25070_010E': 'rent_50_plus_pct',  # 50.0 percent or more
            'B25070_001E': 'rent_total_units'   # Total renter-occupied housing units
        }
    
    def fetch_data(self, params: Dict[str, Any]) -> Optional[List[Dict]]:
        """Fetch data from the Census API."""
        try:
            # Add API key to params
            params = params.copy()
            params['key'] = self.api_key
            
            # Make the request
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Convert to list of dicts
            headers = data[0]
            rows = data[1:]
            
            return [dict(zip(headers, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text[:500]}...")
            return None
    
    def fetch_counties(self) -> Optional[pd.DataFrame]:
        """Fetch data for all counties in Hawaii."""
        logger.info("Fetching county-level data...")
        
        # Build the query
        params = {
            'get': ','.join(['NAME'] + list(self.variables.keys())),
            'for': 'county:*',
            'in': 'state:15'
        }
        
        # Fetch the data
        data = self.fetch_data(params)
        if not data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Rename columns
        rename_cols = {k: v for k, v in self.variables.items() if k in df.columns}
        df = df.rename(columns=rename_cols)
        
        # Add GEOID (state + county)
        df['geoid'] = df['state'] + df['county']
        
        # Calculate derived metrics
        df = self._calculate_metrics(df)
        
        # Save to CSV
        output_file = self.output_dir / 'hawaii_counties_acs_2023.csv'
        df.to_csv(output_file, index=False)
        logger.info(f"Saved county data to {output_file}")
        
        return df
    
    def fetch_state_house_districts(self) -> Optional[pd.DataFrame]:
        """Fetch data for all state house districts in Hawaii."""
        logger.info("Fetching state house district data...")
        
        # Build the query
        params = {
            'get': ','.join(['NAME'] + list(self.variables.keys())),
            'for': 'state legislative district (lower chamber):*',
            'in': 'state:15'
        }
        
        # Fetch the data
        data = self.fetch_data(params)
        if not data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Rename columns
        rename_cols = {k: v for k, v in self.variables.items() if k in df.columns}
        df = df.rename(columns=rename_cols)
        
        # Clean up district numbers and create GEOID (state + district number)
        df['district'] = df['state legislative district (lower chamber)'].astype(str).str.zfill(3)
        df['geoid'] = df['state'] + df['district']
        
        # Calculate derived metrics
        df = self._calculate_metrics(df)
        
        # Save to CSV
        output_file = self.output_dir / 'hawaii_house_districts_acs_2023.csv'
        df.to_csv(output_file, index=False)
        logger.info(f"Saved state house district data to {output_file}")
        
        return df
        
    def fetch_state_senate_districts(self) -> Optional[pd.DataFrame]:
        """Fetch data for all state senate districts in Hawaii."""
        logger.info("Fetching state senate district data...")
        
        # Build the query
        params = {
            'get': ','.join(['NAME'] + list(self.variables.keys())),
            'for': 'state legislative district (upper chamber):*',
            'in': 'state:15'
        }
        
        # Fetch the data
        data = self.fetch_data(params)
        if not data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Rename columns
        rename_cols = {k: v for k, v in self.variables.items() if k in df.columns}
        df = df.rename(columns=rename_cols)
        
        # Clean up district numbers and create GEOID (state + district number)
        df['district'] = df['state legislative district (upper chamber)'].astype(str).str.zfill(2)
        df['geoid'] = df['state'] + df['district']
        
        # Calculate derived metrics
        df = self._calculate_metrics(df)
        
        # Save to CSV
        output_file = self.output_dir / 'hawaii_senate_districts_acs_2023.csv'
        df.to_csv(output_file, index=False)
        logger.info(f"Saved state senate district data to {output_file}")
        
        return df
        
    def fetch_state_data(self) -> Optional[pd.DataFrame]:
        """Fetch data for the entire state of Hawaii."""
        logger.info("Fetching state-level data...")
        
        # Build the query
        params = {
            'get': ','.join(['NAME'] + list(self.variables.keys())),
            'for': 'state:15'
        }
        
        # Fetch the data
        data = self.fetch_data(params)
        if not data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Rename columns
        rename_cols = {k: v for k, v in self.variables.items() if k in df.columns}
        df = df.rename(columns=rename_cols)
        
        # Add GEOID (state FIPS code)
        df['geoid'] = df['state']
        
        # Calculate derived metrics
        df = self._calculate_metrics(df)
        
        # Save to CSV
        output_file = self.output_dir / 'hawaii_state_acs_2023.csv'
        df.to_csv(output_file, index=False)
        logger.info(f"Saved state-level data to {output_file}")
        
        return df
    
    def _calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate derived metrics from the raw data."""
        df = df.copy()
        
        # Convert numeric columns
        for col in self.variables.values():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate poverty rate
        if 'below_poverty' in df.columns and 'total_population_poverty' in df.columns:
            df['poverty_rate'] = (df['below_poverty'] / df['total_population_poverty'] * 100).round(2)
        
        # Calculate educational attainment (bachelor's degree or higher)
        if 'bachelors_plus' in df.columns and 'pop_25_plus' in df.columns:
            df['bachelors_rate'] = (df['bachelors_plus'] / df['pop_25_plus'] * 100).round(2)
        
        # Calculate renter rate
        if 'renter_occupied' in df.columns and 'total_housing_units' in df.columns:
            df['renter_rate'] = (df['renter_occupied'] / df['total_housing_units'] * 100).round(2)
        
        # Calculate rent burden (percentage of households paying 30% or more of income on rent)
        rent_burden_cols = ['rent_30_34_pct', 'rent_35_39_pct', 'rent_40_49_pct', 'rent_50_plus_pct']
        if all(col in df.columns for col in rent_burden_cols) and 'rent_total_units' in df.columns:
            # Sum all households paying 30% or more of income on rent
            df['rent_burden_households'] = df[rent_burden_cols].sum(axis=1)
            # Calculate percentage
            df['rent_burden_rate'] = (df['rent_burden_households'] / df['rent_total_units'] * 100).round(2)
            
            # Log the calculation for debugging
            logger.debug(f"Calculated rent burden for {len(df)} areas")
        else:
            missing_cols = [col for col in rent_burden_cols + ['rent_total_units'] if col not in df.columns]
            logger.warning(f"Could not calculate rent burden, missing columns: {missing_cols}")
        
        return df

def main():
    """Main function to fetch and save ACS data."""
    # Initialize the scraper with your API key
    api_key = "2104852dd7bfd83fbc9e320d650eb57decc11817"
    scraper = ACSScraper(api_key=api_key, year=2023)
    
    try:
        # Fetch and save state-level data
        state_df = scraper.fetch_state_data()
        if state_df is not None:
            print("\nState Data:")
            print(state_df[['NAME', 'poverty_rate', 'median_income']].to_string(index=False))
        
        # Fetch and save county data
        county_df = scraper.fetch_counties()
        if county_df is not None:
            print("\nCounty Data:")
            print(county_df[['NAME', 'poverty_rate', 'median_income']].to_string(index=False))
        
        # Fetch and save state house district data
        house_df = scraper.fetch_state_house_districts()
        if house_df is not None:
            print("\nState House District Data:")
            print(house_df[['NAME', 'poverty_rate', 'median_income']].to_string(index=False))
            
        # Fetch and save state senate district data
        senate_df = scraper.fetch_state_senate_districts()
        if senate_df is not None:
            print("\nState Senate District Data:")
            print(senate_df[['NAME', 'poverty_rate', 'median_income']].to_string(index=False))
        
        logger.info("\nAll data fetched and saved successfully!")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
