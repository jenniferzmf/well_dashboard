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

app.layout = html.Div([
    html.Div([
        html.Div([
            html.H4("Select Radius (miles)"),
            dcc.Dropdown(
                id='radius-dropdown',
                options=[{'label': f'{r} mile', 'value': r} for r in [1, 2, 5, 10]],
                value=2,
                clearable=False,
                style={'width': '150px'}
            ),
            html.Br(),
            html.Div(id='selected-well-info', style={'fontSize': 14, 'marginBottom': '10px'}),
            html.H4("Wells within Radius"),
            dash_table.DataTable(
                id='wells-table',
                columns=[
                    {'name': 'API_UWI', 'id': 'API_UWI'},
                    {'name': 'WellName', 'id': 'WellName'},
                    {'name': 'ENVOperator', 'id': 'ENVOperator'},
                    {'name': 'ENVWellType', 'id': 'ENVWellType'},
                    {'name': 'County', 'id': 'County'},
                    {'name': 'Latitude', 'id': 'Latitude'},
                    {'name': 'Longitude', 'id': 'Longitude'}
                ],
                page_size=8,
                style_table={'overflowX': 'auto'},
                style_cell={'fontSize': 12, 'padding': '5px'},
            )
        ], style={'width': '35%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'height': '600px', 'overflowY': 'auto'}),
        html.Div([
            dcc.Graph(id='well-map', config={'scrollZoom': True})
        ], style={'width': '64%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    ], style={'width': '100%', 'display': 'flex', 'flexDirection': 'row'}),
    html.Div([
        html.Div([
            html.H4("Production History (BOE)"),
            dcc.Graph(id='prod-history')
        ], style={'width': '100%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    ], style={'width': '100%', 'padding': '10px'})
], style={'padding': '10px'})

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
        center = wells_map[wells_map[well_id_col] == point['hovertext']].iloc[0]
    # Calculate distances
    dists = haversine(center[lat_col], center[lon_col], wells_map[lat_col], wells_map[lon_col])
    wells_map['distance'] = dists
    filtered = wells_map[dists <= radius]
    filtered_ids = filtered[well_id_col].tolist()
    # Map coloring
    color_arr = np.where(wells_map[well_id_col] == center[well_id_col], 'Selected',
                        np.where(wells_map[well_id_col].isin(filtered_ids), 'In Radius', 'Other'))
    fig = px.scatter_mapbox(
        wells_map,
        lat=lat_col,
        lon=lon_col,
        hover_name=well_id_col,
        color=color_arr,
        zoom=8,
        height=500
    )
    fig.update_layout(mapbox_style="open-street-map", showlegend=False)  # Remove color legend
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
    # Selected well info
    info = html.Div([
        html.P(f"Well ID: {center[well_id_col]}", style={'margin': '0'}),
        html.P(f"Operator: {center['ENVOperator']}", style={'margin': '0'}),
        html.P(f"Type: {center['ENVWellType']}", style={'margin': '0'}),
        html.P(f"Name: {center['WellName']}", style={'margin': '0'}),
        html.P(f"County: {center['County']}", style={'margin': '0'}),
        html.P(f"Latitude: {center[lat_col]:.5f}, Longitude: {center[lon_col]:.5f}", style={'margin': '0'})
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
        markers=True
    )
    fig_prod.update_layout(xaxis_title='Month', yaxis_title='BOE')
    return fig, info, table_data, fig_prod

if __name__ == '__main__':
    app.run(debug=True) 