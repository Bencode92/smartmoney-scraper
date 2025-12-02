#!/usr/bin/env python3
"""SmartMoney Portfolio Generator

Usage:
    python main.py --engine v23      # Buffett-style (default)
    python main.py --engine v22      # Legacy smart-money dominant
    python main.py --engine v23 --top-n 50 --dry-run
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
    return parser.parse_args()


def generate_extras(portfolio_data: dict, output_dir: Path, engine_version: str):
    """Génère dashboard, memo et alerts."""
    
    # 1. Dashboard HTML
    try:
        from src.dashboard import generate_dashboard
        generate_dashboard(portfolio_data, output_dir)
        print("   ✓ dashboard.html")
    except Exception as e:
        print(f"   ⚠️ Dashboard: {e}")
    
    # 2. Memo markdown
    try:
        from src.memo import generate_memo
        generate_memo(portfolio_data, output_dir)
        print("   ✓ memo.md")
    except ImportError:
        # Générer un memo basique si le module n'existe pas
        try:
            generate_basic_memo(portfolio_data, output_dir, engine_version)
            print("   ✓ memo.md (basic)")
        except Exception as e:
            print(f"   ⚠️ Memo: {e}")
    except Exception as e:
        print(f"   ⚠️ Memo: {e}")
    
    # 3. Alerts JSON
    try:
        from src.alerts import generate_alerts
        generate_alerts(portfolio_data, output_dir)
        print("   ✓ alerts.json")
    except ImportError:
        # Générer des alertes basiques si le module n'existe pas
        try:
            generate_basic_alerts(portfolio_data, output_dir)
            print("   ✓ alerts.json (basic)")
        except Exception as e:
            print(f"   ⚠️ Alerts: {e}")
    except Exception as e:
        print(f"   ⚠️ Alerts: {e}")


def generate_basic_memo(portfolio_data: dict, output_dir: Path, engine_version: str):
    """Génère un memo markdown basique."""
    metrics = portfolio_data.get("metrics", {})
    positions = portfolio_data.get("portfolio", [])
    date_str = portfolio_data.get("metadata", {}).get("date", datetime.now().strftime("%Y-%m-%d"))
    
    # Top 5 positions
    top5 = sorted(positions, key=lambda x: x.get("weight", 0), reverse=True)[:5]
    top5_str = "\n".join([
        f"| {p.get('symbol', 'N/A')} | {p.get('sector', 'N/A')[:15]} | {p.get('weight', 0)*100:.1f}% | {p.get('score_composite', 0):.3f} |"
        for p in top5
    ])
    
    # Secteurs
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
| ROE moyen | {metrics.get('avg_roe', 'N/A')}% |
| D/E moyen | {metrics.get('avg_debt_equity', 'N/A')} |

## Top 5 Positions

| Ticker | Secteur | Poids | Score |
|--------|---------|-------|-------|
{top5_str}

## Répartition Sectorielle

{sectors_str}

## Notes

- Généré automatiquement par SmartMoney Engine v{engine_version}
- Date: {datetime.now().isoformat()}
"""
    
    memo_path = output_dir / "memo.md"
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo)


def generate_basic_alerts(portfolio_data: dict, output_dir: Path):
    """Génère des alertes basiques."""
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
                "message": f"RSI survente ({rsi:.0f})",
                "severity": "medium"
            })
        elif rsi and rsi > 70:
            alerts.append({
                "type": "warning",
                "ticker": symbol,
                "message": f"RSI surachat ({rsi:.0f})",
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
                "message": f"Forte baisse YTD ({perf_ytd:.0f}%)",
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
    
    alerts_data = {
        "generated_at": datetime.now().isoformat(),
        "count": len(alerts),
        "alerts": alerts
    }
    
    alerts_path = output_dir / "alerts.json"
    with open(alerts_path, "w", encoding="utf-8") as f:
        json.dump(alerts_data, f, indent=2)


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
            
            # Extras (dashboard, memo, alerts)
            if not args.skip_extras:
                print("\n📦 Génération des extras...")
                generate_extras(portfolio_data, output_dir, args.engine.replace("v", ""))
            
        except ImportError:
            print("⚠️ Config OUTPUTS non trouvé")
    
    print("\n✅ TERMINÉ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
