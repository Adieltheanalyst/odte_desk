from __future__ import annotations

from pathlib import Path 
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
from src.store.schema import TABLES

CURATED_DIR = Path("data")/ "curated"

def _validate(df: pd.DataFrame, schema: pa.Schema, table_name: str) -> pd.DataFrame:
    expected=set(schema.names)
    actual = set(df.columns)

    missing = expected- actual
    if missing:
        raise ValueError(f"{table_name}: missing columns {sorted(missing)}")

    extra = actual - expected
    if extra:
        raise ValueError(
            f"{table_name}: unexpected columns {sorted(extra)}. "
            "Add them to the schema deliberately, or drop them before writing."

        )
    if df.empty:
        raise ValueError(f"{table_name}: refusing to write an empty frame")

    return df[list(schema.names)]

def write_curated(df: pd.DataFrame, table_name: str) -> Path:
    if table_name not in TABLES:
        raise KeyError(f"unknown table {table_name!r}, known: {sorted(TABLES)}")

    schema, partition_col = TABLES[table_name]
    df = _validate(df, schema, table_name)

    table = pa.Table.from_pandas(df,preserve_index=False)
    table= table.cast(schema)

    base_dir= CURATED_DIR / table_name
    base_dir.mkdir(parents=True, exist_ok=True)

    if partition_col:
        partition = ds.partitioning(
            pa.schema([schema.field(partition_col)]),
            flavor="hive",
        )
    else:
        partitioning=None

    ds.write_dataset(
        table,
        base_dir=base_dir,
        format="parquet",
        partitioning=partitioning,
        existing_data_behavior="delete_matching",
        basename_template="part-{i}.parquet",
    )

    n_parts = df[partition_col].nunique() if partition_col else 1
    print(f"Wrote {len(df):,} rows to {base_dir} across {n_parts} partition(s)")
    return base_dir
