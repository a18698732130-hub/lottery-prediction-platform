import os
import requests
import pandas as pd
from datetime import datetime
from core.lottery import GameType

DATA_DIR = "data"

class LotteryFetcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_data(self, game_type: GameType, limit: int = 100000) -> pd.DataFrame:
        if game_type == GameType.SSQ:
            url = f"https://datachart.500.com/ssq/history/newinc/history.php?limit={limit}&sort=0"
            return self._fetch_and_parse(url, game_type)
        elif game_type == GameType.DLT:
            url = f"https://datachart.500.com/dlt/history/newinc/history.php?limit={limit}&sort=0"
            return self._fetch_and_parse(url, game_type)
        else:
            raise ValueError(f"Unsupported game type: {game_type}")

    def _fetch_and_parse(self, url: str, game_type: GameType) -> pd.DataFrame:
        try:
            print(f"Fetching data from {url}...")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            dfs = pd.read_html(response.text)
            if not dfs:
                raise ValueError("No tables found in response")
            
            df = dfs[0]
            return self._clean_data(df, game_type)
            
        except Exception as e:
            print(f"Error fetching data for {game_type.value}: {e}")
            raise

    def _clean_data(self, df: pd.DataFrame, game_type: GameType) -> pd.DataFrame:
        if game_type == GameType.SSQ:
            # SSQ: Issue(0), Red1-6(1-6), Blue(7), Date(15)
            target_indices = [0, 1, 2, 3, 4, 5, 6, 7, 15]
            column_names = ['issue', 'red1', 'red2', 'red3', 'red4', 'red5', 'red6', 'blue', 'date']
        elif game_type == GameType.DLT:
            # DLT: Issue(0), Red1-5(1-5), Blue1-2(6-7), Date(14)
            target_indices = [0, 1, 2, 3, 4, 5, 6, 7, 14]
            column_names = ['issue', 'red1', 'red2', 'red3', 'red4', 'red5', 'blue1', 'blue2', 'date']
        
        # Check if indices are valid for this dataframe
        max_idx = df.shape[1] - 1
        if any(idx > max_idx for idx in target_indices):
             # Fallback if table structure changed or date column missing
             print(f"Warning: Table structure mismatch. Expected max index {max(target_indices)}, got {max_idx}. Skipping date.")
             if game_type == GameType.SSQ:
                 target_indices = [0, 1, 2, 3, 4, 5, 6, 7]
                 column_names = ['issue', 'red1', 'red2', 'red3', 'red4', 'red5', 'red6', 'blue']
             else:
                 target_indices = [0, 1, 2, 3, 4, 5, 6, 7]
                 column_names = ['issue', 'red1', 'red2', 'red3', 'red4', 'red5', 'blue1', 'blue2']
        
        df_subset = df.iloc[:, target_indices].copy()
        df_subset.columns = column_names
        
        # Clean Issue
        df_subset['issue'] = df_subset['issue'].astype(str)
        # Filter rows where issue is numeric
        df_subset = df_subset[df_subset['issue'].str.match(r'^\d+$')]
        
        # Sort
        df_subset = df_subset.sort_values('issue', ascending=True)
        return df_subset

class DataLoader:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.fetcher = LotteryFetcher()

    def get_data_path(self, game_type: GameType) -> str:
        return os.path.join(self.data_dir, f"{game_type.value}_history.csv")

    def load_data(self, game_type: GameType, force_update: bool = False) -> pd.DataFrame:
        path = self.get_data_path(game_type)
        
        should_update = force_update
        
        # Check if file exists and is stale (older than 12 hours)
        if os.path.exists(path) and not should_update:
            mtime = os.path.getmtime(path)
            # If older than 12 hours (43200 seconds)
            if (datetime.now().timestamp() - mtime) > 43200:
                 print(f"Data for {game_type.value} is stale (>12h). Auto-updating...")
                 should_update = True

        if not os.path.exists(path) or should_update:
            print(f"Data for {game_type.value} not found or update requested. Fetching...")
            try:
                df = self.fetcher.fetch_data(game_type)
                df.to_csv(path, index=False)
                return df
            except Exception as e:
                print(f"Failed to fetch data: {e}")
                if os.path.exists(path):
                    print("Falling back to existing local data.")
                    return pd.read_csv(path, dtype={'issue': str})
                else:
                    return pd.DataFrame()
        
        return pd.read_csv(path, dtype={'issue': str})
