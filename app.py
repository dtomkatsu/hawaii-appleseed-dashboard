import streamlit as st
import logging
import sys

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

# Import the simplified map view
from src.ui.map_view import create_map_view

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Hawaii Appleseed Dashboard",
        page_icon="🌺",
        layout="wide"
    )
    
    st.title("Hawaii Appleseed Dashboard")
    
    # Add some basic CSS for layout
    st.markdown("""
    <style>
    .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create a simple layout
    st.subheader("Hawaii Map")
    create_map_view(debug_info=True)
    
    # Add controls in a sidebar
    st.sidebar.subheader("Controls")
    year = st.sidebar.slider("Select Year", 2018, 2023, 2023)
    data_type = st.sidebar.selectbox(
        "Select Data Type",
        ["Housing", "Education", "Economic"]
    )
    
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
