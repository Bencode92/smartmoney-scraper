"""SmartMoney Engine v3.0 - Buffett-Quant

Poids v3.0:
- Value: 45%
- Quality: 35%
- Risk: 20%
- Smart Money: 0% (indicateur only)
- Insider: 0% (tie-breaker only)

Date: Decembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional
from pathlib import Path

from src.engine_base import SmartMoneyEngineBase

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        "min_positions": 12,
        "max_positions": 25,
        "max_weight": 0.10,
        "max_sector": 0.25,
        "min_score": 0.35,
    }

from src.scoring.value_composite import score_value
from src.scoring.quality_composite import score_quality
from src.scoring.risk_score import score_risk
from src.filters.liquidity import apply_liquidity_filters
from src.filters.hard_filters import apply_hard_filters

logger = logging.getLogger(__name__)


class SmartMoneyEngineV30(SmartMoneyEngineBase):
    """Moteur v3.0 Buffett-Quant"""
    
    version = "3.0.0"
    version_name = "Buffett-Quant"
    
    def __init__(self):
        super().__init__()
        self.weights = WEIGHTS_V30.copy()
        self.constraints = CONSTRAINTS_V30.copy()
    
    def calculate_scores(self) -> pd.DataFrame:
        return self.calculate_scores_v30()
    
    def apply_filters(self) -> pd.DataFrame:
        before = len(self.universe)
        min_score = self.constraints.get("min_score", 0.35)
        score_col = "score_composite_v30" if "score_composite_v30" in self.universe.columns else "score_composite"
        
        if score_col in self.universe.columns:
            self.universe = self.universe[self.universe[score_col] >= min_score]
        
        max_pos = self.constraints.get("max_positions", 25)
        self.universe = self.universe.head(max_pos * 2)
        
        logger.info(f"Filtres finaux v3.0: {before} -> {len(self.universe)} tickers")
        return self.universe
    
    def _calculate_indicators(self):
        if "gp_buys" in self.universe.columns:
            self.universe["gp_buys_rank"] = self.universe["gp_buys"].rank(pct=True)
        
        for idx, row in self.universe.iterrows():
            self.universe.loc[idx, "indicator_smart_money"] = self._score_sm(row)
            self.universe.loc[idx, "indicator_insider"] = self._score_insider(row)
    
    def _score_sm(self, row) -> float:
        score = 0
        tier_map = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}
        score += tier_map.get(row.get("gp_tier", "D"), 0.25) * 0.25
        buys_rank = row.get("gp_buys_rank", 0.5)
        if pd.isna(buys_rank):
            buys_rank = min(row.get("gp_buys", 0) / 10, 1.0)
        score += buys_rank * 0.50
        weight = min(row.get("gp_weight", 0) / 0.2, 1.0)
        score += weight * 0.25
        return round(score, 3)
    
    def _score_insider(self, row) -> float:
        buys = row.get("insider_buys", 0)
        sells = row.get("insider_sells", 0)
        net_value = row.get("insider_net_value", 0)
        ratio_score = buys / (buys + sells) if buys + sells > 0 else 0.5
        value_score = (min(max(net_value / 10_000_000, -1), 1) + 1) / 2
        return round(ratio_score * 0.6 + value_score * 0.4, 3)
    
    def apply_filters_v30(self, verbose: bool = True, min_after_filters: int = 20) -> pd.DataFrame:
        if self.universe.empty:
            raise ValueError("Univers vide")
        
        initial_count = len(self.universe)
        df_backup = self.universe.copy()
        
        try:
            self.universe = apply_liquidity_filters(self.universe, verbose=verbose)
            after_liquidity = len(self.universe)
            self.universe = apply_hard_filters(self.universe, verbose=verbose)
            after_hard = len(self.universe)
            
            if verbose:
                print(f"   Filtres v3.0: {initial_count} -> {after_liquidity} (liquidite) -> {after_hard} (hard)")
        except Exception as e:
            logger.warning(f"Erreur filtres v3.0: {e}")
            self.universe = df_backup
        
        if len(self.universe) < min_after_filters:
            print(f"   Warning: {len(self.universe)} tickers apres filtres")
            self.universe = df_backup
            if "debt_equity" in self.universe.columns:
                mask = (self.universe["debt_equity"] <= 4.0) | self.universe["debt_equity"].isna()
                self.universe = self.universe[mask]
                print(f"   Filtre allege D/E <= 4.0: {len(self.universe)} tickers")
        
        return self.universe
    
    def calculate_scores_v30(self, sector_medians=None, historical_data_map=None) -> pd.DataFrame:
        if self.universe.empty:
            raise ValueError("Univers vide")
        
        print("\n" + "=" * 50)
        print(f"SCORING v{self.version} \"{self.version_name}\"")
        print("=" * 50)
        print(f"   Poids: Value={self.weights['value']*100:.0f}%, Quality={self.weights['quality']*100:.0f}%, Risk={self.weights['risk']*100:.0f}%")
        
        print("\n1. Indicateurs (Smart Money, Insider - poids 0%)...")
        self._calculate_indicators()
        
        print("2. Score Value...")
        try:
            self.universe = score_value(self.universe, sector_medians)
        except Exception as e:
            logger.warning(f"Erreur score_value: {e}")
            self.universe["score_value"] = 0.5
        
        print("3. Score Quality...")
        try:
            self.universe = score_quality(self.universe, historical_data_map)
        except Exception as e:
            logger.warning(f"Erreur score_quality: {e}")
            self.universe["score_quality_v23"] = 0.5
        
        print("4. Score Risk...")
        try:
            self.universe = score_risk(self.universe)
        except Exception as e:
            logger.warning(f"Erreur score_risk: {e}")
            self.universe["score_risk"] = 0.5
        
        print("5. Composite v3.0 (45/35/20)...")
        self._calculate_composite_v30()
        
        score_col = "score_composite_v30"
        self.universe = self.universe.sort_values(score_col, ascending=False)
        
        print("\n" + "=" * 50)
        print(f"SCORING v{self.version} TERMINE")
        print(f"  Univers: {len(self.universe)} tickers")
        print(f"  Composite: mean={self.universe[score_col].mean():.3f}")
        print("=" * 50)
        
        return self.universe
    
    def _calculate_composite_v30(self):
        value_col = "score_value"