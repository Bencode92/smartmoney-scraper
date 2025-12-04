"""⚠️  [DEPRECATED] Configuration SmartMoney Engine v2.5

╔══════════════════════════════════════════════════════════════════════╗
║  CE FICHIER EST DÉPRÉCIÉ — Utiliser config_v30.py à la place         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Note: v2.5 était une version intermédiaire qui n'a jamais été       ║
║  déployée. Elle a été remplacée par v3.0 "Buffett-Quant".            ║
║                                                                      ║
║  Migration:                                                          ║
║    AVANT:  from config_v25 import WEIGHTS_V25, CONSTRAINTS_V25       ║
║    APRÈS:  from config_v30 import WEIGHTS_V30, CONSTRAINTS_V30       ║
║                                                                      ║
║  Voir MIGRATION_V30.md pour le guide complet.                        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

Différences v2.5 vs v3.0:
- v2.5: Value 40%, Quality 35%, Risk 25%
- v3.0: Value 45%, Quality 35%, Risk 20%
- v3.0: Quality sector-relative + stabilité 5 ans (vs absolue)
- v3.0: Value avec Margin of Safety vs historique

Ce fichier reste disponible pour rétrocompatibilité mais la v2.5
n'a jamais été mise en production.

Date de dépréciation: Décembre 2025
"""

import warnings

# Émettre un warning à l'import
warnings.warn(
    "config_v25 est déprécié (version intermédiaire jamais déployée). "
    "Utiliser config_v30 pour la version Buffett-Quant complète. "
    "Voir MIGRATION_V30.md pour le guide de migration.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Dict, List, Tuple, Any, Literal

# =============================================================================
# POIDS v2.5 (DÉPRÉCIÉ — utiliser WEIGHTS_V30)
# =============================================================================

WEIGHTS_V25: Dict[str, float] = {
    "value": 0.40,          # → 45% en v3.0
    "quality": 0.35,        # = 35% en v3.0
    "risk": 0.25,           # → 20% en v3.0
    "smart_money": 0.00,
    "insider": 0.00,
    "momentum": 0.00,
}

# Validation
assert abs(sum(WEIGHTS_V25.values()) - 1.0) < 0.001, \
    f"Poids v2.5 doivent sommer à 1.0, got {sum(WEIGHTS_V25.values())}"


# =============================================================================
# CONTRAINTES v2.5 (DÉPRÉCIÉ — utiliser CONSTRAINTS_V30)
# =============================================================================

CONSTRAINTS_V25: Dict[str, float] = {
    "min_positions": 15,
    "max_positions": 20,
    "max_weight": 0.10,
    "min_weight": 0.03,
    "max_sector": 0.30,
    "min_sectors": 4,
    "min_score": 0.40,
    "max_top5_weight": 0.40,
    "max_top10_weight": 0.70,
    "min_history_years": 5,
}


# =============================================================================
# HARD FILTERS v2.5 (DÉPRÉCIÉ — utiliser HARD_FILTERS_V30)
# =============================================================================

HARD_FILTERS_V25: Dict[str, float] = {
    "max_debt_equity": 3.0,
    "max_debt_ebitda": 4.0,
    "min_interest_coverage": 2.5,
    "min_roe": 0.05,
}


# =============================================================================
# LIQUIDITÉ v2.5 (DÉPRÉCIÉ — utiliser LIQUIDITY_V30)
# =============================================================================

LIQUIDITY_V25: Dict[str, float] = {
    "min_market_cap": 10_000_000_000,
    "min_adv_usd": 5_000_000,
    "max_position_vs_adv": 0.05,
}


# =============================================================================
# CONFIGS RESTANTES (gardées pour rétrocompatibilité)
# =============================================================================

VALUE_SCORING_V25: Dict[str, Any] = {
    "mode": "cross_sectional",
    "components": {
        "fcf_yield": 0.40,
        "ev_ebit_vs_sector": 0.40,
        "pe_vs_history": 0.20,
    },
    "pe_history_years": 5,
    "pe_discount_target": 0.15,
}

QUALITY_SCORING_V25: Dict[str, Any] = {
    "mode": "sector_relative",
    "components": {
        "roe_sector_rank": 0.30,
        "margin_sector_rank": 0.25,
        "roic_avg_5y": 0.25,
        "stability": 0.20,
    },
    "stability_formula": "1 / (1 + std_roe_5y)",
}

RISK_SCORING_V25: Dict[str, float] = {
    "leverage_safe": 0.40,
    "coverage_safe": 0.30,
    "volatility_low": 0.30,
}

REBALANCING_V25: Dict[str, Any] = {
    "frequency": "Q",
    "max_turnover_annual": 1.00,
    "no_trade_zone": 0.01,
    "transaction_cost_bps": 12,
}

SMART_MONEY_ROLE_V25: Dict[str, Any] = {
    "in_composite": False,
    "role": "indicator",
    "description": "Affiché comme tag informatif, pas dans le score",
    "use_as_filter": False,
    "filter_rule": "Exclure si aucun HF ne détient (optionnel)",
}

INSIDER_ROLE_V25: Dict[str, Any] = {
    "in_composite": False,
    "role": "tie_breaker",
    "description": "À score égal, préférer titres avec achats insiders",
    "tie_breaker_threshold": 0.01,
    "prefer_insider_buys": True,
}

FACTOR_EXPOSURE_TARGETS_V25: Dict[str, Tuple[float, float]] = {
    "beta_vs_spy": (0.90, 1.10),
    "value_tilt": (0.10, 0.25),
    "quality_tilt": (0.15, 0.35),
    "size_tilt": (-0.10, 0.00),
}

BETA_CONTROL_V25: Dict[str, Any] = {
    "controlled": False,
    "monitored": True,
    "target_range": (0.90, 1.10),
    "action_if_outside": "Flag pour review, pas de rebal automatique",
}

RISK_MANAGEMENT_V25: Dict[str, float] = {
    "max_dd_target": -0.25,
    "max_dd_warning": -0.20,
    "max_dd_hard": -0.35,
    "te_expected_range": (0.08, 0.12),
}


def validate_config_v25() -> bool:
    """Valide la cohérence de la config v2.5."""
    errors = []
    
    total_weights = sum(WEIGHTS_V25.values())
    if abs(total_weights - 1.0) > 0.001:
        errors.append(f"Poids ne somment pas à 1.0: {total_weights}")
    
    if CONSTRAINTS_V25["min_positions"] > CONSTRAINTS_V25["max_positions"]:
        errors.append("min_positions > max_positions")
    
    if CONSTRAINTS_V25["min_weight"] > CONSTRAINTS_V25["max_weight"]:
        errors.append("min_weight > max_weight")
    
    if errors:
        for e in errors:
            print(f"❌ {e}")
        return False
    
    print("✅ Config v2.5 validée (mais déprécié — utiliser v3.0)")
    return True


if __name__ == "__main__":
    validate_config_v25()
