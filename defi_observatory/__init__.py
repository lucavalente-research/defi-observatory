"""defi-observatory: small, documented methods for reading public DeFi data.

Four building blocks:

* ``peers``          – a protocol's 30-day change against the median of its peer group
* ``data_check``     – gaps, isolated one-day spikes and drops, revisions, and a 0-100 cleanliness figure
* ``decomposition``  – how much of a change in value locked comes from token prices and how much from net deposits
* ``health_index``   – a 0-100 index built from the rank of five measures inside a peer group

Everything here describes what already happened in the data. Nothing is a forecast or advice.
"""
from . import data_check, decomposition, health_index, peers  # noqa: F401

__version__ = "0.1.0"
