"""
Scraper robuste pour récupérer la liste des top hedge funds depuis HedgeFollow.
"""
import re
from datetime import datetime
from typing import Optional, List, Dict
import pandas as pd
from loguru import logger

from src.config import HEDGEFOLLOW_BASE_URL, HEDGEFOLLOW_TOP_N_FUNDS, RAW_HF_DIR
from src.utils.http import fetch_html
from src.utils.parsing import (
    clean_text,
    extract_table_data,
    make_soup,
    parse_float,
    parse_int,
    slugify,
)
from src.utils.io import save_df
from src.utils.monitoring import track_performance, track_scraping_quality, alerts
from src.validators import DataValidator, ScrapingValidator, validate_scraping_result

HEDGEFOLLOW_TOP_FUNDS_URL = f"{HEDGEFOLLOW_BASE_URL}/funds.php"


@track_performance("hedgefollow.funds")
def scrape_top_funds() -> pd.DataFrame:
    """
    Récupère la liste des top hedge funds depuis HedgeFollow avec validation robuste.
    
    Returns:
        DataFrame validé avec les infos des fonds
        
    Raises:
        ValueError: Si la structure HTML a changé ou données invalides
    """
    logger.info("🚀 Starting HedgeFollow top funds scraping...")
    
    try:
        # Récupérer la page avec anti-détection
        html = fetch_html(HEDGEFOLLOW_TOP_FUNDS_URL, use_smart_session=True)
        soup = make_soup(html)
        
        # Valider la structure HTML de base
        try:
            ScrapingValidator.validate_html_structure(
                soup,
                {
                    "table": "Tableau principal",
                    "th": "Headers de tableau",
                }
            )
        except ValueError as e:
            alerts.send_alert(
                "Structure HedgeFollow changée",
                f"Impossible de trouver les éléments HTML attendus: {e}",
                "CRITICAL"
            )
            raise
        
        # Essayer plusieurs sélecteurs pour trouver le bon tableau
        table = None
        selectors = [
            'table.funds-table',
            'table#hedge-funds',
            'table[data-type="funds"]',
            'table[class*="fund"]',
            'table[id*="fund"]',
            'table'  # Fallback générique
        ]
        
        for selector in selectors:
            tables = soup.select(selector)
            if tables:
                # Chercher le tableau avec les bons headers
                for t in tables:
                    headers = [th.text.strip().lower() for th in t.find_all('th')]
                    if any('fund' in h or 'manager' in h or 'aum' in h for h in headers):
                        table = t
                        logger.debug(f"✅ Found funds table with selector: {selector}")
                        break
                if table:
                    break
        
        if not table:
            # Fallback: prendre le plus gros tableau
            all_tables = soup.find_all("table")
            if all_tables:
                table = max(all_tables, key=lambda t: len(t.find_all("tr")))
                logger.warning("⚠️ Using largest table as fallback")
            else:
                raise ValueError("Aucun tableau trouvé sur la page")
        
        # Valider les headers du tableau
        expected_headers = ["fund", "manager", "aum", "holdings", "performance"]
        try:
            ScrapingValidator.validate_table_headers(table, expected_headers, fuzzy=True)
        except ValueError as e:
            logger.warning(f"Headers non standards détectés: {e}")
        
        # Extraire les données avec gestion d'erreur par ligne
        funds_data = []
        rows = table.find_all("tr")
        
        # Identifier la ligne de headers
        header_row_idx = 0
        for i, row in enumerate(rows):
            if row.find("th"):
                header_row_idx = i
                break
        
        # Parser les données (skip headers)
        for row_idx, row in enumerate(rows[header_row_idx + 1:], start=1):
            try:
                cols = row.find_all(["td", "th"])
                if len(cols) < 3:  # Minimum de colonnes requises
                    continue
                
                # Extraction robuste du nom du fond
                fund_name_cell = cols[0]
                fund_name = None
                fund_url = ""
                
                # Chercher un lien d'abord
                fund_link = fund_name_cell.find("a")
                if fund_link:
                    fund_name = clean_text(fund_link.text or fund_link.get("title", ""))
                    fund_url = fund_link.get("href", "")
                    if fund_url and not fund_url.startswith("http"):
                        fund_url = HEDGEFOLLOW_BASE_URL + "/" + fund_url.lstrip("/")
                
                # Sinon prendre le texte de la cellule
                if not fund_name:
                    fund_name = clean_text(fund_name_cell.text)
                
                # Valider le nom du fond
                if not fund_name or len(fund_name) < 3:
                    logger.debug(f"Ligne {row_idx}: nom de fond invalide, skip")
                    continue
                
                # Extraction sécurisée des autres colonnes
                fund_data = {
                    "fund_id": slugify(fund_name),
                    "name": fund_name,
                    "fund_url": fund_url,
                    "aum_usd": None,
                    "perf_3y": None,
                    "num_holdings": None,
                    "top20_concentration": None,
                    "turnover": None,
                    "source": "HEDGEFOLLOW",
                    "scraped_at": datetime.now().isoformat(),
                }
                
                # Parser les colonnes numériques avec gestion d'erreur
                if len(cols) > 1:
                    fund_data["aum_usd"] = parse_float(cols[1].text)
                if len(cols) > 2:
                    # Chercher la performance (peut être dans différentes colonnes)
                    for i in range(2, min(5, len(cols))):
                        text = cols[i].text
                        if "%" in text or re.search(r'[-+]?\d+\.?\d*', text):
                            perf = parse_float(text)
                            if perf is not None and -100 <= perf <= 1000:  # Valeurs raisonnables
                                fund_data["perf_3y"] = perf
                                break
                
                if len(cols) > 3:
                    fund_data["num_holdings"] = parse_int(cols[3].text)
                if len(cols) > 4:
                    fund_data["top20_concentration"] = parse_float(cols[4].text)
                if len(cols) > 5:
                    fund_data["turnover"] = parse_float(cols[5].text)
                
                funds_data.append(fund_data)
                
            except Exception as e:
                logger.debug(f"Erreur parsing ligne {row_idx}: {e}")
                continue
        
        # Si aucune donnée extraite avec la méthode principale, essayer extract_table_data
        if not funds_data:
            logger.warning("Méthode principale échouée, essai avec extract_table_data")
            table_data = extract_table_data(table)
            
            for row in table_data:
                # Mapping flexible des colonnes
                fund_name = (
                    row.get("Manager") or 
                    row.get("Fund") or 
                    row.get("Fund Name") or
                    row.get("Name") or
                    ""
                )
                
                if not fund_name:
                    continue
                
                funds_data.append({
                    "fund_id": slugify(fund_name),
                    "name": clean_text(fund_name),
                    "fund_url": "",
                    "aum_usd": parse_float(
                        row.get("AUM") or row.get("Assets") or row.get("AuM") or ""
                    ),
                    "perf_3y": parse_float(
                        row.get("3Y Perf") or row.get("3Y") or row.get("Performance") or ""
                    ),
                    "num_holdings": parse_int(
                        row.get("Holdings") or row.get("#Holdings") or row.get("Positions") or ""
                    ),
                    "top20_concentration": parse_float(
                        row.get("Top 20") or row.get("Concentration") or row.get("Top20") or ""
                    ),
                    "turnover": parse_float(
                        row.get("Turnover") or row.get("Turn") or ""
                    ),
                    "source": "HEDGEFOLLOW",
                    "scraped_at": datetime.now().isoformat()
                })
        
        # Créer le DataFrame
        df = pd.DataFrame(funds_data)
        
        # Validation des données
        try:
            df = validate_scraping_result(df, "funds")
        except ValueError as e:
            alerts.send_alert(
                "Données HedgeFollow invalides",
                f"Échec de validation: {e}",
                "ERROR"
            )
            # Essayer de continuer avec ce qu'on a
            if df.empty:
                raise
        
        # Trier par AUM décroissant
        if not df.empty and "aum_usd" in df.columns:
            df = df.sort_values("aum_usd", ascending=False, na_position="last")
        
        # Enregistrer les métriques de qualité
        track_scraping_quality(df, "HEDGEFOLLOW")
        
        logger.info(f"✅ Scraped {len(df)} funds from HedgeFollow successfully")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Failed to scrape HedgeFollow: {e}")
        alerts.send_alert(
            "Échec scraping HedgeFollow",
            str(e),
            "CRITICAL"
        )
        raise


