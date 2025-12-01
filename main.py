"""SmartMoney Engine - Point d'entrée principal v2.2"""
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

from config import (
    OUTPUTS, TWELVE_DATA_KEY, OPENAI_KEY,
    BACKTEST, VALIDATION, SCORING, CORRELATION
)
from src.engine import SmartMoneyEngine
from src.copilot import Copilot
from src.dashboard import generate_dashboard


def parse_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="SmartMoney Engine v2.2")
    
    parser.add_argument(
        "--backtest",
        choices=["legacy", "walkforward", "both", "none"],
        default="both",
        help="Type de backtest: legacy (ancien), walkforward (nouveau), both, none"
    )
    
    parser.add_argument(
        "--rebal-freq",
        choices=["W", "M", "Q"],
        default=BACKTEST.get("rebal_freq", "M"),
        help="Fréquence de rebalancement pour walk-forward (W=hebdo, M=mensuel, Q=trimestriel)"
    )
    
    parser.add_argument(
        "--require-outperformance",
        action="store_true",
        default=VALIDATION.get("require_outperformance", False),
        help="Échouer si le portefeuille ne bat pas les benchmarks"
    )
    
    parser.add_argument(
        "--top-n",
        type=int,
        default=40,
        help="Nombre de tickers à enrichir (défaut: 40)"
    )
    
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Passer l'enrichissement Twelve Data (utilise le cache)"
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 60)
    print("🚀 SMARTMONEY ENGINE v2.2")
    print("   Scoring + Fondamentaux + HRP + Backtest Walk-Forward")
    print("=" * 60)
    
    # === CRÉER LE DOSSIER DATÉ ===
    today = datetime.now().strftime("%Y-%m-%d")
    dated_dir = OUTPUTS / today
    dated_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Dossier de sortie: {dated_dir}")
    
    # === AFFICHER CONFIG ===
    print(f"\n⚙️ CONFIGURATION:")
    print(f"   Backtest: {args.backtest}")
    print(f"   Rebal freq: {args.rebal_freq}")
    print(f"   Z-score scoring: {SCORING.get('use_zscore', False)}")
    print(f"   Sector-neutral quality: {SCORING.get('sector_neutral_quality', False)}")
    print(f"   Real correlations: {CORRELATION.get('use_real_correlation', False)}")
    
    # === VÉRIFICATIONS ===
    if not TWELVE_DATA_KEY:
        print("\n⚠️ API_TWELVEDATA non configurée - enrichissement désactivé")
    if not OPENAI_KEY:
        print("⚠️ API_OPENAI non configurée - copilot désactivé")
    
    # === ENGINE ===
    print("\n" + "-" * 60)
    print("PHASE 1: Chargement des données")
    print("-" * 60)
    engine = SmartMoneyEngine()
    engine.load_data()
    
    print("\n" + "-" * 60)
    print("PHASE 2: Enrichissement Twelve Data")
    print("   (Quote, Profile, RSI, TimeSeries, Statistics,")
    print("    Balance Sheet, Income Statement, Cash Flow)")
    print("-" * 60)
    if TWELVE_DATA_KEY and not args.skip_enrichment:
        engine.enrich(top_n=args.top_n)
    else:
        if args.skip_enrichment:
            print("⏭️ Skipped (--skip-enrichment)")
        else:
            print("⏭️ Skipped (pas de clé API)")
    
    print("\n" + "-" * 60)
    print("PHASE 3: Scoring")
    print("-" * 60)
    engine.calculate_scores()
    engine.apply_filters()
    
    print("\n" + "-" * 60)
    print("PHASE 4: Optimisation HRP")
    print("-" * 60)
    engine.optimize()
    
    print("\n" + "-" * 60)
    print("PHASE 5: Export Portfolio")
    print("-" * 60)
    portfolio = engine.export(dated_dir)
    
    # === DASHBOARD HTML ===
    print("\n" + "-" * 60)
    print("PHASE 6: Dashboard HTML")
    print("-" * 60)
    generate_dashboard(portfolio, dated_dir)
    
    # === BACKTEST ===
    validation_result = None
    walkforward_result = None
    backtest_passed = True
    
    # --- BACKTEST LEGACY ---
    if args.backtest in ["legacy", "both"] and TWELVE_DATA_KEY:
        print("\n" + "-" * 60)
        print("PHASE 7a: Backtest Legacy")
        print("-" * 60)
        try:
            from src.backtest import Backtester
            backtester = Backtester()
            result = backtester.generate_report(
                portfolio.get("portfolio", []),
                dated_dir,
                validate=True,
                strict=VALIDATION.get("strict_benchmark", True)
            )
            validation_result = result.get("validation")
            
            if validation_result:
                _print_legacy_validation(validation_result)
                
        except Exception as e:
            print(f"⚠️ Erreur Backtest Legacy: {e}")
    
    # --- BACKTEST WALK-FORWARD ---
    if args.backtest in ["walkforward", "both"] and TWELVE_DATA_KEY:
        print("\n" + "-" * 60)
        print("PHASE 7b: Backtest Walk-Forward (sans look-ahead bias)")
        print("-" * 60)
        try:
            walkforward_result = run_walkforward_backtest(
                portfolio, 
                dated_dir,
                rebal_freq=args.rebal_freq
            )
            
            if walkforward_result:
                wf_metrics = walkforward_result.get("portfolio", {})
                backtest_passed = _validate_walkforward(wf_metrics, walkforward_result.get("benchmarks", {}))
                
        except Exception as e:
            print(f"⚠️ Erreur Backtest Walk-Forward: {e}")
            import traceback
            traceback.print_exc()
    
    if args.backtest == "none":
        print("\n⏭️ Backtest skipped (--backtest none)")
    elif not TWELVE_DATA_KEY:
        print("\n⏭️ Backtest skipped (pas de clé API)")
    
    # === COPILOT ===
    alerts = _generate_alerts(validation_result, walkforward_result)
    
    if OPENAI_KEY:
        print("\n" + "-" * 60)
        print("PHASE 8: IA Copilot")
        print("-" * 60)
        try:
            copilot = Copilot()
            copilot.export_memo(portfolio, dated_dir)
            
            copilot_alerts = copilot.generate_alerts(portfolio)
            alerts.extend(copilot_alerts)
            
        except Exception as e:
            print(f"⚠️ Erreur Copilot: {e}")
    else:
        print("\n⏭️ Copilot skipped (pas de clé API)")
    
    # Export des alertes
    if alerts:
        alerts_path = dated_dir / "alerts.json"
        with open(alerts_path, "w") as f:
            json.dump(alerts, f, indent=2)
        print(f"📁 {len(alerts)} alertes exportées: {alerts_path.name}")
    
    # === CHECK OUTPERFORMANCE REQUIREMENT ===
    if args.require_outperformance and not backtest_passed:
        print("\n" + "=" * 60)
        print("❌ ÉCHEC: Portefeuille ne bat pas les benchmarks")
        print("   Mode --require-outperformance activé")
        print("   Le portefeuille ne sera PAS publié")
        print("=" * 60)
        return 1
    
    # === COPIER DANS outputs/latest/ ===
    latest_dir = OUTPUTS / "latest"
    try:
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        shutil.copytree(dated_dir, latest_dir)
        print(f"\n📁 Copié vers: outputs/latest/")
    except Exception as e:
        print(f"⚠️ Erreur copie vers latest: {e}")
    
    # === RÉSUMÉ ===
    _print_summary(engine, portfolio, validation_result, walkforward_result, dated_dir)
    
    return 0


