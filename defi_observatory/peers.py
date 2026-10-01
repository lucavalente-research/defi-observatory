"""A protocol's 30-day change, compared with the median of its peer group.

Two kinds of series are treated differently:

* **levels** (value locked, stablecoin supply, a market share): the change compares today's value with the *median
  of the five days around 30 days earlier* (days 32 to 28 back). A single odd day at the starting point then cannot
  inflate or deflate the change.
* **sums** (fees, revenue, trading volume): the change compares the total of the last 30 days with the total of the
  30 days before.

A comparison is only made inside groups of at least five members. Smaller groups return no median.
"""
from __future__ import annotations

import datetime as _dt
import statistics
from typing import Dict, Mapping, Optional

MIN_GROUP = 5


def _back(day: str, n: int) -> str:
    return (_dt.date.fromisoformat(day) - _dt.timedelta(days=n)).isoformat()


def change_30d_level(series: Mapping[str, float], day: str, min_base_days: int = 3) -> Optional[float]:
    """30-day change of a level series, as a fraction (0.12 = +12%).

    The base is the median of the values 32 to 28 days before ``day``; at least ``min_base_days`` of those five days
    must be present, otherwise the result is ``None``.

    >>> s = {"2026-09-30": 220.0, "2026-08-29": 100.0, "2026-08-30": 60.0, "2026-08-31": 101.0,
    ...      "2026-09-01": 99.0, "2026-09-02": 100.0}
    >>> round(change_30d_level(s, "2026-09-30"), 2)   # the one-day dip to 60 does not move the base
    1.2
    """
    if day not in series:
        return None
    base = [series[d] for d in (_back(day, k) for k in range(28, 33)) if d in series]
    if len(base) < min_base_days:
        return None
    middle = statistics.median(base)
    return series[day] / middle - 1 if middle > 0 else None


def change_30d_sum(series: Mapping[str, float], end_day: str, min_days: int = 27) -> Optional[float]:
    """30-day change of a flow series: total of the 30 days ending on ``end_day`` against the 30 days before.

    Returns ``None`` when either window has fewer than ``min_days`` published days or the earlier total is zero.

    >>> s = {(_dt.date(2026, 9, 30) - _dt.timedelta(days=i)).isoformat(): (2.0 if i < 30 else 1.0) for i in range(60)}
    >>> change_30d_sum(s, "2026-09-30")
    1.0
    """
    recent = [series[d] for d in (_back(end_day, i) for i in range(30)) if d in series]
    before = [series[d] for d in (_back(end_day, 30 + i) for i in range(30)) if d in series]
    if len(recent) < min_days or len(before) < min_days or not sum(before):
        return None
    return sum(recent) / sum(before) - 1


def compare_with_peers(changes: Mapping[str, float], min_group: int = MIN_GROUP) -> Dict[str, dict]:
    """Compare each member's change with the median change of the group.

    ``changes`` maps a member name to its 30-day change (fraction). The result maps each name to its change, the group
    median, the gap in percentage points, and the group size. With fewer than ``min_group`` members no comparison is
    made: the median and the gap are ``None``.

    >>> out = compare_with_peers({"a": 0.10, "b": 0.20, "c": 0.30, "d": 0.40, "e": 2.00})
    >>> out["e"]["peer_median"], out["e"]["gap_points"]
    (0.3, 170.0)
    """
    values = list(changes.values())
    median = statistics.median(values) if len(values) >= min_group else None
    return {name: {"change": x, "peer_median": median, "peers": len(values),
                   "gap_points": round((x - median) * 100, 1) if median is not None else None}
            for name, x in changes.items()}
