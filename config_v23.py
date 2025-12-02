"""Configuration SmartMoney Engine v2.3

Extension de config.py avec nouveaux paramètres v2.3.
Importer avec: from config_v23 import *

Changements v2.3:
- Nouveaux poids (smart_money réduit, value/quality/risk ajoutés)
- Hard filters (D/E, coverage, ND/EBITDA)
- Filtres de liquidité
- Contrôle look-ahead

Changements v2.3.1:
- Ajout mode Buffett (filtres, scoring, contraintes portefeuille)

Validé: Claude + GPT - Décembre 2025
"""

from typing import Dict, List, Tuple, Any

# =============================================================================
# POIDS v2.3 (remplace WEIGHTS de config.py)
# =============================================================================

WEIGHTS_V23: Dict[str, float] = {
    # Signaux de marché (30% vs 85% en v2.2)
    "smart_money": 0.15,    # Était 0.45
    "insider": 0.10,        # Était 0.15
    "momentum": 0.05,       # Était 0.25
    
    # Fondamentaux Buffett (55% - NOUVEAU)
    "value": 0.30,          # FCF yield, EV/EBIT, MoS
    "quality": 0.25,        # ROIC, marges, croissance, discipline
    
    # Garde-fou (15% - NOUVEAU)
    "risk": 0.15,           # INVERSÉ: score élevé = faible risque = bonus
}

# Validation
assert abs(sum(WEIGHTS_V23.values()) - 1.0) < 0.001, \
    f"Poids v2.3 doivent sommer à 1.0, got {sum(WEIGHTS_V23.values())}"
assert all(w >= 0 for w in WEIGHTS_V23.values()), \
    "Tous les poids doivent être positifs (risk est inversé, pas négatif)"


# =============================================================================
# SOUS-COMPOSANTES DES NOUVEAUX FACTEURS
# =============================================================================

VALUE_COMPONENTS: Dict[str, float] = {
    "fcf_yield": 0.40,          # Robuste, observable
    "ev_ebit_vs_sector": 0.40,  # Comparable, relatif
    "mos_simple": 0.20,         # P/E vs historique (pas DCF)
}

QUALITY_COMPONENTS: Dict[str, float] = {
    "roic_avg": 0.35,           # Rentabilité du capital (5 ans)
    "margin_stability": 0.25,   # Stabilité des marges op
    "fcf_growth": 0.20,         # Croissance FCF/action
    "capital_discipline": 0.20, # Buybacks + levier prudent
}

RISK_COMPONENTS: Dict[str, float] = {
    "leverage_safe": 0.50,      # D/E, ND/EBITDA
    "coverage_safe": 0.30,      # Interest coverage
    "volatility_low": 0.20,     # Vol annuelle
}


# =============================================================================
# HARD FILTERS (Exclusion binaire - NOUVEAU)
# =============================================================================

HARD_FILTERS: Dict[str, float] = {
    "max_debt_equity": 3.0,         # D/E > 3 = exclu
    "max_debt_ebitda": 4.0,         # ND/EBITDA > 4 = exclu
    "min_interest_coverage": 2.5,   # Coverage < 2.5 = exclu
}


# =============================================================================
# FILTRES DE LIQUIDITÉ (NOUVEAU)
# =============================================================================

LIQUIDITY: Dict[str, float] = {
    "min_market_cap": 2_000_000_000,    # $2B minimum
    "min_adv_usd": 5_000_000,           # $5M ADV minimum
    "max_position_vs_adv": 0.02,        # Position max = 2% de l'ADV
}


# =============================================================================
# CONTRÔLE LOOK-AHEAD (NOUVEAU)
# =============================================================================

LOOK_AHEAD: Dict[str, int] = {
    "publication_lag_days": 60,     # Délai publication 10-K
    "quarterly_lag_days": 45,       # Délai publication 10-Q
}


# =============================================================================
# CONTRAINTES v2.3 (étend CONSTRAINTS de config.py)
# =============================================================================

CONSTRAINTS_V23: Dict[str, float] = {
    # Positions
    "min_positions": 12,        # Était 15
    "max_positions": 20,        # Était 25
    "max_weight": 0.12,         # Était 0.06
    "max_sector": 0.30,
    "min_sectors": 4,
    "min_score": 0.40,          # Était 0.30
    
    # Historique requis
    "min_history_years": 5,
}


# =============================================================================
# GESTION DU RISQUE (NOUVEAU)
# =============================================================================

RISK_MANAGEMENT: Dict[str, float] = {
    # Drawdown
    "max_dd_target": -0.25,     # Objectif
    "max_dd_warning": -0.20,    # Alerte
    "max_dd_hard": -0.35,       # Limite absolue
    
    # Beta (optionnel)
    "max_beta_vs_spy": 1.3,
}


