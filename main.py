"""SmartMoney Engine - Point d'entrée principal"""
import sys
from datetime import datetime
from pathlib import Path

from config import OUTPUTS, TWELVE_DATA_KEY, OPENAI_KEY
from src.engine import SmartMoneyEngine
from src.copilot import Copilot
from src.dashboard import generate_dashboard


def main():
    print("="*60)
    print("🚀 SMARTMONEY ENGINE v2.0")
    print("   Scoring + Fondamentaux + HRP + Backtest")
    print("="*60)
    
    # === CRÉER LE DOSSIER DATÉ ===
    today = datetime.now().strftime("%Y-%m-%d")
    dated_dir = OUTPUTS / today
    dated_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Dossier de sortie: {dated_dir}")
    
    # === VÉRIFICATIONS ===
    if not TWELVE_DATA_KEY:
        print("⚠️ API_TWELVEDATA non configurée - enrichissement désactivé")
    if not OPENAI_KEY:
        print("⚠️ API_OPENAI non configurée - copilot désactivé")
    
    # === ENGINE ===
    print("\n" + "-"*60)
    print("PHASE 1: Chargement des données")
    print("-"*60)
    engine = SmartMoneyEngine()
    engine.load_data()
    
    print("\n" + "-"*60)
    print("PHASE 2: Enrichissement Twelve Data")
    print("   (Quote, Profile, RSI, TimeSeries, Statistics,")
    print("    Balance Sheet, Income Statement, Cash Flow)")
    print("-"*60)
    if TWELVE_DATA_KEY:
        engine.enrich(top_n=40)
    else:
        print("⏭️ Skipped (pas de clé API)")
    
    print("\n" + "-"*60)
    print("PHASE 3: Scoring")
    print("-"*60)
    engine.calculate_scores()
    engine.apply_filters()
    
    print("\n" + "-"*60)
    print("PHASE 4: Optimisation HRP")
    print("-"*60)
    engine.optimize()
    
    print("\n" + "-"*60)
    print("PHASE 5: Export Portfolio")
    print("-"*60)
    portfolio = engine.export(dated_dir)  # Passe le dossier daté
    
    # === DASHBOARD HTML ===
    print("\n" + "-"*60)
    print("PHASE 6: Dashboard HTML")
    print("-"*60)
    generate_dashboard(portfolio, dated_dir)  # Passe le dossier daté
    
    # === BACKTEST ===
    print("\n" + "-"*60)
    print("PHASE 7: Backtest & Benchmark (SPY + CAC40)")
    print("-"*60)
    if TWELVE_DATA_KEY:
        try:
            from src.backtest import Backtester
            backtester = Backtester()
            backtester.generate_report(portfolio.get("portfolio", []), dated_dir)  # Passe le dossier daté
        except Exception as e:
            print(f"⚠️ Erreur Backtest: {e}")
    else:
        print("⏭️ Skipped (pas de clé API)")
    
    # === COPILOT ===
    if OPENAI_KEY:
        print("\n" + "-"*60)
        print("PHASE 8: IA Copilot")
        print("-"*60)
        try:
            copilot = Copilot()
            copilot.export_memo(portfolio, dated_dir)    # Passe le dossier daté
            copilot.export_alerts(portfolio, dated_dir)  # Passe le dossier daté
        except Exception as e:
            print(f"⚠️ Erreur Copilot: {e}")
    else:
        print("\n⏭️ Copilot skipped (pas de clé API)")
    
    # === CRÉER LE SYMLINK latest ===
    latest_link = OUTPUTS / "latest"
    try:
        if latest_link.is_symlink():
            latest_link.unlink()
        elif latest_link.exists():
            import shutil
            shutil.rmtree(latest_link)
        latest_link.symlink_to(dated_dir.name, target_is_directory=True)
        print(f"\n🔗 Symlink créé: latest → {dated_dir.name}")
    except Exception as e:
        print(f"⚠️ Impossible de créer le symlink: {e}")
    
    # === RÉSUMÉ ===
    print("\n" + "="*60)
    print("✅ TERMINÉ")
    print("="*60)
    
    metrics = engine.portfolio_metrics
    print(f"\n📊 MÉTRIQUES PORTEFEUILLE:")
    print(f"   Positions: {metrics.get('positions', 0)}")
    print(f"   Perf 3M: {metrics.get('perf_3m', 'N/A')}%")
    print(f"   Perf YTD: {metrics.get('perf_ytd', 'N/A')}%")
    print(f"   Vol 30j: {metrics.get('vol_30d', 'N/A')}%")
    print(f"   ROE moyen: {metrics.get('avg_roe', 'N/A')}%")
    print(f"   D/E moyen: {metrics.get('avg_debt_equity', 'N/A')}")
    print(f"   Marge nette moy: {metrics.get('avg_net_margin', 'N/A')}%")
    
    # Liste des fichiers générés
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
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
