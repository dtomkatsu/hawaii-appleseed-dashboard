"""Geographic Detail Page for Hawaii Appleseed Dashboard."""
import streamlit as st
from streamlit.components.v1 import html

st.set_page_config(
    page_title="Geographic Detail - Hawaii Appleseed Dashboard",
    page_icon="🏝️",
    layout="wide"
)

def display_snap_fact_sheet():
    """Display the SNAP fact sheet HTML."""
    snap_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SNAP Fact Sheet - Hawaii Preview</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
                padding: 20px;
            }
            
            .fact-sheet {
                max-width: 8in;
                margin: 0 auto;
                background: white;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            
            .header {
                background-color: #2c5f2d;
                color: white;
                padding: 15px 20px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .header .organization {
                font-size: 12px;
                font-weight: normal;
            }
            
            .main-content {
                padding: 20px;
            }
            
            .title-section {
                text-align: center;
                margin-bottom: 20px;
            }
            
            .main-title {
                font-size: 24px;
                font-weight: bold;
                color: #2c5f2d;
                margin-bottom: 5px;
            }
            
            .state-name {
                font-size: 28px;
                font-weight: bold;
                color: #d32f2f;
            }
            
            .intro-section {
                background-color: #f8f9fa;
                padding: 15px;
                margin-bottom: 20px;
                border-left: 4px solid #2c5f2d;
            }
            
            .intro-section strong {
                color: #2c5f2d;
                font-weight: 900;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: 1.2fr 0.8fr;
                gap: 25px;
                margin: 20px 0;
                align-items: start;
            }
            
            .four-stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            
            .small-stat-box {
                text-align: center;
                padding: 15px 10px;
                background-color: #f0f7f0;
                border-radius: 5px;
                min-height: 90px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            
            .small-stat-number {
                font-size: 28px;
                font-weight: 900;
                color: #d32f2f;
                display: block;
                text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }
            
            .small-stat-label {
                font-size: 13px;
                color: #333;
                margin-top: 5px;
                line-height: 1.3;
                font-weight: 600;
            }
            
            .impact-section {
                margin: 20px 0;
            }
            
            .impact-title {
                font-size: 18px;
                font-weight: bold;
                color: #2c5f2d;
                margin-bottom: 15px;
            }
            
            .bullet-points {
                list-style: none;
                padding: 0;
            }
            
            .bullet-points li {
                margin-bottom: 15px;
                padding-left: 25px;
                position: relative;
                padding-top: 5px;
                padding-bottom: 5px;
            }
            
            .bullet-points li:nth-child(odd) {
                background-color: #f8fdf8;
                border-radius: 6px;
                padding: 8px 8px 8px 25px;
                margin-left: -3px;
                margin-right: -3px;
            }
            
            .bullet-points li:nth-child(even) {
                background-color: #fefffe;
                border-radius: 6px;
                padding: 8px 8px 8px 25px;
                margin-left: -3px;
                margin-right: -3px;
            }
            
            .bullet-points li strong {
                color: #2c5f2d;
                font-weight: 900;
            }
            
            .bullet-points li .stat-highlight {
                color: #d32f2f;
                font-weight: 900;
                font-size: 1.1em;
            }
            
            .bullet-points li:before {
                content: "▶";
                color: #2c5f2d;
                position: absolute;
                left: 0;
            }
            
            .highlight-box {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }
            
            .highlight-box strong {
                color: #2c5f2d;
                font-weight: 900;
                font-size: 1.05em;
            }
            
            .call-to-action {
                background-color: #d32f2f;
                color: white;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            
            .footer {
                background-color: #2c5f2d;
                color: white;
                padding: 10px 20px;
                text-align: center;
                font-size: 12px;
            }
            
            .strengthen-section {
                background-color: #2c5f2d;
                color: white;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="fact-sheet">
            <div class="header">
                <div class="organization">FOOD RESEARCH &amp; ACTION CENTER | WWW.FRAC.ORG MAY 2025</div>
                <h1>KEY ECONOMIC FACTS</h1>
            </div>
            
            <div class="main-content">
                <div class="title-section">
                    <div class="main-title">PROTECT SNAP to Reduce Hunger and<br>Strengthen Local Economies in</div>
                    <div class="state-name">HAWAII</div>
                </div>
                
                <div class="intro-section">
                    <p>The Supplemental Nutrition Assistance Program (SNAP) is the nation's first line of defense against hunger, helping <strong>158,170</strong> people in <strong>HAWAII</strong> put food on the table. In fiscal year 2024, SNAP brought <strong>$731,331,421</strong> to the state. With <strong>10%</strong> of HAWAII households experiencing food insecurity and high food prices, protecting and strengthening SNAP is more important than ever.</p>
                </div>
                
                <div class="stats-grid">
                    <div>
                        <ul class="bullet-points">
                            <li><span class="stat-highlight">11%</span> of households in HAWAII participated in SNAP. SNAP participants reside throughout the state: one in 6 small-town households and one in 10 households in metro areas in HAWAII.</li>
                            <li>In FY 2024, SNAP participants in HAWAII received an average of <span class="stat-highlight">$377.11</span> per month in SNAP benefits. This averages <span class="stat-highlight">$12.39</span> per person per day.</li>
                            <li>SNAP helped over <span class="stat-highlight">46,018</span> children in HAWAII in FY 2023. It also provided these children with eligibility for school meals. Cuts to SNAP would mean that children in families with low incomes would lose access to school meals.</li>
                        </ul>
                    </div>
                    
                    <div class="four-stats">
                        <div class="small-stat-box">
                            <span class="small-stat-number">50%</span>
                            <div class="small-stat-label">SNAP households with children</div>
                        </div>
                        <div class="small-stat-box">
                            <span class="small-stat-number">47%</span>
                            <div class="small-stat-label">SNAP households with a person with a disability</div>
                        </div>
                        <div class="small-stat-box">
                            <span class="small-stat-number">50%</span>
                            <div class="small-stat-label">SNAP households with older adults</div>
                        </div>
                        <div class="small-stat-box">
                            <span class="small-stat-number">8,235</span>
                            <div class="small-stat-label">Veterans participating in SNAP</div>
                        </div>
                    </div>
                </div>
                
                <div class="impact-section">
                    <div class="impact-title">SNAP'S IMPACT IN HAWAII</div>
                    <ul class="bullet-points">
                        <li><strong>SNAP supports working families.</strong> Between 2019–2023, an average of <span class="stat-highlight">84%</span> of SNAP households in HAWAII included someone who was working.</li>
                        <li><strong>SNAP stimulates the economy and creates jobs.</strong> Each SNAP dollar has up to a <span class="stat-highlight">$1.80</span> impact during economic downturns, supporting the supply chain from farmer to store.</li>
                        <li><strong>SNAP supports local businesses,</strong> including <span class="stat-highlight">941</span> retailers in HAWAII, which redeemed a total of <span class="stat-highlight">$858,976,504</span> in 2023. Retailers include grocery stores and farmers' markets, which contribute to local taxes that fund services like schools and health care.</li>
                    </ul>
                </div>
                
                <div class="highlight-box">
                    <strong>SNAP IS A PROVEN, COST-EFFECTIVE PROGRAM</strong> that reduces food insecurity, supports the health of children, older adults, and veterans. SNAP reduces health care costs, improves educational outcomes, and supports local economies. Support HAWAII families by opposing any cuts to SNAP.
                </div>
                
                <div class="strengthen-section">
                    STRENGTHEN SNAP, STRENGTHEN HAWAII
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

def main():
    """Main function for the geographic detail page."""
    st.title("🏝️ Geographic Detail")
    
    # Get the geo_id from query parameters
    query_params = st.experimental_get_query_params()
    geo_id = query_params.get('geo_id', [None])[0]
    
    if geo_id:
        st.success(f"Successfully navigated to detail page for geo_id: {geo_id}")
        
        # Display basic information
        st.subheader("Feature Information")
        st.write(f"**Geographic ID:** {geo_id}")
        
        # Display the SNAP fact sheet
        st.subheader("SNAP Fact Sheet")
        display_snap_fact_sheet()
        
        # Placeholder for future detailed content
        st.info("🚧 Detailed geographic data will be displayed here in future updates.")
        
        # Add a back button
        if st.button("← Back to Map"):
            st.switch_page("run_leaflet.py")
            
    else:
        st.error("No geographic ID provided. Please select a feature from the map.")
        if st.button("← Back to Map"):
            st.switch_page("run_leaflet.py")

if __name__ == "__main__":
    main()
