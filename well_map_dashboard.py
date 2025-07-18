# Install dash and plotly: pip install dash plotly
import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px

# 1. Read data
prod_df = pd.read_csv('data/Wells_Production_for modeling-882ff_2025-06-16.csv', parse_dates=['ProducingMonth'])
header_df = pd.read_csv('data/Header_Wells_info_by each API-14cc3_2025-06-16.csv')  # Assume header wells file name

# 2. Column names (modify if different)
well_id_col = 'API_UWI'      # Well ID column, must exist in both tables
lat_col = 'Latitude'         # Latitude column in header wells
lon_col = 'Longitude'        # Longitude column in header wells
prod_col = 'Prod_BOE'        # Production column
date_col = 'ProducingMonth'  # Date column

# 3. Merge data
# Merge production and header data on well ID, add latitude and longitude to each production record

df = pd.merge(prod_df, header_df[[well_id_col, lat_col, lon_col]], on=well_id_col, how='inner')

# 4. Keep only one point per well for the map
wells_map = df.drop_duplicates(well_id_col)

# 5. Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Wells Map with Production History"),
    dcc.Graph(
        id='well-map',
        figure=px.scatter_mapbox(
            wells_map,
            lat=lat_col,
            lon=lon_col,
            hover_name=well_id_col,
            zoom=5,
            height=600
        ).update_layout(mapbox_style="open-street-map")
    ),
    html.Hr(),
    html.H4("Production History"),
    dcc.Graph(id='prod-history')
])

@app.callback(
    Output('prod-history', 'figure'),
    Input('well-map', 'clickData')
)
def update_prod_history(clickData):
    if clickData is None:
        well_id = wells_map[well_id_col].iloc[0]
    else:
        well_id = clickData['points'][0]['hovertext']
    well_data = df[df[well_id_col] == well_id].sort_values(by=date_col)
    fig = px.line(
        well_data,
        x=date_col,
        y=prod_col,
        title=f'Production History of {well_id}',
        markers=True
    )
    return fig

if __name__ == '__main__':
    app.run(debug=True) 