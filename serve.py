import os
import dash
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
from dash import html, dcc, Input, Output, dash_table, clientside_callback
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
    dcc.Markdown("", id='url-click-output'),  # Use dcc.Markdown to handle HTML
    dcc.Dropdown(
        id='metric-select',
        options=[{'label': col, 'value': col} for col in df.columns if df[col].dtype in ['float64', 'int64']],
        value=[col for col in df.columns if df[col].dtype in ['float64', 'int64']],  # Default to all numeric columns
        multi=True  # Allow multiple selections
    ),
    dcc.Graph(id='time-series-chart'),
    html.Div(f"Last Updated: {readable_time}", style={'position': 'fixed', 'bottom': '10px', 'right': '10px'}),
])

# Callback for updating the graph based on selected metrics
@app.callback(
    Output('time-series-chart', 'figure'),
    Input('metric-select', 'value')
)
def update_graph(selected_metrics):
    if not selected_metrics:
        return {}
    # Create a subplot figure with one row per selected metric
    fig = make_subplots(rows=len(selected_metrics), cols=1, shared_xaxes=True, vertical_spacing=0.02)
    
    for i, metric in enumerate(selected_metrics):
        trace = px.line(
            df,
            x='build_datetime',
            y=metric,
            title=f'Trend of {metric}',
            text='commit_link'  # This is where the hover text comes from
        ).data[0]
        fig.add_trace(
            trace,
            row=i+1,
            col=1
        )
    
    fig.update_traces(
        mode='markers+lines',
        hovertemplate='%{y}<extra></extra>'  # Customize hover text
    )
    
    fig.update_layout(
        height=300 * len(selected_metrics),  # Adjust height based on the number of metrics
        title_text="Performance Metrics Over Time",
        hovermode='closest'
    )
    return fig

clientside_callback(
    """
    function(clickData) {
        if (clickData) {
            var url = clickData.points[0].text.split("URL: ")[1];
            return `[Open Commit ${url}](${url})`;
        }
        return "Click on a point to see the URL.";
    }
    """,
    Output('url-click-output', 'children'),
    Input('time-series-chart', 'clickData'),
)

if __name__ == '__main__':
    app.run_server(debug=True)
