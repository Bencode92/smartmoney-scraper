"""
Scraper pour le Grand Portfolio de Dataroma (agrégat de tous les superinvestors).
"""
import pandas as pd
from datetime import datetime
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
from src.utils.io import save_df, get_dated_filename


# URL du Grand Portfolio
DATAROMA_GRAND_PORTFOLIO_URL = f"{DATAROMA_BASE_URL}/grandportfolio.php"


def scrape_grand_portfolio() -> pd.DataFrame:
    """
    Récupère le Grand Portfolio de Dataroma.
    
    Returns:
        DataFrame avec les données agrégées
    """
    logger.info("Scraping Dataroma Grand Portfolio...")
    
    try:
        html = fetch_html(DATAROMA_GRAND_PORTFOLIO_URL)
    except Exception as e:
        logger.error(f"Failed to fetch Grand Portfolio: {e}")
        return pd.DataFrame()
    
    soup = make_soup(html)
    
    portfolio_data = []
    
    # Trouver le tableau principal
    tables = soup.find_all("table")
    
    for table in tables:
        rows = table.find_all("tr")
        
        if len(rows) > 10:  # Le Grand Portfolio a généralement beaucoup de lignes
            logger.debug("Found potential Grand Portfolio table")
            
            # Analyser les headers
            if rows:
                header_row = rows[0]
                headers = [clean_text(th.text).lower() for th in header_row.find_all(["th", "td"])]
                
                # Parcourir les lignes de données
                for row in rows[1:]:
                    cols = row.find_all("td")
                    
                    if len(cols) >= 3:  # Minimum: stock, num investors, value
                        
                        # Première colonne : stock
                        stock_cell = cols[0]
                        stock_link = stock_cell.find("a")
                        
                        if stock_link:
                            stock_text = stock_link.text
                        else:
                            stock_text = stock_cell.text
                        
                        stock_text = clean_text(stock_text)
                        
                        # Parser ticker et nom
                        ticker = ""
                        company_name = stock_text
                        
                        # Essayer différents formats
                        if " - " in stock_text:
                            parts = stock_text.split(" - ", 1)
                            ticker = normalize_ticker(parts[0])
                            company_name = parts[1] if len(parts) > 1 else stock_text
                        elif stock_text:
                            words = stock_text.split()
                            if words and words[0].isupper() and len(words[0]) <= 5:
                                ticker = normalize_ticker(words[0])
                                company_name = " ".join(words[1:]) if len(words) > 1 else stock_text
                        
                        # Extraire les métriques
                        num_investors = parse_int(cols[1].text) if len(cols) > 1 else None
                        total_value = parse_float(cols[2].text) if len(cols) > 2 else None
                        avg_weight = parse_float(cols[3].text) if len(cols) > 3 else None
                        
                        # Parfois il y a des colonnes supplémentaires comme le changement
                        change_pct = parse_float(cols[4].text) if len(cols) > 4 else None
                        
                        if ticker or company_name:
                            item = {
                                "ticker": ticker,
                                "company_name": company_name,
                                "num_investors": num_investors,
                                "total_value_usd": total_value,
                                "avg_weight": avg_weight,
                                "change_pct": change_pct,
                                "source": "DATAROMA_GRAND",
                                "scraped_at": datetime.now().isoformat()
                            }
                            
                            portfolio_data.append(item)
            
            if portfolio_data:  # Si on a trouvé des données, arrêter
                break
    
    df = pd.DataFrame(portfolio_data)
    
    if df.empty:
        logger.error("No Grand Portfolio data extracted")
        return df
    
    # Trier par nombre d'investisseurs
    if "num_investors" in df.columns:
        df = df.sort_values("num_investors", ascending=False)
    
    logger.info(f"Scraped {len(df)} stocks from Grand Portfolio")
    
    return df


def get_consensus_picks(min_investors: int = 5) -> pd.DataFrame:
    """
    Obtient les picks avec le plus de consensus (détenus par plusieurs superinvestors).
    
    Args:
        min_investors: Nombre minimum d'investisseurs
        
    Returns:
        DataFrame filtré
    """
    df = scrape_grand_portfolio()
    
    if df.empty:
        return df
    
    # Filtrer par nombre minimum d'investisseurs
    if "num_investors" in df.columns:
        df = df[df["num_investors"] >= min_investors]
    
    logger.info(f"Found {len(df)} consensus picks (>={min_investors} investors)")
    
    return df


if __name__ == "__main__":
    # Exécution directe : scraper le Grand Portfolio
    df = scrape_grand_portfolio()
    
    if not df.empty:
        # Sauvegarder avec la date
        filename = get_dated_filename("grand_portfolio")
        output_path = RAW_DTR_DIR / filename
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} stocks from Grand Portfolio")
        
        # Top 10 par nombre d'investisseurs
        print("\nTop 10 stocks by number of investors:")
        print(df[["ticker", "company_name", "num_investors", "total_value_usd"]].head(10))
        
        # Consensus picks
        consensus = get_consensus_picks(min_investors=7)
        if not consensus.empty:
            print(f"\n{len(consensus)} strong consensus picks (>=7 investors):")
            print(consensus[["ticker", "company_name", "num_investors", "avg_weight"]].head(10))
    else:
        print("No Grand Portfolio data scraped")