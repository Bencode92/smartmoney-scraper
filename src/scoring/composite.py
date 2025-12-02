"""SmartMoney v2.3 — Composite Scorer

Agrégation finale de tous les scores avec les poids v2.3.

Poids v2.3:
- smart_money: 15% (était 45%)
- insider: 10% (était 15%)
- momentum: 5% (était 25%)
- value: 30% (NOUVEAU)
- quality: 25% (NOUVEAU, différent de v2.2)
- risk: 15% (NOUVEAU, inversé)

TOTAL = 100%

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import WEIGHTS_V23
except ImportError:
    WEIGHTS_V23 = {
        "smart_money": 0.15,
        "insider": 0.10,
        "momentum": 0.05,
        "value": 0.30,
        "quality": 0.25,
        "risk": 0.15,
    }

logger = logging.getLogger(__name__)


@dataclass
class CompositeResult:
    """Résultat du scoring composite."""
    score: float
    components: Dict[str, float]
    z_scores: Optional[Dict[str, float]] = None
    buffett_score: Optional[float] = None  # (value + quality + risk) / 3


class CompositeScorer:
    """
    Agrège tous les scores avec les poids v2.3.
    
    Features:
    - Normalisation z-score optionnelle
    - Calcul du Buffett Score pur
    - Validation des poids
    
    Example:
        >>> scorer = CompositeScorer()
        >>> df = scorer.calculate(df)
        >>> print(df[["symbol", "score_composite", "buffett_score"]].head())
    """
    
    # Mapping colonnes → facteurs
    COLUMN_MAP = {
        "smart_money": ["score_sm", "score_smart_money"],
        "insider": ["score_insider"],
        "momentum": ["score_momentum"],
        "value": ["score_value"],
        "quality": ["score_quality"],
        "risk": ["score_risk"],
    }
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        use_zscore: bool = True,
    ):
        """
        Args:
            weights: Override des poids (doit sommer à 1.0)
            use_zscore: Normaliser en z-score avant agrégation
        """
        self.weights = weights or WEIGHTS_V23
        self.use_zscore = use_zscore
        
        # Valider les poids
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Poids doivent sommer à 1.0, got {total}")
        
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("Poids négatifs non autorisés (risk est inversé, pas négatif)")
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le score composite pour tout l'univers.
        
        Args:
            df: DataFrame avec scores par facteur
        
        Returns:
            DataFrame avec score_composite et buffett_score ajoutés
        """
        df = df.copy()
        
        # Trouver les colonnes de scores
        score_cols = {}
        for factor, possible_cols in self.COLUMN_MAP.items():
            for col in possible_cols:
                if col in df.columns:
                    score_cols[factor] = col
                    break
        
        # Vérifier les facteurs manquants
        missing = set(self.weights.keys()) - set(score_cols.keys())
        if missing:
            logger.warning(f"Facteurs manquants (poids ignorés): {missing}")
        
        # Ajuster les poids pour les facteurs disponibles
        available_weights = {k: v for k, v in self.weights.items() if k in score_cols}
        total_available = sum(available_weights.values())
        
        if total_available == 0:
            raise ValueError("Aucun score disponible pour le composite")
        
        # Normaliser les poids disponibles
        normalized_weights = {k: v / total_available for k, v in available_weights.items()}
        
        # === Normalisation z-score ===
        if self.use_zscore:
            for factor, col in score_cols.items():
                mean = df[col].mean()
                std = df[col].std()
                
                if std > 0:
                    df[f"{col}_z"] = (df[col] - mean) / std
                else:
                    df[f"{col}_z"] = 0
            
            # Composite sur z-scores
            df["score_composite"] = sum(
                normalized_weights[factor] * df[f"{score_cols[factor]}_z"]
                for factor in normalized_weights
            ).round(4)
        else:
            # Composite sur scores bruts
            df["score_composite"] = sum(
                normalized_weights[factor] * df[score_cols[factor]]
                for factor in normalized_weights
            ).round(4)
        
        # === Buffett Score pur ===
        buffett_factors = ["value", "quality", "risk"]
        buffett_cols = [score_cols[f] for f in buffett_factors if f in score_cols]
        
        if len(buffett_cols) == 3:
            df["buffett_score"] = df[buffett_cols].mean(axis=1).round(3)
            logger.info(
                f"Buffett score calculé: moyenne={df['buffett_score'].mean():.3f}"
            )
        else:
            df["buffett_score"] = np.nan
            logger.warning(
                f"Buffett score incomplet: seulement {len(buffett_cols)}/3 facteurs"
            )
        
        # === Ranking ===
        df["rank_composite"] = df["score_composite"].rank(ascending=False).astype(int)
        
        if "buffett_score" in df.columns and df["buffett_score"].notna().any():
            df["rank_buffett"] = df["buffett_score"].rank(ascending=False).astype(int)
        
        # Log
        logger.info(
            f"Composite v2.3 calculé: "
            f"moyenne={df['score_composite'].mean():.3f}, "
            f"std={df['score_composite'].std():.3f}"
        )
        
        return df
    
    def get_top_holdings(
        self,
        df: pd.DataFrame,
        n: int = 20,
        sort_by: str = "score_composite",
    ) -> pd.DataFrame:
        """
        Retourne les top N holdings.
        
        Args:
            df: DataFrame avec scores
            n: Nombre de positions
            sort_by: Colonne de tri ("score_composite" ou "buffett_score")
        
        Returns:
            DataFrame trié avec top N
        """
        cols = ["symbol", "company", "sector"]
        score_cols = [
            "score_composite", "buffett_score",
            "score_value", "score_quality", "score_risk",
            "score_sm", "score_insider", "score_momentum",
        ]
        
        available_cols = [c for c in cols + score_cols if c in df.columns]
        
        return (
            df[available_cols]
            .sort_values(sort_by, ascending=False)
            .head(n)
            .reset_index(drop=True)
        )


