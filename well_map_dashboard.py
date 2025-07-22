# Install dash and plotly: pip install dash plotly
import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import plotly.express as px
import numpy as np

# Haversine distance function (miles)
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

# 1. Read data
prod_df = pd.read_csv('data/Wells_Production_for modeling-882ff_2025-06-16.csv', parse_dates=['ProducingMonth'])
header_df = pd.read_csv('data/Header_Wells_info_by each API-14cc3_2025-06-16.csv')

# 2. Column names
well_id_col = 'API_UWI'
lat_col = 'Latitude'
lon_col = 'Longitude'
prod_col = 'Prod_BOE'
date_col = 'ProducingMonth'

# 3. Merge data
header_cols = [well_id_col, lat_col, lon_col, 'ENVOperator', 'ENVWellType', 'WellName', 'County']
df = pd.merge(prod_df, header_df[header_cols], on=well_id_col, how='inner')
wells_map = header_df[header_cols].drop_duplicates(subset=well_id_col).reset_index(drop=True)

# 4. Get current month for BOE calculation
latest_month = df[date_col].max()
current_month_df = df[df[date_col] == latest_month]

# 5. Dash App
app = dash.Dash(__name__)

# 6. Custom styles
CARD_STYLE = {
    'background': 'white',
    'borderRadius': '10px',
    'boxShadow': '0 2px 8px rgba(0,0,0,0.07)',
    'padding': '18px',
    'marginBottom': '18px',
}
BG_STYLE = {
    'background': '#f8f9fa',
    'minHeight': '100vh',
    'fontFamily': 'Roboto, Open Sans, Arial, sans-serif',
}
TITLE_STYLE = {
    'fontSize': '2.3rem',
    'fontWeight': 'bold',
    'color': '#1a237e',
    'marginBottom': '0.2em',
    'letterSpacing': '0.02em',
}
DESC_STYLE = {
    'fontSize': '1.1rem',
    'color': '#495057',
    'marginBottom': '1.5em',
}

app.layout = html.Div([
    html.Div([
        html.H1("Well Production Overview", style=TITLE_STYLE),
        html.P("Interactive dashboard for visualizing well locations, production history, and nearby well statistics. Select a well and radius to explore production trends and spatial relationships.", style=DESC_STYLE)
    ], style={'textAlign': 'center', 'background': 'white', 'padding': '24px', 'marginBottom': '18px', 'borderRadius': '10px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.07)'}),
    html.Div([
        html.Div([
            html.H4("Select Radius (miles)", style={'fontWeight': 'bold', 'color': '#1565c0'}),
            dcc.Dropdown(
                id='radius-dropdown',
                options=[{'label': f'{r} mile', 'value': r} for r in [1, 2, 5, 10]],
                value=2,
                clearable=False,
                style={'width': '150px', 'marginBottom': '10px'}
            ),
            html.Div(id='selected-well-info', style={'fontSize': 15, 'marginBottom': '14px'}),
            html.H4("Wells within Radius", style={'fontWeight': 'bold', 'color': '#1565c0', 'marginTop': '18px'}),
            dash_table.DataTable(
                id='wells-table',
                columns=[
                    {'name': 'API', 'id': 'API_UWI'},
                    {'name': 'Name', 'id': 'WellName'},
                    {'name': 'Operator', 'id': 'ENVOperator'},
                    {'name': 'Type', 'id': 'ENVWellType'},
                    {'name': 'County', 'id': 'County'},
                    {'name': 'Lat', 'id': 'Latitude'},
                    {'name': 'Lon', 'id': 'Longitude'}
                ],
                page_size=8,
                style_table={'overflowX': 'auto', 'background': 'white'},
                style_cell={
                    'fontSize': 13,
                    'padding': '6px',
                    'minWidth': '60px',
                    'maxWidth': '180px',
                    'whiteSpace': 'normal',
                    'fontFamily': 'Roboto, Open Sans, Arial, sans-serif',
                },
                style_header={
                    'backgroundColor': '#e3eafc',
                    'fontWeight': 'bold',
                    'fontSize': 14,
                    'borderBottom': '2px solid #90caf9',
                },
                style_data_conditional=[
                    {
                        'if': {'state': 'active'},
                        'backgroundColor': '#e3f2fd',
                        'border': '1px solid #90caf9',
                    },
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f5faff',
                    },
                ],
            )
        ], style={**CARD_STYLE, 'width': '35%', 'display': 'inline-block', 'verticalAlign': 'top', 'height': '600px', 'overflowY': 'auto'}),
        html.Div([
            dcc.Graph(id='well-map', config={'scrollZoom': True})
        ], style={**CARD_STYLE, 'width': '64%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0', 'height': '600px'}),
    ], style={'width': '100%', 'display': 'flex', 'flexDirection': 'row', 'gap': '2%' }),
    html.Div([
        html.Div([
            html.H4("Production History (BOE)", style={'fontWeight': 'bold', 'color': '#1565c0'}),
            dcc.Graph(id='prod-history')
        ], style={**CARD_STYLE, 'width': '100%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginBottom': 0}),
    ], style={'width': '100%', 'padding': '10px', 'background': 'transparent'}),
], style=BG_STYLE)

