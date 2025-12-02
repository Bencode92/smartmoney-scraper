#!/usr/bin/env python3
"""SmartMoney v2.3 — Smoke Test Sprint 2 (Scoring)

Test complet du pipeline de scoring v2.3.

Usage:
    python scripts/smoke_test_v23_scoring.py

"""

import sys
import os
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_universe(n_tickers: int = 50) -> pd.DataFrame:
    """Crée un univers de test réaliste."""
    np.random.seed(42)
    
    sectors = [
        "Technology", "Healthcare", "Financials", 
        "Consumer Discretionary", "Industrials"
    ]
    
    data = []
    for i in range(n_tickers):
        # Profil aléatoire
        is_quality = np.random.random() > 0.5
        is_value = np.random.random() > 0.5
        is_safe = np.random.random() > 0.3
        
        market_cap = np.random.uniform(5e9, 500e9)
        equity = market_cap * np.random.uniform(0.3, 0.8)
        
        if is_safe:
            de_ratio = np.random.uniform(0.1, 0.8)
        else:
            de_ratio = np.random.uniform(1.5, 4)
        
        total_debt = equity * de_ratio
        cash = equity * np.random.uniform(0.1, 0.4)
        
        if is_quality:
            ebit_margin = np.random.uniform(0.15, 0.30)
            fcf_margin = np.random.uniform(0.10, 0.20)
        else:
            ebit_margin = np.random.uniform(0.05, 0.15)
            fcf_margin = np.random.uniform(-0.05, 0.10)
        
        revenue = market_cap * np.random.uniform(0.3, 0.8)
        ebit = revenue * ebit_margin
        fcf = revenue * fcf_margin
        net_income = ebit * np.random.uniform(0.6, 0.85)
        
        if is_value:
            pe = np.random.uniform(8, 15)
        else:
            pe = np.random.uniform(20, 40)
        
        interest_expense = total_debt * np.random.uniform(0.03, 0.07)
        vol = np.random.uniform(15, 50) if is_safe else np.random.uniform(40, 70)
        
        data.append({
            "symbol": f"TICK{i:03d}",
            "company": f"Company {i}",
            "sector": np.random.choice(sectors),
            "market_cap": market_cap,
            "revenue": revenue,
            "ebit": ebit,
            "net_income": net_income,
            "fcf": fcf,
            "total_debt": total_debt,
            "equity": equity,
            "cash": cash,
            "interest_expense": interest_expense,
            "pe_ratio": pe,
            "vol_30d": vol,
            # Scores v2.2 simulés
            "score_sm": np.random.uniform(0.3, 0.9),
            "score_insider": np.random.uniform(0.2, 0.8),
            "score_momentum": np.random.uniform(0.3, 0.7),
        })
    
    return pd.DataFrame(data)


