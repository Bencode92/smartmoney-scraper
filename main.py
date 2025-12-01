"""SmartMoney Engine - Point d'entrée principal"""
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

from config import OUTPUTS, TWELVE_DATA_KEY, OPENAI_KEY
from src.engine import SmartMoneyEngine
from src.copilot import Copilot
from src.dashboard import generate_dashboard


# === CONFIGURATION ===
# Si True, le pipeline échoue si le portefeuille ne bat pas les benchmarks
REQUIRE_OUTPERFORMANCE = False  # Mettre à True pour mode strict

# Si True, doit battre SPY ET CAC. Si False, un seul suffit.
STRICT_BENCHMARK = True


def main():
    print("="*60)
    print("🚀 SMARTMONEY ENGINE v2.1")
    print("   Scoring + Fondamentaux + HRP + Backtest + Validation")
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
    portfolio = engine.export(dated_dir)
    
    # === DASHBOARD HTML ===
    print("\n" + "-"*60)
    print("PHASE 6: Dashboard HTML")
    print("-"*60)
    generate_dashboard(portfolio, dated_dir)
    
    # === BACKTEST AVEC VALIDATION ===
    print("\n" + "-"*60)
    print("PHASE 7: Backtest & Validation Surperformance")
    print("-"*60)
    
    validation_result = None
    backtest_passed = True
    
    if TWELVE_DATA_KEY:
        try:
            from src.backtest import Backtester
            backtester = Backtester()
            result = backtester.generate_report(
                portfolio.get("portfolio", []), 
                dated_dir,
                validate=True,
                strict=STRICT_BENCHMARK
            )
            validation_result = result.get("validation")
            
            if validation_result:
                backtest_passed = validation_result.get("valid", True)
                
                # Affichage résumé de validation
                print("\n" + "="*60)
                if validation_result.get("beats_all"):
                    print("🏆 VALIDATION: PORTEFEUILLE BAT SPY ET CAC")
                elif validation_result.get("beats_spy"):
                    print("⚠️ VALIDATION: Bat SPY mais pas CAC")
                elif validation_result.get("beats_cac"):
                    print("⚠️ VALIDATION: Bat CAC mais pas SPY")
                else:
                    print("❌ VALIDATION: SOUS-PERFORMANCE vs BENCHMARKS")
                print("="*60)
                
                print(f"   Portefeuille 3M: {validation_result['portfolio_return']:+.2f}%")
                print(f"   SPY 3M:          {validation_result['spy_return']:+.2f}%  (Alpha: {validation_result['alpha_spy']:+.2f}%)")
                print(f"   CAC 3M:          {validation_result['cac_return']:+.2f}%  (Alpha: {validation_result['alpha_cac']:+.2f}%)")
                
        except Exception as e:
            print(f"⚠️ Erreur Backtest: {e}")
    else:
        print("⏭️ Skipped (pas de clé API)")
    
    # === COPILOT ===
    # Génère les alertes et le memo (inclut alerte sous-performance)
    alerts = []
    
    # Ajouter alerte si sous-performance
    if validation_result and not validation_result.get("beats_all"):
        severity = "high" if not validation_result.get("valid") else "medium"
        alerts.append({
            "type": "benchmark",
            "severity": severity,
            "symbol": None,
            "message": validation_result.get("message", "Portefeuille sous-performe les benchmarks"),
            "details": {
                "portfolio_return": validation_result.get("portfolio_return"),
                "spy_return": validation_result.get("spy_return"),
                "cac_return": validation_result.get("cac_return"),
                "alpha_spy": validation_result.get("alpha_spy"),
                "alpha_cac": validation_result.get("alpha_cac")
            }
        })
    
    if OPENAI_KEY:
        print("\n" + "-"*60)
        print("PHASE 8: IA Copilot")
        print("-"*60)
        try:
            copilot = Copilot()
            copilot.export_memo(portfolio, dated_dir)
            
            # Ajoute les alertes du copilot aux alertes existantes
            copilot_alerts = copilot.generate_alerts(portfolio)
            alerts.extend(copilot_alerts)
            
        except Exception as e:
            print(f"⚠️ Erreur Copilot: {e}")
    else:
        print("\n⏭️ Copilot skipped (pas de clé API)")
    
    # Export des alertes (combine backtest + copilot)
    if alerts:
        alerts_path = dated_dir / "alerts.json"
        with open(alerts_path, "w") as f:
            json.dump(alerts, f, indent=2)
        print(f"📁 {len(alerts)} alertes exportées: {alerts_path.name}")
    
    # === CHECK OUTPERFORMANCE REQUIREMENT ===
    if REQUIRE_OUTPERFORMANCE and not backtest_passed:
        print("\n" + "="*60)
        print("❌ ÉCHEC: Portefeuille ne bat pas les benchmarks")
        print("   Mode REQUIRE_OUTPERFORMANCE activé")
        print("   Le portefeuille ne sera PAS publié")
        print("="*60)
        return 1  # Exit avec erreur
    
    # === COPIER DANS outputs/latest/ (pas symlink - plus robuste) ===
    latest_dir = OUTPUTS / "latest"
    try:
        # Supprimer l'ancien dossier latest s'il existe
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        
        # Copier tous les fichiers du dossier daté vers latest
        shutil.copytree(dated_dir, latest_dir)
        print(f"\n📁 Copié vers: outputs/latest/")
    except Exception as e:
        print(f"⚠️ Erreur copie vers latest: {e}")
    
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
    
    # Statut de surperformance
    if validation_result:
        print(f"\n🎯 STATUT BENCHMARK:")
        if validation_result.get("beats_all"):
            print("   ✅ Bat SPY ET CAC sur 3M")
        else:
            print(f"   {'✅' if validation_result.get('beats_spy') else '❌'} vs SPY ({validation_result['alpha_spy']:+.2f}%)")
            print(f"   {'✅' if validation_result.get('beats_cac') else '❌'} vs CAC ({validation_result['alpha_cac']:+.2f}%)")
    
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
