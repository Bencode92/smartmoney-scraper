"""Configuration SmartMoney Engine v3.0 — Buffett-Quant

Version unifiée qui intègre la mentalité Buffett DÈS MAINTENANT,
pas dans une roadmap fantôme.

Philosophie v3.0:
"Un modèle quantitatif dont la définition des facteurs reflète
les principes de Buffett : Quality = rentabilité élevée et stable
vs pairs, Value = prix raisonnable vs secteur et historique,
Risk = éviter la perte permanente de capital."

Ce n'est PAS un clone de Buffett.
C'est une traduction quantitative de sa mentalité.

Validé: Session IC ChatGPT + Claude — Décembre 2025
"""

from typing import Dict, List, Tuple, Any

# =============================================================================
# POIDS v3.0 — BUFFETT-QUANT
# =============================================================================

WEIGHTS_V30: Dict[str, float] = {
    # Fondamentaux Buffett (100% du composite)
    "value": 0.45,          # Prix raisonnable (cross-section + MoS)
    "quality": 0.35,        # Great business (sector-relative + stabilité)
    "risk": 0.20,           # Éviter perte permanente de capital
    
    # HORS COMPOSITE — Indicateurs seulement
    "smart_money": 0.00,    # Informatif only
    "insider": 0.00,        # Tie-breaker only
    "momentum": 0.00,       # Supprimé
}

# Validation
assert abs(sum(WEIGHTS_V30.values()) - 1.0) < 0.001, \
    f"Poids v3.0 doivent sommer à 1.0, got {sum(WEIGHTS_V30.values())}"


# =============================================================================
# QUALITY v3.0 — "Great Business dans son secteur"
# =============================================================================
"""
Buffett cherche:
- ROE / ROIC élevés PAR RAPPORT AUX PAIRS
- Marges élevées ET STABLES
- Bilan propre (levier raisonnable)

Ce n'est PAS "ROE > 15% en absolu".
C'est "ROE dans le top de son secteur, de manière durable".
"""

QUALITY_V30: Dict[str, Any] = {
    # Mode de calcul
    "mode": "sector_relative_with_stability",
    "history_years": 5,
    
    # Composantes (somme = 1.0)
    "components": {
        # PROFITABILITÉ RELATIVE (50%)
        # = "Great business vs pairs"
        "roe_sector_rank_5y": 0.20,      # ROE moyen 5 ans, ranké dans le secteur
        "roic_sector_rank_5y": 0.15,     # ROIC moyen 5 ans, ranké dans le secteur
        "margin_sector_rank_5y": 0.15,   # Marge op moyenne 5 ans, rankée secteur
        
        # STABILITÉ (30%)
        # = "Moat durable, pas un one-shot"
        "roe_stability": 0.15,           # 1 / (1 + std(ROE) sur 5 ans)
        "margin_stability": 0.15,        # 1 / (1 + std(marge) sur 5 ans)
        
        # BILAN (20%)
        # = "Pas de fragilité financière"
        "leverage_score": 0.10,          # Bas D/E, bas ND/EBITDA = bon
        "coverage_score": 0.10,          # Coverage élevé = bon
    },
    
    # Formules
    "stability_formula": "1 / (1 + coefficient_variation)",
    "leverage_formula": "1 - rank(D/E) dans univers",
    "coverage_formula": "rank(interest_coverage) dans univers",
}

# Validation Quality
assert abs(sum(QUALITY_V30["components"].values()) - 1.0) < 0.001, \
    "Composantes Quality doivent sommer à 1.0"


# =============================================================================
# VALUE v3.0 — "Prix raisonnable pour ce type de business"
# =============================================================================
"""
Buffett cherche:
- Pas nécessairement les P/E les plus bas
- Un BON business payé à un prix un peu EN-DESSOUS de sa valeur
- Ou de son historique (Margin of Safety)

Ce n'est PAS "deep value = P/E < 10".
C'est "great business at a fair/discounted price".
"""

