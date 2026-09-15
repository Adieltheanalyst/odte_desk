# Curated store — schema

Design decisions for `data/curated/`. Written before the loader, deliberately.

Two timestamps appear on every table and mean different things:

- **`as_of_ts`** — the moment the fact became true in the market.
- **`ingested_ts`** — the moment I pulled it.

`as_of_ts` is what `get_features(date, cutoff)` filters on. `ingested_ts` exists so that
two snapshots of the same fact can be told apart when a source revises history.

All timestamps are UTC. All dates are naive calendar dates.

---

## Table: `daily_bars`

| column | type | notes |
|---|---|---|
| `date` | date32 | partition key, US trading session date |
| `symbol` | string | `"SPY"`. Kept so QQQ can be added without a migration. |
| `open` | float64 | raw, unadjusted |
| `high` | float64 | raw, unadjusted |
| `low` | float64 | raw, unadjusted |
| `close` | float64 | raw, unadjusted |
| `volume` | int64 | shares |
| `as_of_ts` | timestamp[us, UTC] | session close: 20:00 UTC (EDT) / 21:00 UTC (EST) |
| `ingested_ts` | timestamp[us, UTC] | when the download ran |

**One row =** one symbol on one trading session.
**Unique on:** (`symbol`, `date`)
**Partition:** `date`

**No `adj_close` column.** yfinance recomputes it on every download, so it is not
point-in-time and storing it would violate the append-only rule. Adjusted prices are derived
on demand from `daily_bars` + `corporate_actions`.

**Why `as_of_ts` is the session close, not midnight.** A bar is only fully true once the
session ends — its `close` is unknowable before 16:00 ET. If `as_of_ts` were midnight of
`date`, a pre-market query with an 08:00 ET cutoff would return today's bar, including today's
close, and the leak test in 1.7 would pass while leaking the future. This column choice is
what makes the loader correct.

The offset changes with US daylight saving: 20:00 UTC Mar–Nov, 21:00 UTC Nov–Mar. Compute it
with `zoneinfo` from `America/New_York`, never hardcode it.

---

## Table: `corporate_actions`

| column | type | notes |
|---|---|---|
| `symbol` | string | |
| `ex_date` | date32 | the date the event took effect |
| `action_type` | string | `"dividend"` or `"split"` |
| `amount` | float64 | dollars for a dividend, ratio for a split |
| `ingested_ts` | timestamp[us, UTC] | |

**One row =** one corporate action for one symbol.
**Unique on:** (`symbol`, `ex_date`, `action_type`)
**Partition:** none. A few hundred rows total.

**No separate `as_of_ts`** — `ex_date` is it. The event became true that day and will never be
revised.

**How adjustment is derived.** For a dividend `D` with ex-date `E`, and `P` = the unadjusted
close on the session before `E`:

```
factor = (P - D) / P
```

To adjust a price on date `d`, multiply it by the factors of every action with `ex_date > d`.
A 2-for-1 split uses `factor = 1/2`. Chain: raw prices + event log → factors → adjusted
prices, all reproducible, none of it silently rewritten.

---

## Table: `option_chain_snapshot`

| column | type | notes |
|---|---|---|
| `date` | date32 | partition key, session date of the snapshot |
| `underlying` | string | `"SPY"` |
| `contract_symbol` | string | OCC symbol, e.g. `SPY260918C00750000` |
| `expiry` | date32 | |
| `strike` | float64 | |
| `option_type` | string | `"call"` or `"put"` |
| `dte` | int32 | calendar days to expiry at snapshot |
| `bid` | float64 | |
| `ask` | float64 | |
| `last_price` | float64 | |
| `volume` | int64 | contracts traded that session |
| `open_interest` | int64 | **GEX uses this, not volume** |
| `implied_volatility` | float64 | vendor IV, kept for comparison only |
| `in_the_money` | bool | |
| `spot` | float64 | underlying price at snapshot. Greeks are meaningless without it. |
| `last_trade_ts` | timestamp[us, UTC] | when this contract last actually traded |
| `as_of_ts` | timestamp[us, UTC] | when the snapshot was taken |
| `ingested_ts` | timestamp[us, UTC] | |

**One row =** one contract at one snapshot.
**Unique on:** (`underlying`, `expiry`, `strike`, `option_type`, `as_of_ts`)
**Partition:** `date`

**Three timestamps, not two.** `last_trade_ts` is the one hiding in the data and it matters:
an illiquid strike can carry a quote whose last actual trade was days ago. A contract with
`as_of_ts` today and `last_trade_ts` from last week is stale, and its `last_price` and
`implied_volatility` are fiction. The OI floor chosen in task 2.5 is the first filter for this;
`last_trade_ts` is the second.

**`as_of_ts` is approximate.** yfinance quotes are delayed roughly 15 minutes, so the true
market time is earlier than the wall clock at collection. The collector runs at a consistent
time daily so the error is at least consistent. Note it as a known limitation rather than
pretending to precision.

**`implied_volatility` is not trusted.** Kept so that IV computed locally in Phase 2 can be
compared against it. Where they disagree, mine wins.

---

## Conventions

1. Lowercase `snake_case` everywhere. yfinance's `Adj Close` and `openInterest` get renamed on
   the way into curated.
2. Raw prices only. Anything adjusted is computed, never stored.
3. Nothing reads these files except `get_features()`.
4. Adding a column is fine. Changing the meaning of an existing one is not — add a new one.