@app.callback(
    Output('well-map', 'figure'),
    Output('selected-well-info', 'children'),
    Output('wells-table', 'data'),
    Output('prod-history', 'figure'),
    Input('well-map', 'clickData'),
    Input('radius-dropdown', 'value')
)
def update_dashboard(clickData, radius):
    # Default: select first well
    if clickData is None:
        center = wells_map.iloc[0]
    else:
        point = clickData['points'][0]
        # Only handle clicks on well points (not the circle)
        if 'customdata' in point and point['customdata'] is not None:
            api_val = point['customdata'][2]  # 'API_UWI' is the third in custom_data
            center = wells_map[wells_map[well_id_col] == api_val].iloc[0]
        else:
            # Fallback: do not change center well if click is not on a well point
            center = wells_map.iloc[0]
    # Calculate distances
    dists = haversine(center[lat_col], center[lon_col], wells_map[lat_col], wells_map[lon_col])
    wells_map['distance'] = dists
    filtered = wells_map[dists <= radius]
    filtered_ids = filtered[well_id_col].tolist()
    # Map coloring and hover tooltip
    color_arr = np.full(len(wells_map), '#a0522d')  # default brown
    if len(filtered_ids) > 0:
        # Set in-radius wells to medium blue
        in_radius_mask = wells_map[well_id_col].isin(filtered_ids)
        color_arr[in_radius_mask] = '#64b5f6'
    # Set selected well to dark blue
    selected_mask = wells_map[well_id_col] == center[well_id_col]
    color_arr[selected_mask] = '#1976d2'
    hovertemplate = (
        '<b>Well Name:</b> %{customdata[0]}<br>'
        '<b>Operator:</b> %{customdata[1]}<br>'
        '<b>API:</b> %{customdata[2]}<br>'
        '<b>Type:</b> %{customdata[3]}<br>'
        '<b>County:</b> %{customdata[4]}<br>'
        '<b>Lat:</b> %{lat:.5f}<br>'
        '<b>Lon:</b> %{lon:.5f}<extra></extra>'
    )
    fig = px.scatter_mapbox(
        wells_map,
        lat=lat_col,
        lon=lon_col,
        custom_data=['WellName', 'ENVOperator', 'API_UWI', 'ENVWellType', 'County'],
        zoom=8,
        height=500
    )
    fig.update_traces(
        marker=dict(size=8, color=color_arr, opacity=0.85),
        hovertemplate=hovertemplate
    )
    fig.update_layout(mapbox_style="open-street-map", showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
    # Draw circle overlay
    circle_lats = []
    circle_lons = []
    for angle in np.linspace(0, 2*np.pi, 100):
        dlat = (radius / 69.0) * np.cos(angle)
        dlon = (radius / (69.0 * np.cos(np.radians(center[lat_col])))) * np.sin(angle)
        circle_lats.append(center[lat_col] + dlat)
        circle_lons.append(center[lon_col] + dlon)
    fig.add_trace(
        px.line_mapbox(
            pd.DataFrame({lat_col: circle_lats, lon_col: circle_lons}),
            lat=lat_col, lon=lon_col
        ).data[0]
    )
    # Calculate metrics for filtered wells
    num_wells = len(filtered)
    filtered_current = current_month_df[current_month_df[well_id_col].isin(filtered_ids)]
    total_boe = filtered_current[prod_col].sum()
    # Selected well info
    info = html.Div([
        html.P(f"Well ID: {center[well_id_col]}", style={'margin': '0'}),
        html.P(f"Operator: {center['ENVOperator']}", style={'margin': '0'}),
        html.P(f"Type: {center['ENVWellType']}", style={'margin': '0'}),
        html.P(f"Name: {center['WellName']}", style={'margin': '0'}),
        html.P(f"County: {center['County']}", style={'margin': '0'}),
        html.P(f"Latitude: {center[lat_col]:.5f}, Longitude: {center[lon_col]:.5f}", style={'margin': '0'}),
        # Metrics summary cards
        html.Div([
            html.Div([
                html.Div("Number of Wells", style={'fontSize': 13, 'color': '#607d8b'}),
                html.Div(f"{num_wells}", style={'fontWeight': 'bold', 'fontSize': 20, 'color': '#1976d2'})
            ], style={'display': 'inline-block', 'marginRight': '32px', 'padding': '8px 18px', 'background': '#f5faff', 'borderRadius': '8px', 'boxShadow': '0 1px 4px rgba(33,150,243,0.07)'}),
            html.Div([
                html.Div("Total Current Month BOE", style={'fontSize': 13, 'color': '#607d8b'}),
                html.Div(f"{total_boe:,.0f}", style={'fontWeight': 'bold', 'fontSize': 20, 'color': '#1976d2'})
            ], style={'display': 'inline-block', 'padding': '8px 18px', 'background': '#f5faff', 'borderRadius': '8px', 'boxShadow': '0 1px 4px rgba(33,150,243,0.07)'})
        ], style={'margin': '12px 0 8px 0'})
    ])
    # Table data
    table_data = filtered[header_cols].to_dict('records')
    # Production history for selected well
    well_prod = df[df[well_id_col] == center[well_id_col]].sort_values(date_col)
    fig_prod = px.line(
        well_prod,
        x=date_col,
        y=prod_col,
        title=f'Production History for {center["WellName"]}',
        markers=True,
        line_shape='spline'
    )
    fig_prod.update_traces(
        line=dict(color='#1976d2', width=3),
        marker=dict(size=6, color='#1976d2'),
        fill='tozeroy',
        fillcolor='rgba(33, 150, 243, 0.18)'
    )
    fig_prod.update_layout(
        xaxis_title='Month',
        yaxis_title='BOE',
        font=dict(family='Roboto, Open Sans, Arial, sans-serif', size=15),
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='white',
        margin=dict(l=30, r=30, t=50, b=30),
        title=dict(font=dict(size=20, color='#1565c0', family='Roboto, Open Sans, Arial, sans-serif')),
        hovermode='x unified',
    )
    return fig, info, table_data, fig_prod

if __name__ == '__main__':
    app.run(debug=True) 