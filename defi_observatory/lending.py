"""Lending markets: how much of the deposits is lent out, market by market?

For each market the inputs are what the lending protocols publish themselves: deposits, borrowed amount, available
liquidity and the two interest rates. **Utilization** is borrowed divided by deposits. A market is *highlighted*
when utilization is above 90%, deposits are at least $10M and the market is not frozen.

This is a snapshot of one moment: utilization moves minute by minute. It is a description only. Many interest-rate
models are built to keep utilization close to a set level (Morpho's is built around 90%), so a market near that
level is where its design puts it.
"""
from __future__ import annotations

from typing import Iterable, List, Mapping, Optional

HIGHLIGHT_ABOVE = 0.90
MIN_DEPOSITS = 10e6


def utilization(deposits: float, borrowed: float) -> Optional[float]:
    """Borrowed divided by deposits; ``None`` when there are no deposits.

    >>> utilization(200.0, 150.0)
    0.75
    >>> utilization(0, 0) is None
    True
    """
    if not deposits or deposits <= 0:
        return None
    return borrowed / deposits


def summarize(markets: Iterable[Mapping], highlight_above: float = HIGHLIGHT_ABOVE,
              min_deposits: float = MIN_DEPOSITS) -> dict:
    """Count the large markets and the highlighted ones.

    Each market is a mapping with ``deposits_usd``, ``borrowed_usd`` and optionally ``utilization`` (taken as
    published when present) and ``frozen``.

    >>> ms = [{"name": "a", "deposits_usd": 50e6, "borrowed_usd": 47e6},
    ...       {"name": "b", "deposits_usd": 80e6, "borrowed_usd": 40e6},
    ...       {"name": "c", "deposits_usd": 2e6, "borrowed_usd": 1.9e6}]
    >>> out = summarize(ms)
    >>> out["large_markets"], out["highlighted"], [m["name"] for m in out["highlighted_markets"]]
    (2, 1, ['a'])
    >>> out["utilization_of_large_markets"]
    0.6692
    """
    large: List[dict] = []
    for m in markets:
        u = m.get("utilization")
        if u is None:
            u = utilization(m["deposits_usd"], m["borrowed_usd"])
        if u is None or m["deposits_usd"] < min_deposits or m.get("frozen"):
            continue
        large.append(dict(m, utilization=u))
    highlighted = sorted((m for m in large if m["utilization"] > highlight_above), key=lambda m: -m["deposits_usd"])
    deposits = sum(m["deposits_usd"] for m in large)
    return {"large_markets": len(large), "highlighted": len(highlighted), "highlighted_markets": highlighted,
            "deposits_usd": deposits, "deposits_in_highlighted_usd": sum(m["deposits_usd"] for m in highlighted),
            "utilization_of_large_markets": round(sum(m["borrowed_usd"] for m in large) / deposits, 4) if deposits else None}
