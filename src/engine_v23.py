"""SmartMoney Engine v2.3 — Buffett-Style Scoring

Hérite de SmartMoneyEngineBase (tronc commun) et implémente:
- calculate_scores(): Scoring v2.3 (value/quality/risk + signaux)
- apply_filters(): Filtres liquidité + hard filters + score minimum

Changements vs v2.2:
- Nouveaux poids (smart_money réduit 45% → 15%, value/quality/risk ajoutés)
- Filtres de liquidité et hard filters
- Scoring Buffett-style (value, quality, risk inversé)
- Contrôle look-ahead

Architecture:
    SmartMoneyEngineBase (tronc commun)
        ├── SmartMoneyEngineV22 (legacy)
        └── SmartMoneyEngineV23 (Buffett-style) ← CE FICHIER

Usage:
    from src.engine_v23 import SmartMoneyEngineV23
    
    engine = SmartMoneyEngineV23()
    engine.load_data()
    engine.enrich(top_n=50)
    engine.apply_filters_v23()      # Filtres liquidité + hard
    engine.calculate_scores_v23()   # Nouveaux scores
    engine.apply_filters()          # Filtre score minimum
    engine.optimize()
    engine.export(output_dir)

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional
from pathlib import Path

# Import de la BASE (pas de v2.2 !)
from src.engine_base import SmartMoneyEngineBase

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

try:
    from config import SCORING
except ImportError:
    SCORING = {"use_zscore": True, "sector_neutral_quality": True, "smart_money_dedup": True}

from src.filters.liquidity import apply_liquidity_filters
from src.filters.hard_filters import apply_hard_filters
from src.scoring.value_composite import score_value
from src.scoring.quality_composite import score_quality
from src.scoring.risk_score import score_risk
from src.scoring.composite import calculate_composite_score

logger = logging.getLogger(__name__)


class SmartMoneyEngineV23(SmartMoneyEngineBase):
    """
    Moteur SmartMoney v2.3 — Buffett-Style.
    
    Hérite de SmartMoneyEngineBase (PAS de v2.2) et ajoute:
    - Filtres de liquidité et hard filters
    - Scoring Value, Quality, Risk
    - Poids v2.3 (smart_money réduit de 45% à 15%)
    - Buffett score (moyenne value + quality + risk)
    
    Example:
        >>> engine = SmartMoneyEngineV23()
        >>> engine.load_data()
        >>> engine.enrich(top_n=50)
        >>> engine.apply_filters_v23()      # Nouveaux filtres
        >>> engine.calculate_scores_v23()   # Nouveaux scores
        >>> engine.apply_filters()          # Score minimum
        >>> engine.optimize()
    """
    
    version = "2.3"
    
    def __init__(self):
        super().__init__()
        self.weights = WEIGHTS_V23.copy()
        self.constraints = CONSTRAINTS_V23.copy()
    
    # =========================================================================
    # MÉTHODES DE SCORING DE SIGNAUX (partagées avec v2.2)
    # Copiées ici pour éviter l'héritage implicite de v2.2
    # =========================================================================
    
    def _prepare_ranks(self):
        """Prépare les rangs pour le scoring."""
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
        """Score basé sur les positions des hedge funds (Dataroma)."""
        score = 0
        
        # Tier (A=meilleur)
        tier_map = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}
        score += tier_map.get(row.get("gp_tier", "D"), 0.25) * 0.25
        
        # Nombre d'achats
        buys_rank = row.get("gp_buys_rank", 0.5)
        if pd.isna(buys_rank):
            buys_rank = min(row.get("gp_buys", 0) / 10, 1.0)
        score += buys_rank * 0.50
        
        # Poids dans les portefeuilles
        weight = min(row.get("gp_weight", 0) / 0.2, 1.0)
        score += weight * 0.25
        
        return round(score, 3)
    
    def score_insider(self, row) -> float:
        """Score basé sur les transactions d'initiés."""
        buys = row.get("insider_buys", 0)
        sells = row.get("insider_sells", 0)
        net_value = row.get("insider_net_value", 0)
        
        # Ratio achats/ventes
        ratio_score = buys / (buys + sells) if buys + sells > 0 else 0.5
        
        # Valeur nette des transactions
        value_score = (min(max(net_value / 10_000_000, -1), 1) + 1) / 2
        
        return round(ratio_score * 0.6 + value_score * 0.4, 3)
    
    def score_momentum(self, row) -> float:
        """Score momentum basé sur RSI et performance."""
        score = 0
        
        # RSI (40-60 = zone neutre idéale)
        rsi = row.get("rsi", 50) or 50
        if 40 <= rsi <= 60:
            rsi_score = 1.0
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            rsi_score = 0.7
        elif rsi < 30:
            rsi_score = 0.8  # Survente = opportunité
        else:
            rsi_score = 0.3  # Surachat
        score += rsi_score * 0.4
        
        # Performance 3 mois
        perf_3m = row.get("perf_3m", 0) or 0
        if perf_3m > 15:
            score += 0.3
        elif perf_3m > 5:
            score += 0.25
        elif perf_3m > 0:
            score += 0.2
        elif perf_3m > -10:
            score += 0.1
        
        return round(min(score, 1.0), 3)
    
    # =========================================================================
    # MÉTHODES ABSTRAITES IMPLÉMENTÉES
    # =========================================================================
    
    def calculate_scores(self) -> pd.DataFrame:
        """
        Implémentation requise par SmartMoneyEngineBase.
        Redirige vers calculate_scores_v23().
        """
        return self.calculate_scores_v23()
    
    def apply_filters(self) -> pd.DataFrame:
        """
        Applique les filtres finaux v2.3 (après scoring).
        """
        before = len(self.universe)
        
        # Filtre score minimum
        min_score = self.constraints.get("min_score", 0.40)
        if "score_composite" in self.universe.columns:
            self.universe = self.universe[self.universe["score_composite"] >= min_score]
        
        # Limiter au max_positions * 2 (pour laisser de la marge à HRP)
        max_pos = self.constraints.get("max_positions", 20)
        self.universe = self.universe.head(max_pos * 2)
        
        logger.info(f"Filtres finaux v2.3: {before} → {len(self.universe)} tickers")
        return self.universe
    
    # =========================================================================
    # MÉTHODES SPÉCIFIQUES V2.3
    # =========================================================================
    
    def apply_filters_v23(self, verbose: bool = True, min_after_filters: int = 15) -> pd.DataFrame:
        """
        Applique les filtres v2.3 (liquidité + hard filters) avec fallback.
        À appeler AVANT calculate_scores_v23().
        
        Args:
            verbose: Afficher les logs
            min_after_filters: Nombre minimum de tickers après filtres.
                              Si moins, on relaxe les filtres progressivement.
        
        Returns:
            DataFrame filtré
        """
        if self.universe.empty:
            raise ValueError("Univers vide. Appeler load_data() et enrich() d'abord.")
        
        initial_count = len(self.universe)
        df_backup = self.universe.copy()
        
        # 1. Tenter les filtres complets
        try:
            # Filtres de liquidité
            self.universe = apply_liquidity_filters(self.universe, verbose=verbose)
            after_liquidity = len(self.universe)
            
            # Hard filters
            self.universe = apply_hard_filters(self.universe, verbose=verbose)
            after_hard = len(self.universe)
            
            if verbose:
                print(f"   Filtres v2.3: {initial_count} → {after_liquidity} (liquidité) → {after_hard} (hard)")
        except Exception as e:
            logger.warning(f"Erreur filtres v2.3: {e}")
            self.universe = df_backup
            after_hard = len(self.universe)
        
        # 2. FALLBACK si trop peu de tickers
        if len(self.universe) < min_after_filters:
            print(f"   ⚠️ Seulement {len(self.universe)} tickers après filtres stricts")
            print(f"   ↳ Fallback: utilisation de l'univers nettoyé ({len(df_backup)} tickers)")
            
            # Option A: Garder l'univers complet sans hard filters
            self.universe = df_backup
            
            # Option B: Filtres allégés (D/E < 5 au lieu de 3)
            if "debt_equity" in self.universe.columns:
                relaxed_de = 5.0
                mask_de = (self.universe["debt_equity"] <= relaxed_de) | self.universe["debt_equity"].isna()
                filtered_relaxed = self.universe[mask_de]
                if len(filtered_relaxed) >= min_after_filters:
                    self.universe = filtered_relaxed
                    print(f"   ↳ Filtre allégé D/E ≤ {relaxed_de}: {len(self.universe)} tickers")
        
        if verbose:
            logger.info(f"Filtres v2.3 final: {initial_count} → {len(self.universe)} tickers")
        
        return self.universe
    
    def calculate_scores_v23(
        self,
        sector_medians: Optional[Dict[str, float]] = None,
        historical_data_map: Optional[Dict[str, Dict]] = None,
    ) -> pd.DataFrame:
        """
        Calcule les scores v2.3 (value, quality, risk + composite).
        
        Pipeline:
        1. Scores de signaux (smart_money, insider, momentum) - méthodes locales
        2. Score Value (FCF yield, EV/EBIT, MoS)
        3. Score Quality (ROIC, stabilité, FCF growth)
        4. Score Risk inversé (leverage, coverage, volatility)
        5. Composite v2.3 + Buffett Score
        
        Args:
            sector_medians: Médianes EV/EBIT par secteur (optionnel)
            historical_data_map: Historiques par ticker (optionnel)
        
        Returns:
            DataFrame avec tous les scores
        """
        if self.universe.empty:
            raise ValueError("Univers vide après filtres. Vérifier les données ou relaxer les filtres.")
        
        print("\n" + "=" * 50)
        print("SCORING v2.3 (Buffett-Style)")
        print("=" * 50)
        
        # 1. Scores de signaux (méthodes LOCALES, pas v2.2)
        print("\n1. Scores signaux (smart_money, insider, momentum)...")
        self._prepare_ranks()
        
        for idx, row in self.universe.iterrows():
            self.universe.loc[idx, "score_sm"] = self.score_smart_money(row)
            self.universe.loc[idx, "score_insider"] = self.score_insider(row)
            self.universe.loc[idx, "score_momentum"] = self.score_momentum(row)
        
        # 2. Score Value
        print("2. Score Value...")
        try:
            self.universe = score_value(self.universe, sector_medians)
        except Exception as e:
            logger.warning(f"Erreur score_value: {e}")
            self.universe["score_value"] = 0.5  # Fallback neutre
        
        # 3. Score Quality
        print("3. Score Quality...")
        try:
            self.universe = score_quality(self.universe, historical_data_map)
        except Exception as e:
            logger.warning(f"Erreur score_quality: {e}")
            self.universe["score_quality_v23"] = 0.5  # Fallback neutre
        
        # 4. Score Risk (inversé)
        print("4. Score Risk (inversé)...")
        try:
            self.universe = score_risk(self.universe)
        except Exception as e:
            logger.warning(f"Erreur score_risk: {e}")
            self.universe["score_risk"] = 0.5  # Fallback neutre
        
        # 5. Composite v2.3
        print("5. Composite v2.3...")
        try:
            self.universe = calculate_composite_score(
                self.universe,
                weights=self.weights,
            )
        except Exception as e:
            logger.warning(f"Erreur composite: {e}")
            # Fallback: moyenne simple des scores disponibles
            score_cols = ["score_sm", "score_insider", "score_momentum", 
                         "score_value", "score_quality_v23", "score_risk"]
            available = [c for c in score_cols if c in self.universe.columns]
            if available:
                self.universe["score_composite"] = self.universe[available].mean(axis=1)
            else:
                self.universe["score_composite"] = 0.5
        
        # Tri par score
        self.universe = self.universe.sort_values("score_composite", ascending=False)
        
        print("\n" + "=" * 50)
        print("SCORING v2.3 TERMINÉ")
        print(f"  Univers: {len(self.universe)} tickers")
        print(f"  Composite: mean={self.universe['score_composite'].mean():.3f}")
        if "buffett_score" in self.universe.columns:
            print(f"  Buffett:   mean={self.universe['buffett_score'].mean():.3f}")
        print("=" * 50)
        
        return self.universe
    
    def get_top_buffett(self, n: int = 20) -> pd.DataFrame:
        """
        Retourne les top N par Buffett score (value + quality + risk).
        
        Args:
            n: Nombre de positions
        
        Returns:
            DataFrame trié par buffett_score
        """
        sort_col = "buffett_score" if "buffett_score" in self.universe.columns else "score_composite"
        
        cols = [
            "symbol", "company", "sector",
            "buffett_score", "score_composite",
            "score_value", "score_quality_v23", "score_risk",
            "score_sm", "score_insider", "score_momentum",
        ]
        available_cols = [c for c in cols if c in self.universe.columns]
        
        return (
            self.universe[available_cols]
            .sort_values(sort_col, ascending=False)
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
