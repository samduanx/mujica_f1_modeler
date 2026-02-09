"""Tyre module for F1 tyre modelling.

This module contains tyre degradation and tyre type functionality:
- Tyre degradation calculations
- Tyre compound characteristics
- Tyre wear and performance modelling
"""

from .tyre_types import (
    tyre_compounds_2022,
    df_tyre_compounds,
)

__all__ = [
    "tyre_compounds_2022",
    "df_tyre_compounds",
]