VALUE_V30: Dict[str, Any] = {
    # Mode de calcul
    "mode": "cross_section_with_margin_of_safety",
    "mos_history_years": 5,  # Historique pour MoS (idéal 10 ans si dispo)
    
    # Composantes (somme = 1.0)
    "components": {
        # VALUE CROSS-SECTIONNELLE (60%)
        # = "Cheap vs pairs du secteur"
        "fcf_yield_sector_rank": 0.25,   # FCF yield ranké dans le secteur
        "ev_ebit_sector_rank": 0.25,     # 1 - rank(EV/EBIT) dans secteur
        "pe_sector_rank": 0.10,          # 1 - rank(P/E) dans secteur
        
        # MARGIN OF SAFETY (40%)
        # = "Moins cher que d'habitude pour CE business"
        "pe_vs_history": 0.20,           # P/E actuel vs P/E moyen 5 ans
        "fcf_yield_vs_history": 0.20,    # FCF yield actuel vs moyenne 5 ans
    },
    
    # Formules MoS
    "pe_discount_formula": "(pe_5y_avg - pe_current) / pe_5y_avg",
    "fcf_premium_formula": "(fcf_yield_current - fcf_yield_5y_avg) / fcf_yield_5y_avg",
    
    # Normalisation
    "mos_normalization": "rank_in_universe",  # Puis norm_cdf pour [0,1]
}

# Validation Value
assert abs(sum(VALUE_V30["components"].values()) - 1.0) < 0.001, \
    "Composantes Value doivent sommer à 1.0"


# =============================================================================
# RISK v3.0 — "Éviter la perte permanente de capital"
# =============================================================================
"""
Ce n'est PAS un facteur "low vol" académique.
C'est une PÉNALISATION des profils susceptibles de générer
une perte PERMANENTE de capital:
- Fort levier
- Drawdowns extrêmes récurrents
- Volatilité excessive

Buffett: "Rule #1: Don't lose money. Rule #2: Don't forget rule #1."
"""

RISK_V30: Dict[str, Any] = {
    # Mode de calcul
    "mode": "permanent_loss_avoidance",
    
    # Composantes (somme = 1.0)
    "components": {
        # BILAN (50%)
        # = "Pas de risque de faillite"
        "leverage_safe": 0.25,           # Bas D/E = bon
        "debt_ebitda_safe": 0.15,        # Bas ND/EBITDA = bon
        "coverage_safe": 0.10,           # Coverage élevé = bon
        
        # DRAWDOWN (30%)
        # = "Pas de chutes catastrophiques"
        "max_dd_5y": 0.20,               # Max drawdown 5 ans (moins = mieux)
        "dd_recovery": 0.10,             # Vitesse de recovery
        
        # VOLATILITÉ (20%)
        # = "Pas trop violent"
        "volatility_annual": 0.20,       # Vol annuelle (moins = mieux)
    },
    
    # Ce score est INVERSÉ: score élevé = FAIBLE risque = BON
    "inverted": True,
}

# Validation Risk
assert abs(sum(RISK_V30["components"].values()) - 1.0) < 0.001, \
    "Composantes Risk doivent sommer à 1.0"


# =============================================================================
# CONTRAINTES v3.0
# =============================================================================

CONSTRAINTS_V30: Dict[str, float] = {
    # Positions
    "min_positions": 15,
    "max_positions": 20,
    
    # Poids par ligne
    "max_weight": 0.10,         # 10% max
    "min_weight": 0.03,         # 3% min (pas de micro-lignes)
    
    # Secteurs
    "max_sector": 0.30,         # 30% max par secteur
    "min_sectors": 4,           # Au moins 4 secteurs
    
    # Score
    "min_score": 0.40,          # Score composite minimum
    
    # Concentration
    "max_top5_weight": 0.40,    # Top 5 ≤ 40%
    "max_top10_weight": 0.70,   # Top 10 ≤ 70%
    
    # Historique requis
    "min_history_years": 5,     # 5 ans d'historique minimum
}


