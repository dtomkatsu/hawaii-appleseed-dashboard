#!/usr/bin/env python3
"""
Fetch public transportation percentage data from ACS S0802 table and add to existing ACS CSV files.
"""

import pandas as pd
import requests
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_acs_detailed_data(variables, level='county', state='15', year=2023):
    """Fetch data from ACS Detailed Tables API."""
    base_url = f"https://api.census.gov/data/{year}/acs/acs5"
    
    # Map level to Census geography
    geo_mapping = {
        'state': ('state', '15'),
        'county': ('county', '*'),
        'state_lower': ('state legislative district (lower chamber)', '*'),
        'state_upper': ('state legislative district (upper chamber)', '*')
    }
    
    if level not in geo_mapping:
        raise ValueError(f"Unsupported geographic level: {level}")
    
    # Build parameters
    params = {
        'get': ','.join(variables + ['NAME']),
        'for': f'{geo_mapping[level][0]}:{geo_mapping[level][1]}',
        'in': f'state:{state}'
    }
    
    if level == 'state':
        params = {
            'get': ','.join(variables + ['NAME']),
            'for': f'state:{state}'
        }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.error(f"Error fetching {level} data: {e}")
        return None

def fetch_and_add_public_transport_data():
    """Fetch public transportation data and add to existing ACS CSV files."""
    
    # B08301_001E = Total workers, B08301_010E = Public transportation workers
    transport_vars = ['B08301_001E', 'B08301_010E']
    
    data_dir = Path('data/processed')
    
    # Geographic levels and their corresponding files
    geo_levels = {
        'state': 'hawaii_state_acs_2023.csv',
        'county': 'hawaii_counties_acs_2023.csv', 
        'state_lower': 'hawaii_house_districts_acs_2023.csv',
        'state_upper': 'hawaii_senate_districts_acs_2023.csv'
    }
    
    for level, filename in geo_levels.items():
        logger.info(f"Processing {level} data...")
        
        # Fetch transportation data from API
        transport_data = get_acs_detailed_data(transport_vars, level=level)
        
        if not transport_data or len(transport_data) < 2:
            logger.warning(f"No transportation data found for {level}")
            continue
            
        # Convert to DataFrame
        headers = transport_data[0]
        rows = transport_data[1:]
        transport_df = pd.DataFrame(rows, columns=headers)
        
        # Clean up column names and calculate percentage
        transport_df.columns = transport_df.columns.str.lower()
        transport_df['total_workers'] = pd.to_numeric(transport_df['b08301_001e'], errors='coerce')
        transport_df['public_transport_workers'] = pd.to_numeric(transport_df['b08301_010e'], errors='coerce')
        
        # Calculate percentage: (public transport workers / total workers) * 100
        transport_df['public_transportation_pct'] = (
            transport_df['public_transport_workers'] / transport_df['total_workers'] * 100
        ).fillna(0)
        
        # Create GEOID for merging
        if level == 'state':
            transport_df['geoid'] = transport_df['state'].astype(str)
        elif level == 'county':
            transport_df['geoid'] = (transport_df['state'].astype(str) + 
                                   transport_df['county'].astype(str).str.zfill(3))
        elif level == 'state_lower':
            transport_df['geoid'] = (transport_df['state'].astype(str) + 
                                   transport_df['state legislative district (lower chamber)'].astype(str).str.zfill(3))
        elif level == 'state_upper':
            transport_df['geoid'] = (transport_df['state'].astype(str) + 
                                   transport_df['state legislative district (upper chamber)'].astype(str).str.zfill(3))
        
        # Load existing ACS file
        acs_file = data_dir / filename
        if not acs_file.exists():
            logger.warning(f"ACS file not found: {acs_file}")
            continue
            
        acs_df = pd.read_csv(acs_file)
        
        # Ensure geoid columns are strings for proper matching
        acs_df['geoid'] = acs_df['geoid'].astype(str)
        transport_df['geoid'] = transport_df['geoid'].astype(str)
        
        # Merge transportation data
        merge_cols = ['geoid', 'public_transportation_pct']
        acs_df = acs_df.merge(transport_df[merge_cols], on='geoid', how='left')
        
        # Save updated file
        acs_df.to_csv(acs_file, index=False)
        logger.info(f"Updated {filename} with public transportation data")
        logger.info(f"Added public_transportation_pct to {len(acs_df)} records")

if __name__ == "__main__":
    fetch_and_add_public_transport_data()
    print("Public transportation data fetch complete!")
