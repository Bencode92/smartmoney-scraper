"""SmartMoney v2.3.1 — Composite Scorer

Agrégation finale de tous les scores avec les poids v2.3.

Poids v2.3:
- smart_money: 15% (était 45%)
- insider: 10% (était 15%)
- momentum: 5% (était 25%)
- value: 30% (NOUVEAU)
- quality: 25% (NOUVEAU, différent de v2.2)
- risk: 15% (NOUVEAU, inversé)

TOTAL = 100%

v2.3.1: Ajout score_buffett séparé (60% qualité + 40% valorisation)

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
    from config_v23 import WEIGHTS_V23, BUFFETT_SCORING
except ImportError:
    WEIGHTS_V23 = {
        "smart_money": 0.15,
        "insider": 0.10,
        "momentum": 0.05,
        "value": 0.30,
        "quality": 0.25,
        "risk": 0.15,
    }
    BUFFETT_SCORING = {
        "quality_weight": 0.60,
        "valuation_weight": 0.40,
        "moat_weight": 0.40,
        "cash_quality_weight": 0.25,
        "solidity_weight": 0.20,
        "cap_alloc_weight": 0.15,
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


# =============================================================================
# BUFFETT SCORING v2.3.1 — Score séparé style Warren Buffett
# =============================================================================

def calculate_buffett_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule le score Buffett séparé (indépendant de score_composite).
    
    Formule:
        score_buffett = 60% × score_quality_buffett + 40% × score_valo_buffett
    
    Où score_quality_buffett =
        40% × moat (ROIC + ROE + stabilité)
        25% × cash_quality (FCF/NI + accruals bas)
        20% × solidity (réutilise score_risk existant)
        15% × cap_alloc (réutilise capital_discipline existant)
    
    Et score_valo_buffett = score_value existant (pas de recalcul).
    
    Colonnes requises (optionnelles avec fallback):
        - roic_avg ou roic
        - roe_avg ou roe
        - margin_stability ou score_quality
        - fcf_ni_ratio (calculé par compute_buffett_features)
        - accruals (calculé par compute_buffett_features)
        - score_risk (calculé par score_risk)
        - capital_discipline ou score_quality
        - score_value
    
    Colonnes ajoutées:
        - score_moat_buffett
        - score_cash_buffett
        - score_quality_buffett
        - score_valo_buffett
        - score_buffett
        - rank_buffett_v2
    
    Args:
        df: DataFrame avec métriques et scores existants
    
    Returns:
        DataFrame avec colonnes Buffett ajoutées
    
    Example:
        >>> from src.filters.buffett_filters import compute_buffett_features
        >>> df = compute_buffett_features(df)  # Calcule accruals, fcf_ni_ratio
        >>> df = calculate_buffett_score(df)
        >>> print(df[["symbol", "score_buffett", "score_composite"]].head())
    """
    df = df.copy()
    
    # Récupérer les poids depuis config
    quality_weight = BUFFETT_SCORING.get("quality_weight", 0.60)
    valo_weight = BUFFETT_SCORING.get("valuation_weight", 0.40)
    
    moat_w = BUFFETT_SCORING.get("moat_weight", 0.40)
    cash_w = BUFFETT_SCORING.get("cash_quality_weight", 0.25)
    solid_w = BUFFETT_SCORING.get("solidity_weight", 0.20)
    cap_w = BUFFETT_SCORING.get("cap_alloc_weight", 0.15)
    
    # =========================================================================
    # QUALITÉ BUFFETT (60%)
    # =========================================================================
    
    # 1. Moat Score (40% de qualité)
    df["score_moat_buffett"] = _score_moat(df)
    
    # 2. Cash Quality Score (25% de qualité)
    df["score_cash_buffett"] = _score_cash_quality(df)
    
    # 3. Solidity Score (20% de qualité) — réutilise score_risk existant
    if "score_risk" in df.columns:
        solidity = df["score_risk"].fillna(0.5)
    else:
        solidity = pd.Series(0.5, index=df.index)
        logger.debug("score_risk absent → solidity = 0.5")
    
    # 4. Capital Allocation Score (15% de qualité)
    cap_alloc = _get_cap_alloc_score(df)
    
    # Agrégation qualité
    df["score_quality_buffett"] = (
        moat_w * df["score_moat_buffett"] +
        cash_w * df["score_cash_buffett"] +
        solid_w * solidity +
        cap_w * cap_alloc
    ).clip(0, 1).round(3)
    
    # =========================================================================
    # VALORISATION BUFFETT (40%)
    # =========================================================================
    # Réutilise score_value existant (pas de recalcul)
    
    if "score_value" in df.columns:
        df["score_valo_buffett"] = df["score_value"].fillna(0.5)
    else:
        df["score_valo_buffett"] = 0.5
        logger.warning("score_value absent → score_valo_buffett = 0.5")
    
    # =========================================================================
    # SCORE BUFFETT TOTAL
    # =========================================================================
    
    df["score_buffett"] = (
        quality_weight * df["score_quality_buffett"] +
        valo_weight * df["score_valo_buffett"]
    ).round(3)
    
    # Ranking
    df["rank_buffett_v2"] = df["score_buffett"].rank(ascending=False).astype(int)
    
    # Stats
    mean_score = df["score_buffett"].mean()
    std_score = df["score_buffett"].std()
    
    logger.info(
        f"Score Buffett v2.3.1 calculé: "
        f"mean={mean_score:.3f}, std={std_score:.3f}, "
        f"min={df['score_buffett'].min():.3f}, max={df['score_buffett'].max():.3f}"
    )
    
    return df


