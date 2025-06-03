import streamlit as st
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Import views
from src.ui.map_view import create_map_view
from src.ui.acs_dashboard import ACSDashboard

# Page config
st.set_page_config(
    page_title="Hawaii Appleseed Dashboard",
    page_icon="🌺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main .block-container {
        max-width: 95%;
        padding: 2rem 2rem 6rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stDownloadButton>button {
        width: 100%;
    }
    /* Dropdown menu fixes */
    .stSelectbox div[data-baseweb="select"] > div {
        padding-top: 8px;
        padding-bottom: 8px;
        min-height: 40px;
    }
    .stSelectbox div[data-baseweb="select"] > div > div {
        line-height: 1.5 !important;
        padding-top: 4px;
        padding-bottom: 4px;
    }
    .stSelectbox [role="listbox"] [role="option"] {
        padding: 8px 12px !important;
        line-height: 1.5 !important;
    }
    .stSelectbox [role="listbox"] {
        max-height: 300px !important;
        overflow-y: auto !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Map Explorer", "ACS Data Dashboard"],
        index=0
    )
    
    if page == "Map Explorer":
        st.title("Hawaii Map Explorer")
        create_map_view(debug_info=True)
    elif page == "ACS Data Dashboard":
        acs_dashboard = ACSDashboard()
        acs_dashboard.render()
    
    # Add some basic information
    st.markdown("---")
    st.header("Map Information")
    st.markdown("""
    ### Map Layers
    The map includes the following geographic layers:
    - **State**: Hawaii state boundary
    - **Counties**: County boundaries (2022)
    - **State House Districts**: Hawaii State House legislative districts (2022)
    - **State Senate Districts**: Hawaii State Senate legislative districts (2022)
    
    ### Map Controls
    - Use the mouse wheel to zoom in and out
    - Click and drag to pan the map
    - Click the layers icon in the top-right corner to toggle layers
    
    Note: Legislative districts are based on 2022 redistricting data.
    """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Application error: {str(e)}", exc_info=True)
        st.error("An error occurred. Please check the logs for more details.")
