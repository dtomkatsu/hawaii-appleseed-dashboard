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
    
    # Add housing cost burden data if available
    if 'housing' in geo_data and 'rent_burden_rate' in geo_data['housing']:
        rent_burden = geo_data['housing']['rent_burden_rate']
        geo_data['housing_cost_burden'] = f"{float(rent_burden):.1f}%" if rent_burden is not None else "N/A"
    else:
        geo_data['housing_cost_burden'] = "N/A"
    
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
    
    javascript_code = """
    function printFactSheet() {
        window.print();
    }
    
    // Setup tooltips function
    function setupTooltips() {
        // Get all tooltip pairs
        const tooltipPairs = [
            { trigger: '.alice-rate-text', tooltip: '.alice-tooltip' },
            { trigger: '.snap-title', tooltip: '.snap-tooltip' },
            { trigger: '.housing-title', tooltip: '.housing-tooltip' }
        ];
        
        // Store persistent states
        const persistentStates = {};
        
        tooltipPairs.forEach(pair => {
            const triggerEl = document.querySelector(pair.trigger);
            const tooltipEl = document.querySelector(pair.tooltip);
            
            if (!triggerEl || !tooltipEl) {
                console.log('Missing element:', pair.trigger, 'or', pair.tooltip);
                return;
            }
            
            // Initialize persistent state
            persistentStates[pair.trigger] = false;
            
            // Click to toggle persistent tooltip
            triggerEl.addEventListener('click', function(e) {
                e.stopPropagation();
                e.preventDefault();
                
                persistentStates[pair.trigger] = !persistentStates[pair.trigger];
                
                if (persistentStates[pair.trigger]) {
                    tooltipEl.classList.add('visible', 'persistent');
                    
                    // Close other tooltips
                    tooltipPairs.forEach(otherPair => {
                        if (otherPair.trigger !== pair.trigger) {
                            const otherTooltip = document.querySelector(otherPair.tooltip);
                            if (otherTooltip) {
                                otherTooltip.classList.remove('visible', 'persistent');
                                persistentStates[otherPair.trigger] = false;
                            }
                        }
                    });
                } else {
                    tooltipEl.classList.remove('visible', 'persistent');
                }
            });
            
            // Show on hover (if not persistent)
            triggerEl.addEventListener('mouseenter', function() {
                if (!persistentStates[pair.trigger]) {
                    tooltipEl.classList.add('visible');
                }
            });
            
            // Hide on mouse leave (if not persistent)
            triggerEl.addEventListener('mouseleave', function() {
                if (!persistentStates[pair.trigger]) {
                    tooltipEl.classList.remove('visible');
                }
            });
        });
        
        // Close all tooltips when clicking outside
        document.addEventListener('click', function(e) {
            tooltipPairs.forEach(pair => {
                const triggerEl = document.querySelector(pair.trigger);
                const tooltipEl = document.querySelector(pair.tooltip);
                
                if (!triggerEl || !tooltipEl) return;
                
                if (persistentStates[pair.trigger] && 
                    !triggerEl.contains(e.target) && 
                    !tooltipEl.contains(e.target)) {
                    tooltipEl.classList.remove('visible', 'persistent');
                    persistentStates[pair.trigger] = false;
                }
            });
        });
    }
    
    // Wait for DOM and then setup tooltips
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupTooltips);
    } else {
        // DOM is already loaded, but wait a bit for dynamic content
        setTimeout(setupTooltips, 100);
    }
    
    // Function to fix housing tooltip positioning
    function fixHousingTooltipPosition() {
        const housingTitle = document.querySelector('.housing-title');
        const housingTooltip = document.querySelector('.housing-tooltip');
        if (!housingTitle || !housingTooltip) return;
        
        // Move tooltip to body if not already there
        if (housingTooltip.parentNode !== document.body) {
            document.body.appendChild(housingTooltip);
        }
        
        function positionTooltip() {
            if (!housingTooltip) return;
            
            const rect = housingTitle.getBoundingClientRect();
            const tooltipRect = housingTooltip.getBoundingClientRect();
            
            // Calculate position - center it more on the page
            const viewportWidth = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
            const viewportHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
            
            // Calculate centered position
            let left = (viewportWidth - tooltipRect.width) / 2;
            let top = (viewportHeight - tooltipRect.height) / 2;
            
            // Ensure it's not too close to the edges
            const padding = 20;
            left = Math.max(padding, Math.min(left, viewportWidth - tooltipRect.width - padding));
            top = Math.max(padding, Math.min(top, viewportHeight - tooltipRect.height - padding));
            
            // Apply position with transform for better performance
            housingTooltip.style.transform = `translate3d(${left}px, ${top}px, 0)`;
            housingTooltip.style.webkitTransform = `translate3d(${left}px, ${top}px, 0)`;
            housingTooltip.style.opacity = '1';
        }
        
        // Initial position
        positionTooltip();
        
        // Update position on hover
        housingTitle.addEventListener('mouseenter', positionTooltip);
        
        // Update position when tooltip becomes visible
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.target === housingTooltip && 
                    (housingTooltip.classList.contains('visible') || 
                     housingTooltip.classList.contains('persistent'))) {
                    positionTooltip();
                }
            });
        });
        
        observer.observe(housingTooltip, {
            attributes: true,
            attributeFilter: ['class']
        });
        
        // Update position on scroll/resize with debounce
        let resizeTimer;
        function handleResize() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(positionTooltip, 100);
        }
        
        window.addEventListener('scroll', handleResize, { passive: true });
        window.addEventListener('resize', handleResize);
        
        // Clean up event listeners when tooltip is removed
        return function cleanup() {
            window.removeEventListener('scroll', handleResize);
            window.removeEventListener('resize', handleResize);
            observer.disconnect();
            housingTitle.removeEventListener('mouseenter', positionTooltip);
        };
    }  
    // Initialize everything
    function initTooltips() {
        setupTooltips();
        fixHousingTooltipPosition();
    }
    
    // Wait for DOM and then initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTooltips);
    } else {
        // DOM is already loaded, but wait a bit for dynamic content
        setTimeout(initTooltips, 100);
    }
    
    // Also retry after a longer delay as a failsafe
    setTimeout(initTooltips, 500);
    """
    
    return f"""
    <!DOCTYPE html>
    <html style="height: 100%;">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SNAP Fact Sheet - {geo_name}</title>
        <style>
            /* Reset and base styles */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            html, body {{
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden;
                font-family: Arial, sans-serif;
            }}
            
            body {{
                display: flex;
                flex-direction: column;
                height: 100vh;
                margin: 0;
                padding: 0;
                background: #f5f5f5;
            }}
            
            .fact-sheet-container {{
                flex: 1;
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
                width: 100%;
                max-width: 8in;
                margin: 0 auto;
                background: white;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            
            .fact-sheet {{
                padding: 20px;
                width: 100%;
                box-sizing: border-box;
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
            
            /* Base tooltip styles */
            .alice-tooltip, .snap-tooltip {{
                visibility: hidden;
                width: 300px;
                background-color: #f9f9f9;
                color: #333;
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
                border: 1px solid #ddd;
            }}
            
            .alice-tooltip p, .snap-tooltip p {{
                margin: 0 0 10px 0;
                color: #333;
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
                border-color: transparent transparent #f9f9f9 transparent;
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
            
            /* Housing tooltip specific styles */
            .housing-title {{
                cursor: help;
                border-bottom: 1px dashed #555;
                display: inline-block;
                position: relative;
                z-index: 1;
            }}
            
            /* Move tooltip to body level to avoid parent container issues */
            /* Move tooltip to body level to avoid parent container issues */
            .housing-tooltip {{
                visibility: hidden;
                width: 300px;
                background-color: #2A3B72 !important;
                color: #fff !important;
                text-align: left;
                border-radius: 8px;
                padding: 15px;
                position: fixed;
                z-index: 2147483647;
                opacity: 0;
                transition: opacity 0.3s ease, transform 0.3s ease, visibility 0.3s ease;
                font-size: 14px;
                line-height: 1.5;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                pointer-events: none;
                max-width: 90vw;
                border: none !important;
                background-image: none !important;
                transform: translate3d(0, 0, 0);
                -webkit-transform: translate3d(0, 0, 0);
                -webkit-backface-visibility: hidden;
                -webkit-perspective: 1000;
                -webkit-background-clip: padding-box;
                background-clip: padding-box;
                left: 0;
                top: 0;
                will-change: transform, opacity;
            }}
            
            /* Tooltip content styling */
            .housing-tooltip * {{
                position: relative;
                z-index: 2;
                color: #fff !important;
                text-shadow: none !important;
            }}
            
            /* Background layer for tooltip */
            .housing-tooltip::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: #2A3B72 !important;
                border-radius: 8px;
                z-index: 1;
                /* Ensure this covers the entire tooltip */
                box-shadow: 0 0 0 10px #2A3B72; /* Extend beyond borders */
                margin: -10px;
            }}
            
            .housing-tooltip.visible,
            .housing-tooltip.persistent {{
                visibility: visible;
                opacity: 1;
                pointer-events: auto;
                background: #2A3B72 !important;
                /* Keep the transform for positioning */
                transform: translate3d(-50%, -5px, 0);
                -webkit-transform: translate3d(-50%, -5px, 0);
            }}
            
            .housing-title:hover + .housing-tooltip,
            .housing-tooltip:hover {{
                transform: translate3d(-50%, -8px, 0);
                -webkit-transform: translate3d(-50%, -8px, 0);
                box-shadow: 0 6px 25px rgba(0, 0, 0, 0.2);
            }}
            
            .housing-tooltip p {{
                margin: 0 0 10px 0;
            }}
            
            .housing-tooltip p:last-child {{
                margin-bottom: 0;
            }}
            
            .housing-tooltip::after {{
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -10px;
                border-width: 10px;
                border-style: solid;
                border-color: #2A3B72 transparent transparent transparent;
                z-index: 99999;
                pointer-events: none;
                transition: all 0.3s ease;
            }}
            
            .housing-tooltip.visible::after,
            .housing-tooltip.persistent::after {{
                border-width: 12px;
                margin-left: -12px;
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
                /* Reset print margins and padding */
                @page {{
                    size: auto;
                    margin: 1cm;
                }}
                
                /* Hide print button */
                .print-button {{
                    display: none !important;
                }}
                
                /* Reset body styles for printing */
                html, body {{
                    height: auto !important;
                    overflow: visible !important;
                    background: white !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
                
                /* Make sure the fact sheet takes full width and has no shadow */
                .fact-sheet-container {{
                    width: 100% !important;
                    max-width: 100% !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    box-shadow: none !important;
                    overflow: visible !important;
                    height: auto !important;
                }}
                
                /* Ensure fact sheet content is visible */
                .fact-sheet {{
                    width: 100% !important;
                    max-width: 100% !important;
                    margin: 0 !important;
                    padding: 0.5cm !important;
                    box-shadow: none !important;
                    break-inside: avoid;
                }}
                
                /* Prevent page breaks inside important sections */
                .stats-grid, .four-stats, .bullet-points li {{
                    break-inside: avoid;
                }}
                
                /* Ensure text is black for better print contrast */
                * {{
                    color: #000 !important;
                }}
                
                /* Make sure links are visible in print */
                a {{
                    text-decoration: underline !important;
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
            
            /* Ensure the four-stats container doesn't create a stacking context */
            .four-stats {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
                /* Remove any z-index or transform properties */
                position: static;
            }}
            
            /* Alternative approach if :has() is not supported */
            .small-stat-box.tooltip-active {{
                z-index: 1000 !important;
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
                position: relative;
                overflow: visible !important;
                /* Remove z-index from stat boxes to prevent stacking issues */
            }}
            
            /* Add hover state to temporarily increase z-index */
            .small-stat-box:has(.housing-title:hover),
            .small-stat-box:has(.housing-tooltip.visible) {{
                z-index: 1000 !important;
            }}
            
            .small-stat-number {{
                font-size: 28px;
                font-weight: 900;
                color: #d32f2f;
                display: block;
                text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }}
            
            .small-stat-label {{
                font-size: 12px;
                color: #555;
                margin-top: 5px;
                text-align: center;
                line-height: 1.2;
                position: relative;
                display: inline-block;
                overflow: visible !important;
                /* Remove z-index */
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
        <div class="fact-sheet-container">
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
                            <li>Approximately <strong style="color: black;">{snap_fraction} households <span style="background-color: #006400; color: white; padding: 2px 6px; border-radius: 4px; margin: 0 2px;">({snap_participation_rate})</span></strong> participate in SNAP. <span style="color: red; font-weight: bold;">{comparison_text}</span></li>
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
                            <div class="small-stat-number">{geo_data.get('housing_cost_burden', 'N/A')}</div>
                            <div class="small-stat-label">
                                <span class="housing-title">Households with housing cost burden</span>
                                <div class="housing-tooltip">
                                    <p>A household is considered "housing cost burdened" by the Census if it spends more than 30% of its income on housing expenses, which include rent or mortgage payments, utilities, and related fees.</p>
                                    <p>If a household spends more than 50% of its income on these costs, it is classified as "severely cost burdened".</p>
                                </div>
                            </div>
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
    # Remove fixed height and scrolling to use the parent container's scroll
    html(html_content, height=None, scrolling=False)

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
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.exception(e)

def main():
    """Main function for the geographic detail page."""
    # Hide the title and other Streamlit UI elements
    hide_streamlit_style = """
    <style>
        #MainMenu, header, .stApp [data-testid="stToolbar"] {
            display: none !important;
        }
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
        }
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
    </style>
    """
    # Enhanced CSS to handle scrolling and layout
    hide_streamlit_style = """
    <style>
        /* Hide Streamlit UI elements */
        #MainMenu, header, .stApp [data-testid="stToolbar"] {
            display: none !important;
        }
        
        /* Reset body and html to full height */
        html, body, #root, .stApp {
            margin: 0 !important;
            padding: 0 !important;
            height: 100% !important;
            width: 100% !important;
            overflow: hidden;
        }
        
        /* Main container */
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
            height: 100vh !important;
            margin: 0 !important;
        }
        
        /* Iframe styling */
        iframe {
            border: none !important;
            width: 100% !important;
            height: 100% !important;
            min-height: 100vh !important;
        }
        
        /* Hide Streamlit's default scrolling */
        .stApp > div > div > div > div > section > div {
            padding: 0 !important;
            overflow: visible !important;
        }
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Get the geo_id from query parameters
    query_params = st.experimental_get_query_params()
    geo_id = query_params.get('geo_id', [None])[0]
    
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