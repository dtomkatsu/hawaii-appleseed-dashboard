"""
Utility functions for working with GEOIDs across different geographic levels.
"""
from typing import Dict, Any, Optional, Union
import logging

# Set up logging
logger = logging.getLogger(__name__)

class GeoIDStandardizer:
    """Class to standardize GEOIDs across different geographic levels."""
    
    # Mapping of geographic levels to their GEOID formats
    GEOID_FORMATS = {
        'state': {
            'length': 2,  # SS (State FIPS)
            'source_columns': ['state'],
            'target_columns': ['state_fips'],
            'format': lambda x: str(x.get('state', '')).zfill(2)
        },
        'county': {
            'length': 5,  # SSCCC (State + County)
            'source_columns': ['state', 'county'],
            'target_columns': ['state_fips', 'county_fips'],
            'format': lambda x: f"{x.get('state', '').zfill(2)}{x.get('county', '').zfill(3)}"
        },
        'tract': {
            'length': 11,  # SSCCCTTTTTT (State + County + Tract)
            'source_columns': ['state', 'county', 'tract'],
            'format': lambda x: f"{x.get('state', '').zfill(2)}{x.get('county', '').zfill(3)}{str(x.get('tract', '')).replace('.', '').ljust(6, '0')}"
        },
        'block group': {
            'length': 12,  # SSCCCTTTTTTB (State + County + Tract + Block Group)
            'source_columns': ['state', 'county', 'tract', 'block group'],
            'format': lambda x: f"{x.get('state', '').zfill(2)}{x.get('county', '').zfill(3)}{str(x.get('tract', '')).replace('.', '').ljust(6, '0')}{str(x.get('block group', '0')).zfill(1)}"
        },
        'state_lower': {
            'length': 5,  # SSDDD (State + District)
            'source_columns': ['sldlst'],
            'target_columns': ['house_id'],
            'format': lambda x: f"{x.get('state', '15').zfill(2)}{str(x.get('sldlst', '')).zfill(3)}"
        },
        'state_upper': {
            'length': 4,  # SSDD (State + District)
            'source_columns': ['sldust'],
            'target_columns': ['senate_id'],
            'format': lambda x: f"{x.get('state', '15').zfill(2)}{str(x.get('sldust', '')).zfill(2)}"
        }
    }
    
    @classmethod
    def standardize_geoid(cls, row: Dict[str, Any], level: str) -> str:
        """Generate a standardized GEOID for the given row and geographic level.
        
        Args:
            row: Dictionary containing the row data
            level: Geographic level ('county', 'tract', 'block group', 'state_lower', 'state_upper')
            
        Returns:
            Standardized GEOID string
        """
        if level not in cls.GEOID_FORMATS:
            logger.warning(f"Unsupported geographic level: {level}")
            return ""
            
        try:
            return cls.GEOID_FORMATS[level]['format'](row)
        except Exception as e:
            logger.error(f"Error generating GEOID for {level}: {str(e)}")
            return ""
    
    @classmethod
    def get_geoid_info(cls, level: str) -> Dict[str, Any]:
        """Get information about the GEOID structure for a given geographic level.
        
        Args:
            level: Geographic level
            
        Returns:
            Dictionary containing GEOID format information
        """
        return cls.GEOID_FORMATS.get(level, {})
    
    @classmethod
    def validate_geoid(cls, geoid: str, level: str) -> bool:
        """Validate that a GEOID matches the expected format for its level.
        
        Args:
            geoid: The GEOID to validate
            level: Geographic level
            
        Returns:
            True if the GEOID is valid, False otherwise
        """
        if level not in cls.GEOID_FORMATS:
            return False
            
        expected_length = cls.GEOID_FORMATS[level].get('length', 0)
        return len(str(geoid)) == expected_length and str(geoid).isdigit()
    
    @classmethod
    def get_geoid_from_map_data(cls, feature: Dict[str, Any], level: str) -> str:
        """Extract a standardized GEOID from map feature data.
        
        Args:
            feature: Feature dictionary from a GeoJSON or similar source
            level: Geographic level
            
        Returns:
            Standardized GEOID string
        """
        if level not in cls.GEOID_FORMATS:
            return ""
            
        # Try to find matching columns in the feature properties
        props = feature.get('properties', {})
        
        # For state legislative districts, we need to handle the special case
        if level == 'state_lower' and 'house_id' in props:
            return f"15{str(props['house_id']).zfill(3)}"
        elif level == 'state_upper' and 'senate_id' in props:
            return f"15{str(props['senate_id']).zfill(2)}"
        # For counties
        elif level == 'county' and 'county_fips' in props and 'state_fips' in props:
            return f"{props['state_fips']}{props['county_fips']}"
            
        # Fall back to generating from available fields
        row = {}
        for col in cls.GEOID_FORMATS[level].get('source_columns', []):
            if col in props:
                row[col] = props[col]
                
        return cls.standardize_geoid(row, level)
