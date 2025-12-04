"""SmartMoney v3.0 — Value Scorer "Buffett-Quant"

Value = "Prix raisonnable pour ce type de business"

Différence avec v2.3:
- v2.3: Seuils ABSOLUS (FCF yield > 8% = excellent)
- v3.0: Cross-section + MARGIN OF SAFETY vs historique

Philosophie Buffett:
"Je ne cherche pas les P/E les plus bas.
Je cherche un BON business payé à un prix un peu en-dessous
de sa valeur ou de son historique."

Composantes v3.0:
- Cross-section (60%): Cheap vs pairs du secteur
- Margin of Safety (40%): Discount vs historique propre

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field
from scipy import stats

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v30 import VALUE_V30
except ImportError:
    VALUE_V30 = {
        "mode": "cross_section_with_margin_of_safety",
        "mos_history_years": 5,
        "components": {
            "fcf_yield_sector_rank": 0.25,
            "ev_ebit_sector_rank": 0.25,
            "pe_sector_rank": 0.10,
            "pe_vs_history": 0.20,
            "fcf_yield_vs_history": 0.20,
        },
    }

logger = logging.getLogger(__name__)


@dataclass
class ValueScoreV30:
    """Résultat du scoring Value v3.0."""
    total: float
    cross_section_score: float      # 60%
    margin_of_safety_score: float   # 40%
    components: Dict[str, float] = field(default_factory=dict)


class ValueScorerV30:
    """
    Calcule le score Value v3.0 "Buffett-Quant".
    
    Différence clé:
    - Cross-section: "Cheap vs pairs du secteur" (pas absolu)
    - Margin of Safety: "Moins cher que d'habitude pour CE business"
    
    Margin of Safety:
    - P/E actuel < P/E historique = discount
    - FCF yield actuel > FCF yield historique = premium
    - Combinaison = "Great business at a fair price"
    
    Example:
        >>> scorer = ValueScorerV30()
        >>> df = scorer.score_universe(df)
        >>> print(df[["symbol", "score_value_v30", "_mos_score"]].head())
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or VALUE_V30
        self.components = self.config["components"]
        self.mos_years = self.config.get("mos_history_years", 5)
    
    def score_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le score Value v3.0 pour tout l'univers.
        
        Args:
            df: DataFrame avec colonnes:
                - sector: Secteur GICS
                - fcf_yield: FCF / Market Cap
                - ev_ebit: EV / EBIT
                - pe_ratio: P/E ratio
                - pe_5y_avg (optionnel): P/E moyen historique
                - fcf_yield_5y_avg (optionnel): FCF yield moyen historique
        
        Returns:
            DataFrame avec score_value_v30 et composantes
        """
        df = df.copy()
        
        # === 1. CROSS-SECTION (60%) ===
        df = self._score_cross_section(df)
        
        # === 2. MARGIN OF SAFETY (40%) ===
        df = self._score_margin_of_safety(df)
        
        # === COMPOSITE ===
        df["score_value_v30"] = (
            0.60 * df["_cross_section_score"] +
            0.40 * df["_mos_score"]
        ).round(3)
        
        logger.info(
            f"Value v3.0 calculé: "
            f"mean={df['score_value_v30'].mean():.3f}, "
            f"std={df['score_value_v30'].std():.3f}"
        )
        
        return df
    
    def _score_cross_section(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score cross-section = cheap vs pairs du secteur.
        
        Pour chaque métrique, on ranke par secteur.
        FCF yield: plus élevé = mieux
        EV/EBIT: plus bas = mieux
        P/E: plus bas = mieux
        """
        # Récupérer les métriques
        df["_fcf_yield"] = df.get("fcf_yield", np.nan)
        df["_ev_ebit"] = df.get("ev_ebit", np.nan)
        df["_pe"] = df.get("pe_ratio", df.get("pe", np.nan))
        
        # Ranks par secteur
        if "sector" in df.columns:
            # FCF yield: plus élevé = meilleur rank
            df["_fcf_yield_rank"] = df.groupby("sector")["_fcf_yield"].rank(pct=True)
            
            # EV/EBIT: plus bas = meilleur rank (donc 1 - rank)
            df["_ev_ebit_rank"] = 1 - df.groupby("sector")["_ev_ebit"].rank(pct=True)
            
            # P/E: plus bas = meilleur rank (donc 1 - rank)
            df["_pe_rank"] = 1 - df.groupby("sector")["_pe"].rank(pct=True)
        else:
            # Fallback: rank global
            df["_fcf_yield_rank"] = df["_fcf_yield"].rank(pct=True)
            df["_ev_ebit_rank"] = 1 - df["_ev_ebit"].rank(pct=True)
            df["_pe_rank"] = 1 - df["_pe"].rank(pct=True)
        
        # Remplir NaN avec 0.5 (neutre)
        df["_fcf_yield_rank"] = df["_fcf_yield_rank"].fillna(0.5)
        df["_ev_ebit_rank"] = df["_ev_ebit_rank"].fillna(0.5)
        df["_pe_rank"] = df["_pe_rank"].fillna(0.5)
        
        # Score cross-section composite
        # FCF: 25%, EV/EBIT: 25%, PE: 10% -> total 60%
        w_fcf = self.components.get("fcf_yield_sector_rank", 0.25) / 0.60
        w_ev = self.components.get("ev_ebit_sector_rank", 0.25) / 0.60
        w_pe = self.components.get("pe_sector_rank", 0.10) / 0.60
        
        df["_cross_section_score"] = (
            w_fcf * df["_fcf_yield_rank"] +
            w_ev * df["_ev_ebit_rank"] +
            w_pe * df["_pe_rank"]
        ).clip(0, 1)
        
        return df
    
    def _score_margin_of_safety(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score Margin of Safety = discount vs historique propre.
        
        Formules:
        - pe_discount = (pe_5y_avg - pe_current) / pe_5y_avg
          > 0 = moins cher que d'habitude = BON
        
        - fcf_premium = (fcf_yield_current - fcf_yield_5y_avg) / fcf_yield_5y_avg
          > 0 = plus de FCF que d'habitude = BON
        
        Puis on ranke ces discounts/premiums dans l'univers.
        """
        # Récupérer les historiques (si disponibles)
        pe_current = df["_pe"]
        pe_history = df.get("pe_5y_avg", df.get("pe_avg", np.nan))
        
        fcf_yield_current = df["_fcf_yield"]
        fcf_yield_history = df.get("fcf_yield_5y_avg", df.get("fcf_yield_avg", np.nan))
        
        # === P/E Discount ===
        # (pe_history - pe_current) / pe_history
        # Positif si pe_current < pe_history = discount = bon
        if isinstance(pe_history, pd.Series) and pe_history.notna().any():
            pe_history_safe = pe_history.replace(0, np.nan)
            df["_pe_discount"] = (pe_history_safe - pe_current) / pe_history_safe.abs()
        else:
            # Pas d'historique: estimer depuis le niveau actuel
            # P/E bas dans l'univers = probablement un discount
            df["_pe_discount"] = (df["_pe"].median() - pe_current) / df["_pe"].median()
        
        # Remplir NaN et ranker
        df["_pe_discount"] = df["_pe_discount"].fillna(0)
        df["_pe_discount_rank"] = df["_pe_discount"].rank(pct=True)
        
        # === FCF Yield Premium ===
        # (fcf_yield_current - fcf_yield_history) / fcf_yield_history
        # Positif si fcf_yield_current > fcf_yield_history = premium = bon
        if isinstance(fcf_yield_history, pd.Series) and fcf_yield_history.notna().any():
            fcf_history_safe = fcf_yield_history.replace(0, np.nan)
            df["_fcf_premium"] = (fcf_yield_current - fcf_history_safe) / fcf_history_safe.abs()
        else:
            # Pas d'historique: estimer depuis le niveau actuel
            df["_fcf_premium"] = (fcf_yield_current - df["_fcf_yield"].median()) / df["_fcf_yield"].median()
        
        # Remplir NaN et ranker
        df["_fcf_premium"] = df["_fcf_premium"].fillna(0)
        df["_fcf_premium_rank"] = df["_fcf_premium"].rank(pct=True)
        
        # Score MoS composite
        # PE discount: 20%, FCF premium: 20% -> total 40%
        w_pe_mos = self.components.get("pe_vs_history", 0.20) / 0.40
        w_fcf_mos = self.components.get("fcf_yield_vs_history", 0.20) / 0.40
        
        df["_mos_score"] = (
            w_pe_mos * df["_pe_discount_rank"] +
            w_fcf_mos * df["_fcf_premium_rank"]
        ).clip(0, 1)
        
        return df


def score_value_v30(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fonction helper pour calculer le score Value v3.0.
    
    Args:
        df: DataFrame avec métriques
    
    Returns:
        DataFrame avec score_value_v30 ajouté
    """
    scorer = ValueScorerV30()
    return scorer.score_universe(df)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test avec données synthétiques
    test_data = pd.DataFrame({
        "symbol": ["AAPL", "MSFT", "JNJ", "XOM", "BAC"],
        "sector": ["Technology", "Technology", "Healthcare", "Energy", "Financials"],
        "fcf_yield": [0.04, 0.03, 0.06, 0.10, 0.08],
        "ev_ebit": [25, 30, 18, 8, 10],
        "pe_ratio": [28, 35, 15, 10, 9],
        # Historiques (simulés)
        "pe_5y_avg": [32, 30, 18, 12, 11],        # AAPL: discount, MSFT: premium
        "fcf_yield_5y_avg": [0.035, 0.028, 0.055, 0.08, 0.07],
    })
    
    result = score_value_v30(test_data)
    
    print("\n" + "=" * 60)
    print("TEST VALUE v3.0 - Cross-Section + Margin of Safety")
    print("=" * 60)
    print(result[["symbol", "pe_ratio", "pe_5y_avg", "_pe_discount", "score_value_v30"]].to_string())
    print("\nNote: AAPL a un P/E de 28 vs historique 32 = DISCOUNT = bon MoS")
    print("      MSFT a un P/E de 35 vs historique 30 = PREMIUM = mauvais MoS")
