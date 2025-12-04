"""SmartMoney v2.4 — Value Composite Scorer

Score Value avec deux modes:
- MODE ABSOLU (legacy): Seuils fixes (FCF Yield > 8%, P/E < 15x, etc.)
- MODE CROSS-SECTIONNEL (v2.4): Percentiles relatifs à l'univers

Le mode cross-sectionnel résout le problème des scores uniformes (0.7)
observé avec les megacaps du S&P 500 qui ont des profils similaires.

Composantes:
- FCF Yield (40%): Rendement du free cash flow
- EV/EBIT vs Secteur (40%): Valorisation relative
- MoS Simple (20%): Marge de sécurité P/E vs historique

Philosophie: "Price is what you pay, value is what you get" — Buffett

CHANGELOG v2.4:
- Ajout du mode cross-sectionnel (percentiles)
- score_value_cross_sectional() pour distribution uniforme [0, 1]
- Configuration via VALUE_SCORING_MODE dans config_v23.py
- Meilleure discrimination entre les positions

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Tuple, Literal
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import VALUE_COMPONENTS, VALUE_SCORING_MODE
except ImportError:
    VALUE_COMPONENTS = {
        "fcf_yield": 0.40,
        "ev_ebit_vs_sector": 0.40,
        "mos_simple": 0.20,
    }
    VALUE_SCORING_MODE = "cross_sectional"  # "absolute" ou "cross_sectional"

logger = logging.getLogger(__name__)


@dataclass
class ValueScore:
    """Résultat du scoring Value."""
    total: float
    fcf_yield_score: float
    ev_ebit_score: float
    mos_score: float
    details: Dict[str, float]


# =============================================================================
# SCORER ABSOLU (LEGACY)
# =============================================================================

class ValueScorer:
    """
    Calcule le score Value composite avec seuils absolus (legacy).
    
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


# =============================================================================
# SCORER CROSS-SECTIONNEL (v2.4 - NOUVEAU)
# =============================================================================

