"""SmartMoney v2.3 — Value Composite Scorer

Score Value basé sur:
- FCF Yield (40%): Rendement du free cash flow
- EV/EBIT vs Secteur (40%): Valorisation relative
- MoS Simple (20%): Marge de sécurité P/E vs historique

Philosophie: "Price is what you pay, value is what you get" — Buffett

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
    from config_v23 import VALUE_COMPONENTS
except ImportError:
    VALUE_COMPONENTS = {
        "fcf_yield": 0.40,
        "ev_ebit_vs_sector": 0.40,
        "mos_simple": 0.20,
    }

logger = logging.getLogger(__name__)


@dataclass
class ValueScore:
    """Résultat du scoring Value."""
    total: float
    fcf_yield_score: float
    ev_ebit_score: float
    mos_score: float
    details: Dict[str, float]


class ValueScorer:
    """
    Calcule le score Value composite.
    
    Composantes:
    1. FCF Yield = FCF / Market Cap
       - > 8% = excellent (1.0)
       - > 5% = bon (0.75)
       - > 3% = correct (0.50)
       - > 0% = faible (0.25)
       - ≤ 0% = mauvais (0.0)
    
    2. EV/EBIT vs Médiane Sectorielle
       - < 0.6x médiane = très sous-valorisé (1.0)
       - < 0.8x médiane = sous-valorisé (0.80)
       - < 1.0x médiane = fair value (0.60)
       - < 1.2x médiane = légèrement cher (0.40)
       - ≥ 1.2x médiane = cher (0.20)
    
    3. MoS Simple = P/E actuel vs P/E historique médian
       - < 0.7x historique = fort discount (1.0)
       - < 0.85x historique = discount (0.75)
       - < 1.0x historique = fair (0.50)
       - < 1.15x historique = premium (0.25)
       - ≥ 1.15x historique = cher (0.0)
    
    Example:
        >>> scorer = ValueScorer()
        >>> score = scorer.score(row, sector_medians)
        >>> print(f"Value: {score.total:.2f}")
    """
    
    # Seuils FCF Yield
    FCF_YIELD_THRESHOLDS = [
        (0.08, 1.00),   # > 8%
        (0.05, 0.75),   # > 5%
        (0.03, 0.50),   # > 3%
        (0.00, 0.25),   # > 0%
    ]
    
    # Seuils EV/EBIT relatif
    EV_EBIT_THRESHOLDS = [
        (0.60, 1.00),   # < 0.6x médiane
        (0.80, 0.80),   # < 0.8x médiane
        (1.00, 0.60),   # < 1.0x médiane
        (1.20, 0.40),   # < 1.2x médiane
    ]
    
    # Seuils MoS (P/E ratio)
    MOS_THRESHOLDS = [
        (0.70, 1.00),   # < 0.7x historique
        (0.85, 0.75),   # < 0.85x historique
        (1.00, 0.50),   # < 1.0x historique
        (1.15, 0.25),   # < 1.15x historique
    ]
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: Override des poids par composante
        """
        self.weights = weights or VALUE_COMPONENTS
    
    def score(self, 
              row: pd.Series,
              sector_medians: Optional[Dict[str, float]] = None,
              historical_pe: Optional[float] = None) -> ValueScore:
        """
        Calcule le score Value pour une ligne.
        
        Args:
            row: Série avec fcf, market_cap, ev, ebit, pe_ratio, sector
            sector_medians: Dict {sector: median_ev_ebit}
            historical_pe: P/E historique médian du titre
        
        Returns:
            ValueScore avec total et composantes
        """
        details = {}
        
        # === 1. FCF Yield ===
        fcf_yield_score, fcf_yield = self._score_fcf_yield(row)
        details["fcf_yield"] = fcf_yield
        details["fcf_yield_score"] = fcf_yield_score
        
        # === 2. EV/EBIT vs Secteur ===
        ev_ebit_score, ev_ebit_ratio = self._score_ev_ebit(
            row, sector_medians
        )
        details["ev_ebit"] = ev_ebit_ratio
        details["ev_ebit_score"] = ev_ebit_score
        
        # === 3. MoS Simple ===
        mos_score, pe_vs_hist = self._score_mos(row, historical_pe)
        details["pe_vs_historical"] = pe_vs_hist
        details["mos_score"] = mos_score
        
        # === Composite ===
        total = (
            self.weights["fcf_yield"] * fcf_yield_score +
            self.weights["ev_ebit_vs_sector"] * ev_ebit_score +
            self.weights["mos_simple"] * mos_score
        )
        
        return ValueScore(
            total=round(total, 3),
            fcf_yield_score=fcf_yield_score,
            ev_ebit_score=ev_ebit_score,
            mos_score=mos_score,
            details=details,
        )
    
    def _score_fcf_yield(self, row: pd.Series) -> Tuple[float, Optional[float]]:
        """Score le FCF Yield."""
        fcf = row.get("fcf")
        market_cap = row.get("market_cap")
        
        if pd.isna(fcf) or pd.isna(market_cap) or market_cap <= 0:
            return 0.50, None  # Score neutre si données manquantes
        
        fcf_yield = fcf / market_cap
        
        # Appliquer les seuils
        for threshold, score in self.FCF_YIELD_THRESHOLDS:
            if fcf_yield > threshold:
                return score, round(fcf_yield * 100, 2)
        
        return 0.0, round(fcf_yield * 100, 2)
    
    def _score_ev_ebit(self, 
                       row: pd.Series,
                       sector_medians: Optional[Dict[str, float]] = None
                       ) -> Tuple[float, Optional[float]]:
        """Score EV/EBIT vs médiane sectorielle."""
        # Calculer EV
        market_cap = row.get("market_cap", 0)
        total_debt = row.get("total_debt", 0)
        cash = row.get("cash", 0)
        
        if pd.isna(market_cap):
            return 0.50, None
        
        ev = market_cap + (total_debt or 0) - (cash or 0)
        
        # EBIT
        ebit = row.get("ebit")
        if pd.isna(ebit) or ebit <= 0:
            return 0.50, None
        
        ev_ebit = ev / ebit
        
        # Comparer à la médiane sectorielle
        sector = row.get("sector", "Unknown")
        
        if sector_medians and sector in sector_medians:
            median = sector_medians[sector]
            if median > 0:
                ratio_vs_median = ev_ebit / median
                
                for threshold, score in self.EV_EBIT_THRESHOLDS:
                    if ratio_vs_median < threshold:
                        return score, round(ev_ebit, 1)
                
                return 0.20, round(ev_ebit, 1)
        
        # Fallback: seuils absolus si pas de médiane
        absolute_thresholds = [
            (8, 1.00),    # < 8x
            (12, 0.80),   # < 12x
            (16, 0.60),   # < 16x
            (20, 0.40),   # < 20x
        ]
        
        for threshold, score in absolute_thresholds:
            if ev_ebit < threshold:
                return score, round(ev_ebit, 1)
        
        return 0.20, round(ev_ebit, 1)
    
    def _score_mos(self, 
                   row: pd.Series,
                   historical_pe: Optional[float] = None
                   ) -> Tuple[float, Optional[float]]:
        """Score Margin of Safety (P/E vs historique)."""
        pe = row.get("pe_ratio")
        
        # Si P/E non fourni, essayer de le calculer
        if pd.isna(pe):
            price = row.get("td_price", row.get("current_price"))
            eps = row.get("eps")
            
            if not pd.isna(price) and not pd.isna(eps) and eps > 0:
                pe = price / eps
            else:
                return 0.50, None
        
        if pe <= 0:
            return 0.50, None  # P/E négatif = entreprise en perte
        
        # Comparer au P/E historique
        if historical_pe and historical_pe > 0:
            ratio = pe / historical_pe
            
            for threshold, score in self.MOS_THRESHOLDS:
                if ratio < threshold:
                    return score, round(ratio, 2)
            
            return 0.0, round(ratio, 2)
        
        # Fallback: seuils absolus
        absolute_thresholds = [
            (10, 1.00),   # < 10x
            (15, 0.75),   # < 15x
            (20, 0.50),   # < 20x
            (25, 0.25),   # < 25x
        ]
        
        for threshold, score in absolute_thresholds:
            if pe < threshold:
                return score, round(pe, 1)
        
        return 0.0, round(pe, 1)


