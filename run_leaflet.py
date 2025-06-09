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
    page_title="Data Dashboard",
    page_icon="📊",
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
                color: #2a5a0c;
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
    
    # Add basic message handling for color scheme changes
    st.components.v1.html("""
        <script>
            // Handle color scheme changes from map
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
    with open(Path(__file__).parent / "src" / "ui" / "enhanced_style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    try:
        # Initialize session state for county layer if not already set
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
            logger.info("Initializing session state with Counties layer")
        
        # Create custom sidebar with green labels
        st.sidebar.title("🌴 Hawaii Appleseed Dashboard")
        
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
            'median_home_value': 'Median Home Value ($)',
            'unemployment_rate': 'Unemployment Rate (%)',
            'college_educated_pct': 'Bachelor\'s Degree or Higher (%)',
            'rent_burden_rate': 'Housing Cost Burden (%)',
            'alice_rate': 'ALICE Households (%)',
            'white_alone_pct': 'White Alone (%)',
            'asian_alone_pct': 'Asian Alone (%)',
            'native_hawaiian_pi_pct': 'Native Hawaiian/Pacific Islander (%)',
            'snap_household_rate': 'SNAP Households (%)',
            'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit ($)',
            'snap_benefits_annual_total': 'Total Annual SNAP Benefits ($)'
        }
        
        # Initialize selected variable if not set
        if 'selected_variable' not in st.session_state:
            st.session_state.selected_variable = 'poverty_rate'
        
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
        
        # Custom colored labels
        st.sidebar.markdown('<p style="color:#2a5a0c; font-family:Roboto; font-weight:600; margin-bottom:0px;">Geography:</p>', unsafe_allow_html=True)
        
        # Safe layer index calculation
        try:
            layer_index = layer_options.index(st.session_state.active_layer)
        except (ValueError, KeyError):
            layer_index = 0
            
        active_layer = st.sidebar.selectbox(
            "",
            options=layer_options,
            index=layer_index,
            key="sidebar_layer_selector"
        )
        st.session_state.active_layer = active_layer
        
        # Variable selection with custom label
        st.sidebar.markdown('<p style="color:#2a5a0c; font-family:Roboto; font-weight:600; margin-bottom:0px;">Data Variable:</p>', unsafe_allow_html=True)
        
        # Safe variable index calculation
        try:
            variable_index = list(variable_options.keys()).index(st.session_state.selected_variable)
        except (ValueError, KeyError):
            variable_index = 0
            
        selected_variable = st.sidebar.selectbox(
            "",
            options=list(variable_options.keys()),
            format_func=lambda x: variable_options[x],
            index=variable_index,
            key="sidebar_variable_selector"
        )
        st.session_state.selected_variable = selected_variable
        
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
        st.markdown("<h1 style='color: #3a7710; margin: 0; padding: 0; line-height: 1;'>Data Dashboard</h1>", unsafe_allow_html=True)
        
        # Apply JavaScript to ensure form labels are green
        st.markdown("""
        <script>
            // Function to change label colors
            function setLabelColors() {
                // Target all label elements
                const labels = document.querySelectorAll('.stSelectbox label, .stRadio label');
                labels.forEach(label => {
                    label.style.color = '#2a5a0c';
                    label.style.fontWeight = '600';
                    // Also target child elements
                    const children = label.querySelectorAll('*');
                    children.forEach(child => {
                        child.style.color = '#2a5a0c';
                        child.style.fontWeight = '600';
                    });
                });
            }
            
            // Run immediately and also after a short delay to catch dynamically loaded elements
            setLabelColors();
            setTimeout(setLabelColors, 500);
            setTimeout(setLabelColors, 1000);
            
            // Create a MutationObserver to watch for DOM changes
            const observer = new MutationObserver(function(mutations) {
                setLabelColors();
            });
            
            // Start observing once the DOM is fully loaded
            document.addEventListener('DOMContentLoaded', function() {
                observer.observe(document.body, { childList: true, subtree: true });
            });
        </script>
        """, unsafe_allow_html=True)
        
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
