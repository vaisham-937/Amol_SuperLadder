import pandas as pd
import io
import requests

def check_csv():
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    print(f"Fetching {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # Using requests to get content first
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        
        df = pd.read_csv(io.StringIO(r.text), nrows=5)
        print("Columns:", df.columns.tolist())
        print("First row:", df.iloc[0].to_dict())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_csv()
