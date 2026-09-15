from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import yfinance as yf

from src.store.schema import session_close_utc
from src.store.writer import write_curated

RAW_BARS = Path("data") / "raw" / "spy_year_data.parquet"
SYMBOL = "SPY"

RENAME = {
    "Open": "open"
    ,"High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}

def build_daily_bars(symbol: str = SYMBOL)-> pd.DataFrame:
    raw=pd.read_parquet(RAW_BARS)
    df = raw.rename(columns=RENAME).reset_index()
    df.columns=[c.lower() for c in df.columns]

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["year"] = pd.to_datetime(df["date"]).dt.year.astype("int32")
    df["symbol"]= symbol
    df["volume"]=df["volume"].astype("int64")

    df["as_of_ts"] = df["date"].map(session_close_utc)

    if "ingested_ts" not in df.columns:
        df["ingested_ts"]=pd.Timestamp.now(tz="UTC")
    df["ingested_ts"]= pd.to_datetime(df["ingested_ts"],utc=True)

    keep= ["date","year", "symbol", "open", "high", "low", "close",
           "volume", "as_of_ts", "ingested_ts"]

    df=df[keep]

    dupes=df.duplicated(subset=["symbol","date"]).sum()
    if dupes:
        raise ValueError(f"{dupes} duplicate(symbol, date) rows in raw bars")

    return df 

def build_corporate_actions(symbol: str = SYMBOL)-> pd.DataFrame:

    t=yf.Ticker(symbol)
    now=pd.Timestamp.now(tz="UTC")
    frames=[]
    divs = t.dividends
    if not divs.empty:
        frames.append(pd.DataFrame({
            "ex_date": divs.index.date,
            "action_type": "dividend",
            "amount": divs.values.astype("float64"),
        }))

    splits=t.splits
    if not splits.empty:
        frames.append(pd.DataFrame({
            "ex_date": splits.date,
            "action_type": "split",
            "amount": splits.values.astype("float64")
        }))

    if not frames:
        raise RuntimeError(f"no corporate actions returned for {symbol}")

    df = pd.concat(frames, ignore_index=True)
    df["symbol"]=symbol
    df["ingested_ts"]= now
    return df[["symbol", "ex_date", "action_type","amount", "ingested_ts"]]

def main() -> int:
    bars=build_daily_bars()
    write_curated(bars,"daily_bars")
    print(f"{bars['date'].min()} -> {bars['date'].max()}")
    actions=build_corporate_actions()
    write_curated(actions, "corporate_actions")
    print(f" {len(actions)} actions, latest {actions["ex_date"].max()}")

    return 0

if __name__=="__main__":
    sys.exit(main())