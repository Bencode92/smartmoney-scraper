"""Configuration SmartMoney Engine v2.5 — Noyau Institutionnel Propre

Version "IC Ready" avec uniquement les facteurs défendables.

Changements v2.4 → v2.5:
- Smart Money: 15% → 0% (relégué en indicateur)
- Insider: 10% → 0% (relégué en tie-breaker)
- Momentum: 5% → 0% (supprimé)
- Value: 30% → 40%
- Quality: 25% → 35%
- Risk: 15% → 25%

Philosophie v2.5:
"Portefeuille Large Cap US Quality/Value, construit de manière
equal-weight + tilt, sans prétention d'edge Smart Money."

Validé: Session IC ChatGPT + Claude — Décembre 2025
"""

from typing import Dict, List, Tuple, Any, Literal

# =============================================================================
# POIDS v2.5 — NOYAU DÉFENDABLE UNIQUEMENT
# =============================================================================

WEIGHTS_V25: Dict[str, float] = {
    # Fondamentaux (100% du composite)
    "value": 0.40,          # FCF yield, EV/EBIT, P/E relatif
    "quality": 0.35,        # ROIC, marges, stabilité, discipline
    "risk": 0.25,           # Leverage, coverage, volatilité (INVERSÉ)
    
    # Signaux de marché — EXCLUS du composite (tags seulement)
    "smart_money": 0.00,    # Indicateur, pas dans le score
    "insider": 0.00,        # Tie-breaker seulement
    "momentum": 0.00,       # Supprimé
}

# Validation
assert abs(sum(WEIGHTS_V25.values()) - 1.0) < 0.001, \
    f"Poids v2.5 doivent sommer à 1.0, got {sum(WEIGHTS_V25.values())}"


# =============================================================================
# CONTRAINTES v2.5 — RENFORCÉES
# =============================================================================

CONSTRAINTS_V25: Dict[str, float] = {
    # Positions
    "min_positions": 15,
    "max_positions": 20,
    
    # Poids par ligne
    "max_weight": 0.10,         # Réduit de 12% à 10%
    "min_weight": 0.03,         # NOUVEAU: éviter micro-lignes
    
    # Secteurs
    "max_sector": 0.30,
    "min_sectors": 4,
    
    # Score
    "min_score": 0.40,
    
    # Concentration (NOUVEAU)
    "max_top5_weight": 0.40,    # Top 5 ≤ 40%
    "max_top10_weight": 0.70,   # Top 10 ≤ 70%
    
    # Historique
    "min_history_years": 5,
}


# =============================================================================
# HARD FILTERS v2.5 — Exclusion binaire
# =============================================================================

HARD_FILTERS_V25: Dict[str, float] = {
    # Leverage
    "max_debt_equity": 3.0,         # D/E > 3 = exclu
    "max_debt_ebitda": 4.0,         # ND/EBITDA > 4 = exclu
    
    # Solvabilité
    "min_interest_coverage": 2.5,   # Coverage < 2.5 = exclu
    
    # Rentabilité (assoupli vs v2.4)
    "min_roe": 0.05,                # ROE < 5% = exclu (était 8%)
    # Note: ROE relatif par secteur géré dans le score, pas en hard filter
}


# =============================================================================
# LIQUIDITÉ v2.5
# =============================================================================

LIQUIDITY_V25: Dict[str, float] = {
    "min_market_cap": 10_000_000_000,   # $10B minimum (renforcé)
    "min_adv_usd": 5_000_000,           # $5M ADV minimum
    "max_position_vs_adv": 0.05,        # Position max = 5% de l'ADV
}


# =============================================================================
# SCORING VALUE v2.5
# =============================================================================

VALUE_SCORING_V25: Dict[str, Any] = {
    # Mode de calcul
    "mode": "cross_sectional",  # Percentiles globaux
    
    # Composantes
    "components": {
        "fcf_yield": 0.40,          # Cross-sectionnel
        "ev_ebit_vs_sector": 0.40,  # Relatif au secteur
        "pe_vs_history": 0.20,      # vs historique propre (MoS simple)
    },
    
    # Seuils pour PE vs historique
    "pe_history_years": 5,
    "pe_discount_target": 0.15,  # 15% de discount = score max
}


# =============================================================================
# SCORING QUALITY v2.5
# =============================================================================

QUALITY_SCORING_V25: Dict[str, Any] = {
    # Mode de calcul
    "mode": "sector_relative",  # Percentiles intra-secteur
    
    # Composantes
    "components": {
        "roe_sector_rank": 0.30,        # ROE vs pairs secteur
        "margin_sector_rank": 0.25,     # Marge op vs pairs secteur
        "roic_avg_5y": 0.25,            # ROIC moyen 5 ans
        "stability": 0.20,              # Stabilité ROE/marges
    },
    
    # Stabilité = pénaliser la volatilité
    "stability_formula": "1 / (1 + std_roe_5y)",
}


# =============================================================================
# SCORING RISK v2.5 (inversé: score élevé = faible risque)
# =============================================================================

RISK_SCORING_V25: Dict[str, float] = {
    "leverage_safe": 0.40,      # D/E, ND/EBITDA bas
    "coverage_safe": 0.30,      # Interest coverage élevé
    "volatility_low": 0.30,     # Volatilité annuelle basse
}


# =============================================================================
# REBALANCING & TURNOVER v2.5
# =============================================================================

REBALANCING_V25: Dict[str, Any] = {
    "frequency": "Q",               # Trimestriel
    "max_turnover_annual": 1.00,    # 100% max (réduit de 150%)
    "no_trade_zone": 0.01,          # Pas de trade si ajustement < 1%
    "transaction_cost_bps": 12,     # 12 bps par trade
}


# =============================================================================
# SMART MONEY & INSIDER — HORS COMPOSITE
# =============================================================================

