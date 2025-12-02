"""SmartMoney v2.3 — Backtest Package

Modules de backtest:
- backtest_v23: Backtest walk-forward avec nouveaux scores
- stress_tests: Tests de stress (COVID, 2008, rate hikes)
- metrics: Calcul des métriques de performance
- reports: Génération de rapports
"""

from .backtest_v23 import BacktestEngine, run_backtest
from .stress_tests import StressTester, run_stress_tests
from .metrics import calculate_metrics, PerformanceMetrics
from .reports import generate_report

__all__ = [
    "BacktestEngine",
    "run_backtest",
    "StressTester",
    "run_stress_tests",
    "calculate_metrics",
    "PerformanceMetrics",
    "generate_report",
]
