"""Hawaii Appleseed Dashboard - Leaflet Version."""
import sys
import logging
from pathlib import Path
import streamlit as st

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import local modules
from utils.logging_utils import setup_logging, log_error
from ui.sidebar import create_sidebar
from ui.leaflet_map_view import create_leaflet_map_view, create_data_summary

# Set page config
st.set_page_config(
    page_title="Hawaii Appleseed Dashboard",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application function for the Leaflet version."""
    # Set up logging
    logger = setup_logging()
    
    # Load custom CSS
    with open(Path(__file__).parent / "src" / "ui" / "custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    try:
        # Create sidebar and get user selections
        sidebar_config = create_sidebar()
        
        # Main content area
        st.title("Hawaii Geographic Data Explorer (Leaflet)")
        st.markdown("---")
        
        # Create two columns for the main content
        col1, col2 = st.columns([2, 1])
        
        # Left column - Leaflet Map View
        with col1:
            create_leaflet_map_view(
                debug_info=sidebar_config.get('debug_info', False)
            )
        
        # Right column - Data Summary
        with col2:
            create_data_summary()
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)

if __name__ == "__main__":
    main()
