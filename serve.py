import os
import dash
import pandas as pd
import plotly.express as px
from dash import html, dcc, Input, Output, dash_table
from datetime import datetime
from zoneinfo import ZoneInfo  # This is for Python 3.9 and later

tz = 'America/Los_Angeles'
local_tz = ZoneInfo(tz)  # Change this to your timezone, e.g., 'Europe/London', 'Asia/Tokyo'

# Load your Excel file
file_path = "buildkite_benchmarks.xlsx"
df = pd.read_excel(file_path)

timestamp = os.path.getmtime(file_path)
last_modified_time = datetime.fromtimestamp(timestamp).astimezone(local_tz)
readable_time = last_modified_time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + tz

# Create a column with the commit link as text (since Plotly hover can't render HTML)
df['commit_link'] = df['commit_url'].apply(lambda x: f"URL: {x}")

# Create a Dash application
app = dash.Dash(__name__)

# Dropdown to select the metric for plotting
app.layout = html.Div([
    html.H1('Performance Metrics Over Time'),
    dcc.Dropdown(
        id='metric-select',
        options=[{'label': col, 'value': col} for col in df.columns if df[col].dtype in ['float64', 'int64']],
        value='Average Latency'  # Default value
    ),
    dcc.Graph(id='time-series-chart'),
    html.Div(id='url-click-output'),  # To handle click outputs
    html.Div(f"Last Updated: {readable_time}", style={'position': 'fixed', 'bottom': '10px', 'right': '10px'}),
])

# Callback for updating the graph based on selected metric
@app.callback(
    Output('time-series-chart', 'figure'),
    Input('metric-select', 'value')
)
def update_graph(selected_metric):
    fig = px.line(
        df,
        x='build_datetime',
        y=selected_metric,
        title=f'Trend of {selected_metric}',
        text='commit_link'  # This is where the hover text comes from
    )
    fig.update_traces(
        mode='markers+lines',
        hovertemplate='%{y}<extra></extra>'  # Customize hover text
    )
    return fig

# Optional: Callback to handle clicks and potentially open URLs
@app.callback(
    Output('url-click-output', 'children'),
    [Input('time-series-chart', 'clickData')],
    prevent_initial_call=True
)
def on_point_click(clickData):
    if clickData:
        url = clickData['points'][0]['text'].split("URL: ")[1]
        # Display the URL; in a real app, you might try to open this URL with JavaScript
        return html.A(f"Open Commit {url}", href=url, target="_blank")
    return "Click on a point to see the URL."

if __name__ == '__main__':
    app.run_server(debug=True)
