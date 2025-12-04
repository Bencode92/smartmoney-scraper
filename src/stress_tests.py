"""SmartMoney v2.4 — Stress Tests

Simule le comportement du portefeuille dans des scénarios historiques de stress :
- 2008 Financial Crisis
- 2011 European Debt Crisis
- 2015-2016 China/Oil
- Q4 2018 Vol Spike
- Mars 2020 COVID
- 2022 Rate Hike

Usage:
    python -m src.stress_tests

Date: Décembre 2025
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUTS


# =============================================================================
# SCÉNARIOS DE STRESS HISTORIQUES
# =============================================================================

@dataclass
class StressScenario:
    """Définition d'un scénario de stress."""
    name: str
    period: str
    spy_drawdown: float  # Drawdown SPY en %
    duration_days: int
    recovery_days: int
    description: str
    # Facteurs de stress par style
    value_impact: float      # Impact relatif sur Value (-1 à +1)
    quality_impact: float    # Impact relatif sur Quality
    momentum_impact: float   # Impact relatif sur Momentum
    concentration_impact: float  # Impact de la concentration


STRESS_SCENARIOS = [
    StressScenario(
        name="2008 Financial Crisis",
        period="Sep 2008 - Mar 2009",
        spy_drawdown=-56.8,
        duration_days=180,
        recovery_days=1400,
        description="Crise financière mondiale, effondrement Lehman",
        value_impact=-0.15,      # Value massacré (financials)
        quality_impact=0.05,      # Quality légèrement mieux
        momentum_impact=-0.20,    # Momentum catastrophique
        concentration_impact=-0.10,
    ),
    StressScenario(
        name="2011 European Debt Crisis",
        period="Jul 2011 - Oct 2011",
        spy_drawdown=-21.6,
        duration_days=90,
        recovery_days=180,
        description="Crise de la dette européenne, downgrade US",
        value_impact=-0.05,
        quality_impact=0.08,
        momentum_impact=-0.10,
        concentration_impact=-0.05,
    ),
    StressScenario(
        name="2015-2016 China/Oil",
        period="Aug 2015 - Feb 2016",
        spy_drawdown=-14.2,
        duration_days=180,
        recovery_days=120,
        description="Dévaluation Yuan, chute du pétrole",
        value_impact=-0.08,
        quality_impact=0.05,
        momentum_impact=-0.05,
        concentration_impact=-0.03,
    ),
    StressScenario(
        name="Q4 2018 Vol Spike",
        period="Oct 2018 - Dec 2018",
        spy_drawdown=-19.8,
        duration_days=90,
        recovery_days=120,
        description="Fed hawkish, guerre commerciale",
        value_impact=-0.03,
        quality_impact=0.02,
        momentum_impact=-0.15,
        concentration_impact=-0.08,
    ),
    StressScenario(
        name="COVID-19 Crash",
        period="Feb 2020 - Mar 2020",
        spy_drawdown=-33.9,
        duration_days=33,
        recovery_days=150,
        description="Pandémie mondiale, lockdowns",
        value_impact=-0.12,
        quality_impact=0.10,
        momentum_impact=-0.25,
        concentration_impact=-0.05,
    ),
    StressScenario(
        name="2022 Rate Hike",
        period="Jan 2022 - Oct 2022",
        spy_drawdown=-25.4,
        duration_days=280,
        recovery_days=400,
        description="Hausse agressive des taux Fed",
        value_impact=0.08,        # Value surperforme
        quality_impact=-0.05,     # Quality souffre (multiples)
        momentum_impact=-0.10,
        concentration_impact=-0.03,
    ),
]


# =============================================================================
# STRESS TEST ENGINE
# =============================================================================

@dataclass
class StressTestResult:
    """Résultat d'un stress test."""
    scenario_name: str
    spy_drawdown: float
    portfolio_drawdown_estimated: float
    relative_performance: float
    recovery_time_estimated: int
    risk_assessment: str  # "low", "medium", "high", "extreme"


