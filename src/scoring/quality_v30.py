"""SmartMoney v3.0 — Quality Scorer "Buffett-Quant"

Quality = "Great Business dans son secteur"

Différence avec v2.3:
- v2.3: Seuils ABSOLUS (ROE > 15% = bon)
- v3.0: Ranks SECTOR-RELATIVE + STABILITÉ 5 ans

Philosophie Buffett:
"Je ne regarde pas si ROE > 15% en absolu.
Je regarde si le ROE est élevé ET DURABLE par rapport
à ce que le business peut naturellement faire."

Composantes v3.0:
- Profitabilité relative (50%): ROE, ROIC, marges vs pairs secteur
- Stabilité (30%): Volatilité ROE et marges sur 5 ans
- Bilan (20%): Leverage et coverage

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v30 import QUALITY_V30
except ImportError:
    QUALITY_V30 = {
        "mode": "sector_relative_with_stability",
        "history_years": 5,
        "components": {
            "roe_sector_rank_5y": 0.20,
            "roic_sector_rank_5y": 0.15,
            "margin_sector_rank_5y": 0.15,
            "roe_stability": 0.15,
            "margin_stability": 0.15,
            "leverage_score": 0.10,
            "coverage_score": 0.10,
        },
    }

logger = logging.getLogger(__name__)


@dataclass
class QualityScoreV30:
    """Résultat du scoring Quality v3.0."""
    total: float
    profitability_score: float      # 50%
    stability_score: float          # 30%
    balance_sheet_score: float      # 20%
    components: Dict[str, float] = field(default_factory=dict)


class QualityScorerV30:
    """
    Calcule le score Quality v3.0 "Buffett-Quant".
    
    Différence clé avec v2.3:
    - Au lieu de: "ROE > 15% = 0.70"
    - On fait: "ROE ranké 80e percentile dans le secteur = 0.80"
    
    Avantages:
    1. Un ROE de 10% en Healthcare peut être excellent (80e percentile)
    2. Un ROE de 10% en Tech peut être médiocre (20e percentile)
    3. La stabilité sur 5 ans évite les "one-shots"
    
    Example:
        >>> scorer = QualityScorerV30()
        >>> df = scorer.score_universe(df)
        >>> print(df[["symbol", "score_quality_v30"]].head())
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or QUALITY_V30
        self.components = self.config["components"]
        self.history_years = self.config.get("history_years", 5)
    
    def score_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le score Quality v3.0 pour tout l'univers.
        
        Args:
            df: DataFrame avec colonnes:
                - sector: Secteur GICS
                - roe ou roe_avg: ROE (idéalement moyenne 5 ans)
                - roic ou roic_avg: ROIC
                - operating_margin ou margin_avg: Marge opérationnelle
                - roe_std, margin_std: Ecart-types (si disponibles)
                - debt_equity ou total_debt, equity
                - interest_coverage
        
        Returns:
            DataFrame avec score_quality_v30 et composantes
        """
        df = df.copy()
        
        # === 1. PROFITABILITÉ RELATIVE (50%) ===
        df = self._score_profitability_relative(df)
        
        # === 2. STABILITÉ (30%) ===
        df = self._score_stability(df)
        
        # === 3. BILAN (20%) ===
        df = self._score_balance_sheet(df)
        
        # === COMPOSITE ===
        df["score_quality_v30"] = (
            0.50 * df["_profitability_score"] +
            0.30 * df["_stability_score"] +
            0.20 * df["_balance_sheet_score"]
        ).round(3)
        
        # Cleanup colonnes temporaires
        temp_cols = [c for c in df.columns if c.startswith("_")]
        # On garde les colonnes intermédiaires pour debug
        # df = df.drop(columns=temp_cols)
        
        logger.info(
            f"Quality v3.0 calculé: "
            f"mean={df['score_quality_v30'].mean():.3f}, "
            f"std={df['score_quality_v30'].std():.3f}"
        )
        
        return df
    
    def _score_profitability_relative(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score profitabilité RELATIVE au secteur.
        
        Au lieu de seuils absolus, on ranke chaque métrique
        au sein du secteur puis on convertit en score [0, 1].
        """
        # Récupérer les métriques (avec fallbacks)
        df["_roe"] = df.get("roe_avg", df.get("roe", np.nan))
        df["_roic"] = df.get("roic_avg", df.get("roic", np.nan))
        df["_margin"] = df.get("margin_avg", df.get("operating_margin", np.nan))
        
        # Ranks par secteur (percentiles)
        if "sector" in df.columns:
            df["_roe_sector_rank"] = df.groupby("sector")["_roe"].rank(pct=True)
            df["_roic_sector_rank"] = df.groupby("sector")["_roic"].rank(pct=True)
            df["_margin_sector_rank"] = df.groupby("sector")["_margin"].rank(pct=True)
        else:
            # Fallback: rank global si pas de secteur
            df["_roe_sector_rank"] = df["_roe"].rank(pct=True)
            df["_roic_sector_rank"] = df["_roic"].rank(pct=True)
            df["_margin_sector_rank"] = df["_margin"].rank(pct=True)
        
        # Remplir les NaN avec 0.5 (neutre)
        df["_roe_sector_rank"] = df["_roe_sector_rank"].fillna(0.5)
        df["_roic_sector_rank"] = df["_roic_sector_rank"].fillna(0.5)
        df["_margin_sector_rank"] = df["_margin_sector_rank"].fillna(0.5)
        
        # Score profitabilité composite (pondéré selon config)
        # ROE: 20%, ROIC: 15%, Margin: 15% -> total 50%
        # Normalisé à 1.0 pour cette composante
        w_roe = self.components.get("roe_sector_rank_5y", 0.20) / 0.50
        w_roic = self.components.get("roic_sector_rank_5y", 0.15) / 0.50
        w_margin = self.components.get("margin_sector_rank_5y", 0.15) / 0.50
        
        df["_profitability_score"] = (
            w_roe * df["_roe_sector_rank"] +
            w_roic * df["_roic_sector_rank"] +
            w_margin * df["_margin_sector_rank"]
        ).clip(0, 1)
        
        return df
    
    def _score_stability(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score stabilité = pénaliser la volatilité des métriques.
        
        Formule: 1 / (1 + coefficient_de_variation)
        - CV faible (marges stables) = score élevé
        - CV élevé (marges volatiles) = score bas
        """
        # Récupérer les écarts-types (si disponibles)
        df["_roe_std"] = df.get("roe_std", np.nan)
        df["_margin_std"] = df.get("margin_std", np.nan)
        
        # Coefficient de variation = std / mean
        # Pour ROE
        roe_mean = df["_roe"].replace(0, np.nan)
        df["_roe_cv"] = (df["_roe_std"].abs() / roe_mean.abs()).fillna(0.5)
        df["_roe_stability"] = (1 / (1 + df["_roe_cv"])).clip(0, 1)
        
        # Pour marges
        margin_mean = df["_margin"].replace(0, np.nan)
        df["_margin_cv"] = (df["_margin_std"].abs() / margin_mean.abs()).fillna(0.5)
        df["_margin_stability"] = (1 / (1 + df["_margin_cv"])).clip(0, 1)
        
        # Si pas de std disponible, estimer depuis les niveaux
        # (entreprises avec marges très élevées sont souvent plus stables)
        mask_no_roe_std = df["_roe_std"].isna()
        mask_no_margin_std = df["_margin_std"].isna()
        
        if mask_no_roe_std.any():
            # Proxy: ROE élevé = souvent plus stable
            df.loc[mask_no_roe_std, "_roe_stability"] = (
                df.loc[mask_no_roe_std, "_roe_sector_rank"] * 0.7 + 0.15
            )
        
        if mask_no_margin_std.any():
            # Proxy: marge élevée = souvent plus stable
            df.loc[mask_no_margin_std, "_margin_stability"] = (
                df.loc[mask_no_margin_std, "_margin_sector_rank"] * 0.7 + 0.15
            )
        
        # Score stabilité composite
        # ROE stability: 15%, Margin stability: 15% -> total 30%
        w_roe_stab = self.components.get("roe_stability", 0.15) / 0.30
        w_margin_stab = self.components.get("margin_stability", 0.15) / 0.30
        
        df["_stability_score"] = (
            w_roe_stab * df["_roe_stability"] +
            w_margin_stab * df["_margin_stability"]
        ).clip(0, 1)
        
        return df
    
    def _score_balance_sheet(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score bilan = leverage et coverage.
        
        Moins de dette + meilleure couverture = meilleur score.
        """
        # Debt/Equity
        if "debt_equity" in df.columns:
            df["_de_ratio"] = df["debt_equity"]
        elif "total_debt" in df.columns and "equity" in df.columns:
            df["_de_ratio"] = df["total_debt"] / df["equity"].replace(0, np.nan)
        else:
            df["_de_ratio"] = np.nan
        
        # Leverage score: D/E bas = bon
        # Normaliser: D/E 0 = 1.0, D/E 3+ = 0.0
        df["_leverage_score"] = (1 - df["_de_ratio"].clip(0, 3) / 3).fillna(0.5)
        
        # Interest Coverage
        if "interest_coverage" in df.columns:
            df["_coverage"] = df["interest_coverage"]
        else:
            # Estimer depuis EBIT et interest expense
            ebit = df.get("ebit", np.nan)
            interest = df.get("interest_expense", np.nan)
            if isinstance(ebit, pd.Series) and isinstance(interest, pd.Series):
                df["_coverage"] = ebit / interest.replace(0, np.nan).abs()
            else:
                df["_coverage"] = np.nan
        
        # Coverage score: coverage élevé = bon
        # Normaliser: coverage 0 = 0.0, coverage 10+ = 1.0
        df["_coverage_score"] = (df["_coverage"].clip(0, 10) / 10).fillna(0.5)
        
        # Score bilan composite
        # Leverage: 10%, Coverage: 10% -> total 20%
        w_leverage = self.components.get("leverage_score", 0.10) / 0.20
        w_coverage = self.components.get("coverage_score", 0.10) / 0.20
        
        df["_balance_sheet_score"] = (
            w_leverage * df["_leverage_score"] +
            w_coverage * df["_coverage_score"]
        ).clip(0, 1)
        
        return df


def score_quality_v30(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fonction helper pour calculer le score Quality v3.0.
    
    Args:
        df: DataFrame avec métriques
    
    Returns:
        DataFrame avec score_quality_v30 ajouté
    """
    scorer = QualityScorerV30()
    return scorer.score_universe(df)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    # Test avec données synthétiques
    logging.basicConfig(level=logging.INFO)
    
    test_data = pd.DataFrame({
        "symbol": ["AAPL", "MSFT", "JNJ", "XOM", "BAC"],
        "sector": ["Technology", "Technology", "Healthcare", "Energy", "Financials"],
        "roe": [0.45, 0.35, 0.22, 0.12, 0.10],
        "roic": [0.30, 0.25, 0.15, 0.08, 0.07],
        "operating_margin": [0.30, 0.40, 0.25, 0.12, 0.25],
        "debt_equity": [1.5, 0.5, 0.4, 0.8, 1.2],
        "interest_coverage": [30, 50, 20, 8, 5],
    })
    
    result = score_quality_v30(test_data)
    
    print("\n" + "=" * 60)
    print("TEST QUALITY v3.0 - Sector Relative")
    print("=" * 60)
    print(result[["symbol", "sector", "roe", "score_quality_v30"]].to_string())
    print("\nNote: AAPL et MSFT ont des ROE élevés mais sont comparés")
    print("      entre eux (même secteur Tech), pas vs JNJ (Healthcare).")
