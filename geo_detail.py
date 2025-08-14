"""Standalone Geography Detail Page for Hawaii Appleseed Dashboard."""
import sys
import logging
from pathlib import Path
import streamlit as st

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import local modules
from utils.logging_utils import setup_logging
from ui.geo_detail_view import display_geo_detail_view

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Note: set_page_config is handled in the main app file (run_leaflet.py)

# Suppress deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Import and apply full-width layout utility
sys.path.append(str(Path(__file__).parent))
from src.ui.full_width_utils import set_full_width_layout
set_full_width_layout()

# Additional custom styles specific to this page
st.markdown("""
    <style>
        /* Chart and content containers */
        .stPlotlyChart, .stDataFrame, .element-container {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# Add logo and header
col1, col2 = st.columns([1, 10])
with col1:
    # Try to load logo
    try:
        logo_path = Path(__file__).parent / "static" / "images" / "logo.png"
        st.image(str(logo_path), width=150, use_column_width=False)
    except Exception as e:
        st.write("Hawaii Appleseed")
        
with col2:
    st.markdown("<h1 style='color: #3a7710; margin: 0; padding-top: 15px; line-height: 1;'>Geography Detail View</h1>", unsafe_allow_html=True)

# Get the geography ID from URL parameters
geo_id = st.query_params.get("geo_id")

# Display the geography detail view
display_geo_detail_view(geo_id)

# Add footer
st.markdown("---")
st.markdown("© Hawaii Appleseed Center for Law and Economic Justice")
