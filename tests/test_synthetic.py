"""Tests on small made-up data: each rule is checked in isolation."""
import datetime as dt

import pytest

from defi_observatory import data_check, decomposition, health_index, peers


def days(end, n):
    end = dt.date.fromisoformat(end)
    return [(end - dt.timedelta(days=i)).isoformat() for i in range(n)]


# ---------------------------------------------------------------- peers
def test_level_change_ignores_a_one_day_dip_at_the_base():
    s = {d: 100.0 for d in days("2026-09-30", 40)}
    s["2026-08-31"] = 55.0          # exactly 30 days before: a one-day dip
    s["2026-09-30"] = 200.0
    assert peers.change_30d_level(s, "2026-09-30") == pytest.approx(1.0)


def test_level_change_needs_three_base_days():
    s = {"2026-09-30": 200.0, "2026-08-31": 100.0, "2026-09-01": 100.0}
    assert peers.change_30d_level(s, "2026-09-30") is None


def test_sum_change_compares_two_thirty_day_totals():
    s = {d: (3.0 if i < 30 else 1.0) for i, d in enumerate(days("2026-09-29", 60))}
    assert peers.change_30d_sum(s, "2026-09-29") == pytest.approx(2.0)


def test_sum_change_needs_enough_days():
    s = {d: 1.0 for d in days("2026-09-29", 40)}
    assert peers.change_30d_sum(s, "2026-09-29") is None


def test_no_peer_median_under_five_members():
    out = peers.compare_with_peers({"a": 0.1, "b": 0.2, "c": 0.3, "d": 0.4})
    assert out["a"]["peer_median"] is None and out["a"]["gap_points"] is None


def test_gap_is_in_percentage_points():
    out = peers.compare_with_peers({"a": 0.10, "b": 0.20, "c": 0.30, "d": 0.40, "e": 2.00})
    assert out["e"]["gap_points"] == 170.0 and out["a"]["gap_points"] == -20.0


# ---------------------------------------------------------------- data check
def flat(end="2026-09-30", n=90, value=100.0):
    return {d: value for d in days(end, n)}


def test_clean_series_is_100():
    out = data_check.check_series(flat(), "2026-09-30")
    assert out["cleanliness"] == 100.0 and out["events"] == []


def test_gap_is_flagged_but_a_published_zero_is_not():
    s = flat()
    del s["2026-09-10"]
    s["2026-09-12"] = 0.0
    out = data_check.check_series(s, "2026-09-30")
    assert [(e["type"], e["day"]) for e in out["events"]] == [("gap", "2026-09-10")]


def test_isolated_spike_needs_normal_neighbours():
    s = flat()
    s["2026-09-15"] = 600.0
    assert data_check.check_series(s, "2026-09-30")["counts"]["isolated_spike"] == 1
    s["2026-09-16"] = 600.0        # two high days in a row: a change of level, not an isolated day
    assert data_check.check_series(s, "2026-09-30")["counts"]["isolated_spike"] == 0


def test_spike_threshold_is_five_times_the_median():
    s = flat()
    s["2026-09-15"] = 499.0
    assert data_check.check_series(s, "2026-09-30")["counts"]["isolated_spike"] == 0


def test_isolated_drop_only_for_levels():
    s = flat()
    s["2026-09-15"] = 45.0
    assert data_check.check_series(s, "2026-09-30", level=True)["counts"]["isolated_drop"] == 1
    assert data_check.check_series(s, "2026-09-30", level=False)["counts"]["isolated_drop"] == 0


def test_revision_above_one_percent_between_two_download_days():
    downloads = [("2026-09-20", 100.0, "2026-09-21"), ("2026-09-20", 100.5, "2026-09-22"),   # 0.5%: not a revision
                 ("2026-09-21", 100.0, "2026-09-21"), ("2026-09-21", 150.0, "2026-09-22"),   # same-day snapshot ignored
                 ("2026-09-22", 100.0, "2026-09-23"), ("2026-09-22", 110.0, "2026-09-24")]   # 10%: a revision
    out = data_check.check_series(flat(), "2026-09-30", downloads=downloads)
    assert [(e["type"], e["day"]) for e in out["events"]] == [("revision", "2026-09-22")]


