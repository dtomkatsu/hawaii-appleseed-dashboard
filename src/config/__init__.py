"""Configuration module for the Hawaii Appleseed Dashboard."""
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data" / "Processed GeoJsons"
LOG_DIR = BASE_DIR / "logs"

# GeoJSON files
GEOJSON_FILES = {
    'State': DATA_DIR / 'hawaii_state_boundary.geojson',
    'Counties': DATA_DIR / 'hawaii_county_boundaries.geojson',
    'State House Districts': DATA_DIR / 'Hawaii_State_House_Districts_2022.geojson',
    'State Senate Districts': DATA_DIR / 'Hawaii_State_Senate_Districts_2022.geojson'
}
