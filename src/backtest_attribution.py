"""SmartMoney v2.4 — Attribution Factorielle

Compare deux versions du modèle :
1. Core : Quality/Value/Risk (sans Smart Money)
2. Core + Smart Money : Version complète

Objectif : Prouver (ou non) que Smart Money apporte de l'alpha.

Usage:
    python -m src.backtest_attribution --start 2015-01-01 --end 2024-12-31

Date: Décembre 2025
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from dataclasses import dataclass, asdict
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUTS
from src.backtest_walkforward import WalkForwardBacktester


# =============================================================================
# CONFIGURATIONS À COMPARER
# =============================================================================

# Version CORE : Sans Smart Money
WEIGHTS_CORE = {
    "smart_money": 0.00,  # Désactivé
    "insider": 0.12,      # +2% (redistribué)
    "momentum": 0.08,     # +3% (redistribué)
    "value": 0.35,        # +5% (redistribué)
    "quality": 0.28,      # +3% (redistribué)
    "risk": 0.17,         # +2% (redistribué)
}

# Version CORE + SMART MONEY : Version v2.4
WEIGHTS_CORE_SM = {
    "smart_money": 0.15,
    "insider": 0.10,
    "momentum": 0.05,
    "value": 0.30,
    "quality": 0.25,
    "risk": 0.15,
}

# Version SMART MONEY RÉDUIT : Compromis
WEIGHTS_SM_REDUCED = {
    "smart_money": 0.05,  # Réduit de 15% à 5%
    "insider": 0.10,
    "momentum": 0.05,
    "value": 0.33,        # +3%
    "quality": 0.27,      # +2%
    "risk": 0.20,         # +5%
}

CONFIGS = {
    "core": {
        "name": "Core (Quality/Value/Risk)",
        "weights": WEIGHTS_CORE,
        "description": "Sans Smart Money - Pure Quality/Value",
    },
    "core_sm": {
        "name": "Core + Smart Money (v2.4)",
        "weights": WEIGHTS_CORE_SM,
        "description": "Version actuelle avec Smart Money à 15%",
    },
    "sm_reduced": {
        "name": "Smart Money Réduit (5%)",
        "weights": WEIGHTS_SM_REDUCED,
        "description": "Compromis avec Smart Money à 5%",
    },
}


# =============================================================================
# ATTRIBUTION ANALYSIS
# =============================================================================

@dataclass
class AttributionResult:
    """Résultat de l'attribution factorielle."""
    config_name: str
    cagr: float
    total_alpha: float
    hit_rate: float
    sharpe: float
    info_ratio: float
    max_drawdown: float
    tracking_error: float


def run_attribution(
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
    output_dir: Path = None,
) -> Dict[str, AttributionResult]:
    """
    Exécute le backtest pour chaque configuration et compare.
    
    Returns:
        Dict des résultats par configuration
    """
    if output_dir is None:
        output_dir = OUTPUTS / "attribution"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("ATTRIBUTION FACTORIELLE — CORE vs CORE+SM")
    print("=" * 70)
    print(f"Période: {start_date} → {end_date}")
    print()
    
    results = {}
    
    for config_key, config in CONFIGS.items():
        print("-" * 70)
        print(f"Configuration: {config['name']}")
        print(f"Description: {config['description']}")
        print("-" * 70)
        
        # Afficher les poids
        print("Poids:")
        for factor, weight in config["weights"].items():
            print(f"  {factor}: {weight*100:.0f}%")
        print()
        
        # Exécuter le backtest
        bt = WalkForwardBacktester(
            frozen_weights=config["weights"],
            benchmark="SPY",
        )
        
        bt.run(start_date=start_date, end_date=end_date)
        
        # Générer le rapport
        report_path = output_dir / f"backtest_{config_key}.json"
        report = bt.generate_report(output_path=report_path)
        
        if report is None:
            print(f"⚠️ Pas de résultats pour {config_key}")
            continue
        
        # Extraire les métriques
        s = report.summary
        r = report.risk_metrics
        
        # Calculer Sharpe approximatif
        if r["portfolio_volatility"] > 0:
            sharpe = (s["portfolio_cagr"] - 4.5) / r["portfolio_volatility"]
        else:
            sharpe = 0
        
        result = AttributionResult(
            config_name=config["name"],
            cagr=s["portfolio_cagr"],
            total_alpha=s["total_alpha"],
            hit_rate=s["hit_rate"],
            sharpe=round(sharpe, 2),
            info_ratio=s["information_ratio"],
            max_drawdown=r["max_drawdown"],
            tracking_error=r["tracking_error"],
        )
        
        results[config_key] = result
    
    # Afficher la comparaison
    print_comparison(results)
    
    # Sauvegarder
    save_attribution_report(results, output_dir)
    
    return results