class ValueScorerCrossSectional:
    """
    Calcule le score Value basé sur les PERCENTILES de l'univers (v2.4).
    
    Avantages vs mode absolu:
    - Distribution uniforme des scores [0, 1]
    - Meilleure discrimination entre les positions similaires
    - Adapté aux univers homogènes (S&P 500 megacaps)
    - Pas de clustering autour de 0.7
    
    Composantes (identiques mais calculées en percentiles):
    1. FCF Yield: Percentile du rendement FCF (plus élevé = meilleur)
    2. EV/EBIT: Percentile inversé (plus bas = meilleur)
    3. P/E Ratio: Percentile inversé (plus bas = meilleur)
    
    Example:
        >>> scorer = ValueScorerCrossSectional()
        >>> df = scorer.score_universe(df)
        >>> print(df["score_value"].describe())
        # Distribution uniforme de 0 à 1
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: Override des poids par composante
        """
        self.weights = weights or VALUE_COMPONENTS
    
    def score_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les scores Value cross-sectionnels pour tout l'univers.
        
        Args:
            df: DataFrame avec fcf, market_cap, ebit, pe_ratio, sector, etc.
        
        Returns:
            DataFrame avec colonnes score_value_* ajoutées
        """
        df = df.copy()
        
        # === 1. Calculer les métriques brutes ===
        df = self._calculate_raw_metrics(df)
        
        # === 2. Calculer les percentiles ===
        df = self._calculate_percentile_scores(df)
        
        # === 3. Calculer le score composite ===
        df["score_value"] = (
            self.weights["fcf_yield"] * df["score_value_fcf_yield"].fillna(0.5) +
            self.weights["ev_ebit_vs_sector"] * df["score_value_ev_ebit"].fillna(0.5) +
            self.weights["mos_simple"] * df["score_value_mos"].fillna(0.5)
        )
        
        df["score_value"] = df["score_value"].round(3)
        
        # Log stats de distribution
        logger.info(
            f"Value scores (cross-sectional): "
            f"mean={df['score_value'].mean():.3f}, "
            f"std={df['score_value'].std():.3f}, "
            f"min={df['score_value'].min():.3f}, "
            f"max={df['score_value'].max():.3f}"
        )
        
        return df
    
    def _calculate_raw_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule les métriques Value brutes."""
        
        # --- FCF Yield ---
        if "fcf" in df.columns and "market_cap" in df.columns:
            # Éviter division par zéro
            df["_fcf_yield"] = df.apply(
                lambda r: r["fcf"] / r["market_cap"] 
                if pd.notna(r["fcf"]) and pd.notna(r["market_cap"]) and r["market_cap"] > 0 
                else np.nan,
                axis=1
            )
            # Clipper les valeurs extrêmes
            df["_fcf_yield"] = df["_fcf_yield"].clip(-0.50, 0.50)
        else:
            df["_fcf_yield"] = np.nan
        
        # --- EV/EBIT ---
        if "ebit" in df.columns and "market_cap" in df.columns:
            df["_ev"] = (
                df["market_cap"].fillna(0) + 
                df["total_debt"].fillna(0) - 
                df["cash"].fillna(0)
            )
            df["_ev_ebit"] = df.apply(
                lambda r: r["_ev"] / r["ebit"] 
                if pd.notna(r["ebit"]) and r["ebit"] > 0 
                else np.nan,
                axis=1
            )
            # Clipper les valeurs extrêmes
            df["_ev_ebit"] = df["_ev_ebit"].clip(0, 100)
        else:
            df["_ev_ebit"] = np.nan
        
        # --- P/E Ratio ---
        if "pe_ratio" in df.columns:
            df["_pe_ratio"] = df["pe_ratio"].copy()
        elif "td_price" in df.columns and "eps" in df.columns:
            df["_pe_ratio"] = df.apply(
                lambda r: r["td_price"] / r["eps"] 
                if pd.notna(r["td_price"]) and pd.notna(r["eps"]) and r["eps"] > 0 
                else np.nan,
                axis=1
            )
        else:
            df["_pe_ratio"] = np.nan
        
        # Clipper P/E
        df["_pe_ratio"] = df["_pe_ratio"].clip(0, 200)
        
        return df
    
    def _calculate_percentile_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convertit les métriques brutes en scores percentiles."""
        
        # --- FCF Yield: plus élevé = meilleur ---
        if df["_fcf_yield"].notna().sum() >= 5:
            df["score_value_fcf_yield"] = df["_fcf_yield"].rank(pct=True)
        else:
            df["score_value_fcf_yield"] = 0.5
        
        # --- EV/EBIT: plus bas = meilleur (inverser le percentile) ---
        if df["_ev_ebit"].notna().sum() >= 5:
            df["score_value_ev_ebit"] = 1 - df["_ev_ebit"].rank(pct=True)
        else:
            df["score_value_ev_ebit"] = 0.5
        
        # --- P/E: plus bas = meilleur (inverser le percentile) ---
        if df["_pe_ratio"].notna().sum() >= 5:
            df["score_value_mos"] = 1 - df["_pe_ratio"].rank(pct=True)
        else:
            df["score_value_mos"] = 0.5
        
        # Nettoyer les colonnes temporaires
        temp_cols = ["_fcf_yield", "_ev_ebit", "_ev", "_pe_ratio"]
        df = df.drop(columns=[c for c in temp_cols if c in df.columns], errors="ignore")
        
        return df


# =============================================================================
# SCORER CROSS-SECTIONNEL PAR SECTEUR (BONUS)
# =============================================================================

class ValueScorerSectorNeutral:
    """
    Calcule le score Value en percentiles INTRA-SECTEUR.
    
    Avantage: Compare chaque titre à ses pairs du même secteur,
    évitant les biais sectoriels (ex: Tech a naturellement des P/E plus élevés).
    
    Example:
        >>> scorer = ValueScorerSectorNeutral()
        >>> df = scorer.score_universe(df)
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or VALUE_COMPONENTS
    
    def score_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score Value par percentiles intra-secteur."""
        df = df.copy()
        
        # Calculer les métriques brutes
        scorer_cs = ValueScorerCrossSectional(self.weights)
        df = scorer_cs._calculate_raw_metrics(df)
        
        # Calculer les percentiles PAR SECTEUR
        if "sector" in df.columns:
            df["score_value_fcf_yield"] = df.groupby("sector")["_fcf_yield"].rank(pct=True)
            df["score_value_ev_ebit"] = 1 - df.groupby("sector")["_ev_ebit"].rank(pct=True)
            df["score_value_mos"] = 1 - df.groupby("sector")["_pe_ratio"].rank(pct=True)
        else:
            # Fallback global
            df["score_value_fcf_yield"] = df["_fcf_yield"].rank(pct=True)
            df["score_value_ev_ebit"] = 1 - df["_ev_ebit"].rank(pct=True)
            df["score_value_mos"] = 1 - df["_pe_ratio"].rank(pct=True)
        
        # Remplir les NaN avec 0.5 (score neutre)
        for col in ["score_value_fcf_yield", "score_value_ev_ebit", "score_value_mos"]:
            df[col] = df[col].fillna(0.5)
        
        # Composite
        df["score_value"] = (
            self.weights["fcf_yield"] * df["score_value_fcf_yield"] +
            self.weights["ev_ebit_vs_sector"] * df["score_value_ev_ebit"] +
            self.weights["mos_simple"] * df["score_value_mos"]
        )
        
        df["score_value"] = df["score_value"].round(3)
        
        # Nettoyer
        temp_cols = ["_fcf_yield", "_ev_ebit", "_ev", "_pe_ratio"]
        df = df.drop(columns=[c for c in temp_cols if c in df.columns], errors="ignore")
        
        logger.info(
            f"Value scores (sector-neutral): "
            f"mean={df['score_value'].mean():.3f}, "
            f"std={df['score_value'].std():.3f}"
        )
        
        return df


# =============================================================================
# FONCTIONS PRINCIPALES
# =============================================================================

def score_value(
    df: pd.DataFrame,
    sector_medians: Optional[Dict[str, float]] = None,
    historical_pe_map: Optional[Dict[str, float]] = None,
    mode: Literal["absolute", "cross_sectional", "sector_neutral"] = None,
) -> pd.DataFrame:
    """
    Calcule le score Value pour tout l'univers.
    
    Args:
        df: DataFrame univers
        sector_medians: Dict {sector: median_ev_ebit} (mode absolu uniquement)
        historical_pe_map: Dict {symbol: historical_pe} (mode absolu uniquement)
        mode: Mode de scoring
            - "absolute": Seuils fixes (legacy)
            - "cross_sectional": Percentiles globaux (v2.4, défaut)
            - "sector_neutral": Percentiles intra-secteur
    
    Returns:
        DataFrame avec colonnes score_value_* ajoutées
    """
    # Déterminer le mode
    if mode is None:
        mode = VALUE_SCORING_MODE
    
    logger.info(f"Score Value mode: {mode}")
    
    if mode == "cross_sectional":
        scorer = ValueScorerCrossSectional()
        return scorer.score_universe(df)
    
    elif mode == "sector_neutral":
        scorer = ValueScorerSectorNeutral()
        return scorer.score_universe(df)
    
    else:  # mode == "absolute" (legacy)
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
        
        logger.info(f"Value scores (absolute): mean={df['score_value'].mean():.3f}")
        
        return df


def score_value_cross_sectional(df: pd.DataFrame) -> pd.DataFrame:
    """
    Raccourci pour score_value en mode cross-sectionnel.
    
    Usage:
        >>> df = score_value_cross_sectional(df)
        >>> print(df["score_value"].describe())
    """
    return score_value(df, mode="cross_sectional")


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


# =============================================================================
# DIAGNOSTIC DE DISTRIBUTION
# =============================================================================

def diagnose_value_distribution(df: pd.DataFrame) -> Dict:
    """
    Diagnostique la distribution des scores Value.
    
    Utile pour vérifier que le mode cross-sectionnel améliore
    la discrimination par rapport au mode absolu.
    
    Returns:
        Dict avec statistiques de distribution
    """
    if "score_value" not in df.columns:
        return {"error": "score_value non calculé"}
    
    scores = df["score_value"].dropna()
    
    diagnosis = {
        "count": len(scores),
        "mean": round(scores.mean(), 3),
        "std": round(scores.std(), 3),
        "min": round(scores.min(), 3),
        "max": round(scores.max(), 3),
        "median": round(scores.median(), 3),
        "q25": round(scores.quantile(0.25), 3),
        "q75": round(scores.quantile(0.75), 3),
        "iqr": round(scores.quantile(0.75) - scores.quantile(0.25), 3),
        "unique_values": len(scores.unique()),
        "clustering_warning": None,
    }
    
    # Détecter le clustering (problème v2.3)
    if diagnosis["std"] < 0.10:
        diagnosis["clustering_warning"] = (
            f"⚠️ Scores très concentrés (std={diagnosis['std']:.3f}). "
            f"Considérer le mode cross_sectional."
        )
    
    if diagnosis["iqr"] < 0.15:
        diagnosis["clustering_warning"] = (
            f"⚠️ Faible dispersion (IQR={diagnosis['iqr']:.3f}). "
            f"Considérer le mode cross_sectional."
        )
    
    return diagnosis
