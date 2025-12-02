#!/usr/bin/env python3
"""SmartMoney Portfolio Generator

Usage:
    python main.py --engine v23      # Buffett-style (default)
    python main.py --engine v22      # Legacy smart-money dominant
    python main.py --engine v23 --top-n 50 --dry-run
    python main.py --engine v23 --with-backtest
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def parse_args():
    parser = argparse.ArgumentParser(description="SmartMoney Portfolio Generator")
    parser.add_argument("--engine", choices=["v22", "v23"], default="v23")
    parser.add_argument("--top-n", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--skip-extras", action="store_true", help="Skip dashboard, memo, alerts")
    parser.add_argument("--with-backtest", action="store_true", help="Run backtest (requires price data)")
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
        # Fallback basique
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
        
        # FCF négatif (si disponible)
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


def run_backtest(portfolio_data: dict, output_dir: Path, engine_version: str):
    """Lance le backtest walk-forward."""
    print("\n📈 Backtest walk-forward...")
    
    try:
        from src.backtest import run_simple_backtest
        
        # Extraire les symboles du portefeuille
        positions = portfolio_data.get("portfolio", [])
        symbols = [p.get("symbol") for p in positions if p.get("symbol")]
        weights = {p.get("symbol"): p.get("weight", 0) for p in positions}
        
        if not symbols:
            print("   ⚠️ Pas de symboles pour le backtest")
            return
        
        # Lancer le backtest
        results = run_simple_backtest(
            symbols=symbols,
            weights=weights,
            lookback_days=252,
            benchmark="SPY"
        )
        
        # Sauvegarder les résultats
        backtest_path = output_dir / "backtest.json"
        with open(backtest_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"   ✓ backtest.json")
        
        # Afficher résumé
        if results:
            print(f"\n   📊 Résultats Backtest (1 an):")
            print(f"      Return: {results.get('total_return', 'N/A')}%")
            print(f"      Sharpe: {results.get('sharpe_ratio', 'N/A')}")
            print(f"      Max DD: {results.get('max_drawdown', 'N/A')}%")
            print(f"      vs SPY: {results.get('alpha_vs_spy', 'N/A')}%")
        
    except ImportError as e:
        print(f"   ⚠️ Module backtest non disponible: {e}")
        # Générer un backtest placeholder
        generate_backtest_placeholder(portfolio_data, output_dir)
    except Exception as e:
        print(f"   ⚠️ Erreur backtest: {e}")
        generate_backtest_placeholder(portfolio_data, output_dir)


def generate_backtest_placeholder(portfolio_data: dict, output_dir: Path):
    """Génère un placeholder backtest basé sur les perfs historiques."""
    positions = portfolio_data.get("portfolio", [])
    metrics = portfolio_data.get("metrics", {})
    
    # Calculer des métriques approximatives
    perf_3m = metrics.get("perf_3m", 0) or 0
    perf_ytd = metrics.get("perf_ytd", 0) or 0
    vol = metrics.get("vol_30d", 20) or 20
    
    # Estimation Sharpe (simplifié)
    rf_rate = 4.5  # Taux sans risque
    excess_return = perf_ytd - rf_rate
    sharpe_estimate = excess_return / vol if vol > 0 else 0
    
    backtest = {
        "generated_at": datetime.now().isoformat(),
        "type": "estimated",
        "note": "Backtest estimé basé sur les métriques actuelles (pas de données historiques complètes)",
        "period": {
            "start": "N/A",
            "end": datetime.now().strftime("%Y-%m-%d")
        },
        "metrics": {
            "total_return_ytd": perf_ytd,
            "return_3m": perf_3m,
            "volatility_annualized": vol,
            "sharpe_ratio_estimate": round(sharpe_estimate, 2),
            "max_drawdown_estimate": round(-vol * 1.5, 1),  # Rule of thumb
        },
        "positions_count": len(positions),
        "top_performers": [
            {
                "symbol": p.get("symbol"),
                "perf_ytd": p.get("perf_ytd")
            }
            for p in sorted(positions, key=lambda x: x.get("perf_ytd") or -999, reverse=True)[:5]
        ],
        "worst_performers": [
            {
                "symbol": p.get("symbol"),
                "perf_ytd": p.get("perf_ytd")
            }
            for p in sorted(positions, key=lambda x: x.get("perf_ytd") or 999)[:5]
        ]
    }
    
    backtest_path = output_dir / "backtest.json"
    with open(backtest_path, "w") as f:
        json.dump(backtest, f, indent=2)
    
    print("   ✓ backtest.json (estimated)")


def main():
    args = parse_args()
    
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
    
    print(f"   Top-N: {args.top_n} tickers")
    print(f"   Mode: {'DRY-RUN' if args.dry_run else 'PRODUCTION'}")
    print("="*60)
    
    engine = Engine()
    
    print("\n📂 Étape 1/6: Chargement des données...")
    engine.load_data()
    
    print(f"\n📊 Étape 2/6: Enrichissement ({args.top_n} tickers)...")
    engine.enrich(top_n=args.top_n)
    
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
    print("📊 RÉSUMÉ")
    print("="*60)
    for k, v in engine.summary().items():
        print(f"  {k}: {v}")
    
    if args.engine == "v23" and hasattr(engine, 'get_top_buffett'):
        print("\n🏆 TOP 10 BUFFETT SCORE")
        print(engine.get_top_buffett(10).to_string())
    
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
            
            # Backtest (optionnel ou par défaut)
            if args.with_backtest or not args.skip_extras:
                run_backtest(portfolio_data, output_dir, args.engine.replace("v", ""))
            
        except ImportError:
            print("⚠️ Config OUTPUTS non trouvé")
    
    print("\n" + "="*60)
    print("✅ TERMINÉ — Fichiers générés:")
    print("   • portfolio.json / portfolio.csv")
    print("   • dashboard.html")
    print("   • memo.md (Buffett style)")
    print("   • alerts.json")
    print("   • backtest.json")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
