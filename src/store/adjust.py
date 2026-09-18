from __future__ import annotations
import sys 
import numpy as np
import pandas as pd
from src.store.loader import get_features

FAR_FUTURE ="2099-01-01"

def adjustment_factors(bars: pd.DataFrame, actions: pd.DataFrame)-> pd.Series:

    bars = bars.sort_values("date").reset_index(drop=True)
    actions = actions.sort_values("ex_date").reset_index(drop=True)
    dates = bars["date"].to_numpy()
    closes=bars["close"].to_numpy()
    n=len(bars)


    slots=np.ones(n+1)
    for _, action in actions.iterrows():
        i= int(np.searchsorted(dates, action["ex_date"], side="left"))

        if i==0:
            continue

        prior_close=closes[i-1]
        if action["action_type"] == "dividend":
            factor=(prior_close- action["amount"]) / prior_close

        elif action["action_type"] == "split":
            factor=1.0/action["amount"]
        else:
            raise ValueError(f"unknown action_type {action['action_type']!r}")

        slots[i]*= factor

    factors = np.ones(n)
    running=1.0
    for j in range(n-1, -1,-1):
        factors[j] = running
        running *= slots[j]

    return pd.Series(factors, index=bars.index, name="adj_factor")

def adjust(bars: pd.DataFrame, actions: pd.DataFrame)-> pd.DataFrame:
    bars= bars.sort_values("date").reset_index(drop=True)
    factors=adjustment_factors(bars, actions)

    out = bars.copy()
    out["adj_factor"] = factors
    for col in ("open","high","low","close"):
        out[f"adj_{col}"]= out[col] * factors

    return out

def load_and_adjust(day=FAR_FUTURE, cutoff_time: str = "23:59") -> pd.DataFrame:

    bars= get_features(day, cutoff_time, table="daily_bars")
    actions= get_features(day, cutoff_time, table="corporate_actions")
    return adjust(bars, actions)

def main() -> int:
    df=load_and_adjust()

    first = df.iloc[0]
    last=df.iloc[-1]

    print(f"{len(df):,} sessions, {first['date']} to {last['date']}")
    print(f"\nfirst session  {first['date']}")
    print(f"  raw close      {first['close']:.2f}")
    print(f"  adj factor     {first['adj_factor']:.6f}")
    print(f"  adjusted close {first['adj_close']:.2f}")
    print("  yfinance said  181.67  <- should be close to the line above")
 
    print(f"\nlast session   {last['date']}")
    print(f"  raw close      {last['close']:.2f}")
    print(f"  adj factor     {last['adj_factor']:.6f}  <- 1.0, nothing after it")
    print(f"  adjusted close {last['adj_close']:.2f}")
 
    price_mult = last["close"] / first["close"]
    total_mult = last["adj_close"] / first["adj_close"]

    print(f"\nprice-only growth   {price_mult:.3f}x  ({price_mult - 1:.1%})")
    print(f"total-return growth {total_mult:.3f}x  ({total_mult - 1:.1%})")
    print(f"dividend uplift     {total_mult / price_mult - 1:.1%} over the period")

    years = (last["date"] - first["date"]).days / 365.25
    print(f"annualised dividend {(total_mult / price_mult) ** (1 / years) - 1:.2%}")
    return 0

if __name__=="__main__":
    sys.exit(main())