"""A two-minute tour: run with `python examples/quick_tour.py` from the repository root."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # works without installing

from defi_observatory import data_check, decomposition, peers

HERE = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")

case = json.load(open(os.path.join(HERE, "aave_v2_fees.json")))
report = data_check.check_series(case["series"], case["end_day"])
spike = [e for e in report["events"] if e["type"] == "isolated_spike"][0]
published, cleaned = data_check.change_with_and_without(case["series"], case["sums_end_day"], [spike["day"]])
print("Data check, Aave V2 fees: %s is %.0f times the surrounding median; 30-day change %+.0f%% as published, "
      "%+.0f%% without that day; cleanliness %.1f" % (spike["day"], spike["times_the_median"], 100 * published,
                                                    100 * cleaned, report["cleanliness"]))

case = json.load(open(os.path.join(HERE, "meta_pool_near.json")))
base = decomposition.median_base_day(case["value_locked_by_day"], case["candidate_base_days"])
out = decomposition.decompose({k: tuple(v) for k, v in case["start"].items()},
                              {k: tuple(v) for k, v in case["end"].items()},
                              case["value_locked_by_day"][base], case["value_locked_by_day"][case["end_day"]])
print("Decomposition, Meta Pool Near: value locked %+.0f%%, token prices %+.0f%%, net deposits %+.1f%%"
      % (100 * out["change"], 100 * out["price_effect"], 100 * out["flow_effect"]))

case = json.load(open(os.path.join(HERE, "dex_fee_changes.json")))
row = peers.compare_with_peers(case["changes"])[case["member"]]
print("Peer comparison, Raydium fees: %+.0f%% against a median of %+.0f%% across %d exchanges"
      % (100 * row["change"], 100 * row["peer_median"], row["peers"]))
