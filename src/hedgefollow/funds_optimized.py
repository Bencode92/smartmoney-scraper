"""
Scraper optimisé pour récupérer les top hedge funds HedgeFollow.
Paramétrable via variables d'environnement.
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from loguru import logger

from src.config import HEDGEFOLLOW_BASE_URL, RAW_HF_DIR
from src.utils.http import fetch_html
from src.utils.parsing import make_soup, parse_float, parse_int, slugify, clean_text
from src.utils.io import save_df

# Configuration from environment
RUN_ID = os.getenv("RUN_ID", datetime.now().strftime("%Y%m%d"))
HF_TOP_FUNDS = int(os.getenv("HF_TOP_FUNDS", "20"))
HF_MIN_AUM_BILLIONS = float(os.getenv("HF_MIN_AUM_BILLIONS", "1.0"))

HEDGEFOLLOW_FUNDS_URL = f"{HEDGEFOLLOW_BASE_URL}/funds.php"

def extract_fund_from_row(row) -> Optional[Dict[str, Any]]:
    """Extract fund data from table row."""
    try:
        cols = row.find_all(["td", "th"])
        if len(cols) < 3:
            return None
        
        # Extract name and URL
        fund_link = cols[0].find("a")
        if fund_link:
            fund_name = clean_text(fund_link.text)
            fund_url = fund_link.get("href", "")
            if fund_url and not fund_url.startswith("http"):
                fund_url = HEDGEFOLLOW_BASE_URL + "/" + fund_url.lstrip("/")
        else:
            fund_name = clean_text(cols[0].text)
            fund_url = ""
        
        if not fund_name:
            return None
        
        return {
            "fund_id": slugify(fund_name),
            "name": fund_name,
            "fund_url": fund_url,
            "aum_usd": parse_float(cols[1].text) if len(cols) > 1 else None,
            "perf_3y": parse_float(cols[2].text) if len(cols) > 2 else None,
            "num_holdings": parse_int(cols[3].text) if len(cols) > 3 else None,
            "run_id": RUN_ID,
            "source": "HEDGEFOLLOW",
            "scraped_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.debug(f"Row extraction failed: {e}")
        return None

def scrape_top_funds() -> pd.DataFrame:
    """Scrape top hedge funds from HedgeFollow."""
    logger.info(f"Scraping HedgeFollow (RUN_ID: {RUN_ID}, TOP: {HF_TOP_FUNDS})")
    
    try:
        html = fetch_html(HEDGEFOLLOW_FUNDS_URL)
        soup = make_soup(html)
        
        funds_data = []
        tables = soup.find_all("table")
        
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header
                fund_data = extract_fund_from_row(row)
                if fund_data:
                    funds_data.append(fund_data)
            
            if funds_data:  # Found data, stop
                break
        
        df = pd.DataFrame(funds_data)
        
        if df.empty:
            logger.warning("No funds extracted")
            return df
        
        # Filter by AUM
        if "aum_usd" in df.columns and HF_MIN_AUM_BILLIONS > 0:
            min_aum = HF_MIN_AUM_BILLIONS * 1_000_000_000
            df = df[df["aum_usd"] >= min_aum]
        
        # Sort and limit
        if "aum_usd" in df.columns:
            df = df.sort_values("aum_usd", ascending=False)
        df = df.head(HF_TOP_FUNDS)
        
        logger.info(f"Extracted {len(df)} funds")
        return df
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return pd.DataFrame()

def main():
    """Main entry point."""
    df = scrape_top_funds()
    
    if not df.empty:
        # Save with RUN_ID
        output_file = RAW_HF_DIR / f"funds_{RUN_ID}.csv"
        save_df(df, output_file)
        
        # Also save as latest
        save_df(df, RAW_HF_DIR / "funds_latest.csv")
        
        print(f"\n=== HedgeFollow Funds ===")
        print(f"Run ID: {RUN_ID}")
        print(f"Scraped: {len(df)} funds")
        print(f"Output: {output_file}")
    else:
        logger.error("No data scraped")
        sys.exit(1)

if __name__ == "__main__":
    main()