def run_walkforward_backtest(portfolio: dict, output_dir: Path, rebal_freq: str = "M") -> dict:
    """
    Lance le backtest walk-forward.
    
    Args:
        portfolio: Données du portefeuille
        output_dir: Dossier de sortie
        rebal_freq: Fréquence de rebalancement
        
    Returns:
        Résultats du backtest ou None si erreur
    """
    from src.backtest_walkforward import (
        WalkForwardBacktester, 
        PriceDataLoader,
        create_simple_portfolio_builder
    )
    
    positions = portfolio.get("portfolio", [])
    symbols = [p["symbol"] for p in positions]
    
    if not symbols:
        print("⚠️ Pas de positions dans le portefeuille")
        return None
    
    print(f"📊 {len(symbols)} tickers à backtester")
    
    # Charger les prix
    cache_path = OUTPUTS / BACKTEST.get("cache_path", "price_cache.parquet")
    loader = PriceDataLoader()
    
    try:
        if cache_path.exists() and BACKTEST.get("cache_prices", True):
            print(f"💾 Chargement du cache: {cache_path.name}")
            prices = loader.load_from_cache(cache_path)
            
            # Vérifier les symboles manquants
            all_symbols = set(symbols + BACKTEST.get("benchmarks", ["SPY"]))
            missing = all_symbols - set(prices.columns)
            
            if missing:
                print(f"📥 Téléchargement symboles manquants: {missing}")
                import pandas as pd
                new_prices = loader.fetch_prices(list(missing))
                prices = pd.concat([prices, new_prices], axis=1)
                loader.save_to_cache(prices, cache_path)
        else:
            print("📥 Téléchargement des prix historiques...")
            all_symbols = symbols + BACKTEST.get("benchmarks", ["SPY"])
            prices = loader.fetch_prices(all_symbols, outputsize=900)
            
            if BACKTEST.get("cache_prices", True):
                loader.save_to_cache(prices, cache_path)
                
    except Exception as e:
        print(f"⚠️ Erreur chargement prix: {e}")
        return None
    
    # Séparer benchmarks et portfolio
    benchmark_cols = [c for c in BACKTEST.get("benchmarks", ["SPY"]) if c in prices.columns]
    benchmarks = {col: prices[col] for col in benchmark_cols}
    portfolio_prices = prices.drop(columns=benchmark_cols, errors="ignore")
    
    # Créer le builder
    from src.engine import SmartMoneyEngine
    build_fn = create_simple_portfolio_builder(SmartMoneyEngine)
    
    # Lancer le backtest
    backtester = WalkForwardBacktester(
        prices=portfolio_prices,
        build_portfolio_fn=build_fn,
        benchmarks=benchmarks,
        tc_bps=BACKTEST.get("tc_bps", 10),
        lookback_days=BACKTEST.get("lookback_days", 252),
        risk_free_rate=BACKTEST.get("risk_free_rate", 0.045)
    )
    
    results = backtester.run(
        rebal_freq=rebal_freq,
        verbose=True
    )
    
    # Exporter le rapport
    backtester.export_report(output_dir)
    
    return results


