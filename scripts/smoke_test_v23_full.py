#!/usr/bin/env python3
"""SmartMoney v2.3 — Smoke Test Complet (Sprint 1 + 2 + 3)

Test rapide de tout le pipeline v2.3.

Usage:
    python scripts/smoke_test_v23_full.py

Date: Décembre 2025
"""

import sys
import os
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

import pandas as pd
import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_data(n_symbols: int = 30):
    """Crée des données de test."""
    np.random.seed(42)
    
    sectors = ["Technology", "Healthcare", "Financials", "Industrials"]
    
    universe = []
    for i in range(n_symbols):
        is_quality = np.random.random() > 0.4
        
        market_cap = np.random.uniform(5e9, 200e9)
        equity = market_cap * np.random.uniform(0.3, 0.7)
        de_ratio = np.random.uniform(0.2, 0.8) if is_quality else np.random.uniform(1.5, 3)
        total_debt = equity * de_ratio
        
        ebit_margin = np.random.uniform(0.12, 0.25) if is_quality else np.random.uniform(0.05, 0.12)
        revenue = market_cap * np.random.uniform(0.4, 0.8)
        ebit = revenue * ebit_margin
        
        universe.append({
            "symbol": f"TICK{i:03d}",
            "sector": np.random.choice(sectors),
            "market_cap": market_cap,
            "adv_usd": market_cap * np.random.uniform(0.002, 0.01),
            "revenue": revenue,
            "ebit": ebit,
            "net_income": ebit * np.random.uniform(0.6, 0.85),
            "fcf": ebit * np.random.uniform(0.4, 0.8),
            "total_debt": total_debt,
            "equity": equity,
            "cash": equity * np.random.uniform(0.1, 0.3),
            "interest_expense": total_debt * 0.05,
            "vol_30d": np.random.uniform(15, 45),
            "pe_ratio": np.random.uniform(10, 30),
            "td_price": np.random.uniform(50, 500),
            # Scores v2.2 simulés
            "score_sm": np.random.uniform(0.3, 0.9),
            "score_insider": np.random.uniform(0.3, 0.8),
            "score_momentum": np.random.uniform(0.3, 0.7),
        })
    
    return pd.DataFrame(universe)


