"""SmartMoney Engine v2.3 — Intégration

Extension de engine.py avec les nouveaux scores v2.3.

Changements vs v2.2:
- Nouveaux poids (smart_money réduit, value/quality/risk ajoutés)
- Filtres de liquidité et hard filters
- Scoring Buffett-style
- Contrôle look-ahead

Usage:
    from src.engine_v23 import SmartMoneyEngineV23
    
    engine = SmartMoneyEngineV23()
    engine.load_data()
    engine.enrich(top_n=50)
    engine.calculate_scores_v23()  # Nouveaux scores
    engine.optimize()
    engine.export(output_dir)

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional
from pathlib import Path

# Import du moteur v2.2
from src.engine import SmartMoneyEngine

# Imports v2.3
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config_v23 import WEIGHTS_V23, CONSTRAINTS_V23
except ImportError:
    WEIGHTS_V23 = {
        "smart_money": 0.15, "insider": 0.10, "momentum": 0.05,
        "value": 0.30, "quality": 0.25, "risk": 0.15,
    }
    CONSTRAINTS_V23 = {
        "min_positions": 12, "max_positions": 20,
        "max_weight": 0.12, "min_score": 0.40,
    }

from src.filters.liquidity import apply_liquidity_filters
from src.filters.hard_filters import apply_hard_filters
from src.scoring.value_composite import score_value
from src.scoring.quality_composite import score_quality
from src.scoring.risk_score import score_risk
from src.scoring.composite import calculate_composite_score

logger = logging.getLogger(__name__)


class SmartMoneyEngineV23(SmartMoneyEngine):
    """
    Moteur SmartMoney v2.3.
    
    Hérite de SmartMoneyEngine v2.2 et ajoute:
    - Filtres de liquidité et hard filters
    - Scoring Value, Quality, Risk
    - Poids v2.3 (smart_money réduit)
    - Buffett score
    
    Example:
        >>> engine = SmartMoneyEngineV23()
        >>> engine.load_data()
        >>> engine.enrich(top_n=50)
        >>> engine.apply_filters_v23()  # Nouveaux filtres
        >>> engine.calculate_scores_v23()  # Nouveaux scores
        >>> engine.optimize()
    """
    
    def __init__(self):
        super().__init__()
        self.version = "2.3"
        self.weights = WEIGHTS_V23
        self.constraints = CONSTRAINTS_V23
    
    def apply_filters_v23(self, verbose: bool = True) -> pd.DataFrame:
        """
        Applique les filtres v2.3 (liquidité + hard filters).
        
        Returns:
            DataFrame filtré
        """
        if self.universe.empty:
            raise ValueError("Univers vide. Appeler load_data() et enrich() d'abord.")
        
        initial_count = len(self.universe)
        
        # 1. Filtres de liquidité
        self.universe = apply_liquidity_filters(self.universe, verbose=verbose)
        after_liquidity = len(self.universe)
        
        # 2. Hard filters
        self.universe = apply_hard_filters(self.universe, verbose=verbose)
        after_hard = len(self.universe)
        
        if verbose:
            logger.info(
                f"Filtres v2.3: {initial_count} \u2192 {after_liquidity} \u2192 {after_hard} tickers"
            )
        
        return self.universe
    
    def calculate_scores_v23(
        self,
        sector_medians: Optional[Dict[str, float]] = None,
        historical_data_map: Optional[Dict[str, Dict]] = None,
    ) -> pd.DataFrame:
        """
        Calcule les scores v2.3 (value, quality, risk + composite).
        
        Args:
            sector_medians: Médianes EV/EBIT par secteur (optionnel)
            historical_data_map: Historiques par ticker (optionnel)
        
        Returns:
            DataFrame avec tous les scores
        """
        if self.universe.empty:
            raise ValueError("Univers vide.")
        
        logger.info("\n" + "=" * 50)
        logger.info("SCORING v2.3")
        logger.info("=" * 50)
        
        # 1. Scores v2.2 (smart_money, insider, momentum)
        # Utiliser les méthodes du parent
        logger.info("\n1. Scores v2.2 (smart_money, insider, momentum)...")
        self._prepare_ranks()
        
        for idx, row in self.universe.iterrows():
            self.universe.loc[idx, "score_sm"] = self.score_smart_money(row)
            self.universe.loc[idx, "score_insider"] = self.score_insider(row)
            self.universe.loc[idx, "score_momentum"] = self.score_momentum(row)
        
        # 2. Score Value
        logger.info("\n2. Score Value...")
        self.universe = score_value(self.universe, sector_medians)
        
        # 3. Score Quality
        logger.info("\n3. Score Quality...")
        self.universe = score_quality(self.universe, historical_data_map)
        
        # 4. Score Risk (inversé)
        logger.info("\n4. Score Risk (inversé)...")
        self.universe = score_risk(self.universe)
        
        # 5. Composite v2.3
        logger.info("\n5. Composite v2.3...")
        self.universe = calculate_composite_score(
            self.universe,
            weights=self.weights,
        )
        
        # Tri par score
        self.universe = self.universe.sort_values("score_composite", ascending=False)
        
        logger.info("\n" + "=" * 50)
        logger.info("SCORING v2.3 TERMINÉ")
        logger.info(f"  Univers: {len(self.universe)} tickers")
        logger.info(f"  Composite: mean={self.universe['score_composite'].mean():.3f}")
        if "buffett_score" in self.universe.columns:
            logger.info(f"  Buffett:   mean={self.universe['buffett_score'].mean():.3f}")
        logger.info("=" * 50)
        
        return self.universe
    
    def apply_filters(self) -> pd.DataFrame:
        """
        Override: applique les filtres v2.3 en plus des filtres de base.
        """
        # Filtres v2.2 de base
        super().apply_filters()
        
        # Filtres v2.3 additionnels
        min_score = self.constraints.get("min_score", 0.40)
        self.universe = self.universe[self.universe["score_composite"] >= min_score]
        
        # Limiter au max_positions
        max_pos = self.constraints.get("max_positions", 20)
        self.universe = self.universe.head(max_pos * 2)
        
        logger.info(f"Après filtres v2.3: {len(self.universe)} tickers")
        
        return self.universe
    
    def get_top_buffett(self, n: int = 20) -> pd.DataFrame:
        """
        Retourne les top N par Buffett score (value + quality + risk).
        
        Args:
            n: Nombre de positions
        
        Returns:
            DataFrame trié par buffett_score
        """
        if "buffett_score" not in self.universe.columns:
            raise ValueError("Buffett score non calculé. Appeler calculate_scores_v23() d'abord.")
        
        cols = [
            "symbol", "company", "sector",
            "buffett_score", "score_composite",
            "score_value", "score_quality", "score_risk",
            "score_sm", "score_insider", "score_momentum",
        ]
        available_cols = [c for c in cols if c in self.universe.columns]
        
        return (
            self.universe[available_cols]
            .sort_values("buffett_score", ascending=False)
            .head(n)
            .reset_index(drop=True)
        )
    
    def summary(self) -> Dict:
        """
        Retourne un résumé de l'état actuel.
        
        Returns:
            Dict avec statistiques
        """
        summary = {
            "version": self.version,
            "universe_size": len(self.universe),
            "portfolio_size": len(self.portfolio) if not self.portfolio.empty else 0,
        }
        
        if "score_composite" in self.universe.columns:
            summary["score_composite_mean"] = round(self.universe["score_composite"].mean(), 3)
        
        if "buffett_score" in self.universe.columns:
            summary["buffett_score_mean"] = round(self.universe["buffett_score"].mean(), 3)
        
        if "sector" in self.universe.columns:
            summary["sectors"] = self.universe["sector"].value_counts().to_dict()
        
        return summary


# === MAIN ===

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s"
    )
    
    engine = SmartMoneyEngineV23()
    
    # 1. Charger les données
    engine.load_data()
    
    # 2. Enrichir (API Twelve Data)
    engine.enrich(top_n=40)
    
    # 3. Nettoyer
    engine.clean_universe(strict=False)
    
    # 4. Filtres v2.3
    engine.apply_filters_v23()
    
    # 5. Scores v2.3
    engine.calculate_scores_v23()
    
    # 6. Filtres finaux
    engine.apply_filters()
    
    # 7. Optimisation HRP
    engine.optimize()
    
    # 8. Export
    from config import OUTPUTS
    from datetime import datetime
    
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUTS / today
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine.export(output_dir)
    
    # 9. Afficher top Buffett
    print("\n" + "=" * 60)
    print("TOP 10 BUFFETT SCORE")
    print("=" * 60)
    print(engine.get_top_buffett(10).to_string())
