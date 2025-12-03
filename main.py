#!/usr/bin/env python3
"""SmartMoney Portfolio Generator

Usage:
    python main.py                              # Mode smart_money (80 tickers)
    python main.py --mode sp500                 # Mode S&P 500 (503 tickers)
    python main.py --mode sp500 --top-n 100    # S&P 500, top 100 seulement
    python main.py --engine v23 --dry-run
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def parse_args():
    parser = argparse.ArgumentParser(description="SmartMoney Portfolio Generator")
    parser.add_argument("--engine", choices=["v22", "v23"], default="v23")
    parser.add_argument("--mode", choices=["smart_money", "sp500"], default=None,
                       help="Mode: smart_money (80 tickers) ou sp500 (503 tickers)")
    parser.add_argument("--top-n", type=int, default=None,
                       help="Nombre de tickers à enrichir (défaut: 40 pour smart_money, 500 pour sp500)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--skip-extras", action="store_true", help="Skip dashboard, memo, alerts")
    parser.add_argument("--skip-backtest", action="store_true", help="Skip backtest")
    parser.add_argument("--backtest-days", type=int, default=90, help="Backtest period in days")
    return parser.parse_args()


def generate_extras(portfolio_data: dict, output_dir: Path, engine_version: str):
    """Génère dashboard, memo Buffett et alerts."""
    
    # 1. Dashboard HTML
    try:
        from src.dashboard import generate_dashboard
        generate_dashboard(portfolio_data, output_dir)
        print("   ✓ dashboard.html")
    except Exception as e:
        print(f"   ⚠️ Dashboard: {e}")
    
    # 2. Memo Buffett style
    try:
        from src.memo_buffett import generate_buffett_memo
        generate_buffett_memo(portfolio_data, output_dir)
        print("   ✓ memo.md (Buffett style)")
    except ImportError:
        try:
            generate_basic_memo(portfolio_data, output_dir, engine_version)
            print("   ✓ memo.md (basic)")
        except Exception as e:
            print(f"   ⚠️ Memo: {e}")
    except Exception as e:
        print(f"   ⚠️ Memo: {e}")
    
    # 3. Alerts JSON
    try:
        generate_alerts(portfolio_data, output_dir)
        print("   ✓ alerts.json")
    except Exception as e:
        print(f"   ⚠️ Alerts: {e}")


def generate_basic_memo(portfolio_data: dict, output_dir: Path, engine_version: str):
    """Génère un memo markdown basique (fallback)."""
    metrics = portfolio_data.get("metrics", {})
    positions = portfolio_data.get("portfolio", [])
    date_str = portfolio_data.get("metadata", {}).get("date", datetime.now().strftime("%Y-%m-%d"))
    
    top5 = sorted(positions, key=lambda x: x.get("weight", 0), reverse=True)[:5]
    top5_str = "\n".join([
        f"| {p.get('symbol', 'N/A')} | {p.get('sector', 'N/A')[:15]} | {p.get('weight', 0)*100:.1f}% | {p.get('score_composite', 0):.3f} |"
        for p in top5
    ])
    
    sector_weights = metrics.get("sector_weights", {})
    sectors_str = ", ".join([f"{k}: {v}%" for k, v in sorted(sector_weights.items(), key=lambda x: -x[1])[:5]])
    
    memo = f"""# 📊 SmartMoney Portfolio — {date_str}

## Résumé

| Métrique | Valeur |
|----------|--------|
| Engine | v{engine_version} |
| Positions | {metrics.get('positions', len(positions))} |
| Perf 3M | {metrics.get('perf_3m', 'N/A')}% |
| Perf YTD | {metrics.get('perf_ytd', 'N/A')}% |
| Volatilité 30j | {metrics.get('vol_30d', 'N/A')}% |

## Top 5 Positions

| Ticker | Secteur | Poids | Score |
|--------|---------|-------|-------|
{top5_str}

## Répartition Sectorielle

{sectors_str}