def run_full_smoke_test():
    """Lance le smoke test complet."""
    print("=" * 70)
    print("SMARTMONEY v2.3 — SMOKE TEST COMPLET")
    print("=" * 70)
    print()
    
    errors = []
    
    # === SPRINT 1: Filtres ===
    print("\n" + "=" * 50)
    print("SPRINT 1: FILTRES & VALIDATION")
    print("=" * 50)
    
    # 1. Config
    print("\n1. Configuration v2.3...")
    try:
        from config_v23 import WEIGHTS_V23, HARD_FILTERS, LIQUIDITY
        
        total = sum(WEIGHTS_V23.values())
        assert abs(total - 1.0) < 0.001
        print(f"   \u2705 Poids: somme = {total:.3f}")
        print(f"      smart_money={WEIGHTS_V23['smart_money']}, value={WEIGHTS_V23['value']}, quality={WEIGHTS_V23['quality']}")
    except Exception as e:
        errors.append(f"Config: {e}")
        print(f"   \u274c {e}")
    
    # 2. Filtres liquidité
    print("\n2. Filtres liquidité...")
    try:
        from src.filters.liquidity import apply_liquidity_filters
        
        universe = create_test_data(50)
        filtered = apply_liquidity_filters(universe, verbose=False)
        print(f"   \u2705 {len(filtered)}/{len(universe)} passent les filtres")
    except Exception as e:
        errors.append(f"Liquidity: {e}")
        print(f"   \u274c {e}")
    
    # 3. Hard filters
    print("\n3. Hard filters...")
    try:
        from src.filters.hard_filters import apply_hard_filters
        
        filtered2 = apply_hard_filters(filtered, verbose=False)
        print(f"   \u2705 {len(filtered2)}/{len(filtered)} passent")
    except Exception as e:
        errors.append(f"Hard filters: {e}")
        print(f"   \u274c {e}")
    
    # === SPRINT 2: Scoring ===
    print("\n" + "=" * 50)
    print("SPRINT 2: SCORING BUFFETT-STYLE")
    print("=" * 50)
    
    # 4. Value scoring
    print("\n4. Value Composite...")
    try:
        from src.scoring.value_composite import score_value
        
        df = score_value(filtered2)
        print(f"   \u2705 mean={df['score_value'].mean():.3f}, std={df['score_value'].std():.3f}")
    except Exception as e:
        errors.append(f"Value: {e}")
        print(f"   \u274c {e}")
    
    # 5. Quality scoring
    print("\n5. Quality Composite...")
    try:
        from src.scoring.quality_composite import score_quality
        
        df = score_quality(df)
        print(f"   \u2705 mean={df['score_quality'].mean():.3f}, std={df['score_quality'].std():.3f}")
    except Exception as e:
        errors.append(f"Quality: {e}")
        print(f"   \u274c {e}")
    
    # 6. Risk scoring
    print("\n6. Risk Score (inversé)...")
    try:
        from src.scoring.risk_score import score_risk
        
        df = score_risk(df)
        print(f"   \u2705 mean={df['score_risk'].mean():.3f} (rappel: élevé = sûr)")
    except Exception as e:
        errors.append(f"Risk: {e}")
        print(f"   \u274c {e}")
    
    # 7. Composite
    print("\n7. Composite v2.3...")
    try:
        from src.scoring.composite import calculate_composite_score
        
        df = calculate_composite_score(df)
        print(f"   \u2705 Composite: mean={df['score_composite'].mean():.3f}")
        print(f"   \u2705 Buffett:   mean={df['buffett_score'].mean():.3f}")
    except Exception as e:
        errors.append(f"Composite: {e}")
        print(f"   \u274c {e}")
    
    # === SPRINT 3: Backtest ===
    print("\n" + "=" * 50)
    print("SPRINT 3: BACKTEST & MÉTRIQUES")
    print("=" * 50)
    
    # 8. Métriques
    print("\n8. Calcul métriques...")
    try:
        from src.backtest.metrics import calculate_metrics
        
        # Générer des rendements simulés
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", "2023-12-31", freq="B")
        returns = pd.Series(
            np.random.normal(0.0004, 0.012, len(dates)),
            index=dates
        )
        
        metrics = calculate_metrics(returns)
        print(f"   \u2705 CAGR: {metrics.cagr:+.1f}%")
        print(f"   \u2705 Sharpe: {metrics.sharpe_ratio:.2f}")
        print(f"   \u2705 Max DD: {metrics.max_drawdown:.1f}%")
    except Exception as e:
        errors.append(f"Metrics: {e}")
        print(f"   \u274c {e}")
    
    # 9. Stress tests
    print("\n9. Stress tests...")
    try:
        from src.backtest.stress_tests import StressTester
        
        tester = StressTester()
        print(f"   \u2705 {len(tester.periods)} périodes de stress définies")
        print(f"      Ex: covid_crash, gfc_2008, rate_hikes_2022...")
    except Exception as e:
        errors.append(f"Stress tests: {e}")
        print(f"   \u274c {e}")
    
    # 10. Engine v2.3
    print("\n10. Engine v2.3 intégré...")
    try:
        from src.engine_v23 import SmartMoneyEngineV23
        
        engine = SmartMoneyEngineV23()
        summary = engine.summary()
        
        print(f"   \u2705 Version: {summary['version']}")
        print(f"   \u2705 Poids: value={engine.weights['value']}, quality={engine.weights['quality']}")
    except Exception as e:
        errors.append(f"Engine v2.3: {e}")
        print(f"   \u274c {e}")
    
    # 11. Reports
    print("\n11. Génération rapports...")
    try:
        from src.backtest.reports import generate_report
        from src.backtest.backtest_v23 import BacktestResult
        
        # Créer un résultat minimal
        result = BacktestResult(
            metrics=metrics,
            returns=returns,
            cumulative_returns=(1 + returns).cumprod(),
            drawdowns=pd.Series([0] * len(returns)),
            weights_history=pd.DataFrame(),
            holdings_history=[],
            validation_passed=True,
            validation_notes=["Test"],
        )
        
        text_report = generate_report(result, format="text")
        json_report = generate_report(result, format="json")
        html_report = generate_report(result, format="html")
        
        print(f"   \u2705 Rapport texte: {len(text_report)} caractères")
        print(f"   \u2705 Rapport JSON: {len(json_report)} caractères")
        print(f"   \u2705 Rapport HTML: {len(html_report)} caractères")
    except Exception as e:
        errors.append(f"Reports: {e}")
        print(f"   \u274c {e}")
    
    # === TOP HOLDINGS ===
    print("\n" + "=" * 50)
    print("TOP 5 PAR SCORE COMPOSITE")
    print("=" * 50)
    
    try:
        top5 = df.nlargest(5, "score_composite")[["symbol", "sector", "score_composite", "buffett_score"]]
        print(top5.to_string(index=False))
    except:
        pass
    
    # === RÉSUMÉ ===
    print("\n" + "=" * 70)
    if errors:
        print(f"\u274c SMOKE TEST ÉCHOUÉ — {len(errors)} erreur(s):")
        for e in errors:
            print(f"   - {e}")
        return False
    else:
        print("\u2705 SMOKE TEST v2.3 COMPLET RÉUSSI")
        print()
        print("Tous les sprints validés:")
        print("  \u2705 Sprint 1: Filtres & Validation")
        print("  \u2705 Sprint 2: Scoring Buffett-style")
        print("  \u2705 Sprint 3: Backtest & Métriques")
        print()
        print("Commandes disponibles:")
        print("  pytest tests/test_v23_*.py -v          # Tous les tests")
        print("  python scripts/run_backtest_v23.py    # Backtest complet")
        print()
        print("Pour utiliser l'engine v2.3:")
        print("  from src.engine_v23 import SmartMoneyEngineV23")
        print("  engine = SmartMoneyEngineV23()")
        print("  engine.load_data()")
        print("  engine.enrich(top_n=50)")
        print("  engine.apply_filters_v23()")
        print("  engine.calculate_scores_v23()")
        print("  engine.optimize()")
        return True


if __name__ == "__main__":
    success = run_full_smoke_test()
    sys.exit(0 if success else 1)
