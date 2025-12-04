"""SmartMoney v2.4 — Score de Crowding

Mesure le niveau de "crowding" (sur-détention) d'un titre par les hedge funds.
Utilisé pour pénaliser les positions trop populaires et réduire le risque
de deleveraging synchronisé.

Formule:
    crowding_score = (
        0.4 * nb_funds_normalized +
        0.3 * avg_weight_normalized +
        0.3 * buying_pressure
    )

    SmartMoneyEffectif = SmartMoneyRaw * (1 - penalty * crowding_score)

Usage:
    from src.scoring.crowding_score import CrowdingScorer
    
    scorer = CrowdingScorer()
    df = scorer.score_universe(df)
    # df now has 'crowding_score' and 'smart_money_adjusted'

Date: Décembre 2025
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


class CrowdingScorer:
    """
    Calcule le score de crowding pour chaque titre.
    
    Un score élevé indique que le titre est:
    - Détenu par beaucoup de hedge funds
    - Avec des poids importants
    - Avec une pression achéteuse récente (tous achètent en même temps)
    
    Attributes:
        weight_nb_funds: Poids du nombre de fonds (défaut: 0.4)
        weight_avg_position: Poids de la position moyenne (défaut: 0.3)
        weight_buying_pressure: Poids de la pression achéteuse (défaut: 0.3)
        crowding_penalty: Pénalité max sur Smart Money (défaut: 0.5)
    """
    
    def __init__(
        self,
        weight_nb_funds: float = 0.40,
        weight_avg_position: float = 0.30,
        weight_buying_pressure: float = 0.30,
        crowding_penalty: float = 0.50,
    ):
        self.weight_nb_funds = weight_nb_funds
        self.weight_avg_position = weight_avg_position
        self.weight_buying_pressure = weight_buying_pressure
        self.crowding_penalty = crowding_penalty
        
        # Vérifier que les poids somment à 1
        total = weight_nb_funds + weight_avg_position + weight_buying_pressure
        assert abs(total - 1.0) < 0.01, f"Poids doivent sommer à 1, got {total}"
    
    def score_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le score de crowding pour tout l'univers.
        
        Args:
            df: DataFrame avec colonnes:
                - nb_hedge_funds: Nombre de hedge funds détenant le titre
                - avg_hf_weight: Poids moyen dans les portefeuilles HF (%)
                - hf_change_3m: Changement du nombre de HF sur 3 mois
                - smart_money_score: Score Smart Money brut (optionnel)
        
        Returns:
            DataFrame avec colonnes ajoutées:
                - crowding_score: Score de crowding [0, 1]
                - crowding_percentile: Percentile dans l'univers
                - crowding_tier: 'low', 'medium', 'high', 'extreme'
                - smart_money_adjusted: Score SM ajusté (si SM présent)
        """
        df = df.copy()
        
        # 1. Normaliser le nombre de hedge funds (percentile)
        if "nb_hedge_funds" in df.columns:
            df["_nb_funds_norm"] = df["nb_hedge_funds"].rank(pct=True)
        else:
            df["_nb_funds_norm"] = 0.5
        
        # 2. Normaliser le poids moyen (percentile)
        if "avg_hf_weight" in df.columns:
            df["_avg_weight_norm"] = df["avg_hf_weight"].rank(pct=True)
        else:
            df["_avg_weight_norm"] = 0.5
        
        # 3. Calculer la pression achéteuse
        # = proportion de fonds qui ont augmenté leur position
        if "hf_change_3m" in df.columns:
            # Si positif = plus de fonds achètent
            df["_buying_pressure"] = (df["hf_change_3m"] > 0).astype(float)
            # Normaliser par l'amplitude
            df["_buying_pressure"] = df["hf_change_3m"].clip(lower=0).rank(pct=True)
        else:
            df["_buying_pressure"] = 0.5
        
        # 4. Score composite de crowding
        df["crowding_score"] = (
            self.weight_nb_funds * df["_nb_funds_norm"] +
            self.weight_avg_position * df["_avg_weight_norm"] +
            self.weight_buying_pressure * df["_buying_pressure"]
        )
        
        # 5. Percentile de crowding
        df["crowding_percentile"] = df["crowding_score"].rank(pct=True)
        
        # 6. Tier de crowding
        df["crowding_tier"] = pd.cut(
            df["crowding_percentile"],
            bins=[0, 0.5, 0.75, 0.90, 1.0],
            labels=["low", "medium", "high", "extreme"],
            include_lowest=True,
        )
        
        # 7. Ajuster le score Smart Money si présent
        if "smart_money_score" in df.columns:
            # Pénalité = crowding_score * penalty_factor
            # Pour un titre très crowdé (score=1), on réduit SM de 50%
            penalty = self.crowding_penalty * df["crowding_score"]
            df["smart_money_adjusted"] = df["smart_money_score"] * (1 - penalty)
        
        # Nettoyer les colonnes temporaires
        df = df.drop(columns=["_nb_funds_norm", "_avg_weight_norm", "_buying_pressure"])
        
        return df
    
    def get_crowded_positions(self, df: pd.DataFrame, top_pct: float = 0.10) -> pd.DataFrame:
        """
        Retourne les positions les plus crowdées.
        
        Args:
            df: DataFrame avec crowding_score
            top_pct: Percentile (défaut: top 10%)
        
        Returns:
            DataFrame des positions les plus crowdées
        """
        if "crowding_score" not in df.columns:
            df = self.score_universe(df)
        
        threshold = df["crowding_score"].quantile(1 - top_pct)
        return df[df["crowding_score"] >= threshold].sort_values(
            "crowding_score", ascending=False
        )
    
    def diagnose_portfolio_crowding(self, portfolio_df: pd.DataFrame, universe_df: pd.DataFrame) -> Dict:
        """
        Analyse le crowding du portefeuille vs l'univers.
        
        Returns:
            Dict avec:
            - avg_crowding: Crowding moyen du portefeuille
            - pct_in_top_10: % du portefeuille dans le top 10% crowdé
            - extreme_positions: Positions en tier 'extreme'
        """
        # Scorer l'univers si pas fait
        if "crowding_score" not in universe_df.columns:
            universe_df = self.score_universe(universe_df)
        
        # Matcher le portefeuille
        portfolio_symbols = set(portfolio_df["symbol"].values)
        portfolio_crowding = universe_df[universe_df["symbol"].isin(portfolio_symbols)]
        
        if portfolio_crowding.empty:
            return {"error": "Aucun match trouvé"}
        
        # Métriques
        avg_crowding = portfolio_crowding["crowding_score"].mean()
        universe_avg = universe_df["crowding_score"].mean()
        
        # % dans le top 10%
        top_10_threshold = universe_df["crowding_score"].quantile(0.90)
        pct_in_top_10 = (portfolio_crowding["crowding_score"] >= top_10_threshold).mean() * 100
        
        # Positions extrêmes
        extreme = portfolio_crowding[portfolio_crowding["crowding_tier"] == "extreme"]
        
        return {
            "portfolio_avg_crowding": round(avg_crowding, 3),
            "universe_avg_crowding": round(universe_avg, 3),
            "crowding_vs_universe": round(avg_crowding - universe_avg, 3),
            "pct_in_top_10_crowded": round(pct_in_top_10, 1),
            "nb_extreme_positions": len(extreme),
            "extreme_positions": extreme["symbol"].tolist() if not extreme.empty else [],
            "warning": pct_in_top_10 > 30,  # Alerte si >30% dans top 10% crowdé
        }


