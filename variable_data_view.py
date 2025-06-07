"""Variable Data View for Hawaii Appleseed Dashboard."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import logging

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import local modules
from src.data.data_loader import DataLoader

# Set up logging
logger = logging.getLogger(__name__)

def create_variable_data_view():
    """Create the Variable Data view for detailed geography information."""
    
    # Check if a feature is selected
    if 'selected_feature_data' not in st.session_state or not st.session_state['selected_feature_data']:
        st.info("👆 Please click on a geography in the Map View tab to see detailed variable data.")
        return
    
    # Get the selected feature data
    feature_data = st.session_state['selected_feature_data']
    feature_name = feature_data.get('name', 'Unknown')
    
    # Display header
    st.markdown(f"# 📍 {feature_name}")
    st.markdown("---")
    
    # Create summary metrics
    create_summary_metrics(feature_data)
    
    # Create visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        create_demographic_chart(feature_data)
        create_economic_indicators_chart(feature_data)
    
    with col2:
        create_housing_chart(feature_data)
        create_education_health_chart(feature_data)
    
    # Create detailed data table
    st.markdown("---")
    create_data_table(feature_data)
    
    # Add comparison section
    st.markdown("---")
    create_comparison_section(feature_data)

def create_summary_metrics(feature_data):
    """Create summary metric cards for key indicators."""
    st.markdown("### Key Indicators")
    
    # Define metric groups
    metrics = [
        ("Population", feature_data.get('population', 'N/A'), "👥"),
        ("Poverty Rate", f"{feature_data.get('poverty_rate', 'N/A')}%", "📊"),
        ("Median Income", f"${feature_data.get('median_income', 'N/A'):,}" if isinstance(feature_data.get('median_income'), (int, float)) else 'N/A', "💰"),
        ("Unemployment", f"{feature_data.get('unemployment_rate', 'N/A')}%", "💼")
    ]
    
    cols = st.columns(len(metrics))
    for col, (label, value, icon) in zip(cols, metrics):
        with col:
            st.metric(
                label=f"{icon} {label}",
                value=value
            )

def create_demographic_chart(feature_data):
    """Create demographic breakdown chart."""
    st.markdown("### Demographics")
    
    # Prepare demographic data
    demo_data = {
        'Race/Ethnicity': [],
        'Percentage': []
    }
    
    race_columns = {
        'white_alone_pct': 'White Alone',
        'asian_alone_pct': 'Asian Alone',
        'native_hawaiian_pi_pct': 'Native Hawaiian/PI',
        'black_alone_pct': 'Black Alone',
        'hispanic_pct': 'Hispanic/Latino',
        'two_or_more_races_pct': 'Two or More Races'
    }
    
    for col, label in race_columns.items():
        if col in feature_data and feature_data[col] != 'N/A':
            demo_data['Race/Ethnicity'].append(label)
            demo_data['Percentage'].append(float(feature_data[col]))
    
    if demo_data['Race/Ethnicity']:
        df = pd.DataFrame(demo_data)
        fig = px.pie(df, values='Percentage', names='Race/Ethnicity', 
                     title="Racial/Ethnic Composition",
                     hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No demographic data available")

def create_economic_indicators_chart(feature_data):
    """Create economic indicators chart."""
    st.markdown("### Economic Indicators")
    
    # Prepare economic data
    indicators = {
        'poverty_rate': 'Poverty Rate',
        'unemployment_rate': 'Unemployment Rate',
        'snap_benefits_pct': 'SNAP Benefits',
        'no_health_insurance_pct': 'No Health Insurance'
    }
    
    values = []
    labels = []
    
    for col, label in indicators.items():
        if col in feature_data and feature_data[col] != 'N/A':
            values.append(float(feature_data[col]))
            labels.append(label)
    
    if values:
        fig = go.Figure(data=[
            go.Bar(x=labels, y=values, text=[f"{v:.1f}%" for v in values],
                   textposition='auto',
                   marker_color=['#EF5350', '#FF7043', '#FFA726', '#FFCA28'])
        ])
        fig.update_layout(
            title="Economic Challenges (%)",
            yaxis_title="Percentage",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No economic data available")

def create_housing_chart(feature_data):
    """Create housing-related chart."""
    st.markdown("### Housing")
    
    # Create housing metrics
    housing_metrics = []
    
    if 'median_home_value' in feature_data and feature_data['median_home_value'] != 'N/A':
        housing_metrics.append(("Median Home Value", f"${feature_data['median_home_value']:,}"))
    
    if 'median_rent' in feature_data and feature_data['median_rent'] != 'N/A':
        housing_metrics.append(("Median Rent", f"${feature_data['median_rent']:,}"))
    
    if 'homeownership_rate' in feature_data and feature_data['homeownership_rate'] != 'N/A':
        housing_metrics.append(("Homeownership Rate", f"{feature_data['homeownership_rate']}%"))
    
    if 'rent_burden_rate' in feature_data and feature_data['rent_burden_rate'] != 'N/A':
        housing_metrics.append(("Rent Burden Rate", f"{feature_data['rent_burden_rate']}%"))
    
    if housing_metrics:
        # Create a simple table for housing metrics
        for metric, value in housing_metrics:
            st.metric(label=metric, value=value)
    else:
        st.info("No housing data available")

def create_education_health_chart(feature_data):
    """Create education and health chart."""
    st.markdown("### Education & Health")
    
    # Prepare data
    categories = []
    values = []
    
    edu_health_cols = {
        'college_educated_pct': 'College Educated',
        'high_school_grad_pct': 'High School Graduate',
        'health_insurance_pct': 'Has Health Insurance',
        'disability_pct': 'Has Disability'
    }
    
    for col, label in edu_health_cols.items():
        if col in feature_data and feature_data[col] != 'N/A':
            categories.append(label)
            values.append(float(feature_data[col]))
    
    if categories:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=categories,
            y=values,
            mode='markers+lines',
            marker=dict(size=12, color='#1E88E5'),
            line=dict(width=3, color='#1E88E5'),
            text=[f"{v:.1f}%" for v in values],
            textposition='top center'
        ))
        fig.update_layout(
            title="Education & Health Indicators (%)",
            yaxis_title="Percentage",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No education/health data available")

def create_data_table(feature_data):
    """Create a comprehensive data table."""
    st.markdown("### All Variables")
    
    # Organize data into categories
    categories = {
        "Demographics": [
            'population', 'white_alone_pct', 'asian_alone_pct', 
            'native_hawaiian_pi_pct', 'black_alone_pct', 'hispanic_pct',
            'two_or_more_races_pct'
        ],
        "Economic": [
            'poverty_rate', 'median_income', 'unemployment_rate',
            'snap_benefits_pct', 'per_capita_income', 'gini_index'
        ],
        "Housing": [
            'median_home_value', 'median_rent', 'homeownership_rate',
            'rent_burden_rate', 'overcrowded_housing_pct', 'vacant_housing_pct'
        ],
        "Education & Health": [
            'college_educated_pct', 'high_school_grad_pct', 'bachelors_rate',
            'health_insurance_pct', 'disability_pct', 'veteran_pct'
        ]
    }
    
    # Create expandable sections for each category
    for category, variables in categories.items():
        with st.expander(f"{category} Variables", expanded=True):
            data_rows = []
            for var in variables:
                if var in feature_data:
                    # Format the variable name
                    display_name = var.replace('_', ' ').replace('pct', '(%)').title()
                    value = feature_data[var]
                    
                    # Format the value
                    if value == 'N/A':
                        formatted_value = 'N/A'
                    elif 'pct' in var or 'rate' in var:
                        formatted_value = f"{value}%"
                    elif var in ['median_income', 'median_home_value', 'median_rent', 'per_capita_income']:
                        formatted_value = f"${value:,}" if isinstance(value, (int, float)) else value
                    else:
                        formatted_value = f"{value:,}" if isinstance(value, (int, float)) else value
                    
                    data_rows.append({
                        'Variable': display_name,
                        'Value': formatted_value
                    })
            
            if data_rows:
                df = pd.DataFrame(data_rows)
                st.dataframe(df, hide_index=True, use_container_width=True)
            else:
                st.info(f"No {category.lower()} data available")

def create_comparison_section(feature_data):
    """Create comparison with other geographies."""
    st.markdown("### Geographic Comparison")
    
    # Get the current geography level
    geo_level = st.session_state.get('active_layer', 'State Boundary')
    
    # Load all data for comparison
    data_loader = DataLoader()
    geo_level_map = {
        'State Boundary': 'state',
        'Counties': 'county',
        'House Districts': 'house',
        'Senate Districts': 'senate'
    }
    
    comparison_data = data_loader.get_data(geo_level_map.get(geo_level, 'state'))
    
    if comparison_data is not None and not comparison_data.empty:
        # Select variable to compare
        numeric_cols = [col for col in comparison_data.columns 
                       if col not in ['name', 'NAME', 'geoid', 'GEOID'] 
                       and comparison_data[col].dtype in ['float64', 'int64']]
        
        selected_var = st.selectbox(
            "Select variable to compare:",
            options=numeric_cols,
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        if selected_var:
            # Create comparison chart
            fig = px.bar(
                comparison_data.sort_values(by=selected_var, ascending=False),
                x='name' if 'name' in comparison_data.columns else 'NAME',
                y=selected_var,
                title=f"{selected_var.replace('_', ' ').title()} Across All {geo_level}",
                color=selected_var,
                color_continuous_scale='Blues'
            )
            
            # Highlight the selected geography
            current_name = feature_data.get('name', feature_data.get('NAME'))
            if current_name:
                # Find the index of the current geography
                x_values = comparison_data['name'].tolist() if 'name' in comparison_data.columns else comparison_data['NAME'].tolist()
                if current_name in x_values:
                    idx = x_values.index(current_name)
                    fig.add_annotation(
                        x=current_name,
                        y=comparison_data.iloc[idx][selected_var],
                        text="Selected",
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=2,
                        arrowcolor="red",
                        ax=0,
                        ay=-40
                    )
            
            fig.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show ranking
            if current_name:
                sorted_data = comparison_data.sort_values(by=selected_var, ascending=False)
                name_col = 'name' if 'name' in sorted_data.columns else 'NAME'
                rank = sorted_data[sorted_data[name_col] == current_name].index[0] + 1
                total = len(sorted_data)
                st.info(f"**{current_name}** ranks **#{rank}** out of **{total}** for {selected_var.replace('_', ' ').title()}")
    else:
        st.warning("No comparison data available")