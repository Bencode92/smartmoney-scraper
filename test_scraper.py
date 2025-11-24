#!/usr/bin/env python
"""
Quick test script to verify the scraper is working.
Run with: python test_scraper.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")
    try:
        import requests
        import bs4
        import pandas as pd
        from loguru import logger
        print("✅ All dependencies installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False
    
    try:
        from src.config import HEDGEFOLLOW_BASE_URL, DATAROMA_BASE_URL
        from src.utils.http import fetch_html
        from src.utils.parsing import normalize_ticker
        print("✅ All modules importable")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_connection():
    """Test connection to target sites."""
    print("\n🌐 Testing connections...")
    
    from src.utils.http import fetch_html
    from src.config import HEDGEFOLLOW_BASE_URL, DATAROMA_BASE_URL
    
    # Test HedgeFollow
    try:
        print(f"Connecting to {HEDGEFOLLOW_BASE_URL}...")
        html = fetch_html(HEDGEFOLLOW_BASE_URL)
        if html and len(html) > 100:
            print(f"✅ HedgeFollow reachable ({len(html)} bytes)")
        else:
            print("⚠️ HedgeFollow returned empty response")
    except Exception as e:
        print(f"❌ HedgeFollow error: {e}")
    
    # Test Dataroma
    try:
        print(f"Connecting to {DATAROMA_BASE_URL}...")
        html = fetch_html(f"{DATAROMA_BASE_URL}/home.php")
        if html and len(html) > 100:
            print(f"✅ Dataroma reachable ({len(html)} bytes)")
        else:
            print("⚠️ Dataroma returned empty response")
    except Exception as e:
        print(f"❌ Dataroma error: {e}")

def test_scraper_module():
    """Test a simple scraper function."""
    print("\n🤖 Testing scraper functionality...")
    
    try:
        from src.hedgefollow.funds import scrape_top_funds
        print("Attempting to scrape top hedge funds...")
        
        df = scrape_top_funds()
        
        if not df.empty:
            print(f"✅ Successfully scraped {len(df)} hedge funds!")
            print(f"   Columns: {', '.join(df.columns)}")
            print(f"   Top fund: {df.iloc[0]['name'] if 'name' in df.columns else 'N/A'}")
            return True
        else:
            print("⚠️ Scraper returned empty dataframe")
            print("   This might be normal if the HTML structure has changed")
            return False
            
    except Exception as e:
        print(f"❌ Scraper error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("🚀 SmartMoney Scraper Test Suite")
    print("=" * 50)
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Fix import issues before continuing")
        return 1
    
    # Test 2: Connections
    test_connection()
    
    # Test 3: Scraper
    test_scraper_module()
    
    print("\n" + "=" * 50)
    print("📊 Test complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Run individual scrapers: python -m src.hedgefollow.funds")
    print("2. Run full pipeline: bash scripts/run_pipeline.sh")
    print("3. Or trigger GitHub Action from the Actions tab")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