def score_value(
    df: pd.DataFrame,
    sector_medians: Optional[Dict[str, float]] = None,
    historical_pe_map: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Calcule le score Value pour tout l'univers.
    
    Args:
        df: DataFrame univers
        sector_medians: Dict {sector: median_ev_ebit}
        historical_pe_map: Dict {symbol: historical_pe}
    
    Returns:
        DataFrame avec colonnes score_value_* ajoutées
    """
    scorer = ValueScorer()
    df = df.copy()
    
    # Calculer les médianes sectorielles si non fournies
    if sector_medians is None and "ebit" in df.columns and "sector" in df.columns:
        sector_medians = _calculate_sector_medians(df)
    
    scores = []
    for idx, row in df.iterrows():
        symbol = row.get("symbol", "")
        hist_pe = historical_pe_map.get(symbol) if historical_pe_map else None
        
        result = scorer.score(row, sector_medians, hist_pe)
        scores.append({
            "idx": idx,
            "score_value": result.total,
            "score_value_fcf_yield": result.fcf_yield_score,
            "score_value_ev_ebit": result.ev_ebit_score,
            "score_value_mos": result.mos_score,
        })
    
    scores_df = pd.DataFrame(scores).set_index("idx")
    
    for col in scores_df.columns:
        df[col] = scores_df[col]
    
    logger.info(f"Value scores calculés: moyenne={df['score_value'].mean():.3f}")
    
    return df


def _calculate_sector_medians(df: pd.DataFrame) -> Dict[str, float]:
    """Calcule les médianes EV/EBIT par secteur."""
    medians = {}
    
    for sector in df["sector"].unique():
        sector_df = df[df["sector"] == sector]
        
        if len(sector_df) < 3:  # Minimum 3 peers
            continue
        
        # Calculer EV/EBIT pour le secteur
        ev_ebits = []
        for _, row in sector_df.iterrows():
            market_cap = row.get("market_cap", 0)
            total_debt = row.get("total_debt", 0)
            cash = row.get("cash", 0)
            ebit = row.get("ebit")
            
            if not pd.isna(ebit) and ebit > 0 and not pd.isna(market_cap):
                ev = market_cap + (total_debt or 0) - (cash or 0)
                ev_ebits.append(ev / ebit)
        
        if len(ev_ebits) >= 3:
            medians[sector] = np.median(ev_ebits)
    
    logger.debug(f"Médianes sectorielles EV/EBIT: {medians}")
    
    return medians
