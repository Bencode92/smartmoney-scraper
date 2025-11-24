"""
Scraper pour le stock screener de HedgeFollow.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from src.config import (
    HEDGEFOLLOW_BASE_URL,
    RAW_HF_DIR
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


# URL du screener
HEDGEFOLLOW_SCREENER_URL = f"{HEDGEFOLLOW_BASE_URL}/screener.php"


def fetch_screener_results(
    filters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Récupère les résultats du stock screener de HedgeFollow.
    
    Args:
        filters: Filtres à appliquer (dict de paramètres)
        
    Returns:
        DataFrame avec les résultats du screener
    """
    logger.info("Fetching HedgeFollow screener results")
    
    # Utiliser les filtres par défaut si non fournis
    if filters is None:
        # Filtres recommandés : fonds performants + insiders acheteurs
        filters = {
            "outperforming_funds": True,
            "insider_net_buys": True,
            "min_funds": 3
        }
    
    # Construire l'URL avec paramètres
    # Note: Adapter selon l'API réelle de HedgeFollow
    url = HEDGEFOLLOW_SCREENER_URL
    
    try:
        # Pour l'instant on récupère la page par défaut
        # TODO: Implémenter l'envoi des filtres (GET ou POST)
        html = fetch_html(url)
    except Exception as e:
        logger.error(f"Failed to fetch screener results: {e}")
        return pd.DataFrame()
    
    soup = make_soup(html)
    
    # Trouver le tableau des résultats
    screener_data = []
    tables = soup.find_all("table")
    
    for table in tables:
        # Identifier le tableau du screener
        headers = [h.text.strip().lower() for h in table.find_all("th")]
        
        # Vérifier si c'est le bon tableau (contient ticker/stock)
        if any("ticker" in h or "stock" in h or "symbol" in h for h in headers):
            logger.debug("Found screener results table")
            
            rows = table.find_all("tr")[1:]  # Skip header
            
            for row in rows:
                cols = row.find_all("td")
                
                if len(cols) >= 3:  # Minimum: ticker, name, metric
                    
                    # Extraire ticker et nom
                    stock_cell = cols[0]
                    stock_link = stock_cell.find("a")
                    
                    if stock_link:
                        stock_text = stock_link.text
                    else:
                        stock_text = stock_cell.text
                    
                    # Parser ticker et nom
                    parts = stock_text.split("-", 1)
                    if len(parts) == 2:
                        ticker = normalize_ticker(parts[0])
                        company_name = clean_text(parts[1])
                    else:
                        ticker = normalize_ticker(stock_text)
                        company_name = clean_text(cols[1].text) if len(cols) > 1 else ""
                    
                    result = {
                        "ticker": ticker,
                        "company_name": company_name,
                        "num_funds_holding": parse_int(cols[2].text) if len(cols) > 2 else None,
                        "total_value_bought": parse_float(cols[3].text) if len(cols) > 3 else None,
                        "avg_weight": parse_float(cols[4].text) if len(cols) > 4 else None,
                        "insider_activity": clean_text(cols[5].text) if len(cols) > 5 else "",
                        "price_change_1m": parse_float(cols[6].text) if len(cols) > 6 else None,
                        "price_change_3m": parse_float(cols[7].text) if len(cols) > 7 else None,
                        "source": "HEDGEFOLLOW_SCREENER",
                        "scraped_at": datetime.now().isoformat()
                    }
                    
                    # Ajouter les filtres appliqués comme métadonnées
                    result["filters_applied"] = str(filters)
                    
                    screener_data.append(result)
            
            break  # On a trouvé le tableau
    
    df = pd.DataFrame(screener_data)
    
    if not df.empty:
        logger.info(f"Extracted {len(df)} stocks from screener")
        
        # Trier par nombre de fonds détenteurs
        if "num_funds_holding" in df.columns:
            df = df.sort_values("num_funds_holding", ascending=False)
    else:
        logger.warning("No screener results found")
    
    return df


def get_high_conviction_picks(
    min_funds: int = 5,
    min_insider_net_buy: float = 1_000_000
) -> pd.DataFrame:
    """
    Filtre les résultats du screener pour obtenir les picks à haute conviction.
    
    Args:
        min_funds: Nombre minimum de fonds détenteurs
        min_insider_net_buy: Valeur minimum d'achats nets insiders
        
    Returns:
        DataFrame filtré avec les meilleures opportunités
    """
    # Récupérer les résultats du screener
    df = fetch_screener_results()
    
    if df.empty:
        return df
    
    # Appliquer les filtres
    if "num_funds_holding" in df.columns:
        df = df[df["num_funds_holding"] >= min_funds]
    
    # Filtrer par activité insider si disponible
    # (dépend de la structure réelle des données)
    
    # Trier par conviction (nombre de fonds * valeur moyenne)
    if "num_funds_holding" in df.columns and "avg_weight" in df.columns:
        df["conviction_score"] = df["num_funds_holding"] * df["avg_weight"].fillna(1)
        df = df.sort_values("conviction_score", ascending=False)
    
    logger.info(f"Found {len(df)} high conviction picks")
    
    return df


if __name__ == "__main__":
    # Exécution directe : scraper le screener
    df = fetch_screener_results()
    
    if not df.empty:
        # Sauvegarder avec la date
        filename = get_dated_filename("screener")
        output_path = RAW_HF_DIR / filename
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} stocks from screener")
        
        # Top 10 par nombre de fonds
        print("\nTop 10 stocks by fund ownership:")
        if "num_funds_holding" in df.columns:
            print(df[["ticker", "company_name", "num_funds_holding", "total_value_bought"]].head(10))
        
        # High conviction picks
        high_conviction = get_high_conviction_picks()
        if not high_conviction.empty:
            print(f"\n{len(high_conviction)} high conviction picks:")
            print(high_conviction[["ticker", "company_name", "num_funds_holding"]].head(10))
    else:
        print("No screener data scraped")