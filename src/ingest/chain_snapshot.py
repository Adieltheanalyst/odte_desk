from __future__ import annotations
import sys 
import time
from pathlib import Path 
import pandas as pd
import yfinance as yf 

TICKER = "SPY"
MAX_DTE = 60 
SLEEP_BETWEEN  =0.5
RAW_DIR = Path("data") / "raw" / "option_chain"

def get_spot(t: yf.Ticker) -> float:
    try: 
        return float(t.fast_info["last_price"])
    except Exception:
        hist = t.history(period="1d", interval="1m")
        if hist.empty:
            raise RuntimeError("could not determine spot price")
        return float(hist["Close"].iloc[-1])


def fetch_chain(ticker: str = TICKER, max_dte: int = MAX_DTE) -> pd.DataFrame:
    t= yf.Ticker(ticker)
    spot= get_spot(t)
    as_of = pd.Timestamp.now(tz="UTC")

    expires = t.options
    if not expires:
        raise RuntimeError("no expires returned -- yfinance may be rate limiting ")

    today = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    frames =[]
    for exp in expires:
        dte=(pd.Timestamp(exp) - today).days
        if dte >max_dte:
            continue

        try:
            chain= t.option_chain(exp)
        except Exception as exc:
            print(f" Skipped {exp}: {exc}")
            continue

        for side, df in (("call", chain.calls), ("put", chain.puts)):
            df=df.copy()
            df["option_type"]= side
            df["expiry"] = pd.Timestamp(exp)
            df["dte"]= dte
            frames.append(df)

        time.sleep(SLEEP_BETWEEN)

    if not frames:
        raise RuntimeError("no chain data collected")

    out= pd.concat(frames, ignore_index=True)
    out["underlying"] = ticker 
    out["spot"]= spot
    out["as_of_ts"]= as_of
    out["ingested_ts"] = pd.Timestamp.now(tz="UTC")
    return out 

def write_snapshot(df: pd.DataFrame) -> Path:
    """Ensures it is one file per run and never overwrite"""
    as_of = df["as_of_ts"].iloc[0]
    day = as_of.strftime("%Y-%m-%d")
    stamp = as_of.strftime("%h%M%S")

    folder = RAW_DIR / f"date={day}"
    folder.mkidr(parents=True, exist_ok=True)

    path = folder / f"{TICKER}_{stamp}.parquet"
    df.to_parquet(path, index=False)
    return path

def main() -> int:
    now = pd.Timestamp.now(tz="UTC")

    if now.weekday() >= 5:
        print(f"{now.date()} is a weekend, nothing to collect ")
        return 0

    try:
        df = fetch_chain()
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    path = write_snapshot(df)
    print(
        f"{now.isoformat()} | {len(df):,} contracts | "
        f"spot {df['spot'].iloc[0]:.2f} | "
        f"{df["expiry"].nunique()} expires | -> {path}"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
    