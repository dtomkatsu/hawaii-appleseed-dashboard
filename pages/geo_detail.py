"""Geographic Detail Page for Hawaii Appleseed Dashboard."""
import streamlit as st
from streamlit.components.v1 import html
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_loader import DataLoader

# Initialize the data loader
data_loader = DataLoader()

st.set_page_config(
    page_title="Geographic Detail - Hawaii Appleseed Dashboard",
    page_icon="🏝️",
    layout="wide"
)

# Constants for economic impact (would ideally come from data)
ECONOMIC_IMPACT_DEFAULTS = {
    'working_families_rate': "84%",
    'economic_impact': "$1.80",
    'retailers_count': "941",
    'retailers_redemption': "$858,976,504"
}

def format_number(value, is_percent=False, is_currency=False, decimals=0):
    """Format a number for display in the fact sheet."""
    if value is None:
        return "N/A"
    try:
        if is_currency:
            return f"${float(value):,.{decimals}f}"
        elif is_percent:
            return f"{float(value):.1f}%"
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return str(value)

def get_fraction_text(rate, household_suffix="households"):
    """Convert a percentage rate to a fraction with qualifiers.
    
    Args:
        rate: The rate as a percentage (e.g., 42.5)
        household_suffix: Text to append after fraction (default: "households")
        
    Returns:
        str: Formatted string like "just over 2 in 5 households"
    """
    if not rate or rate <= 0:
        return ""
        
    decimal_fraction = rate / 100.0
    
    # Common fractions to check against
    common_fractions = [
        (1, 2, 0.5), (1, 3, 0.333), (2, 3, 0.666), (1, 4, 0.25),
        (3, 4, 0.75), (1, 5, 0.2), (2, 5, 0.4), (3, 5, 0.6),
        (4, 5, 0.8), (1, 6, 0.166), (5, 6, 0.833), (1, 7, 0.142),
        (2, 7, 0.285), (3, 7, 0.428), (4, 7, 0.571), (5, 7, 0.714),
        (6, 7, 0.857), (1, 8, 0.125), (1, 9, 0.111)
    ]
    
    # Find the closest fraction
    closest = min(common_fractions, key=lambda f: abs(decimal_fraction - f[2]))
    num, denom, value = closest
    diff = decimal_fraction - value
    
    # Determine the qualifier based on the difference
    if abs(diff) < 0.002:  # Less than 0.2% difference
        prefix = ""
    elif diff > 0.002:  # More than 0.2% above
        prefix = "just over " if diff < 0.01 else "over "
    else:  # More than 0.2% below
        prefix = "just under " if diff > -0.01 else "under "
    
    suffix = f" {household_suffix}" if household_suffix else ""
    return f"{prefix}{num} in {denom}{suffix}"

def prepare_geo_data(geo_data):
    """Prepare and enhance geography data with calculated fields."""
    # Ensure all required data fields are present
    geo_data.setdefault('snap', {})
    geo_data.setdefault('demographics', {})
    geo_data.setdefault('economic', {})
    
    snap_data = geo_data['snap']
    
    # Map SNAP data fields for consistency
    snap_data.update({
        'household_count': snap_data.get('snap_household_count', 0),
        'household_rate': snap_data.get('snap_household_rate', 0),
        'benefits_annual_total': snap_data.get('snap_benefits_annual_total', 0),
        'benefit_annual_per_household': snap_data.get('snap_benefit_annual_per_household', 0)
    })
    
    # Calculate derived values
    annual_per_household = snap_data.get('benefit_annual_per_household', 0)
    if annual_per_household:
        snap_data['monthly_benefit'] = annual_per_household / 12
        snap_data['daily_benefit_per_person'] = snap_data['monthly_benefit'] / 30
    else:
        snap_data['monthly_benefit'] = 0
        snap_data['daily_benefit_per_person'] = 0
    
    # Estimate children in SNAP households
    household_count = snap_data.get('household_count', 0)
    snap_data['estimated_children'] = int(household_count * 2.5 * 0.4) if household_count else 0
    
    return geo_data

