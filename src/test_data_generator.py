"""
Test scraper simple pour vérifier que le pipeline fonctionne.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger

from src.config import RAW_HF_DIR, RAW_DTR_DIR
from src.utils.io import save_df

def test_hedgefollow():
    """Crée des données de test pour HedgeFollow."""
    logger.info("Creating test HedgeFollow data...")
    
    # Données fictives mais réalistes
    test_funds = pd.DataFrame({
        'fund_id': ['bridgewater', 'renaissance', 'citadel'],
        'name': ['Bridgewater Associates', 'Renaissance Technologies', 'Citadel'],
        'aum_usd': [150_000_000_000, 130_000_000_000, 65_000_000_000],
        'perf_3y': [12.5, 25.3, 18.7],
        'num_holdings': [250, 180, 320],
        'source': 'HEDGEFOLLOW_TEST'
    })
    
    test_holdings = pd.DataFrame({
        'fund_id': ['bridgewater'] * 5 + ['renaissance'] * 5,
        'fund_name': ['Bridgewater Associates'] * 5 + ['Renaissance Technologies'] * 5,
        'ticker': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'JPM', 'V'],
        'company_name': ['Apple Inc', 'Microsoft Corp', 'Alphabet Inc', 'Amazon.com Inc', 'Nvidia Corp',
                        'Meta Platforms', 'Tesla Inc', 'Berkshire Hathaway', 'JPMorgan Chase', 'Visa Inc'],
        'weight_in_fund': [5.2, 4.8, 4.5, 3.9, 3.5, 3.2, 2.8, 2.5, 2.3, 2.1],
        'value_usd': [7_800_000_000, 7_200_000_000, 6_750_000_000, 5_850_000_000, 5_250_000_000,
                     4_160_000_000, 3_640_000_000, 3_250_000_000, 2_990_000_000, 2_730_000_000],
        'source': 'HEDGEFOLLOW_TEST'
    })
    
    # Sauvegarder
    save_df(test_funds, RAW_HF_DIR / "funds_top.csv")
    save_df(test_holdings, RAW_HF_DIR / f"holdings_{datetime.now().strftime('%Y%m%d')}.csv")
    
    logger.info(f"Created test data: {len(test_funds)} funds, {len(test_holdings)} holdings")
    return True

def test_dataroma():
    """Crée des données de test pour Dataroma."""
    logger.info("Creating test Dataroma data...")
    
    # Données fictives mais réalistes
    test_managers = pd.DataFrame({
        'manager_id': ['buffett', 'klarman', 'loeb'],
        'name': ['Warren Buffett', 'Seth Klarman', 'Daniel Loeb'],
        'portfolio_value_usd': [350_000_000_000, 30_000_000_000, 18_000_000_000],
        'num_positions': [45, 35, 52],
        'source': 'DATAROMA_TEST'
    })
    
    test_grand = pd.DataFrame({
        'ticker': ['AAPL', 'BAC', 'KO', 'CVX', 'AXP'],
        'company_name': ['Apple Inc', 'Bank of America', 'Coca-Cola', 'Chevron', 'American Express'],
        'num_investors': [12, 10, 9, 8, 7],
        'total_value_usd': [45_000_000_000, 38_000_000_000, 25_000_000_000, 22_000_000_000, 18_000_000_000],
        'avg_weight': [8.5, 7.2, 6.8, 5.9, 5.2],
        'source': 'DATAROMA_GRAND_TEST'
    })
    
    # Sauvegarder
    save_df(test_managers, RAW_DTR_DIR / "managers.csv")
    save_df(test_grand, RAW_DTR_DIR / f"grand_portfolio_{datetime.now().strftime('%Y%m%d')}.csv")
    
    logger.info(f"Created test data: {len(test_managers)} managers, {len(test_grand)} grand portfolio stocks")
    return True

if __name__ == "__main__":
    # Créer les données de test
    print("\n=== Creating Test Data ===\n")
    
    success_hf = test_hedgefollow()
    success_dtr = test_dataroma()
    
    if success_hf and success_dtr:
        print("\n✅ Test data created successfully!")
        print(f"Check data/raw/hedgefollow/ and data/raw/dataroma/")
    else:
        print("\n❌ Failed to create test data")