def print_comparison(results: Dict[str, AttributionResult]):
    """Affiche la comparaison des configurations."""
    print()
    print("=" * 70)
    print("COMPARAISON DES CONFIGURATIONS")
    print("=" * 70)
    
    # Header
    print(f"{'Métrique':<20} ", end="")
    for config_key in results:
        print(f"{config_key:<18} ", end="")
    print()
    print("-" * 70)
    
    # Métriques
    metrics = [
        ("CAGR", "cagr", "%"),
        ("Alpha Total", "total_alpha", "%"),
        ("Hit Rate", "hit_rate", "%"),
        ("Sharpe", "sharpe", ""),
        ("Info Ratio", "info_ratio", ""),
        ("Max DD", "max_drawdown", "%"),
        ("Tracking Error", "tracking_error", "%"),
    ]
    
    for metric_name, attr, suffix in metrics:
        print(f"{metric_name:<20} ", end="")
        for config_key, result in results.items():
            value = getattr(result, attr)
            if suffix == "%":
                print(f"{value:+.2f}%{'':<12} ", end="")
            else:
                print(f"{value:.2f}{'':<15} ", end="")
        print()
    
    # Analyse
    print()
    print("-" * 70)
    print("ANALYSE")
    print("-" * 70)
    
    if "core" in results and "core_sm" in results:
        core = results["core"]
        core_sm = results["core_sm"]
        
        alpha_diff = core_sm.total_alpha - core.total_alpha
        sharpe_diff = core_sm.sharpe - core.sharpe
        ir_diff = core_sm.info_ratio - core.info_ratio
        
        print(f"\n📊 Impact du Smart Money (15%):")
        print(f"   Alpha: {alpha_diff:+.2f}%")
        print(f"   Sharpe: {sharpe_diff:+.2f}")
        print(f"   Info Ratio: {ir_diff:+.2f}")
        
        if alpha_diff > 0 and ir_diff > 0:
            print(f"\n   ✅ Smart Money AJOUTE de la valeur")
            print(f"   Recommandation: Garder à 15% ou réduire légèrement")
        elif alpha_diff > 0 and ir_diff <= 0:
            print(f"\n   ⚠️ Smart Money ajoute de l'alpha mais dégrade l'IR")
            print(f"   Recommandation: Réduire à 5-10%")
        else:
            print(f"\n   ❌ Smart Money N'AJOUTE PAS de valeur")
            print(f"   Recommandation: Réduire à 0-5% ou supprimer")
    
    if "sm_reduced" in results and "core_sm" in results:
        sm_reduced = results["sm_reduced"]
        core_sm = results["core_sm"]
        
        print(f"\n📊 Impact de la réduction SM (15% → 5%):")
        print(f"   Alpha: {sm_reduced.total_alpha - core_sm.total_alpha:+.2f}%")
        print(f"   Sharpe: {sm_reduced.sharpe - core_sm.sharpe:+.2f}")


