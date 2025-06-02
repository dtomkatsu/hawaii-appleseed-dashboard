"""
Test configuration for pytest.
"""
import os
import sys
import pytest
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

@pytest.fixture
def sample_acs_data():
    """Return sample ACS data for testing."""
    return [
        {
            'NAME': 'Hawaii',
            'total_population': 1445635,
            'below_poverty': 140461,
            'total_population_poverty': 1409460,
            'median_income': 98317,
            'poverty_rate': 9.97,
            'bachelors_rate': 22.45,
            'renter_rate': 37.45,
            'rent_burden_rate': 51.9
        },
        {
            'NAME': 'State House District 1 (2022); Hawaii',
            'total_population': 24680,
            'below_poverty': 2984,
            'total_population_poverty': 24680,
            'median_income': 65123,
            'poverty_rate': 12.09,
            'bachelors_rate': 18.75,
            'renter_rate': 42.31,
            'rent_burden_rate': 48.7
        }
    ]

@pytest.fixture
def sample_geojson_data():
    """Return sample GeoJSON data for testing."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "NAME": "Hawaii",
                    "display_name": "Hawaii State",
                    "objectid": 1
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "house_id": 1,
                    "house_name": "State House District 1",
                    "county": "HAWAII",
                    "display_name": "House District 1"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.5], [0.5, 0.5], [0.5, 0], [0, 0]]]
                }
            }
        ]
    }

@pytest.fixture
def mock_session_state():
    """Mock Streamlit session state."""
    class MockSessionState(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            
        def __getattr__(self, key):
            if key in self:
                return self[key]
            return None
            
        def __setattr__(self, key, value):
            self[key] = value
    
    return MockSessionState(
        active_layer="State Boundary",
        selected_variable="poverty_rate",
        color_scheme="blue"
    )
