"""⚠️  [DEPRECATED] Configuration SmartMoney Engine v2.3/v2.4

╔══════════════════════════════════════════════════════════════════════╗
║  CE FICHIER EST DÉPRÉCIÉ — Utiliser config_v30.py à la place         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Migration:                                                          ║
║    AVANT:  from config_v23 import WEIGHTS_V23, CONSTRAINTS_V23       ║
║    APRÈS:  from config_v30 import WEIGHTS_V30, CONSTRAINTS_V30       ║
║                                                                      ║
║  Voir MIGRATION_V30.md pour le guide complet.                        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

Différences clés v2.3 vs v3.0:
- v2.3: Smart Money 15%, Insider 10%, Momentum 5%
- v3.0: Smart Money 0%, Insider 0%, Momentum 0% (indicateurs only)

Ce fichier reste disponible pour rétrocompatibilité mais émettra
des warnings de dépréciation dans une future version.

Date de dépréciation: Décembre 2025
"""

import warnings

# Émettre un warning à l'import
warnings.warn(
    "config_v23 est déprécié. Utiliser config_v30 pour la nouvelle logique Buffett-Quant. "
    "Voir MIGRATION_V30.md pour le guide de migration.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Dict, List, Tuple, Any, Literal

# =============================================================================
# POIDS v2.3 (DÉPRÉCIÉ — utiliser WEIGHTS_V30)
# =============================================================================

WEIGHTS_V23: Dict[str, float] = {
    # Signaux de marché (30% vs 85% en v2.2)
    "smart_money": 0.15,    # → 0% en v3.0
    "insider": 0.10,        # → 0% en v3.0
    "momentum": 0.05,       # → 0% en v3.0
    
    # Fondamentaux Buffett (55% - NOUVEAU)
    "value": 0.30,          # → 45% en v3.0
    "quality": 0.25,        # → 35% en v3.0
    
    # Garde-fou (15% - NOUVEAU)
    "risk": 0.15,           # → 20% en v3.0
}

# Validation
assert abs(sum(WEIGHTS_V23.values()) - 1.0) < 0.001, \
    f"Poids v2.3 doivent sommer à 1.0, got {sum(WEIGHTS_V23.values())}"
assert all(w >= 0 for w in WEIGHTS_V23.values()), \
    "Tous les poids doivent être positifs (risk est inversé, pas négatif)"


# =============================================================================
# SOUS-COMPOSANTES DES FACTEURS (DÉPRÉCIÉ)
# =============================================================================

VALUE_COMPONENTS: Dict[str, float] = {
    "fcf_yield": 0.40,
    "ev_ebit_vs_sector": 0.40,
    "mos_simple": 0.20,
}

VALUE_SCORING_MODE: Literal["absolute", "cross_sectional", "sector_neutral"] = "cross_sectional"

QUALITY_COMPONENTS: Dict[str, float] = {
    "roic_avg": 0.35,
    "margin_stability": 0.25,
    "fcf_growth": 0.20,
    "capital_discipline": 0.20,
}

RISK_COMPONENTS: Dict[str, float] = {
    "leverage_safe": 0.50,
    "coverage_safe": 0.30,
    "volatility_low": 0.20,
}


# =============================================================================
# HARD FILTERS (DÉPRÉCIÉ — utiliser HARD_FILTERS_V30)
# =============================================================================

HARD_FILTERS: Dict[str, float] = {
    "max_debt_equity": 3.0,
    "max_debt_ebitda": 4.0,
    "min_interest_coverage": 2.5,
}


# =============================================================================
# FILTRES DE LIQUIDITÉ (DÉPRÉCIÉ — utiliser LIQUIDITY_V30)
# =============================================================================

LIQUIDITY: Dict[str, float] = {
    "min_market_cap": 2_000_000_000,    # → $10B en v3.0
    "min_adv_usd": 5_000_000,
    "max_position_vs_adv": 0.02,        # → 5% en v3.0
}


# =============================================================================
# CONTRAINTES v2.3 (DÉPRÉCIÉ — utiliser CONSTRAINTS_V30)
# =============================================================================

CONSTRAINTS_V23: Dict[str, float] = {
    "min_positions": 12,        # → 15 en v3.0
    "max_positions": 20,
    "max_weight": 0.12,         # → 10% en v3.0
    "max_sector": 0.30,
    "min_sectors": 4,
    "min_score": 0.40,
    "min_history_years": 5,
}


# =============================================================================
# AUTRES CONFIGS (gardées pour rétrocompatibilité)
# =============================================================================

LOOK_AHEAD: Dict[str, int] = {
    "publication_lag_days": 60,
    "quarterly_lag_days": 45,
}

RISK_MANAGEMENT: Dict[str, float] = {
    "max_dd_target": -0.25,
    "max_dd_warning": -0.20,
    "max_dd_hard": -0.35,
    "max_beta_vs_spy": 1.3,
}

VALIDATION_V23: Dict[str, float] = {
    "min_sharpe": 0.55,
    "min_sortino": 0.70,
    "min_calmar": 0.45,
    "max_turnover_annual": 1.50,
}

BACKTEST_V23: Dict[str, Any] = {
    "rebal_freq": "Q",
    "tc_bps": 12.0,
    "risk_free_rate": 0.045,
    "start_date": "2010-01-01",
    "end_date": "2024-12-31",
}

DATA_BOUNDS: Dict[str, Tuple[float, float]] = {
    "revenue": (0, 1e13),
    "gross_profit": (-1e12, 1e13),
    "ebit": (-1e12, 1e12),
    "ebitda": (-1e12, 1.5e12),
    "net_income": (-1e12, 1e12),
    "fcf": (-5e11, 5e11),
    "capex": (-5e11, 0),
    "total_debt": (0, 5e12),
    "cash": (0, 5e12),
    "equity": (-1e12, 5e12),
    "total_assets": (0, 1e13),
    "shares_outstanding": (1e6, 50e9),
    "interest_expense": (-1e11, 1e11),
    "market_cap": (1e8, 5e13),
}

REQUIRED_FIELDS: List[str] = [
    "revenue",
    "ebit", 
    "net_income",
    "equity",
    "total_debt",
]

SMOKE_TEST_MODE: bool = False

SMOKE_TEST_CONFIG: Dict[str, Any] = {
    "start_date": "2018-01-01",
    "end_date": "2024-12-31",
    "disable_mos": True,
    "disable_fcf_growth": True,
    "disable_capital_disc": True,
    "disable_volatility": True,
}

# Buffett mode (gardé pour rétrocompatibilité)
BUFFETT_FILTERS: Dict[str, Any] = {
    "min_history_years": 7,
    "max_loss_years": 3,
    "ideal_history_years": 10,
    "min_roe_avg": 0.10,
    "min_roic_avg": 0.08,
    "allowed_sectors": [
        "Consumer Staples",
        "Consumer Discretionary",
        "Financials",
        "Industrials",
        "Healthcare",
        "Technology",
        "Communication Services",
        "Energy",
    ],
    "excluded_industries": [
        "Biotechnology",
        "Blank Checks",
        "Shell Companies",
    ],
}

BUFFETT_SCORING: Dict[str, float] = {
    "quality_weight": 0.60,
    "valuation_weight": 0.40,
    "moat_weight": 0.40,
    "cash_quality_weight": 0.25,
    "solidity_weight": 0.20,
    "cap_alloc_weight": 0.15,
}

BUFFETT_PORTFOLIO: Dict[str, Any] = {
    "min_positions": 10,
    "max_positions": 20,
    "max_weight": 0.15,
    "max_sector": 0.35,
    "rebal_freq": "A",
    "sell_score_threshold": 0.35,
    "sell_valuation_ceiling": 35,
    "hold_if_top_n": 40,
}

FACTOR_EXPOSURE_TARGETS: Dict[str, Tuple[float, float]] = {
    "beta_vs_spy": (0.90, 1.15),
    "value_tilt": (0.05, 0.20),
    "quality_tilt": (0.10, 0.30),
    "size_tilt": (-0.15, 0.05),
    "momentum_tilt": (-0.05, 0.10),
}

FACTOR_ETF_PROXIES: Dict[str, str] = {
    "value": "IVE",
    "quality": "QUAL",
    "momentum": "MTUM",
    "low_vol": "SPLV",
    "size_small": "IWM",
    "market": "SPY",
}
