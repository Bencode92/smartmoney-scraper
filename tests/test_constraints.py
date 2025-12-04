"""Tests unitaires pour les contraintes de portefeuille SmartMoney v2.4

Ces tests vérifient que l'optimiseur respecte bien:
- La contrainte de poids maximum par position (max_weight)
- La contrainte de poids maximum par secteur (max_sector)
- La somme des poids = 100%
- Le nombre min/max de positions

Usage:
    pytest tests/test_constraints.py -v
    python -m pytest tests/test_constraints.py -v

Date: 4 décembre 2025
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine_v23 import SmartMoneyEngineV23


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_universe():
    """Crée un univers de test avec des données simulées."""
    np.random.seed(42)
    n_tickers = 50
    
    # Distribution sectorielle déséquilibrée pour tester les contraintes
    sectors = (
        ["Technology"] * 20 +      # 40% Tech - devrait déclencher contrainte secteur
        ["Financial Services"] * 15 +  # 30% Finance
        ["Healthcare"] * 10 +      # 20% Health
        ["Consumer Defensive"] * 5  # 10% Consumer
    )
    
    df = pd.DataFrame({
        "symbol": [f"TEST{i:02d}" for i in range(n_tickers)],
        "company": [f"Test Company {i}" for i in range(n_tickers)],
        "sector": sectors,
        "industry": ["Test Industry"] * n_tickers,
        "score_composite": np.random.uniform(0.5, 0.95, n_tickers),
        "score_sm": np.random.uniform(0.3, 0.9, n_tickers),
        "score_insider": np.random.uniform(0.2, 0.8, n_tickers),
        "score_momentum": np.random.uniform(0.4, 0.9, n_tickers),
        "score_quality": np.random.uniform(0.5, 0.95, n_tickers),
        "score_value": np.random.uniform(0.5, 0.9, n_tickers),
        "score_risk": np.random.uniform(0.4, 0.8, n_tickers),
        "buffett_score": np.random.uniform(0.3, 0.9, n_tickers),
        "vol_30d": np.random.uniform(15, 40, n_tickers),
        "perf_3m": np.random.uniform(-10, 20, n_tickers),
        "perf_ytd": np.random.uniform(-5, 30, n_tickers),
        "rsi": np.random.uniform(30, 70, n_tickers),
        "td_price": np.random.uniform(50, 500, n_tickers),
        "gp_buys": np.random.randint(0, 10, n_tickers),
        "gp_tier": np.random.choice(["A", "B", "C", "D"], n_tickers),
        "insider_buys": np.random.randint(0, 5, n_tickers),
        "roe": np.random.uniform(5, 35, n_tickers),
        "debt_equity": np.random.uniform(0.1, 2.0, n_tickers),
        "net_margin": np.random.uniform(5, 25, n_tickers),
        "current_ratio": np.random.uniform(1.0, 3.0, n_tickers),
    })
    
    return df


@pytest.fixture
def engine_with_mock_data(mock_universe):
    """Engine initialisé avec données de test."""
    engine = SmartMoneyEngineV23()
    engine.universe = mock_universe.copy()
    engine.constraints = {
        "min_positions": 12,
        "max_positions": 20,
        "max_weight": 0.12,
        "max_sector": 0.30,
    }
    return engine


@pytest.fixture
def engine_with_extreme_concentration(mock_universe):
    """Engine avec scores très concentrés pour tester les limites."""
    engine = SmartMoneyEngineV23()
    df = mock_universe.copy()
    
    # Créer des scores très élevés pour quelques tickers Tech
    # pour forcer une concentration maximale
    df.loc[df["sector"] == "Technology", "score_composite"] = 0.99
    df.loc[df["sector"] != "Technology", "score_composite"] = 0.50
    
    engine.universe = df
    engine.constraints = {
        "min_positions": 12,
        "max_positions": 20,
        "max_weight": 0.12,
        "max_sector": 0.30,
    }
    return engine


# =============================================================================
# TESTS DES CONTRAINTES DE POIDS PAR POSITION
# =============================================================================

class TestMaxWeightConstraint:
    """Tests de la contrainte de poids maximum par position."""
    
    def test_max_weight_respected(self, engine_with_mock_data):
        """Vérifie que le poids max par position est respecté."""
        engine = engine_with_mock_data
        engine.optimize()
        
        max_weight_limit = engine.constraints["max_weight"]
        max_weight_actual = engine.portfolio["weight"].max()
        
        # Tolérance de 0.5% pour les arrondis
        tolerance = 0.005
        
        assert max_weight_actual <= max_weight_limit + tolerance, \
            f"Poids max {max_weight_actual:.2%} dépasse la limite {max_weight_limit:.2%}"
    
    def test_max_weight_with_extreme_scores(self, engine_with_extreme_concentration):
        """Vérifie la contrainte même avec des scores très concentrés."""
        engine = engine_with_extreme_concentration
        engine.optimize()
        
        max_weight_limit = engine.constraints["max_weight"]
        max_weight_actual = engine.portfolio["weight"].max()
        
        tolerance = 0.005
        
        assert max_weight_actual <= max_weight_limit + tolerance, \
            f"Poids max {max_weight_actual:.2%} dépasse la limite {max_weight_limit:.2%} " \
            f"(même avec scores extrêmes)"
    
    def test_all_positions_under_cap(self, engine_with_mock_data):
        """Vérifie que TOUTES les positions sont sous le cap."""
        engine = engine_with_mock_data
        engine.optimize()
        
        max_weight_limit = engine.constraints["max_weight"]
        tolerance = 0.005
        
        over_cap = engine.portfolio[engine.portfolio["weight"] > max_weight_limit + tolerance]
        
        assert len(over_cap) == 0, \
            f"{len(over_cap)} positions dépassent le cap: " \
            f"{over_cap[['symbol', 'weight']].to_dict('records')}"


# =============================================================================
# TESTS DES CONTRAINTES SECTORIELLES
# =============================================================================

class TestMaxSectorConstraint:
    """Tests de la contrainte de poids maximum par secteur."""
    
    def test_max_sector_respected(self, engine_with_mock_data):
        """Vérifie que le poids max par secteur est respecté."""
        engine = engine_with_mock_data
        engine.optimize()
        
        max_sector_limit = engine.constraints["max_sector"]
        sector_weights = engine.portfolio.groupby("sector")["weight"].sum()
        max_sector_actual = sector_weights.max()
        
        tolerance = 0.005
        
        assert max_sector_actual <= max_sector_limit + tolerance, \
            f"Secteur max {max_sector_actual:.2%} dépasse la limite {max_sector_limit:.2%}"
    
    def test_max_sector_with_tech_heavy_universe(self, engine_with_extreme_concentration):
        """Vérifie la contrainte sectorielle avec univers très Tech."""
        engine = engine_with_extreme_concentration
        engine.optimize()
        
        max_sector_limit = engine.constraints["max_sector"]
        sector_weights = engine.portfolio.groupby("sector")["weight"].sum()
        
        tolerance = 0.005
        
        for sector, weight in sector_weights.items():
            assert weight <= max_sector_limit + tolerance, \
                f"Secteur {sector} = {weight:.2%} dépasse la limite {max_sector_limit:.2%}"
    
    def test_all_sectors_under_cap(self, engine_with_mock_data):
        """Vérifie que TOUS les secteurs sont sous le cap."""
        engine = engine_with_mock_data
        engine.optimize()
        
        max_sector_limit = engine.constraints["max_sector"]
        sector_weights = engine.portfolio.groupby("sector")["weight"].sum()
        
        tolerance = 0.005
        
        over_cap_sectors = sector_weights[sector_weights > max_sector_limit + tolerance]
        
        assert len(over_cap_sectors) == 0, \
            f"Secteurs dépassant le cap: {over_cap_sectors.to_dict()}"


# =============================================================================
# TESTS DE COHÉRENCE DES POIDS
# =============================================================================

class TestWeightsCoherence:
    """Tests de cohérence des poids du portefeuille."""
    
    def test_weights_sum_to_one(self, engine_with_mock_data):
        """Vérifie que la somme des poids = 100%."""
        engine = engine_with_mock_data
        engine.optimize()
        
        total = engine.portfolio["weight"].sum()
        
        assert abs(total - 1.0) < 0.001, \
            f"Somme des poids {total:.4f} ≠ 1.0"
    
    def test_all_weights_positive(self, engine_with_mock_data):
        """Vérifie que tous les poids sont positifs."""
        engine = engine_with_mock_data
        engine.optimize()
        
        min_weight = engine.portfolio["weight"].min()
        
        assert min_weight > 0, \
            f"Poids négatif trouvé: {min_weight}"
    
    def test_no_nan_weights(self, engine_with_mock_data):
        """Vérifie qu'il n'y a pas de poids NaN."""
        engine = engine_with_mock_data
        engine.optimize()
        
        nan_count = engine.portfolio["weight"].isna().sum()
        
        assert nan_count == 0, \
            f"{nan_count} poids sont NaN"


# =============================================================================
# TESTS DU NOMBRE DE POSITIONS
# =============================================================================

class TestPositionCount:
    """Tests du nombre de positions dans le portefeuille."""
    
    def test_min_positions(self, engine_with_mock_data):
        """Vérifie le nombre minimum de positions."""
        engine = engine_with_mock_data
        engine.optimize()
        
        min_pos = engine.constraints["min_positions"]
        n_positions = len(engine.portfolio)
        
        # Note: peut être inférieur si l'univers filtré est trop petit
        if len(engine.universe) >= min_pos:
            assert n_positions >= min_pos, \
                f"Seulement {n_positions} positions, minimum {min_pos} requis"
    
    def test_max_positions(self, engine_with_mock_data):
        """Vérifie le nombre maximum de positions."""
        engine = engine_with_mock_data
        engine.optimize()
        
        max_pos = engine.constraints["max_positions"]
        n_positions = len(engine.portfolio)
        
        assert n_positions <= max_pos, \
            f"{n_positions} positions dépasse le maximum {max_pos}"


# =============================================================================
# TESTS DE COHÉRENCE VOLATILITÉ
# =============================================================================

class TestVolatilityCoherence:
    """Tests de cohérence des métriques de volatilité."""
    
    def test_portfolio_vol_less_than_weighted_sum(self, engine_with_mock_data):
        """Vérifie que la vol portfolio < somme pondérée des vols individuelles."""
        engine = engine_with_mock_data
        engine.optimize()
        
        if "vol_30d" not in engine.portfolio.columns:
            pytest.skip("vol_30d non disponible")
        
        # Somme pondérée des vols individuelles (sans diversification)
        weighted_vol_sum = (
            engine.portfolio["weight"] * engine.portfolio["vol_30d"].fillna(25)
        ).sum()
        
        # Vol portfolio (avec diversification) devrait être calculée différemment
        # mais au minimum elle ne devrait pas être supérieure à la somme pondérée
        portfolio_vol = engine.portfolio_metrics.get("vol_30d", 0)
        
        if portfolio_vol and portfolio_vol > 0:
            assert portfolio_vol <= weighted_vol_sum * 1.1, \
                f"Vol portfolio {portfolio_vol:.1f}% semble incohérente " \
                f"(somme pondérée: {weighted_vol_sum:.1f}%)"


# =============================================================================
# TESTS D'INTÉGRATION
# =============================================================================

class TestIntegration:
    """Tests d'intégration end-to-end."""
    
    def test_full_pipeline(self, engine_with_mock_data):
        """Test du pipeline complet: scores → filtres → optimize."""
        engine = engine_with_mock_data
        
        # Le score_composite est déjà dans le mock
        engine.optimize()
        
        # Vérifications de base
        assert len(engine.portfolio) > 0, "Portefeuille vide"
        assert "weight" in engine.portfolio.columns, "Colonne weight manquante"
        assert engine.portfolio["weight"].sum() > 0.99, "Poids ne somment pas à ~1"
    
    def test_constraints_all_satisfied(self, engine_with_mock_data):
        """Vérifie que TOUTES les contraintes sont satisfaites."""
        engine = engine_with_mock_data
        engine.optimize()
        
        constraints = engine.constraints
        tolerance = 0.005
        
        # 1. Max weight
        max_weight_actual = engine.portfolio["weight"].max()
        assert max_weight_actual <= constraints["max_weight"] + tolerance, \
            f"Contrainte max_weight violée"
        
        # 2. Max sector
        if "sector" in engine.portfolio.columns:
            sector_weights = engine.portfolio.groupby("sector")["weight"].sum()
            max_sector_actual = sector_weights.max()
            assert max_sector_actual <= constraints["max_sector"] + tolerance, \
                f"Contrainte max_sector violée"
        
        # 3. Position count
        n_pos = len(engine.portfolio)
        assert n_pos <= constraints["max_positions"], \
            f"Contrainte max_positions violée"
        
        # 4. Weights sum
        assert abs(engine.portfolio["weight"].sum() - 1.0) < 0.001, \
            f"Somme des poids ≠ 1"


