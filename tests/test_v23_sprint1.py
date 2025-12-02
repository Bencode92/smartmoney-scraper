"""SmartMoney v2.3 — Tests Sprint 1

Tests pour:
- Configuration v2.3
- Filtres de liquidité
- Hard filters
- Look-ahead filter
- Data validator

Lancer avec: pytest tests/test_v23_sprint1.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

# Ajouter le repo au path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_universe():
    """Univers de test avec différents profils de liquidité."""
    return pd.DataFrame({
        "symbol": ["AAPL", "MSFT", "SMALL", "ILLIQ", "GOOD"],
        "market_cap": [3e12, 2.8e12, 500e6, 5e9, 50e9],
        "adv_usd": [10e9, 8e9, 1e6, 100e3, 50e6],
        "td_price": [180, 380, 5, 25, 100],
        "total_debt": [100e9, 80e9, 50e6, 2e9, 5e9],
        "equity": [60e9, 200e9, 100e6, 500e6, 20e9],
        "ebit": [100e9, 90e9, 10e6, 100e6, 3e9],
        "interest_expense": [3e9, 2e9, 5e6, 80e6, 100e6],
        "cash": [50e9, 100e9, 10e6, 100e6, 2e9],
        "revenue": [400e9, 200e9, 100e6, 1e9, 20e9],
        "net_income": [80e9, 70e9, 5e6, 50e6, 2e9],
    })


@pytest.fixture
def sample_fundamentals():
    """10 ans de fondamentaux fictifs."""
    return pd.DataFrame({
        "year": list(range(2015, 2025)),
        "revenue": [100e9 * (1.05 ** i) for i in range(10)],
        "ebit": [20e9 * (1.05 ** i) for i in range(10)],
        "net_income": [15e9 * (1.05 ** i) for i in range(10)],
        "fcf": [12e9 * (1.05 ** i) for i in range(10)],
        "total_debt": [30e9] * 10,
        "cash": [20e9] * 10,
        "equity": [80e9 * (1.03 ** i) for i in range(10)],
    })


@pytest.fixture
def high_leverage_data():
    """Données avec fort levier (doit être exclu)."""
    return pd.Series({
        "symbol": "RISKY",
        "total_debt": 100e9,
        "equity": 20e9,      # D/E = 5 > 3
        "ebit": 5e9,
        "interest_expense": 4e9,  # Coverage = 1.25 < 2.5
        "cash": 5e9,
        "revenue": 50e9,
        "net_income": 2e9,
    })


# =============================================================================
# TESTS CONFIG v2.3
# =============================================================================

class TestConfigV23:
    """Tests de la configuration v2.3."""
    
    def test_weights_sum_to_one(self):
        """Les poids v2.3 doivent sommer exactement à 1.0."""
        from config_v23 import WEIGHTS_V23
        
        total = sum(WEIGHTS_V23.values())
        assert abs(total - 1.0) < 0.001, f"Somme des poids = {total}, attendu 1.0"
    
    def test_all_weights_positive(self):
        """Tous les poids doivent être >= 0."""
        from config_v23 import WEIGHTS_V23
        
        for name, weight in WEIGHTS_V23.items():
            assert weight >= 0, f"Poids '{name}' = {weight} < 0"
    
    def test_smart_money_reduced(self):
        """smart_money doit être réduit par rapport à v2.2."""
        from config_v23 import WEIGHTS_V23
        from config import WEIGHTS
        
        assert WEIGHTS_V23["smart_money"] < WEIGHTS["smart_money"], \
            f"smart_money v2.3 ({WEIGHTS_V23['smart_money']}) >= v2.2 ({WEIGHTS['smart_money']})"
    
    def test_new_factors_present(self):
        """Les nouveaux facteurs (value, quality, risk) doivent être présents."""
        from config_v23 import WEIGHTS_V23
        
        assert "value" in WEIGHTS_V23
        assert "quality" in WEIGHTS_V23
        assert "risk" in WEIGHTS_V23
    
    def test_hard_filters_reasonable(self):
        """Hard filters dans des ranges raisonnables."""
        from config_v23 import HARD_FILTERS
        
        assert 1.0 <= HARD_FILTERS["max_debt_equity"] <= 5.0
        assert 2.0 <= HARD_FILTERS["max_debt_ebitda"] <= 6.0
        assert 1.5 <= HARD_FILTERS["min_interest_coverage"] <= 4.0


# =============================================================================
# TESTS LIQUIDITY FILTERS
# =============================================================================

class TestLiquidityFilters:
    """Tests des filtres de liquidité."""
    
    def test_filters_small_caps(self, sample_universe):
        """Exclut les small caps < $2B."""
        from src.filters.liquidity import apply_liquidity_filters
        
        filtered = apply_liquidity_filters(sample_universe, verbose=False)
        
        assert "SMALL" not in filtered["symbol"].values
        assert len(filtered) < len(sample_universe)
    
    def test_filters_illiquid(self, sample_universe):
        """Exclut les titres illiquides."""
        from src.filters.liquidity import apply_liquidity_filters
        
        filtered = apply_liquidity_filters(sample_universe, verbose=False)
        
        assert "ILLIQ" not in filtered["symbol"].values
    
    def test_keeps_large_liquid(self, sample_universe):
        """Garde les large caps liquides."""
        from src.filters.liquidity import apply_liquidity_filters
        
        filtered = apply_liquidity_filters(sample_universe, verbose=False)
        
        assert "AAPL" in filtered["symbol"].values
        assert "MSFT" in filtered["symbol"].values
    
    def test_check_single_liquid(self):
        """Test check_liquidity_single pour un titre liquide."""
        from src.filters.liquidity import check_liquidity_single
        
        result = check_liquidity_single(
            market_cap=100e9,
            adv_usd=500e6,
        )
        
        assert result["passes"] == True
    
    def test_check_single_illiquid(self):
        """Test check_liquidity_single pour un titre illiquide."""
        from src.filters.liquidity import check_liquidity_single
        
        result = check_liquidity_single(
            market_cap=500e6,  # < $2B
            adv_usd=1e6,       # < $5M
        )
        
        assert result["passes"] == False


# =============================================================================
# TESTS HARD FILTERS
# =============================================================================

class TestHardFilters:
    """Tests des hard filters."""
    
    def test_excludes_high_leverage(self, high_leverage_data):
        """Exclut les entreprises trop endettées."""
        from src.filters.hard_filters import check_hard_filters_single
        
        result = check_hard_filters_single(
            total_debt=high_leverage_data["total_debt"],
            equity=high_leverage_data["equity"],
            ebit=high_leverage_data["ebit"],
            interest_expense=high_leverage_data["interest_expense"],
            cash=high_leverage_data["cash"],
        )
        
        assert result["should_exclude"] == True
        assert len(result["reasons"]) > 0
    
    def test_keeps_healthy_company(self):
        """Garde les entreprises saines."""
        from src.filters.hard_filters import check_hard_filters_single
        
        result = check_hard_filters_single(
            total_debt=100e9,
            equity=60e9,        # D/E = 1.67
            ebit=100e9,
            interest_expense=3e9,  # Coverage = 33
            cash=50e9,
        )
        
        assert result["should_exclude"] == False
    
    def test_apply_hard_filters_dataframe(self, sample_universe):
        """Test apply_hard_filters sur DataFrame."""
        from src.filters.hard_filters import apply_hard_filters
        
        filtered = apply_hard_filters(sample_universe, verbose=False)
        
        # Doit avoir au moins quelques tickers restants
        assert len(filtered) > 0
        assert len(filtered) <= len(sample_universe)


# =============================================================================
# TESTS LOOK-AHEAD
# =============================================================================

class TestLookAhead:
    """Tests du filtre look-ahead."""
    
    def test_filters_future_data(self, sample_fundamentals):
        """Filtre les données non encore publiées."""
        from src.filters.look_ahead import filter_by_publication_date
        
        # Au 15 janvier 2024, les données 2023 ne sont pas encore publiées
        filtered = filter_by_publication_date(
            sample_fundamentals,
            as_of_date="2024-01-15",
        )
        
        # 2023 et 2024 doivent être exclus
        assert 2023 not in filtered["year"].values
        assert 2024 not in filtered["year"].values
    
    def test_keeps_old_data(self, sample_fundamentals):
        """Garde les données anciennes."""
        from src.filters.look_ahead import filter_by_publication_date
        
        filtered = filter_by_publication_date(
            sample_fundamentals,
            as_of_date="2024-06-01",
        )
        
        # 2022 doit être disponible en juin 2024
        assert 2022 in filtered["year"].values
    
    def test_get_latest_year(self):
        """Test get_latest_available_year."""
        from src.filters.look_ahead import get_latest_available_year
        
        # Mi-janvier → 2023 pas encore publié
        year = get_latest_available_year("2024-01-15")
        assert year <= 2022
        
        # Mi-avril → 2023 publié
        year = get_latest_available_year("2024-04-15")
        assert year == 2023


# =============================================================================
# TESTS DATA VALIDATOR
# =============================================================================

class TestDataValidator:
    """Tests du validateur de données."""
    
    def test_valid_row(self):
        """Ligne valide passe."""
        from src.validation.data_validator import DataValidator
        
        validator = DataValidator()
        row = pd.Series({
            "revenue": 100e9,
            "ebit": 20e9,
            "net_income": 15e9,
            "equity": 80e9,
            "total_debt": 30e9,
        })
        
        result = validator.validate_row(row, "TEST")
        
        assert result.is_valid == True
        assert len(result.errors) == 0
    
    def test_missing_required_field(self):
        """Champ obligatoire manquant = invalide."""
        from src.validation.data_validator import DataValidator
        
        validator = DataValidator()
        row = pd.Series({
            "revenue": 100e9,
            # ebit manquant
            "net_income": 15e9,
            "equity": 80e9,
            "total_debt": 30e9,
        })
        
        result = validator.validate_row(row, "TEST")
        
        assert result.is_valid == False
        assert any("ebit" in e.lower() for e in result.errors)
    
    def test_nan_value(self):
        """Valeur NaN = invalide."""
        from src.validation.data_validator import DataValidator
        
        validator = DataValidator()
        row = pd.Series({
            "revenue": 100e9,
            "ebit": np.nan,
            "net_income": 15e9,
            "equity": 80e9,
            "total_debt": 30e9,
        })
        
        result = validator.validate_row(row, "TEST")
        
        assert result.is_valid == False
    
    def test_winsorize_outlier(self):
        """Outliers winsorisés."""
        from src.validation.data_validator import DataValidator
        
        validator = DataValidator(winsorize_outliers=True)
        row = pd.Series({
            "revenue": 100e9,
            "ebit": 20e9,
            "net_income": 15e9,
            "equity": 80e9,
            "total_debt": 30e9,
            "market_cap": 100e15,  # Outlier
        })
        
        result = validator.validate_row(row, "TEST")
        
        assert result.is_valid == True
        assert result.cleaned_data["market_cap"] <= 5e13


# =============================================================================
# TESTS D'INTÉGRATION
# =============================================================================

class TestIntegration:
    """Tests d'intégration du pipeline."""
    
    def test_full_filter_pipeline(self, sample_universe):
        """Test du pipeline complet de filtrage."""
        from src.filters.liquidity import apply_liquidity_filters
        from src.filters.hard_filters import apply_hard_filters
        
        # 1. Filtres liquidité
        df1 = apply_liquidity_filters(sample_universe, verbose=False)
        
        # 2. Hard filters
        df2 = apply_hard_filters(df1, verbose=False)
        
        # Doit avoir moins de titres qu'au départ
        assert len(df2) < len(sample_universe)
        
        # Les titres restants doivent être "bons"
        for _, row in df2.iterrows():
            assert row["market_cap"] >= 2e9


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