---
_Généré par SmartMoney Engine v{engine_version}_
"""
    
    memo_path = output_dir / "memo.md"
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo)


def generate_alerts(portfolio_data: dict, output_dir: Path):
    """Génère des alertes basées sur les métriques."""
    positions = portfolio_data.get("portfolio", [])
    alerts = []
    
    for pos in positions:
        symbol = pos.get("symbol", "")
        
        # RSI extrême
        rsi = pos.get("rsi")
        if rsi and rsi < 30:
            alerts.append({
                "type": "opportunity",
                "ticker": symbol,
                "message": f"RSI survente ({rsi:.0f}) - opportunité potentielle",
                "severity": "medium"
            })
        elif rsi and rsi > 70:
            alerts.append({
                "type": "warning",
                "ticker": symbol,
                "message": f"RSI surachat ({rsi:.0f}) - prudence",
                "severity": "medium"
            })
        
        # Volatilité élevée
        vol = pos.get("vol_30d")
        if vol and vol > 50:
            alerts.append({
                "type": "risk",
                "ticker": symbol,
                "message": f"Volatilité élevée ({vol:.0f}%)",
                "severity": "high"
            })
        
        # Performance négative forte
        perf_ytd = pos.get("perf_ytd")
        if perf_ytd and perf_ytd < -30:
            alerts.append({
                "type": "warning",
                "ticker": symbol,
                "message": f"Forte baisse YTD ({perf_ytd:.0f}%) - vérifier les fondamentaux",
                "severity": "high"
            })
        
        # D/E élevé
        de = pos.get("debt_equity")
        if de and de > 2:
            alerts.append({
                "type": "risk",
                "ticker": symbol,
                "message": f"Endettement élevé (D/E={de:.1f})",
                "severity": "medium"
            })
        
        # ROE négatif
        roe = pos.get("roe")
        if roe and roe < 0:
            alerts.append({
                "type": "warning",
                "ticker": symbol,
                "message": f"ROE négatif ({roe:.1f}%) - business en difficulté?",
                "severity": "high"
            })
        
        # FCF négatif
        fcf = pos.get("fcf")
        if fcf and fcf < 0:
            alerts.append({
                "type": "warning",
                "ticker": symbol,
                "message": "FCF négatif - cash burn",
                "severity": "medium"
            })
    
    # Alertes portfolio level
    metrics = portfolio_data.get("metrics", {})
    vol_port = metrics.get("vol_30d")
    if vol_port and vol_port > 25:
        alerts.append({
            "type": "risk",
            "ticker": "PORTFOLIO",
            "message": f"Volatilité portefeuille élevée ({vol_port:.1f}%)",
            "severity": "medium"
        })
    
    alerts_data = {
        "generated_at": datetime.now().isoformat(),
        "count": len(alerts),
        "by_severity": {
            "high": len([a for a in alerts if a["severity"] == "high"]),
            "medium": len([a for a in alerts if a["severity"] == "medium"]),
            "low": len([a for a in alerts if a["severity"] == "low"])
        },
        "alerts": alerts
    }
    
    alerts_path = output_dir / "alerts.json"
    with open(alerts_path, "w", encoding="utf-8") as f:
        json.dump(alerts_data, f, indent=2)


def run_real_backtest(portfolio_data: dict, output_dir: Path, days: int = 90) -> dict:
    """
    Lance le VRAI backtest walk-forward avec comparaison SPY/CAC.
    
    Returns:
        dict avec résultats et validation
    """
    print("\n" + "="*60)
    print("📈 BACKTEST RÉEL vs SPY & CAC40")
    print("="*60)
    
    try:
        # Import correct : BacktestEngine au lieu de Backtester
        from src.backtest import BacktestEngine
        
        positions = portfolio_data.get("portfolio", [])
        
        if not positions:
            print("   ⚠️ Pas de positions pour le backtest")
            return {"error": "No positions"}
        
        # Initialiser le backtester
        backtester = BacktestEngine()
        
        # Lancer le backtest complet avec validation
        result = backtester.generate_report(
            portfolio=positions,
            output_dir=output_dir,
            validate=True,
            strict=True  # Doit battre SPY ET CAC
        )
        
        # Récupérer le résultat de validation
        validation = result.get("validation", {})
        
        print("\n" + "-"*60)
        print("🎯 VERDICT")
        print("-"*60)
        
        if validation:
            if validation.get("valid"):
                print("✅ PORTEFEUILLE VALIDÉ")
            else:
                print("⚠️ PORTEFEUILLE SOUS-PERFORME")
            
            print(f"\n   Portfolio:  {validation.get('portfolio_return', 0):+.2f}%")
            print(f"   vs SPY:     {validation.get('alpha_spy', 0):+.2f}% {'✅' if validation.get('beats_spy') else '❌'}")
            print(f"   vs CAC40:   {validation.get('alpha_cac', 0):+.2f}% {'✅' if validation.get('beats_cac') else '❌'}")
        
        return result
        
    except ImportError as e:
        print(f"   ⚠️ Module backtest non disponible: {e}")
        return generate_backtest_fallback(portfolio_data, output_dir)
    except Exception as e:
        print(f"   ⚠️ Erreur backtest: {e}")
        import traceback
        traceback.print_exc()
        return generate_backtest_fallback(portfolio_data, output_dir)


def generate_backtest_fallback(portfolio_data: dict, output_dir: Path) -> dict:
    """Génère un backtest estimé si le vrai échoue."""
    print("   ↳ Génération backtest estimé (fallback)...")
    
    positions = portfolio_data.get("portfolio", [])
    metrics = portfolio_data.get("metrics", {})
    
    # Métriques approximatives
    perf_3m = metrics.get("perf_3m", 0) or 0
    perf_ytd = metrics.get("perf_ytd", 0) or 0
    vol = metrics.get("vol_30d", 20) or 20
    
    # Estimation Sharpe
    rf_rate = 4.5
    excess_return = perf_ytd - rf_rate
    sharpe_estimate = excess_return / vol if vol > 0 else 0
    
    backtest = {
        "generated_at": datetime.now().isoformat(),
        "type": "estimated",
        "note": "Backtest estimé (pas de clé API ou erreur). Relancer avec --with-backtest pour données réelles.",
        "period": {
            "start": "N/A",
            "end": datetime.now().strftime("%Y-%m-%d")
        },
        "portfolio": {
            "return_pct": perf_3m,
            "return_ytd_pct": perf_ytd,
            "volatility_pct": vol,
            "sharpe_estimate": round(sharpe_estimate, 2),
            "max_drawdown_estimate": round(-vol * 1.5, 1),
            "positions": len(positions)
        },
        "benchmarks": {
            "SPY": {"note": "Données non disponibles"},
            "CAC": {"note": "Données non disponibles"}
        },
        "validation": {
            "valid": None,
            "message": "Validation impossible sans données benchmark"
        },
        "top_performers": [
            {"symbol": p.get("symbol"), "perf_ytd": p.get("perf_ytd")}
            for p in sorted(positions, key=lambda x: x.get("perf_ytd") or -999, reverse=True)[:5]
        ],
        "worst_performers": [
            {"symbol": p.get("symbol"), "perf_ytd": p.get("perf_ytd")}
            for p in sorted(positions, key=lambda x: x.get("perf_ytd") or 999)[:5]
        ]
    }
    
    backtest_path = output_dir / "backtest.json"
    with open(backtest_path, "w") as f:
        json.dump(backtest, f, indent=2)
    
    print("   ✓ backtest.json (estimated)")
    return {"report": backtest, "validation": None}


def main():
    args = parse_args()
    
    # Déterminer le mode (CLI > env var > config > default)
    mode = args.mode or os.getenv("ENRICHMENT_MODE", "smart_money")
    
    # Définir top_n selon le mode si non spécifié
    if args.top_n is None:
        top_n = 500 if mode == "sp500" else 40
    else:
        top_n = args.top_n
    
    # Set env var pour que engine_base.py le voie
    os.environ["ENRICHMENT_MODE"] = mode
    
    print("="*60)
    print("🚀 SmartMoney Portfolio Generator")
    print("="*60)
    
    # Import engine selon version
    if args.engine == "v23":
        try:
            from src.engine_v23 import SmartMoneyEngineV23 as Engine
            print("📊 Engine: v2.3 (Buffett-Style)")
            print("   Poids: value=30%, quality=25%, risk=15%, signals=30%")
        except ImportError as e:
            print(f"❌ Erreur import v2.3: {e}")
            return 1
    else:
        try:
            from src.engine_v22 import SmartMoneyEngineV22 as Engine
            print("📊 Engine: v2.2 (Legacy Smart Money)")
            print("   Poids: smart_money=45%, momentum=25%, insider=15%, quality=15%")
        except ImportError:
            from src.engine import SmartMoneyEngine as Engine
            print("📊 Engine: v2.2 (Legacy - engine.py)")
    
    mode_emoji = "🌐" if mode == "sp500" else "🎯"
    print(f"   {mode_emoji} Mode: {mode.upper()} ({top_n} tickers)")
    print(f"   📁 Mode: {'DRY-RUN' if args.dry_run else 'PRODUCTION'}")
    print("="*60)
    
    engine = Engine()
    
    print("\n📂 Étape 1/6: Chargement des données...")
    engine.load_data(mode=mode)
    
    print(f"\n📊 Étape 2/6: Enrichissement ({top_n} tickers)...")
    engine.enrich(top_n=top_n)
    
    print(f"\n🧹 Étape 3/6: Nettoyage univers...")
    engine.clean_universe(strict=args.strict)
    
    if args.engine == "v23":
        print("\n🔍 Étape 4/6: Filtres v2.3...")
        engine.apply_filters_v23(verbose=args.verbose)
        
        print("\n📈 Étape 5/6: Scoring v2.3...")
        engine.calculate_scores_v23()
        engine.apply_filters()
    else:
        print("\n📈 Étape 4/6: Scoring v2.2...")
        engine.calculate_scores()
        
        print("\n🔍 Étape 5/6: Filtres v2.2...")
        engine.apply_filters()
    
    print("\n⚙️ Étape 6/6: Optimisation HRP...")
    engine.optimize()
    
    print("\n" + "="*60)
    print("📊 RÉSUMÉ PORTEFEUILLE")
    print("="*60)
    for k, v in engine.summary().items():
        print(f"  {k}: {v}")
    
    if args.engine == "v23" and hasattr(engine, 'get_top_buffett'):
        print("\n🏆 TOP 10 BUFFETT SCORE")
        print(engine.get_top_buffett(10).to_string())
    
    backtest_result = None
    
    if not args.dry_run:
        try:
            from config import OUTPUTS
            output_dir = Path(args.output_dir) if args.output_dir else OUTPUTS / datetime.now().strftime("%Y-%m-%d")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Export principal (portfolio.json, portfolio.csv)
            portfolio_data = engine.export(output_dir)
            print(f"\n✅ Portfolio exporté vers: {output_dir}")
            
            # Extras (dashboard, memo Buffett, alerts)
            if not args.skip_extras:
                print("\n📦 Génération des extras...")
                generate_extras(portfolio_data, output_dir, args.engine.replace("v", ""))
            
            # BACKTEST RÉEL
            if not args.skip_backtest:
                backtest_result = run_real_backtest(
                    portfolio_data, 
                    output_dir, 
                    days=args.backtest_days
                )
            
        except ImportError:
            print("⚠️ Config OUTPUTS non trouvé")
    
    # Résumé final
    print("\n" + "="*60)
    print("✅ TERMINÉ — Fichiers générés:")
    print("="*60)
    print("   • portfolio.json / portfolio.csv")
    print("   • dashboard.html")
    print("   • memo.md (Buffett style)")
    print("   • alerts.json")
    print("   • backtest.json (vs SPY & CAC40)")
    
    # Verdict backtest
    if backtest_result and backtest_result.get("validation"):
        validation = backtest_result["validation"]
        print("\n" + "-"*60)
        if validation.get("valid"):
            print("🎯 VALIDATION: ✅ Portefeuille bat les benchmarks!")
        else:
            print("🎯 VALIDATION: ⚠️ Portefeuille sous-performe")
            print("   → Recommandation: Revoir la stratégie de sélection")
    
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
