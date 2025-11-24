"""
Scraper pour le tracker d'insider trading de HedgeFollow.
"""
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from loguru import logger

from src.config import (
    HEDGEFOLLOW_BASE_URL,
    RAW_HF_DIR,
    INSIDER_MIN_VALUE_USD,
    INSIDER_DAYS_BACK
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


# URL du tracker insider
HEDGEFOLLOW_INSIDER_URL = f"{HEDGEFOLLOW_BASE_URL}/insider.php"


def fetch_insider_trades(
    min_value_usd: float = INSIDER_MIN_VALUE_USD,
    days_back: int = INSIDER_DAYS_BACK
) -> pd.DataFrame:
    """
    Récupère les trades insiders récents depuis HedgeFollow.
    
    Args:
        min_value_usd: Valeur minimum du trade en USD
        days_back: Nombre de jours en arrière à chercher
        
    Returns:
        DataFrame avec les trades insiders
    """
    logger.info(f"Fetching insider trades (min ${min_value_usd:,.0f}, last {days_back} days)")
    
    # Construire l'URL avec paramètres si possible
    # Note: Il faudra peut-être ajuster selon comment HedgeFollow gère les filtres
    url = HEDGEFOLLOW_INSIDER_URL
    
    try:
        html = fetch_html(url)
    except Exception as e:
        logger.error(f"Failed to fetch insider trades: {e}")
        return pd.DataFrame()
    
    soup = make_soup(html)
    
    # Trouver le tableau des trades insiders
    trades_data = []
    tables = soup.find_all("table")
    
    for table in tables:
        # Chercher un tableau qui ressemble à des trades insiders
        headers = [h.text.strip().lower() for h in table.find_all("th")]
        
        # Vérifier si c'est le bon tableau
        if any("insider" in h or "filed" in h or "transaction" in h for h in headers):
            logger.debug("Found insider trades table")
            
            rows = table.find_all("tr")[1:]  # Skip header
            
            for row in rows:
                cols = row.find_all("td")
                
                if len(cols) >= 4:  # Minimum: date, stock, value, type
                    
                    # Extraire les données de base
                    # L'ordre des colonnes peut varier, on fait de notre mieux
                    
                    # Date Filed (première colonne généralement)
                    filed_date_text = clean_text(cols[0].text)
                    
                    # Stock/Ticker (deuxième colonne généralement)
                    stock_cell = cols[1]
                    stock_link = stock_cell.find("a")
                    
                    if stock_link:
                        stock_text = stock_link.text
                    else:
                        stock_text = stock_cell.text
                    
                    # Parser ticker et nom de la compagnie
                    parts = stock_text.split("-", 1)
                    if len(parts) == 2:
                        ticker = normalize_ticker(parts[0])
                        company_name = clean_text(parts[1])
                    else:
                        ticker = normalize_ticker(stock_text)
                        company_name = ""
                    
                    # Valeur de la transaction
                    value_text = cols[2].text if len(cols) > 2 else "0"
                    transaction_value = parse_float(value_text)
                    
                    # Type de transaction (Buy/Sell)
                    transaction_type = "Unknown"
                    if len(cols) > 3:
                        type_text = cols[3].text.strip().upper()
                        if "BUY" in type_text or "PURCHASE" in type_text:
                            transaction_type = "Buy"
                        elif "SELL" in type_text or "SALE" in type_text:
                            transaction_type = "Sell"
                        else:
                            transaction_type = type_text
                    
                    # Insider name et role (si disponible)
                    insider_name = ""
                    insider_role = ""
                    if len(cols) > 4:
                        insider_text = clean_text(cols[4].text)
                        # Essayer de parser name et role
                        if "(" in insider_text and ")" in insider_text:
                            name_part = insider_text.split("(")[0].strip()
                            role_part = insider_text.split("(")[1].split(")")[0].strip()
                            insider_name = name_part
                            insider_role = role_part
                        else:
                            insider_name = insider_text
                    
                    # Prix et shares si disponibles
                    price = parse_float(cols[5].text) if len(cols) > 5 else None
                    shares = parse_int(cols[6].text) if len(cols) > 6 else None
                    
                    # Filtrer par valeur minimum
                    if transaction_value and transaction_value >= min_value_usd:
                        trade = {
                            "ticker": ticker,
                            "company_name": company_name,
                            "insider_name": insider_name,
                            "role": insider_role,
                            "transaction_type": transaction_type,
                            "transaction_value_usd": transaction_value,
                            "shares": shares,
                            "price": price,
                            "trade_date": filed_date_text,  # TODO: parser en date
                            "filed_date": filed_date_text,
                            "source": "HEDGEFOLLOW",
                            "scraped_at": datetime.now().isoformat()
                        }
                        
                        trades_data.append(trade)
            
            break  # On a trouvé le tableau
    
    df = pd.DataFrame(trades_data)
    
    if not df.empty:
        logger.info(f"Extracted {len(df)} insider trades")
        
        # Calculer les stats
        buys = df[df["transaction_type"] == "Buy"]
        sells = df[df["transaction_type"] == "Sell"]
        
        logger.info(f"Buys: {len(buys)}, Sells: {len(sells)}")
        
        if "transaction_value_usd" in df.columns:
            total_buy_value = buys["transaction_value_usd"].sum()
            total_sell_value = sells["transaction_value_usd"].sum()
            logger.info(f"Total buy value: ${total_buy_value:,.0f}")
            logger.info(f"Total sell value: ${total_sell_value:,.0f}")
            logger.info(f"Net: ${total_buy_value - total_sell_value:,.0f}")
    else:
        logger.warning("No insider trades found")
    
    return df


def get_net_insider_activity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule l'activité nette des insiders par ticker.
    
    Args:
        df: DataFrame des trades insiders
        
    Returns:
        DataFrame avec l'activité nette par ticker
    """
    if df.empty:
        return pd.DataFrame()
    
    # Grouper par ticker
    grouped = df.groupby(["ticker", "transaction_type"])["transaction_value_usd"].agg([
        ("total_value", "sum"),
        ("num_trades", "count")
    ]).reset_index()
    
    # Pivot pour avoir buys et sells en colonnes
    pivot = grouped.pivot(
        index="ticker",
        columns="transaction_type",
        values=["total_value", "num_trades"]
    ).fillna(0)
    
    # Flatten les colonnes
    pivot.columns = ["_".join(col).strip() for col in pivot.columns.values]
    pivot = pivot.reset_index()
    
    # Calculer le net
    buy_col = "total_value_Buy" if "total_value_Buy" in pivot.columns else None
    sell_col = "total_value_Sell" if "total_value_Sell" in pivot.columns else None
    
    if buy_col and sell_col:
        pivot["net_value"] = pivot[buy_col] - pivot[sell_col]
    elif buy_col:
        pivot["net_value"] = pivot[buy_col]
    elif sell_col:
        pivot["net_value"] = -pivot[sell_col]
    else:
        pivot["net_value"] = 0
    
    # Trier par activité nette
    pivot = pivot.sort_values("net_value", ascending=False)
    
    return pivot


if __name__ == "__main__":
    # Exécution directe : scraper les trades insiders
    df = fetch_insider_trades()
    
    if not df.empty:
        # Sauvegarder avec la date
        filename = get_dated_filename("insiders")
        output_path = RAW_HF_DIR / filename
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} insider trades")
        print(f"Unique tickers: {df['ticker'].nunique()}")
        
        # Top 10 par valeur
        print("\nTop 10 trades by value:")
        top_trades = df.nlargest(10, "transaction_value_usd")
        print(top_trades[["ticker", "company_name", "transaction_type", "transaction_value_usd"]])
        
        # Activité nette par ticker
        net_activity = get_net_insider_activity(df)
        if not net_activity.empty:
            print("\nTop 10 tickers by net insider activity:")
            print(net_activity.head(10))
    else:
        print("No insider trades scraped")