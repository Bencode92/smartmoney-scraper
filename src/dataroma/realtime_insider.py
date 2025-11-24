"""
Scraper pour le Real-Time Insider Trading de Dataroma.
"""
import pandas as pd
from datetime import datetime
from loguru import logger

from src.config import (
    DATAROMA_BASE_URL,
    RAW_DTR_DIR,
    INSIDER_MIN_VALUE_USD
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


# URL du Real-Time Insider
DATAROMA_RT_INSIDER_URL = f"{DATAROMA_BASE_URL}/insider.php"


def scrape_realtime_insiders() -> pd.DataFrame:
    """
    Récupère les trades insiders récents depuis Dataroma.
    
    Returns:
        DataFrame avec les trades insiders
    """
    logger.info("Scraping Dataroma Real-Time Insider trades...")
    
    try:
        html = fetch_html(DATAROMA_RT_INSIDER_URL)
    except Exception as e:
        logger.error(f"Failed to fetch Dataroma insiders: {e}")
        return pd.DataFrame()
    
    soup = make_soup(html)
    
    trades_data = []
    
    # Trouver le tableau des trades
    tables = soup.find_all("table")
    
    for table in tables:
        rows = table.find_all("tr")
        
        # Vérifier si c'est le bon tableau
        if len(rows) > 1:
            # Analyser les headers pour identifier le tableau
            header_row = rows[0] if rows else None
            if header_row:
                headers = [clean_text(th.text).lower() for th in header_row.find_all(["th", "td"])]
                
                # Vérifier si c'est un tableau d'insiders
                is_insider_table = any(
                    "insider" in h or "filed" in h or "transaction" in h 
                    for h in headers
                )
                
                if is_insider_table or len(rows) > 5:  # Heuristique
                    logger.debug("Found insider trades table")
                    
                    # Parcourir les lignes de données
                    for row in rows[1:]:
                        cols = row.find_all("td")
                        
                        if len(cols) >= 4:  # Minimum: date, stock, insider, value
                            
                            # Extraire les données selon la structure typique
                            # Col 0: Date
                            date_text = clean_text(cols[0].text)
                            
                            # Col 1: Stock
                            stock_cell = cols[1]
                            stock_link = stock_cell.find("a")
                            
                            if stock_link:
                                stock_text = stock_link.text
                            else:
                                stock_text = stock_cell.text
                            
                            stock_text = clean_text(stock_text)
                            
                            # Parser ticker et nom
                            ticker = ""
                            company_name = stock_text
                            
                            if " - " in stock_text:
                                parts = stock_text.split(" - ", 1)
                                ticker = normalize_ticker(parts[0])
                                company_name = parts[1] if len(parts) > 1 else stock_text
                            elif stock_text:
                                words = stock_text.split()
                                if words and words[0].isupper() and len(words[0]) <= 5:
                                    ticker = normalize_ticker(words[0])
                                    company_name = " ".join(words[1:]) if len(words) > 1 else stock_text
                            
                            # Col 2: Insider name/role
                            insider_text = clean_text(cols[2].text) if len(cols) > 2 else ""
                            insider_name = insider_text
                            role = ""
                            
                            # Essayer de séparer nom et rôle
                            if "(" in insider_text and ")" in insider_text:
                                name_part = insider_text.split("(")[0].strip()
                                role_part = insider_text.split("(")[1].split(")")[0].strip()
                                insider_name = name_part
                                role = role_part
                            
                            # Col 3: Transaction type
                            transaction_type = clean_text(cols[3].text) if len(cols) > 3 else "Unknown"
                            if "buy" in transaction_type.lower() or "purchase" in transaction_type.lower():
                                transaction_type = "Buy"
                            elif "sell" in transaction_type.lower() or "sale" in transaction_type.lower():
                                transaction_type = "Sell"
                            
                            # Col 4: Value
                            value_text = cols[4].text if len(cols) > 4 else "0"
                            transaction_value = parse_float(value_text)
                            
                            # Col 5: Shares
                            shares = parse_int(cols[5].text) if len(cols) > 5 else None
                            
                            # Col 6: Price
                            price = parse_float(cols[6].text) if len(cols) > 6 else None
                            
                            # Ajouter le trade si la valeur est suffisante
                            if not transaction_value or transaction_value >= INSIDER_MIN_VALUE_USD:
                                trade = {
                                    "ticker": ticker,
                                    "company_name": company_name,
                                    "insider_name": insider_name,
                                    "role": role,
                                    "transaction_type": transaction_type,
                                    "transaction_value_usd": transaction_value,
                                    "shares": shares,
                                    "price": price,
                                    "trade_date": date_text,
                                    "filed_date": date_text,  # Dataroma ne distingue pas toujours
                                    "source": "DATAROMA_RT_INSIDER",
                                    "scraped_at": datetime.now().isoformat()
                                }
                                
                                trades_data.append(trade)
                    
                    break  # On a trouvé le tableau
    
    df = pd.DataFrame(trades_data)
    
    if not df.empty:
        logger.info(f"Extracted {len(df)} insider trades from Dataroma")
        
        # Calculer les stats
        if "transaction_type" in df.columns:
            buys = df[df["transaction_type"] == "Buy"]
            sells = df[df["transaction_type"] == "Sell"]
            logger.info(f"Buys: {len(buys)}, Sells: {len(sells)}")
    else:
        logger.warning("No insider trades found")
    
    return df


def get_significant_insider_activity() -> pd.DataFrame:
    """
    Filtre pour obtenir uniquement l'activité insider significative.
    
    Returns:
        DataFrame avec les trades significatifs
    """
    df = scrape_realtime_insiders()
    
    if df.empty:
        return df
    
    # Filtrer par valeur minimum (déjà fait dans scrape_realtime_insiders)
    
    # Grouper par ticker pour voir l'activité nette
    if "ticker" in df.columns and "transaction_value_usd" in df.columns:
        activity = df.groupby("ticker").agg({
            "transaction_value_usd": "sum",
            "transaction_type": lambda x: "Net Buy" if x.value_counts().index[0] == "Buy" else "Net Sell",
            "company_name": "first"
        }).reset_index()
        
        # Trier par valeur absolue de l'activité
        activity["abs_value"] = activity["transaction_value_usd"].abs()
        activity = activity.sort_values("abs_value", ascending=False)
        
        logger.info(f"Found {len(activity)} tickers with insider activity")
        
        return activity
    
    return df


if __name__ == "__main__":
    # Exécution directe : scraper les trades insiders
    df = scrape_realtime_insiders()
    
    if not df.empty:
        # Sauvegarder avec la date
        filename = get_dated_filename("realtime_insider")
        output_path = RAW_DTR_DIR / filename
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} insider trades from Dataroma")
        print(f"Unique tickers: {df['ticker'].nunique()}")
        
        # Top 10 par valeur
        if "transaction_value_usd" in df.columns:
            print("\nTop 10 trades by value:")
            top_trades = df.nlargest(10, "transaction_value_usd")
            print(top_trades[["ticker", "company_name", "insider_name", "transaction_type", "transaction_value_usd"]])
        
        # Activité significative
        significant = get_significant_insider_activity()
        if not significant.empty:
            print("\nTop 10 tickers by insider activity:")
            print(significant.head(10))
    else:
        print("No insider trades scraped")