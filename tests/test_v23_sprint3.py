"""SmartMoney v2.3 — Tests Sprint 3 (Backtest & Intégration)

Tests pour:
- Métriques de performance
- Stress tests
- Backtest engine
- Intégration engine v2.3

Lancer avec: pytest tests/test_v23_sprint3.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_returns():
    """Rendements journaliers simulés sur 3 ans."""
    np.random.seed(42)
    dates = pd.date_range("2021-01-01", "2023-12-31", freq="B")
    
    # Rendements avec tendance positive et volatilité réaliste
    returns = np.random.normal(0.0004, 0.012, len(dates))  # ~10% CAGR, ~19% vol
    
    return pd.Series(returns, index=dates)


@pytest.fixture
def sample_benchmark():
    """Benchmark (SPY) simulé."""
    np.random.seed(123)
    dates = pd.date_range("2021-01-01", "2023-12-31", freq="B")
    
    returns = np.random.normal(0.0003, 0.011, len(dates))  # ~8% CAGR, ~17% vol
    
    return pd.Series(returns, index=dates)


@pytest.fixture
def sample_weights_history():
    """Historique des poids simulé."""
    dates = pd.date_range("2021-01-01", "2023-12-31", freq="Q")
    
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    
    data = []
    for date in dates:
        weights = np.random.dirichlet(np.ones(5))
        row = {"date": date}
        for sym, w in zip(symbols, weights):
            row[sym] = w
        data.append(row)
    
    return pd.DataFrame(data).set_index("date")


@pytest.fixture
def crisis_returns():
    """Rendements incluant une crise (COVID-style)."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", "2020-06-30", freq="B")
    
    returns = []
    for i, date in enumerate(dates):
        if date >= pd.Timestamp("2020-02-20") and date <= pd.Timestamp("2020-03-23"):
            # Crash
            ret = np.random.normal(-0.02, 0.04)
        elif date >= pd.Timestamp("2020-03-24") and date <= pd.Timestamp("2020-05-31"):
            # Recovery
            ret = np.random.normal(0.01, 0.025)
        else:
            ret = np.random.normal(0.0005, 0.01)
        returns.append(ret)
    
    return pd.Series(returns, index=dates)


# =============================================================================
# TESTS METRICS
# =============================================================================

class TestMetrics:
    """Tests des métriques de performance."""
    
    def test_calculate_metrics(self, sample_returns):
        """Test calcul des métriques de base."""
        from src.backtest.metrics import calculate_metrics
        
        metrics = calculate_metrics(sample_returns)
        
        # Vérifier que les métriques sont calculées
        assert metrics.total_return is not None
        assert metrics.cagr is not None
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown is not None
        
        # Vérifier les ranges raisonnables
        assert -100 < metrics.total_return < 500
        assert -50 < metrics.cagr < 100
        assert -2 < metrics.sharpe_ratio < 4
        assert -80 < metrics.max_drawdown <= 0
    
    def test_sharpe_positive_returns(self, sample_returns):
        """Sharpe devrait être positif pour des rendements positifs."""
        from src.backtest.metrics import calculate_metrics
        
        # Forcer des rendements positifs
        positive_returns = sample_returns.abs() + 0.001
        metrics = calculate_metrics(positive_returns)
        
        assert metrics.sharpe_ratio > 0
    
    def test_benchmark_stats(self, sample_returns, sample_benchmark):
        """Test des stats vs benchmark."""
        from src.backtest.metrics import calculate_metrics
        
        metrics = calculate_metrics(sample_returns, sample_benchmark)
        
        assert metrics.alpha is not None
        assert metrics.beta is not None
        assert metrics.information_ratio is not None
    
    def test_turnover_calculation(self, sample_returns, sample_weights_history):
        """Test du calcul de turnover."""
        from src.backtest.metrics import calculate_metrics
        
        metrics = calculate_metrics(
            sample_returns,
            weights_history=sample_weights_history,
        )
        
        assert metrics.turnover_annual >= 0


# =============================================================================
# TESTS STRESS TESTS
# =============================================================================

class TestStressTests:
    """Tests des stress tests."""
    
    def test_stress_tester_creation(self):
        """Test création du StressTester."""
        from src.backtest.stress_tests import StressTester
        
        tester = StressTester()
        assert tester is not None
        assert len(tester.periods) > 0
    
    def test_run_stress_tests(self, crisis_returns):
        """Test exécution des stress tests."""
        from src.backtest.stress_tests import run_stress_tests
        
        # Définir une période de test personnalisée
        custom_periods = {
            "test_crisis": {
                "start": "2020-02-20",
                "end": "2020-03-23",
                "description": "Test crisis",
                "max_acceptable_dd": -40,
            }
        }
        
        results = run_stress_tests(
            crisis_returns,
            periods=custom_periods,
        )
        
        assert len(results.results) > 0
        assert results.passed_count + results.failed_count == len(results.results)
    
    def test_stress_report_generation(self, crisis_returns):
        """Test génération du rapport."""
        from src.backtest.stress_tests import run_stress_tests, generate_stress_report
        
        custom_periods = {
            "test_crisis": {
                "start": "2020-02-20",
                "end": "2020-03-23",
                "description": "Test crisis",
                "max_acceptable_dd": -40,
            }
        }
        
        results = run_stress_tests(crisis_returns, periods=custom_periods)
        report = generate_stress_report(results)
        
        assert "STRESS TESTS REPORT" in report
        assert "test_crisis" in report


