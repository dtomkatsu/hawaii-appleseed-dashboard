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
    # Set up logging with debug level
    logger = setup_logging(level=logging.DEBUG)
    logger.info("Starting Hawaii Appleseed Dashboard - Leaflet Version with DEBUG logging")
    
    # Enhanced dropdown styling with borders and hover effects
    st.markdown("""
    <style>
        /* Base dropdown styles */
        .stSelectbox {
            color: var(--text-color) !important;
            margin-bottom: 1rem;
        }
        
        /* Dropdown container */
        [data-baseweb="select"] {
            min-height: 38px;
            border: 1px solid var(--border-color, #ccc);
            border-radius: 4px;
            transition: all 0.2s ease;
            background-color: var(--background-color, #fff);
        }
        
        /* Hover state */
        [data-baseweb="select"]:hover {
            border-color: var(--primary-color, #4c9ffe);
            box-shadow: 0 0 0 1px var(--primary-color, #4c9ffe);
        }
        
        /* Focus state */
        [data-baseweb="select"]:focus-within {
            border-color: var(--primary-color, #4c9ffe);
            box-shadow: 0 0 0 2px rgba(76, 159, 254, 0.2);
        }
        
        /* Dropdown text */
        [data-baseweb="select"] > div > div {
            color: var(--text-color) !important;
            line-height: 1.5;
            padding: 8px 12px;
        }
        
        /* Dropdown menu */
        [data-baseweb="popover"] {
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            border: 1px solid var(--border-color, #e0e0e0);
        }
        
        /* Menu items */
        [data-baseweb="menu"] {
            padding: 4px 0;
            opacity: 0;
            transform: translateY(-10px);
            animation: menuFadeIn 0.2s forwards;
        }
        
        @keyframes menuFadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        [data-baseweb="menu"] [role="option"] {
            padding: 8px 16px;
            transition: all 0.2s ease;
            opacity: 0;
            transform: translateY(-5px);
            animation: itemFadeIn 0.2s forwards;
        }
        
        /* Stagger the animation for each menu item */
        [data-baseweb="menu"] [role="option"]:nth-child(1) { animation-delay: 0.05s; }
        [data-baseweb="menu"] [role="option"]:nth-child(2) { animation-delay: 0.1s; }
        [data-baseweb="menu"] [role="option"]:nth-child(3) { animation-delay: 0.15s; }
        [data-baseweb="menu"] [role="option"]:nth-child(4) { animation-delay: 0.2s; }
        [data-baseweb="menu"] [role="option"]:nth-child(5) { animation-delay: 0.25s; }
        
        @keyframes itemFadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        [data-baseweb="menu"] [role="option"]:hover {
            background-color: var(--hover-color, #f5f8ff);
            transform: translateX(4px);
        }
    </style>
    """, unsafe_allow_html=True)
    
    try:
        # Initialize session state for county layer if not already set
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
            logger.info("Initializing session state with Counties layer")
        
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
