"""SmartMoney Engine - Point d'entrée principal"""
import sys
from pathlib import Path

from config import OUTPUTS, TWELVE_DATA_KEY, OPENAI_KEY
from src.engine import SmartMoneyEngine
from src.copilot import Copilot


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
    
    # === COPILOT ===
    if OPENAI_KEY:
        print("\n" + "-"*60)
        print("PHASE 6: IA Copilot")
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
    print(f"📁 Outputs: {OUTPUTS}")
    
    # Affiche le top 10
    print("\n🏆 TOP 10 POSITIONS:")
    for i, pos in enumerate(portfolio.get("portfolio", [])[:10], 1):
        symbol = pos.get("symbol", "?")
        weight = pos.get("weight", 0) * 100
        score = pos.get("score_composite", 0)
        print(f"  {i:2}. {symbol:6} {weight:5.2f}%  (score: {score:.3f})")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