# =============================================================================
# CONSTANTES ET CONFIGURATION
# =============================================================================

# Titres connus comme très crowdés (historiquement)
KNOWN_CROWDED_TICKERS = [
    "MSFT", "AAPL", "GOOGL", "GOOG", "META", "AMZN",  # Megacaps tech
    "V", "MA",  # Payments (favoris HF)
    "UNH",  # Healthcare favorite
    "NVDA",  # AI darling
]

# Seuils de crowding
CROWDING_THRESHOLDS = {
    "low": 0.25,       # < 25% = peu crowdé
    "medium": 0.50,    # 25-50% = normal
    "high": 0.75,      # 50-75% = crowdé
    "extreme": 0.90,   # > 90% = très crowdé → risque
}


if __name__ == "__main__":
    # Test rapide
    import numpy as np
    
    # Créer des données de test
    np.random.seed(42)
    test_df = pd.DataFrame({
        "symbol": ["AAPL", "MSFT", "V", "JPM", "XOM", "PG", "KO", "WMT"],
        "nb_hedge_funds": [150, 140, 120, 80, 60, 40, 30, 25],
        "avg_hf_weight": [5.2, 4.8, 3.5, 2.0, 1.5, 1.0, 0.8, 0.5],
        "hf_change_3m": [10, 8, 5, 2, -3, 0, -2, 1],
        "smart_money_score": [0.85, 0.82, 0.78, 0.65, 0.55, 0.50, 0.45, 0.40],
    })
    
    scorer = CrowdingScorer()
    result = scorer.score_universe(test_df)
    
    print("\n" + "=" * 60)
    print("TEST CROWDING SCORER")
    print("=" * 60)
    print(result[["symbol", "crowding_score", "crowding_tier", "smart_money_adjusted"]].to_string())
    
    print("\nTop 10% les plus crowdés:")
    crowded = scorer.get_crowded_positions(result, top_pct=0.25)
    print(crowded[["symbol", "crowding_score", "crowding_tier"]].to_string())
