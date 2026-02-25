"""Hawaii Appleseed Dashboard - Leaflet Version."""
import os
import sys
import logging
import json
from pathlib import Path
from functools import lru_cache
import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import local modules
from utils.logging_utils import setup_logging, log_error
from ui.sidebar import create_sidebar
from ui.leaflet_map_view import create_leaflet_map_view, create_data_summary

# Set page config with wide layout and viewport settings
st.set_page_config(
    page_title="Data Dashboard",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.hawaiiappleseed.org/',
        'About': "Interactive data visualization tool for Hawaii"
    }
)

# Suppress deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Import and apply full-width layout utility
from src.ui.full_width_utils import set_full_width_layout
set_full_width_layout()

# Additional custom styles specific to this app
st.markdown("""
    <style>
        /* Map container styles */
        .stMap, .map-container, .leaflet-container {
            width: 100% !important;
            height: 70vh !important;
            min-height: 500px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        
        /* Adjust sidebar */
        section[data-testid="stSidebar"] {
            width: 300px !important;
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0 1rem 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

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

def serve_static_file(file_path):
    """Serve a static file from the static directory."""
    static_dir = Path(__file__).parent / 'static'
    full_path = (static_dir / file_path).resolve()
    
    # Security check to prevent directory traversal
    try:
        full_path.relative_to(static_dir)
    except ValueError:
        return None
    
    if not full_path.exists():
        return None
    
    # Determine content type based on file extension
    content_type = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.eot': 'application/vnd.ms-fontobject',
        '.otf': 'font/otf'
    }.get(full_path.suffix.lower(), 'application/octet-stream')
    
    with open(full_path, 'rb') as f:
        return f.read(), content_type

@lru_cache(maxsize=128)
def get_geo_data(geo_id):
    """Get geographic data for a given ID."""
    # This is a placeholder - in a real app, you'd fetch this from your data source
    # For now, we'll return a mock response
    return {
        'id': geo_id,
        'name': f'Location {geo_id}',
        'type': 'county',
        'demographics': {
            'total_population': 100000,
            'age_distribution': {
                '0-17': 20,
                '18-34': 25,
                '35-54': 30,
                '55-64': 15,
                '65+': 10
            },
            'race_distribution': {
                'White': 40,
                'Native Hawaiian/Pacific Islander': 30,
                'Asian': 20,
                'Other': 10
            }
        },
        'economic': {
            'median_income': 75000,
            'poverty_rate': 10.5,
            'unemployment_rate': 5.2,
            'employment': {
                'employed': 65,
                'unemployed': 5,
                'not_in_labor_force': 30
            }
        },
        'housing': {
            'median_home_value': 650000,
            'homeownership_rate': 55.5,
            'median_rent': 2000,
            'median_home_value_trend': {
                '2018': 550000,
                '2019': 580000,
                '2020': 600000,
                '2021': 620000,
                '2022': 650000
            }
        },
        'geometry': {
            'type': 'Polygon',
            'coordinates': [[
                [-157.965, 21.482],
                [-157.955, 21.482],
                [-157.955, 21.492],
                [-157.965, 21.492],
                [-157.965, 21.482]
            ]]
        },
        'centroid': [-157.96, 21.487],
        'bbox': [-157.965, 21.482, -157.955, 21.492]
    }

def handle_geo_api(geo_id):
    """Handle API requests for geographic data."""
    try:
        geo_data = get_geo_data(geo_id)
        return json.dumps(geo_data), 'application/json'
    except Exception as e:
        return json.dumps({'error': str(e)}), 'application/json', 500

def load_css():
    """Load custom CSS to force light theme."""
    css_file = Path(__file__).parent / "static" / "css" / "force-light-theme.css"
    with open(css_file) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def main():
    """Main application function for the Leaflet version."""
    # Set up logging and load CSS
    logger = logging.getLogger(__name__)
    load_css()
    
    # Check if this is a request for a static file or API endpoint
    query_params = st.query_params
    request_path = query_params.get('__path__', '/')
    
    # Handle static file requests
    if request_path.startswith('/static/'):
        file_path = request_path[8:]  # Remove '/static/' prefix
        response = serve_static_file(file_path)
        if response:
            content, content_type = response
            st.markdown(f'<meta http-equiv="refresh" content="0;url=/static/{file_path}">', unsafe_allow_html=True)
            return
    
    # Handle API requests
    if request_path.startswith('/api/geo/'):
        geo_id = request_path.split('/')[-1]
        content, content_type, *status = handle_geo_api(geo_id)
        st.write(content)
        st.stop()
    
    # Regular page load - render the main app
    logger.info("Starting Hawaii Appleseed Dashboard - Leaflet Version")
    
    # Custom CSS for layout and typography
    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            /* Reset all vertical spacing */
            html, body, #root, #root > div, #root > div > div,
            .stApp, .appview-container, .main, .block-container,
            [data-testid="stAppViewContainer"],
            [data-testid="stSidebar"],
            [data-testid="stSidebarContent"],
            [data-testid="stVerticalBlock"],
            [data-testid="stVerticalBlockBorderWrapper"] {
                margin-top: 0 !important;
                padding-top: 0 !important;
                min-height: 0 !important;
            }

            /* Target specific Streamlit containers */
            .stApp > div:first-child,
            .appview-container > div:first-child,
            [data-testid="stAppViewContainer"] > div:first-child,
            .main > div:first-child {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

            /* Remove any remaining spacing from vertical wrappers */
            [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div {
                margin-top: 0 !important;
                padding-top: 0 !important;
                gap: 0 !important;
            }

            /* Add controlled spacing between elements */
            [data-testid="stVerticalBlock"] {
                gap: 0.25rem !important;
                row-gap: 0.25rem !important;
            }
            
            /* Add space below the title */
            h1 {
                margin-bottom: 0.5rem !important;
                padding-bottom: 0 !important;
            }
            
            /* Add space above tabs */
            [role="tablist"] {
                margin-top: 0.5rem !important;
            }
            
            /* Ensure dropdown labels have proper spacing */
            .dropdown-label {
                margin-bottom: 0.5rem !important;
                display: block;
                font-weight: 500;
                color: #1E5BA8;
                font-family: 'Roboto', sans-serif;
            }

            /* Hide the sidebar collapse control and its spacer */
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="stLogoSpacer"] {
                display: none !important;
                height: 0 !important;
                width: 0 !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            header[data-testid="stHeader"] {
                display: none;
            }
            section[data-testid="stSidebar"],
            div[data-testid="stSidebarNav"] {
                padding-top: 0;
                margin-top: 0;
            }
            .stApp > div:first-child {
                margin-top: -1rem;
            }
            
            /* Apply Roboto to specific elements */
            h1, h2, h3, h4, h5, h6,
            .stMarkdown h1, 
            .stMarkdown h2, 
            .stMarkdown h3,
            .stMarkdown h4,
            .stMarkdown h5,
            .stMarkdown h6 {
                font-family: 'Roboto', sans-serif !important;
            }
            
            /* Style form labels with higher specificity */
            .stSelectbox > label,
            .stRadio > label,
            .stButton > button,
            .stTextInput > label,
            .stNumberInput > label,
            .stSlider > label,
            .stMultiSelect > label,
            .stDateInput > label,
            .stTimeInput > label,
            .stFileUploader > label,
            div[data-testid='stForm'] label,
            div[data-baseweb='form-control'] > div:first-child {
                font-family: 'Roboto', sans-serif !important;
                color: #2a5a0c !important;  /* Darker green */
                font-weight: 600 !important;
            }
            
            /* Target the actual text nodes */
            .stSelectbox > label > div:first-child,
            .stRadio > label > div:first-child,
            div[data-testid='stForm'] label > div:first-child,
            div[data-baseweb='form-control'] > div:first-child > div:first-child {
                color: #2a5a0c !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
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
        .stSelectbox > div[data-baseweb="select"] > div {
            background-color: #f0f7e9;  /* Very light green background */
            border: none !important;  /* Remove borders */
            border-radius: 4px;
            padding: 0.25rem 0.5rem;
            transition: all 0.2s ease;
        }
        
        /* Style the dropdown arrow */
        .stSelectbox svg {
            color: #2a5a0c !important;  /* Dark green arrow */
            opacity: 0.8;
        }
        
        /* Hover and focus states for dropdowns */
        .stSelectbox > div[data-baseweb="select"]:hover > div,
        .stSelectbox > div[data-baseweb="select"].st-bb > div,
        .stSelectbox > div[data-baseweb="select"]:focus-within > div {
            background-color: #e8f3df;
            border: none !important;  /* Remove borders even on hover */
            box-shadow: none !important;  /* Remove box shadow */
        }
        
        /* Style the dropdown menu */
        .stSelectbox > div > div > div {
            background-color: #f0f7e9;  /* Light green background */
            border: none !important;  /* Remove borders */
            border-radius: 4px;
            padding: 0.5rem 0.75rem;
        }
        
        /* Dropdown menu items */
        [role="option"] {
            background-color: #f0f7e9 !important;  /* Match the light green */
            color: #2a5a0c !important;  /* Dark green text */
            padding: 8px 16px !important;
            transition: background-color 0.2s ease !important;
        }
        
        /* Hover state for dropdown items */
        [role="option"]:hover {
            background-color: #e0edd0 !important;  /* Slightly darker green on hover */
        }
        
        /* Selected item in dropdown */
        [aria-selected="true"] {
            background-color: #d0e3c4 !important;  /* Even darker for selected */
            font-weight: 500 !important;
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
    
    # Load additional custom CSS if needed
    with open(Path(__file__).parent / "src" / "ui" / "enhanced_style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    try:
        # Initialize session state for county layer if not already set
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
            logger.info("Initializing session state with Counties layer")
        
        # Create custom sidebar with green labels (title removed per design request)
        # st.sidebar.title("🌴 Hawaii Appleseed Dashboard")
        
        # Define layer options
        layer_options = [
            'State Boundary',
            'Counties',
            'House Districts',
            'Senate Districts'
        ]
        
        # Initialize session state for active layer if not set
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
        
        # Variable options with descriptions
        variable_options = {
            'poverty_rate': 'Poverty Rate',
            'median_income': 'Median Income',
            'college_educated_pct': 'Bachelor\'s Degree or Higher (%)',
            'rent_burden_rate': 'Housing Cost Burden (%)',
            'alice_rate': 'ALICE Households (%)',
            'white_alone_pct': 'White Alone (%)',
            'asian_alone_pct': 'Asian Alone (%)',
            'native_hawaiian_pi_pct': 'Native Hawaiian/Pacific Islander (%)',
            'snap_household_rate': 'SNAP Households (%)',
            'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit ($)',
            'snap_benefits_annual_total': 'Total Annual SNAP Benefits ($)',
            'travel_time_to_work_minutes': 'Average Travel Time to Work (minutes)',
            'public_transportation_pct': 'Public Transportation Commuters (%)',
            'ctc_avg_amount': 'Child Tax Credit - Average Amount ($)',
            'ctc_participation_rate': 'Child Tax Credit - Participation Rate (%)',
            'federal_eitc_avg_amount': 'Federal EITC - Average Amount ($)',
            'eitc_participation_rate': 'Federal EITC - Participation Rate (%)',
            'state_eitc_avg_amount': 'State EITC - Average Amount ($)'
        }
        
        # Initialize selected variable if not set
        if 'selected_variable' not in st.session_state:
            st.session_state.selected_variable = 'alice_rate'
        
        # Color scheme options with descriptive names
        color_schemes = {
            'blue': 'Blue Scale',
            'green': 'Green Scale',
            'red': 'Red Scale',
            'purple': 'Purple Scale'
        }
        
        # Initialize color scheme if not set
        if 'color_scheme' not in st.session_state:
            st.session_state.color_scheme = 'blue'
        
        # Data visualization controls
        st.sidebar.markdown("### 📊 Visualization Controls")
        
        # Note: Geography and variable selection moved to main content area
        # This provides better layout and prevents sidebar/main content conflicts
        
        # Color scheme selection
        st.sidebar.markdown('<p style="color:#2a5a0c; font-family:Roboto; font-weight:600; margin-bottom:0px;">Color Scheme:</p>', unsafe_allow_html=True)
        
        # Safe color scheme index calculation
        try:
            color_index = list(color_schemes.keys()).index(st.session_state.color_scheme)
        except (ValueError, KeyError):
            color_index = 0
            
        selected_color = st.sidebar.selectbox(
            "",
            options=list(color_schemes.keys()),
            format_func=lambda x: color_schemes[x],
            index=color_index,
            key="sidebar_color_selector"
        )
        if selected_color != st.session_state.get('color_scheme'):
            st.session_state.color_scheme = selected_color
        
        # Display options
        st.sidebar.markdown("### 🔧 Display Options")
        show_legend = st.sidebar.checkbox("Show Legend", value=True)
        show_labels = st.sidebar.checkbox("Show Area Labels", value=True)
        debug_info = st.sidebar.checkbox("Show Debug Info", value=False)
        
        # Create sidebar config dictionary
        sidebar_config = {
            'active_layer': st.session_state.active_layer,
            'selected_variable': st.session_state.selected_variable,
            'color_scheme': st.session_state.color_scheme,
            'show_legend': show_legend,
            'show_labels': show_labels,
            'debug_info': debug_info
        }
        
        # Main content area
        st.markdown("""
        <link href='https://fonts.googleapis.com/css2?family=Poppins:wght@600&display=swap' rel='stylesheet'>
        <style>
            .dashboard-title {
                font-family: 'Poppins', sans-serif;
                color: #3a7710;
                margin: 0;
                padding: 0;
                line-height: 1;
                font-weight: 600;
                letter-spacing: -0.5px;
            }
        </style>
        <h1 class="dashboard-title"></h1>
        """, unsafe_allow_html=True)
        
        # Label colors handled by CSS above (no JavaScript MutationObserver needed)
        
        # Clean and simple dashboard without complex URL handling
        
        # Add minimal space before tabs
        st.markdown("<div style='margin-top: 0.1rem;'></div>", unsafe_allow_html=True)
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["🗺️ Map View", "📊 Data Analysis"])
        
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
