"""A two-minute tour: run with `python examples/quick_tour.py` from the repository root."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # works without installing

from defi_observatory import concentration, data_check, decomposition, event_study, fee_quality, lending, peers

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

case = json.load(open(os.path.join(HERE, "fee_quality_cases.json")))
aave = json.load(open(os.path.join(HERE, "aave_v2_fees.json")))["series"]
out = fee_quality.recurring_share(aave, case["end_day"], case["aave_v2"]["flagged_days"])
print("Fee quality, Aave V2: $%s of fees in 30 days, %.0f%% recurring (one day holds the rest)"
      % (format(round(out["fees"]), ","), 100 * out["recurring_share"]))

case = json.load(open(os.path.join(HERE, "concentration_cases.json")))
out = concentration.by_chain(case["value_locked_by_chain"])
print("Concentration, Morpho Blue: %d chains, %.0f%% on %s, index %.2f (like %.1f equal chains)"
      % (out["chains"], 100 * out["largest_chain_share"], out["largest_chain"], out["index"], out["equivalent_chains"]))

case = json.load(open(os.path.join(HERE, "lending_snapshot.json")))
out = lending.summarize(case["markets"])
print("Lending, sixteen large Aave v3 and Morpho markets at %s: %d above 90%% of deposits lent out"
      % (case["snapshot_utc"], out["highlighted"]))

case = json.load(open(os.path.join(HERE, "incident_effects.json")))
out = event_study.event_study([e["effects"]["30"] for e in case["events"]])
print("Event study, %d security incidents: value locked %+.1f points against peers 30 days later (90%% interval %+.1f to "
      "%+.1f). Same period, not proven cause." % (out["events"], 100 * out["mean"], 100 * out["low"], 100 * out["high"]))
