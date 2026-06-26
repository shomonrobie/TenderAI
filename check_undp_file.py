# check_undp_csv.py - Check UNDP CSV structure

import pandas as pd

CSV_PATH = "data/demo/undp.csv"

def check_undp_csv():
    """Check UNDP CSV file structure"""
    try:
        df = pd.read_csv(CSV_PATH)
        
        print("📋 UNDP CSV FILE STRUCTURE")
        print("=" * 60)
        print(f"File: {CSV_PATH}")
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print("\nFirst 5 rows:")
        print(df.head())
        print("\nData types:")
        print(df.dtypes)
        
        return df
        
    except FileNotFoundError:
        print(f"❌ File not found: {CSV_PATH}")
        return None
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None


if __name__ == "__main__":
    check_undp_csv()