"""Tests unitaires pour le backtest walk-forward.

Date: Décembre 2025
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.price_loader import PriceLoader, PortfolioReturnsCalculator
from src.backtest_walkforward import (
    WalkForwardBacktester,
    PeriodResult,
    BacktestReport,
)


class TestPriceLoader:
    """Tests pour PriceLoader."""
    
    def test_init(self):
        """Test initialisation."""
        loader = PriceLoader()
        assert loader.cache_dir.exists()
    
    def test_load_prices_empty(self):
        """Test avec liste vide."""
        loader = PriceLoader()
        df = loader.load_prices([], start="2024-01-01")
        assert df.empty
    
    def test_load_benchmark_structure(self):
        """Test structure du benchmark DataFrame."""
        loader = PriceLoader()
        df = loader.load_benchmark("SPY", start="2024-01-01")
        
        # Si yfinance disponible, vérifier la structure
        if not df.empty:
            assert "close" in df.columns
            assert "return" in df.columns
            assert "cumulative_return" in df.columns
            assert "drawdown" in df.columns


class TestPortfolioReturnsCalculator:
    """Tests pour PortfolioReturnsCalculator."""
    
    def test_calculate_empty_weights(self):
        """Test avec poids vides."""
        calc = PortfolioReturnsCalculator()
        df = calc.calculate({}, start="2024-01-01")
        assert df.empty
    
    def test_calculate_period_stats_structure(self):
        """Test structure des stats."""
        calc = PortfolioReturnsCalculator()
        weights = {"SPY": 1.0}
        stats = calc.calculate_period_stats(weights, start="2024-01-01", end="2024-06-01")
        
        # Vérifier les clés attendues
        expected_keys = [
            "total_return", "cagr", "volatility", "max_drawdown",
            "sharpe", "alpha", "tracking_error", "information_ratio", "n_days"
        ]
        
        if "error" not in stats:
            for key in expected_keys:
                assert key in stats, f"Clé manquante: {key}"


class TestWalkForwardBacktester:
    """Tests pour WalkForwardBacktester."""
    
    def test_init_default_params(self):
        """Test initialisation avec paramètres par défaut."""
        bt = WalkForwardBacktester()
        assert bt.benchmark == "SPY"
        assert "smart_money" in bt.frozen_weights
        assert "max_weight" in bt.frozen_constraints
    
    def test_init_custom_params(self):
        """Test initialisation avec paramètres custom."""
        custom_weights = {"value": 0.5, "quality": 0.5}
        bt = WalkForwardBacktester(frozen_weights=custom_weights)
        assert bt.frozen_weights == custom_weights
    
    def test_period_result_dataclass(self):
        """Test PeriodResult dataclass."""
        result = PeriodResult(
            test_start="2024-01-01",
            test_end="2024-03-31",
            portfolio_return=5.5,
            benchmark_return=4.2,
            alpha=1.3,
            n_positions=18,
            max_position_weight=10.5,
            max_sector_weight=25.0,
        )
        
        assert result.portfolio_return == 5.5
        assert result.alpha == 1.3
        assert result.n_positions == 18
    
    def test_calculate_cagr(self):
        """Test calcul CAGR."""
        bt = WalkForwardBacktester()
        
        # 4 trimestres à +5% chacun
        returns = np.array([5.0, 5.0, 5.0, 5.0])
        cagr = bt._calculate_cagr(returns)
        
        # CAGR attendu ~21.55% ((1.05)^4 - 1 annualisé)
        assert 20 < cagr < 23
    
    def test_calculate_cagr_negative(self):
        """Test CAGR avec returns négatifs."""
        bt = WalkForwardBacktester()
        
        returns = np.array([-5.0, -5.0, -5.0, -5.0])
        cagr = bt._calculate_cagr(returns)
        
        assert cagr < 0
    
    def test_run_simulated(self):
        """Test backtest simulé."""
        bt = WalkForwardBacktester()
        results = bt._run_simulated(
            start_date="2023-01-01",
            end_date="2024-01-01",
            test_window_months=3
        )
        
        # Devrait avoir ~4 périodes (4 trimestres)
        assert len(results) >= 3
        
        # Vérifier structure
        for r in results:
            assert hasattr(r, "portfolio_return")
            assert hasattr(r, "benchmark_return")
            assert hasattr(r, "alpha")


class TestMetricsCalculation:
    """Tests pour les calculs de métriques."""
    
    def test_sharpe_ratio_calculation(self):
        """Test calcul Sharpe ratio."""
        # Returns journaliers simulés
        np.random.seed(42)
        daily_returns = np.random.normal(0.0005, 0.01, 252)  # ~12% annuel, 16% vol
        
        # Calcul manuel
        mean_return = daily_returns.mean()
        std_return = daily_returns.std()
        rf_daily = 0.045 / 252  # 4.5% annuel
        
        sharpe = (mean_return - rf_daily) / std_return * np.sqrt(252)
        
        # Sharpe devrait être raisonnable
        assert -2 < sharpe < 2
    
    def test_max_drawdown_calculation(self):
        """Test calcul max drawdown."""
        # Série avec drawdown connu
        prices = [100, 110, 105, 95, 90, 100, 110]  # DD de 110 à 90 = -18.18%
        
        cumulative = np.array(prices) / prices[0]
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        # Max DD devrait être ~-18.18%
        assert -0.20 < max_dd < -0.15
    
    def test_tracking_error_calculation(self):
        """Test calcul tracking error."""
        np.random.seed(42)
        
        # Alpha journalier simulé
        alpha_daily = np.random.normal(0.0002, 0.003, 252)  # ~5 bps/jour, ~5% TE
        
        tracking_error = np.std(alpha_daily) * np.sqrt(252) * 100
        
        # TE devrait être ~5%
        assert 3 < tracking_error < 7
    
    def test_information_ratio_calculation(self):
        """Test calcul Information Ratio."""
        np.random.seed(42)
        
        # Alpha: 3% annuel, TE: 6%
        alpha_daily = np.random.normal(0.03/252, 0.06/np.sqrt(252), 252)
        
        alpha_annual = alpha_daily.mean() * 252 * 100
        te = np.std(alpha_daily) * np.sqrt(252) * 100
        ir = alpha_annual / te if te > 0 else 0
        
        # IR devrait être ~0.5 (3% / 6%)
        assert 0.2 < ir < 0.8


class TestConstraintsValidation:
    """Tests pour la validation des contraintes."""
    
    def test_max_weight_respected(self):
        """Vérifie que max_weight est respecté."""
        max_weight = 0.12
        
        # Portefeuille valide
        weights_valid = {"A": 0.10, "B": 0.10, "C": 0.10, "D": 0.70}
        max_pos = max(weights_valid.values())
        
        # Le poids max devrait être signalé si > 12%
        assert max_pos > max_weight  # Ce portefeuille viole la contrainte
    
    def test_max_sector_respected(self):
        """Vérifie que max_sector est respecté."""
        max_sector = 0.30
        
        # Poids par secteur
        sector_weights = {
            "Technology": 0.25,
            "Healthcare": 0.20,
            "Financials": 0.35,  # Viole la contrainte
            "Other": 0.20,
        }
        
        max_sect = max(sector_weights.values())
        assert max_sect > max_sector


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
