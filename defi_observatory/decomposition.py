"""Price or deposits? Splitting a change in value locked into two parts.

A protocol's value locked is the sum, over deposited tokens, of quantity times price. Between two days:

* **price effect** = the quantities held on the first day times the change in each token's price
  (what would have happened if nobody had touched anything);
* **flow effect**  = the change in quantities times the prices on the last day (deposits minus withdrawals).

The two add up to the change in the value of the tokens. Stablecoins are treated as fixed-price: all of their change
is flow. A token present on only one of the two days is all flow. The difference between the published change in
value locked and the two effects is the **residual**; it is reported whenever it exceeds 1% of the starting value.

One caveat is detected and flagged: when a protocol swaps one token for another (a migration), the method shows a
huge outflow and a huge price effect that cancel out. Such a result is marked ``composition_changed``.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional, Tuple

STABLECOINS = frozenset({
    "USDT", "USDC", "DAI", "USDE", "USDS", "FDUSD", "PYUSD", "TUSD", "USDP", "BUSD", "LUSD", "GHO", "CRVUSD", "USDD",
    "USD0", "USD1", "RLUSD", "USDB", "FRAX", "FRXUSD", "USDT0", "USDC.E", "USDBC", "USDF", "USDX", "USDTB", "USDG",
    "DOLA", "SUSD", "GUSD", "USDH", "AUSD"})
TOLERANCE = 0.01


def median_base_day(value_locked_by_day: Mapping[str, float], candidates: Iterable[str]) -> Optional[str]:
    """Pick the starting day: among the candidate days (the five days around 30 days earlier), the one whose value
    locked is the median. It is a real day with a real composition, and a one-day dip cannot become the base.

    >>> median_base_day({"d1": 100, "d2": 60, "d3": 101, "d4": 99, "d5": 100}, ["d1", "d2", "d3", "d4", "d5"])
    'd1'
    """
    present = sorted((value_locked_by_day[d], d) for d in candidates if value_locked_by_day.get(d))
    return present[len(present) // 2][1] if len(present) >= 3 else None


def decompose(start: Mapping[str, Tuple[float, float]], end: Mapping[str, Tuple[float, float]],
              value_locked_start: Optional[float] = None, value_locked_end: Optional[float] = None,
              stablecoins: Iterable[str] = STABLECOINS) -> dict:
    """Split the change in value locked between two days.

    ``start`` and ``end`` map a token symbol to ``(quantity, value_in_usd)`` on each day. ``value_locked_start`` and
    ``value_locked_end`` are the published totals; when omitted, the sums of the token values are used.

    All effects are returned in dollars and as fractions of the starting value locked.

    >>> out = decompose({"ETH": (10, 20000), "USDC": (5000, 5000)}, {"ETH": (9, 27000), "USDC": (8000, 8000)})
    >>> out["price_effect_usd"], out["flow_effect_usd"], out["adds_up"]
    (10000.0, 0.0, True)
    """
    stable = {s.upper() for s in stablecoins}
    v0 = value_locked_start if value_locked_start is not None else sum(u for _q, u in start.values())
    v1 = value_locked_end if value_locked_end is not None else sum(u for _q, u in end.values())
    if not v0:
        raise ValueError("starting value locked is zero or missing")
    price = flow = unpriced = stable_start = 0.0
    for symbol in set(start) | set(end):
        q0, u0 = start.get(symbol, (0.0, 0.0))
        q1, u1 = end.get(symbol, (0.0, 0.0))
        q0, u0, q1, u1 = q0 or 0.0, u0 or 0.0, q1 or 0.0, u1 or 0.0
        if symbol.upper() in stable:
            flow += u1 - u0
            stable_start += u0
        elif q0 > 0 and u0 > 0 and q1 > 0 and u1 > 0:
            p0, p1 = u0 / q0, u1 / q1
            price += q0 * (p1 - p0)
            flow += (q1 - q0) * p1
        elif u1 <= 0 and q1 <= 0:
            flow -= u0                      # left entirely
        elif u0 <= 0 and q0 <= 0:
            flow += u1                      # arrived during the period
        else:
            unpriced += u1 - u0             # no price on one of the two days
    total = v1 - v0
    residual = total - price - flow
    gross = abs(price) + abs(flow)
    return {"value_locked_start": v0, "value_locked_end": v1, "change": total / v0,
            "price_effect_usd": round(price, 2), "flow_effect_usd": round(flow, 2), "residual_usd": round(residual, 2),
            "price_effect": price / v0, "flow_effect": flow / v0, "residual": residual / v0,
            "adds_up": abs(residual / v0) <= TOLERANCE, "unpriced_usd": round(unpriced, 2),
            "stablecoin_share_start": stable_start / v0,
            "composition_changed": gross > 0.5 * v0 and abs(total) < 0.25 * gross}
