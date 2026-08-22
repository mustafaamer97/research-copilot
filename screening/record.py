"""
Screening record public API.

Canonical ScreeningRecord is defined in domain.screening.
This module exists only as the screening package import boundary.
"""

from domain.screening import ScreeningRecord

__all__ = [
    "ScreeningRecord",
]
