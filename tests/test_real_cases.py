"""Four real cases saved as small fixtures: the library must give the numbers the nightly observatory published."""
import json
import os

import pytest

from defi_observatory import data_check, decomposition, health_index, peers

HERE = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def test_data_check_aave_v2_fees_14_september_2026():
    case = load("aave_v2_fees.json")
    exp = case["expected"]
    out = data_check.check_series(case["series"], case["end_day"])
    spikes = [e for e in out["events"] if e["type"] == "isolated_spike"]
    assert len(spikes) == 1
    assert spikes[0]["day"] == exp["flagged_day"] and spikes[0]["value"] == exp["value"]
    assert spikes[0]["times_the_median"] == exp["times_the_median"]
    assert out["cleanliness"] == exp["cleanliness"]
    published, cleaned = data_check.change_with_and_without(case["series"], case["sums_end_day"], [exp["flagged_day"]])
    assert round(published, 4) == exp["change_30d"]
    assert round(cleaned, 4) == exp["change_30d_without_flagged_day"]


def test_decomposition_meta_pool_near_september_2026():
    case = load("meta_pool_near.json")
    exp = case["expected"]
    base = decomposition.median_base_day(case["value_locked_by_day"], case["candidate_base_days"])
    assert base == exp["start_day"] == case["start_day"]
    out = decomposition.decompose({k: tuple(v) for k, v in case["start"].items()},
                                  {k: tuple(v) for k, v in case["end"].items()},
                                  case["value_locked_by_day"][base], case["value_locked_by_day"][case["end_day"]])
    assert round(out["change"], 4) == exp["change"]
    assert round(out["price_effect"], 4) == exp["price_effect"]
    assert round(out["flow_effect"], 4) == exp["flow_effect"]
    assert out["adds_up"] and not out["composition_changed"]
    assert out["change"] > 1 and out["flow_effect"] < 0        # value locked more than doubled while deposits fell


def test_peer_comparison_raydium_fees_29_september_2026():
    case = load("dex_fee_changes.json")
    exp = case["expected"]
    totals = case["raydium_totals"]
    assert round(totals["last_30_days"] / totals["previous_30_days"] - 1, 4) == exp["change"]
    out = peers.compare_with_peers(case["changes"])[case["member"]]
    assert out["peers"] == exp["peers"]
    assert round(out["peer_median"], 4) == exp["peer_median"]
    assert out["gap_points"] == exp["gap_points"]


def test_health_index_collateralised_debt_group_30_september_2026():
    case = load("cdp_group.json")
    out = health_index.health_index(case["group"])
    for name, exp in case["expected"].items():
        assert out[name]["index"] == exp["index"], name
        assert out[name]["measures"] == exp["measures"], name
