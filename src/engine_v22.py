"""SmartMoney Engine v2.2 - Legacy Scoring (Smart Money dominant)

Hérite de SmartMoneyEngineBase et implémente:
- calculate_scores(): Scoring v2.2 (smart_money 45%, momentum 25%, etc.)
- apply_filters(): Filtres simples v2.2

Poids v2.2:
- smart_money: 45%
- insider: 15%
- momentum: 25%
- quality: 15%
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.engine_base import SmartMoneyEngineBase

try:
    from config import WEIGHTS, CONSTRAINTS, SCORING
except ImportError:
    WEIGHTS = {"smart_money": 0.45, "insider": 0.15, "momentum": 0.25, "quality": 0.15}
    CONSTRAINTS = {"min_buys": 2, "min_price": 5, "min_score": 0.40, "max_positions": 20, "min_positions": 10, "max_weight": 0.15}
    SCORING = {"use_zscore": True, "sector_neutral_quality": True, "smart_money_dedup": True}


class SmartMoneyEngineV22(SmartMoneyEngineBase):
    """Engine SmartMoney v2.2 - Legacy avec scoring smart money dominant."""
    
    version = "2.2"
    
    def __init__(self):
        super().__init__()
        self.weights = WEIGHTS.copy()
        self.constraints = CONSTRAINTS.copy()
    
    def _prepare_ranks(self):
        if "gp_buys" in self.universe.columns:
            self.universe["gp_buys_rank"] = self.universe["gp_buys"].rank(pct=True)
        
        if SCORING.get("sector_neutral_quality", True):
            quality_cols = ["roe", "net_margin", "debt_equity", "current_ratio"]
            for col in quality_cols:
                if col in self.universe.columns:
                    if col == "debt_equity":
                        self.universe[f"{col}_rank"] = 1 - self.universe.groupby("sector")[col].rank(pct=True)
                    else:
                        self.universe[f"{col}_rank"] = self.universe.groupby("sector")[col].rank(pct=True)
    
    def score_smart_money(self, row) -> float:
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
    
    def score_insider(self, row) -> float:
        buys = row.get("insider_buys", 0)
        sells = row.get("insider_sells", 0)
        net_value = row.get("insider_net_value", 0)
        ratio_score = buys / (buys + sells) if buys + sells > 0 else 0.5
        value_score = (min(max(net_value / 10_000_000, -1), 1) + 1) / 2
        return round(ratio_score * 0.6 + value_score * 0.4, 3)
    
    def score_momentum(self, row) -> float:
        score = 0
        rsi = row.get("rsi", 50) or 50
        if 40 <= rsi <= 60: rsi_score = 1.0
        elif 30 <= rsi < 40 or 60 < rsi <= 70: rsi_score = 0.7
        elif rsi < 30: rsi_score = 0.8
        else: rsi_score = 0.3
        score += rsi_score * 0.4
        
        perf_3m = row.get("perf_3m", 0) or 0
        if perf_3m > 15: score += 0.3
        elif perf_3m > 5: score += 0.25
        elif perf_3m > 0: score += 0.2
        elif perf_3m > -10: score += 0.1
        
        return round(min(score, 1.0), 3)
    
    def score_quality(self, row) -> float:
        score = 0.5
        roe_rank = row.get("roe_rank")
        if roe_rank is not None and not pd.isna(roe_rank):
            if roe_rank >= 0.8: score += 0.20
            elif roe_rank >= 0.6: score += 0.10
            elif roe_rank < 0.2: score -= 0.15
        return round(max(0, min(1, score)), 3)
    
    def calculate_scores(self) -> pd.DataFrame:
        if self.universe.empty:
            self.load_data()
        
        print("📈 Calcul des scores v2.2...")
        self._prepare_ranks()
        
        scores = []
        for _, row in self.universe.iterrows():
            row["score_sm"] = self.score_smart_money(row)
            row["score_insider"] = self.score_insider(row)
            row["score_momentum"] = self.score_momentum(row)
            row["score_quality"] = self.score_quality(row)
            scores.append(row)
        
        self.universe = pd.DataFrame(scores)
        
        if SCORING.get("use_zscore", True):
            for col in ["score_sm", "score_insider", "score_momentum", "score_quality"]:
                mean, std = self.universe[col].mean(), self.universe[col].std()
                self.universe[f"{col}_z"] = (self.universe[col] - mean) / std if std > 0 else 0
            
            self.universe["score_composite"] = (
                self.weights["smart_money"] * self.universe["score_sm_z"] +
                self.weights["insider"] * self.universe["score_insider_z"] +
                self.weights["momentum"] * self.universe["score_momentum_z"] +
                self.weights["quality"] * self.universe["score_quality_z"]
            ).round(3)
        else:
            self.universe["score_composite"] = (
                self.weights["smart_money"] * self.universe["score_sm"] +
                self.weights["insider"] * self.universe["score_insider"] +
                self.weights["momentum"] * self.universe["score_momentum"] +
                self.weights["quality"] * self.universe["score_quality"]
            ).round(3)
        
        self.universe = self.universe.sort_values("score_composite", ascending=False)
        print(f"✅ Scores v2.2 calculés pour {len(self.universe)} tickers")
        return self.universe
    
    def apply_filters(self) -> pd.DataFrame:
        before = len(self.universe)
        df = self.universe.copy()
        price_col = "td_price" if "td_price" in df.columns else "current_price"
        df = df[df[price_col] >= self.constraints["min_price"]]
        df = df[df["score_composite"] >= self.constraints["min_score"]]
        df = df.head(self.constraints["max_positions"] * 2)
        self.universe = df
        print(f"🔍 Filtres v2.2: {before} → {len(df)} tickers")
        return self.universe
    
    def summary(self) -> dict:
        return {
            "version": self.version,
            "universe_size": len(self.universe),
            "portfolio_size": len(self.portfolio),
            "weights": self.weights,
            "metrics": self.portfolio_metrics,
        }


if __name__ == "__main__":
    engine = SmartMoneyEngineV22()
    engine.load_data()
    engine.enrich(top_n=40)
    engine.clean_universe(strict=False)
    engine.calculate_scores()
    engine.apply_filters()
    engine.optimize()
    print(engine.summary())
