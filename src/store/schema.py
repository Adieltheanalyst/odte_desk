from __future__ import annotations
from datetime import datetime 
from zoneinfo import ZoneInfo
import pandas as pd
import pyarrow as pa

ET = ZoneInfo("America/New_York")
UTC_TS = pa.timestamp("us", tz="UTC")

DAILY_BARS = pa.schema([
    ("date", pa.date32()),
    ("year", pa.int32()),
    ("symbol", pa.string()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.int64()),
    ("as_of_ts", UTC_TS),
    ("ingested_ts", UTC_TS),
])

CORPORATE_ACTIONS = pa.schema([
    ("symbol", pa.string())
    ,("ex_date", pa.date32()),
    ("action_type", pa.string()),
    ("amount", pa.float64()),
    ("ingested_ts", UTC_TS)
])

OPTION_CHAIN_SNAPSHOT = pa.schema([
    ("date",               pa.date32()),
    ("underlying",         pa.string()),
    ("contract_symbol",    pa.string()),
    ("expiry",             pa.date32()),
    ("strike",             pa.float64()),
    ("option_type",        pa.string()),
    ("dte",                pa.int32()),
    ("bid",                pa.float64()),
    ("ask",                pa.float64()),
    ("last_price",         pa.float64()),
    ("volume",             pa.int64()),
    ("open_interest",      pa.int64()),
    ("implied_volatility", pa.float64()),
    ("in_the_money",       pa.bool_()),
    ("spot",               pa.float64()),
    ("last_trade_ts",      UTC_TS),
    ("as_of_ts",           UTC_TS),
    ("ingested_ts",        UTC_TS),
])

TABLES = {
    "daily_bars": (DAILY_BARS,"year"),
    "corporate_actions": (CORPORATE_ACTIONS, None),
    "option_chain_snapshot": (OPTION_CHAIN_SNAPSHOT,"date"),
}

def session_close_utc(day) -> pd.Timestamp:

    day = pd.Timestamp(day)
    naive = datetime(day.year, day.month, day.day, 16, 0)
    return pd.Timestamp(naive, tz=ET).tz_convert("UTC")