def test_cleanliness_is_the_share_of_unflagged_days():
    s = flat()
    del s["2026-09-10"]
    s["2026-09-15"] = 900.0
    assert data_check.check_series(s, "2026-09-30")["cleanliness"] == pytest.approx(100.0 * 88 / 90, abs=0.05)


def test_change_with_and_without_the_flagged_day():
    s = {d: 10.0 for d in days("2026-09-29", 60)}
    s["2026-09-14"] = 310.0
    published, cleaned = data_check.change_with_and_without(s, "2026-09-29", ["2026-09-14"])
    assert published == pytest.approx(1.0) and cleaned == pytest.approx(-1 / 30)


# ---------------------------------------------------------------- decomposition
def test_price_and_flow_add_up():
    out = decomposition.decompose({"ETH": (10, 20000.0), "USDC": (5000, 5000.0)},
                                  {"ETH": (12, 36000.0), "USDC": (4000, 4000.0)})
    assert out["price_effect_usd"] == 10000.0          # 10 ETH x (3000 - 2000)
    assert out["flow_effect_usd"] == 5000.0            # +2 ETH x 3000, -1000 USDC
    assert out["adds_up"] and out["residual_usd"] == 0.0


def test_value_up_while_deposits_fall():
    out = decomposition.decompose({"NEAR": (100, 200.0)}, {"NEAR": (90, 450.0)})
    assert out["change"] == pytest.approx(1.25) and out["flow_effect"] < 0 < out["price_effect"]


def test_stablecoins_are_all_flow():
    out = decomposition.decompose({"USDT": (1000, 1000.0)}, {"USDT": (1500, 1498.0)})
    assert out["price_effect_usd"] == 0.0 and out["flow_effect_usd"] == 498.0


def test_token_present_on_one_day_only_is_all_flow():
    out = decomposition.decompose({"A": (1, 100.0)}, {"B": (1, 150.0)})
    assert out["price_effect_usd"] == 0.0 and out["flow_effect_usd"] == 50.0


def test_residual_is_reported_when_totals_do_not_match():
    out = decomposition.decompose({"ETH": (1, 100.0)}, {"ETH": (1, 100.0)}, value_locked_start=100.0, value_locked_end=120.0)
    assert not out["adds_up"] and out["residual"] == pytest.approx(0.2)


def test_token_swap_is_flagged():
    out = decomposition.decompose({"OLD": (100, 1000.0), "X": (1, 10.0)}, {"NEW": (10, 1050.0), "X": (1, 10.0)})
    assert not out["composition_changed"]               # all flow, nothing cancels
    out = decomposition.decompose({"T": (100, 1000.0)}, {"T": (30, 1050.0)})    # price x3.5, 70% withdrawn
    assert out["composition_changed"]


def test_median_base_day():
    tvl = {"a": 100.0, "b": 60.0, "c": 101.0, "d": 99.0, "e": 100.5}
    assert decomposition.median_base_day(tvl, list(tvl)) == "a"
    assert decomposition.median_base_day({"a": 1.0, "b": 2.0}, ["a", "b"]) is None


# ---------------------------------------------------------------- health index
def test_percentile_rank_handles_ties():
    assert health_index.percentile_rank(1, [1, 1, 2, 3]) == 25.0
    assert health_index.percentile_rank(3, [1, 1, 2, 3]) == 87.5


def test_index_is_the_plain_average_of_ranks():
    g = {n: {"fees_on_value": i, "token_vs_btc": i, "data_cleanliness": i} for i, n in enumerate("abcde")}
    out = health_index.health_index(g)
    assert out["a"]["index"] == 10.0 and out["e"]["index"] == 90.0 and out["c"]["index"] == 50.0


def test_index_needs_three_measures_and_five_members():
    g = {n: {"fees_on_value": i, "token_vs_btc": i} for i, n in enumerate("abcde")}
    assert health_index.health_index(g)["a"]["index"] is None
    g = {n: {"fees_on_value": i, "token_vs_btc": i, "data_cleanliness": i} for i, n in enumerate("abcd")}
    assert health_index.health_index(g)["a"]["index"] is None


def test_a_measure_counts_only_if_five_members_have_it():
    g = {n: {"fees_on_value": i, "token_vs_btc": i, "data_cleanliness": i} for i, n in enumerate("abcdef")}
    g["a"]["transactions"] = 5.0
    assert health_index.health_index(g)["a"]["measures"] == 3