def run_scoring_smoke_test():
    """Lance le smoke test du scoring v2.3."""
    print("=" * 70)
    print("SMARTMONEY v2.3 — SMOKE TEST SCORING (Sprint 2)")
    print("=" * 70)
    print()
    
    errors = []
    
    # === 1. VALUE SCORER ===
    print("1. Test Value Scorer...")
    try:
        from src.scoring.value_composite import ValueScorer, score_value
        
        universe = create_test_universe(50)
        df = score_value(universe)
        
        assert "score_value" in df.columns
        assert df["score_value"].between(0, 1).all()
        
        print(f"   ✅ Value: mean={df['score_value'].mean():.3f}, std={df['score_value'].std():.3f}")
        print(f"      Top 3: {df.nlargest(3, 'score_value')[['symbol', 'score_value']].values.tolist()}")
        
    except Exception as e:
        errors.append(f"Value Scorer: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 2. QUALITY SCORER ===
    print("2. Test Quality Scorer...")
    try:
        from src.scoring.quality_composite import QualityScorer, score_quality
        
        df = score_quality(df)
        
        assert "score_quality" in df.columns
        assert df["score_quality"].between(0, 1).all()
        
        print(f"   ✅ Quality: mean={df['score_quality'].mean():.3f}, std={df['score_quality'].std():.3f}")
        print(f"      Top 3: {df.nlargest(3, 'score_quality')[['symbol', 'score_quality']].values.tolist()}")
        
    except Exception as e:
        errors.append(f"Quality Scorer: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 3. RISK SCORER (INVERSÉ) ===
    print("3. Test Risk Scorer (inversé: score élevé = sûr)...")
    try:
        from src.scoring.risk_score import RiskScorer, score_risk
        
        df = score_risk(df)
        
        assert "score_risk" in df.columns
        assert df["score_risk"].between(0, 1).all()
        
        print(f"   ✅ Risk: mean={df['score_risk'].mean():.3f}, std={df['score_risk'].std():.3f}")
        print(f"      Top 3 (les plus sûrs): {df.nlargest(3, 'score_risk')[['symbol', 'score_risk']].values.tolist()}")
        
    except Exception as e:
        errors.append(f"Risk Scorer: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 4. COMPOSITE SCORER ===
    print("4. Test Composite Scorer...")
    try:
        from src.scoring.composite import CompositeScorer, calculate_composite_score
        
        df = calculate_composite_score(df)
        
        assert "score_composite" in df.columns
        assert "buffett_score" in df.columns
        
        print(f"   ✅ Composite: mean={df['score_composite'].mean():.3f}")
        print(f"   ✅ Buffett:   mean={df['buffett_score'].mean():.3f}")
        
    except Exception as e:
        errors.append(f"Composite Scorer: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 5. PIPELINE COMPLET ===
    print("5. Test Pipeline Complet (calculate_all_scores)...")
    try:
        from src.scoring.composite import calculate_all_scores
        
        universe2 = create_test_universe(30)
        df2 = calculate_all_scores(universe2)
        
        expected_cols = [
            "score_value", "score_quality", "score_risk",
            "score_composite", "buffett_score", "rank_composite"
        ]
        
        for col in expected_cols:
            assert col in df2.columns, f"Colonne {col} manquante"
        
        print(f"   ✅ Pipeline complet fonctionne")
        print(f"      Colonnes ajoutées: {expected_cols}")
        
    except Exception as e:
        errors.append(f"Pipeline complet: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 6. COMPARAISON SCORES ===
    print("6. Analyse des corrélations entre scores...")
    try:
        corr_matrix = df[["score_value", "score_quality", "score_risk", 
                          "score_sm", "score_composite", "buffett_score"]].corr()
        
        print("   Corrélations avec score_composite:")
        for col in ["score_value", "score_quality", "score_risk", "score_sm"]:
            print(f"      - {col}: {corr_matrix.loc[col, 'score_composite']:.2f}")
        
        print(f"\n   Corrélation composite vs buffett: {corr_matrix.loc['score_composite', 'buffett_score']:.2f}")
        
    except Exception as e:
        errors.append(f"Analyse corrélations: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 7. TOP HOLDINGS ===
    print("7. Top 10 Holdings (par score composite)...")
    try:
        from src.scoring.composite import CompositeScorer
        
        scorer = CompositeScorer()
        top10 = scorer.get_top_holdings(df, n=10)
        
        print("   Rank | Symbol | Composite | Buffett | Value | Quality | Risk")
        print("   " + "-" * 60)
        for i, row in top10.iterrows():
            print(
                f"   {i+1:4} | {row['symbol']:6} | "
                f"{row['score_composite']:9.3f} | "
                f"{row['buffett_score']:7.3f} | "
                f"{row['score_value']:5.3f} | "
                f"{row['score_quality']:7.3f} | "
                f"{row['score_risk']:4.3f}"
            )
        
    except Exception as e:
        errors.append(f"Top Holdings: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === RÉSUMÉ ===
    print("=" * 70)
    if errors:
        print(f"❌ SMOKE TEST ÉCHOUÉ — {len(errors)} erreur(s):")
        for e in errors:
            print(f"   - {e}")
        return False
    else:
        print("✅ SMOKE TEST SCORING v2.3 RÉUSSI")
        print()
        print("Récapitulatif des poids v2.3:")
        print("  smart_money: 15% (était 45%)")
        print("  insider:     10% (était 15%)")
        print("  momentum:     5% (était 25%)")
        print("  value:       30% (NOUVEAU)")
        print("  quality:     25% (NOUVEAU)")
        print("  risk:        15% (NOUVEAU, inversé)")
        print()
        print("Prochaines étapes:")
        print("  - Sprint 3: Backtest 2010-2024")
        print("  - Intégration dans engine.py")
        print()
        print("Pour lancer les tests pytest:")
        print("  pytest tests/test_v23_sprint2.py -v")
        return True


if __name__ == "__main__":
    success = run_scoring_smoke_test()
    sys.exit(0 if success else 1)