def _validate_walkforward(metrics: dict, benchmarks: dict) -> bool:
    """Valide les résultats du backtest walk-forward."""
    
    portfolio_return = metrics.get("annual_return_pct", 0)
    portfolio_sharpe = metrics.get("sharpe", 0)
    portfolio_dd = metrics.get("max_drawdown_pct", 0)
    
    # Vérifier les seuils
    min_sharpe = VALIDATION.get("min_sharpe", 0.5)
    max_dd = VALIDATION.get("max_drawdown", -25)
    
    sharpe_ok = portfolio_sharpe >= min_sharpe
    dd_ok = portfolio_dd >= max_dd
    
    # Vérifier vs benchmarks
    beats_benchmarks = True
    for name, bench in benchmarks.items():
        bench_return = bench.get("annual_return_pct", 0)
        if portfolio_return <= bench_return:
            beats_benchmarks = False
            break
    
    print("\n" + "=" * 60)
    print("🎯 VALIDATION WALK-FORWARD")
    print("=" * 60)
    print(f"   Sharpe: {portfolio_sharpe:.2f} (min: {min_sharpe}) {'✅' if sharpe_ok else '❌'}")
    print(f"   Max DD: {portfolio_dd:.1f}% (max: {max_dd}%) {'✅' if dd_ok else '❌'}")
    print(f"   Bat benchmarks: {'✅' if beats_benchmarks else '❌'}")
    
    is_valid = sharpe_ok and dd_ok
    if VALIDATION.get("strict_benchmark", True):
        is_valid = is_valid and beats_benchmarks
    
    if is_valid:
        print("\n✅ PORTEFEUILLE VALIDÉ")
    else:
        print("\n⚠️ PORTEFEUILLE NE PASSE PAS TOUS LES CRITÈRES")
    
    return is_valid


def _print_legacy_validation(validation_result: dict):
    """Affiche les résultats de validation legacy."""
    print("\n" + "=" * 60)
    if validation_result.get("beats_all"):
        print("🏆 VALIDATION LEGACY: PORTEFEUILLE BAT SPY ET CAC")
    elif validation_result.get("beats_spy"):
        print("⚠️ VALIDATION LEGACY: Bat SPY mais pas CAC")
    elif validation_result.get("beats_cac"):
        print("⚠️ VALIDATION LEGACY: Bat CAC mais pas SPY")
    else:
        print("❌ VALIDATION LEGACY: SOUS-PERFORMANCE vs BENCHMARKS")
    print("=" * 60)
    
    print(f"   Portefeuille 3M: {validation_result['portfolio_return']:+.2f}%")
    print(f"   SPY 3M:          {validation_result['spy_return']:+.2f}%  (Alpha: {validation_result['alpha_spy']:+.2f}%)")
    print(f"   CAC 3M:          {validation_result['cac_return']:+.2f}%  (Alpha: {validation_result['alpha_cac']:+.2f}%)")


