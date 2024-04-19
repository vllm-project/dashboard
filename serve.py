from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

@app.route('/')
def display_excel():
    # Load the Excel file
    df = pd.read_excel('buildkite_benchmarks.xlsx')
    return render_template('display.html', tables=df.to_html(classes='data', header="true"))

if __name__ == '__main__':
    app.run(debug=True)
