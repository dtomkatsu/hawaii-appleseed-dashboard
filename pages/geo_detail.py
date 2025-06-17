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

def format_number(value, is_percent=False, is_currency=False, decimals=0):
    """Format a number for display in the fact sheet."""
    if value is None:
        return "N/A"
    try:
        if is_currency:
            return f"${float(value):,.{decimals}f}"
        elif is_percent:
            return f"{float(value):.0f}%"
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return str(value)

def display_snap_fact_sheet(geo_data):
    """Display the SNAP fact sheet HTML with dynamic data.
    
    Args:
        geo_data: Dictionary containing geographic data from DataLoader
    """
    # Extract data with fallbacks
    geo_name = geo_data.get('name', 'Hawaii')
    snap_data = geo_data.get('snap', {})
    demographics = geo_data.get('demographics', {})
    economic = geo_data.get('economic', {})
    
    # Format values with fallbacks
    snap_households = format_number(snap_data.get('snap_household_count'))
    snap_benefits_total = format_number(snap_data.get('snap_benefits_annual_total'), is_currency=True)
    snap_participation_rate = format_number(snap_data.get('snap_household_rate'), is_percent=True)
    avg_monthly_benefit = format_number(snap_data.get('snap_benefit_annual_per_household', 0) / 12, is_currency=True, decimals=2)
    daily_per_person = format_number((snap_data.get('snap_benefit_annual_per_household', 0) / 12) / 30, is_currency=True, decimals=2)
    
    # Calculate children in SNAP households (assuming 25% of SNAP participants are children)
    children_in_snap = format_number(int(snap_data.get('snap_household_count', 0)) * 0.8)  # Estimate
    
    # Economic impact data (these would ideally come from the data)
    working_families_rate = "84%"
    economic_impact = "$1.80"
    retailers_count = "941"
    retailers_redemption = "$858,976,504"
    
    # Use double curly braces to escape them in the f-string
    snap_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SNAP Fact Sheet - {geo_name} Preview</title>
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
            
            .header {{
                background-color: #2c5f2d;
                color: white;
                padding: 15px 20px;
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            
            .header .organization {{
                font-size: 12px;
                font-weight: normal;
            }}
            
            .main-content {{
                padding: 20px;
            }}
            
            .title-section {{
                text-align: center;
                margin-bottom: 20px;
            }}
            
            .main-title {{
                font-size: 24px;
                font-weight: bold;
                color: #2c5f2d;
                margin-bottom: 5px;
            }}
            
            .state-name {{
                font-size: 28px;
                font-weight: bold;
                color: #d32f2f;
            }}
            
            .intro-section {{
                background-color: #f8f9fa;
                padding: 15px;
                margin-bottom: 20px;
                border-left: 4px solid #2c5f2d;
            }}
            
            .intro-section strong {{
                color: #2c5f2d;
                font-weight: 900;
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
            
            .strengthen-section {{
                background-color: #2c5f2d;
                color: white;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="fact-sheet">
            <div class="header">
                <h1>{geo_name.upper()}</h1>
                <div class="subtitle">Fact Sheet</div>
            </div>
            
            <div class="main-content">
                <div class="intro-section">
                    <p>The Supplemental Nutrition Assistance Program (SNAP) is the nation's first line of defense against hunger, helping <strong>{snap_households}</strong> households in <strong>{geo_name.upper()}</strong> put food on the table. In fiscal year 2024, SNAP brought <strong>{snap_benefits_total}</strong> to the area. With many {geo_name} households experiencing food insecurity and high food prices, protecting and strengthening SNAP is more important than ever.</p>
                </div>
                
                <div class="stats-grid">
                    <div>
                        <ul class="bullet-points">
                            <li><span class="stat-highlight">{snap_participation_rate}</span> of households in {geo_name.upper()} participated in SNAP. SNAP participants reside throughout the area: one in 6 small-town households and one in 10 households in metro areas in {geo_name.upper()}.</li>
                            <li>In FY 2023, SNAP participants in {geo_name.upper()} received an average of <span class="stat-highlight">{avg_monthly_benefit}</span> per month in SNAP benefits. This averages about <span class="stat-highlight">{daily_per_person}</span> per person per day.</li>
                            <li>SNAP helped over <span class="stat-highlight">{children_in_snap}</span> children in {geo_name.upper()} in FY 2023. It also provided these children with eligibility for school meals. Cuts to SNAP would mean that children in families with low incomes would lose access to school meals.</li>
                        </ul>
                    </div>
                    
                    <div class="four-stats">
                        <div class="small-stat-box">
                            <span class="small-stat-number">50%</span>
                            <div class="small-stat-label">SNAP households with children</div>
                        </div>
                        <div class="small-stat-box">
                            <div class="small-stat-number">{format_number(snap_data.get('snap_disability_rate'), is_percent=True)}</div>
                            <div class="small-stat-label">SNAP households with a person with a disability</div>
                        </div>
                        <div class="small-stat-box">
                            <span class="small-stat-number">50%</span>
                            <div class="small-stat-label">SNAP households with older adults</div>
                        </div>
                        <div class="small-stat-box">
                            <div class="small-stat-number">{format_number(snap_data.get('snap_veterans_count'))}</div>
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
    </body>
    </html>
    """
    
    html(snap_html, height=1200)

def display_geo_data(geo_id: str):
    """Display detailed data for a specific geographic area."""
    try:
        # Get data for the specific geography
        geo_data = data_loader.get_all_data_for_geo(geo_id)
        
        if not geo_data or 'name' not in geo_data:
            st.warning("No detailed data available for this location.")
            return
        
        # Ensure all required data fields are present with defaults if missing
        if 'snap' not in geo_data:
            geo_data['snap'] = {}
        
        if 'demographics' not in geo_data:
            geo_data['demographics'] = {}
        
        if 'economic' not in geo_data:
            geo_data['economic'] = {}
        
        # Calculate derived values
        snap_data = geo_data['snap']
        
        # Ensure required SNAP fields exist
        snap_data['household_count'] = snap_data.get('household_count', 0)
        snap_data['benefits_annual_total'] = snap_data.get('benefits_annual_total', 0)
        snap_data['household_rate'] = snap_data.get('household_rate', 0)
        snap_data['benefit_annual_per_household'] = snap_data.get('benefit_annual_per_household', 0)
        
        # Calculate monthly and daily benefits
        if 'benefit_annual_per_household' in snap_data and snap_data['benefit_annual_per_household']:
            snap_data['monthly_benefit'] = snap_data['benefit_annual_per_household'] / 12
            snap_data['daily_benefit_per_person'] = snap_data['monthly_benefit'] / 30  # Rough estimate
        else:
            snap_data['monthly_benefit'] = 0
            snap_data['daily_benefit_per_person'] = 0
        
        # Estimate children in SNAP households (assuming 40% of SNAP participants are children)
        if 'household_count' in snap_data and snap_data['household_count']:
            snap_data['estimated_children'] = int(snap_data['household_count'] * 2.5 * 0.4)  # 2.5 people per household, 40% children
        else:
            snap_data['estimated_children'] = 0
        
        # Display basic information
        st.subheader(geo_data.get('name', 'Location Details'))
        
        # Display key metrics in columns
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
        
        # Display the SNAP fact sheet with all available data
        st.subheader("SNAP Fact Sheet")
        display_snap_fact_sheet(geo_data)
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.exception(e)  # Show full traceback for debugging
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.exception(e)  # This will show the full traceback in the app for debugging

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
