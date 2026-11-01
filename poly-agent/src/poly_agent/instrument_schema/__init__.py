"""Instrument schema parsers for Polymarket Exchange.

Maps instrument metadata to typed market types without parsing slugs.
Per the docs: "Do not parse the instrument symbol or slug - identify markets using fields below."
"""

from . import sports
from . import crypto

__all__ = ["sports", "crypto"]