def get_comparison_text(geo_data, parent_geo):
    """Generate comparison text between current and parent geography."""
    if not parent_geo or 'snap' not in parent_geo:
        return ""
    
    parent_rate = parent_geo['snap'].get('snap_household_rate', 0)
    current_rate = geo_data['snap'].get('snap_household_rate', 0)
    
    if not (parent_rate and current_rate):
        return ""
    
    diff = current_rate - parent_rate
    parent_type = parent_geo.get('type', 'state')
    
    if abs(diff) < 0.1:  # Consider rates equal if difference is less than 0.1%
        return f"This matches the {parent_type} average of {parent_rate:.1f}%."
    elif diff > 0:
        return f"This is {abs(diff):.1f} percentage points higher than the {parent_type} average of {parent_rate:.1f}%."
    else:
        return f"This is {abs(diff):.1f} percentage points lower than the {parent_type} average of {parent_rate:.1f}%."

def get_parent_geography_data(geo_id: str) -> dict:
    """Get parent geography data for comparison."""
    geo_id_str = str(geo_id).strip()
    geo_level = len(geo_id_str)
    
    # Determine parent based on geography level
    if geo_level in [4, 5]:  # House/Senate districts or counties
        parent_geo_id = '15'  # Hawaii state FIPS
        parent_geo_type = 'state'
    else:
        return None
    
    try:
        parent_data = data_loader.get_all_data_for_geo(parent_geo_id)
        if parent_data and 'name' in parent_data:
            return {
                'type': parent_geo_type,
                'id': parent_geo_id,
                'name': parent_data.get('name', 'Hawaii'),
                'snap': parent_data.get('snap', {})
            }
    except Exception as e:
        st.warning(f"Could not load parent geography data: {str(e)}")
    
    return None

