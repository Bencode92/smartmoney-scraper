"""
Scraper pour récupérer les holdings des hedge funds depuis HedgeFollow.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from src.config import (
    HEDGEFOLLOW_BASE_URL,
    RAW_HF_DIR,
    HEDGEFOLLOW_TOP_N_FUNDS
)
from src.utils.http import fetch_html
from src.utils.parsing import (
    make_soup,
    extract_table_data,
    normalize_ticker,
    parse_float,
    parse_int,
    clean_text
)
from src.utils.io import save_df, get_dated_filename, merge_dataframes
from src.hedgefollow.funds import get_top_n_funds


def fetch_fund_holdings(fund_id: str, fund_url: str = "") -> pd.DataFrame:
    """
    Récupère les holdings d'un fond spécifique.
    
    Args:
        fund_id: Identifiant du fond
        fund_url: URL de la page du fond (optionnel)
        
    Returns:
        DataFrame avec les holdings du fond
    """
    logger.info(f"Fetching holdings for fund: {fund_id}")
    
    # Construire l'URL si non fournie
    if not fund_url:
        # Essayer plusieurs patterns d'URL possibles
        fund_url = f"{HEDGEFOLLOW_BASE_URL}/fund.php?fund={fund_id}"
    
    try:
        html = fetch_html(fund_url)
    except Exception as e:
        logger.error(f"Failed to fetch holdings for {fund_id}: {e}")
        return pd.DataFrame()
    
    soup = make_soup(html)
    
    # Extraire le nom du fond et la date du rapport
    fund_name = fund_id  # Par défaut
    report_date = datetime.now().strftime("%Y-%m-%d")
    
    # Chercher le nom du fond dans la page
    fund_title = soup.find("h1") or soup.find("h2")
    if fund_title:
        fund_name = clean_text(fund_title.text)
    
    # Chercher la date du rapport (souvent mentionnée comme "As of" ou "Report Date")
    date_patterns = ["as of", "report date", "filed", "date"]
    for text in soup.stripped_strings:
        text_lower = text.lower()
        for pattern in date_patterns:
            if pattern in text_lower:
                # Extraire la date du texte
                # TODO: Parser la date plus intelligemment
                logger.debug(f"Found potential date text: {text}")
                break
    
    # Trouver le tableau des holdings
    holdings_data = []
    tables = soup.find_all("table")
    
    for table in tables:
        # Chercher un tableau qui ressemble à des holdings
        headers = [h.text.strip().lower() for h in table.find_all("th")]
        
        # Vérifier si c'est un tableau de holdings
        if any("stock" in h or "ticker" in h or "symbol" in h for h in headers):
            logger.debug("Found holdings table")
            
            rows = table.find_all("tr")[1:]  # Skip header
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:  # Au minimum : ticker, name, weight/value
                    
                    # Extraire le ticker et nom
                    ticker_cell = cols[0]
                    ticker_link = ticker_cell.find("a")
                    
                    if ticker_link:
                        ticker_text = ticker_link.text
                    else:
                        ticker_text = ticker_cell.text
                    
                    # Parfois ticker et nom sont dans la même cellule
                    parts = ticker_text.split("-", 1)
                    if len(parts) == 2:
                        ticker = normalize_ticker(parts[0])
                        company_name = clean_text(parts[1])
                    else:
                        ticker = normalize_ticker(ticker_text)
                        company_name = clean_text(cols[1].text) if len(cols) > 1 else ""
                    
                    holding = {
                        "fund_id": fund_id,
                        "fund_name": fund_name,
                        "ticker": ticker,
                        "company_name": company_name,
                        "sector": clean_text(cols[2].text) if len(cols) > 2 else "",
                        "report_date": report_date,
                        "weight_in_fund": parse_float(cols[3].text) if len(cols) > 3 else None,
                        "value_usd": parse_float(cols[4].text) if len(cols) > 4 else None,
                        "shares": parse_int(cols[5].text) if len(cols) > 5 else None,
                        "price": parse_float(cols[6].text) if len(cols) > 6 else None,
                        "source": "HEDGEFOLLOW",
                        "scraped_at": datetime.now().isoformat()
                    }
                    
                    holdings_data.append(holding)
            
            break  # On a trouvé le tableau des holdings
    
    if not holdings_data:
        # Fallback : essayer d'extraire depuis n'importe quel tableau
        logger.warning(f"Could not find specific holdings table for {fund_id}")
        if tables:
            table_data = extract_table_data(tables[0])
            for row in table_data:
                ticker = normalize_ticker(
                    row.get("Ticker", row.get("Symbol", row.get("Stock", "")))
                )
                if ticker:
                    holdings_data.append({
                        "fund_id": fund_id,
                        "fund_name": fund_name,
                        "ticker": ticker,
                        "company_name": clean_text(row.get("Company", row.get("Name", ""))),
                        "sector": clean_text(row.get("Sector", "")),
                        "report_date": report_date,
                        "weight_in_fund": parse_float(row.get("Weight", row.get("%", ""))),
                        "value_usd": parse_float(row.get("Value", row.get("Market Value", ""))),
                        "shares": parse_int(row.get("Shares", row.get("Quantity", ""))),
                        "price": parse_float(row.get("Price", "")),
                        "source": "HEDGEFOLLOW",
                        "scraped_at": datetime.now().isoformat()
                    })
    
    df = pd.DataFrame(holdings_data)
    
    if not df.empty:
        logger.info(f"Extracted {len(df)} holdings for {fund_id}")
    else:
        logger.warning(f"No holdings found for {fund_id}")
    
    return df


def scrape_all_top_funds_holdings() -> pd.DataFrame:
    """
    Récupère les holdings de tous les top fonds.
    
    Returns:
        DataFrame avec tous les holdings concaténés
    """
    logger.info("Starting to scrape holdings for all top funds")
    
    # Récupérer la liste des top fonds
    top_funds = get_top_n_funds()
    
    if top_funds.empty:
        logger.error("No top funds available")
        return pd.DataFrame()
    
    logger.info(f"Will scrape holdings for {len(top_funds)} funds")
    
    # Récupérer les holdings pour chaque fond
    all_holdings = []
    
    for _, fund in top_funds.iterrows():
        fund_id = fund["fund_id"]
        fund_url = fund.get("fund_url", "")
        
        holdings_df = fetch_fund_holdings(fund_id, fund_url)
        
        if not holdings_df.empty:
            all_holdings.append(holdings_df)
        
        # Petit délai entre les fonds pour éviter de surcharger le serveur
        # (déjà géré dans fetch_html)
    
    # Combiner tous les holdings
    if all_holdings:
        combined_df = merge_dataframes(*all_holdings)
        logger.info(f"Total holdings scraped: {len(combined_df)}")
        return combined_df
    else:
        logger.warning("No holdings data collected")
        return pd.DataFrame()


if __name__ == "__main__":
    # Exécution directe : scraper tous les holdings des top fonds
    df = scrape_all_top_funds_holdings()
    
    if not df.empty:
        # Sauvegarder avec la date
        filename = get_dated_filename("holdings")
        output_path = RAW_HF_DIR / filename
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} total holdings")
        print(f"Unique tickers: {df['ticker'].nunique()}")
        print(f"Unique funds: {df['fund_id'].nunique()}")
        
        # Top 10 positions par valeur
        if "value_usd" in df.columns:
            top_holdings = df.nlargest(10, "value_usd", keep="first")
            print("\nTop 10 holdings by value:")
            print(top_holdings[["fund_name", "ticker", "company_name", "value_usd"]])
    else:
        print("No holdings data scraped")