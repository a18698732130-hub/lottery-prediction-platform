from core.data import DataLoader
from core.lottery import GameType

def main():
    dl = DataLoader()
    print("Fetching SSQ...")
    df_ssq = dl.load_data(GameType.SSQ)
    print(f"SSQ Data: {len(df_ssq)} records")
    print(df_ssq.head())

    print("\nFetching DLT...")
    df_dlt = dl.load_data(GameType.DLT)
    print(f"DLT Data: {len(df_dlt)} records")
    print(df_dlt.head())

if __name__ == "__main__":
    main()
