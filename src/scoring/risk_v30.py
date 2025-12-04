"""SmartMoney v3.0 — Risk Scorer "Buffett-Quant"

Risk = "Éviter la perte permanente de capital"

Différence avec v2.3:
- v2.3: "Low vol" académique (volatilité basse = bon)
- v3.0: Éviter les profils à risque de PERTE PERMANENTE

Philosophie Buffett:
"Rule #1: Don't lose money.
Rule #2: Don't forget rule #1."

Ce n'est PAS un facteur "low vol".
C'est une PÉNALISATION des profils susceptibles de générer
une perte PERMANENTE de capital:
- Fort levier (risque de faillite)
- Drawdowns extrêmes récurrents
- Volatilité excessive

Composantes v3.0:
- Bilan (50%): Leverage, coverage
- Drawdown (30%): Max DD 5 ans, recovery
- Volatilité (20%): Vol annuelle

Score INVERSÉ: score élevé = FAIBLE risque = BON

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v30 import RISK_V30
except ImportError:
    RISK_V30 = {
        "mode": "permanent_loss_avoidance",
        "components": {
            "leverage_safe": 0.25,
            "debt_ebitda_safe": 0.15,
            "coverage_safe": 0.10,
            "max_dd_5y": 0.20,
            "dd_recovery": 0.10,
            "volatility_annual": 0.20,
        },
        "inverted": True,
    }

logger = logging.getLogger(__name__)


@dataclass
class RiskScoreV30:
    """Résultat du scoring Risk v3.0."""
    total: float
    balance_sheet_score: float      # 50%
    drawdown_score: float           # 30%
    volatility_score: float         # 20%
    components: Dict[str, float] = field(default_factory=dict)


class RiskScorerV30:
    """
    Calcule le score Risk v3.0 "Buffett-Quant".
    
    Objectif: Identifier et pénaliser les entreprises
    à risque de perte PERMANENTE de capital.
    
    Ce n'est PAS:
    - Un facteur "low vol" académique
    - Un ranking de volatilité
    
    C'est:
    - Une pénalisation du risque de FAILLITE (levier)
    - Une pénalisation des DRAWDOWNS extrêmes
    - Un filtre de sécurité
    
    Score INVERSÉ: score élevé = risque FAIBLE = BON
    
    Example:
        >>> scorer = RiskScorerV30()
        >>> df = scorer.score_universe(df)
        >>> print(df[["symbol", "score_risk_v30", "debt_equity"]].head())
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or RISK_V30
        self.components = self.config["components"]
    
    def score_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le score Risk v3.0 pour tout l'univers.
        
        Args:
            df: DataFrame avec colonnes:
                - debt_equity ou total_debt, equity
                - debt_ebitda ou net_debt, ebitda
                - interest_coverage
                - max_drawdown_5y (optionnel)
                - volatility_annual (optionnel)
        
        Returns:
            DataFrame avec score_risk_v30 et composantes
        """
        df = df.copy()
        
        # === 1. BILAN (50%) ===
        df = self._score_balance_sheet_risk(df)
        
        # === 2. DRAWDOWN (30%) ===
        df = self._score_drawdown_risk(df)
        
        # === 3. VOLATILITÉ (20%) ===
        df = self._score_volatility_risk(df)
        
        # === COMPOSITE (INVERSÉ) ===
        # Score élevé = risque FAIBLE = BON
        df["score_risk_v30"] = (
            0.50 * df["_balance_sheet_risk_score"] +
            0.30 * df["_drawdown_risk_score"] +
            0.20 * df["_volatility_risk_score"]
        ).round(3)
        
        logger.info(
            f"Risk v3.0 calculé: "
            f"mean={df['score_risk_v30'].mean():.3f}, "
            f"std={df['score_risk_v30'].std():.3f}"
        )
        
        return df
    
    def _score_balance_sheet_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score risque bilan = leverage et coverage.
        
        Score élevé = bilan SOLIDE = risque FAIBLE = BON
        """
        # === Debt/Equity ===
        if "debt_equity" in df.columns:
            df["_de_ratio"] = df["debt_equity"]
        elif "total_debt" in df.columns and "equity" in df.columns:
            df["_de_ratio"] = df["total_debt"] / df["equity"].replace(0, np.nan)
        else:
            df["_de_ratio"] = np.nan
        
        # Score leverage: D/E bas = bon score
        # D/E 0 = 1.0, D/E 3+ = 0.0
        df["_leverage_score"] = (1 - df["_de_ratio"].clip(0, 3) / 3).fillna(0.5)
        
        # === Debt/EBITDA ===
        if "debt_ebitda" in df.columns:
            df["_debt_ebitda"] = df["debt_ebitda"]
        elif "net_debt" in df.columns and "ebitda" in df.columns:
            df["_debt_ebitda"] = df["net_debt"] / df["ebitda"].replace(0, np.nan)
        elif "total_debt" in df.columns and "ebitda" in df.columns:
            cash = df.get("cash", 0)
            df["_debt_ebitda"] = (df["total_debt"] - cash) / df["ebitda"].replace(0, np.nan)
        else:
            df["_debt_ebitda"] = np.nan
        
        # Score debt/EBITDA: ratio bas = bon score
        # ND/EBITDA 0 = 1.0, ND/EBITDA 4+ = 0.0
        df["_debt_ebitda_score"] = (1 - df["_debt_ebitda"].clip(0, 4) / 4).fillna(0.5)
        
        # === Interest Coverage ===
        if "interest_coverage" in df.columns:
            df["_coverage"] = df["interest_coverage"]
        else:
            ebit = df.get("ebit", np.nan)
            interest = df.get("interest_expense", np.nan)
            if isinstance(ebit, pd.Series) and isinstance(interest, pd.Series):
                df["_coverage"] = ebit / interest.replace(0, np.nan).abs()
            else:
                df["_coverage"] = np.nan
        
        # Score coverage: élevé = bon score
        # Coverage 0 = 0.0, Coverage 10+ = 1.0
        df["_coverage_score"] = (df["_coverage"].clip(0, 10) / 10).fillna(0.5)
        
        # Score bilan composite
        # Leverage: 25%, Debt/EBITDA: 15%, Coverage: 10% -> total 50%
        w_lev = self.components.get("leverage_safe", 0.25) / 0.50
        w_debt = self.components.get("debt_ebitda_safe", 0.15) / 0.50
        w_cov = self.components.get("coverage_safe", 0.10) / 0.50
        
        df["_balance_sheet_risk_score"] = (
            w_lev * df["_leverage_score"] +
            w_debt * df["_debt_ebitda_score"] +
            w_cov * df["_coverage_score"]
        ).clip(0, 1)
        
        return df
    
    def _score_drawdown_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score risque drawdown = max DD et recovery.
        
        Score élevé = drawdowns FAIBLES = risque FAIBLE = BON
        """
        # === Max Drawdown 5Y ===
        if "max_drawdown_5y" in df.columns:
            df["_max_dd"] = df["max_drawdown_5y"].abs()  # Toujours positif
        elif "max_drawdown" in df.columns:
            df["_max_dd"] = df["max_drawdown"].abs()
        else:
            # Fallback: estimer depuis la volatilité ou utiliser valeur neutre
            vol = df.get("volatility_annual", df.get("volatility", np.nan))
            if isinstance(vol, pd.Series):
                # Estimation grossière: DD ~ 2.5 * vol
                df["_max_dd"] = (vol * 2.5).fillna(0.30)  # 30% par défaut
            else:
                df["_max_dd"] = 0.30
        
        # Score max DD: DD faible = bon score
        # DD 0% = 1.0, DD 60%+ = 0.0
        df["_max_dd_score"] = (1 - df["_max_dd"].clip(0, 0.60) / 0.60).fillna(0.5)
        
        # === DD Recovery ===
        # Si disponible, sinon estimer
        if "dd_recovery_months" in df.columns:
            # Recovery rapide = bon
            # 0 mois = 1.0, 24+ mois = 0.0
            df["_recovery_score"] = (1 - df["dd_recovery_months"].clip(0, 24) / 24).fillna(0.5)
        else:
            # Fallback: proxy via volatilité (vol basse = recovery rapide)
            vol = df.get("_max_dd", 0.30)
            if isinstance(vol, pd.Series):
                df["_recovery_score"] = (1 - vol / 0.60).clip(0, 1).fillna(0.5)
            else:
                df["_recovery_score"] = 0.5
        
        # Score drawdown composite
        # Max DD: 20%, Recovery: 10% -> total 30%
        w_dd = self.components.get("max_dd_5y", 0.20) / 0.30
        w_rec = self.components.get("dd_recovery", 0.10) / 0.30
        
        df["_drawdown_risk_score"] = (
            w_dd * df["_max_dd_score"] +
            w_rec * df["_recovery_score"]
        ).clip(0, 1)
        
        return df
    
    def _score_volatility_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score risque volatilité.
        
        Score élevé = volatilité FAIBLE = risque FAIBLE = BON
        """
        # Récupérer la volatilité
        if "volatility_annual" in df.columns:
            df["_volatility"] = df["volatility_annual"]
        elif "volatility" in df.columns:
            df["_volatility"] = df["volatility"]
        elif "beta" in df.columns:
            # Proxy: beta * vol marché (~16%)
            df["_volatility"] = df["beta"] * 0.16
        else:
            df["_volatility"] = 0.25  # Valeur par défaut
        
        # Score volatilité: vol faible = bon score
        # Vol 0% = 1.0, Vol 60%+ = 0.0
        df["_volatility_risk_score"] = (1 - df["_volatility"].clip(0, 0.60) / 0.60).fillna(0.5)
        
        return df