# =============================================================================
# TESTS DE RÉGRESSION
# =============================================================================

class TestRegression:
    """Tests de régression pour s'assurer que les bugs corrigés ne reviennent pas."""
    
    def test_no_post_normalization_cap_violation(self, engine_with_mock_data):
        """
        Régression v2.4: Vérifie que le cap n'est pas violé après renormalisation.
        
        Bug corrigé: weights = min(weights, cap) puis normalize() → redépassait le cap
        """
        engine = engine_with_mock_data
        
        # Forcer des scores très élevés sur quelques tickers
        engine.universe.loc[:5, "score_composite"] = 0.99
        
        engine.optimize()
        
        max_weight_limit = engine.constraints["max_weight"]
        max_weight_actual = engine.portfolio["weight"].max()
        
        tolerance = 0.005
        
        assert max_weight_actual <= max_weight_limit + tolerance, \
            f"RÉGRESSION: Cap violé après renormalisation " \
            f"({max_weight_actual:.2%} > {max_weight_limit:.2%})"
    
    def test_sector_constraint_actually_enforced(self, engine_with_extreme_concentration):
        """
        Régression v2.4: Vérifie que la contrainte sectorielle est IMPLÉMENTÉE.
        
        Bug corrigé: max_sector était dans la config mais jamais appliquée
        """
        engine = engine_with_extreme_concentration
        engine.optimize()
        
        max_sector_limit = engine.constraints["max_sector"]
        sector_weights = engine.portfolio.groupby("sector")["weight"].sum()
        
        tech_weight = sector_weights.get("Technology", 0)
        
        tolerance = 0.005
        
        assert tech_weight <= max_sector_limit + tolerance, \
            f"RÉGRESSION: Contrainte sectorielle non enforced " \
            f"(Tech = {tech_weight:.2%} > limite {max_sector_limit:.2%})"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
