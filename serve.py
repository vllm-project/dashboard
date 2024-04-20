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
metrics = [col for col in df.columns if df[col].dtype in ['float64', 'int64']]

timestamp = os.path.getmtime(file_path)
last_modified_time = datetime.fromtimestamp(timestamp).astimezone(local_tz)
readable_time = last_modified_time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + tz

# Create a column with the commit link as text (since Plotly hover can't render HTML)
df['commit_link'] = df['commit_url'].apply(lambda x: f"URL: {x}")

# Create a Dash application
app = dash.Dash(__name__)

def create_metric_figure(metric):
    # Create a subplot figure for each metric, as there is only one metric per plot here
    fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
    trace = px.line(
        df,
        x='build_datetime',
        y=metric,
        title=f'Trend of {metric}',
        text='commit_link'  # This is where the hover text comes from
    ).data[0]
    fig.add_trace(trace, row=1, col=1)
    
    fig.update_traces(
        mode='markers+lines',
        hovertemplate='%{y}<extra></extra>'  # Customize hover text
    )
    fig.update_layout(
        height=300,  # Fixed height as each metric is in a separate plot now
        title_text=f"Performance Metrics for {metric}",
        hovermode='closest'
    )
    return fig

# Dropdown to select the metric for plotting
app.layout = html.Div([
    html.H1('Performance Metrics Over Time'),
    dcc.Markdown("", id='url-click-output'),  # Use dcc.Markdown to handle HTML
    dcc.Dropdown(
        id='metric-select',
        options=[{'label': metric, 'value': metric} for metric in metrics],
        value=metrics,
        multi=True
    ),
    # Generate a plot for each metric, hidden by default
    html.Div([dcc.Graph(id=f'graph-{metric}', figure=create_metric_figure(metric), style={'display': 'none'})
              for metric in metrics]),
    dcc.Store(id='plot-visibility'),
    html.Div(f"Last Updated: {readable_time}", style={'position': 'fixed', 'bottom': '10px', 'right': '10px'}),
])

clientside_callback(
    """
    function(selectedMetrics, ...plotIds) {
            // Loop through all plot IDs and set visibility
            plotIds.forEach((plotId) => {
                const plotElement = document.getElementById(plotId);
                if (plotElement) {
                    plotElement.style.display = selectedMetrics.includes(plotId.replace('graph-', '')) ? 'block' : 'none';
                }
            });
            return null;
        }
    """,
    Output('plot-visibility', 'data'),
    Input('metric-select', 'value'),
    state=[Input(f'graph-{metric}', 'id') for metric in metrics]  # Passing plot IDs as state
)

for metric in metrics:
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
        Output('url-click-output', 'children', allow_duplicate=True),
        Input(f'graph-{metric}', 'clickData'),
        prevent_initial_call=True,
    )

if __name__ == '__main__':
    app.run_server(debug=True)
