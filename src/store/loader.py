from __future__ import annotations
from datetime import datetime, time 
from pathlib import Path 
import pandas as pd
import pyarrow as pa 
import pyarrow.dataset as ds

from src.store.schema import ET, TABLES

CURATED_DIR =Path("data") / "curated"

def _as_time(value: str | time )-> time:

    if isinstance(value,time):
        return value
    hh,_, mm = value.partition(":")
    return time(int(hh), int(mm or 0))

def cutoff_utc(day, cutoff_time: str | time) -> pd.Timestamp:

    day = pd.Timestamp(day).date()
    t=_as_time(cutoff_time)
    naive= datetime(day.year, day.month, day.day, t.hour, t.minute)
    return pd.Timestamp(naive, tz=ET).tz_convert("UTC")

def get_features(day,
                 cutoff_time:str | time = "08:00",
                 table:str = "daily_bars",
                 )-> pd.DataFrame:
    if table not in TABLES:
        raise KeyError(f"unknown table {table!r}, known: {sorted(TABLES)}")

    schema, partition_col = TABLES[table]
    base_dir= CURATED_DIR / table

    if not base_dir.exists():
        raise FileNotFoundError(F"{base_dir} does not exist -- build it first")

    cutoff = cutoff_utc(day, cutoff_time)

    if partition_col:
        partitioning= ds.partitioning(
            pa.schema([schema.field(partition_col)]),
            flavor="hive",
        )

    else: 
        partitioning = None 

    dataset = ds.dataset(base_dir, format="parquet", partitioning= partitioning)

    expr = None 

    if partition_col == "year":
        expr=ds.field("year") <= pd.Timestamp(day).year
    elif partition_col == "date":
        expr = ds.field("date") <= pd.Timestamp(day).date()
    df=dataset.to_table(filter=expr).to_pandas()

    if df.empty:
        return df

    df= df[df["as_of_ts"] <= cutoff]

    return df.sort_values("as_of_ts").reset_index(drop=True)


def latest(day, cutoff_time:str | time="08:00", table: str ="daily_bars"):
    df =get_features(day, cutoff_time,table)
    if df.empty:
        return None
    return df.iloc[-1]
