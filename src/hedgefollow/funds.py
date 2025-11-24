"""
Scraper pour récupérer la liste des top hedge funds depuis HedgeFollow.
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
    parse_float,
    parse_int,
    slugify,
    clean_text
)
from src.utils.io import save_df


# URL de la page des top hedge funds
HEDGEFOLLOW_TOP_FUNDS_URL = f"{HEDGEFOLLOW_BASE_URL}/funds.php"


def scrape_top_funds() -> pd.DataFrame:
    """
    Récupère la liste des top hedge funds depuis HedgeFollow.
    
    Returns:
        DataFrame avec les infos des fonds
    """
    logger.info("Scraping HedgeFollow top funds...")
    
    # Récupérer la page
    html = fetch_html(HEDGEFOLLOW_TOP_FUNDS_URL)
    soup = make_soup(html)
    
    # Trouver le tableau principal
    # Chercher un tableau avec les colonnes typiques des hedge funds
    tables = soup.find_all("table")
    
    funds_data = []
    
    for table in tables:
        # Vérifier si c'est le bon tableau en regardant les headers
        headers = table.find_all("th")
        header_texts = [h.text.strip().lower() for h in headers]
        
        # Chercher des headers typiques
        if any("manager" in h or "fund" in h for h in header_texts):
            logger.debug("Found funds table")
            
            # Extraire les données du tableau
            rows = table.find_all("tr")[1:]  # Skip header row
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 5:  # S'assurer qu'on a assez de colonnes
                    
                    # Extraire le nom du fond et l'URL si disponible
                    fund_name_cell = cols[0]
                    fund_link = fund_name_cell.find("a")
                    
                    if fund_link:
                        fund_name = clean_text(fund_link.text)
                        fund_url = fund_link.get("href", "")
                        if fund_url and not fund_url.startswith("http"):
                            fund_url = HEDGEFOLLOW_BASE_URL + "/" + fund_url.lstrip("/")
                    else:
                        fund_name = clean_text(fund_name_cell.text)
                        fund_url = ""
                    
                    # Extraire les autres données
                    fund_data = {
                        "fund_id": slugify(fund_name),
                        "name": fund_name,
                        "fund_url": fund_url,
                        "aum_usd": parse_float(cols[1].text) if len(cols) > 1 else None,
                        "perf_3y": parse_float(cols[2].text) if len(cols) > 2 else None,
                        "num_holdings": parse_int(cols[3].text) if len(cols) > 3 else None,
                        "top20_concentration": parse_float(cols[4].text) if len(cols) > 4 else None,
                        "turnover": parse_float(cols[5].text) if len(cols) > 5 else None,
                        "source": "HEDGEFOLLOW",
                        "scraped_at": datetime.now().isoformat()
                    }
                    
                    funds_data.append(fund_data)
            
            break  # On a trouvé le bon tableau
    
    if not funds_data:
        # Fallback : essayer d'extraire depuis le premier tableau
        logger.warning("Could not find specific funds table, trying generic extraction")
        if tables:
            table_data = extract_table_data(tables[0])
            for row in table_data:
                fund_name = row.get("Manager", row.get("Fund", ""))
                if fund_name:
                    funds_data.append({
                        "fund_id": slugify(fund_name),
                        "name": clean_text(fund_name),
                        "fund_url": "",
                        "aum_usd": parse_float(row.get("AUM", "")),
                        "perf_3y": parse_float(row.get("3Y Perf", row.get("3Y", ""))),
                        "num_holdings": parse_int(row.get("Holdings", row.get("#Holdings", ""))),
                        "top20_concentration": parse_float(row.get("Top 20", row.get("Concentration", ""))),
                        "turnover": parse_float(row.get("Turnover", "")),
                        "source": "HEDGEFOLLOW",
                        "scraped_at": datetime.now().isoformat()
                    })
    
    # Créer le DataFrame
    df = pd.DataFrame(funds_data)
    
    if df.empty:
        logger.error("No funds data extracted")
        return df
    
    # Trier par AUM décroissant
    df = df.sort_values("aum_usd", ascending=False, na_position="last")
    
    logger.info(f"Scraped {len(df)} funds from HedgeFollow")
    
    return df


def get_top_n_funds(
    n: int = HEDGEFOLLOW_TOP_N_FUNDS,
    min_aum: Optional[float] = 1_000_000_000,  # 1B USD minimum
    min_holdings: Optional[int] = 10,
    min_perf_3y: Optional[float] = None
) -> pd.DataFrame:
    """
    Sélectionne les top N fonds selon des critères.
    
    Args:
        n: Nombre de fonds à sélectionner
        min_aum: AUM minimum en USD
        min_holdings: Nombre minimum de positions
        min_perf_3y: Performance 3 ans minimum (%)
        
    Returns:
        DataFrame filtré des top fonds
    """
    # Charger ou scraper les fonds
    funds_file = RAW_HF_DIR / "funds_top.csv"
    
    if funds_file.exists():
        logger.info(f"Loading existing funds data from {funds_file}")
        df = pd.read_csv(funds_file)
    else:
        logger.info("No existing funds data, scraping...")
        df = scrape_top_funds()
        save_df(df, funds_file)
    
    if df.empty:
        logger.warning("No funds data available")
        return df
    
    # Appliquer les filtres
    if min_aum is not None:
        df = df[df["aum_usd"] >= min_aum]
    
    if min_holdings is not None:
        df = df[df["num_holdings"] >= min_holdings]
    
    if min_perf_3y is not None:
        df = df[df["perf_3y"] >= min_perf_3y]
    
    # Prendre les top N
    df = df.head(n)
    
    logger.info(f"Selected top {len(df)} funds with filters")
    
    return df


if __name__ == "__main__":
    # Exécution directe : scraper et sauvegarder les top funds
    df = scrape_top_funds()
    
    if not df.empty:
        output_path = RAW_HF_DIR / "funds_top.csv"
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} funds")
        print(f"\nTop 10 by AUM:")
        print(df[["name", "aum_usd", "perf_3y", "num_holdings"]].head(10))
    else:
        print("No data scraped")