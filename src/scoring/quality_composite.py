"""SmartMoney v2.3 — Quality Composite Scorer

Score Quality basé sur:
- ROIC moyen 5 ans (35%): Rentabilité du capital investi
- Stabilité des marges (25%): Écart-type des marges opérationnelles
- FCF Growth (20%): Croissance du FCF par action
- Capital Discipline (20%): Buybacks + gestion prudente du levier

Philosophie: "A wonderful company at a fair price" — Buffett

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import QUALITY_COMPONENTS
except ImportError:
    QUALITY_COMPONENTS = {
        "roic_avg": 0.35,
        "margin_stability": 0.25,
        "fcf_growth": 0.20,
        "capital_discipline": 0.20,
    }

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Résultat du scoring Quality."""
    total: float
    roic_score: float
    margin_stability_score: float
    fcf_growth_score: float
    capital_discipline_score: float
    details: Dict[str, float]


class QualityScorer:
    """
    Calcule le score Quality composite.
    
    Composantes:
    1. ROIC moyen (5 ans)
       - > 25% = excellent (1.0)
       - > 20% = très bon (0.85)
       - > 15% = bon (0.70)
       - > 10% = correct (0.50)
       - > 5% = faible (0.30)
       - ≤ 5% = mauvais (0.0)
    
    2. Stabilité des marges (écart-type marges op / moyenne)
       - < 0.10 = très stable (1.0)
       - < 0.20 = stable (0.80)
       - < 0.30 = acceptable (0.60)
       - < 0.50 = instable (0.30)
       - ≥ 0.50 = très instable (0.0)
    
    3. FCF Growth (CAGR 5 ans)
       - > 15% = excellent (1.0)
       - > 10% = très bon (0.80)
       - > 5% = bon (0.60)
       - > 0% = stable (0.40)
       - ≤ 0% = déclin (0.0)
    
    4. Capital Discipline
       - Buybacks + D/E < 1 = excellent (1.0)
       - Buybacks OU D/E < 1 = bon (0.70)
       - D/E < 1.5 = acceptable (0.50)
       - D/E < 2 = risqué (0.30)
       - D/E ≥ 2 = mauvais (0.0)
    
    Example:
        >>> scorer = QualityScorer()
        >>> score = scorer.score(row, historical_data)
        >>> print(f"Quality: {score.total:.2f}")
    """
    
    # Seuils ROIC
    ROIC_THRESHOLDS = [
        (0.25, 1.00),   # > 25%
        (0.20, 0.85),   # > 20%
        (0.15, 0.70),   # > 15%
        (0.10, 0.50),   # > 10%
        (0.05, 0.30),   # > 5%
    ]
    
    # Seuils stabilité marges (CV = écart-type / moyenne)
    MARGIN_CV_THRESHOLDS = [
        (0.10, 1.00),   # < 10%
        (0.20, 0.80),   # < 20%
        (0.30, 0.60),   # < 30%
        (0.50, 0.30),   # < 50%
    ]
    
    # Seuils FCF Growth
    FCF_GROWTH_THRESHOLDS = [
        (0.15, 1.00),   # > 15%
        (0.10, 0.80),   # > 10%
        (0.05, 0.60),   # > 5%
        (0.00, 0.40),   # > 0%
    ]
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: Override des poids par composante
        """
        self.weights = weights or QUALITY_COMPONENTS
    
    def score(self, 
              row: pd.Series,
              historical_data: Optional[Dict] = None) -> QualityScore:
        """
        Calcule le score Quality pour une ligne.
        
        Args:
            row: Série avec métriques courantes
            historical_data: Dict avec historique {
                "roic_history": [float],
                "margin_history": [float],
                "fcf_history": [float],
                "shares_history": [float],
            }
        
        Returns:
            QualityScore avec total et composantes
        """
        details = {}
        historical_data = historical_data or {}
        
        # === 1. ROIC moyen ===
        roic_score, roic_avg = self._score_roic(row, historical_data)
        details["roic_avg"] = roic_avg
        details["roic_score"] = roic_score
        
        # === 2. Stabilité des marges ===
        margin_score, margin_cv = self._score_margin_stability(row, historical_data)
        details["margin_cv"] = margin_cv
        details["margin_stability_score"] = margin_score
        
        # === 3. FCF Growth ===
        fcf_growth_score, fcf_cagr = self._score_fcf_growth(row, historical_data)
        details["fcf_cagr"] = fcf_cagr
        details["fcf_growth_score"] = fcf_growth_score
        
        # === 4. Capital Discipline ===
        discipline_score, discipline_details = self._score_capital_discipline(
            row, historical_data
        )
        details["capital_discipline"] = discipline_details
        details["capital_discipline_score"] = discipline_score
        
        # === Composite ===
        total = (
            self.weights["roic_avg"] * roic_score +
            self.weights["margin_stability"] * margin_score +
            self.weights["fcf_growth"] * fcf_growth_score +
            self.weights["capital_discipline"] * discipline_score
        )
        
        return QualityScore(
            total=round(total, 3),
            roic_score=roic_score,
            margin_stability_score=margin_score,
            fcf_growth_score=fcf_growth_score,
            capital_discipline_score=discipline_score,
            details=details,
        )
    
    def _score_roic(self, 
                    row: pd.Series,
                    historical_data: Dict) -> Tuple[float, Optional[float]]:
        """Score ROIC moyen."""
        roic_history = historical_data.get("roic_history", [])
        
        if roic_history and len(roic_history) >= 3:
            roic_avg = np.mean(roic_history)
        else:
            # Fallback: calculer depuis données actuelles
            ebit = row.get("ebit")
            equity = row.get("equity")
            total_debt = row.get("total_debt", 0)
            cash = row.get("cash", 0)
            
            if pd.isna(ebit) or pd.isna(equity):
                return 0.50, None
            
            invested_capital = equity + (total_debt or 0) - (cash or 0)
            if invested_capital <= 0:
                return 0.50, None
            
            # ROIC = EBIT × (1 - tax_rate) / Invested Capital
            # Approximation avec tax_rate = 25%
            nopat = ebit * 0.75
            roic_avg = nopat / invested_capital
        
        # Appliquer les seuils
        for threshold, score in self.ROIC_THRESHOLDS:
            if roic_avg > threshold:
                return score, round(roic_avg * 100, 1)
        
        return 0.0, round(roic_avg * 100, 1) if roic_avg else None
    
    def _score_margin_stability(self, 
                                 row: pd.Series,
                                 historical_data: Dict) -> Tuple[float, Optional[float]]:
        """Score stabilité des marges."""
        margin_history = historical_data.get("margin_history", [])
        
        if margin_history and len(margin_history) >= 3:
            margins = np.array(margin_history)
            mean_margin = np.mean(margins)
            
            if mean_margin > 0:
                cv = np.std(margins) / mean_margin
            else:
                cv = 1.0  # Très instable si moyenne négative
        else:
            # Fallback: utiliser operating_margin actuel
            margin = row.get("operating_margin")
            if pd.isna(margin):
                return 0.50, None
            
            # Sans historique, on suppose stabilité moyenne
            cv = 0.25
        
        # Appliquer les seuils (inversé: CV faible = bon)
        for threshold, score in self.MARGIN_CV_THRESHOLDS:
            if cv < threshold:
                return score, round(cv * 100, 1)
        
        return 0.0, round(cv * 100, 1)
    
    def _score_fcf_growth(self, 
                          row: pd.Series,
                          historical_data: Dict) -> Tuple[float, Optional[float]]:
        """Score croissance FCF."""
        fcf_history = historical_data.get("fcf_history", [])
        shares_history = historical_data.get("shares_history", [])
        
        if fcf_history and len(fcf_history) >= 3:
            # FCF par action si on a les shares
            if shares_history and len(shares_history) == len(fcf_history):
                fcf_per_share = [f/s if s > 0 else 0 for f, s in zip(fcf_history, shares_history)]
            else:
                fcf_per_share = fcf_history
            
            # Calculer CAGR
            start = fcf_per_share[0]
            end = fcf_per_share[-1]
            years = len(fcf_per_share) - 1
            
            if start > 0 and end > 0 and years > 0:
                cagr = (end / start) ** (1 / years) - 1
            elif start <= 0 and end > 0:
                cagr = 0.15  # Retour à la profitabilité = bon
            else:
                cagr = -0.10  # Déclin
        else:
            # Fallback: utiliser FCF actuel vs estimation
            fcf = row.get("fcf")
            revenue = row.get("revenue")
            
            if pd.isna(fcf) or pd.isna(revenue) or revenue <= 0:
                return 0.50, None
            
            fcf_margin = fcf / revenue
            # Estimer la croissance basée sur la marge
            if fcf_margin > 0.15:
                cagr = 0.12
            elif fcf_margin > 0.10:
                cagr = 0.08
            elif fcf_margin > 0.05:
                cagr = 0.04
            else:
                cagr = 0.0
        
        # Appliquer les seuils
        for threshold, score in self.FCF_GROWTH_THRESHOLDS:
            if cagr > threshold:
                return score, round(cagr * 100, 1)
        
        return 0.0, round(cagr * 100, 1) if cagr else None
    
    def _score_capital_discipline(self, 
                                   row: pd.Series,
                                   historical_data: Dict) -> Tuple[float, Dict]:
        """Score discipline du capital."""
        details = {}
        
        # D/E ratio
        total_debt = row.get("total_debt", 0)
        equity = row.get("equity")
        
        if pd.isna(equity) or equity <= 0:
            de_ratio = 2.0  # Pénalité si pas de données
        else:
            de_ratio = (total_debt or 0) / equity
        
        details["de_ratio"] = round(de_ratio, 2)
        
        # Buybacks (shares en baisse)
        shares_history = historical_data.get("shares_history", [])
        has_buybacks = False
        
        if shares_history and len(shares_history) >= 2:
            shares_change = shares_history[-1] / shares_history[0] - 1
            has_buybacks = shares_change < -0.02  # > 2% de réduction
            details["shares_change"] = round(shares_change * 100, 1)
        
        details["has_buybacks"] = has_buybacks
        
        # Scoring
        if has_buybacks and de_ratio < 1.0:
            score = 1.00
        elif has_buybacks or de_ratio < 1.0:
            score = 0.70
        elif de_ratio < 1.5:
            score = 0.50
        elif de_ratio < 2.0:
            score = 0.30
        else:
            score = 0.0
        
        return score, details


def score_quality(
    df: pd.DataFrame,
    historical_data_map: Optional[Dict[str, Dict]] = None,
) -> pd.DataFrame:
    """
    Calcule le score Quality pour tout l'univers.
    
    Args:
        df: DataFrame univers
        historical_data_map: Dict {symbol: {roic_history, margin_history, ...}}
    
    Returns:
        DataFrame avec colonnes score_quality_* ajoutées
    """
    scorer = QualityScorer()
    df = df.copy()
    historical_data_map = historical_data_map or {}
    
    scores = []
    for idx, row in df.iterrows():
        symbol = row.get("symbol", "")
        hist_data = historical_data_map.get(symbol, {})
        
        result = scorer.score(row, hist_data)
        scores.append({
            "idx": idx,
            "score_quality": result.total,
            "score_quality_roic": result.roic_score,
            "score_quality_margin": result.margin_stability_score,
            "score_quality_fcf_growth": result.fcf_growth_score,
            "score_quality_discipline": result.capital_discipline_score,
        })
    
    scores_df = pd.DataFrame(scores).set_index("idx")
    
    for col in scores_df.columns:
        df[col] = scores_df[col]
    
    logger.info(f"Quality scores calculés: moyenne={df['score_quality'].mean():.3f}")
    
    return df