def get_top_n_funds(
    n: int = HEDGEFOLLOW_TOP_N_FUNDS,
    min_aum: Optional[float] = 1_000_000_000,
    min_holdings: Optional[int] = 10,
    min_perf_3y: Optional[float] = None,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Sélectionne les top N fonds selon des critères avec cache intelligent.
    
    Args:
        n: Nombre de fonds à sélectionner
        min_aum: AUM minimum en USD (défaut: 1B)
        min_holdings: Nombre minimum de positions
        min_perf_3y: Performance 3 ans minimum (%)
        force_refresh: Force le re-scraping même si cache existe
        
    Returns:
        DataFrame filtré et validé des top fonds
    """
    funds_file = RAW_HF_DIR / "funds_top.csv"
    
    # Vérifier si on doit rafraîchir
    should_refresh = force_refresh
    
    if not should_refresh and funds_file.exists():
        # Vérifier l'âge du fichier
        file_age_hours = (datetime.now().timestamp() - funds_file.stat().st_mtime) / 3600
        
        if file_age_hours > 24:  # Plus de 24h
            logger.info(f"Cache trop vieux ({file_age_hours:.1f}h), rafraîchissement...")
            should_refresh = True
        else:
            logger.info(f"Using cache ({file_age_hours:.1f}h old)")
    else:
        should_refresh = True
    
    # Charger ou scraper les données
    if should_refresh:
        logger.info("Scraping fresh data from HedgeFollow...")
        df = scrape_top_funds()
        if not df.empty:
            save_df(df, funds_file)
    else:
        logger.info(f"Loading cached funds data from {funds_file}")
        df = pd.read_csv(funds_file)
        
        # Valider même les données cachées
        try:
            DataValidator.validate_funds(df, min_funds=3)
            DataValidator.check_data_freshness(df, max_days=7)
        except ValueError as e:
            logger.warning(f"Cache invalide: {e}, re-scraping...")
            df = scrape_top_funds()
            if not df.empty:
                save_df(df, funds_file)
    
    if df.empty:
        logger.error("No funds data available")
        return df
    
    # Appliquer les filtres
    initial_count = len(df)
    
    if min_aum is not None and "aum_usd" in df.columns:
        df = df[df["aum_usd"] >= min_aum]
        logger.debug(f"Filter AUM >= {min_aum:,.0f}: {initial_count} -> {len(df)}")
    
    if min_holdings is not None and "num_holdings" in df.columns:
        df = df[df["num_holdings"] >= min_holdings]
        logger.debug(f"Filter holdings >= {min_holdings}: {len(df)} remaining")
    
    if min_perf_3y is not None and "perf_3y" in df.columns:
        df = df[df["perf_3y"] >= min_perf_3y]
        logger.debug(f"Filter perf >= {min_perf_3y}%: {len(df)} remaining")
    
    # Prendre les top N
    df = df.head(n)
    
    logger.info(f"✅ Selected top {len(df)}/{n} funds with filters")
    
    return df


if __name__ == "__main__":
    # Test avec monitoring complet
    from src.utils.monitoring import metrics, check_scraping_health
    
    logger.info("=== HedgeFollow Funds Scraper Test ===")
    
    # Test de connectivité d'abord
    from src.utils.http import test_connectivity
    if not test_connectivity():
        logger.error("Connectivity test failed, check network/proxy settings")
        exit(1)
    
    # Scraper avec toutes les protections
    try:
        df = scrape_top_funds()
        
        if not df.empty:
            output_path = RAW_HF_DIR / "funds_top.csv"
            save_df(df, output_path)
            
            # Afficher un résumé
            print(f"\n✅ Scraped {len(df)} funds successfully")
            print("\nTop 10 by AUM:")
            print(df[["name", "aum_usd", "perf_3y", "num_holdings"]].head(10))
            
            # Afficher les métriques
            print("\n📊 Metrics Summary:")
            summary = metrics.get_summary()
            print(f"  - Duration: {summary['run_duration']:.2f}s")
            print(f"  - Errors: {summary['total_errors']}")
            for metric, stats in summary["metrics_summary"].items():
                print(f"  - {metric}: {stats}")
        else:
            print("❌ No data scraped")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Scraping failed: {e}")
        
    # Vérifier la santé globale
    print("\n🏥 Health Check:")
    health = check_scraping_health()
    print(f"  Status: {health['status']}")
    for check, result in health["checks"].items():
        print(f"  - {check}: {result}")