def _score_moat(df: pd.DataFrame) -> pd.Series:
    """
    Calcule le score Moat (avantage concurrentiel durable).
    
    Composantes:
    - ROIC niveau (40%): ROIC > 15% = excellent
    - ROE niveau (30%): ROE > 20% = excellent
    - Stabilité marges (30%): Marges stables sur le temps
    
    Args:
        df: DataFrame avec roic, roe, margin_stability
    
    Returns:
        Series score moat [0, 1]
    """
    scores = pd.DataFrame(index=df.index)
    
    # --- ROIC (40%) ---
    # Seuils: < 5% = 0, 5-10% = 0.3-0.6, 10-15% = 0.6-0.8, > 15% = 0.8-1.0
    roic = df.get("roic_avg")
    if roic is None:
        roic = df.get("roic")
    if roic is None:
        roic = pd.Series(0.10, index=df.index)  # Neutre
        logger.debug("ROIC absent → valeur neutre 10%")
    
    # Normalisation: ROIC clippé à [0, 25%] puis mappé à [0, 1]
    scores["roic"] = (roic.clip(0, 0.25) / 0.25).fillna(0.5)
    
    # --- ROE (30%) ---
    roe = df.get("roe_avg")
    if roe is None:
        roe = df.get("roe")
    if roe is None:
        roe = pd.Series(0.12, index=df.index)  # Neutre
        logger.debug("ROE absent → valeur neutre 12%")
    
    # Normalisation: ROE clippé à [0, 30%] puis mappé à [0, 1]
    scores["roe"] = (roe.clip(0, 0.30) / 0.30).fillna(0.5)
    
    # --- Stabilité marges (30%) ---
    if "margin_stability" in df.columns:
        # margin_stability devrait déjà être en [0, 1]
        scores["stability"] = df["margin_stability"].fillna(0.5)
    elif "score_quality" in df.columns:
        # Fallback sur score_quality global
        scores["stability"] = df["score_quality"].fillna(0.5)
    else:
        scores["stability"] = 0.5
        logger.debug("margin_stability absent → valeur neutre 0.5")
    
    # Agrégation
    moat_score = (
        0.40 * scores["roic"] +
        0.30 * scores["roe"] +
        0.30 * scores["stability"]
    ).clip(0, 1)
    
    return moat_score


def _score_cash_quality(df: pd.DataFrame) -> pd.Series:
    """
    Calcule le score Cash Quality (qualité des bénéfices).
    
    Composantes:
    - FCF/NI ratio (60%): > 1 = excellent (profits convertis en cash)
    - Accruals bas (40%): < 5% = excellent (bénéfices = cash réel)
    
    Pré-requis: Appeler compute_buffett_features() avant pour calculer
    les colonnes fcf_ni_ratio et accruals.
    
    Args:
        df: DataFrame avec fcf_ni_ratio, accruals
    
    Returns:
        Series score cash quality [0, 1]
    """
    scores = pd.DataFrame(index=df.index)
    
    # --- FCF/NI Ratio (60%) ---
    # Seuils: < 0.5 = 0-0.3, 0.5-1.0 = 0.3-0.7, > 1.0 = 0.7-1.0
    if "fcf_ni_ratio" in df.columns:
        ratio = df["fcf_ni_ratio"].clip(0.3, 1.5)
        # Mapping: 0.3 → 0, 1.5 → 1
        scores["fcf_ni"] = ((ratio - 0.3) / 1.2).fillna(0.5)
    else:
        scores["fcf_ni"] = 0.5
        logger.debug("fcf_ni_ratio absent → valeur neutre 0.5")
    
    # --- Accruals (40%) ---
    # Plus c'est bas, mieux c'est: < 5% = 1.0, > 15% = 0.0
    if "accruals" in df.columns:
        # Inverser: accruals bas = score haut
        accruals_clipped = df["accruals"].clip(0, 0.20)
        scores["accruals"] = (1 - accruals_clipped / 0.20).fillna(0.5)
    else:
        scores["accruals"] = 0.5
        logger.debug("accruals absent → valeur neutre 0.5")
    
    # Agrégation
    cash_score = (
        0.60 * scores["fcf_ni"] +
        0.40 * scores["accruals"]
    ).clip(0, 1)
    
    return cash_score


def _get_cap_alloc_score(df: pd.DataFrame) -> pd.Series:
    """
    Récupère le score Capital Allocation.
    
    Utilise capital_discipline s'il existe, sinon fallback sur score_quality
    ou valeur neutre.
    
    Args:
        df: DataFrame
    
    Returns:
        Series score cap alloc [0, 1]
    """
    if "capital_discipline" in df.columns:
        return df["capital_discipline"].fillna(0.5)
    elif "score_quality" in df.columns:
        # Approximation via score qualité global
        return df["score_quality"].fillna(0.5)
    else:
        logger.debug("capital_discipline absent → valeur neutre 0.5")
        return pd.Series(0.5, index=df.index)


def get_buffett_score_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retourne le détail du score Buffett pour analyse.
    
    Args:
        df: DataFrame avec scores Buffett calculés
    
    Returns:
        DataFrame avec colonnes de breakdown
    """
    cols = [
        "symbol",
        "score_buffett",
        "score_quality_buffett",
        "score_valo_buffett",
        "score_moat_buffett",
        "score_cash_buffett",
        "rank_buffett_v2",
    ]
    
    available = [c for c in cols if c in df.columns]
    
    return df[available].sort_values("score_buffett", ascending=False)
