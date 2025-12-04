"""SmartMoney v2.4 — Générateur de Rapport Backtest

Génère un rapport complet avec:
- Performance vs SPY
- Métriques de risque
- Analyse des pires/meilleures périodes
- Graphiques (optionnel)

Usage:
    python -m src.generate_backtest_report --start 2020-01-01 --end 2024-12-31

Date: Décembre 2025
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUTS
from config_v23 import WEIGHTS_V23, CONSTRAINTS_V23
from src.backtest_walkforward import WalkForwardBacktester, generate_markdown_report


def generate_full_report(
    start_date: str = "2020-01-01",
    end_date: str = None,
    benchmark: str = "SPY",
    output_dir: Path = None,
) -> Dict:
    """
    Génère un rapport de backtest complet.
    
    Args:
        start_date: Date de début
        end_date: Date de fin (défaut: aujourd'hui)
        benchmark: Ticker du benchmark
        output_dir: Dossier de sortie
    
    Returns:
        Dict avec le rapport complet
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    if output_dir is None:
        output_dir = OUTPUTS / "backtest"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("SMARTMONEY v2.4 — BACKTEST REPORT GENERATOR")
    print("=" * 70)
    print(f"\nPériode: {start_date} → {end_date}")
    print(f"Benchmark: {benchmark}")
    print(f"Output: {output_dir}")
    
    # 1. Exécuter le backtest walk-forward
    print("\n" + "-" * 70)
    print("PHASE 1: Walk-Forward Backtest")
    print("-" * 70)
    
    bt = WalkForwardBacktester(
        frozen_weights=WEIGHTS_V23,
        frozen_constraints=CONSTRAINTS_V23,
        benchmark=benchmark,
    )
    
    bt.run(start_date=start_date, end_date=end_date)
    
    # 2. Générer le rapport
    print("\n" + "-" * 70)
    print("PHASE 2: Génération du Rapport")
    print("-" * 70)
    
    json_path = output_dir / "backtest_report.json"
    report = bt.generate_report(output_path=json_path)
    
    if report is None:
        print("❌ Erreur: Pas de résultats à reporter")
        return {}
    
    # 3. Générer le rapport Markdown
    md_path = output_dir / "backtest_report.md"
    generate_markdown_report(report, md_path)
    
    # 4. Générer le résumé exécutif
    print("\n" + "-" * 70)
    print("PHASE 3: Résumé Exécutif")
    print("-" * 70)
    
    executive_summary = generate_executive_summary(report)
    
    summary_path = output_dir / "executive_summary.md"
    with open(summary_path, "w") as f:
        f.write(executive_summary)
    
    print(f"\n📄 Résumé exécutif: {summary_path}")
    
    # 5. Afficher le verdict final
    print("\n" + "=" * 70)
    print("VERDICT FINAL")
    print("=" * 70)
    
    s = report.summary
    r = report.risk_metrics
    
    # Critères de validation
    criteria = {
        "Alpha positif": s["total_alpha"] > 0,
        "Hit rate > 50%": s["hit_rate"] > 50,
        "Max DD > -40%": r["max_drawdown"] > -40,
        "IR > 0.3": s["information_ratio"] > 0.3,
    }
    
    passed = sum(criteria.values())
    total = len(criteria)
    
    for criterion, passed_flag in criteria.items():
        status = "✅" if passed_flag else "❌"
        print(f"  {status} {criterion}")
    
    print(f"\n  Score: {passed}/{total}")
    
    if passed == total:
        print("\n🏆 STRATÉGIE VALIDÉE — Prête pour production")
    elif passed >= 3:
        print("\n⚠️ STRATÉGIE ACCEPTABLE — Améliorations recommandées")
    else:
        print("\n❌ STRATÉGIE À REVOIR — Paramètres à ajuster")
    
    print("=" * 70)
    
    return asdict(report)


def generate_executive_summary(report) -> str:
    """Génère un résumé exécutif d'une page."""
    
    s = report.summary
    r = report.risk_metrics
    m = report.metadata
    
    # Déterminer le verdict
    if s["total_alpha"] > 0 and s["hit_rate"] > 55 and s["information_ratio"] > 0.5:
        verdict = "RECOMMANDÉ"
        verdict_emoji = "✅"
        verdict_detail = "La stratégie génère un alpha significatif avec une consistance satisfaisante."
    elif s["total_alpha"] > 0 and s["hit_rate"] > 50:
        verdict = "ACCEPTABLE"
        verdict_emoji = "⚠️"
        verdict_detail = "Alpha positif mais consistance à améliorer. Utilisable en poche satellite."
    else:
        verdict = "À REVOIR"
        verdict_emoji = "❌"
        verdict_detail = "Performance insuffisante. Révision des paramètres nécessaire."
    
    summary = f"""# SmartMoney v2.4 — Résumé Exécutif

*Généré le {datetime.now().strftime("%Y-%m-%d %H:%M")}*

---

## {verdict_emoji} Verdict: **{verdict}**

{verdict_detail}

---

## Métriques Clés

| Métrique | Valeur | Benchmark | Commentaire |
|----------|--------|-----------|-------------|
| **CAGR** | {s['portfolio_cagr']:+.2f}% | {s['benchmark_cagr']:+.2f}% | {"Surperformance" if s['portfolio_cagr'] > s['benchmark_cagr'] else "Sous-performance"} |
| **Alpha cumulé** | {s['total_alpha']:+.2f}% | — | {"Positif" if s['total_alpha'] > 0 else "Négatif"} |
| **Hit Rate** | {s['hit_rate']:.1f}% | — | {"Bon" if s['hit_rate'] > 55 else "Acceptable" if s['hit_rate'] > 50 else "Faible"} |
| **Info Ratio** | {s['information_ratio']:.2f} | — | {"Excellent" if s['information_ratio'] > 0.7 else "Bon" if s['information_ratio'] > 0.5 else "Acceptable"} |

---

## Profil de Risque

| Métrique | Valeur | Seuil | Status |
|----------|--------|-------|--------|
| Max Drawdown | {r['max_drawdown']:.2f}% | > -35% | {"✅" if r['max_drawdown'] > -35 else "⚠️"} |
| Volatilité | {r['portfolio_volatility']:.2f}% | 15-20% | {"✅" if 12 < r['portfolio_volatility'] < 22 else "⚠️"} |
| Tracking Error | {r['tracking_error']:.2f}% | 8-12% | {"✅" if 6 < r['tracking_error'] < 14 else "⚠️"} |
| Pire période | {r['worst_period_return']:.2f}% | > -15% | {"✅" if r['worst_period_return'] > -15 else "⚠️"} |

---

## Période Analysée

- **Début**: {m['start_date']}
- **Fin**: {m['end_date']}
- **Benchmark**: {m['benchmark']}
- **Périodes testées**: {m['total_periods']}

---

## Paramètres Figés (v2.4)

**Poids des facteurs:**
- Smart Money: 15%
- Value: 30%
- Quality: 25%
- Risk: 15%
- Insider: 10%
- Momentum: 5%

**Contraintes:**
- Max position: 12%
- Max secteur: 30%
- Positions: 15-20

---

## Usage Recommandé

| Caractéristique | Recommandation |
|-----------------|----------------|
| **Allocation** | Poche satellite (10-20% du portefeuille) |
| **Capacité** | 1-5 M$ |
| **Horizon** | 3-5 ans minimum |
| **Rebalancing** | Trimestriel |
| **Drawdown attendu** | -35% à -40% max |

---

## Prochaines Étapes

1. {"✅ Stratégie validée — Passage en production" if verdict == "RECOMMANDÉ" else "⚠️ Optimiser les paramètres avant production" if verdict == "ACCEPTABLE" else "❌ Revoir l'approche fondamentale"}
2. Implémenter le monitoring en temps réel
3. Définir les triggers de rebalancing
4. Préparer l'Investment Memo complet

---

*Ce résumé est généré automatiquement. Pour le rapport complet, voir `backtest_report.md`.*
"""
    
    return summary


def main():
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(
        description="SmartMoney v2.4 — Générateur de Rapport Backtest"
    )
    parser.add_argument(
        "--start", "-s",
        default="2020-01-01",
        help="Date de début (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", "-e",
        default=None,
        help="Date de fin (défaut: aujourd'hui)"
    )
    parser.add_argument(
        "--benchmark", "-b",
        default="SPY",
        help="Benchmark (défaut: SPY)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Dossier de sortie"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output) if args.output else None
    
    generate_full_report(
        start_date=args.start,
        end_date=args.end,
        benchmark=args.benchmark,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
