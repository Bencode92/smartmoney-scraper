"""
Scraper pour récupérer la liste des superinvestors depuis Dataroma.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from src.config import (
    DATAROMA_BASE_URL,
    RAW_DTR_DIR,
    DATAROMA_TOP_N_MANAGERS
)
from src.utils.http import fetch_html
from src.utils.parsing import (
    make_soup,
    parse_float,
    parse_int,
    slugify,
    clean_text
)
from src.utils.io import save_df


# URL de la page des superinvestors
DATAROMA_MANAGERS_URL = f"{DATAROMA_BASE_URL}/managers.php"


def scrape_managers() -> pd.DataFrame:
    """
    Récupère la liste des superinvestors depuis Dataroma.
    
    Returns:
        DataFrame avec les infos des managers
    """
    logger.info("Scraping Dataroma superinvestors...")
    
    try:
        html = fetch_html(DATAROMA_MANAGERS_URL)
    except Exception as e:
        logger.error(f"Failed to fetch Dataroma managers: {e}")
        return pd.DataFrame()
    
    soup = make_soup(html)
    
    managers_data = []
    
    # Dataroma a souvent une liste de liens vers les managers
    # Chercher les patterns typiques
    
    # Option 1: Tableau de managers
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        
        for row in rows:
            cols = row.find_all("td")
            if cols:
                # Extraire le nom et l'URL du manager
                manager_cell = cols[0]
                manager_link = manager_cell.find("a")
                
                if manager_link:
                    manager_name = clean_text(manager_link.text)
                    manager_url = manager_link.get("href", "")
                    
                    if manager_url and not manager_url.startswith("http"):
                        manager_url = DATAROMA_BASE_URL + "/" + manager_url.lstrip("/")
                    
                    # Extraire les autres infos si disponibles
                    portfolio_value = parse_float(cols[1].text) if len(cols) > 1 else None
                    num_positions = parse_int(cols[2].text) if len(cols) > 2 else None
                    
                    if manager_name:
                        managers_data.append({
                            "manager_id": slugify(manager_name),
                            "name": manager_name,
                            "manager_url": manager_url,
                            "portfolio_value_usd": portfolio_value,
                            "num_positions": num_positions,
                            "style": clean_text(cols[3].text) if len(cols) > 3 else "",
                            "source": "DATAROMA",
                            "scraped_at": datetime.now().isoformat()
                        })
    
    # Option 2: Liste de liens directs
    if not managers_data:
        logger.debug("Trying alternative extraction method for managers")
        
        # Chercher tous les liens qui pointent vers des pages de portefeuille
        links = soup.find_all("a", href=True)
        
        for link in links:
            href = link["href"]
            
            # Identifier les liens vers les managers (ex: portfolio.php?manager=XXX)
            if "portfolio" in href or "manager" in href:
                manager_name = clean_text(link.text)
                
                if manager_name and len(manager_name) > 3:  # Filtrer les liens vides
                    manager_url = href if href.startswith("http") else DATAROMA_BASE_URL + "/" + href.lstrip("/")
                    
                    # Vérifier qu'on n'a pas déjà ce manager
                    if not any(m["name"] == manager_name for m in managers_data):
                        managers_data.append({
                            "manager_id": slugify(manager_name),
                            "name": manager_name,
                            "manager_url": manager_url,
                            "portfolio_value_usd": None,
                            "num_positions": None,
                            "style": "",
                            "source": "DATAROMA",
                            "scraped_at": datetime.now().isoformat()
                        })
    
    df = pd.DataFrame(managers_data)
    
    if df.empty:
        logger.error("No managers data extracted")
        return df
    
    # Trier par valeur de portefeuille si disponible
    if "portfolio_value_usd" in df.columns:
        df = df.sort_values("portfolio_value_usd", ascending=False, na_position="last")
    
    logger.info(f"Scraped {len(df)} managers from Dataroma")
    
    return df


def get_top_n_managers(
    n: int = DATAROMA_TOP_N_MANAGERS,
    min_portfolio_value: Optional[float] = None
) -> pd.DataFrame:
    """
    Sélectionne les top N managers selon des critères.
    
    Args:
        n: Nombre de managers à sélectionner
        min_portfolio_value: Valeur minimum du portefeuille en USD
        
    Returns:
        DataFrame filtré des top managers
    """
    # Charger ou scraper les managers
    managers_file = RAW_DTR_DIR / "managers.csv"
    
    if managers_file.exists():
        logger.info(f"Loading existing managers data from {managers_file}")
        df = pd.read_csv(managers_file)
    else:
        logger.info("No existing managers data, scraping...")
        df = scrape_managers()
        save_df(df, managers_file)
    
    if df.empty:
        logger.warning("No managers data available")
        return df
    
    # Appliquer les filtres
    if min_portfolio_value is not None and "portfolio_value_usd" in df.columns:
        df = df[df["portfolio_value_usd"] >= min_portfolio_value]
    
    # Prendre les top N
    df = df.head(n)
    
    logger.info(f"Selected top {len(df)} managers")
    
    return df


if __name__ == "__main__":
    # Exécution directe : scraper et sauvegarder les managers
    df = scrape_managers()
    
    if not df.empty:
        output_path = RAW_DTR_DIR / "managers.csv"
        save_df(df, output_path)
        
        # Afficher un résumé
        print(f"\nScraped {len(df)} managers")
        print("\nTop 10 managers:")
        print(df[["name", "portfolio_value_usd", "num_positions"]].head(10))
    else:
        print("No managers data scraped")