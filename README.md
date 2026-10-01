# defi-observatory

Small, documented methods for reading public DeFi data, plus the daily numbers they produce.

The code answers four plain questions about a protocol:

1. **Is it moving differently from its peers?** – `peers`
2. **Can the number be trusted?** – `data_check`
3. **Did value locked grow because of prices or because of deposits?** – `decomposition`
4. **Where does it stand in its own sector, on five measures at once?** – `health_index`

Everything here describes what the data already shows. Nothing in this repository is a forecast, a signal or
investment advice.

## Install and test

```bash
python -m venv .venv && . .venv/bin/activate
pip install --upgrade pip
pip install -e ".[test]"
pytest
python examples/quick_tour.py
```

No dependencies besides the Python standard library (3.9+). The tests run on small made-up data and on four real
cases saved in `tests/fixtures/`.

## What each part measures, and how to read it

### 1. Peer comparison (`defi_observatory.peers`)

A protocol's 30-day change is compared with the **median** change of its peer group (decentralised exchanges with
decentralised exchanges, lending with lending, and so on, one protocol per family).

- For **sums** (fees, revenue, trading volume) the change is the total of the last 30 days against the 30 days before.
- For **levels** (value locked, stablecoin supply, a market share) the change is today's value against the *median of
  the five days around 30 days earlier*. One odd day at the starting point cannot inflate the result.
- No comparison is made in groups of fewer than five members.

```python
from defi_observatory import peers

changes = {"a": 0.10, "b": 0.20, "c": 0.30, "d": 0.40, "e": 2.00}   # 30-day changes of five peers
peers.compare_with_peers(changes)["e"]
# {'change': 2.0, 'peer_median': 0.3, 'peers': 5, 'gap_points': 170.0}
```

How to read it: "+170 points" means the protocol grew 170 percentage points more than the typical peer. It does not
say why.

### 2. Data check (`defi_observatory.data_check`)

Rankings of "who grew the most" reward the strangest numbers, and the strangest numbers are often a single day. For
the last 90 days of a daily series the check flags:

| mark | rule |
|---|---|
| gap | a day the source did not publish (a published zero is data, not a gap) |
| isolated spike | a day above 5× the median of the 14 days around it, with both neighbours below 2× |
| isolated drop | level series only: a day below half that median, with both neighbours above half |
| revision | a past day changed by more than 1% between two downloads made on different days |

`cleanliness` is the share (0–100) of days with no mark. The data is never corrected: days are flagged, and the
30-day change can be computed with and without them.

```python
from defi_observatory import data_check

report = data_check.check_series(daily_fees, end_day="2026-09-30")
report["cleanliness"], report["events"]
data_check.change_with_and_without(daily_fees, "2026-09-29", flagged_days=["2026-09-14"])
```

Real case in the tests: Aave V2 fees. The public series shows $182,683 on 14 September 2026, 39 times the median of
the surrounding two weeks. The 30-day change is +342% with that day and +99% without it.

How to read it: the check does not claim the day is an error. It may be a real one-day event. Either way it is not
a trend.

### 3. Price or deposits (`defi_observatory.decomposition`)

Value locked is quantity × price, summed over deposited tokens. The change between two days splits into:

- **price effect** – the quantities held at the start × the change in each token's price;
- **flow effect** – the change in quantities × the prices at the end (deposits minus withdrawals).

Stablecoins are treated as fixed-price. The two effects must add up to the published change within 1%; any
difference is returned as the residual. A token swap (one token replaced by another) shows up as a large outflow
and a large price effect that cancel out: such results are flagged `composition_changed`.

```python
from defi_observatory import decomposition

start = {"ETH": (10, 20_000.0), "USDC": (5_000, 5_000.0)}     # token: (quantity, value in USD)
end = {"ETH": (12, 36_000.0), "USDC": (4_000, 4_000.0)}
out = decomposition.decompose(start, end)
out["price_effect_usd"], out["flow_effect_usd"]               # (10000.0, 5000.0)
```

Real case in the tests: Meta Pool Near, 30 days to 30 September 2026. Value locked +160%; token prices +169%; net
deposits −9.5%.

How to read it: prices used are the ones implied by the source (value ÷ quantity). Tokens that accrue yield have a
price that rises on its own; that part lands in the price effect.

### 4. Health index (`defi_observatory.health_index`)

A 0–100 number per protocol. Five measures, each turned into a percentile rank **inside the peer group**, equal
weights: deposit growth, fees on value locked, transactions, token return against BTC over 90 days, data
cleanliness. At least three measures and a group of at least five are required; otherwise no index is given.

```python
from defi_observatory import health_index

group = {"p1": {"fees_on_value": 0.02, "token_vs_btc": 0.4, "data_cleanliness": 100}, ...}
health_index.health_index(group)["p1"]      # {'index': ..., 'measures': 3, 'ranks': {...}, 'reason': None}
```

How to read it: 90 means "near the top of its own sector on most measures", not "90% healthy". Group medians sit
near 50 by construction, so sectors cannot be compared with each other through this index.

## Limits – what this does not tell you

- It does not predict anything and it does not recommend anything.
- It depends on public sources. When a source is wrong, late or revised, the numbers follow; the data check exists
  to make that visible, not to hide it.
- The most recent day of fee, revenue and volume series is often revised by the source in the following hours.
  The daily files in `data/` stop sums two days back for this reason.
- Peer groups follow the categories of the data source, with a few documented corrections. A different grouping
  gives different medians.
- A percentile rank inside a small group moves in large steps.

## Daily data (`data/`)

Aggregated results only – no raw copy of any source. See [`data/README.md`](data/README.md) for the columns.

| file | content |
|---|---|
| `health_index_<date>.csv` | health index and the five ranks, protocols above $50M in value locked with 90 days of history |
| `real_money_<date>.csv` | 30-day change in value locked split into price effect and net deposits |
| `data_check_<date>.csv` | cleanliness and counts of flagged days per protocol and measure |
| `*_latest.csv` | the most recent of each |

Before the files are written, a sample of the night's numbers is downloaded again from the original source and
recomputed; anything outside a 1% tolerance is left out.

## Sources and their terms

The methods are source-agnostic. The daily data is computed from:

| source | used for | terms |
|---|---|---|
| [DefiLlama](https://defillama.com) | value locked, per-token balances, fees, revenue, DEX volume, stablecoin supply | open API; attribution requested |
| [CoinGecko](https://www.coingecko.com) | token prices | CoinGecko API terms; attribution required |
| [Binance](https://www.binance.com) | perpetual futures funding and open interest | public market-data API terms |
| [GitHub](https://github.com) | commit counts of public repositories | GitHub REST API terms |
| [growthepie](https://www.growthepie.xyz) | layer-2 transactions and economics | CC BY-NC 4.0; attribution required |

Check each provider's current terms before reusing their data. This repository redistributes only derived,
aggregated figures.

## License

Code: MIT (see `LICENSE`).

Daily data in `data/`: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) – free to reuse with attribution ("Luca Valente, defi-observatory") and the attribution of the original sources listed above; not for commercial resale. The non-commercial clause follows from growthepie's CC BY-NC 4.0 terms, one of the inputs.

Author: Luca Valente.
