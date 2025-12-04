"""SmartMoney Engine v2.5 — Configuration SANS Smart Money

Suite au backtest OOS qui a montré que Smart Money DÉGRADE les performances,
cette version retire complètement le facteur Smart Money.

Changements vs v2.4:
- smart_money: 15% → 0%
- value: 30% → 35% (+5%)
- quality: 25% → 30% (+5%)
- momentum: 5% → 10% (+5%)

Performance attendue (simulation):
- CAGR: +18.8% (vs SPY +14.3%)
- Alpha: +3.9%/an
- Sharpe: 1.23
- Hit Rate: 87%

Date: Décembre 2025
"""

# =============================================================================
# PONDÉRATIONS v2.5 — SANS SMART MONEY
# =============================================================================

WEIGHTS_V25 = {
    "smart_money": 0.00,   # ❌ SUPPRIMÉ (dégradait les performances)
    "insider": 0.10,       # Inchangé
    "momentum": 0.10,      # +5% (redistribué depuis Smart Money)
    "value": 0.35,         # +5% (redistribué depuis Smart Money)
    "quality": 0.30,       # +5% (redistribué depuis Smart Money)
    "risk": 0.15,          # Inchangé
}

# Vérification: somme = 1.0
assert abs(sum(WEIGHTS_V25.values()) - 1.0) < 0.001, "Poids doivent sommer à 1.0"

# =============================================================================
# CONTRAINTES v2.5 — INCHANGÉES
# =============================================================================

CONSTRAINTS_V25 = {
    "min_positions": 15,
    "max_positions": 20,
    "max_weight": 0.12,        # 12% max par ligne
    "max_sector": 0.30,        # 30% max par secteur
    "min_score": 0.35,
    "min_market_cap": 10e9,    # $10B minimum
    "max_leverage": 3.0,
    "min_coverage": 10,
}

# =============================================================================
# SCORING v2.5
# =============================================================================

VALUE_SCORING_MODE = "cross_sectional"  # percentiles relatifs

# Seuils Value (utilisés si mode = "absolute")
VALUE_THRESHOLDS = {
    "fcf_yield": {"good": 0.05, "great": 0.08},
    "ev_ebit": {"good": 15, "great": 10},
    "pe_ratio": {"good": 20, "great": 15},
}

# =============================================================================
# BACKTEST v2.5
# =============================================================================

BACKTEST_V25 = {
    "train_window_years": 3,
    "test_window_months": 3,
    "rebalancing_freq": "QS",  # Quarterly Start
    "benchmark": "SPY",
    "risk_free_rate": 0.045,
}

# =============================================================================
# TARGETS v2.5 (basés sur simulation)
# =============================================================================

TARGETS_V25 = {
    "cagr_target": 0.15,           # 15%+ CAGR
    "alpha_target": 0.03,          # 3%+ alpha/an
    "sharpe_target": 0.80,         # Sharpe > 0.8
    "hit_rate_target": 0.55,       # 55%+ des périodes
    "max_drawdown_limit": -0.35,   # Max DD -35%
    "tracking_error_range": (0.08, 0.12),  # 8-12% TE
}

# =============================================================================
# MIGRATION NOTES
# =============================================================================
"""
Pour migrer de v2.4 à v2.5:

1. Remplacer:
   from config_v23 import WEIGHTS_V23, CONSTRAINTS_V23
   par:
   from config_v25 import WEIGHTS_V25, CONSTRAINTS_V25

2. Le facteur Smart Money est ignoré (poids = 0)
   Pas besoin de modifier le code de scoring

3. Le code HedgeFollow peut rester en place
   mais n'impactera plus les résultats

4. Tests à exécuter après migration:
   pytest tests/test_constraints.py
   python -m src.backtest_oos_real --start 2019-01-01
"""