# =============================================================================
# VALIDATION v2.3
# =============================================================================

VALIDATION_V23: Dict[str, float] = {
    "min_sharpe": 0.55,         # Était 0.50
    "min_sortino": 0.70,
    "min_calmar": 0.45,
    "max_turnover_annual": 1.50,  # 150% max
}


# =============================================================================
# BACKTEST v2.3
# =============================================================================

BACKTEST_V23: Dict[str, Any] = {
    "rebal_freq": "Q",          # Trimestriel (était M)
    "tc_bps": 12.0,             # Était 10
    "risk_free_rate": 0.045,
    "start_date": "2010-01-01",
    "end_date": "2024-12-31",
}


# =============================================================================
# DATA VALIDATOR - Bornes acceptables
# =============================================================================

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


# =============================================================================
# MODE SMOKE TEST
# =============================================================================

SMOKE_TEST_MODE: bool = False

SMOKE_TEST_CONFIG: Dict[str, Any] = {
    "start_date": "2018-01-01",
    "end_date": "2024-12-31",
    "disable_mos": True,
    "disable_fcf_growth": True,
    "disable_capital_disc": True,
    "disable_volatility": True,
}


# =============================================================================
# COMPARAISON v2.2 vs v2.3
# =============================================================================

"""
TRANSFORMATION DES POIDS:

              v2.2    v2.3    Δ
              ----    ----    ---
smart_money   0.45    0.15   -67%
insider       0.15    0.10   -33%
momentum      0.25    0.05   -80%
quality       0.15    0.00   remplacé

value         0.00    0.30   NOUVEAU
quality       0.00    0.25   NOUVEAU (différent de v2.2)
risk          0.00    0.15   NOUVEAU
              ----    ----
TOTAL         1.00    1.00

IMPACT ATTENDU:
- Score Buffett: 0.55 → 0.80
- Score Institutionnel: 0.62 → 0.85
- Max Drawdown: < -25% (cible)
"""


# =============================================================================
# BUFFETT MODE v2.3.1 — Configuration séparée style Warren Buffett
# =============================================================================

BUFFETT_FILTERS: Dict[str, Any] = {
    # --- CORE (toujours appliqués en mode Buffett) ---
    "min_history_years": 7,         # Un cycle économique complet
    "max_loss_years": 3,            # Max 3 années de pertes sur 10 ans
    
    # --- PREFERENCES (soft = pénalité, strict = exclusion) ---
    "ideal_history_years": 10,      # Idéal pour évaluer le moat
    "min_roe_avg": 0.10,            # ROE moyen > 10%
    "min_roic_avg": 0.08,           # ROIC moyen > 8%
    
    # --- Cercle de compétence ---
    "allowed_sectors": [
        "Consumer Staples",
        "Consumer Discretionary",
        "Financials",
        "Industrials",
        "Healthcare",
        "Technology",
        "Communication Services",
        "Energy",                   # Buffett a OXY
    ],
    "excluded_industries": [
        "Biotechnology",            # Trop spéculatif, pas de moat prévisible
        "Blank Checks",             # SPACs
        "Shell Companies",
    ],
}

BUFFETT_SCORING: Dict[str, float] = {
    # Score Buffett = Quality × 60% + Valorisation × 40%
    "quality_weight": 0.60,
    "valuation_weight": 0.40,
    
    # Sous-composantes Quality (somme = 1.0)
    "moat_weight": 0.40,            # ROIC + ROE + stabilité marges
    "cash_quality_weight": 0.25,    # FCF/NI ratio + accruals bas
    "solidity_weight": 0.20,        # D/E + coverage + current ratio
    "cap_alloc_weight": 0.15,       # Buybacks + payout ratio
}

BUFFETT_PORTFOLIO: Dict[str, Any] = {
    # Mode conservateur (défaut)
    "min_positions": 10,
    "max_positions": 20,
    "max_weight": 0.15,             # Plus concentré que v2.3 (0.12)
    "max_sector": 0.35,             # Plus tolérant que v2.3 (0.30)
    "rebal_freq": "A",              # Annuel (vs Trimestriel pour v2.3)
    
    # Règles de vente Buffett (faible rotation)
    "sell_score_threshold": 0.35,   # Vendre si score_buffett < 0.35
    "sell_valuation_ceiling": 35,   # Vendre si EV/EBIT > 35
    "hold_if_top_n": 40,            # Ne pas vendre si reste dans top 2×N
}


# Validation Buffett
assert BUFFETT_SCORING["quality_weight"] + BUFFETT_SCORING["valuation_weight"] == 1.0, \
    "Poids Buffett quality + valuation doivent sommer à 1.0"
