#!/usr/bin/env python3
"""SmartMoney v2.3 — Smoke Test

Test rapide pour vérifier que le pipeline v2.3 fonctionne.

Usage:
    python scripts/smoke_test_v23.py

Vérifie:
1. Configuration v2.3 valide
2. Filtres fonctionnels
3. Data validator fonctionnel
4. Intégration avec engine.py existant
"""

import sys
import os
from pathlib import Path

# Ajouter le repo au path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

import pandas as pd
import numpy as np
from datetime import datetime


def create_mock_universe(n_tickers: int = 100) -> pd.DataFrame:
    """Crée un univers fictif pour test."""
    np.random.seed(42)
    
    sectors = [
        "Technology", "Healthcare", "Financials", "Consumer Discretionary",
        "Industrials", "Energy", "Materials", "Utilities"
    ]
    
    data = []
    for i in range(n_tickers):
        is_large = np.random.random() > 0.3
        is_liquid = np.random.random() > 0.2
        is_healthy = np.random.random() > 0.2
        
        market_cap = np.random.uniform(5e9, 500e9) if is_large else np.random.uniform(100e6, 2e9)
        adv_usd = market_cap * np.random.uniform(0.001, 0.01) if is_liquid else np.random.uniform(100e3, 2e6)
        
        equity = market_cap * np.random.uniform(0.3, 0.8)
        total_debt = equity * np.random.uniform(0.1, 0.8) if is_healthy else equity * np.random.uniform(2, 5)
        ebit = market_cap * np.random.uniform(0.05, 0.15)
        interest_expense = total_debt * 0.05
        
        data.append({
            "symbol": f"TICK{i:03d}",
            "company": f"Company {i}",
            "sector": np.random.choice(sectors),
            "market_cap": market_cap,
            "adv_usd": adv_usd,
            "td_price": np.random.uniform(10, 500),
            "total_debt": total_debt,
            "equity": equity,
            "ebit": ebit,
            "interest_expense": interest_expense,
            "cash": equity * np.random.uniform(0.1, 0.3),
            "revenue": ebit * np.random.uniform(5, 10),
            "net_income": ebit * np.random.uniform(0.5, 0.9),
            "fcf": ebit * np.random.uniform(0.3, 0.8),
            "gp_buys": np.random.randint(0, 15),
            "gp_tier": np.random.choice(["A", "B", "C", "D"]),
            "insider_buys": np.random.randint(0, 5),
        })
    
    return pd.DataFrame(data)


