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

# Set page config
st.set_page_config(
    page_title="Geography Detail View",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for full-width display
st.markdown("""
    <style>
        /* Main container adjustments */
        .main .block-container {
            padding: 2rem 1rem !important;
            max-width: 100% !important;
            width: 100% !important;
        }
        
        /* Full width for the main content area */
        .main {
            padding: 0 !important;
            max-width: 100% !important;
        }
        
        /* Ensure content takes full width */
        .stApp {
            max-width: 100% !important;
            padding: 0 !important;
        }
        
        /* Fix for streamlit report view */
        .reportview-container .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        
        /* Make sure all direct children take full width */
        .stApp > div {
            max-width: 100% !important;
        }
        
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
