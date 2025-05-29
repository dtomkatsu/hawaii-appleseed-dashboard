"""
Debug script to analyze the data joining between GeoJSON and CSV files
"""
import json
import pandas as pd
from pathlib import Path
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/debug_join.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def debug_data_join():
    """Debug the data joining process between GeoJSON and CSV files."""
    logger.info("Starting detailed data join debugging...")
    
    # Base directory
    base_dir = Path(__file__).parent.parent
    
    # Create debug directory
    debug_dir = base_dir / 'logs' / 'debug_data'
    debug_dir.mkdir(exist_ok=True, parents=True)
    
    # Load GeoJSON files
    geojson_dir = base_dir / 'data' / 'Processed GeoJsons'
    geojson_files = {
        'house': 'Hawaii_State_House_Districts_2022.geojson',
        'senate': 'Hawaii_State_Senate_Districts_2022.geojson'
    }
    
    # Load CSV files
    csv_dir = base_dir / 'data' / 'processed'
    csv_files = {
        'house': 'hawaii_house_districts_acs_2023.csv',
        'senate': 'hawaii_senate_districts_acs_2023.csv'
    }
    
    # Process each geographic level
    for geo_level, geojson_file in geojson_files.items():
        logger.info(f"=== Analyzing {geo_level} level ===")
        
        # Load GeoJSON
        try:
            geojson_path = geojson_dir / geojson_file
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            # Load CSV
            csv_path = csv_dir / csv_files.get(geo_level)
            df = pd.read_csv(csv_path)
            
            # Save sample data for debugging
            with open(debug_dir / f"{geo_level}_geojson_sample.json", 'w') as f:
                json.dump(geojson_data['features'][:5], f, indent=2)
            
            df.head(10).to_csv(debug_dir / f"{geo_level}_csv_sample.csv", index=False)
            
            # Extract IDs from GeoJSON
            geojson_ids = []
            for feature in geojson_data.get('features', []):
                props = feature.get('properties', {})
                feature_id = None
                
                # Try different ID fields
                if geo_level == 'house':
                    if 'house_id' in props:
                        feature_id = props['house_id']
                    elif 'state_house' in props:
                        feature_id = props['state_house']
                elif geo_level == 'senate':
                    if 'senate_id' in props:
                        feature_id = props['senate_id']
                    elif 'state_senate' in props:
                        feature_id = props['state_senate']
                
                if feature_id:
                    geojson_ids.append(str(feature_id))
                    
                    # Log the first 5 features in detail
                    if len(geojson_ids) <= 5:
                        logger.info(f"GeoJSON Feature {len(geojson_ids)}: ID={feature_id}, Properties={list(props.keys())}")
            
            # Extract IDs from CSV
            csv_ids = df['geoid'].astype(str).tolist()
            
            # Log CSV data
            logger.info(f"CSV columns: {df.columns.tolist()}")
            for i in range(min(5, len(df))):
                logger.info(f"CSV Row {i+1}: geoid={df.iloc[i]['geoid']}, poverty_rate={df.iloc[i]['poverty_rate']}")
            
            # Test ID conversion
            logger.info("Testing ID conversion:")
            for i, geoid in enumerate(geojson_ids[:5]):
                # For house districts
                if geo_level == 'house':
                    if geoid.startswith('H'):
                        # Convert H01 to 15001
                        converted = '15' + geoid[1:].zfill(3)
                    else:
                        # Convert numeric ID to 15xxx format
                        converted = '15' + str(geoid).zfill(3)
                    
                    logger.info(f"House ID conversion: {geoid} -> {converted}")
                    
                    # Check if in CSV
                    matching_rows = df[df['geoid'] == converted]
                    if not matching_rows.empty:
                        logger.info(f"  MATCH FOUND in CSV: {converted}")
                        # Get the poverty rate
                        poverty_rate = matching_rows['poverty_rate'].values[0]
                        logger.info(f"  Poverty rate: {poverty_rate}")
                    else:
                        logger.info(f"  NO MATCH in CSV for {converted} (exact comparison)")
                        
                        # Try case-insensitive comparison
                        for csv_id in csv_ids:
                            if csv_id.lower() == converted.lower():
                                logger.info(f"  CASE-INSENSITIVE MATCH: {csv_id}")
                                poverty_rate = df[df['geoid'] == csv_id]['poverty_rate'].values[0]
                                logger.info(f"  Poverty rate: {poverty_rate}")
                                break
                
                # For senate districts
                elif geo_level == 'senate':
                    if geoid.startswith('S'):
                        # Convert S01 to 15001
                        converted = '15' + geoid[1:].zfill(3)
                    else:
                        # Convert numeric ID to 15xxx format
                        converted = '15' + str(geoid).zfill(3)
                    
                    logger.info(f"Senate ID conversion: {geoid} -> {converted}")
                    
                    # Check if in CSV
                    matching_rows = df[df['geoid'] == converted]
                    if not matching_rows.empty:
                        logger.info(f"  MATCH FOUND in CSV: {converted}")
                        # Get the poverty rate
                        poverty_rate = matching_rows['poverty_rate'].values[0]
                        logger.info(f"  Poverty rate: {poverty_rate}")
                    else:
                        logger.info(f"  NO MATCH in CSV for {converted} (exact comparison)")
                        
                        # Try case-insensitive comparison
                        for csv_id in csv_ids:
                            if csv_id.lower() == converted.lower():
                                logger.info(f"  CASE-INSENSITIVE MATCH: {csv_id}")
                                poverty_rate = df[df['geoid'] == csv_id]['poverty_rate'].values[0]
                                logger.info(f"  Poverty rate: {poverty_rate}")
                                break
            
            # Check for matches
            matches = []
            for geoid in geojson_ids:
                # Try different formats
                potential_ids = []
                
                # Original ID
                potential_ids.append(geoid)
                
                # For house districts
                if geo_level == 'house':
                    if geoid.startswith('H'):
                        # Convert H01 to 15001
                        potential_ids.append('15' + geoid[1:].zfill(3))
                    else:
                        # Convert numeric ID to 15xxx format
                        potential_ids.append('15' + str(geoid).zfill(3))
                
                # For senate districts
                elif geo_level == 'senate':
                    if geoid.startswith('S'):
                        # Convert S01 to 15001
                        potential_ids.append('15' + geoid[1:].zfill(3))
                    else:
                        # Convert numeric ID to 15xxx format
                        potential_ids.append('15' + str(geoid).zfill(3))
                
                # Check if any potential ID matches
                for pid in potential_ids:
                    if pid in csv_ids:
                        matches.append((geoid, pid))
                        break
            
            # Log match statistics
            logger.info(f"Match statistics for {geo_level}:")
            logger.info(f"  Total GeoJSON features: {len(geojson_ids)}")
            logger.info(f"  Total CSV rows: {len(csv_ids)}")
            logger.info(f"  Matched features: {len(matches)}")
            logger.info(f"  Match percentage: {len(matches)/len(geojson_ids)*100:.1f}%")
            
            # Log first few matches
            for i, (orig_id, matched_id) in enumerate(matches[:5]):
                logger.info(f"  Match {i+1}: {orig_id} -> {matched_id}")
                
                # Get the poverty rate for this match
                if matched_id in csv_ids:
                    poverty_rate = df[df['geoid'] == matched_id]['poverty_rate'].values[0]
                    logger.info(f"    Poverty rate: {poverty_rate}")
            
        except Exception as e:
            logger.error(f"Error processing {geo_level}: {str(e)}", exc_info=True)
    
    logger.info("Data join debugging complete.")

if __name__ == "__main__":
    debug_data_join()
