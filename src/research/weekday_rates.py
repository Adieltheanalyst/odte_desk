from __future__ import annotations
import sys
from pathlib import Path
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd

from src.store.loader import get_features

OUT_DIR=Path("outputs") / "weekday_rates"
CLAIMED_RATE = 0.94
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday","Friday"]

def load_bars() -> pd.DataFrame:

    df = get_features("2099-01-01", "23:59")
    if df.empty:
        raise RuntimeError("curated store is empty -- run build_daily_bars first")

    df = df.sort_values("date").reset_index(drop=True)
    df["weekday"]=pd.to_datetime(df["date"]).dt.day_name()
    df["green_intraday"]=df["close"]>df["open"]
    df["green_overnight"]=df["close"]>df["close"].shift(1)
    return df

def rate_table(df: pd.DataFrame, col: str)-> pd.DataFrame:

    sub=df.dropna(subset=[col])
    g = sub.groupby("weekday")[col]

    out = pd.DataFrame({
        "n": g.size(),
        "green":g.sum().astype(int),
        "rate": g.mean(),
    })
    out["se"]=np.sqrt(out["rate"]* (1-out["rate"])/ out["n"])
    out["ci_low"]= out["rate"]- 1.96 *out["se"]
    out["ci_high"] = out["rate"] + 1.96 * out["se"]
    return out.reindex([d for d in WEEKDAY_ORDER if d in out.index])

def by_year(df: pd.DataFrame, col:str)-> pd.DataFrame:

    sub=df.dropna(subset=[col]).copy()
    sub["year"]= pd.to_datetime(sub["date"]).dt.year
    pivot=sub.pivot_table(
        index="year", columns="weekday", values = col, aggfunc="mean"
    )
    return pivot.reindex(columns=[d for d in WEEKDAY_ORDER if d in pivot.columns])

def plot_rates(table: pd.DataFrame, label:str, path: Path)-> None:
    fig, ax =plt.subplots(figsize=(10,6))

    x= np.arange(len(table))
    ax.bar(x, table["rate"], color="#4a7ba7", width=0.6)
    ax.errorbar(
        x,table["rate"],
        yerr=1.96 * table["se"],
        fmt="none", ecolor="black", capsize=4, linewidth=1,
    )
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=1)
    ax.text(len(table)-0.4, 0.505, "coin flip",fontsize=9, color="grey")

    ax.axhline(CLAIMED_RATE, color="#c0392b", linestyle="-", linewidth=1.5)
    ax.text(
        -0.45, CLAIMED_RATE + 0.012,
        f"claimed Friday rate: {CLAIMED_RATE:.0%}",
        fontsize=10, color="#c0392b",
    )
 
    for i, (rate, n) in enumerate(zip(table["rate"], table["n"])):
        ax.text(i, rate + 0.015, f"{rate:.1%}\nn={n}",
                ha="center", fontsize=9)
 
    ax.set_xticks(x)
    ax.set_xticklabels(table.index)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("green-day rate")
    ax.set_title(f"SPY green-day rate by weekday ({label})\n"
                 f"bars show 95% confidence interval")
 
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
 
 
def plot_by_year(pivot: pd.DataFrame, label: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    for day in pivot.columns:
        ax.plot(pivot.index, pivot[day], marker="o", label=day, linewidth=1.2)
 
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=1)
    ax.set_ylim(0.2, 0.8)
    ax.set_ylabel("green-day rate")
    ax.set_xlabel("year")
    ax.set_title(f"SPY green-day rate by weekday, per year ({label})")
    ax.legend(ncol=5, fontsize=9)
 
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
 
 
def report(table: pd.DataFrame, label: str) -> None:
    print(f"\n{label}")
    print("-" * 62)
    print(f"{'weekday':<11}{'n':>6}{'rate':>9}{'se':>8}{'95% CI':>20}")
    for day, row in table.iterrows():
        ci = f"[{row['ci_low']:.1%}, {row['ci_high']:.1%}]"
        print(f"{day:<11}{int(row['n']):>6}{row['rate']:>9.1%}"
              f"{row['se']:>8.3f}{ci:>20}")
 
    best = table["rate"].idxmax()
    spread = table["rate"].max() - table["rate"].min()
    pooled_se = table["se"].mean()
    print(f"\nhighest: {best} at {table.loc[best, 'rate']:.1%}")
    print(f"spread across weekdays: {spread:.1%} "
          f"({spread / pooled_se:.1f} standard errors)")
    print(f"claimed Friday rate: {CLAIMED_RATE:.0%} -- "
          f"actual: {table.loc['Friday', 'rate']:.1%} "
          f"(off by {CLAIMED_RATE - table.loc['Friday', 'rate']:.1%})")
 
 
def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_bars()
 
    print(f"{len(df):,} sessions, "
          f"{df['date'].min()} to {df['date'].max()}")
 
    for col, label in (("green_intraday", "close > open"),
                       ("green_overnight", "close > previous close")):
        table = rate_table(df, col)
        report(table, label)
 
        slug = col.replace("green_", "")
        table.to_csv(OUT_DIR / f"weekday_{slug}.csv")
        plot_rates(table, label, OUT_DIR / f"weekday_{slug}.png")
 
        pivot = by_year(df, col)
        pivot.to_csv(OUT_DIR / f"weekday_{slug}_by_year.csv")
        plot_by_year(pivot, label, OUT_DIR / f"weekday_{slug}_by_year.png")
 
        fri = pivot["Friday"].dropna()
        print(f"Friday by year: min {fri.min():.1%}, max {fri.max():.1%}, "
              f"years above 60%: {(fri > 0.6).sum()} of {len(fri)}")
 
    print(f"\nwrote charts and tables to {OUT_DIR}")
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())
 