def generate_fact_sheet_html(geo_data):
    """Generate the SNAP fact sheet HTML with all styles and scripts inline."""
    # Extract data with enhanced preparation
    geo_name = geo_data.get('name', 'Hawaii')
    snap_data = geo_data.get('snap', {})
    
    # Format all values
    snap_households = format_number(snap_data.get('snap_household_count'))
    snap_benefits_total = format_number(snap_data.get('snap_benefits_annual_total'), is_currency=True)
    snap_participation_rate = format_number(snap_data.get('snap_household_rate'), is_percent=True)
    avg_monthly_benefit = format_number(snap_data.get('monthly_benefit', 0), is_currency=True, decimals=2)
    daily_per_person = format_number(snap_data.get('daily_benefit_per_person', 0), is_currency=True, decimals=2)
    
    # Get comparison text
    comparison_text = geo_data.get('comparison_text', '')
    
    # Format rates and fractions
    alice_rate_value = geo_data.get('economic', {}).get('alice_rate', 0)
    alice_rate = format_number(alice_rate_value, is_percent=True)
    alice_fraction = get_fraction_text(alice_rate_value, "households")
    
    snap_rate_value = snap_data.get('snap_household_rate', 0)
    snap_fraction = get_fraction_text(snap_rate_value, "")
    
    disability_rate = format_number(snap_data.get('snap_disability_rate'), is_percent=True)
    veterans_count = format_number(snap_data.get('snap_veterans_count'))
    
    # Get economic impact data with defaults
    eco_defaults = ECONOMIC_IMPACT_DEFAULTS
    working_families_rate = eco_defaults['working_families_rate']
    economic_impact = eco_defaults['economic_impact']
    retailers_count = eco_defaults['retailers_count']
    retailers_redemption = eco_defaults['retailers_redemption']
    
    # Fixed JavaScript that waits for DOM to be ready
    javascript_code = """
    function printFactSheet() {
        window.print();
    }
    
    // Wait for next tick to ensure DOM is ready
    setTimeout(function() {
        // ALICE tooltip elements
        const aliceRate = document.querySelector('.alice-rate-text');
        const aliceTooltip = document.querySelector('.alice-tooltip');
        
        // SNAP tooltip elements
        const snapTitle = document.querySelector('.snap-title');
        const snapTooltip = document.querySelector('.snap-tooltip');
        
        // Track persistent state
        let isAliceTooltipPersistent = false;
        let isSnapTooltipPersistent = false;
        
        function setupTooltip(element, tooltip, isPersistentRef) {
            if (!element || !tooltip) return;
            
            // Click to toggle persistent
            element.addEventListener('click', function(e) {
                e.stopPropagation();
                isPersistentRef.value = !isPersistentRef.value;
                tooltip.classList.toggle('persistent', isPersistentRef.value);
                tooltip.classList.toggle('visible', isPersistentRef.value);
            });
            
            // Show on hover
            element.addEventListener('mouseenter', function() {
                if (!isPersistentRef.value) {
                    tooltip.classList.add('visible');
                }
            });
            
            // Hide on mouse leave
            element.addEventListener('mouseleave', function() {
                if (!isPersistentRef.value) {
                    tooltip.classList.remove('visible');
                }
            });
            
            return isPersistentRef;
        }
        
        // Setup tooltips with reference objects
        const aliceRef = {value: false};
        const snapRef = {value: false};
        
        setupTooltip(aliceRate, aliceTooltip, aliceRef);
        setupTooltip(snapTitle, snapTooltip, snapRef);
        
        // Close tooltips when clicking outside
        document.addEventListener('click', function(e) {
            if (aliceRef.value && aliceTooltip && !aliceTooltip.contains(e.target) && !aliceRate.contains(e.target)) {
                aliceRef.value = false;
                aliceTooltip.classList.remove('persistent', 'visible');
            }
            
            if (snapRef.value && snapTooltip && !snapTooltip.contains(e.target) && !snapTitle.contains(e.target)) {
                snapRef.value = false;
                snapTooltip.classList.remove('persistent', 'visible');
            }
        });
    }, 100);
    """
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SNAP Fact Sheet - {geo_name} Preview</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
                padding: 20px;
            }}
            
            .fact-sheet {{
                max-width: 8in;
                margin: 0 auto;
                background: white;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            
            .alice-section {{
                background-color: #f0f4ff;
                color: #000;
                padding: 6px 10px;
                margin: 5px auto 10px auto;
                border: 1px solid #D4AF37;
                font-size: 0.8em;
                max-width: 50%;
                text-align: center;
                border-radius: 3px;
                position: relative;
            }}
            
            .alice-rate {{
                font-size: 16px;
                font-weight: normal;
                margin: 2px 0;
                text-align: center;
                color: #000;
                line-height: 1.3;
                position: relative;
                display: inline-block;
            }}
            
            .alice-rate-text {{
                font-weight: 700;
                border-bottom: 1px dotted #2A3B72;
                cursor: pointer;
                position: relative;
                color: white;
                padding: 1px 6px;
                border-radius: 3px;
                font-weight: bold;
                margin-left: 4px;
                font-size: 0.95em;
                box-shadow: 0 1px 2px rgba(0,0,0,0.15);
                background-color: #2A3B72;
            }}
            
            .percentage-box {{
                font-size: 0.8em;
                font-weight: normal;
                color: white;
                margin-left: 4px;
                padding: 1px 4px;
                border-radius: 3px;
                background-color: #2A3B62;
                border: 1px solid #2A3B62;
            }}
            
            /* Tooltip styles */
            .alice-tooltip, .snap-tooltip {{
                visibility: hidden;
                width: 300px;
                background-color: #2A3B72;
                color: #fff;
                text-align: left;
                border-radius: 5px;
                padding: 15px;
                position: absolute;
                z-index: 1100;
                top: 100%;
                left: 0;
                margin-top: 10px;
                opacity: 0;
                transition: opacity 0.3s, visibility 0.3s;
                font-size: 14px;
                line-height: 1.5;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                pointer-events: none;
            }}
            
            .alice-tooltip p, .snap-tooltip p {{
                margin: 0 0 10px 0;
            }}
            
            .alice-tooltip p:last-child, .snap-tooltip p:last-child {{
                margin-bottom: 0;
            }}
            
            .alice-tooltip::after, .snap-tooltip::after {{
                content: '';
                position: absolute;
                bottom: 100%;
                left: 20px;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: transparent transparent #2A3B72 transparent;
            }}
            
            .alice-tooltip.visible, .snap-tooltip.visible {{
                visibility: visible;
                opacity: 1;
                pointer-events: auto;
            }}
            
            .alice-tooltip.persistent, .snap-tooltip.persistent {{
                pointer-events: auto;
            }}
            
            .snap-title {{
                cursor: help;
                border-bottom: 1px dotted #2A3B72;
                position: relative;
                display: inline-block;
            }}
            
            .header {{
                background-color: #2c5f2d;
                color: white;
                padding: 15px 20px;
                text-align: center;
                position: relative;
            }}
            
            .header h1 {{
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
                padding: 0 40px;
            }}
            
            .print-button {{
                position: absolute;
                top: 10px;
                right: 10px;
                background-color: #fff;
                color: #2c5f2d;
                border: 1px solid #fff;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 5px;
                transition: all 0.2s;
            }}
            
            .print-button:hover {{
                background-color: #f0f0f0;
            }}
            
            @media print {{
                .print-button {{
                    display: none;
                }}
                body {{
                    padding: 0;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
                .fact-sheet {{
                    box-shadow: none;
                    margin: 0;
                    max-width: 100%;
                }}
            }}
            
            @page {{
                size: letter;
                margin: 0.5in;
            }}
            
            .main-content {{
                padding: 20px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: 1.2fr 0.8fr;
                gap: 25px;
                margin: 20px 0;
                align-items: start;
            }}
            
            .four-stats {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            
            .small-stat-box {{
                text-align: center;
                padding: 15px 10px;
                background-color: #f0f7f0;
                border-radius: 5px;
                min-height: 90px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            
            .small-stat-number {{
                font-size: 28px;
                font-weight: 900;
                color: #d32f2f;
                display: block;
                text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }}
            
            .small-stat-label {{
                font-size: 13px;
                color: #333;
                margin-top: 5px;
                line-height: 1.3;
                font-weight: 600;
            }}
            
            .impact-section {{
                margin: 20px 0;
            }}
            
            .impact-title {{
                font-size: 18px;
                font-weight: bold;
                color: #2c5f2d;
                margin-bottom: 15px;
            }}
            
            .bullet-points {{
                list-style: none;
                padding: 0;
            }}
            
            .bullet-points li {{
                margin-bottom: 15px;
                padding-left: 25px;
                position: relative;
                padding-top: 5px;
                padding-bottom: 5px;
            }}
            
            .bullet-points li:nth-child(odd) {{
                background-color: #f8fdf8;
                border-radius: 6px;
                padding: 8px 8px 8px 25px;
                margin-left: -3px;
                margin-right: -3px;
            }}
            
            .bullet-points li:nth-child(even) {{
                background-color: #fefffe;
                border-radius: 6px;
                padding: 8px 8px 8px 25px;
                margin-left: -3px;
                margin-right: -3px;
            }}
            
            .bullet-points li strong {{
                color: #2c5f2d;
                font-weight: 900;
            }}
            
            .bullet-points li .stat-highlight {{
                color: #d32f2f;
                font-weight: 900;
                font-size: 1.1em;
            }}
            
            .bullet-points li:before {{
                content: "▶";
                color: #2c5f2d;
                position: absolute;
                left: 0;
            }}
            
            .highlight-box {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            
            .highlight-box strong {{
                color: #2c5f2d;
                font-weight: 900;
                font-size: 1.05em;
            }}
            
            .strengthen-section {{
                background-color: #2c5f2d;
                color: white;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
                font-weight: bold;
            }}
            
            .call-to-action {{
                background-color: #d32f2f;
                color: white;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }}
            
            .footer {{
                background-color: #2c5f2d;
                color: white;
                padding: 10px 20px;
                text-align: center;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="fact-sheet">
            <div class="header">
                <button class="print-button" onclick="printFactSheet()">
                    <i class="fas fa-print"></i> Print/Save
                </button>
                <h1>{geo_name.upper()}</h1>
                <div class="subtitle">Fact Sheet</div>
            </div>
            
            <div class="alice-section">
                <div class="alice-rate">
                    <span class="alice-rate-text">ALICE Rate</span>: {alice_fraction} <span class="percentage-box">({alice_rate})</span>
                    <div class="alice-tooltip">
                        <p><strong>ALICE</strong> stands for <strong>A</strong>sset <strong>L</strong>imited, <strong>I</strong>ncome <strong>C</strong>onstrained, <strong>E</strong>mployed.</p>
                        <p>It describes people and families who have jobs but still struggle to afford basic needs like housing, food, child care, health care, and transportation.</p>
                    </div>
                </div>
            </div>
            
            <div class="main-content">
                <div class="stats-grid">
                    <div>
                        <h3 style="font-weight: bold; color: black; margin-bottom: 10px; position: relative;">
                            <span class="snap-title">Supplemental Nutrition Assistance Program (SNAP)</span>
                            <div class="snap-tooltip">
                                <p><strong>SNAP</strong> stands for the Supplemental Nutrition Assistance Program, a government program that helps low-income people buy food.</p>
                                <p>Recipients get monthly benefits on a special card, which they can use like a debit card at grocery stores and certain farmers' markets.</p>
                                <p>The goal is to make sure everyone can avoid going hungry while having better access to healthy food.</p>
                            </div>
                        </h3>
                        <ul class="bullet-points">
                            <li>Approximately <strong style="color: black;">{snap_fraction} households <span style="background-color: #006400; color: white; padding: 2px 6px; border-radius: 4px; margin: 0 2px;">({snap_participation_rate})</span></strong> participate in SNAP. <span style="color: red; font-weight: bold;">{comparison_text}</span> SNAP participants reside throughout the area: one in 6 small-town households and one in 10 households in metro areas.</li>
                            <li>In FY 2023, SNAP participants in {geo_name.upper()} received an average of <span class="stat-highlight">{avg_monthly_benefit}</span> per month in SNAP benefits. This averages about <span class="stat-highlight">{daily_per_person}</span> per person per day.</li>
                            <li>SNAP brought <span class="stat-highlight">$519,968,308</span> in benefits to the area in that year.</li>
                        </ul>
                    </div>
                    
                    <div class="four-stats">
                        <div class="small-stat-box">
                            <span class="small-stat-number">50%</span>
                            <div class="small-stat-label">SNAP households with children</div>
                        </div>
                        <div class="small-stat-box">
                            <div class="small-stat-number">{disability_rate}</div>
                            <div class="small-stat-label">SNAP households with a person with a disability</div>
                        </div>
                        <div class="small-stat-box">
                            <span class="small-stat-number">50%</span>
                            <div class="small-stat-label">SNAP households with older adults</div>
                        </div>
                        <div class="small-stat-box">
                            <div class="small-stat-number">{veterans_count}</div>
                            <div class="small-stat-label">Veterans participating in SNAP</div>
                        </div>
                    </div>
                </div>
                
                <div class="impact-section">
                    <div class="impact-title">SNAP'S IMPACT IN {geo_name.upper()}</div>
                    <ul class="bullet-points">
                        <li><strong>SNAP supports working families.</strong> Between 2019–2023, an average of <span class="stat-highlight">{working_families_rate}</span> of SNAP households in {geo_name.upper()} included someone who was working.</li>
                        <li><strong>SNAP stimulates the economy and creates jobs.</strong> Each SNAP dollar has up to a <span class="stat-highlight">{economic_impact}</span> impact during economic downturns, supporting the supply chain from farmer to store.</li>
                        <li><strong>SNAP supports local businesses,</strong> including <span class="stat-highlight">{retailers_count}</span> retailers in {geo_name.upper()}, which redeemed a total of <span class="stat-highlight">{retailers_redemption}</span> in 2023. Retailers include grocery stores and farmers' markets, which contribute to local taxes that fund services like schools and health care.</li>
                    </ul>
                </div>
                
                <div class="highlight-box">
                    <strong>SNAP IS A PROVEN, COST-EFFECTIVE PROGRAM</strong> that reduces food insecurity, supports the health of children, older adults, and veterans. SNAP reduces health care costs, improves educational outcomes, and supports local economies. Support {geo_name.upper()} families by opposing any cuts to SNAP.
                </div>
                
                <div class="strengthen-section">
                    STRENGTHEN SNAP, STRENGTHEN {geo_name.upper()}
                </div>
                
                <div class="call-to-action">
                    <strong>TAKE ACTION: REJECT PROPOSALS THAT CUT OR RESTRICT ACCESS TO SNAP BENEFITS.</strong><br>
                    Proposed cuts mean fewer federal funds supporting local economies, children losing school meals, and decreasing WIC participation for babies and toddlers ages 0–4. These cuts would increase hunger by taking food away from Americans in need, decrease local revenue, and overwhelm already strained food pantries. For every meal a pantry provides, SNAP offers nine.
                </div>
            </div>
            
            <div class="footer">
                SOURCES FOR THIS FACT SHEET CAN BE FOUND IN THE TECHNICAL NOTES.
            </div>
        </div>
        <script>{javascript_code}</script>
    </body>
    </html>
    """

def display_snap_fact_sheet(geo_data):
    """Display the SNAP fact sheet HTML with dynamic data."""
    html_content = generate_fact_sheet_html(geo_data)
    html(html_content, height=1200, scrolling=True)

def display_geo_data(geo_id: str):
    """Display detailed data for a specific geographic area."""
    try:
        # Get and prepare data
        geo_data = data_loader.get_all_data_for_geo(geo_id)
        
        if not geo_data or 'name' not in geo_data:
            st.warning("No detailed data available for this location.")
            return
        
        # Prepare data with calculated fields
        geo_data = prepare_geo_data(geo_data)
        
        # Get parent geography for comparison
        parent_geo = get_parent_geography_data(geo_id)
        if parent_geo:
            geo_data['parent_geography'] = parent_geo
            geo_data['comparison_text'] = get_comparison_text(geo_data, parent_geo)
        else:
            geo_data['comparison_text'] = ""
        
        # Display header and metrics
        st.subheader(geo_data.get('name', 'Location Details'))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'population' in geo_data['demographics']:
                st.metric("Total Population", f"{geo_data['demographics']['population']:,}")
        
        with col2:
            if 'poverty_rate' in geo_data['economic']:
                st.metric("Poverty Rate", f"{geo_data['economic']['poverty_rate']}%")
        
        with col3:
            if 'median_income' in geo_data['economic']:
                st.metric("Median Income", f"${geo_data['economic']['median_income']:,.0f}")
        
        # Display fact sheet
        st.subheader("SNAP Fact Sheet")
        display_snap_fact_sheet(geo_data)
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.exception(e)

def main():
    """Main function for the geographic detail page."""
    st.title("🏝️ Geographic Detail")
    
    # Get the geo_id from query parameters
    query_params = st.experimental_get_query_params()
    geo_id = query_params.get('geo_id', [None])[0]
    
    if geo_id:
        st.success(f"Successfully loaded data for location ID: {geo_id}")
        display_geo_data(geo_id)
        
        # Add a back button
        if st.button("← Back to Map"):
            st.switch_page("run_leaflet.py")
    else:
        st.error("No geographic ID provided. Please select a feature from the map.")
        if st.button("← Back to Map"):
            st.switch_page("run_leaflet.py")

if __name__ == "__main__":
    main()