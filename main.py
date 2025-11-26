"""SmartMoney Engine - Point d'entrée principal"""
import sys
from pathlib import Path

from config import OUTPUTS, TWELVE_DATA_KEY, OPENAI_KEY
from src.engine import SmartMoneyEngine
from src.copilot import Copilot
from src.dashboard import generate_dashboard


def main():
    print("="*60)
    print("🚀 SMARTMONEY ENGINE")
    print("="*60)
    
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
    print("PHASE 5: Export")
    print("-"*60)
    portfolio = engine.export(OUTPUTS)
    
    # === DASHBOARD HTML ===
    print("\n" + "-"*60)
    print("PHASE 6: Dashboard HTML")
    print("-"*60)
    generate_dashboard(portfolio, OUTPUTS)
    
    # === COPILOT ===
    if OPENAI_KEY:
        print("\n" + "-"*60)
        print("PHASE 7: IA Copilot")
        print("-"*60)
        try:
            copilot = Copilot()
            copilot.export_memo(portfolio, OUTPUTS)
            copilot.export_alerts(portfolio, OUTPUTS)
        except Exception as e:
            print(f"⚠️ Erreur Copilot: {e}")
    else:
        print("\n⏭️ Copilot skipped (pas de clé API)")
    
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
    
    print(f"\n📁 Outputs: {OUTPUTS}")
    
    # Affiche le top 10
    print("\n🏆 TOP 10 POSITIONS:")
    for i, pos in enumerate(portfolio.get("portfolio", [])[:10], 1):
        symbol = pos.get("symbol", "?")
        weight = pos.get("weight", 0) * 100
        score = pos.get("score_composite", 0)
        sector = pos.get("sector", "?")
        print(f"  {i:2}. {symbol:6} {weight:5.2f}%  (score: {score:.3f}) [{sector}]")
    
    # Répartition sectorielle
    if metrics.get("sector_weights"):
        print("\n🏢 RÉPARTITION SECTORIELLE:")
        for sector, weight in sorted(metrics["sector_weights"].items(), key=lambda x: -x[1]):
            print(f"   {sector}: {weight}%")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
