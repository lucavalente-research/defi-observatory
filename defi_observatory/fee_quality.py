"""Fee quality: how much of a protocol's fees is recurring, and how much comes from one-off days?

Over the last 30 days of a daily fee series, a day is **one-off** when

* it was flagged by the data check (an isolated spike), or
* it is more than 3 times the median day of those 30 days.

Every other day is **recurring**. A one-off day counts in full. The recurring share is recurring fees divided by
all fees of the 30 days.

Some series are not daily in practice: fees settled once a week arrive in a few large days with almost nothing in
between. Under the rule above those days are one-off even though they come back every week. Such series are marked
``lumpy`` (at least 4 one-off days and a median day below 20% of the average day): read their split with care.

This describes the last 30 days only. It does not say why a day stood out, and a high recurring share is not a
promise that the fees will continue.
"""
from __future__ import annotations

import statistics
from typing import Iterable, Mapping

from .peers import _back

WINDOW_DAYS = 30
MIN_DAYS = 27
TIMES_THE_MEDIAN = 3.0
LUMPY_MIN_DAYS = 4
LUMPY_MEDIAN_OVER_MEAN = 0.2


def recurring_share(series: Mapping[str, float], end_day: str, flagged_days: Iterable[str] = (),
                    window_days: int = WINDOW_DAYS) -> dict:
    """Split the fees of the ``window_days`` ending on ``end_day`` into recurring and one-off.

    ``series`` maps ISO days to the fees of that day. ``flagged_days`` are days already flagged by
    :func:`defi_observatory.data_check.check_series`. At least 27 published days and a positive total are required.

    Returns ``{"fees", "recurring", "one_off", "recurring_share", "median_day", "one_off_days", "lumpy"}``.

    >>> import datetime as dt
    >>> days = [(dt.date(2026, 9, 30) - dt.timedelta(days=i)).isoformat() for i in range(30)]
    >>> s = {d: 100.0 for d in days}
    >>> s["2026-09-10"] = 1100.0
    >>> out = recurring_share(s, "2026-09-30")
    >>> out["fees"], out["one_off"], out["recurring_share"]
    (4000.0, 1100.0, 0.725)
    >>> [(x["day"], x["times_the_median"]) for x in out["one_off_days"]]
    [('2026-09-10', 11.0)]
    """
    days = [d for d in (_back(end_day, i) for i in range(window_days)) if series.get(d) is not None]
    if len(days) < MIN_DAYS:
        raise ValueError("only %d published days out of %d" % (len(days), window_days))
    total = float(sum(series[d] for d in days))
    if total <= 0:
        raise ValueError("no fees in the window")
    median = statistics.median(series[d] for d in days)
    flagged = set(flagged_days)
    one_off_days = []
    for day in sorted(days):
        value = series[day]
        if value <= 0:
            continue
        if day in flagged:
            reason = "flagged by the data check"
        elif value > TIMES_THE_MEDIAN * median:
            reason = "above %g times the median day" % TIMES_THE_MEDIAN
        else:
            continue
        one_off_days.append({"day": day, "value": value, "reason": reason,
                             "times_the_median": round(value / median, 2) if median > 0 else None})
    one_off = float(sum(x["value"] for x in one_off_days))
    return {"fees": total, "recurring": total - one_off, "one_off": one_off,
            "recurring_share": round(1 - one_off / total, 4), "median_day": median, "one_off_days": one_off_days,
            "lumpy": len(one_off_days) >= LUMPY_MIN_DAYS and median < LUMPY_MEDIAN_OVER_MEAN * total / len(days)}