def calculate_composite_score(
    df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    use_zscore: bool = True,
) -> pd.DataFrame:
    """
    Fonction helper pour calculer le composite.
    
    Args:
        df: DataFrame avec scores par facteur
        weights: Override des poids v2.3
        use_zscore: Normaliser en z-score
    
    Returns:
        DataFrame avec score_composite ajouté
    """
    scorer = CompositeScorer(weights=weights, use_zscore=use_zscore)
    return scorer.calculate(df)


def calculate_all_scores(
    df: pd.DataFrame,
    sector_medians: Optional[Dict[str, float]] = None,
    historical_data_map: Optional[Dict[str, Dict]] = None,
    historical_pe_map: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Pipeline complet: calcule tous les scores et le composite.
    
    Args:
        df: DataFrame univers avec métriques
        sector_medians: Médianes EV/EBIT par secteur
        historical_data_map: Historique par ticker
        historical_pe_map: P/E historique par ticker
    
    Returns:
        DataFrame avec tous les scores
    """
    from .value_composite import score_value
    from .quality_composite import score_quality
    from .risk_score import score_risk
    
    logger.info("=" * 50)
    logger.info("SCORING v2.3 — Pipeline complet")
    logger.info("=" * 50)
    
    # 1. Value
    logger.info("\n1. Scoring Value...")
    df = score_value(df, sector_medians, historical_pe_map)
    
    # 2. Quality
    logger.info("\n2. Scoring Quality...")
    df = score_quality(df, historical_data_map)
    
    # 3. Risk (inversé)
    logger.info("\n3. Scoring Risk (inversé)...")
    df = score_risk(df)
    
    # 4. Composite
    logger.info("\n4. Calcul Composite v2.3...")
    df = calculate_composite_score(df)
    
    logger.info("\n" + "=" * 50)
    logger.info("SCORING TERMINÉ")
    logger.info(f"  Univers: {len(df)} tickers")
    logger.info(f"  Composite: mean={df['score_composite'].mean():.3f}")
    if "buffett_score" in df.columns:
        logger.info(f"  Buffett:   mean={df['buffett_score'].mean():.3f}")
    logger.info("=" * 50)
    
    return df
