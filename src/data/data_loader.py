"""Refactored data loading utilities for the Hawaii Appleseed Dashboard."""

import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Optional, Union, List, Any
import datetime
import json
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class GeoLevel(Enum):
    """Geographic levels supported by the data loader."""
    STATE = "state"
    COUNTY = "county"
    HOUSE = "house"
    SENATE = "senate"


class DataType(Enum):
    """Types of data available in the dashboard."""
    ACS = "acs"
    ALICE = "alice"
    SNAP = "snap"


@dataclass
class DataConfig:
    """Configuration for data files and columns."""
    file_patterns: Dict[str, str]
    sheet_patterns: Optional[Dict[str, str]] = None
    join_columns: Optional[Dict[str, str]] = None
    id_converters: Optional[Dict[str, callable]] = None


class DataMerger:
    """Handles merging of different data sources."""
    
    def __init__(self, geo_name_mapping: Dict[str, Dict[str, str]]):
        self.geo_name_mapping = geo_name_mapping
    
    def merge_datasets(self, base_data: pd.DataFrame, merge_data: pd.DataFrame, 
                      geo_level: GeoLevel, data_type: DataType) -> pd.DataFrame:
        """Merge datasets based on geographic level and data type."""
        merge_strategies = {
            GeoLevel.STATE: self._merge_state_data,
            GeoLevel.COUNTY: self._merge_county_data,
            GeoLevel.HOUSE: self._merge_district_data,
            GeoLevel.SENATE: self._merge_district_data
        }
        
        strategy = merge_strategies.get(geo_level)
        if not strategy:
            logger.error(f"No merge strategy for {geo_level}")
            return base_data
        
        return strategy(base_data, merge_data, data_type)
    
    def _merge_state_data(self, base_data: pd.DataFrame, merge_data: pd.DataFrame, 
                         data_type: DataType) -> pd.DataFrame:
        """Merge state-level data."""
        merged = base_data.copy()
        if len(merge_data) > 0:
            merge_row = merge_data.iloc[0]
            self._add_columns_by_type(merged, merge_row, data_type)
        return merged
    
    def _merge_county_data(self, base_data: pd.DataFrame, merge_data: pd.DataFrame,
                          data_type: DataType) -> pd.DataFrame:
        """Merge county-level data with name mapping."""
        merged = base_data.copy()
        self._initialize_columns_by_type(merged, data_type)
        
        county_mapping = self._get_county_mapping(data_type)
        
        for base_idx, base_row in base_data.iterrows():
            base_county_name = base_row.get('NAME', '')
            
            for merge_idx, merge_row in merge_data.iterrows():
                merge_county = merge_row.get('name' if data_type == DataType.ALICE else 'NAME', '')
                
                if self._counties_match(base_county_name, merge_county, county_mapping):
                    self._add_columns_by_type(merged, merge_row, data_type, base_idx)
                    logger.debug(f"Matched {base_county_name} with {data_type.value} {merge_county}")
                    break
        
        return merged
    
    def _merge_district_data(self, base_data: pd.DataFrame, merge_data: pd.DataFrame,
                           data_type: DataType) -> pd.DataFrame:
        """Merge district-level data."""
        if data_type == DataType.SNAP and 'geoid' in merge_data.columns:
            return self._merge_by_geoid(base_data, merge_data, data_type)
        
        return self._merge_by_district(base_data, merge_data, data_type)
    
    def _merge_by_geoid(self, base_data: pd.DataFrame, merge_data: pd.DataFrame,
                       data_type: DataType) -> pd.DataFrame:
        """Merge data using geoid field."""
        if 'geoid' not in base_data.columns:
            base_data = self._create_geoid_column(base_data)
        
        merge_cols = self._get_merge_columns(merge_data, data_type)
        return pd.merge(base_data, merge_data[merge_cols], on='geoid', how='left')
    
    def _merge_by_district(self, base_data: pd.DataFrame, merge_data: pd.DataFrame,
                          data_type: DataType) -> pd.DataFrame:
        """Merge data using district numbers."""
        base_key = self._find_district_column(base_data)
        if not base_key or 'district' not in merge_data.columns:
            logger.warning("Could not find matching district columns")
            merged = base_data.copy()
            self._initialize_columns_by_type(merged, data_type)
            return merged
        
        merge_cols = self._get_merge_columns(merge_data, data_type)
        return pd.merge(base_data, merge_data[merge_cols], 
                       left_on=base_key, right_on='district', how='left')
    
    def _get_county_mapping(self, data_type: DataType) -> Dict[str, List[str]]:
        """Get county name mapping for data type."""
        if data_type == DataType.ALICE:
            return {
                'Honolulu County, Hawaii': ['Honolulu', 'Oahu'],
                'Hawaii County, Hawaii': ['Hawaii'],
                'Maui County, Hawaii': ['Maui'],
                'Kauai County, Hawaii': ['Kauai']
            }
        else:
            return {
                'Honolulu County, Hawaii': ['HONOLULU'],
                'Hawaii County, Hawaii': ['HAWAII'],
                'Maui County, Hawaii': ['MAUI'],
                'Kauai County, Hawaii': ['KAUAI']
            }
    
    def _counties_match(self, base_name: str, merge_name: str, 
                       mapping: Dict[str, List[str]]) -> bool:
        """Check if county names match using mapping."""
        if base_name in mapping:
            return merge_name in mapping[base_name]
        return False
    
    def _get_merge_columns(self, merge_data: pd.DataFrame, data_type: DataType) -> List[str]:
        """Get columns to merge based on data type."""
        base_cols = ['geoid'] if 'geoid' in merge_data.columns else ['district']
        
        if data_type == DataType.ALICE:
            return base_cols + ['alice_rate']
        elif data_type == DataType.SNAP:
            snap_cols = ['snap_household_rate', 'snap_benefit_annual_per_household', 'snap_benefits_annual_total']
            return base_cols + [col for col in snap_cols if col in merge_data.columns]
        
        return base_cols
    
    def _find_district_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the district column in a DataFrame."""
        possible_cols = [
            'state legislative district (lower chamber)',
            'state legislative district (upper chamber)',
            'district', 'DISTRICT'
        ]
        
        for col in possible_cols:
            if col in df.columns:
                return col
        return None
    
    def _create_geoid_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create geoid column from district information."""
        df = df.copy()
        district_col = self._find_district_column(df)
        if district_col:
            df['geoid'] = '15' + df[district_col].astype(str).str.zfill(3)
        return df
    
    def _add_columns_by_type(self, df: pd.DataFrame, source_row: pd.Series, 
                           data_type: DataType, target_idx: Optional[int] = None):
        """Add columns to DataFrame based on data type."""
        if data_type == DataType.ALICE:
            self._set_value(df, 'alice_rate', source_row.get('alice_rate'), target_idx)
        elif data_type == DataType.SNAP:
            snap_cols = ['snap_household_rate', 'snap_benefit_annual_per_household', 'snap_benefits_annual_total']
            for col in snap_cols:
                self._set_value(df, col, source_row.get(col), target_idx)
    
    def _initialize_columns_by_type(self, df: pd.DataFrame, data_type: DataType):
        """Initialize columns in DataFrame based on data type."""
        if data_type == DataType.ALICE:
            df['alice_rate'] = None
        elif data_type == DataType.SNAP:
            snap_cols = ['snap_household_rate', 'snap_benefit_annual_per_household', 'snap_benefits_annual_total']
            for col in snap_cols:
                df[col] = None
    
    def _set_value(self, df: pd.DataFrame, column: str, value: Any, 
                  target_idx: Optional[int] = None):
        """Set value in DataFrame column."""
        if target_idx is not None:
            df.loc[target_idx, column] = value
        else:
            df[column] = value


