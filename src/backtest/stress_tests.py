"""SmartMoney v2.3 — Stress Tests

Tests de stress sur périodes critiques:
- COVID-19 (2020)
- Crise financière 2008
- Hausse des taux 2022
- Dot-com crash 2000-2002
- Crises sectorielles

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

from .metrics import calculate_metrics, PerformanceMetrics

logger = logging.getLogger(__name__)


@dataclass
class StressTestResult:
    """Résultat d'un test de stress."""
    name: str
    start_date: str
    end_date: str
    description: str
    
    # Performance portefeuille
    portfolio_return: float
    portfolio_max_dd: float
    portfolio_volatility: float
    
    # Performance benchmark
    benchmark_return: Optional[float] = None
    benchmark_max_dd: Optional[float] = None
    
    # Outperformance
    excess_return: Optional[float] = None
    
    # Statut
    passed: bool = False
    notes: str = ""


@dataclass
class StressTestSuite:
    """Résultats complets des stress tests."""
    results: List[StressTestResult]
    summary: Dict[str, float]
    passed_count: int
    failed_count: int
    overall_passed: bool


# Définition des périodes de stress
STRESS_PERIODS = {
    "covid_crash": {
        "start": "2020-02-19",
        "end": "2020-03-23",
        "description": "COVID-19 crash - Chute rapide des marchés",
        "expected_spy_dd": -34,
        "max_acceptable_dd": -40,
    },
    "covid_recovery": {
        "start": "2020-03-23",
        "end": "2020-08-31",
        "description": "COVID-19 recovery - Rebond post-crash",
        "expected_spy_return": 55,
        "min_capture": 0.5,  # Capturer au moins 50% du rebond
    },
    "gfc_2008": {
        "start": "2008-09-01",
        "end": "2009-03-09",
        "description": "Grande Crise Financière 2008-2009",
        "expected_spy_dd": -50,
        "max_acceptable_dd": -45,  # Doit faire mieux que SPY
    },
    "rate_hikes_2022": {
        "start": "2022-01-03",
        "end": "2022-10-12",
        "description": "Hausse des taux 2022 - Rotation growth/value",
        "expected_spy_dd": -25,
        "max_acceptable_dd": -30,
    },
    "tech_correction_2022": {
        "start": "2021-11-19",
        "end": "2022-12-28",
        "description": "Correction tech 2022 - NASDAQ -33%",
        "expected_qqq_dd": -35,
        "max_acceptable_dd": -30,  # Strategy value doit résister
    },
    "flash_crash_2010": {
        "start": "2010-05-06",
        "end": "2010-05-07",
        "description": "Flash Crash 6 mai 2010",
        "expected_spy_dd": -9,
        "max_acceptable_dd": -12,
    },
    "euro_crisis_2011": {
        "start": "2011-07-01",
        "end": "2011-10-03",
        "description": "Crise dette européenne 2011",
        "expected_spy_dd": -19,
        "max_acceptable_dd": -25,
    },
    "china_deval_2015": {
        "start": "2015-08-10",
        "end": "2015-08-25",
        "description": "Dévaluation Yuan et panique",
        "expected_spy_dd": -12,
        "max_acceptable_dd": -18,
    },
    "volmageddon_2018": {
        "start": "2018-01-26",
        "end": "2018-02-08",
        "description": "Volmageddon - Explosion VIX",
        "expected_spy_dd": -10,
        "max_acceptable_dd": -15,
    },
    "q4_2018": {
        "start": "2018-10-01",
        "end": "2018-12-24",
        "description": "Q4 2018 - Fed hawkish",
        "expected_spy_dd": -20,
        "max_acceptable_dd": -25,
    },
}