# =============================================================================
# HARD FILTERS v3.0 — Exclusions binaires
# =============================================================================

HARD_FILTERS_V30: Dict[str, float] = {
    # Leverage
    "max_debt_equity": 3.0,         # D/E > 3 = exclu
    "max_debt_ebitda": 4.0,         # ND/EBITDA > 4 = exclu
    
    # Solvabilité
    "min_interest_coverage": 2.5,   # Coverage < 2.5 = exclu
    
    # Rentabilité (soft car géré par sector-relative)
    "min_roe": 0.03,                # ROE < 3% = exclu (très bas)
    # Note: ROE relatif par secteur fait le tri fin
}


# =============================================================================
# LIQUIDITÉ v3.0
# =============================================================================

LIQUIDITY_V30: Dict[str, float] = {
    "min_market_cap": 10_000_000_000,   # $10B minimum (Large Cap)
    "min_adv_usd": 5_000_000,           # $5M ADV minimum
    "max_position_vs_adv": 0.05,        # Position max = 5% de l'ADV
}


# =============================================================================
# REBALANCING v3.0 — "Temps & Discipline"
# =============================================================================
"""
Buffett: Horizon long, faible turnover, pas de "trade factoriel"
tous les quatre matins.
"""

REBALANCING_V30: Dict[str, Any] = {
    "frequency": "Q",               # Trimestriel
    "max_turnover_annual": 0.80,    # 80% max (réduit de 100%)
    "no_trade_zone": 0.01,          # Pas de trade si ajustement < 1%
    "transaction_cost_bps": 12,     # 12 bps par trade
    
    # Règle Buffett: ne pas sortir juste parce que le score bouge
    "hold_if_thesis_intact": True,
    "score_drop_threshold": 0.10,   # Sortir seulement si score baisse > 10%
}


# =============================================================================
# SMART MONEY & INSIDER — INDICATEURS SEULEMENT
# =============================================================================
"""
ChatGPT: "Tu arrêtes d'avoir une schizophrénie 'Buffett dans le discours,
hedge funds & RSI dans la formule'."

Smart Money et Insider = 0% dans le composite.
Ils servent uniquement de tags informatifs ou de tie-breakers.
"""

SMART_MONEY_ROLE_V30: Dict[str, Any] = {
    "in_composite": False,
    "weight": 0.00,
    "role": "indicator_only",
    "description": "Affiché comme tag informatif, JAMAIS dans le score",
}

INSIDER_ROLE_V30: Dict[str, Any] = {
    "in_composite": False,
    "weight": 0.00,
    "role": "tie_breaker",
    "description": "À score égal, préférer titres avec achats insiders récents",
    "tie_breaker_threshold": 0.01,  # Si écart score < 1%
}


# =============================================================================
# FILTRE HUMAIN "BUFFETT" — OÙ TON CERVEAU INTERVIENT
# =============================================================================
"""
Le modèle reste quant, mais TON esprit Buffett intervient à trois moments:

1. FILTRE "JE NE COMPRENDS PAS LE BUSINESS"
   Sur le top 20-30 par score, tu vires:
   - Ce que tu ne peux pas expliquer en 2 phrases
   - Ce qui est trop techno/opaque pour toi

2. LECTURE QUALITATIVE DES TOP POSITIONS
   Top 5-10 par poids, tu lis 10-K / lettres / calls,
   tu vérifies que la culture et le moat collent.

3. REFUS DE SUR-TRADER
   Tu gardes la fréquence trimestrielle,
   tu évites de sortir d'un business juste parce que
   le score bouge un peu, si la thèse reste intacte.

C'est ta VRAIE value ajoutée humaine.
"""

