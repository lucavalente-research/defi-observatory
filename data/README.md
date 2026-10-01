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