class StressTester:
    """
    Exécute les stress tests sur un portefeuille.
    
    Vérifie:
    - Max DD pendant les crises
    - Capture des rebonds
    - Outperformance vs benchmark
    
    Example:
        >>> tester = StressTester()
        >>> results = tester.run(portfolio_returns, benchmark_returns)
        >>> print(f"Passé: {results.passed_count}/{len(results.results)}")
    """
    
    def __init__(
        self,
        periods: Optional[Dict] = None,
        hard_dd_limit: float = -0.35,
    ):
        """
        Args:
            periods: Override des périodes de stress
            hard_dd_limit: Limite absolue de DD (-35%)
        """
        self.periods = periods or STRESS_PERIODS
        self.hard_dd_limit = hard_dd_limit
    
    def run(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> StressTestSuite:
        """
        Exécute tous les stress tests.
        
        Args:
            portfolio_returns: Rendements du portefeuille
            benchmark_returns: Rendements du benchmark (SPY)
        
        Returns:
            StressTestSuite avec tous les résultats
        """
        results = []
        
        for name, config in self.periods.items():
            result = self._run_single_test(
                name,
                config,
                portfolio_returns,
                benchmark_returns,
            )
            if result:
                results.append(result)
        
        # Summary
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        
        summary = self._calculate_summary(results)
        
        # Overall: passé si > 70% des tests passent ET pas de DD > hard limit
        hard_limit_breached = any(
            r.portfolio_max_dd < self.hard_dd_limit * 100 
            for r in results
        )
        
        overall_passed = (
            passed_count / len(results) >= 0.7 if results else False
        ) and not hard_limit_breached
        
        return StressTestSuite(
            results=results,
            summary=summary,
            passed_count=passed_count,
            failed_count=failed_count,
            overall_passed=overall_passed,
        )
    
    def _run_single_test(
        self,
        name: str,
        config: Dict,
        portfolio_returns: pd.Series,
        benchmark_returns: Optional[pd.Series],
    ) -> Optional[StressTestResult]:
        """Exécute un seul stress test."""
        start = config["start"]
        end = config["end"]
        
        # Filtrer la période
        try:
            period_returns = portfolio_returns.loc[start:end]
        except KeyError:
            logger.warning(f"Période {name} non disponible dans les données")
            return None
        
        if len(period_returns) < 3:
            logger.warning(f"Période {name}: pas assez de données")
            return None
        
        # Calculer métriques portefeuille
        cumulative = (1 + period_returns).cumprod()
        portfolio_return = (cumulative.iloc[-1] - 1) * 100
        portfolio_max_dd = (cumulative / cumulative.expanding().max() - 1).min() * 100
        portfolio_vol = period_returns.std() * np.sqrt(252) * 100
        
        # Benchmark
        benchmark_return = None
        benchmark_max_dd = None
        excess_return = None
        
        if benchmark_returns is not None:
            try:
                bench_period = benchmark_returns.loc[start:end]
                if len(bench_period) > 0:
                    bench_cumulative = (1 + bench_period).cumprod()
                    benchmark_return = (bench_cumulative.iloc[-1] - 1) * 100
                    benchmark_max_dd = (bench_cumulative / bench_cumulative.expanding().max() - 1).min() * 100
                    excess_return = portfolio_return - benchmark_return
            except KeyError:
                pass
        
        # Évaluer pass/fail
        passed, notes = self._evaluate_test(name, config, portfolio_return, portfolio_max_dd, excess_return)
        
        return StressTestResult(
            name=name,
            start_date=start,
            end_date=end,
            description=config["description"],
            portfolio_return=round(portfolio_return, 2),
            portfolio_max_dd=round(portfolio_max_dd, 2),
            portfolio_volatility=round(portfolio_vol, 2),
            benchmark_return=round(benchmark_return, 2) if benchmark_return else None,
            benchmark_max_dd=round(benchmark_max_dd, 2) if benchmark_max_dd else None,
            excess_return=round(excess_return, 2) if excess_return else None,
            passed=passed,
            notes=notes,
        )
    
    def _evaluate_test(
        self,
        name: str,
        config: Dict,
        portfolio_return: float,
        portfolio_max_dd: float,
        excess_return: Optional[float],
    ) -> Tuple[bool, str]:
        """Détermine si le test est passé."""
        notes = []
        passed = True
        
        # Check DD limit
        max_acceptable_dd = config.get("max_acceptable_dd")
        if max_acceptable_dd and portfolio_max_dd < max_acceptable_dd:
            passed = False
            notes.append(f"DD {portfolio_max_dd:.1f}% > limite {max_acceptable_dd}%")
        elif max_acceptable_dd:
            notes.append(f"DD {portfolio_max_dd:.1f}% OK (limite {max_acceptable_dd}%)")
        
        # Check recovery capture
        min_capture = config.get("min_capture")
        expected_return = config.get("expected_spy_return")
        if min_capture and expected_return:
            min_required = expected_return * min_capture
            if portfolio_return < min_required:
                passed = False
                notes.append(f"Capture {portfolio_return:.1f}% < minimum {min_required:.1f}%")
            else:
                notes.append(f"Capture {portfolio_return:.1f}% OK")
        
        # Check outperformance
        if excess_return is not None:
            if excess_return > 0:
                notes.append(f"Outperformance +{excess_return:.1f}%")
            else:
                notes.append(f"Underperformance {excess_return:.1f}%")
        
        return passed, "; ".join(notes)
    
    def _calculate_summary(self, results: List[StressTestResult]) -> Dict[str, float]:
        """Calcule les statistiques résumées."""
        if not results:
            return {}
        
        dds = [r.portfolio_max_dd for r in results]
        returns = [r.portfolio_return for r in results]
        excess = [r.excess_return for r in results if r.excess_return is not None]
        
        return {
            "avg_dd": round(np.mean(dds), 2),
            "worst_dd": round(min(dds), 2),
            "avg_return": round(np.mean(returns), 2),
            "avg_excess_return": round(np.mean(excess), 2) if excess else None,
            "pct_outperform": round(sum(1 for e in excess if e > 0) / len(excess) * 100, 1) if excess else None,
        }


def run_stress_tests(
    portfolio_returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    periods: Optional[Dict] = None,
) -> StressTestSuite:
    """
    Fonction helper pour lancer les stress tests.
    
    Args:
        portfolio_returns: Rendements du portefeuille
        benchmark_returns: Rendements du benchmark
        periods: Override des périodes
    
    Returns:
        StressTestSuite
    """
    tester = StressTester(periods=periods)
    return tester.run(portfolio_returns, benchmark_returns)


def generate_stress_report(suite: StressTestSuite) -> str:
    """
    Génère un rapport texte des stress tests.
    
    Args:
        suite: Résultats des stress tests
    
    Returns:
        Rapport formaté
    """
    lines = [
        "=" * 70,
        "STRESS TESTS REPORT",
        "=" * 70,
        "",
        f"Résultats: {suite.passed_count}/{len(suite.results)} tests passés",
        f"Statut global: {'\u2705 PASS' if suite.overall_passed else '\u274c FAIL'}",
        "",
        "-" * 70,
        "Détail par période:",
        "-" * 70,
    ]
    
    for r in suite.results:
        status = "\u2705" if r.passed else "\u274c"
        lines.append(f"\n{status} {r.name}: {r.description}")
        lines.append(f"   Période: {r.start_date} → {r.end_date}")
        lines.append(f"   Portefeuille: Return={r.portfolio_return:+.1f}%, DD={r.portfolio_max_dd:.1f}%")
        if r.benchmark_return is not None:
            lines.append(f"   Benchmark:    Return={r.benchmark_return:+.1f}%, DD={r.benchmark_max_dd:.1f}%")
        if r.excess_return is not None:
            lines.append(f"   Excess:       {r.excess_return:+.1f}%")
        if r.notes:
            lines.append(f"   Notes: {r.notes}")
    
    lines.extend([
        "",
        "-" * 70,
        "Résumé:",
        "-" * 70,
    ])
    
    for key, value in suite.summary.items():
        if value is not None:
            lines.append(f"   {key}: {value}")
    
    return "\n".join(lines)