SMART_MONEY_ROLE_V25: Dict[str, Any] = {
    "in_composite": False,
    "role": "indicator",
    "description": "Affiché comme tag informatif, pas dans le score",
    
    # Utilisation optionnelle comme filtre léger
    "use_as_filter": False,
    "filter_rule": "Exclure si aucun HF ne détient (optionnel)",
}

INSIDER_ROLE_V25: Dict[str, Any] = {
    "in_composite": False,
    "role": "tie_breaker",
    "description": "À score égal, préférer titres avec achats insiders",
    
    # Règle de tie-breaker
    "tie_breaker_threshold": 0.01,  # Si écart score < 1%
    "prefer_insider_buys": True,
}


# =============================================================================
# EXPOSITIONS FACTORIELLES CIBLES v2.5
# =============================================================================

FACTOR_EXPOSURE_TARGETS_V25: Dict[str, Tuple[float, float]] = {
    # (min, max) — fourchettes cibles
    "beta_vs_spy": (0.90, 1.10),        # Resserré
    "value_tilt": (0.10, 0.25),         # Tilt Value assumé
    "quality_tilt": (0.15, 0.35),       # Tilt Quality assumé
    "size_tilt": (-0.10, 0.00),         # Biais Large Cap
}

# Note: Beta est SURVEILLÉ ex-post, pas contrôlé explicitement
BETA_CONTROL_V25: Dict[str, Any] = {
    "controlled": False,
    "monitored": True,
    "target_range": (0.90, 1.10),
    "action_if_outside": "Flag pour review, pas de rebal automatique",
}


# =============================================================================
# GESTION DU RISQUE v2.5
# =============================================================================

RISK_MANAGEMENT_V25: Dict[str, float] = {
    # Drawdown
    "max_dd_target": -0.25,
    "max_dd_warning": -0.20,
    "max_dd_hard": -0.35,
    
    # Tracking Error (non ciblé, juste surveillé)
    "te_expected_range": (0.08, 0.12),  # 8-12%
}


# =============================================================================
# COMPARAISON v2.4 → v2.5
# =============================================================================

"""
TRANSFORMATION DES POIDS:

              v2.4    v2.5    Δ       Raison
              ----    ----    ---     ------
smart_money   0.15    0.00    -15%    Non prouvé, relégué en indicateur
insider       0.10    0.00    -10%    Signal faible, relégué en tie-breaker
momentum      0.05    0.00    -5%     Supprimé (pas de vue)
value         0.30    0.40    +10%    Renforcé (noyau)
quality       0.25    0.35    +10%    Renforcé (noyau)
risk          0.15    0.25    +10%    Renforcé (garde-fou)
              ----    ----
TOTAL         1.00    1.00

CHANGEMENTS CLÉS v2.5:
1. Composite = uniquement Value + Quality + Risk
2. Smart Money/Insider hors composite (indicateurs seulement)
3. Contraintes renforcées (max_weight 10%, min_weight 3%)
4. Turnover réduit (100% vs 150%)
5. Market cap minimum relevé ($10B vs $2B)
6. Beta surveillé, pas contrôlé

PHILOSOPHIE:
"Noyau institutionnel propre, défendable devant un comité,
sans prétention d'edge Smart Money non prouvé."

ROADMAP v2.6 (future):
- Quality sector-relative + stabilité 5-10 ans
- Value avec Margin of Safety vs historique
- Métriques ajustées par secteur
"""


# =============================================================================
# VALIDATION FINALE
# =============================================================================

def validate_config_v25() -> bool:
    """Valide la cohérence de la config v2.5."""
    errors = []
    
    # Poids
    total_weights = sum(WEIGHTS_V25.values())
    if abs(total_weights - 1.0) > 0.001:
        errors.append(f"Poids ne somment pas à 1.0: {total_weights}")
    
    # Contraintes cohérentes
    if CONSTRAINTS_V25["min_positions"] > CONSTRAINTS_V25["max_positions"]:
        errors.append("min_positions > max_positions")
    
    if CONSTRAINTS_V25["min_weight"] > CONSTRAINTS_V25["max_weight"]:
        errors.append("min_weight > max_weight")
    
    # Top concentration
    if CONSTRAINTS_V25["max_top5_weight"] > CONSTRAINTS_V25["max_top10_weight"]:
        errors.append("max_top5 > max_top10")
    
    # Smart Money / Insider hors composite
    if WEIGHTS_V25["smart_money"] != 0 or WEIGHTS_V25["insider"] != 0:
        errors.append("Smart Money et Insider doivent être à 0% en v2.5")
    
    if errors:
        for e in errors:
            print(f"❌ {e}")
        return False
    
    print("✅ Config v2.5 validée")
    return True


if __name__ == "__main__":
    validate_config_v25()
    
    print("\n📊 RÉSUMÉ CONFIG v2.5")
    print("=" * 40)
    print(f"Poids: Value {WEIGHTS_V25['value']:.0%}, Quality {WEIGHTS_V25['quality']:.0%}, Risk {WEIGHTS_V25['risk']:.0%}")
    print(f"Smart Money: {WEIGHTS_V25['smart_money']:.0%} (indicateur)")
    print(f"Insider: {WEIGHTS_V25['insider']:.0%} (tie-breaker)")
    print(f"Positions: {CONSTRAINTS_V25['min_positions']}-{CONSTRAINTS_V25['max_positions']}")
    print(f"Poids: {CONSTRAINTS_V25['min_weight']:.0%}-{CONSTRAINTS_V25['max_weight']:.0%}")
    print(f"Secteur max: {CONSTRAINTS_V25['max_sector']:.0%}")
    print(f"Market cap min: ${LIQUIDITY_V25['min_market_cap']/1e9:.0f}B")