# =============================================================================
# TESTS BACKTEST ENGINE
# =============================================================================

class TestBacktestEngine:
    """Tests du moteur de backtest."""
    
    def test_engine_creation(self):
        """Test création du BacktestEngine."""
        from src.backtest.backtest_v23 import BacktestEngine
        
        engine = BacktestEngine()
        assert engine is not None
        assert engine.rebal_freq in ["Q", "M", "W"]
        assert engine.tc_bps > 0
    
    def test_rebal_dates_quarterly(self):
        """Test génération dates trimestrielles."""
        from src.backtest.backtest_v23 import BacktestEngine
        
        engine = BacktestEngine(rebal_freq="Q")
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="B")
        
        rebal_dates = engine._get_rebal_dates(dates, "Q")
        
        # Devrait avoir ~4 dates (fin de trimestre)
        assert len(rebal_dates) >= 3
        assert len(rebal_dates) <= 5
    
    def test_rebal_dates_monthly(self):
        """Test génération dates mensuelles."""
        from src.backtest.backtest_v23 import BacktestEngine
        
        engine = BacktestEngine(rebal_freq="M")
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="B")
        
        rebal_dates = engine._get_rebal_dates(dates, "M")
        
        # Devrait avoir ~12 dates (fin de mois)
        assert len(rebal_dates) >= 10
        assert len(rebal_dates) <= 14


# =============================================================================
# TESTS REPORTS
# =============================================================================

class TestReports:
    """Tests de la génération de rapports."""
    
    def test_text_report(self, sample_returns):
        """Test rapport texte."""
        from src.backtest.metrics import calculate_metrics
        from src.backtest.backtest_v23 import BacktestResult
        from src.backtest.reports import generate_report
        
        metrics = calculate_metrics(sample_returns)
        
        result = BacktestResult(
            metrics=metrics,
            returns=sample_returns,
            cumulative_returns=(1 + sample_returns).cumprod(),
            drawdowns=pd.Series([0] * len(sample_returns)),
            weights_history=pd.DataFrame(),
            holdings_history=[],
            validation_passed=True,
            validation_notes=["Test pass"],
        )
        
        report = generate_report(result, format="text")
        
        assert "SMARTMONEY v2.3" in report
        assert "CAGR" in report
        assert "Sharpe" in report
    
    def test_json_report(self, sample_returns):
        """Test rapport JSON."""
        import json
        from src.backtest.metrics import calculate_metrics
        from src.backtest.backtest_v23 import BacktestResult
        from src.backtest.reports import generate_report
        
        metrics = calculate_metrics(sample_returns)
        
        result = BacktestResult(
            metrics=metrics,
            returns=sample_returns,
            cumulative_returns=(1 + sample_returns).cumprod(),
            drawdowns=pd.Series([0] * len(sample_returns)),
            weights_history=pd.DataFrame(),
            holdings_history=[],
            validation_passed=True,
            validation_notes=[],
        )
        
        report = generate_report(result, format="json")
        
        # Vérifier que c'est du JSON valide
        data = json.loads(report)
        assert "returns" in data
        assert "ratios" in data


# =============================================================================
# TESTS INTÉGRATION ENGINE v2.3
# =============================================================================

class TestEngineV23Integration:
    """Tests d'intégration de l'engine v2.3."""
    
    def test_engine_v23_creation(self):
        """Test création de SmartMoneyEngineV23."""
        from src.engine_v23 import SmartMoneyEngineV23
        
        engine = SmartMoneyEngineV23()
        
        assert engine.version == "2.3"
        assert sum(engine.weights.values()) == pytest.approx(1.0, abs=0.001)
    
    def test_engine_v23_weights(self):
        """Test que les poids v2.3 sont corrects."""
        from src.engine_v23 import SmartMoneyEngineV23
        
        engine = SmartMoneyEngineV23()
        
        # Vérifier les nouveaux facteurs
        assert "value" in engine.weights
        assert "quality" in engine.weights
        assert "risk" in engine.weights
        
        # Vérifier que smart_money est réduit
        assert engine.weights["smart_money"] < 0.20
        
        # Vérifier que value est le plus grand
        assert engine.weights["value"] >= 0.25
    
    def test_summary(self):
        """Test de la méthode summary."""
        from src.engine_v23 import SmartMoneyEngineV23
        
        engine = SmartMoneyEngineV23()
        summary = engine.summary()
        
        assert "version" in summary
        assert summary["version"] == "2.3"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
