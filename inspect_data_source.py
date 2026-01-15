import requests
import pandas as pd
from io import StringIO

def inspect_columns(url, name):
    print(f"--- Inspecting {name} ---")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        dfs = pd.read_html(response.text)
        if dfs:
            df = dfs[0]
            print(f"Total Columns: {len(df.columns)}")
            print("First 5 rows (raw):")
            print(df.head(2))
            # Print last few columns to find date
            print("Last 5 columns:")
            print(df.iloc[:2, -5:])
        else:
            print("No tables found.")
    except Exception as e:
        print(f"Error: {e}")

# SSQ
inspect_columns("https://datachart.500.com/ssq/history/newinc/history.php?limit=5&sort=0", "SSQ")
# DLT
inspect_columns("https://datachart.500.com/dlt/history/newinc/history.php?limit=5&sort=0", "DLT")