def run_smoke_test():
    """Lance le smoke test v2.3."""
    print("=" * 70)
    print("SMARTMONEY v2.3 — SMOKE TEST")
    print("=" * 70)
    print()
    
    errors = []
    
    # === 1. CONFIG v2.3 ===
    print("1. Vérification configuration v2.3...")
    try:
        from config_v23 import WEIGHTS_V23, HARD_FILTERS, LIQUIDITY
        
        total = sum(WEIGHTS_V23.values())
        assert abs(total - 1.0) < 0.001, f"Poids = {total}"
        assert all(w >= 0 for w in WEIGHTS_V23.values()), "Poids négatifs"
        
        print(f"   ✅ Poids v2.3: {WEIGHTS_V23}")
        print(f"   ✅ Somme: {total:.3f}")
        print(f"   ✅ Hard filters: D/E<{HARD_FILTERS['max_debt_equity']}, Coverage>{HARD_FILTERS['min_interest_coverage']}")
    except Exception as e:
        errors.append(f"Config v2.3: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 2. COMPARAISON v2.2 vs v2.3 ===
    print("2. Comparaison v2.2 → v2.3...")
    try:
        from config import WEIGHTS
        from config_v23 import WEIGHTS_V23
        
        print(f"   v2.2: smart_money={WEIGHTS['smart_money']}, momentum={WEIGHTS['momentum']}")
        print(f"   v2.3: smart_money={WEIGHTS_V23['smart_money']}, momentum={WEIGHTS_V23['momentum']}")
        print(f"   v2.3 nouveaux: value={WEIGHTS_V23['value']}, quality={WEIGHTS_V23['quality']}, risk={WEIGHTS_V23['risk']}")
        print(f"   ✅ Réduction smart_money: {WEIGHTS['smart_money']} → {WEIGHTS_V23['smart_money']} (-{(1-WEIGHTS_V23['smart_money']/WEIGHTS['smart_money'])*100:.0f}%)")
    except Exception as e:
        errors.append(f"Comparaison: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 3. FILTRES LIQUIDITÉ ===
    print("3. Test filtres liquidité...")
    try:
        from src.filters.liquidity import apply_liquidity_filters
        
        universe = create_mock_universe(100)
        filtered = apply_liquidity_filters(universe, verbose=False)
        
        pct_remaining = len(filtered) / len(universe) * 100
        print(f"   ✅ {len(filtered)}/{len(universe)} tickers passent ({pct_remaining:.0f}%)")
        
        assert len(filtered) < len(universe), "Filtres n'ont rien exclu"
        assert len(filtered) > 10, "Trop de tickers exclus"
        
    except Exception as e:
        errors.append(f"Liquidité: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 4. HARD FILTERS ===
    print("4. Test hard filters...")
    try:
        from src.filters.hard_filters import apply_hard_filters
        
        filtered2 = apply_hard_filters(filtered, verbose=False)
        
        pct_remaining = len(filtered2) / len(filtered) * 100
        print(f"   ✅ {len(filtered2)}/{len(filtered)} tickers passent ({pct_remaining:.0f}%)")
        
    except Exception as e:
        errors.append(f"Hard filters: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 5. DATA VALIDATOR ===
    print("5. Test data validator...")
    try:
        from src.validation.data_validator import DataValidator
        
        validator = DataValidator()
        
        valid_row = pd.Series({
            "revenue": 100e9,
            "ebit": 20e9,
            "net_income": 15e9,
            "equity": 80e9,
            "total_debt": 30e9,
        })
        result = validator.validate_row(valid_row, "TEST")
        assert result.is_valid, "Ligne valide rejetée"
        
        invalid_row = pd.Series({
            "revenue": 100e9,
        })
        result = validator.validate_row(invalid_row, "TEST")
        assert not result.is_valid, "Ligne invalide acceptée"
        
        print(f"   ✅ Validator fonctionne correctement")
        
    except Exception as e:
        errors.append(f"Validator: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 6. LOOK-AHEAD ===
    print("6. Test look-ahead filter...")
    try:
        from src.filters.look_ahead import filter_by_publication_date, get_latest_available_year
        
        fundamentals = pd.DataFrame({
            "year": list(range(2015, 2025)),
            "revenue": [100e9 * (1.05 ** i) for i in range(10)],
        })
        
        filtered_funda = filter_by_publication_date(
            fundamentals,
            as_of_date="2024-02-01",
        )
        
        assert 2024 not in filtered_funda["year"].values
        assert 2023 not in filtered_funda["year"].values
        assert 2022 in filtered_funda["year"].values
        
        latest = get_latest_available_year("2024-04-01")
        print(f"   ✅ Look-ahead filter fonctionne")
        print(f"      Dernière année dispo au 2024-04-01: {latest}")
        
    except Exception as e:
        errors.append(f"Look-ahead: {e}")
        print(f"   ❌ Erreur: {e}")
    print()
    
    # === 7. PIPELINE COMPLET ===
    print("7. Test pipeline complet (filtres enchaînés)...")
    try:
        from src.filters.liquidity import apply_liquidity_filters
        from src.filters.hard_filters import apply_hard_filters
        from src.validation.data_validator import validate_universe
        
        universe = create_mock_universe(100)
        
        # Pipeline
        df1 = apply_liquidity_filters(universe, verbose=False)
        df2 = apply_hard_filters(df1, verbose=False)
        df3, warnings = validate_universe(df2)
        
        print(f"   Pipeline: {len(universe)} → {len(df1)} → {len(df2)} → {len(df3)}")
        print(f"   ✅ Pipeline complet fonctionne")
        print(f"      Tickers finaux: {len(df3)} ({len(df3)/len(universe)*100:.0f}% de l'univers)")
        
    except Exception as e:
        errors.append(f"Pipeline: {e}")
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
        print("✅ SMOKE TEST v2.3 RÉUSSI")
        print()
        print("Prochaines étapes:")
        print("  - Sprint 2: Scoring (value_composite, quality_composite, risk_score)")
        print("  - Sprint 3: Backtest complet 2010-2024")
        print()
        print("Pour lancer les tests pytest:")
        print("  pytest tests/test_v23_sprint1.py -v")
        return True


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
