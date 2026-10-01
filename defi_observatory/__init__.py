"""defi-observatory: small, documented methods for reading public DeFi data.

Seven building blocks:

* ``peers``          – a protocol's 30-day change against the median of its peer group
* ``data_check``     – gaps, isolated one-day spikes and drops, revisions, and a 0-100 cleanliness figure
* ``decomposition``  – how much of a change in value locked comes from token prices and how much from net deposits
* ``health_index``   – a 0-100 index built from the rank of five measures inside a peer group
* ``fee_quality``    – the share of 30-day fees that is recurring, and the share that comes from one-off days
* ``concentration``  – how much a protocol depends on a few chains or a few days (Herfindahl index)
* ``lending``        – share of deposits lent out per lending market, with the markets above 90% highlighted

Everything here describes what already happened in the data. Nothing is a forecast or advice.
"""
from . import concentration, data_check, decomposition, fee_quality, health_index, lending, peers  # noqa: F401

__version__ = "0.2.0"
