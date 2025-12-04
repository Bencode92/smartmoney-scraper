"""SmartMoney v3.0 — Composite Scorer "Buffett-Quant"

Agrégation finale des scores v3.0:
- Value: 45% (prix raisonnable vs secteur + MoS)
- Quality: 35% (great business sector-relative + stabilité)
- Risk: 20% (éviter perte permanente de capital)

Smart Money et Insider sont HORS du composite.
Ils servent uniquement d'indicateurs ou tie-breakers.

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v30 import WEIGHTS_V30, CONSTRAINTS_V30
except ImportError:
    WEIGHTS_V30 = {
        "value": 0.45,
        "quality": 0.35,
        "risk": 0.20,
        "smart_money": 0.00,
        "insider": 0.00,
        "momentum": 0.00,
    }
    CONSTRAINTS_V30 = {
        "min_positions": 15,
        "max_positions": 20,
        "max_weight": 0.10,
        "min_weight": 0.03,
        "max_sector": 0.30,
        "min_score": 0.40,
    }

from .quality_v30 import score_quality_v30
from .value_v30 import score_value_v30
from .risk_v30 import score_risk_v30

logger = logging.getLogger(__name__)


@dataclass
class CompositeResultV30:
    """Résultat du scoring composite v3.0."""
    score: float
    value_score: float
    quality_score: float
    risk_score: float
    rank: int
    passes_min_score: bool


class CompositeScorerV30:
    """
    Agrège les scores v3.0 en score composite.
    
    Poids:
    - Value: 45% (prix raisonnable vs secteur + MoS)
    - Quality: 35% (great business sector-relative + stabilité)
    - Risk: 20% (éviter perte permanente de capital)
    
    Smart Money et Insider = 0% (indicateurs seulement)
    
    Example:
        >>> scorer = CompositeScorerV30()
        >>> df = scorer.calculate(df)
        >>> print(df[["symbol", "score_composite_v30", "rank_v30"]].head(20))
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        constraints: Optional[Dict[str, float]] = None,
    ):
        self.weights = weights or WEIGHTS_V30
        self.constraints = constraints or CONSTRAINTS_V30
        
        # Valider que Smart Money, Insider, Momentum sont à 0
        assert self.weights.get("smart_money", 0) == 0, "Smart Money doit être à 0% en v3.0"
        assert self.weights.get("insider", 0) == 0, "Insider doit être à 0% en v3.0"
        assert self.weights.get("momentum", 0) == 0, "Momentum doit être à 0% en v3.0"
        
        # Vérifier que les poids actifs somment à 1.0
        active_weights = self.weights["value"] + self.weights["quality"] + self.weights["risk"]
        assert abs(active_weights - 1.0) < 0.001, f"Poids actifs doivent sommer à 1.0, got {active_weights}"
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le score composite v3.0 pour tout l'univers.
        
        Pipeline:
        1. Score Quality v3.0 (sector-relative + stabilité)
        2. Score Value v3.0 (cross-section + MoS)
        3. Score Risk v3.0 (éviter perte permanente)
        4. Composite = 45% Value + 35% Quality + 20% Risk
        
        Args:
            df: DataFrame avec métriques fondamentales
        
        Returns:
            DataFrame avec score_composite_v30 et rank_v30
        """
        df = df.copy()
        
        logger.info("=" * 60)
        logger.info("SCORING v3.0 BUFFETT-QUANT")
        logger.info("=" * 60)
        
        # === 1. Quality v3.0 ===
        logger.info("\n1. Scoring Quality v3.0 (sector-relative + stabilité)...")
        df = score_quality_v30(df)
        
        # === 2. Value v3.0 ===
        logger.info("\n2. Scoring Value v3.0 (cross-section + MoS)...")
        df = score_value_v30(df)
        
        # === 3. Risk v3.0 ===
        logger.info("\n3. Scoring Risk v3.0 (éviter perte permanente)...")
        df = score_risk_v30(df)
        
        # === 4. Composite ===
        logger.info("\n4. Calcul Composite v3.0...")
        
        # Récupérer les scores
        value = df.get("score_value_v30", df.get("score_value", 0.5))
        quality = df.get("score_quality_v30", df.get("score_quality", 0.5))
        risk = df.get("score_risk_v30", df.get("score_risk", 0.5))
        
        # Composite pondéré
        df["score_composite_v30"] = (
            self.weights["value"] * value +
            self.weights["quality"] * quality +
            self.weights["risk"] * risk
        ).round(3)
        
        # Ranking
        df["rank_v30"] = df["score_composite_v30"].rank(ascending=False).astype(int)
        
        # Flag score minimum
        min_score = self.constraints.get("min_score", 0.40)
        df["passes_min_score_v30"] = df["score_composite_v30"] >= min_score
        
        # Stats
        logger.info("\n" + "=" * 60)
        logger.info("SCORING v3.0 TERMINÉ")
        logger.info(f"  Univers: {len(df)} tickers")
        logger.info(f"  Composite: mean={df['score_composite_v30'].mean():.3f}, std={df['score_composite_v30'].std():.3f}")
        logger.info(f"  Passent min_score ({min_score}): {df['passes_min_score_v30'].sum()} tickers")
        logger.info("=" * 60)
        
        return df
    
    def get_top_holdings(
        self,
        df: pd.DataFrame,
        n: int = 20,
        apply_min_score: bool = True,
    ) -> pd.DataFrame:
        """
        Retourne les top N holdings selon le score composite v3.0.
        
        Args:
            df: DataFrame avec scores calculés
            n: Nombre de positions
            apply_min_score: Filtrer par score minimum
        
        Returns:
            DataFrame trié avec top N
        """
        result = df.copy()
        
        # Filtrer par score minimum
        if apply_min_score:
            min_score = self.constraints.get("min_score", 0.40)
            result = result[result["score_composite_v30"] >= min_score]
        
        # Trier et limiter
        result = result.sort_values("score_composite_v30", ascending=False).head(n)
        
        # Colonnes à afficher
        cols = [
            "symbol", "company", "sector",
            "score_composite_v30", "rank_v30",
            "score_value_v30", "score_quality_v30", "score_risk_v30",
        ]
        available = [c for c in cols if c in result.columns]
        
        return result[available].reset_index(drop=True)
    
    def apply_tie_breaker(
        self,
        df: pd.DataFrame,
        threshold: float = 0.01,
    ) -> pd.DataFrame:
        """
        Applique le tie-breaker Insider pour les scores proches.
        
        Si deux titres ont un score à moins de 1% d'écart,
        préférer celui avec des achats insiders récents.
        
        Args:
            df: DataFrame avec scores
            threshold: Seuil pour considérer un "tie" (défaut 1%)
        
        Returns:
            DataFrame avec colonne tie_breaker_bonus
        """
        df = df.copy()
        
        # Vérifier si on a des données insider
        if "score_insider" in df.columns:
            # Bonus très léger (0.001) pour les achats insiders
            df["tie_breaker_bonus"] = df["score_insider"] * 0.001
        elif "insider_buys" in df.columns:
            df["tie_breaker_bonus"] = (df["insider_buys"] > 0).astype(float) * 0.001
        else:
            df["tie_breaker_bonus"] = 0
        
        # Appliquer le bonus au score pour le ranking final
        df["score_with_tiebreaker"] = df["score_composite_v30"] + df["tie_breaker_bonus"]
        
        # Re-ranker
        df["rank_v30_final"] = df["score_with_tiebreaker"].rank(ascending=False).astype(int)
        
        return df


def calculate_all_scores_v30(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline complet v3.0: calcule tous les scores et le composite.
    
    Args:
        df: DataFrame univers avec métriques
    
    Returns:
        DataFrame avec tous les scores v3.0
    """
    scorer = CompositeScorerV30()
    return scorer.calculate(df)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test avec données synthétiques complètes
    test_data = pd.DataFrame({
        "symbol": ["AAPL", "MSFT", "JNJ", "XOM", "BAC", "HIGH_RISK"],
        "company": ["Apple", "Microsoft", "Johnson & Johnson", "Exxon", "Bank of America", "Risky Corp"],
        "sector": ["Technology", "Technology", "Healthcare", "Energy", "Financials", "Technology"],
        
        # Quality inputs
        "roe": [0.45, 0.35, 0.22, 0.12, 0.10, 0.05],
        "roic": [0.30, 0.25, 0.15, 0.08, 0.07, 0.02],
        "operating_margin": [0.30, 0.40, 0.25, 0.12, 0.25, 0.05],
        "debt_equity": [1.5, 0.5, 0.4, 0.8, 1.2, 4.0],
        "interest_coverage": [30, 50, 20, 8, 5, 1.5],
        
        # Value inputs
        "fcf_yield": [0.04, 0.03, 0.06, 0.10, 0.08, 0.02],
        "ev_ebit": [25, 30, 18, 8, 10, 50],
        "pe_ratio": [28, 35, 15, 10, 9, 100],
        "pe_5y_avg": [32, 30, 18, 12, 11, 80],
        "fcf_yield_5y_avg": [0.035, 0.028, 0.055, 0.08, 0.07, 0.03],
        
        # Risk inputs
        "max_drawdown_5y": [0.30, 0.25, 0.20, 0.40, 0.35, 0.65],
        "volatility_annual": [0.28, 0.24, 0.18, 0.32, 0.30, 0.55],
    })
    
    result = calculate_all_scores_v30(test_data)
    
    print("\n" + "=" * 70)
    print("🎯 CLASSEMENT FINAL v3.0 BUFFETT-QUANT")
    print("=" * 70)
    
    display_cols = [
        "rank_v30", "symbol", "sector",
        "score_composite_v30", "score_value_v30", "score_quality_v30", "score_risk_v30"
    ]
    print(result[display_cols].sort_values("rank_v30").to_string())
    
    print("\n📊 POIDS APPLIQUÉS:")
    print(f"   Value: {WEIGHTS_V30['value']:.0%}")
    print(f"   Quality: {WEIGHTS_V30['quality']:.0%}")
    print(f"   Risk: {WEIGHTS_V30['risk']:.0%}")
    print(f"   Smart Money: {WEIGHTS_V30['smart_money']:.0%} (indicateur)")
    print(f"   Insider: {WEIGHTS_V30['insider']:.0%} (tie-breaker)")