def save_attribution_report(results: Dict[str, AttributionResult], output_dir: Path):
    """Sauvegarde le rapport d'attribution."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "configs": {k: asdict(v) for k, v in results.items()},
    }
    
    # Ajouter l'analyse
    if "core" in results and "core_sm" in results:
        core = results["core"]
        core_sm = results["core_sm"]
        
        report["smart_money_impact"] = {
            "alpha_contribution": round(core_sm.total_alpha - core.total_alpha, 2),
            "sharpe_contribution": round(core_sm.sharpe - core.sharpe, 2),
            "ir_contribution": round(core_sm.info_ratio - core.info_ratio, 2),
            "verdict": "positive" if (core_sm.total_alpha > core.total_alpha and core_sm.info_ratio > core.info_ratio) else "negative",
        }
    
    report_path = output_dir / "attribution_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Rapport: {report_path}")
    
    # Générer le markdown
    md_path = output_dir / "attribution_report.md"
    generate_attribution_markdown(results, md_path)
    print(f"📄 Markdown: {md_path}")


def generate_attribution_markdown(results: Dict[str, AttributionResult], output_path: Path):
    """Génère le rapport Markdown."""
    md = """# SmartMoney v2.4 — Rapport d'Attribution Factorielle

*Généré automatiquement*

---

## Objectif

Comparer trois versions du modèle pour déterminer si le facteur Smart Money apporte de l'alpha.

---

## Configurations Testées

| Config | Smart Money | Description |
|--------|-------------|-------------|
| **Core** | 0% | Quality/Value/Risk pur |
| **Core+SM** | 15% | Version v2.4 actuelle |
| **SM Réduit** | 5% | Compromis |

---

## Résultats

| Métrique | Core | Core+SM | SM Réduit |
|----------|------|---------|------------|
"""
    
    for metric, attr, fmt in [
        ("CAGR", "cagr", "{:+.2f}%"),
        ("Alpha Total", "total_alpha", "{:+.2f}%"),
        ("Hit Rate", "hit_rate", "{:.1f}%"),
        ("Sharpe", "sharpe", "{:.2f}"),
        ("Info Ratio", "info_ratio", "{:.2f}"),
        ("Max DD", "max_drawdown", "{:.2f}%"),
        ("Tracking Error", "tracking_error", "{:.2f}%"),
    ]:
        md += f"| {metric} |"
        for config_key in ["core", "core_sm", "sm_reduced"]:
            if config_key in results:
                value = getattr(results[config_key], attr)
                md += f" {fmt.format(value)} |"
            else:
                md += " N/A |"
        md += "\n"
    
    # Analyse
    md += """
---

## Analyse

"""
    
    if "core" in results and "core_sm" in results:
        core = results["core"]
        core_sm = results["core_sm"]
        
        alpha_diff = core_sm.total_alpha - core.total_alpha
        ir_diff = core_sm.info_ratio - core.info_ratio
        
        md += f"### Impact du Smart Money (15%)\n\n"
        md += f"- Alpha contribution: **{alpha_diff:+.2f}%**\n"
        md += f"- Info Ratio contribution: **{ir_diff:+.2f}**\n\n"
        
        if alpha_diff > 0 and ir_diff > 0:
            md += "✅ **Verdict: Smart Money AJOUTE de la valeur**\n\n"
            md += "Recommandation: Garder le poids actuel ou réduire légèrement.\n"
        elif alpha_diff > 0:
            md += "⚠️ **Verdict: Résultats mitigés**\n\n"
            md += "Recommandation: Réduire Smart Money à 5-10%.\n"
        else:
            md += "❌ **Verdict: Smart Money N'AJOUTE PAS de valeur**\n\n"
            md += "Recommandation: Réduire à 0-5% ou supprimer.\n"
    
    md += """
---

*Rapport généré par src/backtest_attribution.py*
"""
    
    with open(output_path, "w") as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(
        description="Attribution Factorielle SmartMoney v2.4"
    )
    parser.add_argument("--start", "-s", default="2015-01-01")
    parser.add_argument("--end", "-e", default="2024-12-31")
    parser.add_argument("--output", "-o", default=None)
    
    args = parser.parse_args()
    
    output_dir = Path(args.output) if args.output else None
    
    run_attribution(
        start_date=args.start,
        end_date=args.end,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
