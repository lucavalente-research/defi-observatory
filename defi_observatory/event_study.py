"""Event study: what happened to a protocol in the days after an event, compared with its peers?

For one event (a governance vote, a launch, a token unlock, a security incident) and one measure:

* **levels** (value locked, token price against BTC): the value ``h`` days after the event against the median of
  the 5 days before it;
* **flows** (fees, transactions): the daily average of days +1 to +h against the average of the 7 days before.

The **effect** is that change minus the median of the same change across sector peers over the same days (at
least 5 peers). For a type of event, :func:`event_study` averages the effects and gives a 90% interval from a
bootstrap (2,000 resamples of the events). Below 15 events no average is returned: the sample is too small.

Limits, stated plainly: this measures what happened in the same period, not what the event caused. Other things
happen on the same days; events of one protocol are not independent of each other; and a list of events built from
public announcements leaves out the events nobody announced.
"""
from __future__ import annotations

import random
import statistics
from typing import Iterable, List, Mapping, Optional, Sequence

from .peers import _back

HORIZONS = (1, 7, 30)
MIN_EVENTS = 15
MIN_PEERS = 5
RESAMPLES = 2000
CONFIDENCE = 0.90


def change_after(series: Mapping[str, float], event_day: str, horizon: int, level: bool = True) -> Optional[float]:
    """Change of one series ``horizon`` days after ``event_day``; ``None`` when days are missing.

    >>> s = {"2026-09-%02d" % d: 100.0 for d in range(1, 11)}
    >>> s["2026-09-17"] = 110.0
    >>> round(change_after(s, "2026-09-10", 7), 4)
    0.1
    """
    if level:
        before = [series[d] for d in (_back(event_day, k) for k in range(1, 6)) if series.get(d)]
        after = series.get(_back(event_day, -horizon))
        if len(before) < 3 or after is None:
            return None
        base = statistics.median(before)
        return after / base - 1 if base > 0 else None
    before = [series[d] for d in (_back(event_day, k) for k in range(1, 8)) if series.get(d) is not None]
    after_days = [series[d] for d in (_back(event_day, -k) for k in range(1, horizon + 1)) if series.get(d) is not None]
    if len(before) < 6 or len(after_days) < max(1, int(0.9 * horizon)):
        return None
    base = sum(before) / len(before)
    return (sum(after_days) / len(after_days)) / base - 1 if base > 0 else None


def effect_against_peers(series: Mapping[str, float], peer_series: Iterable[Mapping[str, float]], event_day: str,
                         horizon: int, level: bool = True, min_peers: int = MIN_PEERS) -> Optional[dict]:
    """The protocol's change minus the median change of its peers over the same days.

    Returns ``{"effect", "change", "peer_median", "peers"}`` or ``None`` when the protocol's change cannot be
    computed or fewer than ``min_peers`` peers have data.
    """
    own = change_after(series, event_day, horizon, level)
    if own is None:
        return None
    peers = [c for c in (change_after(s, event_day, horizon, level) for s in peer_series) if c is not None]
    if len(peers) < min_peers:
        return None
    median = statistics.median(peers)
    return {"effect": own - median, "change": own, "peer_median": median, "peers": len(peers)}


def event_study(effects: Sequence[Optional[float]], resamples: int = RESAMPLES, confidence: float = CONFIDENCE,
                min_events: int = MIN_EVENTS, seed: int = 44) -> dict:
    """Average effect of a type of event, with a bootstrap interval.

    ``effects`` holds one effect per event (``None`` entries are ignored). With fewer than ``min_events`` the result
    is ``{"events": n, "status": "sample too small"}``. Otherwise the events are resampled with replacement
    ``resamples`` times; the interval is the central ``confidence`` share of the resampled means.

    >>> event_study([0.01, -0.02, 0.03])
    {'events': 3, 'status': 'sample too small', 'min_events': 15}
    >>> out = event_study([0.25] * 20)
    >>> out["mean"], out["low"], out["high"], out["includes_zero"]
    (0.25, 0.25, 0.25, False)
    """
    values: List[float] = [x for x in effects if x is not None]
    n = len(values)
    if n < min_events:
        return {"events": n, "status": "sample too small", "min_events": min_events}
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(resamples))
    tail = (1 - confidence) / 2
    low = means[int(tail * resamples)]
    high = means[min(resamples - 1, int((1 - tail) * resamples))]
    return {"events": n, "status": "measured", "mean": sum(values) / n, "median": statistics.median(values),
            "low": low, "high": high, "confidence": confidence, "resamples": resamples,
            "share_positive": sum(1 for v in values if v > 0) / n, "includes_zero": low <= 0 <= high}
