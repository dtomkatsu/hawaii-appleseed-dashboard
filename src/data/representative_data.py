"""Representative data loader for Hawaii House Districts."""

import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class RepresentativeDataLoader:
    """Loads and manages representative data for Hawaii House Districts."""
    
    def __init__(self):
        self.data_path = Path(__file__).parent.parent.parent / "data" / "processed"
        self.rep_data = None
        self._load_data()
    
    def _load_data(self):
        """Load representative data from CSV file."""
        try:
            csv_path = self.data_path / "hawaii_house_districts_2025_complete.csv"
            if csv_path.exists():
                self.rep_data = pd.read_csv(csv_path)
                # Ensure District column is string for consistent matching
                self.rep_data['District'] = self.rep_data['District'].astype(str)
                logger.info(f"Loaded representative data for {len(self.rep_data)} districts")
            else:
                logger.warning(f"Representative data file not found: {csv_path}")
                self.rep_data = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading representative data: {e}")
            self.rep_data = pd.DataFrame()
    
    def get_representative_info(self, district_id: str) -> Dict[str, Optional[str]]:
        """Get representative information for a given district ID."""
        if self.rep_data is None or self.rep_data.empty:
            return {
                'representative_name': None,
                'party': None,
                'areas_covered': None,
                'full_representative': None
            }
        
        # Try to match by district number
        # Extract district number from various formats (15001, 1, etc.)
        district_num = self._extract_district_number(district_id)
        
        if district_num:
            match = self.rep_data[self.rep_data['District'] == district_num]
            if not match.empty:
                row = match.iloc[0]
                return {
                    'representative_name': row.get('Representative_Name'),
                    'party': row.get('Party'),
                    'areas_covered': row.get('Areas_Covered'),
                    'full_representative': row.get('Representative')
                }
        
        logger.debug(f"No representative data found for district ID: {district_id}")
        return {
            'representative_name': None,
            'party': None,
            'areas_covered': None,
            'full_representative': None
        }
    
    def _extract_district_number(self, district_id: str) -> Optional[str]:
        """Extract district number from various ID formats."""
        if not district_id:
            return None
        
        # Handle formats like "15001", "15002", etc. (extract last 1-2 digits)
        if district_id.startswith('150') and len(district_id) == 5:
            district_num = district_id[3:]  # Get last 2 digits
            # Remove leading zero if present
            return str(int(district_num))
        
        # Handle direct district numbers like "1", "22", etc.
        try:
            return str(int(district_id))
        except ValueError:
            pass
        
        return None
    
    def get_all_representatives(self) -> pd.DataFrame:
        """Get all representative data."""
        return self.rep_data.copy() if self.rep_data is not None else pd.DataFrame()

# Global instance
_rep_loader = None

def get_representative_loader() -> RepresentativeDataLoader:
    """Get the global representative data loader instance."""
    global _rep_loader
    if _rep_loader is None:
        _rep_loader = RepresentativeDataLoader()
    return _rep_loader
