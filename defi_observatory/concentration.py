"""Concentration: how much does a protocol depend on a few chains, or on a few days?

The measure is the Herfindahl index: the sum of the squared shares. It is close to 0 when the total is spread
evenly over many parts and equals 1 when everything sits in one part. ``1 / index`` reads as "the number of equal
parts that would give the same concentration".

Two uses here:

* **value locked by chain** – one share per chain the protocol is deployed on;
* **fees by day** – one share per day over 30 days. Thirty equal days give 1/30, not 0, so the index is also
  returned rescaled between 0 (the same amount every day) and 1 (everything in one day).

A high index is a description, not a verdict: a protocol built for one chain is concentrated by design.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional

from .peers import _back


def herfindahl(values: Iterable[float]) -> Optional[float]:
    """Sum of squared shares of the positive ``values``; ``None`` when there is nothing to share out.

    >>> herfindahl([50, 50])
    0.5
    >>> herfindahl([100, 0, 0])
    1.0
    >>> round(herfindahl([70, 20, 10]), 2)
    0.54
    """
    positive = [v for v in values if v and v > 0]
    total = sum(positive)
    if not positive or total <= 0:
        return None
    return sum((v / total) ** 2 for v in positive)


def normalized(index: Optional[float], parts: int) -> Optional[float]:
    """Rescale a Herfindahl index between 0 (``parts`` equal shares) and 1 (one share holds everything).

    >>> normalized(0.5, 2)
    0.0
    >>> normalized(1.0, 30)
    1.0
    """
    if index is None or parts < 2:
        return None
    return max(0.0, (index - 1.0 / parts) / (1.0 - 1.0 / parts))


def by_chain(value_locked: Mapping[str, float]) -> dict:
    """Concentration of value locked across chains.

    >>> out = by_chain({"Ethereum": 800.0, "Base": 150.0, "Arbitrum": 50.0})
    >>> out["largest_chain"], out["largest_chain_share"], out["chains"], round(out["index"], 3)
    ('Ethereum', 0.8, 3, 0.665)
    """
    positive = {k: v for k, v in value_locked.items() if v and v > 0}
    index = herfindahl(positive.values())
    if index is None:
        raise ValueError("no value locked on any chain")
    total = sum(positive.values())
    largest = max(positive, key=positive.get)
    return {"index": index, "chains": len(positive), "equivalent_chains": 1 / index, "largest_chain": largest,
            "largest_chain_share": positive[largest] / total, "value_locked": total}


def by_day(series: Mapping[str, float], end_day: str, window_days: int = 30, min_days: int = 27) -> dict:
    """Concentration of a daily flow (fees, volume) over the ``window_days`` ending on ``end_day``.

    >>> import datetime as dt
    >>> days = [(dt.date(2026, 9, 30) - dt.timedelta(days=i)).isoformat() for i in range(30)]
    >>> even = by_day({d: 10.0 for d in days}, "2026-09-30")
    >>> round(even["index"], 4), even["index_normalized"]
    (0.0333, 0.0)
    """
    days = [d for d in (_back(end_day, i) for i in range(window_days)) if series.get(d) is not None]
    if len(days) < min_days:
        raise ValueError("only %d published days out of %d" % (len(days), window_days))
    values = [max(series[d], 0) for d in days]
    index = herfindahl(values)
    if index is None:
        raise ValueError("nothing in the window")
    total = sum(values)
    ordered = sorted(values, reverse=True)
    return {"index": index, "index_normalized": normalized(index, len(days)), "days": len(days),
            "equivalent_days": 1 / index, "largest_day": max(days, key=lambda d: series[d]),
            "largest_day_share": ordered[0] / total, "three_largest_days_share": sum(ordered[:3]) / total}
