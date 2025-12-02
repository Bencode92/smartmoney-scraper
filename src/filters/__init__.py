"""SmartMoney v2.3.1 — Filters Package

Filtres pour l'univers d'investissement:
- liquidity: Market cap, ADV, position vs ADV
- hard_filters: D/E, Coverage, ND/EBITDA (exclusion binaire)
- look_ahead: Contrôle du biais look-ahead
- buffett_filters: Filtres style Buffett (historique, pertes, industries) [v2.3.1]
"""

from .liquidity import apply_liquidity_filters, check_liquidity_single
from .hard_filters import apply_hard_filters, check_hard_filters_single
from .look_ahead import filter_by_publication_date, validate_no_look_ahead, get_latest_available_year

# Buffett filters v2.3.1
from .buffett_filters import (
    apply_buffett_filters,
    compute_buffett_features,
    check_buffett_eligibility,
    get_buffett_universe_stats,
)

__all__ = [
    # Liquidity
    "apply_liquidity_filters",
    "check_liquidity_single",
    # Hard filters
    "apply_hard_filters",
    "check_hard_filters_single",
    # Look-ahead
    "filter_by_publication_date",
    "validate_no_look_ahead",
    "get_latest_available_year",
    # Buffett v2.3.1
    "apply_buffett_filters",
    "compute_buffett_features",
    "check_buffett_eligibility",
    "get_buffett_universe_stats",
]
