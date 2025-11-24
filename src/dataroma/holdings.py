"""
Scraper pour récupérer les holdings des superinvestors depuis Dataroma.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from src.config import (
    DATAROMA_BASE_URL,
    RAW_DTR_DIR
)
from src.utils.http import fetch_html
from src.utils.parsing import (
    make_soup,
    normalize_ticker,
    parse_float,
    parse_int,
    clean_text
)
from src.utils.io import save_df, get_dated_filename, merge_dataframes
from src.dataroma.managers import get_top_n_managers


def fetch_manager_holdings(manager_id: str, manager_url: str = "") -> pd.DataFrame:
    """
    Récupère les holdings d'un superinvestor spécifique.
    
    Args:
        manager_id: Identifiant du manager
        manager_url: URL de la page du manager
        
    Returns:
        DataFrame avec les holdings du manager
    """
    logger.info(f"Fetching holdings for manager: {manager_id}")
    
    # Construire l'URL si non fournie
    if not manager_url:
        # Pattern typique : portfolio.php?manager=XXX
        manager_url = f"{DATAROMA_BASE_URL}/portfolio.php?manager={manager_id}"
    
    try:
        html = fetch_html(manager_url)
    except Exception as e:
        logger.error(f"Failed to fetch holdings for {manager_id}: {e}")
        return pd.DataFrame()
    
    soup = make_soup(html)
    
    # Extraire le nom du manager et la date du rapport
    manager_name = manager_id  # Par défaut
    report_date = datetime.now().strftime("%Y-%m-%d")
    
    # Chercher le nom dans la page
    title = soup.find("h1") or soup.find("h2") or soup.find("title")
    if title:
        manager_name = clean_text(title.text)
    
    # Chercher la date du rapport ("Quarter ending", "As of", etc.)
    for text in soup.stripped_strings:
        text_lower = text.lower()
        if "quarter" in text_lower or "as of" in text_lower:
            logger.debug(f"Found potential date text: {text}")
            # TODO: Parser la date proprement
            break
    
    # Trouver le tableau des holdings
    holdings_data = []
    tables = soup.find_all("table")
    
    for table in tables:
        rows = table.find_all("tr")
        
        # Vérifier si c'est un tableau de holdings
        if len(rows) > 1:
            # Analyser la première ligne pour identifier les colonnes
            header_row = rows[0]
            headers = [clean_text(th.text).lower() for th in header_row.find_all(["th", "td"])]
            
            # Vérifier si c'est un tableau de holdings
            has_stock_col = any("stock" in h or "company" in h or "ticker" in h for h in headers)
            has_value_col = any("value" in h or "weight" in h or "%" in h for h in headers)
            
            if has_stock_col or (len(rows) > 10 and len(headers) >= 3):  # Heuristique
                logger.debug("Found holdings table")
                
                # Parcourir les lignes de données
                for row in rows[1:]:
                    cols = row.find_all("td")
                    
                    if len(cols) >= 2:  # Minimum: stock, weight/value
                        
                        # Première colonne : généralement le stock
                        stock_cell = cols[0]
                        stock_link = stock_cell.find("a")
                        
                        if stock_link:
                            stock_text = stock_link.text
                        else:
                            stock_text = stock_cell.text
                        
                        # Parser ticker et nom
                        # Dataroma peut avoir différents formats
                        stock_text = clean_text(stock_text)
                        
                        # Essayer de séparer ticker et nom
                        ticker = ""
                        company_name = stock_text
                        
                        # Si le format est "TICKER - Company Name"
                        if " - " in stock_text:
                            parts = stock_text.split(" - ", 1)
                            ticker = normalize_ticker(parts[0])
                            company_name = parts[1] if len(parts) > 1 else stock_text
                        # Si le format est "TICKER Company Name" (ticker en majuscules)
                        elif stock_text:
                            words = stock_text.split()
                            if words and words[0].isupper():
                                ticker = normalize_ticker(words[0])
                                company_name = " ".join(words[1:]) if len(words) > 1 else stock_text
                            else:
                                # Pas de ticker clair, utiliser tout comme nom
                                company_name = stock_text
                        
                        # Extraire les autres colonnes
                        weight = parse_float(cols[1].text) if len(cols) > 1 else None
                        value = parse_float(cols[2].text) if len(cols) > 2 else None
                        shares = parse_int(cols[3].text) if len(cols) > 3 else None
                        
                        if ticker or company_name:  # Au moins l'un des deux
                            holding = {
                                "manager_id": manager_id,
                                "manager_name": manager_name,
                                "ticker": ticker,
                                "company_name": company_name,
                                "sector": "",  # Dataroma ne fournit pas toujours le secteur
                                "report_date": report_date,
                                "weight_in_portfolio": weight,
                                "value_usd": value,
                                "shares": shares,
                                "source": "DATAROMA",
                                "scraped_at": datetime.now().isoformat()
                            }
                            
                            holdings_data.append(holding)
                
                break  # On a trouvé le tableau
    
    df = pd.DataFrame(holdings_data)
    
    if not df.empty:
        logger.info(f"Extracted {len(df)} holdings for {manager_id}")
    else:
        logger.warning(f"No holdings found for {manager_id}")
    
    return df


def scrape_all_top_managers_holdings() -> pd.DataFrame:
    """
    Récupère les holdings de tous les top managers.
    
    Returns:
        DataFrame avec tous les holdings concaténés
    """
    logger.info("Starting to scrape holdings for all top managers")
    
    # Récupérer la liste des top managers
    top_managers = get_top_n_managers()
    
    if top_managers.empty:
        logger.error("No top managers available")
        return pd.DataFrame()
    
    logger.info(f"Will scrape holdings for {len(top_managers)} managers")
    
    # Récupérer les holdings pour chaque manager
    all_holdings = []
    
    for _, manager in top_managers.iterrows():
        manager_id = manager["manager_id"]
        manager_url = manager.get("manager_url", "")
        
        holdings_df = fetch_manager_holdings(manager_id, manager_url)
        
        if not holdings_df.empty:
            all_holdings.append(holdings_df)
    
    # Combiner tous les holdings
    if all_holdings:
        combined_df = merge_dataframes(*all_holdings)
        logger.info(f"Total holdings scraped: {len(combined_df)}")
        return combined_df
    else:
        logger.warning("No holdings data collected")
        return pd.DataFrame()


if __name__ == "__main__":
    # Exécution directe : scraper tous les holdings des top managers
    df = scrape_all_top_managers_holdings()
    
    if not df.empty:
        # Sauvegarder avec la date
        filename = get_dated_filename("holdings")
        output_path = RAW_DTR_DIR / filename
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} total holdings")
        print(f"Unique tickers: {df['ticker'].nunique()}")
        print(f"Unique managers: {df['manager_id'].nunique()}")
        
        # Top 10 positions par poids
        if "weight_in_portfolio" in df.columns:
            top_holdings = df.nlargest(10, "weight_in_portfolio")
            print("\nTop 10 holdings by weight:")
            print(top_holdings[["manager_name", "ticker", "company_name", "weight_in_portfolio"]])
    else:
        print("No holdings data scraped")