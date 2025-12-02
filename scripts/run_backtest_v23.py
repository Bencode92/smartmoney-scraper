#!/usr/bin/env python3
"""SmartMoney v2.3 — Run Backtest

Lance un backtest complet avec la stratégie v2.3.

Usage:
    python scripts/run_backtest_v23.py [--start 2010-01-01] [--end 2024-12-31]

Prérequis:
    - Fichier de prix: data/prices.parquet ou data/prices.csv
    - Fichier de fondamentaux: data/fundamentals.parquet ou data/fundamentals.csv
    - Optionnel: data/spy.parquet pour le benchmark

Date: Décembre 2025
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

import pandas as pd
import numpy as np


def setup_logging():
    """Configure le logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def load_data(data_dir: Path):
    """Charge les données nécessaires."""
    # Prix
    prices_path = data_dir / "prices.parquet"
    if not prices_path.exists():
        prices_path = data_dir / "prices.csv"
    
    if prices_path.exists():
        if prices_path.suffix == ".parquet":
            prices = pd.read_parquet(prices_path)
        else:
            prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)
        logging.info(f"Prix chargés: {prices.shape}")
    else:
        logging.warning("Fichier de prix non trouvé, génération de données synthétiques")
        prices = generate_synthetic_prices()
    
    # Fondamentaux
    funda_path = data_dir / "fundamentals.parquet"
    if not funda_path.exists():
        funda_path = data_dir / "fundamentals.csv"
    
    if funda_path.exists():
        if funda_path.suffix == ".parquet":
            fundamentals = pd.read_parquet(funda_path)
        else:
            fundamentals = pd.read_csv(funda_path)
        logging.info(f"Fondamentaux chargés: {fundamentals.shape}")
    else:
        logging.warning("Fichier de fondamentaux non trouvé, génération de données synthétiques")
        fundamentals = generate_synthetic_fundamentals(prices.columns.tolist())
    
    # Benchmark
    spy_path = data_dir / "spy.parquet"
    if not spy_path.exists():
        spy_path = data_dir / "spy.csv"
    
    if spy_path.exists():
        if spy_path.suffix == ".parquet":
            benchmark = pd.read_parquet(spy_path).squeeze()
        else:
            benchmark = pd.read_csv(spy_path, index_col=0, parse_dates=True).squeeze()
        logging.info(f"Benchmark chargé: {len(benchmark)} jours")
    else:
        benchmark = None
        logging.warning("Benchmark non trouvé")
    
    return prices, fundamentals, benchmark


def generate_synthetic_prices(n_symbols: int = 50, n_years: int = 15) -> pd.DataFrame:
    """Génère des prix synthétiques pour les tests."""
    np.random.seed(42)
    
    dates = pd.date_range(
        start="2010-01-01",
        end="2024-12-31",
        freq="B"
    )
    
    symbols = [f"TICK{i:03d}" for i in range(n_symbols)]
    
    # Générer des prix avec différents profils
    data = {}
    for sym in symbols:
        drift = np.random.uniform(0.0002, 0.0008)  # 5-20% CAGR
        vol = np.random.uniform(0.015, 0.035)      # 24-55% vol
        
        returns = np.random.normal(drift, vol, len(dates))
        prices = 100 * np.exp(np.cumsum(returns))
        
        data[sym] = prices
    
    return pd.DataFrame(data, index=dates)


def generate_synthetic_fundamentals(symbols: list) -> pd.DataFrame:
    """Génère des fondamentaux synthétiques."""
    np.random.seed(42)
    
    sectors = ["Technology", "Healthcare", "Financials", "Industrials", "Consumer"]
    years = list(range(2010, 2025))
    
    data = []
    for sym in symbols:
        sector = np.random.choice(sectors)
        base_revenue = np.random.uniform(1e9, 100e9)
        
        for year in years:
            growth = np.random.uniform(0.95, 1.15)
            revenue = base_revenue * growth ** (year - 2010)
            
            ebit_margin = np.random.uniform(0.08, 0.25)
            ebit = revenue * ebit_margin
            
            data.append({
                "symbol": sym,
                "year": year,
                "sector": sector,
                "revenue": revenue,
                "ebit": ebit,
                "net_income": ebit * np.random.uniform(0.6, 0.85),
                "fcf": ebit * np.random.uniform(0.4, 0.9),
                "total_debt": revenue * np.random.uniform(0.1, 0.5),
                "equity": revenue * np.random.uniform(0.3, 0.8),
                "cash": revenue * np.random.uniform(0.05, 0.2),
                "interest_expense": revenue * np.random.uniform(0.01, 0.03),
                "shares_outstanding": np.random.uniform(100e6, 5e9),
            })
    
    return pd.DataFrame(data)


def main():
    parser = argparse.ArgumentParser(description="Run SmartMoney v2.3 Backtest")
    parser.add_argument("--start", default="2010-01-01", help="Start date")
    parser.add_argument("--end", default="2024-12-31", help="End date")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    parser.add_argument("--no-stress", action="store_true", help="Skip stress tests")
    
    args = parser.parse_args()
    
    setup_logging()
    
    logging.info("=" * 60)
    logging.info("SMARTMONEY v2.3 — BACKTEST")
    logging.info("=" * 60)
    logging.info(f"Période: {args.start} → {args.end}")
    
    # Charger les données
    data_dir = Path(args.data_dir)
    prices, fundamentals, benchmark = load_data(data_dir)
    
    # Import du backtest engine
    from src.backtest.backtest_v23 import BacktestEngine
    from src.backtest.reports import generate_report
    
    # Créer le moteur
    engine = BacktestEngine(
        rebal_freq="Q",
        tc_bps=12.0,
    )
    
    # Lancer le backtest
    logging.info("\nLancement du backtest...")
    
    try:
        result = engine.run(
            prices=prices,
            fundamentals=fundamentals,
            start_date=args.start,
            end_date=args.end,
            benchmark=benchmark,
            run_stress_tests=not args.no_stress,
        )
        
        # Générer les rapports
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Rapport texte
        text_report = generate_report(result, format="text")
        text_path = output_dir / f"backtest_report_{timestamp}.txt"
        text_path.write_text(text_report)
        logging.info(f"\nRapport texte: {text_path}")
        
        # Rapport JSON
        json_report = generate_report(result, format="json")
        json_path = output_dir / f"backtest_report_{timestamp}.json"
        json_path.write_text(json_report)
        logging.info(f"Rapport JSON: {json_path}")
        
        # Rapport HTML
        html_report = generate_report(result, format="html")
        html_path = output_dir / f"backtest_report_{timestamp}.html"
        html_path.write_text(html_report)
        logging.info(f"Rapport HTML: {html_path}")
        
        # Sauvegarder les rendements
        returns_path = output_dir / f"returns_{timestamp}.csv"
        result.returns.to_csv(returns_path)
        logging.info(f"Rendements: {returns_path}")
        
        # Afficher le résumé
        print("\n" + text_report)
        
        # Statut final
        if result.validation_passed:
            logging.info("\n\u2705 BACKTEST RÉUSSI")
            return 0
        else:
            logging.warning("\n\u26a0\ufe0f BACKTEST TERMINÉ AVEC AVERTISSEMENTS")
            return 1
            
    except Exception as e:
        logging.error(f"\n\u274c ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
