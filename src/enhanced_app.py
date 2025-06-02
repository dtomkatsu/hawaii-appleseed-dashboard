"""Hawaii Appleseed Dashboard - Enhanced Application."""
import streamlit as st
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Set up basic logging as fallback
def setup_logging():
    """Set up basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def log_error(logger, message):
    """Log an error message"""
    logger.error(message)

# Import local modules after path setup
from src.ui.sidebar import create_sidebar
from src.ui.map_view import create_map_view, create_data_summary

# Set page config
st.set_page_config(
    page_title="Hawaii Appleseed Dashboard (Enhanced)",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application function."""
    # Set up logging
    logger = setup_logging()
    
    # Load enhanced CSS
    css_path = Path(__file__).parent / "ui" / "enhanced_style.css"
    if not css_path.exists():
        # Try with src prefix
        css_path = Path(__file__).parent.parent / "src" / "ui" / "enhanced_style.css"
    
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    try:
        # Create sidebar and get user selections
        sidebar_config = create_sidebar()
        
        # Main content area
        st.title("Hawaii Geographic Data Explorer")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Map View", "Data Analysis", "About"])
        
        # Tab 1: Map View
        with tab1:
            # Create two columns for the main content
            col1, col2 = st.columns([3, 1])
            
            # Left column - Map View
            with col1:
                create_map_view(
                    debug_info=sidebar_config['debug_info']
                )
            
            # Right column - Data Summary
            with col2:
                create_data_summary()
        
        # Tab 2: Data Analysis
        with tab2:
            st.header("Data Analysis")
            st.write("This section will contain data tables and charts for analysis.")
            
            # Get the active layer and selected variable
            active_layer = st.session_state.get('active_layer', 'State Boundary')
            selected_variable = st.session_state.get('selected_variable', 'poverty_rate')
            
            # Display a simple data table
            from src.data.data_loader import DataLoader
            data_loader = DataLoader()
            
            # Map geo levels to their data loader equivalents
            geo_level_map = {
                'State Boundary': 'state',
                'Counties': 'county',
                'House Districts': 'house',
                'Senate Districts': 'senate'
            }
            
            geo_level = geo_level_map.get(active_layer, 'state')
            
            # Get data for the current geographic level
            data = data_loader.get_data(geo_level)
            
            if data is not None:
                st.dataframe(data)
            else:
                st.warning(f"No data available for {active_layer}")
        
        # Tab 3: About
        with tab3:
            st.header("About This Dashboard")
            st.write("""
            This dashboard provides interactive visualizations of demographic and socioeconomic data for Hawaii.
            
            ### Data Sources
            - American Community Survey (ACS) 5-Year Estimates
            - Geographic boundaries from the US Census Bureau
            
            ### Features
            - Interactive map with clickable regions
            - Detailed popups with demographic and socioeconomic data
            - Data analysis tools
            
            ### How to Use
            1. Use the sidebar to select different map layers and variables
            2. Click on regions in the map to see detailed information
            3. Switch between tabs to explore different views of the data
            """)
        
    except Exception as e:
        log_error(logger, f"Error in main application: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        if sidebar_config and sidebar_config.get('debug_info', False):
            st.exception(e)

if __name__ == "__main__":
    main()
