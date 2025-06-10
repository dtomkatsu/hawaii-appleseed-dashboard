import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from flask import request

from ..app import app
from ..data.data_loader import get_geo_data, get_snap_data, get_census_data
from ..ui.components import create_header, create_footer

# Register this page with the app
dash.register_page(__name__, path='/geo_detail')

def layout():
    # Get geo_id from URL query parameters
    geo_id = request.args.get('geo_id', '')
    
    if not geo_id:
        return html.Div([
            create_header(),
            dbc.Container([
                html.H1("Geography Detail", className="mt-4 mb-4"),
                html.Div("No geography ID provided. Please select a location from the map.", 
                         className="alert alert-warning")
            ]),
            create_footer()
        ])
    
    # Load data for this geography
    geo_data = get_geo_data()
    snap_data = get_snap_data()
    census_data = get_census_data()
    
    # Filter data for this specific geography
    geo_info = geo_data[geo_data['id'] == geo_id].iloc[0] if not geo_data[geo_data['id'] == geo_id].empty else None
    snap_info = snap_data[snap_data['geo_id'] == geo_id] if 'geo_id' in snap_data.columns else pd.DataFrame()
    census_info = census_data[census_data['geo_id'] == geo_id] if 'geo_id' in census_data.columns else pd.DataFrame()
    
    if geo_info is None:
        return html.Div([
            create_header(),
            dbc.Container([
                html.H1("Geography Detail", className="mt-4 mb-4"),
                html.Div(f"Geography ID {geo_id} not found.", className="alert alert-danger")
            ]),
            create_footer()
        ])
    
    # Get the name of the geography
    geo_name = geo_info.get('name', f'Geography {geo_id}')
    
    # Create detailed metrics cards
    metrics_cards = []
    
    # Population metrics
    if not census_info.empty and 'population' in census_info.columns:
        population = census_info['population'].iloc[0]
        metrics_cards.append(
            dbc.Card([
                dbc.CardHeader("Population", className="bg-primary text-white"),
                dbc.CardBody([
                    html.H3(f"{population:,}"),
                    html.P("Total population")
                ])
            ], className="mb-4")
        )
    
    # SNAP metrics
    if not snap_info.empty:
        snap_metrics = []
        
        if 'snap_households' in snap_info.columns:
            snap_households = snap_info['snap_households'].iloc[0]
            snap_metrics.append(html.Div([
                html.Strong("SNAP Households: "),
                html.Span(f"{snap_households:,}")
            ]))
            
        if 'snap_participants' in snap_info.columns:
            snap_participants = snap_info['snap_participants'].iloc[0]
            snap_metrics.append(html.Div([
                html.Strong("SNAP Participants: "),
                html.Span(f"{snap_participants:,}")
            ]))
            
        if 'snap_benefits' in snap_info.columns:
            snap_benefits = snap_info['snap_benefits'].iloc[0]
            snap_metrics.append(html.Div([
                html.Strong("SNAP Benefits: "),
                html.Span(f"${snap_benefits:,.2f}")
            ]))
            
        if snap_metrics:
            metrics_cards.append(
                dbc.Card([
                    dbc.CardHeader("SNAP Program Data", className="bg-success text-white"),
                    dbc.CardBody(snap_metrics)
                ], className="mb-4")
            )
    
    # Demographics metrics
    if not census_info.empty:
        demo_metrics = []
        
        demographic_columns = [
            ('median_income', 'Median Income', '${:,.2f}'),
            ('poverty_rate', 'Poverty Rate', '{:.1f}%'),
            ('child_poverty_rate', 'Child Poverty Rate', '{:.1f}%'),
            ('unemployment_rate', 'Unemployment Rate', '{:.1f}%')
        ]
        
        for col, label, fmt in demographic_columns:
            if col in census_info.columns:
                value = census_info[col].iloc[0]
                if col == 'poverty_rate' or col == 'child_poverty_rate' or col == 'unemployment_rate':
                    value = value * 100  # Convert decimal to percentage
                demo_metrics.append(html.Div([
                    html.Strong(f"{label}: "),
                    html.Span(fmt.format(value))
                ]))
                
        if demo_metrics:
            metrics_cards.append(
                dbc.Card([
                    dbc.CardHeader("Demographics", className="bg-info text-white"),
                    dbc.CardBody(demo_metrics)
                ], className="mb-4")
            )
    
    # Create layout for the page
    return html.Div([
        create_header(),
        dbc.Container([
            html.H1(f"Detailed Data for {geo_name}", className="mt-4 mb-4"),
            
            # Back button
            html.Div([
                dbc.Button("← Back to Map", id="back-to-map", color="secondary", className="mb-4"),
            ]),
            
            # Geography information
            dbc.Row([
                dbc.Col([
                    html.H2("Geography Information", className="mb-3"),
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(geo_name, className="card-title"),
                            html.P(f"ID: {geo_id}", className="card-text"),
                            html.P(f"Type: {geo_info.get('type', 'N/A')}", className="card-text"),
                        ])
                    ], className="mb-4")
                ], md=12)
            ]),
            
            # Metrics section
            dbc.Row([
                dbc.Col([
                    html.H2("Key Metrics", className="mb-3"),
                    html.Div(metrics_cards)
                ], md=12)
            ]),
            
            # Additional data section - can be expanded later
            dbc.Row([
                dbc.Col([
                    html.H2("Additional Data", className="mb-3"),
                    html.P("More detailed data visualizations will be added in future updates.")
                ], md=12)
            ], className="mb-4"),
            
        ], className="py-4"),
        create_footer()
    ])

# Callback for back button
@callback(
    Output("_pages_location", "pathname"),
    Input("back-to-map", "n_clicks"),
    prevent_initial_call=True
)
def go_back_to_map(n_clicks):
    if n_clicks:
        return "/"
    return dash.no_update
