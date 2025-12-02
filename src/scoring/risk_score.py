"""SmartMoney v2.3 — Risk Score (INVERSÉ)

Score Risk basé sur:
- Leverage Safe (50%): D/E et ND/EBITDA
- Coverage Safe (30%): Interest coverage
- Volatility Low (20%): Volatilité annuelle

⚠️ ATTENTION: Score INVERSÉ
- Score ÉLEVÉ = Risque FAIBLE = BONUS pour le portefeuille
- Score BAS = Risque ÉLEVÉ = PÉNALITÉ

Ceci évite les poids négatifs dans le composite (problème v2.2).

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import RISK_COMPONENTS
except ImportError:
    RISK_COMPONENTS = {
        "leverage_safe": 0.50,
        "coverage_safe": 0.30,
        "volatility_low": 0.20,
    }

logger = logging.getLogger(__name__)


@dataclass
class RiskScore:
    """Résultat du scoring Risk (INVERSÉ)."""
    total: float  # Score élevé = risque faible = bon
    leverage_score: float
    coverage_score: float
    volatility_score: float
    details: Dict[str, float]


class RiskScorer:
    """
    Calcule le score Risk INVERSÉ.
    
    IMPORTANT: Les scores sont INVERSÉS:
    - Score 1.0 = Très sûr (D/E faible, coverage élevé, vol basse)
    - Score 0.0 = Très risqué
    
    Composantes:
    1. Leverage Safe (50%)
       - D/E < 0.3 ET ND/EBITDA < 1 = très sûr (1.0)
       - D/E < 0.5 ET ND/EBITDA < 2 = sûr (0.85)
       - D/E < 1.0 ET ND/EBITDA < 3 = acceptable (0.65)
       - D/E < 1.5 ET ND/EBITDA < 4 = risqué (0.40)
       - D/E < 2.0 = très risqué (0.20)
       - D/E ≥ 2.0 = danger (0.0)
    
    2. Coverage Safe (30%)
       - Coverage > 15 = très sûr (1.0)
       - Coverage > 10 = sûr (0.85)
       - Coverage > 5 = acceptable (0.65)
       - Coverage > 2.5 = limite (0.40)
       - Coverage ≤ 2.5 = danger (0.0)
    
    3. Volatility Low (20%)
       - Vol < 15% = très stable (1.0)
       - Vol < 25% = stable (0.80)
       - Vol < 35% = normal (0.60)
       - Vol < 50% = volatile (0.30)
       - Vol ≥ 50% = très volatile (0.0)
    
    Example:
        >>> scorer = RiskScorer()
        >>> score = scorer.score(row)
        >>> print(f"Risk (inversé): {score.total:.2f}")
        >>> # score élevé = faible risque = bon pour le portefeuille
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: Override des poids par composante
        """
        self.weights = weights or RISK_COMPONENTS
    
    def score(self, row: pd.Series) -> RiskScore:
        """
        Calcule le score Risk INVERSÉ pour une ligne.
        
        Args:
            row: Série avec total_debt, equity, ebit, interest_expense, vol_30d, etc.
        
        Returns:
            RiskScore avec total et composantes (score élevé = sûr)
        """
        details = {}
        
        # === 1. Leverage Safe ===
        leverage_score, leverage_details = self._score_leverage_safe(row)
        details.update(leverage_details)
        details["leverage_score"] = leverage_score
        
        # === 2. Coverage Safe ===
        coverage_score, coverage_val = self._score_coverage_safe(row)
        details["coverage"] = coverage_val
        details["coverage_score"] = coverage_score
        
        # === 3. Volatility Low ===
        vol_score, vol_val = self._score_volatility_low(row)
        details["volatility"] = vol_val
        details["volatility_score"] = vol_score
        
        # === Composite ===
        total = (
            self.weights["leverage_safe"] * leverage_score +
            self.weights["coverage_safe"] * coverage_score +
            self.weights["volatility_low"] * vol_score
        )
        
        return RiskScore(
            total=round(total, 3),
            leverage_score=leverage_score,
            coverage_score=coverage_score,
            volatility_score=vol_score,
            details=details,
        )
    
    def _score_leverage_safe(self, row: pd.Series) -> Tuple[float, Dict]:
        """Score levier (inversé: faible levier = score élevé)."""
        details = {}
        
        # D/E ratio
        total_debt = row.get("total_debt", 0)
        equity = row.get("equity")
        cash = row.get("cash", 0)
        
        if pd.isna(equity) or equity <= 0:
            de_ratio = 3.0  # Pénalité max si pas de données
        else:
            de_ratio = (total_debt or 0) / equity
        
        details["de_ratio"] = round(de_ratio, 2)
        
        # ND/EBITDA
        ebit = row.get("ebit")
        ebitda = row.get("ebitda")
        
        if pd.isna(ebitda):
            ebitda = ebit * 1.2 if not pd.isna(ebit) else None
        
        if ebitda and ebitda > 0:
            net_debt = (total_debt or 0) - (cash or 0)
            nd_ebitda = net_debt / ebitda
        else:
            nd_ebitda = 5.0  # Pénalité si pas de données
        
        details["nd_ebitda"] = round(nd_ebitda, 2)
        
        # Scoring combiné (inversé)
        if de_ratio < 0.3 and nd_ebitda < 1.0:
            score = 1.00
        elif de_ratio < 0.5 and nd_ebitda < 2.0:
            score = 0.85
        elif de_ratio < 1.0 and nd_ebitda < 3.0:
            score = 0.65
        elif de_ratio < 1.5 and nd_ebitda < 4.0:
            score = 0.40
        elif de_ratio < 2.0:
            score = 0.20
        else:
            score = 0.0
        
        return score, details
    
    def _score_coverage_safe(self, row: pd.Series) -> Tuple[float, Optional[float]]:
        """Score coverage (inversé: coverage élevé = score élevé)."""
        ebit = row.get("ebit")
        interest_expense = row.get("interest_expense")
        
        # Essayer d'estimer interest_expense si manquant
        if pd.isna(interest_expense) or interest_expense == 0:
            total_debt = row.get("total_debt", 0)
            if total_debt and total_debt > 0:
                interest_expense = total_debt * 0.05  # Estimer à 5%
            else:
                # Pas de dette = coverage infini = très sûr
                return 1.0, None
        
        if pd.isna(ebit):
            return 0.50, None  # Score neutre si pas de données
        
        coverage = ebit / abs(interest_expense) if interest_expense != 0 else float('inf')
        
        # Scoring (inversé: coverage élevé = bon)
        if coverage > 15:
            score = 1.00
        elif coverage > 10:
            score = 0.85
        elif coverage > 5:
            score = 0.65
        elif coverage > 2.5:
            score = 0.40
        else:
            score = 0.0
        
        return score, round(coverage, 1) if coverage != float('inf') else None
    
    def _score_volatility_low(self, row: pd.Series) -> Tuple[float, Optional[float]]:
        """Score volatilité (inversé: vol basse = score élevé)."""
        vol = row.get("vol_30d")  # En pourcentage
        
        if pd.isna(vol):
            # Fallback sur vol calculée autrement
            vol = row.get("volatility", row.get("vol_annual"))
        
        if pd.isna(vol):
            return 0.50, None  # Score neutre si pas de données
        
        # Convertir en décimal si en pourcentage
        if vol > 1:
            vol_pct = vol
        else:
            vol_pct = vol * 100
        
        # Scoring (inversé: vol basse = bon)
        if vol_pct < 15:
            score = 1.00
        elif vol_pct < 25:
            score = 0.80
        elif vol_pct < 35:
            score = 0.60
        elif vol_pct < 50:
            score = 0.30
        else:
            score = 0.0
        
        return score, round(vol_pct, 1)


def score_risk(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcule le score Risk INVERSÉ pour tout l'univers.
    
    Args:
        df: DataFrame univers
    
    Returns:
        DataFrame avec colonnes score_risk_* ajoutées
        
    Note:
        score_risk élevé = risque faible = BON pour le portefeuille
    """
    scorer = RiskScorer()
    df = df.copy()
    
    scores = []
    for idx, row in df.iterrows():
        result = scorer.score(row)
        scores.append({
            "idx": idx,
            "score_risk": result.total,
            "score_risk_leverage": result.leverage_score,
            "score_risk_coverage": result.coverage_score,
            "score_risk_volatility": result.volatility_score,
        })
    
    scores_df = pd.DataFrame(scores).set_index("idx")
    
    for col in scores_df.columns:
        df[col] = scores_df[col]
    
    logger.info(
        f"Risk scores calculés: moyenne={df['score_risk'].mean():.3f} "
        f"(rappel: score élevé = risque faible)"
    )
    
    return df
