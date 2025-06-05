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
    initial_sidebar_state="collapsed"
)

# Hide the sidebar and its toggle button
st.markdown("""
    <style>
        /* Hide sidebar and all related elements */
        section[data-testid="stSidebar"],
        div[data-testid="stSidebarNav"],
        div[data-testid="stSidebarUserContent"],
        div[data-testid="collapsedControl"],
        div[data-testid="stToolbar"],
        .stApp > header,
        .stApp > div:first-child > div:first-child > div:first-child > div:first-child {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            max-width: 0 !important;
            max-height: 0 !important;
            min-width: 0 !important;
            min-height: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
            position: absolute !important;
            z-index: -1000 !important;
        }
        
        /* Make Data Variable dropdown adjust to content width */
        .stSelectbox > div[data-baseweb="select"] > div {
            width: auto !important;
            min-width: 200px;  /* Minimum width to prevent it from being too narrow */
        }
        
        /* Ensure the dropdown options can be as wide as needed */
        .stSelectbox > div[data-baseweb="select"] > div > div {
            width: auto !important;
            max-width: 100vw;  /* Don't exceed viewport width */
        }
        
        /* Make the dropdown options container adjust to content */
        .stSelectbox > div[data-baseweb="select"] > div > div > div {
            width: auto !important;
            min-width: 100%;
        }
        
        /* Ensure the selected value is fully visible */
        .stSelectbox > div[data-baseweb="select"] > div > div > div > div {
            white-space: nowrap;
            overflow: visible;
            text-overflow: unset;
        }
        
        /* Adjust main content layout */
        .stApp > div:first-child {
            padding-top: 1rem;
        }
        
        /* Remove extra padding from main content */
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100% !important;
        }
        
        /* Remove any remaining space where sidebar was */
        .stApp > div:first-child > div:first-child > div:first-child {
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Hide the specific sidebar toggle SVG */
        svg.e10vaf9m1.st-emotion-cache-1f3w014.ex0cdmw0,
        svg[viewBox="0 0 24 24"][fill="currentColor"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            opacity: 0 !important;
            position: absolute !important;
            z-index: -1000 !important;
        }
        
        /* Hide the parent button if needed */
        button[title="View app navigation"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# Add clean CSS for dropdowns
st.markdown("""
<style>
    /* Base dropdown styles */
    .stSelectbox > div > div {
        min-height: 40px;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Dropdown menu items */
    [data-baseweb="menu"] [role="option"] {
        min-height: 40px !important;
        padding: 8px 16px !important;
        white-space: normal !important;
        line-height: 1.4 !important;
        color: #000 !important;
    }
    
    /* Ensure text is visible in dropdown */
    [data-baseweb="menu"] {
        background: white !important;
        color: #000 !important;
    }
    
    /* Selected value */
    [data-baseweb="select"] {
        color: #000 !important;
    }
    
    /* Make sure dropdown is above other elements */
    [data-baseweb="popover"] {
        z-index: 1000 !important;
    }
</style>
""", unsafe_allow_html=True)

def handle_message(message):
    """Handle messages from the iframe."""
    try:
        if message.type == 'message':
            data = message.get('data', {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return
            
            if data.get('type') == 'color_scheme_change':
                new_color_scheme = data.get('color_scheme')
                if new_color_scheme and new_color_scheme in ['blue', 'green', 'red', 'purple']:
                    st.session_state['color_scheme'] = new_color_scheme
                    st.rerun()
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def main():
    """Main application function for the Leaflet version."""
    # Set up logging with debug level
    logger = setup_logging(level=logging.DEBUG)
    logger.info("Starting Hawaii Appleseed Dashboard - Leaflet Version with DEBUG logging")
    
    # Add a message event listener for iframe communication
    st.components.v1.html("""
        <script>
            window.addEventListener('message', function(event) {
                if (event.data.type === 'color_scheme_change') {
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        data: event.data
                    }, '*');
                }
            }, false);
        </script>
    """, height=0)
    
    # Handle messages from the iframe
    if 'color_scheme_change' in st.session_state:
        new_color_scheme = st.session_state.pop('color_scheme_change')
        if new_color_scheme in ['blue', 'green', 'red', 'purple']:
            st.session_state['color_scheme'] = new_color_scheme
    
    # Enhanced dropdown styling with borders and hover effects
    st.markdown("""
    <style>
        /* Remove borders from Streamlit's generated classes */
        .st-au,
        .st-ax,
        .st-av,
        .st-aw,
        .st-bb,
        .st-bd,
        .st-b8,
        .st-b3,
        .st-b4,
        .st-be,
        .st-bf,
        .st-bg,
        .st-bh,
        .st-bi,
        .st-bj,
        .st-bk,
        .st-bl,
        .st-bm,
        .st-bn,
        .st-b1,
        .st-bo,
        .st-bp,
        .st-e7,
        .st-e8,
        .st-e9,
        .st-ea,
        .st-eb,
        .st-bv,
        .st-bc,
        .st-bw,
        .st-bx,
        .st-by,
        .st-bz,
        .st-c0,
        .st-c1,
        .st-c2,
        .st-c3,
        .st-c4,
        .st-c6,
        .st-b6,
        .st-c7,
        .st-c8,
        .st-c9,
        .st-ca,
        .st-cb {
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }
        
        /* Target the dropdown menu container */
        .st-bc.st-bd.st-bx.st-by.st-bz.st-b3.st-c0.st-c1.st-be.st-c2.st-c3.st-c4.st-c5 {
            position: relative;
            z-index: 1000;
        }
        
        /* Target menu items and text content */
        .st-bc.st-bd.st-bx.st-by.st-bz.st-b3.st-c0.st-c1.st-be.st-c2.st-c3.st-c4.st-c5 > div,
        .st-c5.st-bb.st-b6.st-c6.st-c7.st-bd.st-c8.st-c9.st-ca {
            transition: all 0.2s ease !important;
            opacity: 0;
            transform: translateY(-5px);
            animation: itemFadeIn 0.2s forwards;
            transform-origin: left center !important;
            cursor: pointer;
            padding: 12px 16px !important;
            line-height: 1.5 !important;
            min-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            overflow: visible !important;
            white-space: normal !important;
            text-overflow: clip !important;
            height: auto !important;
        }
        
        /* Ensure text container doesn't clip content */
        .st-c5.st-bb.st-b6.st-c6.st-c7.st-bd.st-c8.st-c9.st-ca {
            padding: 8px 16px !important;
            display: inline-flex !important;
            align-items: center !important;
            height: 100% !important;
        }
        
        /* Hover effect for menu items */
        .st-bc.st-bd.st-bx.st-by.st-bz.st-b3.st-c0.st-c1.st-be.st-c2.st-c3.st-c4.st-c5 > div:hover {
            background-color: var(--hover-color, #f5f8ff) !important;
            transform: translateY(0) translateX(8px) !important;
            padding-left: 24px !important;
        }
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
        
        /* Dropdown menu container */
        [data-baseweb="popover"] {
            z-index: 1000 !important;
            border-radius: 4px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            padding: 4px 0 !important;
            margin: 0 !important;
        }
        
        /* Inner popover container */
        [data-baseweb="popover"] > div {
            max-height: 400px !important;
            border-radius: 4px !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
        }
        
        /* List container */
        [data-baseweb="popover"] ul[role="listbox"] {
            padding: 0 !important;
            margin: 0 !important;
            list-style: none !important;
        }
        
        /* List items */
        [data-baseweb="popover"] li[role="option"] {
            all: unset !important;
            display: block !important;
            padding: 8px 16px !important;
            margin: 0 !important;
            background: white !important;
            border-left: 3px solid transparent !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            line-height: 1.5 !important;
            min-height: 36px !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
            text-overflow: ellipsis !important;
            overflow: hidden !important;
        }
        
        /* Hover state */
        [data-baseweb="popover"] li[role="option"]:hover {
            background-color: #f5f8ff !important;
            border-left-color: #1E88E5 !important;
            transform: translateX(8px) !important;
            box-shadow: -4px 0 6px -2px rgba(30, 136, 229, 0.2) !important;
            padding-left: 20px !important;
        }
        
        /* Remove gaps between items */
        [data-baseweb="popover"] li[role="option"] + li[role="option"] {
            margin-top: 0 !important;
        }
        
        /* Selected item */
        [data-baseweb="popover"] li[aria-selected="true"] {
            background-color: #e3f2fd !important;
            font-weight: 500 !important;
        }
        
        /* Focus state */
        [data-baseweb="popover"] li[role="option"]:focus {
            outline: none !important;
            box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.3) !important;
        }
        
        /* Active state */
        [data-baseweb="popover"] li[role="option"]:active {
            background-color: #bbdefb !important;
            transform: translateX(8px) scale(0.99) !important;
        }
        
        /* Dropdown menu - remove all borders */
        [data-baseweb="popover"],
        [data-baseweb="popover"] *,
        [data-baseweb="popover"]::before,
        [data-baseweb="popover"]::after,
        [data-baseweb="popover"] > div,
        [data-baseweb="popover"] > div > *,
        [data-baseweb="popover"] [role="listbox"],
        [data-baseweb="popover"] [role="listbox"] * {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            --border-width: 0 !important;
            border-width: 0 !important;
            border-style: none !important;
            border-image: none !important;
        }
        
        /* Add back box-shadow to popover only */
        [data-baseweb="popover"] {
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
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
            transform-origin: left center;
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
            transform: translateY(0) translateX(8px);
            padding-left: 20px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Add diagnostic script to inspect dropdown styles
    st.markdown("""
    <script>
    // Run after the page loads
    window.addEventListener('load', function() {
        // Create a style element for our diagnostic border
        const style = document.createElement('style');
        style.textContent = `
            /* Highlight all potential border elements */
            [data-baseweb="popover"],
            [data-baseweb="popover"] * {
                outline: 2px solid red !important;
                outline-offset: -1px;
            }
        `;
        document.head.appendChild(style);
        
        // Log the computed styles of the dropdown
        const logStyles = () => {
            const dropdown = document.querySelector('[data-baseweb="popover"]');
            if (dropdown) {
                const styles = window.getComputedStyle(dropdown);
                console.log('Dropdown styles:', {
                    border: styles.border,
                    outline: styles.outline,
                    boxShadow: styles.boxShadow,
                    borderImage: styles.borderImage,
                    borderWidth: styles.borderWidth,
                    borderStyle: styles.borderStyle,
                    borderColor: styles.borderColor
                });
            }
        };
        
        // Log styles when dropdown opens
        document.body.addEventListener('click', function(e) {
            if (e.target.closest('[data-baseweb="select"]')) {
                setTimeout(logStyles, 300);
            }
        });
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Load additional custom CSS if needed
    with open(Path(__file__).parent / "src" / "ui" / "custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
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
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["Map View", "Data Analysis"])
        
        # Map View Tab
        with tab1:
            create_leaflet_map_view(
                debug_info=sidebar_config.get('debug_info', False)
            )
        
        # Data Analysis Tab
        with tab2:
            st.header("Data Analysis")
            create_data_summary()
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)

if __name__ == "__main__":
    main()
