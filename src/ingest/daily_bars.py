import pandas as pd
import yfinance as yf
from pathlib import Path 

output_folder = Path(r"data\raw")
file_path=output_folder / "spy_year_data.parquet"

SPY_DATA= yf.download("SPY", start="2016-09-09",end="2026-09-09", interval="1d",auto_adjust=False)

if isinstance(SPY_DATA.columns, pd.MultiIndex):
    SPY_DATA.columns= SPY_DATA.columns.droplevel(1)
SPY_DATA.name="date"
SPY_DATA["ingested_ts"] = pd.Timestamp.now(tz="UTC")

SPY_DATA.to_parquet(file_path)

print(f"Csv successfully saved {len(SPY_DATA)}")
