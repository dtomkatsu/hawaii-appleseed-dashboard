"""Geographic Detail Page for Hawaii Appleseed Dashboard - New Design."""
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

import base64
import json
import os
from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# Import data loader and other utilities
import sys
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_PROJECT_ROOT)
# Also add src/ so bare `from config.x import y` calls inside src modules resolve
# when this page is loaded directly (e.g. via /geo_detail link in a new tab).
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "src"))
from src.data.data_loader import DataLoader
from src.ui.full_width_utils import set_full_width_layout

# Initialize data loader
data_loader = DataLoader()

# Set full width layout
set_full_width_layout()

# Note: set_page_config is handled in the main app file (run_leaflet.py)

# Additional custom styles specific to this page
st.markdown("""
    <style>
        /* Chart and content containers */
        .stPlotlyChart, .stDataFrame, .element-container {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

def get_image_base64(image_path: str) -> str:
    """Get base64 encoded image or return empty string if not found."""
    try:
        # Find project root by looking for run_leaflet.py or requirements.txt
        current_dir = Path(__file__).parent.absolute()
        project_root = current_dir
        
        # Walk up the directory tree to find project root
        max_levels = 5
        for _ in range(max_levels):
            if (project_root / 'run_leaflet.py').exists() or (project_root / 'requirements.txt').exists():
                break
            if project_root.parent == project_root:  # Reached filesystem root
                break
            project_root = project_root.parent
        
        # Try multiple path strategies
        paths_to_try = [
            Path(image_path),  # Absolute path
            project_root / image_path,  # Relative to project root
            current_dir / image_path,  # Relative to current script
            current_dir.parent / image_path,  # One level up from current script
        ]
        
        for path in paths_to_try:
            if path.exists():
                with open(path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode('utf-8')
        
        # Log all attempted paths for debugging
        print(f"Warning: Image not found. Tried paths:")
        for path in paths_to_try:
            print(f"  - {path} (exists: {path.exists()})")
        return ""
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return ""

# Economic impact defaults for areas without specific data
ECONOMIC_IMPACT_DEFAULTS = {
    'working_families_rate': 75,  # 75% of SNAP households have working family members
    'economic_impact': 1.79,      # Every $1 in SNAP generates $1.79 in economic activity
    'retailers_count': 150,       # Approximate number of retailers accepting SNAP
    'retailers_redemption': 85    # 85% of SNAP benefits redeemed at grocery stores
}

def format_number(value, is_percent=False, is_currency=False, decimals=0):
    """Format a number for display in the fact sheet."""
    if value is None:
        return "N/A"
    try:
        if is_currency:
            return f"${float(value):,.{decimals}f}"
        if is_percent:
            return f"{float(value):.1f}%"
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return str(value)

def get_comparison_text(current_value, comparison_value, comparison_type='state', is_currency=True):
    """Generate comparison text between current value and comparison value."""
    if current_value is None or comparison_value is None or comparison_value == 0:
        return ""
    
    try:
        current = float(current_value)
        comparison = float(comparison_value)
        
        if current > comparison:
            diff = current - comparison
            diff_pct = (diff / comparison) * 100
            diff_str = f"${diff:,.0f}" if is_currency else f"{diff:,.0f}"
            return f"+{diff_str} (+{diff_pct:.1f}%) above {comparison_type} average"
        elif current < comparison:
            diff = comparison - current
            diff_pct = (diff / comparison) * 100
            diff_str = f"${diff:,.0f}" if is_currency else f"{diff:,.0f}"
            return f"-{diff_str} ({diff_pct:.1f}%) below {comparison_type} average"
        else:
            return f"Same as {comparison_type} average"
    except (ValueError, TypeError) as e:
        print(f"Error in get_comparison_text: {e}")
        return ""

def get_snap_comparison_text(geo_data, parent_geo):
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

def get_fraction_text(rate, household_suffix="households"):
    """Convert a percentage rate to a fraction with qualifiers."""
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
    
    # Add housing cost burden data if available
    if 'housing' in geo_data:
        # Process median rent
        if 'median_rent' in geo_data['housing']:
            median_rent = geo_data['housing']['median_rent']
            if median_rent is not None:
                try:
                    geo_data['formatted_median_rent'] = format_number(median_rent, is_currency=True, decimals=0)
                except (ValueError, TypeError) as e:
                    geo_data['formatted_median_rent'] = str(median_rent)
            else:
                geo_data['formatted_median_rent'] = "N/A"
        else:
            geo_data['formatted_median_rent'] = "N/A"
            
        # Move renter_rate to top level for easy access in the template
        if 'renter_rate' in geo_data['housing']:
            raw_renter_rate = geo_data['housing']['renter_rate']
            if raw_renter_rate is not None:
                try:
                    renter_rate_float = float(raw_renter_rate)
                    # If the value is between 0 and 1, assume it's a decimal that needs to be converted to percentage
                    if 0 <= renter_rate_float <= 1:
                        formatted_renter_rate = renter_rate_float * 100
                    else:
                        formatted_renter_rate = renter_rate_float
                        
                    geo_data['renter_rate'] = round(formatted_renter_rate, 1)
                except (ValueError, TypeError) as e:
                    geo_data['renter_rate'] = raw_renter_rate
            else:
                geo_data['renter_rate'] = None
        else:
            geo_data['renter_rate'] = None
        
        # Standard housing cost burden (30%+ of income on rent)
        if 'rent_burden_rate' in geo_data['housing']:
            rent_burden = geo_data['housing']['rent_burden_rate']
            geo_data['housing_cost_burden'] = f"{float(rent_burden):.1f}%" if rent_burden is not None else "N/A"
            geo_data['housing_cost_burden_fraction'] = get_fraction_text(rent_burden, "renters") if rent_burden is not None else "N/A"
        else:
            geo_data['housing_cost_burden'] = "N/A"
            geo_data['housing_cost_burden_fraction'] = "N/A"
            
        # Severe housing cost burden (50%+ of income on rent)
        if 'severe_rent_burden_rate' in geo_data['housing']:
            severe_rent_burden = geo_data['housing']['severe_rent_burden_rate']
            geo_data['severe_housing_cost_burden'] = f"{float(severe_rent_burden):.1f}%" if severe_rent_burden is not None else "N/A"
            geo_data['severe_housing_cost_burden_fraction'] = get_fraction_text(severe_rent_burden, "renters") if severe_rent_burden is not None else "N/A"
        elif 'severe_housing_burden_rate' in geo_data['housing']:
            severe_burden = geo_data['housing']['severe_housing_burden_rate']
            geo_data['severe_housing_cost_burden'] = f"{float(severe_burden):.1f}%" if severe_burden is not None else "N/A"
            geo_data['severe_housing_cost_burden_fraction'] = get_fraction_text(severe_burden, "renters") if severe_burden is not None else "N/A"
        else:
            geo_data['severe_housing_cost_burden'] = "N/A"
            geo_data['severe_housing_cost_burden_fraction'] = "N/A"
    
    # State and county averages (example values - replace with actual data)
    state_avg_income = 83500  # Hawaii state average median income
    county_avg_income = 92000  # County average median income
    state_avg_rent = 1800      # Hawaii state average median rent
    county_avg_rent = 2000     # County average median rent

    # Process median income with comparison
    if 'economic' in geo_data and 'median_income' in geo_data['economic']:
        median_income = geo_data['economic']['median_income']
        if median_income is not None:
            geo_data['formatted_median_income'] = format_number(median_income, is_currency=True, decimals=0)
            
            # Add comparison data for median income
            geo_data['income_comparison_state'] = get_comparison_text(
                median_income, state_avg_income, comparison_type='state', is_currency=True
            )
            geo_data['income_comparison_county'] = get_comparison_text(
                median_income, county_avg_income, comparison_type='county', is_currency=True
            )
    
    # Format population count
    if 'demographics' in geo_data and 'population' in geo_data['demographics']:
        population = geo_data['demographics']['population']
        if population is not None:
            geo_data['formatted_population'] = format_number(population, decimals=0)
    
    # Process median rent comparison if not already done
    if 'housing' in geo_data and 'median_rent' in geo_data['housing'] and 'formatted_median_rent' not in geo_data:
        median_rent = geo_data['housing']['median_rent']
        
        if median_rent is not None and not (isinstance(median_rent, float) and np.isnan(median_rent)):
            geo_data['formatted_median_rent'] = format_number(median_rent, is_currency=True, decimals=0)
            
            # Add comparison data for median rent
            geo_data['rent_comparison_state'] = get_comparison_text(
                median_rent, state_avg_rent, comparison_type='state', is_currency=True
            )
            geo_data['rent_comparison_county'] = get_comparison_text(
                median_rent, county_avg_rent, comparison_type='county', is_currency=True
            )
        else:
            geo_data['rent_comparison_state'] = ""
            geo_data['rent_comparison_county'] = ""
    else:
        geo_data['rent_comparison_state'] = ""
        geo_data['rent_comparison_county'] = ""
    
    return geo_data

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

def generate_fact_sheet_html(geo_data: Dict[str, Any]) -> str:
    """Generate HTML content for the new fact sheet design."""
    
    # Get data from geo_data
    geo_name = geo_data.get('name', 'Hawaii')
    geo_type = geo_data.get('type', 'area')
    
    # Debug: Print the original name and type
    print(f"DEBUG: Original geo_name: '{geo_name}'")
    print(f"DEBUG: geo_type: '{geo_type}'")
    
    # Format names consistently based on geography type
    if ', Hawaii' in geo_name:
        # Extract the base county name
        base_name = geo_name.replace(' County, Hawaii', '').replace(', Hawaii', '')
        
        # Map to proper county names with correct spelling
        county_mapping = {
            'Honolulu': 'Honolulu County',
            'Hawaii': 'Hawaiʻi County',
            'Maui': 'Maui County',
            'Kauai': 'Kauaʻi County'
        }
        
        geo_name = county_mapping.get(base_name, f"{base_name} County")
    elif 'House District' in geo_name or 'Senate District' in geo_name:
        # Clean up House and Senate district names
        # Remove everything after semicolon and "Hawaii" references
        if ';' in geo_name:
            geo_name = geo_name.split(';')[0].strip()
        if ', Hawaii' in geo_name:
            geo_name = geo_name.replace(', Hawaii', '').strip()
        # Remove year references in parentheses like "(2022)"
        import re
        geo_name = re.sub(r'\s*\(\d{4}\)', '', geo_name).strip()
        # Replace "House District" with "State House District" for consistency
        if geo_name.startswith('House District'):
            geo_name = geo_name.replace('House District', 'State House District')
        elif geo_name.startswith('Senate District'):
            geo_name = geo_name.replace('Senate District', 'State Senate District')
    
    # Store original name for title
    fact_sheet_title = f"Hawaiʻi Appleseed Fact Sheet: {geo_name}"
    
    # Debug: Print the final title
    print(f"DEBUG: Final fact_sheet_title: '{fact_sheet_title}'")
    
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
    # Dynamic fraction text matching the alice rate (e.g. "over 1 in 2 households").
    # Falls back to a neutral phrasing when ALICE data is missing for this geography.
    try:
        _alice_numeric = float(alice_rate_value) if alice_rate_value is not None else 0
    except (ValueError, TypeError):
        _alice_numeric = 0
    alice_fraction_text = get_fraction_text(_alice_numeric, "households") or "many households"
    
    # Get tax credit data
    tax_credit_data = geo_data.get('tax_credits', {})
    ctc_avg_amount = format_number(tax_credit_data.get('ctc_avg_amount'), is_currency=True, decimals=0)
    ctc_participation_rate = format_number(tax_credit_data.get('ctc_participation_rate'), is_percent=True)
    federal_eitc_avg_amount = format_number(tax_credit_data.get('federal_eitc_avg_amount'), is_currency=True, decimals=0)
    eitc_participation_rate = format_number(tax_credit_data.get('eitc_participation_rate'), is_percent=True)
    state_eitc_avg_amount = format_number(tax_credit_data.get('state_eitc_avg_amount'), is_currency=True, decimals=0)
    
    # Get transportation data
    transportation_data = geo_data.get('transportation', {})
    travel_time_minutes = format_number(transportation_data.get('travel_time_to_work_minutes'), decimals=1)
    public_transportation_pct = format_number(transportation_data.get('public_transportation_pct'), is_percent=True)
    
    # Load and encode the logo
    logo_path = "static/images/appleseed_logo.png"
    logo_base64 = get_image_base64(logo_path)
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo" alt="Hawaii Appleseed Logo">' if logo_base64 else ''
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{fact_sheet_title}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Roboto', Arial, sans-serif;
                line-height: 1.5;
                color: #333;
                background-color: #f5f5f5;
                font-size: 14px;
            }}
            
            .fact-sheet-container {{
                width: 8.5in;
                margin: 20px auto;
                background: white;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                border-radius: 15px;
                overflow: hidden;
                position: relative;
                min-height: 11in;
            }}
            
            .header {{
                background: linear-gradient(135deg, #4a8c1a 0%, #5a9c2a 100%);
                color: white;
                padding: 25px 30px;
                display: flex;
                align-items: center;
                border-radius: 15px 15px 0 0;
            }}
            
            .logo {{
                height: 50px;
                width: auto;
                margin-right: 20px;
                filter: brightness(0) invert(1);
            }}
            
            .header-title {{
                font-size: 32px;
                font-weight: 700;
                flex-grow: 1;
            }}
            
            .main-content {{
                padding: 30px;
            }}
            
            .did-you-know {{
                background: linear-gradient(135deg, #b8d4a8 0%, #a8c498 100%);
                color: #2c5f2d;
                padding: 20px 25px;
                margin: 0 0 30px 0;
                border-radius: 20px;
                text-align: center;
                font-size: 16px;
                font-weight: 500;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            
            .did-you-know h3 {{
                font-size: 18px;
                font-weight: 700;
                margin-bottom: 10px;
                color: #2c5f2d;
            }}
            
            .stats-row {{
                display: flex;
                gap: 20px;
                margin: 30px 0;
                justify-content: center;
            }}
            
            .stat-card {{
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                min-width: 180px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                transition: transform 0.2s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            
            .stat-number {{
                font-size: 32px;
                font-weight: 900;
                color: #2c5f2d;
                display: block;
                margin-bottom: 8px;
            }}
            
            .stat-label {{
                font-size: 14px;
                font-weight: 600;
                color: #555;
                margin-bottom: 8px;
            }}
            
            .stat-comparison {{
                font-size: 11px;
                color: #666;
                line-height: 1.3;
            }}
            
            .content-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                margin: 30px 0;
            }}
            
            .content-grid.second {{
                margin: 15px 0 30px 0;
                page-break-inside: avoid;
                break-inside: avoid;
            }}
            
            .content-card {{
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            
            .content-card h3 {{
                color: #4a8c1a;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
            }}
            
            .content-card h3:before {{
                content: '▶';
                color: #4a8c1a;
                margin-right: 10px;
                font-size: 16px;
            }}
            
            .bullet-points {{
                list-style: none;
                padding: 0;
            }}
            
            .bullet-points li {{
                margin-bottom: 12px;
                padding-left: 20px;
                position: relative;
                line-height: 1.5;
                font-size: 14px;
            }}
            
            .bullet-points li:before {{
                content: '▶';
                color: #4a8c1a;
                position: absolute;
                left: 0;
                font-size: 12px;
                top: 2px;
            }}
            
            .bullet-points li strong {{
                color: #2c5f2d;
                font-weight: 700;
            }}
            
            .stat-highlight {{
                color: #d32f2f;
                font-weight: 700;
                background: #fff3cd;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 1em;
            }}
            
            .footer {{
                background-color: #f8f9fa;
                border-top: 2px solid #e0e0e0;
                padding: 20px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                color: #666;
            }}
            
            .footer-logo {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .footer-logo img {{
                height: 30px;
                width: auto;
            }}
            
            .footer-website {{
                font-weight: 600;
                color: #4a8c1a;
            }}
            
            .print-button {{
                position: fixed;
                top: 20px;
                right: 20px;
                background: rgba(0, 0, 0, 0.65);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                z-index: 1000;
                font-size: 14px;
                transition: background 0.2s ease;
            }}

            .print-button:hover {{
                background: rgba(0, 0, 0, 0.8);
            }}
            
            @media print {{
                .print-button {{
                    display: none !important;
                }}
            }}
            
            @media print {{
                @page {{
                    size: letter;
                    margin: 0.5in;
                }}
                
                * {{
                    -webkit-print-color-adjust: exact !important;
                    color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
                
                body {{
                    background: white !important;
                }}
                
                .fact-sheet-container {{
                    box-shadow: none !important;
                    border-radius: 0 !important;
                    margin: 0 !important;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #4a8c1a 0%, #5a9c2a 100%) !important;
                    color: white !important;
                    -webkit-print-color-adjust: exact !important;
                    color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
                
                .did-you-know {{
                    background: linear-gradient(135deg, #b8d4a8 0%, #a8c498 100%) !important;
                    color: #2c5f2d !important;
                    -webkit-print-color-adjust: exact !important;
                    color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
                
                .stat-highlight {{
                    background: #fff3cd !important;
                    color: #d32f2f !important;
                    -webkit-print-color-adjust: exact !important;
                    color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
                
                .content-grid {{
                    margin: 20px 0;
                }}
                
                .content-grid.second {{
                    margin: 10px 0 20px 0;
                    page-break-inside: avoid;
                    break-inside: avoid;
                }}
                
                .content-card {{
                    page-break-inside: avoid;
                    break-inside: avoid;
                }}
            }}
        </style>
    </head>
    <body>
        <button class="print-button" onclick="window.print()">💾 Save PDF</button>
        <div class="fact-sheet-container">
            <div class="header">
                {logo_html}
                <div class="header-title">{fact_sheet_title}</div>
            </div>
            
            <div class="main-content">
                <!-- Did You Know Section -->
                <div class="did-you-know">
                    <h3>Did you know?</h3>
                    <p>{alice_fraction_text} ({alice_rate}) are employed, yet struggling to make ends meet.</p>
                </div>
                
                <!-- Stats Row -->
                <div class="stats-row">
                    <div class="stat-card">
                        <div class="stat-number">{geo_data.get('formatted_population', 'N/A')}</div>
                        <div class="stat-label">Total Population</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{geo_data.get('formatted_median_income', 'N/A')}</div>
                        <div class="stat-label">Median Income</div>
                        <div class="stat-comparison">
                            {geo_data.get('income_comparison_state', '')}<br>
                            {geo_data.get('income_comparison_county', '')}
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{geo_data.get('formatted_median_rent', 'N/A')}</div>
                        <div class="stat-label">Median Rent</div>
                        <div class="stat-comparison">
                            {geo_data.get('rent_comparison_state', '')}<br>
                            {geo_data.get('rent_comparison_county', '')}
                        </div>
                    </div>
                </div>
                
                <!-- Content Grid -->
                <div class="content-grid">
                    <!-- Tax Credits Column -->
                    <div class="content-card">
                        <h3>Tax Credits</h3>
                        
                        <h4 style="font-style: italic; margin-bottom: 10px; color: #333;">Child Tax Credit (CTC)</h4>
                        <ul class="bullet-points">
                            <li>Families in this area receive an average of <span class="stat-highlight">{ctc_avg_amount}</span> per year, with a participation rate of <span class="stat-highlight">{ctc_participation_rate}</span>. The CTC helps families afford basic necessities like food, housing, and childcare.</li>
                        </ul>
                        
                        <h4 style="font-style: italic; margin: 20px 0 10px 0; color: #333;">Federal Earned Income Tax Credit (EITC)</h4>
                        <ul class="bullet-points">
                            <li>Working families receive an average of <span class="stat-highlight">{federal_eitc_avg_amount}</span> annually, with <span class="stat-highlight">{eitc_participation_rate}</span> of eligible families participating. The EITC rewards work and lifts families out of poverty.</li>
                        </ul>
                        
                        <h4 style="font-style: italic; margin: 20px 0 10px 0; color: #333;">State Earned Income Tax Credit (EITC)</h4>
                        <ul class="bullet-points">
                            <li>Hawaii's state EITC provides an additional <span class="stat-highlight">{state_eitc_avg_amount}</span> on average to working families, supplementing federal support and keeping more money in local communities.</li>
                        </ul>
                    </div>
                    
                    <!-- Food Security Column -->
                    <div class="content-card">
                        <h3>Food Security</h3>
                        
                        <h4 style="font-style: italic; margin-bottom: 10px; color: #333;">SNAP</h4>
                        <ul class="bullet-points">
                            <li>About <strong>1 in 6 households ({snap_participation_rate})</strong> participate in SNAP.</li>
                            <li>In FY 2023, SNAP participants in {geo_name.upper()} received an average of <span class="stat-highlight">{avg_monthly_benefit}</span> per month in SNAP benefits. This averages about <span class="stat-highlight">{daily_per_person}</span> per person per day.</li>
                            <li>SNAP brought <span class="stat-highlight">$519,968,308</span> in benefits to the area in that year.</li>
                        </ul>
                        
                        <h4 style="font-style: italic; margin: 20px 0 10px 0; color: #333;">School Meals</h4>
                        <ul class="bullet-points">
                            <li>As of SY2024-25, <strong>14.3% of schools</strong> in {geo_name.upper()} provided free meals to all students through CEP. That amounts to <strong>1/7 CEP schools</strong>.</li>
                            <li>List of schools:<br>
                                <div style="margin-left: 20px; margin-top: 5px;">
                                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 2px 0;">
                                        <span><strong>School name</strong></span>
                                        <span><strong>Enrollment number</strong></span>
                                    </div>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
                
                <!-- Second Content Grid -->
                <div class="content-grid second">
                    <!-- Transportation Column -->
                    <div class="content-card">
                        <h3>Transportation</h3>
                        <ul class="bullet-points">
                            <li>The average travel time to work is <strong>{travel_time_minutes} minutes</strong>, reflecting the daily commute burden on workers in the area.</li>
                            <li><strong>{public_transportation_pct}</strong> of workers use public transportation to commute to work, indicating reliance on transit systems.</li>
                            <li>Longer commute times can reduce quality of life, increase transportation costs, and limit time available for family and community engagement.</li>
                            <li>Access to reliable public transportation is essential for low-income families who may not own vehicles.</li>
                        </ul>
                    </div>
                    
                    <!-- Housing Column -->
                    <div class="content-card">
                        <h3>Housing</h3>
                        <ul class="bullet-points">
                            <li><strong>{geo_data.get('renter_rate', 'N/A')}% of households</strong> are renters, with a median rent of <span class="stat-highlight">{geo_data.get('formatted_median_rent', 'N/A')}</span> per month.</li>
                            <li>Over <strong>3 in 5 renters (61.6%)</strong> are cost-burdened, spending more than 30% of their income on housing.</li>
                            <li>Just under <strong>2 in 7 renters (27.9%)</strong> are <em>severely</em> cost-burdened, spending more than 50% of their income on housing.</li>
                            <li>The median home value in the area is approximately <strong>N/A</strong>.</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <div class="footer-logo">
                    {logo_html}
                    <span>HAWAIʻI APPLESEED<br><small>CENTER FOR LAW & ECONOMIC JUSTICE</small></span>
                </div>
                <div class="footer-website">www.hiappleseed.org/data-dashboard</div>
            </div>
        </div>
    </body>
    </html>
    """

def display_snap_fact_sheet(geo_data: Dict[str, Any], show_errors: bool = True):
    """Display the SNAP fact sheet with the given geographic data."""
    try:
        # Generate the HTML content for the fact sheet
        html_content = generate_fact_sheet_html(geo_data)
        
        # Display the HTML content in Streamlit
        st.components.v1.html(html_content, height=1200, scrolling=True)
    except Exception as e:
        if show_errors:
            st.error(f"Error generating fact sheet: {e}")
            st.exception(e)

def display_geo_data(geo_id: str):
    """Display the SNAP fact sheet for a specific geographic area."""
    try:
        # Get and prepare data
        geo_data = data_loader.get_all_data_for_geo(geo_id)
        
        if not geo_data or 'name' not in geo_data:
            st.warning("No detailed data available for this location.")
            return
        
        # Prepare data with calculated fields
        geo_data = prepare_geo_data(geo_data)
        
        # Display the fact sheet
        display_snap_fact_sheet(geo_data)
        
    except FileNotFoundError as e:
        st.warning("Could not find a required resource. Some images or data might not display correctly.")
        st.error(f"Resource not found: {e}")
        # Continue with the rest of the page
        display_snap_fact_sheet(geo_data, show_errors=False)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.exception(e)  # This will show the full traceback for debugging

def main():
    """Main function for the geographic detail page."""
    # Hide the title and other Streamlit UI elements
    hide_streamlit_style = """
    <style>
        /* Hide Streamlit UI elements */
        #MainMenu, header, .stApp [data-testid="stToolbar"] {
            display: none !important;
        }

        /* Hide the multi-page navigation sidebar entirely */
        section[data-testid="stSidebar"],
        div[data-testid="stSidebarNav"],
        div[data-testid="stSidebarUserContent"],
        div[data-testid="collapsedControl"],
        button[data-testid="stBaseButton-headerNoPadding"],
        button[title="View app navigation"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stLogoSpacer"] {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
            position: absolute !important;
            z-index: -1000 !important;
        }
        
        /* Reset body and html to full height */
        html, body, #root, .stApp {
            margin: 0 !important;
            padding: 0 !important;
            height: 100% !important;
            width: 100% !important;
            overflow: hidden;
        }
        
        /* Main container — clamp to viewport so the page itself never scrolls */
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
            height: 100vh !important;
            overflow: hidden !important;
            margin: 0 !important;
        }

        /* Iframe takes all available height; its own scrollbar handles content */
        iframe {
            border: none !important;
            width: 100% !important;
            height: 100vh !important;
            min-height: 100vh !important;
            display: block !important;
        }

        /* Lock every Streamlit wrapper so nothing leaks out to the document */
        .stApp > div > div > div > div > section > div,
        .stApp > div > div > div > div > section,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            padding: 0 !important;
            overflow: hidden !important;
            height: 100vh !important;
        }
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Get the geo_id from query parameters
    query_params = st.query_params
    geo_id = query_params.get('geo_id', None)
    
    # Create a container that will hold our content
    container = st.container()
    
    if geo_id:
        with container:
            display_geo_data(geo_id)
    else:
        with container:
            st.error("No geographic ID provided. Please select a feature from the map.")
            if st.button("← Back to Map"):
                st.switch_page("run_leaflet.py")

if __name__ == "__main__":
    main()