class BaseDataLoader(ABC):
    """Abstract base class for data loaders."""
    
    def __init__(self, data_dir: Path, config: DataConfig):
        self.data_dir = data_dir
        self.config = config
    
    @abstractmethod
    def load_data(self, geo_level: GeoLevel) -> Optional[pd.DataFrame]:
        """Load data for a specific geographic level."""
        pass
    
    def _validate_geo_level(self, geo_level: Union[GeoLevel, str]) -> bool:
        """Validate that the geographic level is supported."""
        if isinstance(geo_level, str):
            geo_level = geo_level.lower()
            return geo_level in ['state', 'county', 'house', 'senate']
        return geo_level in [GeoLevel.STATE, GeoLevel.COUNTY, 
                           GeoLevel.HOUSE, GeoLevel.SENATE]


class ACSDataLoader(BaseDataLoader):
    """Loader for American Community Survey data."""
    
    def load_data(self, geo_level: GeoLevel) -> Optional[pd.DataFrame]:
        """Load ACS data for a geographic level."""
        if not self._validate_geo_level(geo_level):
            logger.error(f"Invalid geographic level: {geo_level}")
            return None
        
        file_path = self.data_dir / self.config.file_patterns[geo_level.value]
        if not file_path.exists():
            logger.error(f"ACS data file not found: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path, dtype={'geoid': str})
            logger.debug(f"Loaded ACS {geo_level.value} data: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Error loading ACS {geo_level.value} data: {e}")
            return None


class ALICEDataLoader(BaseDataLoader):
    """Loader for ALICE (Asset Limited, Income Constrained, Employed) data."""
    
    def load_data(self, geo_level: Union[GeoLevel, str]) -> Optional[pd.DataFrame]:
        """Load ALICE data for a geographic level."""
        try:
            # Convert string geo_level to GeoLevel enum if needed
            if isinstance(geo_level, str):
                try:
                    geo_level = GeoLevel(geo_level.lower())
                except ValueError:
                    logger.error(f"Invalid geographic level for ALICE: {geo_level}")
                    return None
                    
            if not self._validate_geo_level(geo_level):
                logger.error(f"Unsupported geographic level for ALICE: {geo_level}")
                return None
            
            # Try multiple possible file locations
            # Get the project root directory
            project_root = Path(__file__).parent.parent.parent
            possible_paths = [
                project_root / 'data' / 'ALICE By Geography (2023).xlsx',  # Most likely location
                self.data_dir.parent / 'ALICE By Geography (2023).xlsx',
                self.data_dir / 'ALICE By Geography (2023).xlsx',
                Path('data') / 'ALICE By Geography (2023).xlsx',
                Path('ALICE By Geography (2023).xlsx'),
                Path('data/raw') / 'ALICE By Geography (2023).xlsx'
            ]
            
            alice_file = None
            for path in possible_paths:
                logger.info(f"Checking ALICE file path: {path.absolute()}")
                if path.exists():
                    alice_file = path
                    logger.info(f"Found ALICE file at: {alice_file.absolute()}")
                    break
            
            if alice_file is None:
                logger.error("ALICE data file not found in any expected location:")
                for path in possible_paths:
                    logger.error(f"  - {path.absolute()} (exists: {path.exists()})")
                # List contents of data directory for debugging
                try:
                    data_dir_contents = list(self.data_dir.parent.iterdir())
                    logger.error(f"Contents of {self.data_dir.parent}: {[f.name for f in data_dir_contents]}")
                except Exception as e:
                    logger.error(f"Could not list directory contents: {e}")
                return None
            
            try:
                # First, check what sheets are available
                import openpyxl
                wb = openpyxl.load_workbook(alice_file, read_only=True)
                available_sheets = wb.sheetnames
                logger.info(f"Available sheets in ALICE file: {available_sheets}")
                wb.close()
                
                sheet_name = self.config.sheet_patterns[geo_level.value]
                logger.info(f"Looking for sheet: {sheet_name}")
                
                if sheet_name not in available_sheets:
                    logger.error(f"Sheet '{sheet_name}' not found. Available sheets: {available_sheets}")
                    # Try to find a similar sheet name
                    for sheet in available_sheets:
                        if sheet.lower() == sheet_name.lower():
                            logger.info(f"Found case-insensitive match: {sheet}")
                            sheet_name = sheet
                            break
                    else:
                        return None
                
                df = pd.read_excel(alice_file, sheet_name=sheet_name)
                logger.info(f"Successfully read Excel sheet. Shape: {df.shape}")
                logger.info(f"Columns: {df.columns.tolist()}")
                
                df = self._standardize_alice_data(df, geo_level)
                logger.info(f"Loaded ALICE {geo_level.value} data: {df.shape}")
                return df
                
            except Exception as e:
                logger.error(f"Error reading Excel file {alice_file}: {e}", exc_info=True)
                return None
        
        except Exception as e:
            logger.error(f"Error in load_data for ALICE: {str(e)}", exc_info=True)
            # Create fallback dummy data to prevent app from breaking
            logger.warning("Creating fallback ALICE data with default values")
            return self._create_fallback_alice_data(geo_level)
    
    def _standardize_alice_data(self, df: pd.DataFrame, geo_level: Union[GeoLevel, str]) -> pd.DataFrame:
        """Standardize ALICE data columns and identifiers."""
        if df is None or df.empty:
            logger.warning("Empty or None DataFrame passed to _standardize_alice_data")
            return pd.DataFrame()
            
        df = df.copy()
        logger.info(f"Standardizing ALICE data. Initial columns: {df.columns.tolist()}")
        logger.info(f"First few rows of data:\n{df.head()}")
        
        # Standardize ALICE rate column - handle both percentage and decimal formats
        alice_cols = [
            'Percentage of Households Under ALICE Threshold',
            'ALICE Rate',
            'alice_rate',
            'pct_alice_households',
            'alice_household_percentage',  # Additional possible column name
            'alice_households'             # Additional possible column name
        ]
        
        alice_rate_found = False
        for col in alice_cols:
            if col in df.columns:
                logger.info(f"Found ALICE rate column: {col}")
                logger.info(f"Values in {col}: {df[col].head().to_list()}")
                
                # Handle potential string percentages (e.g., '35%')
                if df[col].dtype == 'object':
                    try:
                        # Try to convert string percentages to float
                        df[col] = df[col].astype(str).str.rstrip('%').astype('float') / 100.0
                        logger.info(f"Converted string percentage to float: {df[col].head().to_list()}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert column {col} to float: {e}")
                        continue
                
                # Convert to percentage if it's a decimal (0-1)
                if df[col].max() <= 1.0:
                    df['alice_rate'] = df[col] * 100
                    logger.info(f"Converted decimal to percentage (x100): {df['alice_rate'].head().to_list()}")
                else:
                    # If it's already a percentage, ensure it's not > 100 (might be 0-100 scale)
                    if df[col].max() > 100:
                        df['alice_rate'] = df[col]  # Already in percentage format
                        logger.info(f"Using values as-is (already percentage): {df['alice_rate'].head().to_list()}")
                    else:
                        df['alice_rate'] = df[col]  # Already in 0-100 format
                        logger.info(f"Using values as 0-100 percentage: {df['alice_rate'].head().to_list()}")
                
                alice_rate_found = True
                logger.info(f"Final alice_rate values: {df['alice_rate'].head().to_list()}")
                break
                
        if not alice_rate_found:
            logger.warning(f"No recognized ALICE rate column found in: {df.columns.tolist()}")
            logger.warning("Available columns: " + ", ".join(df.columns.tolist()))
            df['alice_rate'] = 0  # Default to 0 if no ALICE data found
        
        # Add geographic identifiers based on level
        if isinstance(geo_level, str):
            geo_level = geo_level.lower()
            
            if geo_level == 'state':
                df = self._standardize_state_alice(df)
            elif geo_level == 'county':
                df = self._standardize_county_alice(df)
            elif geo_level == 'house':
                df = self._standardize_house_alice(df)
            elif geo_level == 'senate':
                df = self._standardize_senate_alice(df)
        else:
            standardizers = {
                GeoLevel.STATE: self._standardize_state_alice,
                GeoLevel.COUNTY: self._standardize_county_alice,
                GeoLevel.HOUSE: self._standardize_house_alice,
                GeoLevel.SENATE: self._standardize_senate_alice
            }
            
            standardizer = standardizers.get(geo_level)
            if standardizer:
                df = standardizer(df)
        
        # Ensure we have a geoid column for merging
        if 'geoid' not in df.columns and 'GEOID' in df.columns:
            df['geoid'] = df['GEOID']
            
        return df
    
    def _standardize_state_alice(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize state-level ALICE data."""
        df['name'] = 'Hawaii'
        df['display_name'] = 'Hawaii'
        return df
    
    def _standardize_county_alice(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize county-level ALICE data."""
        if 'County' in df.columns:
            df['name'] = df['County']
            df['display_name'] = df['County']
        return df
    
    def _standardize_house_alice(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize house district ALICE data."""
        if 'District' in df.columns:
            df['district'] = df['District'].astype(int)
            df['display_name'] = df['District'].apply(lambda x: f"House District {x}")
        return df
    
    def _standardize_senate_alice(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize senate district ALICE data."""
        if 'Senate District' in df.columns:
            df['district'] = df['Senate District'].astype(int)
            df['display_name'] = df['Senate District'].apply(lambda x: f"Senate District {x}")
        return df
    
    def _create_fallback_alice_data(self, geo_level: GeoLevel) -> pd.DataFrame:
        """Create fallback ALICE data when the Excel file can't be loaded."""
        logger.warning(f"Creating fallback ALICE data for {geo_level.value}")
        
        # Create basic structure based on geo level
        if geo_level == GeoLevel.STATE:
            data = [{
                'name': 'Hawaii',
                'geoid': '15',
                'alice_rate': 35.0  # Default ALICE rate for Hawaii
            }]
        elif geo_level == GeoLevel.COUNTY:
            data = [
                {'name': 'Honolulu County, Hawaii', 'geoid': '15003', 'alice_rate': 33.0},
                {'name': 'Hawaii County, Hawaii', 'geoid': '15001', 'alice_rate': 38.0},
                {'name': 'Maui County, Hawaii', 'geoid': '15009', 'alice_rate': 36.0},
                {'name': 'Kauai County, Hawaii', 'geoid': '15007', 'alice_rate': 34.0}
            ]
        else:
            # For districts, create minimal data structure
            data = [{
                'name': f'District {i}',
                'geoid': f'15{str(i).zfill(3)}',
                'alice_rate': 35.0
            } for i in range(1, 52)]  # Hawaii has 51 house districts, 25 senate districts
        
        df = pd.DataFrame(data)
        logger.info(f"Created fallback ALICE data with {len(df)} rows")
        return df


class SNAPDataLoader(BaseDataLoader):
    """Loader for SNAP (Supplemental Nutrition Assistance Program) data."""
    
    def load_data(self, geo_level: GeoLevel) -> Optional[pd.DataFrame]:
        """Load SNAP data for a geographic level."""
        if not self._validate_geo_level(geo_level):
            logger.error(f"Invalid geographic level for SNAP: {geo_level}")
            return None
        
        file_path = self.data_dir / 'snap_benefits' / self.config.file_patterns[geo_level.value]
        if not file_path.exists():
            logger.error(f"SNAP data file not found: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path, dtype={'geoid': str})
            df = self._standardize_snap_data(df, geo_level)
            logger.debug(f"Loaded SNAP {geo_level.value} data: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Error loading SNAP {geo_level.value} data: {e}")
            return None
    
    def _standardize_snap_data(self, df: pd.DataFrame, geo_level: GeoLevel) -> pd.DataFrame:
        """Standardize SNAP data format."""
        df = df.copy()
        
        # Fix geoid format for districts
        if geo_level in [GeoLevel.HOUSE, GeoLevel.SENATE] and 'geoid' in df.columns:
            df['geoid'] = df['geoid'].apply(self._fix_geoid)
        
        # Convert percentages from decimal to percentage format
        percentage_cols = ['snap_household_rate', 'snap_participation_rate']
        for col in percentage_cols:
            if col in df.columns:
                df[col] = df[col] * 100
        
        return df
    
    def _fix_geoid(self, geoid_str: str) -> str:
        """Fix geoid format for districts."""
        geoid_str = str(geoid_str)
        if len(geoid_str) == 4 and geoid_str.startswith('15'):
            return geoid_str[:2] + '0' + geoid_str[2:]
        elif len(geoid_str) == 5 and geoid_str.startswith('0'):
            return '15' + geoid_str[3:]
        return geoid_str


class GeoJSONProcessor:
    """Handles GeoJSON processing and data merging."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.geojson_configs = {
            GeoLevel.STATE: {
                'file': 'hawaii_state_boundary.geojson',
                'id_field': 'GEOID',
                'converter': lambda x: '15'
            },
            GeoLevel.COUNTY: {
                'file': 'hawaii_county_boundaries.geojson',
                'id_field': 'GEOID',
                'converter': self._convert_county_to_fips
            },
            GeoLevel.HOUSE: {
                'file': 'Hawaii_State_House_Districts_2022.geojson',
                'id_field': 'GEOID',
                'converter': lambda x: '15' + str(x).replace('H', '').zfill(3)
            },
            GeoLevel.SENATE: {
                'file': 'Hawaii_State_Senate_Districts_2022.geojson',
                'id_field': 'GEOID',
                'converter': lambda x: '15' + str(x).replace('S', '').zfill(3)
            }
        }
    
    def get_geojson_path(self, geo_level: GeoLevel) -> Optional[Path]:
        """Get path to GeoJSON file for geographic level."""
        config = self.geojson_configs.get(geo_level)
        if not config:
            return None
        
        geojson_dir = self.base_dir / 'data' / 'Processed GeoJsons'
        geojson_path = geojson_dir / config['file']
        
        return geojson_path if geojson_path.exists() else None
    
    def merge_geojson_with_data(self, geojson_data: dict, data: pd.DataFrame,
                               geo_level: GeoLevel) -> dict:
        """Merge GeoJSON with data DataFrame."""
        if data is None or data.empty:
            logger.warning(f"No data available for merging with {geo_level.value} GeoJSON")
            return geojson_data
        
        # Standardize GeoJSON IDs
        geojson_data = self._standardize_geojson_ids(geojson_data, geo_level)
        
        # Merge data into features
        for feature in geojson_data.get('features', []):
            properties = feature.get('properties', {})
            matching_data = self._find_matching_data(properties, data, geo_level)
            
            if matching_data:
                self._add_data_to_properties(properties, matching_data)
        
        return geojson_data
    
    def _standardize_geojson_ids(self, geojson_data: dict, geo_level: GeoLevel) -> dict:
        """Standardize ID fields in GeoJSON data."""
        config = self.geojson_configs.get(geo_level)
        if not config:
            return geojson_data
        
        # Find the appropriate source field
        source_field = self._find_source_field(geojson_data, geo_level)
        if not source_field:
            return geojson_data
        
        # Convert IDs for each feature
        for feature in geojson_data.get('features', []):
            props = feature.get('properties', {})
            if source_field in props:
                try:
                    source_id = props[source_field]
                    target_id = config['converter'](source_id)
                    props[config['id_field']] = target_id
                    props['geoid'] = target_id
                except Exception as e:
                    logger.error(f"Error converting ID for {geo_level.value}: {e}")
        
        return geojson_data
    
    def _find_source_field(self, geojson_data: dict, geo_level: GeoLevel) -> Optional[str]:
        """Find the source field for ID conversion."""
        features = geojson_data.get('features', [])
        if not features:
            return None
        
        props = features[0].get('properties', {})
        
        field_mappings = {
            GeoLevel.STATE: ['state_fips'],
            GeoLevel.COUNTY: ['county_name'],
            GeoLevel.HOUSE: ['state_house', 'STATE_HOUSE', 'house_id', 'DISTRICT', 'district'],
            GeoLevel.SENATE: ['state_senate', 'STATE_SENATE', 'senate_id', 'DISTRICT', 'district']
        }
        
        possible_fields = field_mappings.get(geo_level, [])
        for field in possible_fields:
            if field in props:
                return field
        
        return None
    
    def _convert_county_to_fips(self, county_name: str) -> str:
        """Convert county name to FIPS code."""
        county_map = {
            'oahu': '15003',
            'honolulu': '15003',
            'hawaii': '15001',
            'maui': '15009',
            'kauai': '15007',
            'kalawao': '15005'
        }
        
        county_name = str(county_name).lower()
        for pattern, fips in county_map.items():
            if pattern in county_name:
                return fips
        
        return '15000'  # Default for unknown county
    
    def _find_matching_data(self, properties: dict, data: pd.DataFrame,
                           geo_level: GeoLevel) -> Optional[dict]:
        """Find matching data row for GeoJSON feature."""
        if geo_level == GeoLevel.STATE and len(data) > 0:
            return data.iloc[0].to_dict()
        
        if geo_level == GeoLevel.COUNTY:
            return self._find_county_match(properties, data)
        
        if geo_level in [GeoLevel.HOUSE, GeoLevel.SENATE]:
            return self._find_district_match(properties, data)
        
        return None
    
    def _find_county_match(self, properties: dict, data: pd.DataFrame) -> Optional[dict]:
        """Find matching county data."""
        county_name = properties.get('county_name', properties.get('NAME', ''))
        
        # Try direct matching strategies
        strategies = [
            ('NAME', county_name),
            ('NAME', f"{county_name} County, Hawaii"),
        ]
        
        # Special case for Oahu/Honolulu
        if 'oahu' in county_name.lower():
            strategies.extend([
                ('NAME', 'Honolulu County, Hawaii'),
                ('NAME', 'Honolulu')
            ])
        
        for col, value in strategies:
            if col in data.columns:
                matches = data[data[col].str.lower() == value.lower()]
                if len(matches) > 0:
                    return matches.iloc[0].to_dict()
        
        return None
    
    def _find_district_match(self, properties: dict, data: pd.DataFrame) -> Optional[dict]:
        """Find matching district data."""
        district_num = None
        
        for field in ['DISTRICT', 'house_id', 'senate_id', 'district']:
            if field in properties:
                district_num = properties[field]
                break
        
        if district_num is None:
            return None
        
        # Try matching on different columns
        for col in ['district', 'state legislative district (lower chamber)',
                   'state legislative district (upper chamber)']:
            if col in data.columns:
                matches = data[data[col] == district_num]
                if len(matches) > 0:
                    return matches.iloc[0].to_dict()
        
        return None
    
    def _add_data_to_properties(self, properties: dict, data: dict):
        """Add data to GeoJSON feature properties."""
        for key, value in data.items():
            if key not in ['index', 'level_0'] and value is not None:
                if pd.isna(value):
                    properties[key] = None
                else:
                    properties[key] = value


class DataLoader:
    """Main data loader class that coordinates all data sources."""
    
    def __init__(self, data_dir: str = 'data/processed'):
        """Initialize the data loader."""
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / data_dir
        self.data_cache = {}
        
        # Initialize data loaders
        self._init_data_loaders()
        
        # Initialize processors
        self.merger = DataMerger(self._get_geo_name_mapping())
        self.geojson_processor = GeoJSONProcessor(self.base_dir)
        
        # Available variables for the dashboard
        self.available_variables = self._get_available_variables()
        
        # Preload all data
        self._preload_data()
    
    def _init_data_loaders(self):
        """Initialize data loaders for different data types."""
        # ACS data configuration
        acs_config = DataConfig({
            'state': 'hawaii_state_acs_2023.csv',
            'county': 'hawaii_counties_acs_2023.csv',
            'house': 'hawaii_house_districts_acs_2023.csv',
            'senate': 'hawaii_senate_districts_acs_2023.csv'
        })
        
        # ALICE data configuration
        alice_config = DataConfig(
            file_patterns={},
            sheet_patterns={
                'state': 'State',
                'county': 'Counties',
                'house': 'House',
                'senate': 'Senate'
            }
        )
        
        # SNAP data configuration
        snap_config = DataConfig({
            'state': 'hawaii_state_snap_2023.csv',
            'county': 'hawaii_county_snap_2023.csv',
            'house': 'hawaii_house_district_snap_2023.csv',
            'senate': 'hawaii_senate_district_snap_2023.csv'
        })
        
        self.loaders = {
            DataType.ACS: ACSDataLoader(self.data_dir, acs_config),
            DataType.ALICE: ALICEDataLoader(self.data_dir, alice_config),
            DataType.SNAP: SNAPDataLoader(self.data_dir, snap_config)
        }
    
    def _get_geo_name_mapping(self) -> Dict[str, Dict[str, str]]:
        """Get geographic name mappings."""
        return {
            'county': {
                'Honolulu': 'Oahu',
                'Hawaii': 'Hawaii',
                'Maui': 'Maui',
                'Kauai': 'Kauai'
            }
        }
    
    def _get_available_variables(self) -> Dict[str, str]:
        """Get available variables and their display names."""
        return {
            'poverty_rate': 'Poverty Rate (%)',
            'median_income': 'Median Household Income ($)',
            'population': 'Total Population',
            'median_age': 'Median Age',
            'bachelors_degree': 'Bachelor\'s Degree or Higher (%)',
            'unemployment_rate': 'Unemployment Rate (%)',
            'median_rent': 'Median Rent ($)',
            'median_home_value': 'Median Home Value ($)',
            'renter_occupied': 'Renter-Occupied Housing (%)',
            'rent_burden_rate': 'Rent Burden (% paying 30%+ of income on rent)',
            'no_health_insurance': 'No Health Insurance (%)',
            'alice_rate': 'ALICE Households (%)',
            'snap_household_rate': 'SNAP Households (%)',
            'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit ($)',
            'snap_benefits_annual_total': 'Total Annual SNAP Benefits ($)'
        }
    
    def _preload_data(self):
        """Preload all data at initialization."""
        for geo_level in GeoLevel:
            for data_type in DataType:
                try:
                    self._load_and_cache_data(data_type, geo_level)
                except Exception as e:
                    logger.error(f"Error preloading {data_type.value} {geo_level.value} data: {e}")
    
    def _load_and_cache_data(self, data_type: DataType, geo_level: GeoLevel):
        """Load and cache data for a specific type and geographic level."""
        cache_key = f"{data_type.value}_{geo_level.value}"
        
        if cache_key not in self.data_cache:
            loader = self.loaders.get(data_type)
            if loader:
                print(f"DEBUG: Loading {data_type.value} data for {geo_level.value}")
                data = loader.load_data(geo_level)
                
                # Log the columns in the loaded data for debugging
                if data is not None and not data.empty:
                    print(f"DEBUG: Loaded {data_type.value} data columns: {data.columns.tolist()}")
                    if 'median_rent' in data.columns:
                        print(f"DEBUG: Found median_rent in {data_type.value} data. First 5 values: {data['median_rent'].head().tolist()}")
                    elif 'b25064_001e' in [col.lower() for col in data.columns]:
                        print(f"DEBUG: Found b25064_001e in {data_type.value} data. First 5 values: {data['b25064_001e'].head().tolist()}")
                    else:
                        print(f"DEBUG: median_rent NOT FOUND in {data_type.value} data columns")
                
                self.data_cache[cache_key] = data
    
    def get_data(self, geo_level: str) -> Optional[pd.DataFrame]:
        """Get combined data for a geographic level."""
        geo_enum = GeoLevel(geo_level)
        
        # Get individual datasets
        acs_data = self.data_cache.get(f"{DataType.ACS.value}_{geo_level}")
        alice_data = self.data_cache.get(f"{DataType.ALICE.value}_{geo_level}")
        snap_data = self.data_cache.get(f"{DataType.SNAP.value}_{geo_level}")
        
        # Log the datasets we found
        print(f"DEBUG: Found datasets - ACS: {acs_data is not None}, ALICE: {alice_data is not None}, SNAP: {snap_data is not None}")
        
        # Start with ACS data as base
        merged_data = acs_data.copy() if acs_data is not None else None
        
        # Log ACS data columns before merging
        if merged_data is not None:
            print(f"DEBUG: ACS data columns before merging: {merged_data.columns.tolist()}")
            if 'median_rent' in merged_data.columns:
                print(f"DEBUG: median_rent in ACS data before merging: {merged_data['median_rent'].head().tolist()}")
        
        # Merge additional datasets
        if merged_data is not None and alice_data is not None:
            print(f"DEBUG: Merging ALICE data")
            merged_data = self.merger.merge_datasets(merged_data, alice_data, geo_enum, DataType.ALICE)
            print(f"DEBUG: After ALICE merge, columns: {merged_data.columns.tolist()}")
        
        if merged_data is not None and snap_data is not None:
            print(f"DEBUG: Merging SNAP data")
            merged_data = self.merger.merge_datasets(merged_data, snap_data, geo_enum, DataType.SNAP)
            print(f"DEBUG: After SNAP merge, columns: {merged_data.columns.tolist()}")
            
        # Log final columns and median_rent if available
        if merged_data is not None:
            print(f"DEBUG: Final merged data columns: {merged_data.columns.tolist()}")
            if 'median_rent' in merged_data.columns:
                print(f"DEBUG: median_rent in final merged data: {merged_data['median_rent'].head().tolist()}")
            else:
                print("DEBUG: median_rent NOT FOUND in final merged data columns")
        
        return merged_data
    
    def get_all_data_for_geo(self, geo_id: str) -> Dict[str, Any]:
        """Get all available data for a specific geography ID."""
        result = {
            "id": geo_id,
            "name": "",
            "demographics": {},
            "economic": {},
            "housing": {},
            "snap": {},
            "tax_credits": {}
        }
        
        print(f"DEBUG: Getting data for geo_id: {geo_id}")
        
        try:
            geo_level = self._determine_geo_level(geo_id)
            if not geo_level:
                logger.warning(f"Could not determine geo level for ID: {geo_id}")
                return result
            
            # Get merged data for the geographic level
            data = self.get_data(geo_level.value)
            if data is None or data.empty:
                logger.warning(f"No data available for {geo_level.value}")
                return result
            
            # Find the specific geography
            print(f"DEBUG: Looking for geo_id: {geo_id} in data")
            print(f"DEBUG: Available geoids: {data['geoid'].head().tolist()}")
            
            geo_row = data[data['geoid'] == str(geo_id)]
            if geo_row.empty:
                logger.warning(f"No data found for geography ID: {geo_id}")
                print(f"DEBUG: Could not find geo_id: {geo_id} in data")
                return result
                
            print(f"DEBUG: Found matching row. Columns: {geo_row.columns.tolist()}")
            if 'median_rent' in geo_row.columns:
                print(f"DEBUG: median_rent value: {geo_row['median_rent'].values[0]}")
            else:
                print("DEBUG: median_rent column not found in the row")
            
            geo_row = geo_row.iloc[0]
            result = self._build_geography_result(result, geo_row)
            
        except Exception as e:
            logger.error(f"Error getting data for geography {geo_id}: {e}")
        
        return result
    
    def _determine_geo_level(self, geo_id: str) -> Optional[GeoLevel]:
        """Determine geographic level from ID length."""
        geo_level_map = {
            2: GeoLevel.STATE,
            5: GeoLevel.COUNTY,
            7: GeoLevel.HOUSE,
            8: GeoLevel.SENATE
        }
        return geo_level_map.get(len(str(geo_id)))
    
    def _build_geography_result(self, result: Dict[str, Any], geo_row: pd.Series) -> Dict[str, Any]:
        """Build the result dictionary from a geography data row."""
        print(f"Debug - Raw geo_row columns: {geo_row.index.tolist()}")  # Debug: Print all available columns
        
        result['name'] = geo_row.get('NAME', f"Geography {result['id']}")
        
        # Log median_rent value if it exists
        median_rent = self._safe_get(geo_row, 'median_rent')
        print(f"Debug - Raw median_rent value: {median_rent}")  # Debug: Print raw median_rent value
        
        # Demographics
        result['demographics'] = {
            'population': self._safe_get(geo_row, 'total_population'),
            'median_age': self._safe_get(geo_row, 'median_age'),
            'population_by_race': {
                'White': self._safe_get(geo_row, 'white_alone', 0),
                'Native Hawaiian/Pacific Islander': self._safe_get(geo_row, 'nhpi_alone', 0),
                'Asian': self._safe_get(geo_row, 'asian_alone', 0),
                'Two or More Races': self._safe_get(geo_row, 'two_or_more_races', 0),
                'Other': self._safe_get(geo_row, 'other_race', 0)
            }
        }
        
        # Economic indicators
        result['economic'] = {
            'median_income': self._safe_get(geo_row, 'median_income'),
            'poverty_rate': self._safe_get(geo_row, 'poverty_rate'),
            'unemployment_rate': self._safe_get(geo_row, 'unemployment_rate'),
            'alice_rate': self._safe_get(geo_row, 'alice_rate')
        }
        
        # Housing indicators
        result['housing'] = {
            'median_home_value': self._safe_get(geo_row, 'median_home_value'),
            'median_rent': median_rent,  # Use the value we already retrieved
            'homeownership_rate': self._safe_get(geo_row, 'homeownership_rate'),
            'rent_burden_rate': self._safe_get(geo_row, 'rent_burden_rate'),
            'severe_rent_burden_rate': self._safe_get(geo_row, 'severe_rent_burden_rate')
        }
        
        print(f"Debug - Final housing data: {result['housing']}")  # Debug: Print final housing data
        
        # SNAP data
        result['snap'] = {
            'snap_household_rate': self._safe_get(geo_row, 'snap_household_rate'),
            'snap_benefit_annual_per_household': self._safe_get(geo_row, 'snap_benefit_annual_per_household'),
            'snap_benefits_annual_total': self._safe_get(geo_row, 'snap_benefits_annual_total')
        }
        
        return result
    
    def _safe_get(self, series: pd.Series, key: str, default: Any = None) -> Any:
        """Safely get a value from a pandas Series, handling NaN values."""
        value = series.get(key, default)
        return None if pd.isna(value) else value
    
    def get_available_variables(self) -> Dict[str, str]:
        """Get available variables and their display names."""
        return self.available_variables
    
    def get_variable_values(self, geo_level: str, variable: str) -> Optional[pd.Series]:
        """Get values for a specific variable at a geographic level."""
        df = self.get_data(geo_level)
        if df is None or variable not in df.columns:
            if df is not None:
                logger.error(f"Variable {variable} not found in {geo_level} data. "
                           f"Available columns: {list(df.columns)}")
            return None
        return df[variable]
    
    def get_geojson_path(self, geo_level: str) -> Optional[Path]:
        """Get path to GeoJSON file for a geographic level."""
        try:
            geo_enum = GeoLevel(geo_level)
            return self.geojson_processor.get_geojson_path(geo_enum)
        except ValueError:
            logger.error(f"Invalid geographic level: {geo_level}")
            return None
    
    def merge_geojson_with_data(self, geojson_data: dict, geo_level: str) -> dict:
        """Merge GeoJSON with data for a geographic level."""
        try:
            geo_enum = GeoLevel(geo_level)
            data = self.get_data(geo_level)
            return self.geojson_processor.merge_geojson_with_data(geojson_data, data, geo_enum)
        except ValueError:
            logger.error(f"Invalid geographic level: {geo_level}")
            return geojson_data
        except Exception as e:
            logger.error(f"Error merging GeoJSON with data for {geo_level}: {e}")
            return geojson_data


# Legacy compatibility functions (if needed for existing code)
def load_acs_data(geo_level: str) -> Optional[pd.DataFrame]:
    """Legacy function for loading ACS data."""
    loader = DataLoader()
    return loader.data_cache.get(f"{DataType.ACS.value}_{geo_level}")


def load_alice_data(geo_level: str) -> Optional[pd.DataFrame]:
    """Legacy function for loading ALICE data."""
    loader = DataLoader()
    return loader.data_cache.get(f"{DataType.ALICE.value}_{geo_level}")


def load_snap_data(geo_level: str) -> Optional[pd.DataFrame]:
    """Legacy function for loading SNAP data."""
    loader = DataLoader()
    return loader.data_cache.get(f"{DataType.SNAP.value}_{geo_level}")


# Example usage and testing
if __name__ == "__main__":
    # Initialize the data loader
    loader = DataLoader()
    
    # Test loading different data types
    for geo_level in ['state', 'county', 'house', 'senate']:
        print(f"\n=== Testing {geo_level.upper()} level ===")
        
        # Get combined data
        combined_data = loader.get_data(geo_level)
        if combined_data is not None:
            print(f"Combined data shape: {combined_data.shape}")
            print(f"Columns: {list(combined_data.columns)[:10]}...")  # First 10 columns
        else:
            print("No combined data available")
        
        # Test specific geography lookup (if data exists)
        if combined_data is not None and not combined_data.empty:
            first_geoid = combined_data['geoid'].iloc[0] if 'geoid' in combined_data.columns else None
            if first_geoid:
                geo_data = loader.get_all_data_for_geo(first_geoid)
                print(f"Sample geography data for {first_geoid}: {geo_data['name']}")
    
    # Test available variables
    variables = loader.get_available_variables()
    print(f"\nAvailable variables: {len(variables)}")
    for var, desc in list(variables.items())[:5]:  # First 5 variables
        print(f"  {var}: {desc}")
    
    print("\nData loader initialization and testing complete!")
    