def _generate_alerts(validation_result: dict, walkforward_result: dict) -> list:
    """Génère les alertes basées sur les résultats de backtest."""
    alerts = []
    
    # Alerte si sous-performance (legacy)
    if validation_result and not validation_result.get("beats_all"):
        severity = "high" if not validation_result.get("valid") else "medium"
        alerts.append({
            "type": "benchmark_legacy",
            "severity": severity,
            "symbol": None,
            "message": validation_result.get("message", "Portefeuille sous-performe (legacy)"),
            "details": {
                "portfolio_return": validation_result.get("portfolio_return"),
                "spy_return": validation_result.get("spy_return"),
                "cac_return": validation_result.get("cac_return"),
            }
        })
    
    # Alerte si walk-forward échoue
    if walkforward_result:
        wf_metrics = walkforward_result.get("portfolio", {})
        
        if wf_metrics.get("sharpe", 0) < VALIDATION.get("min_sharpe", 0.5):
            alerts.append({
                "type": "sharpe_low",
                "severity": "medium",
                "symbol": None,
                "message": f"Sharpe ratio faible: {wf_metrics.get('sharpe', 0):.2f}",
                "details": wf_metrics
            })
        
        if wf_metrics.get("max_drawdown_pct", 0) < VALIDATION.get("max_drawdown", -25):
            alerts.append({
                "type": "drawdown_high",
                "severity": "high",
                "symbol": None,
                "message": f"Drawdown élevé: {wf_metrics.get('max_drawdown_pct', 0):.1f}%",
                "details": wf_metrics
            })
    
    return alerts


def _print_summary(engine, portfolio: dict, validation_result: dict, 
                   walkforward_result: dict, dated_dir: Path):
    """Affiche le résumé final."""
    print("\n" + "=" * 60)
    print("✅ TERMINÉ")
    print("=" * 60)
    
    metrics = engine.portfolio_metrics
    print(f"\n📊 MÉTRIQUES PORTEFEUILLE:")
    print(f"   Positions: {metrics.get('positions', 0)}")
    print(f"   Perf 3M: {metrics.get('perf_3m', 'N/A')}%")
    print(f"   Perf YTD: {metrics.get('perf_ytd', 'N/A')}%")
    print(f"   Vol 30j: {metrics.get('vol_30d', 'N/A')}%")
    print(f"   ROE moyen: {metrics.get('avg_roe', 'N/A')}%")
    print(f"   D/E moyen: {metrics.get('avg_debt_equity', 'N/A')}")
    print(f"   Marge nette moy: {metrics.get('avg_net_margin', 'N/A')}%")
    
    # Walk-forward metrics
    if walkforward_result:
        wf = walkforward_result.get("portfolio", {})
        print(f"\n📈 BACKTEST WALK-FORWARD:")
        print(f"   Return annualisé: {wf.get('annual_return_pct', 'N/A')}%")
        print(f"   Sharpe: {wf.get('sharpe', 'N/A')}")
        print(f"   Sortino: {wf.get('sortino', 'N/A')}")
        print(f"   Max Drawdown: {wf.get('max_drawdown_pct', 'N/A')}%")
        print(f"   VaR 95%: {wf.get('var_95_daily_pct', 'N/A')}%")
        print(f"   Turnover moyen: {wf.get('avg_turnover_per_rebal_pct', 'N/A')}%")
    
    # Legacy validation
    if validation_result:
        print(f"\n🎯 STATUT BENCHMARK (Legacy):")
        if validation_result.get("beats_all"):
            print("   ✅ Bat SPY ET CAC sur 3M")
        else:
            print(f"   {'✅' if validation_result.get('beats_spy') else '❌'} vs SPY ({validation_result['alpha_spy']:+.2f}%)")
            print(f"   {'✅' if validation_result.get('beats_cac') else '❌'} vs CAC ({validation_result['alpha_cac']:+.2f}%)")
    
    # Fichiers générés
    print(f"\n📁 Fichiers générés dans {dated_dir.name}/:")
    for f in sorted(dated_dir.iterdir()):
        print(f"   • {f.name}")
    
    # Top 10
    print("\n🏆 TOP 10 POSITIONS:")
    for i, pos in enumerate(portfolio.get("portfolio", [])[:10], 1):
        symbol = pos.get("symbol", "?")
        weight = pos.get("weight", 0) * 100
        score = pos.get("score_composite", 0)
        sector = pos.get("sector", "?")[:15]
        roe = pos.get("roe")
        roe_str = f"ROE:{roe:.0f}%" if roe else ""
        print(f"  {i:2}. {symbol:6} {weight:5.2f}%  (score: {score:.3f}) [{sector}] {roe_str}")
    
    # Répartition sectorielle
    if metrics.get("sector_weights"):
        print("\n🏢 RÉPARTITION SECTORIELLE:")
        for sector, weight in sorted(metrics["sector_weights"].items(), key=lambda x: -x[1]):
            bar = "█" * int(weight / 2)
            print(f"   {sector:25} {weight:5.1f}% {bar}")


if __name__ == "__main__":
    sys.exit(main())
