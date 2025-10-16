"""
School Data Processor

This script processes school data and CEP information to create a comprehensive dataset
for the Hawaii Appleseed Dashboard. It's designed to be easily updated with new data.

Usage:
    1. Place new data files in the data/raw/ directory:
       - schools_list.csv - Current school directory
       - cep_schools.csv - CEP eligibility data
    2. Run this script
    3. Processed data will be saved to data/processed/schools_processed.csv
"""
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import re
from datetime import datetime

# Configuration
class Config:
    # Directory structure
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    RAW_DIR = DATA_DIR / 'raw'
    PROCESSED_DIR = DATA_DIR / 'processed'
    
    # Input files
    INPUT_FILES = {
        'schools': 'schools_list.csv',
        'cep': 'cep_schools.csv'
    }
    
    # Output file
    OUTPUT_FILE = 'schools_processed.csv'
    
    # Date format for logging
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt=Config.DATE_FORMAT
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [Config.RAW_DIR, Config.PROCESSED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory exists: {directory}")

def clean_school_name(name):
    """
    Clean and standardize school names for matching.
    
    Args:
        name: School name to clean
        
    Returns:
        str: Cleaned school name
    """
    if not isinstance(name, str) or pd.isna(name):
        return ""
    
    # Convert to lowercase and remove extra whitespace
    name = name.lower().strip()
    
    # Remove common suffixes and special characters
    remove_phrases = [
        'elementary', 'elem', 'school', 'high', 'middle', 'intermediate',
        'inter', 'academy', 'public', 'charter', 'pcs', 'kula', 'kaiapuni'
    ]
    
    for phrase in remove_phrases:
        name = re.sub(rf'\b{re.escape(phrase)}\b', '', name)
    
    # Remove special characters and extra spaces
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def load_input_data():
    """
    Load and validate input data files.
    
    Returns:
        tuple: (schools_df, cep_df) DataFrames
    """
    logger.info("Loading input data...")
    
    # Check if input files exist
    missing_files = []
    for file_type, filename in Config.INPUT_FILES.items():
        if not (Config.RAW_DIR / filename).exists():
            missing_files.append(filename)
    
    if missing_files:
        error_msg = f"Missing required files in {Config.RAW_DIR}: {', '.join(missing_files)}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    try:
        # Load school list
        schools_df = pd.read_csv(
            Config.RAW_DIR / Config.INPUT_FILES['schools'],
            dtype={'code': str, 'zip': str},
            encoding='latin1'  # Handle special characters
        )
        
        # Clean column names
        schools_df.columns = [col.strip().lower() for col in schools_df.columns]
        
        # Standardize column names
        column_mapping = {
            'code': 'school_id',
            'name': 'school_name',
            'type': 'school_type',
            'complex': 'complex_name',
            'complex_area': 'complex_area_name',
            'district': 'complex_district',
            'island': 'island',
            'charter': 'is_charter'
        }
        
        # Rename columns and keep only the ones we need
        schools_df = schools_df.rename(columns=column_mapping)
        schools_df = schools_df[list(column_mapping.values()) + ['address', 'city', 'zip']]
        
        # Clean data
        schools_df['school_name'] = schools_df['school_name'].str.strip()
        schools_df['clean_name'] = schools_df['school_name'].apply(clean_school_name)
        
        # Load CEP data
        cep_df = pd.read_csv(
            Config.RAW_DIR / Config.INPUT_FILES['cep'],
            dtype={'school_id': str, 'enrollment': str},
            encoding='latin1'
        )
        
        # Clean CEP data
        cep_df.columns = [col.strip().lower() for col in cep_df.columns]
        cep_df['school_name'] = cep_df['school_name'].str.strip()
        cep_df['clean_name'] = cep_df['school_name'].apply(clean_school_name)
        
        # Process CEP status
        cep_df['is_cep'] = cep_df['is_cep'].notna()
        
        # Process enrollment if it exists
        if 'enrollment' in cep_df.columns:
            cep_df['enrollment'] = (
                cep_df['enrollment']
                .astype(str)
                .str.replace(r'[^\d]', '', regex=True)
                .replace('', pd.NA)
                .astype('Int64')
            )
        
        logger.info(f"Loaded {len(schools_df)} schools and {len(cep_df)} CEP records")
        return schools_df, cep_df
        
    except Exception as e:
        logger.error(f"Error loading input data: {e}", exc_info=True)
        raise

def merge_school_data(schools_df, cep_df):
    """
    Merge school list with CEP data.
    
    Args:
        schools_df: DataFrame with school information
        cep_df: DataFrame with CEP eligibility data
        
    Returns:
        DataFrame: Merged and processed school data
    """
    logger.info("Merging school and CEP data...")
    
    # First try merging on school_id
    merged = pd.merge(
        schools_df,
        cep_df[['school_id', 'is_cep', 'enrollment']],
        on='school_id',
        how='left'
    )
    
    # For schools that didn't match by ID, try by name with fuzzy matching
    unmatched = merged[merged['is_cep'].isna()].copy()
    if not unmatched.empty:
        logger.info(f"Trying to match {len(unmatched)} schools by name...")
        
        # Create a mapping of clean names to CEP data
        # Use a list to handle potential duplicates
        cep_records = []
        for _, row in cep_df.iterrows():
            cep_records.append({
                'clean_name': row['clean_name'],
                'school_id': row['school_id'],
                'is_cep': row['is_cep'],
                'enrollment': row.get('enrollment')
            })
        
        # Try to match by name and ID first, then by name only
        for idx, row in unmatched.iterrows():
            # Try exact match on clean name and school_id if available
            if 'school_id' in row and pd.notna(row['school_id']):
                matches = [r for r in cep_records 
                          if r['clean_name'] == row['clean_name'] 
                          and str(r['school_id']) == str(row['school_id'])]
                if matches:
                    match = matches[0]
                    merged.at[idx, 'is_cep'] = match['is_cep']
                    if 'enrollment' in match and pd.notna(match['enrollment']):
                        merged.at[idx, 'enrollment'] = match['enrollment']
                    continue
            
            # If no match by ID, try name only
            matches = [r for r in cep_records if r['clean_name'] == row['clean_name']]
            if len(matches) == 1:  # Only use if there's exactly one match
                match = matches[0]
                merged.at[idx, 'is_cep'] = match['is_cep']
                if 'enrollment' in match and pd.notna(match['enrollment']):
                    merged.at[idx, 'enrollment'] = match['enrollment']
    
    # Fill missing CEP status with False
    merged['is_cep'] = merged['is_cep'].fillna(False)
    
    # Add metadata
    merged['state'] = 'HI'
    merged['last_updated'] = datetime.now().strftime(Config.DATE_FORMAT)
    
    # Map islands to counties
    island_to_county = {
        'Oahu': 'Honolulu',
        'Hawaii': 'Hawaii',
        'Maui': 'Maui',
        'Molokai': 'Maui',
        'Lanai': 'Maui',
        'Kauai': 'Kauai',
        'Niihau': 'Kauai'
    }
    merged['county'] = merged['island'].map(island_to_county)
    
    # Select and order columns
    output_columns = [
        'school_id', 'school_name', 'school_type', 'is_charter',
        'address', 'city', 'zip', 'county', 'state', 'island',
        'complex_name', 'complex_area_name', 'complex_district',
        'is_cep', 'enrollment', 'last_updated'
    ]
    
    # Only include columns that exist in the dataframe
    output_columns = [col for col in output_columns if col in merged.columns]
    
    return merged[output_columns]

def save_processed_data(df):
    """
    Save the processed data to a CSV file.
    
    Args:
        df: DataFrame to save
    """
    output_path = Config.PROCESSED_DIR / Config.OUTPUT_FILE
    df.to_csv(output_path, index=False)
    logger.info(f"Processed data saved to: {output_path}")
    return output_path

def generate_summary_stats(df):
    """Generate and log summary statistics about the processed data."""
    logger.info("Generating summary statistics...")
    
    stats = {
        'total_schools': len(df),
        'cep_schools': int(df['is_cep'].sum()),
        'cep_percentage': df['is_cep'].mean() * 100,
        'by_island': df['island'].value_counts().to_dict(),
        'by_county': df['county'].value_counts().to_dict(),
        'by_school_type': df['school_type'].value_counts().to_dict()
    }
    
    logger.info(f"Total schools processed: {stats['total_schools']}")
    logger.info(f"CEP schools: {stats['cep_schools']} ({stats['cep_percentage']:.1f}%)")
    
    logger.info("\nSchools by island:")
    for island, count in stats['by_island'].items():
        logger.info(f"- {island}: {count}")
    
    return stats

def main():
    """Main function to process school data."""
    try:
        logger.info("Starting school data processing...")
        
        # Set up directories
        setup_directories()
        
        # Load and process data
        schools_df, cep_df = load_input_data()
        processed_data = merge_school_data(schools_df, cep_df)
        
        # Generate and log statistics
        stats = generate_summary_stats(processed_data)
        
        # Save the processed data
        output_path = save_processed_data(processed_data)
        
        # Print success message
        logger.info("\nProcessing complete!")
        logger.info(f"Output saved to: {output_path}")
        
        # Print a sample of the data
        print("\nSample of processed data:")
        print(processed_data[['school_id', 'school_name', 'island', 'is_cep']].head().to_string())
        
        return True
        
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    import sys
    
    # Run the main function and exit with appropriate status code
    success = main()
    sys.exit(0 if success else 1)
