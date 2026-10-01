"""Data check: is a daily series clean enough to be quoted?

For the last 90 days of a daily series the check marks four kinds of days:

* **gap** – a day the source did not publish (a published zero is data, not a gap);
* **isolated spike** – a day more than 5 times the median of the 14 days around it (7 before, 7 after) while the
  day before and the day after are both below 2 times that median;
* **isolated drop** – for level series only: a day below half that median while both neighbours are above half of it;
* **revision** – a past day whose value changed by more than 1% between two downloads made on different days.

``cleanliness`` is the share (0-100) of days in the window with none of these marks.

The raw data is never corrected: days are flagged, and every figure can be computed with or without them. The check
does not say whether a flagged day is a source error or a real one-day event. It only says the day stands alone.
"""
from __future__ import annotations

import datetime as _dt
import statistics
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from .peers import _back, change_30d_level, change_30d_sum

WINDOW_DAYS = 90
AROUND = 7
MIN_AROUND = 8
SPIKE_TIMES = 5.0
NEIGHBOUR_TIMES = 2.0
DROP_FRACTION = 0.5
MIN_REVISION = 0.01


def check_series(series: Mapping[str, float], end_day: str, level: bool = False,
                 downloads: Optional[Iterable[Tuple[str, float, str]]] = None,
                 window_days: int = WINDOW_DAYS) -> dict:
    """Check one daily series.

    ``series`` maps ISO days to the latest published value. ``end_day`` is the last day of the window. ``level`` is
    True for level series (value locked, stablecoin supply), False for flows (fees, revenue, volume). ``downloads``
    is optional: an iterable of ``(day, value, download_day)`` in download order, used to find revisions; only
    downloads made after the day itself are compared (a reading taken during the day is a snapshot, not a revision).

    Returns ``{"cleanliness", "days", "flagged_days", "counts", "events"}``.

    >>> days = [(_dt.date(2026, 9, 30) - _dt.timedelta(days=i)).isoformat() for i in range(40)]
    >>> s = {d: 100.0 for d in days}
    >>> s["2026-09-15"] = 900.0
    >>> out = check_series(s, "2026-09-30")
    >>> [(e["type"], e["day"], e["times_the_median"]) for e in out["events"]]
    [('isolated_spike', '2026-09-15', 9.0)]
    """
    if not series:
        raise ValueError("empty series")
    start = max(_back(end_day, window_days - 1), min(series))
    n_days = (_dt.date.fromisoformat(end_day) - _dt.date.fromisoformat(start)).days + 1
    days = [_back(end_day, i) for i in range(n_days - 1, -1, -1)]
    events: List[dict] = []
    flagged = set()
    for day in days:
        if day not in series:
            events.append({"type": "gap", "day": day})
            flagged.add(day)
            continue
        around = [series[x] for x in (_back(day, k) for k in range(-AROUND, AROUND + 1)) if x != day and x in series]
        before, after = series.get(_back(day, 1)), series.get(_back(day, -1))
        if len(around) < MIN_AROUND or before is None or after is None:
            continue
        median = statistics.median(around)
        if median <= 0:
            continue
        value, kind = series[day], None
        if value > SPIKE_TIMES * median and before < NEIGHBOUR_TIMES * median and after < NEIGHBOUR_TIMES * median:
            kind = "isolated_spike"
        elif level and value < DROP_FRACTION * median and before > median / NEIGHBOUR_TIMES \
                and after > median / NEIGHBOUR_TIMES:
            kind = "isolated_drop"
        if kind:
            events.append({"type": kind, "day": day, "value": value, "reference_median": median,
                           "times_the_median": round(value / median, 2), "day_before": before, "day_after": after})
            flagged.add(day)
    versions: Dict[str, List[Tuple[str, float]]] = {}
    for day, value, downloaded in downloads or ():
        if downloaded > day:
            versions.setdefault(day, []).append((downloaded, value))
    for day in days:
        seen = versions.get(day) or []
        for (d1, a), (d2, b) in zip(seen, seen[1:]):
            if d2 > d1 and a != b and (a == 0 or abs(b - a) / abs(a) > MIN_REVISION):
                events.append({"type": "revision", "day": day, "value": b, "value_before": a,
                               "downloaded_before": d1, "downloaded_after": d2})
                flagged.add(day)
    events.sort(key=lambda e: (e["day"], e["type"]))
    counts = {k: sum(1 for e in events if e["type"] == k) for k in ("gap", "isolated_spike", "isolated_drop", "revision")}
    return {"cleanliness": round(100.0 * (len(days) - len(flagged)) / len(days), 1), "days": len(days),
            "flagged_days": len(flagged), "counts": counts, "events": events}


def change_with_and_without(series: Mapping[str, float], end_day: str, flagged_days: Iterable[str],
                            level: bool = False) -> Tuple[Optional[float], Optional[float]]:
    """The 30-day change as published, and the same change with the flagged days left out.

    For flows the flagged days are removed from the 30-day totals; for levels they are removed from the five base
    days (and a flagged last day gives ``None``).

    >>> days = [(_dt.date(2026, 9, 30) - _dt.timedelta(days=i)).isoformat() for i in range(60)]
    >>> s = {d: 10.0 for d in days}
    >>> s["2026-09-15"] = 310.0
    >>> change_with_and_without(s, "2026-09-30", ["2026-09-15"])
    (1.0, -0.033333333333333326)
    """
    without = set(flagged_days)
    cleaned = {d: v for d, v in series.items() if d not in without}
    if level:
        return change_30d_level(series, end_day), change_30d_level(cleaned, end_day)
    return change_30d_sum(series, end_day), change_30d_sum(cleaned, end_day, min_days=27 - len(without))
