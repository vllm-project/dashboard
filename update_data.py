import os
import requests
from datetime import datetime, timedelta

import subprocess

def run_curl_command(token, url):
    command = [
        "curl",
        "-H", f"Authorization: Bearer {token}",
        "-X", "GET",
        url
    ]

    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return result.stdout  # Returns the content of the log file
    except subprocess.CalledProcessError as e:
        raise Exception(f"Command failed with return code {e.returncode}: {e.output}")


def get_builds(org_slug, branch, token, days=30):
    url = f"https://api.buildkite.com/v2/organizations/{org_slug}/builds"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Calculate the date 30 days ago from today
    date_from = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
    
    params = {
        "branch": branch,
        "created_from": date_from,
        "per_page": "100",
    }

    all_builds = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            all_builds.extend(response.json())
            # Parse the Link header and look for a 'next' relation
            link_header = response.headers.get('Link', None)
            url = None
            if link_header:
                links = link_header.split(',')
                next_link = [link for link in links if 'rel="next"' in link]
                if next_link:
                    next_url = next_link[0].split(';')[0].strip('<>')
                    url = next_url
                    params = {}  # Clear params because next URL will have necessary params
        else:
            raise Exception(f"Failed to get builds: {response.status_code} - {response.text}")

    return all_builds

import re

# Define a list of dictionaries for patterns
log_patterns = [
    {'key': 'Average Latency', 'pattern': re.compile(r"Avg latency: ([\d.]+) seconds")},
    {'key': '10% Percentile Latency', 'pattern': re.compile(r"10% percentile latency: ([\d.]+) seconds")},
    {'key': '25% Percentile Latency', 'pattern': re.compile(r"25% percentile latency: ([\d.]+) seconds")},
    {'key': '50% Percentile Latency', 'pattern': re.compile(r"50% percentile latency: ([\d.]+) seconds")},
    {'key': '75% Percentile Latency', 'pattern': re.compile(r"75% percentile latency: ([\d.]+) seconds")},
    {'key': '90% Percentile Latency', 'pattern': re.compile(r"90% percentile latency: ([\d.]+) seconds")},
    {'key': 'Throughput', 'pattern': re.compile(r"Throughput: ([\d.]+) requests/s")},
    {'key': 'Token Throughput', 'pattern': re.compile(r"Throughput: [\d.]+ requests/s, ([\d.]+) tokens/s")},
    {'key': 'Successful Requests', 'pattern': re.compile(r"Successful requests: +(\d+)")},
    {'key': 'Benchmark Duration', 'pattern': re.compile(r"Benchmark duration \(s\): +([\d.]+)")},
    {'key': 'Total Input Tokens', 'pattern': re.compile(r"Total input tokens: +(\d+)")},
    {'key': 'Total Generated Tokens', 'pattern': re.compile(r"Total generated tokens: +(\d+)")},
    {'key': 'Request Throughput', 'pattern': re.compile(r"Request throughput \(req/s\): +([\d.]+)")},
    {'key': 'Input Token Throughput', 'pattern': re.compile(r"Input token throughput \(tok/s\): +([\d.]+)")},
    {'key': 'Output Token Throughput', 'pattern': re.compile(r"Output token throughput \(tok/s\): +([\d.]+)")},
    {'key': 'Mean TTFT', 'pattern': re.compile(r"Mean TTFT \(ms\): +([\d.]+)")},
    {'key': 'Median TTFT', 'pattern': re.compile(r"Median TTFT \(ms\): +([\d.]+)")},
    {'key': 'P99 TTFT', 'pattern': re.compile(r"P99 TTFT \(ms\): +([\d.]+)")},
    {'key': 'Mean TPOT', 'pattern': re.compile(r"Mean TPOT \(ms\): +([\d.]+)")},
    {'key': 'Median TPOT', 'pattern': re.compile(r"Median TPOT \(ms\): +([\d.]+)")},
    {'key': 'P99 TPOT', 'pattern': re.compile(r"P99 TPOT \(ms\): +([\d.]+)")}
]

# Function to process log entries using defined patterns
def extract_data_from_logs(logs, patterns=log_patterns):
    results = {}
    for line in logs.split('\n'):
        for pattern_dict in patterns:
            match = pattern_dict['pattern'].search(line)
            if match:
                results[pattern_dict['key']] = match.group(1)
    return results

# Replace 'your_token_here' with your actual Buildkite API token
API_TOKEN = os.environ.get("BUILDKIT_API_TOKEN")  # or 'your_token_here'
ORG_SLUG = "vllm"  # Replace 'vllm' with the actual slug of your organization if different
BRANCH = "main"
cache_dir = ".cache"
os.makedirs(cache_dir, exist_ok=True)

columns = [
    'commit',
    'commit_url',
    'build_datetime',
    'Average Latency',
    '10% Percentile Latency',
    '25% Percentile Latency',
    '50% Percentile Latency',
    '75% Percentile Latency',
    '90% Percentile Latency',
    'Throughput',
    'Token Throughput',
    'Successful Requests',
    'Benchmark Duration',
    'Total Input Tokens',
    'Total Generated Tokens',
    'Request Throughput',
    'Input Token Throughput',
    'Output Token Throughput',
    'Mean TTFT',
    'Median TTFT',
    'P99 TTFT',
    'Mean TPOT',
    'Median TPOT',
    'P99 TPOT'
]
values = []

builds = get_builds(ORG_SLUG, BRANCH, API_TOKEN)
for build in builds:
    commit = build['commit']
    commit_url = f"{build['pipeline']['repository'].replace('.git', '')}/commit/{build['commit']}"
    raw_log_url = None
    for job in build.get('jobs', []):
        if 'name' in job and job['name'] == "Benchmarks":
            raw_log_url = job['raw_log_url']
            break
    if raw_log_url is None:
        continue
    build_datetime = build['created_at']
    filename = f"{build_datetime}_{commit}.log"
    filepath = os.path.join(cache_dir, filename)
    if os.path.exists(filepath):
        print(f"Skipping downloading {filepath} for commit {commit} because it already exists")
    else:
        data = run_curl_command(API_TOKEN, raw_log_url)
        if len(data) <= 100:
            print(f"Skipping processing {filepath} for commit {commit} because the log is empty")
            continue
        with open(filepath, "w") as f:
            f.write(data)
        print(f"Saved {filepath} for commit {commit}")
    with open(filepath, "r") as f:
        logs = f.read()
        results = extract_data_from_logs(logs)
        values.append([commit, commit_url, build_datetime] + [results.get(col, "") for col in columns[3:]])

import pandas as pd
df = pd.DataFrame(values, columns=columns)
df.to_excel("buildkite_benchmarks.xlsx", index=False)