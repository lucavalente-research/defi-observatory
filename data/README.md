# Daily data

One file per product and day, plus `*_latest.csv`. Changes and effects are fractions (0.12 = +12%). Dates are UTC.

## health_index_<date>.csv
`date, protocol_id, protocol, sector, health_index, measures_available, change_7d, rank_deposit_growth,
rank_fees_on_value, rank_transactions, rank_token_vs_btc, rank_data_cleanliness`
Ranks are percentiles inside the sector (0 = lowest, 100 = highest); empty when the measure is not available.
Only protocols with at least $50M in value locked and 90 days of history.

## real_money_<date>.csv
`date, protocol_id, protocol, sector, start_day, value_locked_start_usd, value_locked_end_usd, change_30d,
price_effect, net_deposits_effect, residual`
`start_day` is the day with the median value locked among the five days around 30 days earlier.

## data_check_<date>.csv
`date, protocol_id, protocol, sector, measure, cleanliness_0_100, days_checked, gaps, isolated_spikes,
isolated_drops, revisions, flagged_days`
`flagged_days` lists isolated spikes and drops as `day:times_the_median`.

## fee_quality_<date>.csv (weekly)
`date, protocol_id, protocol, sector, fees_through, fees_30d_usd, recurring_usd, one_off_usd, recurring_share,
one_off_days, paid_in_lumps`
A day is one-off when it was flagged by the data check or is above 3 times the median day of the 30 days ending on
`fees_through`. `one_off_days` lists those days. `paid_in_lumps` = 1 when the fees arrive in a few large days (for
example a weekly settlement): the split is not meaningful there.

## concentration_<date>.csv (weekly)
`date, protocol_id, protocol, sector, value_locked_usd, chains, hhi_value_locked_by_chain, largest_chain,
largest_chain_share, hhi_fees_by_day, hhi_fees_by_day_normalized, largest_day_share, three_largest_days_share`
`hhi` is the Herfindahl index (sum of squared shares, 0 = spread out, 1 = all in one). Chain columns are empty when
the chain breakdown is missing or does not add up to the protocol's value locked within 5%.

## lending_stress_<date>.csv (weekly)
`snapshot_utc, protocol, market, chain, asset, deposits_usd, borrowed_usd, available_liquidity_usd, utilization,
supply_apy, borrow_apy, highlighted`
One row per market with at least $1M of deposits, not frozen. A snapshot taken at `snapshot_utc`, not a daily average.
`highlighted` = 1 when deposits are at least $10M and utilization is above 90% (above 99% for Morpho, whose markets
are built to sit at 90%).