def score_risk_v30(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fonction helper pour calculer le score Risk v3.0.
    
    Args:
        df: DataFrame avec métriques
    
    Returns:
        DataFrame avec score_risk_v30 ajouté
    """
    scorer = RiskScorerV30()
    return scorer.score_universe(df)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test avec données synthétiques
    test_data = pd.DataFrame({
        "symbol": ["AAPL", "MSFT", "JNJ", "XOM", "HIGH_RISK"],
        "debt_equity": [1.5, 0.5, 0.4, 0.8, 4.0],
        "debt_ebitda": [1.0, 0.3, 0.5, 1.2, 5.0],
        "interest_coverage": [30, 50, 20, 8, 1.5],
        "max_drawdown_5y": [0.30, 0.25, 0.20, 0.40, 0.65],
        "volatility_annual": [0.28, 0.24, 0.18, 0.32, 0.55],
    })
    
    result = score_risk_v30(test_data)
    
    print("\n" + "=" * 60)
    print("TEST RISK v3.0 - Éviter la perte permanente de capital")
    print("=" * 60)
    print(result[["symbol", "debt_equity", "max_drawdown_5y", "score_risk_v30"]].to_string())
    print("\nNote: HIGH_RISK a D/E=4.0, DD=65% -> score très bas = risqué")
    print("      JNJ a D/E=0.4, DD=20% -> score élevé = sûr")
    print("\nRappel: score_risk_v30 élevé = risque FAIBLE = BON")