class StressTester:
    """
    Simule le comportement du portefeuille dans des scénarios de stress.
    
    Utilise les caractéristiques du portefeuille (expositions factorielles,
    concentration) pour estimer l'impact.
    """
    
    def __init__(
        self,
        portfolio_beta: float = 1.0,
        value_exposure: float = 0.10,
        quality_exposure: float = 0.15,
        momentum_exposure: float = 0.05,
        concentration_hhi: float = 0.08,
    ):
        """
        Args:
            portfolio_beta: Beta vs SPY
            value_exposure: Exposition Value (0 = neutre)
            quality_exposure: Exposition Quality
            momentum_exposure: Exposition Momentum
            concentration_hhi: Herfindahl-Hirschman Index
        """
        self.beta = portfolio_beta
        self.value_exp = value_exposure
        self.quality_exp = quality_exposure
        self.momentum_exp = momentum_exposure
        self.concentration = concentration_hhi
    
    def run_scenario(self, scenario: StressScenario) -> StressTestResult:
        """
        Simule un scénario de stress.
        
        Formule:
            DD_portfolio = DD_spy * beta 
                         + value_exp * value_impact * |DD_spy|
                         + quality_exp * quality_impact * |DD_spy|
                         + momentum_exp * momentum_impact * |DD_spy|
                         + concentration * concentration_impact * |DD_spy|
        """
        spy_dd = scenario.spy_drawdown
        
        # Impact de base (beta)
        base_impact = spy_dd * self.beta
        
        # Ajustements factoriels (en % du DD SPY)
        value_adj = self.value_exp * scenario.value_impact * abs(spy_dd)
        quality_adj = self.quality_exp * scenario.quality_impact * abs(spy_dd)
        momentum_adj = self.momentum_exp * scenario.momentum_impact * abs(spy_dd)
        concentration_adj = self.concentration * 10 * scenario.concentration_impact * abs(spy_dd)
        
        # Drawdown estimé du portefeuille
        portfolio_dd = base_impact + value_adj + quality_adj + momentum_adj + concentration_adj
        
        # Limiter aux bornes réalistes
        portfolio_dd = max(min(portfolio_dd, 0), spy_dd * 1.5)
        
        # Performance relative
        relative_perf = portfolio_dd - spy_dd
        
        # Recovery time (proportionnel au DD)
        recovery_factor = abs(portfolio_dd / spy_dd) if spy_dd != 0 else 1
        recovery_time = int(scenario.recovery_days * recovery_factor)
        
        # Risk assessment
        if portfolio_dd > -20:
            risk = "low"
        elif portfolio_dd > -35:
            risk = "medium"
        elif portfolio_dd > -50:
            risk = "high"
        else:
            risk = "extreme"
        
        return StressTestResult(
            scenario_name=scenario.name,
            spy_drawdown=round(spy_dd, 1),
            portfolio_drawdown_estimated=round(portfolio_dd, 1),
            relative_performance=round(relative_perf, 1),
            recovery_time_estimated=recovery_time,
            risk_assessment=risk,
        )
    
    def run_all_scenarios(self) -> List[StressTestResult]:
        """Exécute tous les scénarios de stress."""
        return [self.run_scenario(s) for s in STRESS_SCENARIOS]
    
    def generate_report(self, output_path: Path = None) -> Dict:
        """
        Génère un rapport complet des stress tests.
        """
        results = self.run_all_scenarios()
        
        # Statistiques agrégées
        portfolio_dds = [r.portfolio_drawdown_estimated for r in results]
        spy_dds = [r.spy_drawdown for r in results]
        relative_perfs = [r.relative_performance for r in results]
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "portfolio_characteristics": {
                "beta": self.beta,
                "value_exposure": self.value_exp,
                "quality_exposure": self.quality_exp,
                "momentum_exposure": self.momentum_exp,
                "concentration_hhi": self.concentration,
            },
            "summary": {
                "worst_portfolio_dd": min(portfolio_dds),
                "avg_portfolio_dd": round(np.mean(portfolio_dds), 1),
                "worst_relative_perf": min(relative_perfs),
                "avg_relative_perf": round(np.mean(relative_perfs), 1),
                "scenarios_outperform": sum(1 for r in relative_perfs if r > 0),
                "scenarios_underperform": sum(1 for r in relative_perfs if r < 0),
            },
            "scenarios": [asdict(r) for r in results],
        }
        
        # Sauvegarder
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
        
        # Afficher
        self._print_report(results, report)
        
        return report
    
    def _print_report(self, results: List[StressTestResult], report: Dict):
        """Affiche le rapport formaté."""
        print("\n" + "=" * 70)
        print("STRESS TESTS — SmartMoney v2.4")
        print("=" * 70)
        
        print("\nCaractéristiques du portefeuille:")
        chars = report["portfolio_characteristics"]
        print(f"  Beta: {chars['beta']:.2f}")
        print(f"  Value exposure: {chars['value_exposure']:+.2f}")
        print(f"  Quality exposure: {chars['quality_exposure']:+.2f}")
        print(f"  Concentration (HHI): {chars['concentration_hhi']:.3f}")
        
        print("\n" + "-" * 70)
        print(f"{'Scénario':<25} {'SPY DD':>10} {'PF DD':>10} {'Relatif':>10} {'Risque':>10}")
        print("-" * 70)
        
        for r in results:
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "extreme": "🔴"}
            print(
                f"{r.scenario_name:<25} "
                f"{r.spy_drawdown:>+10.1f}% "
                f"{r.portfolio_drawdown_estimated:>+10.1f}% "
                f"{r.relative_performance:>+10.1f}% "
                f"{risk_emoji.get(r.risk_assessment, '')} {r.risk_assessment:>7}"
            )
        
        print("\n" + "-" * 70)
        print("RÉSUMÉ")
        print("-" * 70)
        s = report["summary"]
        print(f"  Pire DD portefeuille: {s['worst_portfolio_dd']:.1f}%")
        print(f"  DD moyen portefeuille: {s['avg_portfolio_dd']:.1f}%")
        print(f"  Pire perf relative: {s['worst_relative_perf']:.1f}%")
        print(f"  Scénarios surperformés: {s['scenarios_outperform']}/6")
        
        # Verdict
        print("\n" + "-" * 70)
        if s["worst_portfolio_dd"] > -50:
            print("✅ VERDICT: Drawdowns dans les limites assumées (-50% max)")
        else:
            print("⚠️ VERDICT: Risque de DD > 50% dans certains scénarios")
        print("=" * 70)


def main():
    """Exécute les stress tests avec les paramètres par défaut."""
    # Paramètres typiques de SmartMoney v2.4
    tester = StressTester(
        portfolio_beta=1.0,
        value_exposure=0.10,      # Tilt Value modéré
        quality_exposure=0.15,    # Tilt Quality
        momentum_exposure=0.05,   # Faible momentum
        concentration_hhi=0.08,   # Concentration modérée
    )
    
    output_path = OUTPUTS / "stress_tests" / "stress_test_report.json"
    tester.generate_report(output_path=output_path)
    
    print(f"\n📁 Rapport: {output_path}")


if __name__ == "__main__":
    main()
