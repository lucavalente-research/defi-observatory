"""Real cases saved as small fixtures: the library must give the numbers the nightly observatory published."""
import json
import os

import pytest

from defi_observatory import (concentration, data_check, decomposition, event_study, fee_quality, health_index, lending,
                              peers)

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


def test_fee_quality_uniswap_v4_and_aave_v2_september_2026():
    case = load("fee_quality_cases.json")
    uni = case["uniswap_v4"]
    out = fee_quality.recurring_share(uni["series"], case["end_day"], uni["flagged_days"])
    assert out["fees"] == uni["expected"]["fees"] and out["one_off"] == uni["expected"]["one_off"]
    assert out["recurring_share"] == uni["expected"]["recurring_share"]
    assert [x["day"] for x in out["one_off_days"]] == uni["expected"]["one_off_days"]
    # Aave V2: the day flagged by the data check (14 September) is more than half of the month's fees
    aave = case["aave_v2"]
    out = fee_quality.recurring_share(load("aave_v2_fees.json")["series"], case["end_day"], aave["flagged_days"])
    assert out["fees"] == aave["expected"]["fees"] and out["one_off"] == aave["expected"]["one_off"]
    assert out["recurring_share"] == aave["expected"]["recurring_share"] < 0.5
    assert [x["day"] for x in out["one_off_days"]] == aave["expected"]["one_off_days"]


def test_concentration_morpho_blue_chains_and_ethena_fee_days_september_2026():
    case = load("concentration_cases.json")
    exp = case["expected"]
    out = concentration.by_chain(case["value_locked_by_chain"])
    assert round(out["index"], 4) == exp["index"] and out["chains"] == exp["chains"]
    assert out["largest_chain"] == exp["largest_chain"]
    assert round(out["largest_chain_share"], 4) == exp["largest_chain_share"]
    exp = case["expected_fees"]
    out = concentration.by_day(case["ethena_usde_fees"], case["fees_end_day"])
    assert round(out["index"], 4) == exp["index"] and round(out["index_normalized"], 4) == exp["index_normalized"]
    assert out["largest_day"] == exp["largest_day"]
    assert round(out["largest_day_share"], 4) == exp["largest_day_share"]
    assert round(out["three_largest_days_share"], 4) == exp["three_largest_days_share"]


def test_lending_snapshot_aave_v3_and_morpho_1_october_2026():
    case = load("lending_snapshot.json")
    exp = case["expected"]
    out = lending.summarize(case["markets"])
    assert out["large_markets"] == exp["large_markets"] and out["highlighted"] == exp["highlighted"]
    assert ["%s %s" % (m["market"], m["asset"]) for m in out["highlighted_markets"]] == exp["highlighted_names"]
    assert all(m["utilization"] > 0.9 and m["deposits_usd"] >= 10e6 for m in out["highlighted_markets"])


def test_event_study_security_incidents_2020_to_2026():
    case = load("incident_effects.json")
    for horizon, exp in case["expected"].items():
        out = event_study.event_study([e["effects"][horizon] for e in case["events"]])
        assert out["status"] == "measured" and out["events"] == exp["events"]
        assert round(out["mean"], 5) == exp["mean"]
        assert round(out["low"], 5) == exp["low"] and round(out["high"], 5) == exp["high"]
        assert out["high"] < 0                 # value locked fell against peers: the interval stays below zero


def test_event_effect_uniswap_governance_vote_23_september_2026():
    case = load("uniswap_vote.json")
    exp = case["expected"]
    out = event_study.effect_against_peers(case["series"], case["peer_series"], case["event_day"], case["horizon"])
    assert out["peers"] == exp["peers"]
    assert round(out["change"], 4) == exp["change"] and round(out["peer_median"], 4) == exp["peer_median"]
    assert round(out["effect"], 4) == exp["effect"]
    assert abs(out["effect"]) < 0.01           # the protocol moved with its sector