HUMAN_OVERLAY_V30: Dict[str, Any] = {
    "enabled": True,
    
    # Filtre compréhension
    "comprehension_filter": {
        "apply_to_top_n": 30,
        "rule": "Exclure si je ne peux pas expliquer le business en 2 phrases",
    },
    
    # Lecture qualitative
    "qualitative_review": {
        "apply_to_top_n": 10,
        "check": ["moat crédible", "culture saine", "management aligné"],
    },
    
    # Anti-sur-trading
    "anti_overtrade": {
        "hold_if_thesis_intact": True,
        "min_holding_period": "2 trimestres",
    },
}


# =============================================================================
# CE QUE TU DIS AU COMITÉ
# =============================================================================

IC_PITCH_V30 = """
Je ne prétends pas remplacer le jugement de Warren Buffett.

En revanche, j'ai construit un modèle quantitatif dont la définition
des facteurs reflète ses principes:

• QUALITY = rentabilité élevée et stable du capital, par rapport
  aux pairs, avec un bilan solide.

• VALUE = valorisation raisonnable vs secteur et vs l'historique
  propre de la société (Margin of Safety).

• RISK = éviter les profils susceptibles de générer une perte
  permanente de capital.

Le moteur me donne une liste disciplinée de candidats qui respectent
cette logique.

Ensuite, en tant que gérant, j'applique une couche qualitative très
simple: je ne retiens pas un titre que je ne comprends pas, ou qui
ne présente pas un moat crédible selon moi.

Smart Money et Insiders ne sont PAS dans le score.
Ils servent uniquement d'indicateurs informatifs.
"""


# =============================================================================
# VALIDATION FINALE
# =============================================================================

def validate_config_v30() -> bool:
    """Valide la cohérence de la config v3.0."""
    errors = []
    
    # Poids
    total_weights = sum(WEIGHTS_V30.values())
    if abs(total_weights - 1.0) > 0.001:
        errors.append(f"Poids ne somment pas à 1.0: {total_weights}")
    
    # Smart Money et Insider doivent être à 0
    if WEIGHTS_V30["smart_money"] != 0:
        errors.append("Smart Money doit être à 0% en v3.0")
    if WEIGHTS_V30["insider"] != 0:
        errors.append("Insider doit être à 0% en v3.0")
    if WEIGHTS_V30["momentum"] != 0:
        errors.append("Momentum doit être à 0% en v3.0")
    
    # Contraintes cohérentes
    if CONSTRAINTS_V30["min_positions"] > CONSTRAINTS_V30["max_positions"]:
        errors.append("min_positions > max_positions")
    
    if CONSTRAINTS_V30["min_weight"] > CONSTRAINTS_V30["max_weight"]:
        errors.append("min_weight > max_weight")
    
    if errors:
        for e in errors:
            print(f"❌ {e}")
        return False
    
    print("✅ Config v3.0 Buffett-Quant validée")
    return True


if __name__ == "__main__":
    validate_config_v30()
    
    print("\n" + "=" * 50)
    print("🎯 SMARTMONEY v3.0 — BUFFETT-QUANT")
    print("=" * 50)
    print(f"\nPoids: Value {WEIGHTS_V30['value']:.0%}, Quality {WEIGHTS_V30['quality']:.0%}, Risk {WEIGHTS_V30['risk']:.0%}")
    print(f"Smart Money: {WEIGHTS_V30['smart_money']:.0%} (indicateur only)")
    print(f"Insider: {WEIGHTS_V30['insider']:.0%} (tie-breaker only)")
    print(f"\nPositions: {CONSTRAINTS_V30['min_positions']}-{CONSTRAINTS_V30['max_positions']}")
    print(f"Poids: {CONSTRAINTS_V30['min_weight']:.0%}-{CONSTRAINTS_V30['max_weight']:.0%}")
    print(f"Secteur max: {CONSTRAINTS_V30['max_sector']:.0%}")
    print(f"\nTurnover max: {REBALANCING_V30['max_turnover_annual']:.0%}/an")
    print(f"Historique requis: {CONSTRAINTS_V30['min_history_years']} ans")
    print("\n" + "=" * 50)
    print("\n💬 PITCH IC:")
    print(IC_PITCH_V30)
