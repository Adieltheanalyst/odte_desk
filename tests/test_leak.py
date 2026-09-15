from __future__ import annotations
import pandas as pd
import pytest 
from src.store.loader import cutoff_utc, get_features


@pytest.fixture(scope="module")
def all_bars() -> pd.DataFrame:

    df= get_features("2099-01-01", "23:59")
    assert not df.empty, "curated store is empty -- run build_daily_bars first"
    return df

@pytest.fixture(scope="module")
def sample_days(all_bars) -> list:

    dates= sorted(all_bars["date"].unique())
    mid= len(dates) // 2
    return [dates[100], dates[mid], dates[-30]]

def test_premarket_excludes_same_session(sample_days):

    for day in sample_days:
        df= get_features(day,"08:00")
        assert day not in set(df["date"]), (
            f"LEAK: {day}'s bar returned to an 08:00 query"
        )

def test_postclose_includes_same_session(sample_days):
    for day in sample_days:
        df =get_features(day,"16:30")
        assert day in set(df["date"]), (
            f"{day}'s bar missing from a 16:30 query"
        )


def test_no_row_exceeds_cutoff(sample_days):

    for day in sample_days:
        for t in ("04:00", "08:00", "09:30","16:30","23:00"):
            df = get_features(day,t)
            if df.empty:
                continue

            cutoff= cutoff_utc(day, t)
            assert df["as_of_ts"].max() <= cutoff,(
                f"LEAK: row after cutoff for {day} {t}"
            )

def test_history_is_returned_not_just_one_day(sample_days):
    day=sample_days[1]
    df = get_features(day, "08:00")
    assert  len(df) >100, "loader should return history, not one row"
    assert df["date"].max()<day

def test_dst_boundary_cutoffs(all_bars):

    summer=cutoff_utc("2024-07-15", "16:00")
    winter = cutoff_utc("2024-12-16", "16:00")
    assert summer.hour == 20
    assert winter.hour == 21

def test_empty_before_history_starts():
    df = get_features("1990-01-02", "08:00")
    assert df.empty


def test_results_are_sorted(sample_days):
    df = get_features(sample_days[1], "08:00")
    assert df["as_of_ts"].is_monotonic_increasing
    
def test_unknown_table_raises():
    with pytest.raises(KeyError):
        get_features("2024-06-03", "08:00", table="not_a_table")
