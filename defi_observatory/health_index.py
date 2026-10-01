"""Health index: a 0-100 number built from five measures, each ranked inside the protocol's peer group.

The five measures (any subset can be supplied):

* ``deposit_growth``     – 30-day growth of value locked, net deposits only when the decomposition is available;
* ``fees_on_value``      – fees of the last 30 days, annualised, divided by value locked;
* ``transactions``       – 30-day change in transactions;
* ``token_vs_btc``       – 90-day token return minus Bitcoin's;
* ``data_cleanliness``   – the 0-100 cleanliness from the data check.

Each measure enters as a percentile rank inside the group (0 = lowest, 100 = highest). The index is the plain average
of the available ranks: equal weights. It needs at least three measures and a group of at least five members; a
measure counts only if at least five members have it.

It is a position among peers, not an absolute grade: 90 means "near the top of its own group on most measures".
Group medians sit near 50 by construction, so groups cannot be compared with each other through this index.
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence

MEASURES = ("deposit_growth", "fees_on_value", "transactions", "token_vs_btc", "data_cleanliness")
MIN_MEASURES = 3
MIN_GROUP = 5


def percentile_rank(x: float, values: Sequence[float]) -> float:
    """Mid-rank percentile of ``x`` among ``values`` (which include ``x``): 0 = lowest, 100 = highest.

    >>> percentile_rank(3, [1, 2, 3, 4, 5])
    50.0
    """
    below = sum(1 for y in values if y < x)
    equal = sum(1 for y in values if y == x)
    return 100.0 * (below + 0.5 * equal) / len(values)


def health_index(group: Mapping[str, Mapping[str, Optional[float]]], min_measures: int = MIN_MEASURES,
                 min_group: int = MIN_GROUP) -> Dict[str, dict]:
    """Compute the index for every member of one peer group.

    ``group`` maps a member name to its raw measures, e.g. ``{"fees_on_value": 0.02, "token_vs_btc": 0.4}``; missing
    or ``None`` measures are skipped. Returns, per member, ``{"index", "measures", "ranks", "reason"}``; ``index`` is
    ``None`` (with a ``reason``) when the group is too small or fewer than ``min_measures`` measures are available.

    >>> g = {n: {"fees_on_value": i, "token_vs_btc": -i, "data_cleanliness": 100} for i, n in enumerate("abcde")}
    >>> health_index(g)["e"]["index"]
    50.0
    """
    names = list(group)
    pools = {m: [group[n][m] for n in names if group[n].get(m) is not None] for m in MEASURES}
    out = {}
    for n in names:
        ranks = {m: round(percentile_rank(group[n][m], pools[m]), 1) for m in MEASURES
                 if group[n].get(m) is not None and len(pools[m]) >= min_group}
        if len(names) < min_group:
            index, reason = None, "group of %d members (%d needed)" % (len(names), min_group)
        elif len(ranks) < min_measures:
            index, reason = None, "%d of 5 measures available (%d needed)" % (len(ranks), min_measures)
        else:
            index, reason = round(sum(ranks.values()) / len(ranks), 1), None
        out[n] = {"index": index, "measures": len(ranks), "ranks": ranks, "reason": reason}
    return out
