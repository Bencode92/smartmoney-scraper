#!/usr/bin/env python3
"""SmartMoney Portfolio Generator

Usage:
    python main.py --engine v23      # Buffett-style (default)
    python main.py --engine v22      # Legacy smart-money dominant
    python main.py --engine v23 --top-n 50 --dry-run
"""
import argparse
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
    return parser.parse_args()


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
            engine.export(output_dir)
            print(f"\n✅ Exporté vers: {output_dir}")
        except ImportError:
            print("⚠️ Config OUTPUTS non trouvé")
    
    print("\n✅ TERMINÉ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
