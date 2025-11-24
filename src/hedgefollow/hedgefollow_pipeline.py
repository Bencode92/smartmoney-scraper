"""
Scraper optimisé pour HedgeFollow : Top funds et leurs holdings détaillées.
"""
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
from loguru import logger

from src.config import HEDGEFOLLOW_BASE_URL, RAW_HF_DIR
from src.utils.http import fetch_html, smart_session
from src.utils.parsing import make_soup, parse_float, parse_int, clean_text, slugify
from src.utils.io import save_df, get_dated_filename
from src.utils.monitoring import track_performance, track_scraping_quality, alerts, metrics
from src.validators import DataValidator, validate_scraping_result


class HedgeFollowScraper:
    """Scraper principal pour HedgeFollow avec pipeline complet."""
    
    BASE_URL = "https://hedgefollow.com"
    FUNDS_URL = f"{BASE_URL}/funds.php"
    
    def __init__(self, top_n_funds: int = 20, top_n_perf: int = 10, top_n_holdings: int = 20):
        """
        Initialise le scraper.
        
        Args:
            top_n_funds: Nombre de fonds à scraper initialement
            top_n_perf: Nombre de fonds à garder après filtrage performance
            top_n_holdings: Nombre de holdings à scraper par fond
        """
        self.top_n_funds = top_n_funds
        self.top_n_perf = top_n_perf
        self.top_n_holdings = top_n_holdings
        self.funds_data = []
        self.holdings_data = []
        
    @track_performance("hedgefollow.scrape_top_funds")
    def scrape_top_funds(self) -> pd.DataFrame:
        """
        Scrape les top N hedge funds depuis la page principale.
        
        Returns:
            DataFrame avec les infos des fonds
        """
        logger.info(f"🎯 Scraping top {self.top_n_funds} funds from HedgeFollow...")
        
        try:
            # Fetch avec smart session (anti-détection)
            html = fetch_html(self.FUNDS_URL, use_smart_session=True)
            soup = make_soup(html)
            
            # Trouver le tableau principal (plusieurs sélecteurs possibles)
            table = None
            for selector in ['table.funds-table', 'table#funds', 'table[data-type="funds"]', 'table']:
                tables = soup.select(selector)
                for t in tables:
                    # Vérifier qu'on a les bonnes colonnes
                    headers = [th.text.strip().lower() for th in t.find_all('th')]
                    if any('fund' in h or 'manager' in h for h in headers):
                        table = t
                        logger.debug(f"✅ Found funds table with selector: {selector}")
                        break
                if table:
                    break
            
            if not table:
                raise ValueError("Cannot find funds table on page")
            
            # Parser les lignes du tableau
            rows = table.find_all('tr')[1:]  # Skip header
            funds_data = []
            
            for idx, row in enumerate(rows[:self.top_n_funds], start=1):
                try:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 5:
                        continue
                    
                    # Extraire le nom et l'URL du fond
                    fund_cell = cols[0]
                    fund_link = fund_cell.find('a')
                    
                    if fund_link:
                        fund_name = clean_text(fund_link.text)
                        fund_url = fund_link.get('href', '')
                        if fund_url and not fund_url.startswith('http'):
                            fund_url = self.BASE_URL + '/' + fund_url.lstrip('/')
                    else:
                        fund_name = clean_text(fund_cell.text)
                        fund_url = ''
                    
                    # Parser la performance 3Y (avec gestion du format percentage)
                    perf_text = cols[1].text if len(cols) > 1 else ''
                    perf_3y = self._parse_performance(perf_text)
                    
                    # Parser AUM (avec gestion des suffixes B/T/M)
                    aum_text = cols[2].text if len(cols) > 2 else ''
                    aum_usd = self._parse_aum(aum_text)
                    
                    # Autres métriques
                    num_holdings = parse_int(cols[3].text) if len(cols) > 3 else None
                    top20_conc = parse_float(cols[4].text) if len(cols) > 4 else None
                    turnover = parse_float(cols[5].text) if len(cols) > 5 else None
                    
                    # Rating (étoiles)
                    rating = self._extract_rating(row)
                    
                    fund_data = {
                        'rank': idx,
                        'fund_id': slugify(fund_name),
                        'fund_name': fund_name,
                        'fund_url': fund_url,
                        'perf_3y_annualized': perf_3y,
                        'aum_billions': aum_usd / 1e9 if aum_usd else None,
                        'num_holdings': num_holdings,
                        'top20_concentration': top20_conc,
                        'turnover': turnover,
                        'rating': rating,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    funds_data.append(fund_data)
                    logger.debug(f"  #{idx}: {fund_name} - Perf: {perf_3y}% - AUM: ${aum_usd/1e9:.1f}B")
                    
                except Exception as e:
                    logger.warning(f"Error parsing fund row {idx}: {e}")
                    continue
            
            df = pd.DataFrame(funds_data)
            
            # Validation
            if df.empty or len(df) < 5:
                raise ValueError(f"Only {len(df)} funds extracted, expected at least 5")
            
            # Trier par performance annualisée
            df = df.sort_values('perf_3y_annualized', ascending=False, na_position='last')
            
            logger.info(f"✅ Scraped {len(df)} funds successfully")
            self.funds_data = df
            
            # Sauvegarder les données brutes
            save_df(df, RAW_HF_DIR / "funds_top20_raw.csv")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape funds: {e}")
            alerts.send_alert("HedgeFollow Funds Scraping Failed", str(e), "ERROR")
            raise
    
    def filter_top_performers(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Filtre les top N fonds par performance annualisée.
        
        Args:
            df: DataFrame des fonds (utilise self.funds_data si None)
            
        Returns:
            DataFrame des top performers
        """
        if df is None:
            df = self.funds_data
        
        if df.empty:
            raise ValueError("No funds data to filter")
        
        # Filtrer les fonds avec performance positive et données valides
        df_valid = df[
            (df['perf_3y_annualized'].notna()) & 
            (df['perf_3y_annualized'] > 0) &
            (df['aum_billions'].notna()) &
            (df['aum_billions'] > 0)
        ].copy()
        
        # Prendre les top N par performance
        df_top = df_valid.nlargest(self.top_n_perf, 'perf_3y_annualized')
        
        logger.info(f"🎯 Selected top {len(df_top)} funds by performance:")
        for idx, row in df_top.iterrows():
            logger.info(f"  • {row['fund_name']}: {row['perf_3y_annualized']:.2f}% annualized")
        
        # Sauvegarder
        save_df(df_top, RAW_HF_DIR / "funds_top10_filtered.csv")
        
        return df_top
    
    @track_performance("hedgefollow.scrape_fund_holdings")
    def scrape_fund_holdings(self, fund_id: str, fund_url: str) -> pd.DataFrame:
        """
        Scrape les holdings d'un fond spécifique.
        
        Args:
            fund_id: Identifiant du fond
            fund_url: URL de la page du fond
            
        Returns:
            DataFrame avec les holdings
        """
        if not fund_url:
            logger.warning(f"No URL for fund {fund_id}, skipping holdings")
            return pd.DataFrame()
        
        logger.info(f"📊 Scraping holdings for {fund_id}...")
        
        try:
            # Attendre un peu entre les requêtes
            time.sleep(random.uniform(2, 4))
            
            html = fetch_html(fund_url, use_smart_session=True)
            soup = make_soup(html)
            
            # Chercher le tableau des holdings
            holdings_table = None
            for selector in ['table.holdings', 'table#holdings', 'table[data-type="holdings"]', 'table']:
                tables = soup.select(selector)
                for t in tables:
                    headers = [th.text.strip().lower() for th in t.find_all('th')]
                    if any('stock' in h or 'company' in h or 'ticker' in h for h in headers):
                        holdings_table = t
                        break
                if holdings_table:
                    break
            
            if not holdings_table:
                logger.warning(f"No holdings table found for {fund_id}")
                return pd.DataFrame()
            
            # Parser les holdings
            holdings_data = []
            rows = holdings_table.find_all('tr')[1:]  # Skip header
            
            for idx, row in enumerate(rows[:self.top_n_holdings], start=1):
                try:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 3:
                        continue
                    
                    # Ticker et nom de la compagnie
                    ticker_cell = cols[0]
                    ticker_link = ticker_cell.find('a')
                    
                    if ticker_link:
                        ticker = clean_text(ticker_link.text).upper()
                    else:
                        ticker = clean_text(ticker_cell.text).upper()
                    
                    company_name = clean_text(cols[1].text) if len(cols) > 1 else ''
                    
                    # Pourcentage du portfolio
                    pct_portfolio = parse_float(cols[2].text) if len(cols) > 2 else None
                    
                    # Shares et valeur
                    shares_owned = self._parse_shares(cols[3].text) if len(cols) > 3 else None
                    value_owned = self._parse_value(cols[4].text) if len(cols) > 4 else None
                    
                    # Activité récente (changement)
                    latest_activity = self._parse_activity(cols[5].text) if len(cols) > 5 else None
                    
                    holding = {
                        'fund_id': fund_id,
                        'position': idx,
                        'ticker': ticker,
                        'company_name': company_name,
                        'portfolio_pct': pct_portfolio,
                        'shares_owned': shares_owned,
                        'value_millions': value_owned / 1e6 if value_owned else None,
                        'latest_activity_pct': latest_activity,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    holdings_data.append(holding)
                    
                except Exception as e:
                    logger.debug(f"Error parsing holding row {idx}: {e}")
                    continue
            
            df_holdings = pd.DataFrame(holdings_data)
            logger.info(f"  → Scraped {len(df_holdings)} holdings for {fund_id}")
            
            return df_holdings
            
        except Exception as e:
            logger.error(f"Failed to scrape holdings for {fund_id}: {e}")
            return pd.DataFrame()
    
    def scrape_all_holdings(self, funds_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Scrape les holdings pour tous les fonds du DataFrame.
        
        Args:
            funds_df: DataFrame des fonds (utilise les top performers si None)
            
        Returns:
            DataFrame consolidé de toutes les holdings
        """
        if funds_df is None:
            funds_df = self.filter_top_performers()
        
        all_holdings = []
        
        for idx, fund in funds_df.iterrows():
            fund_id = fund['fund_id']
            fund_url = fund['fund_url']
            
            # Scraper les holdings
            holdings = self.scrape_fund_holdings(fund_id, fund_url)
            
            if not holdings.empty:
                # Ajouter des infos du fond
                holdings['fund_name'] = fund['fund_name']
                holdings['fund_perf_3y'] = fund['perf_3y_annualized']
                holdings['fund_aum_billions'] = fund['aum_billions']
                
                all_holdings.append(holdings)
            
            # Pause entre les fonds
            time.sleep(random.uniform(3, 5))
        
        # Consolider
        if all_holdings:
            df_all = pd.concat(all_holdings, ignore_index=True)
            
            # Sauvegarder
            filename = get_dated_filename("holdings_top10funds")
            save_df(df_all, RAW_HF_DIR / filename)
            
            logger.info(f"✅ Total holdings scraped: {len(df_all)} positions from {len(all_holdings)} funds")
            
            return df_all
        else:
            logger.warning("No holdings data collected")
            return pd.DataFrame()
    
    def run_full_pipeline(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Execute le pipeline complet de scraping.
        
        Returns:
            Tuple (DataFrame des fonds, DataFrame des holdings)
        """
        logger.info("=" * 50)
        logger.info("🚀 Starting HedgeFollow Full Pipeline")
        logger.info("=" * 50)
        
        # Étape 1: Scraper top 20 fonds
        df_funds = self.scrape_top_funds()
        metrics.record_metric("funds_scraped", len(df_funds))
        
        # Étape 2: Filtrer top 10 par performance
        df_top_funds = self.filter_top_performers(df_funds)
        metrics.record_metric("funds_filtered", len(df_top_funds))
        
        # Étape 3: Scraper holdings des top 10
        df_holdings = self.scrape_all_holdings(df_top_funds)
        metrics.record_metric("holdings_scraped", len(df_holdings))
        
        # Analyse des données
        self._analyze_results(df_top_funds, df_holdings)
        
        logger.info("=" * 50)
        logger.info("✅ Pipeline completed successfully!")
        logger.info("=" * 50)
        
        return df_top_funds, df_holdings
    
    # === Méthodes Helper ===
    
    def _parse_performance(self, text: str) -> Optional[float]:
        """Parse la performance avec gestion des formats variés."""
        if not text:
            return None
        
        # Nettoyer le texte
        text = text.strip()
        
        # Chercher les patterns de performance
        # Format: "133.99% (32.76% Ann.)" ou juste "32.76%"
        
        # D'abord chercher la performance annualisée entre parenthèses
        ann_match = re.search(r'\(([+-]?\d+\.?\d*)%?\s*Ann', text)
        if ann_match:
            return parse_float(ann_match.group(1))
        
        # Sinon prendre la première valeur en pourcentage
        pct_match = re.search(r'([+-]?\d+\.?\d*)%', text)
        if pct_match:
            # Si c'est une perf 3 ans, la convertir en annualisée (approximation)
            perf_3y = parse_float(pct_match.group(1))
            if perf_3y and abs(perf_3y) > 50:  # Probablement une perf 3 ans totale
                # Conversion approximative : (1 + r_total)^(1/3) - 1
                return ((1 + perf_3y/100) ** (1/3) - 1) * 100
            return perf_3y
        
        return parse_float(text)
    
    def _parse_aum(self, text: str) -> Optional[float]:
        """Parse AUM avec gestion des suffixes (B, T, M)."""
        if not text:
            return None
        
        # Format typique: "$ 5.67T" ou "$156.77B"
        text = text.strip().replace('$', '').replace(',', '')
        
        # Extraire le nombre et le suffixe
        match = re.match(r'([0-9.]+)\s*([BTM])?', text, re.I)
        if match:
            value = float(match.group(1))
            suffix = match.group(2)
            
            if suffix:
                suffix = suffix.upper()
                if suffix == 'T':
                    return value * 1e12
                elif suffix == 'B':
                    return value * 1e9
                elif suffix == 'M':
                    return value * 1e6
            
            # Si pas de suffixe, assumer que c'est en milliards
            return value * 1e9
        
        return parse_float(text)
    
    def _parse_shares(self, text: str) -> Optional[float]:
        """Parse le nombre de shares (peut être en M ou B)."""
        if not text:
            return None
        
        text = text.strip().replace(',', '')
        
        # Format: "591.86M" ou "1.93B"
        match = re.match(r'([0-9.]+)\s*([BM])?', text, re.I)
        if match:
            value = float(match.group(1))
            suffix = match.group(2)
            
            if suffix:
                suffix = suffix.upper()
                if suffix == 'B':
                    return value * 1e9
                elif suffix == 'M':
                    return value * 1e6
            
            return value
        
        return parse_float(text)
    
    def _parse_value(self, text: str) -> Optional[float]:
        """Parse la valeur monétaire (en USD)."""
        if not text:
            return None
        
        # Format: "$ 359.96B" ou "$124.68B"
        text = text.strip().replace('$', '').replace(',', '')
        
        match = re.match(r'([0-9.]+)\s*([BTM])?', text, re.I)
        if match:
            value = float(match.group(1))
            suffix = match.group(2)
            
            if suffix:
                suffix = suffix.upper()
                if suffix == 'T':
                    return value * 1e12
                elif suffix == 'B':
                    return value * 1e9
                elif suffix == 'M':
                    return value * 1e6
            
            # Par défaut en milliards pour les grosses valeurs
            if value > 1000:
                return value * 1e6  # Probablement en millions
            
            return value * 1e9  # Probablement en milliards
        
        return parse_float(text)
    
    def _parse_activity(self, text: str) -> Optional[float]:
        """Parse l'activité récente (changement en %)."""
        if not text:
            return None
        
        # Format: "↑ 1.02% (+19.47M)" ou "↓ -0.22% (-2.51M)"
        match = re.search(r'([+-]?\d+\.?\d*)%', text)
        if match:
            return parse_float(match.group(1))
        
        return None
    
    def _extract_rating(self, row) -> Optional[float]:
        """Extrait le rating (nombre d'étoiles)."""
        # Chercher les étoiles (★ ou images)
        stars = row.find_all(class_=re.compile(r'star|rating'))
        if stars:
            # Compter les étoiles pleines
            full_stars = len([s for s in stars if 'full' in str(s) or '★' in str(s)])
            return float(full_stars)
        
        return None
    
    def _analyze_results(self, df_funds: pd.DataFrame, df_holdings: pd.DataFrame):
        """Analyse et affiche les statistiques des résultats."""
        logger.info("\n📊 === ANALYSE DES RÉSULTATS ===")
        
        # Stats des fonds
        logger.info("\n🏦 Top Funds Statistics:")
        logger.info(f"  • Nombre de fonds: {len(df_funds)}")
        logger.info(f"  • Performance moyenne: {df_funds['perf_3y_annualized'].mean():.2f}%")
        logger.info(f"  • AUM total: ${df_funds['aum_billions'].sum():.1f}B")
        logger.info(f"  • Holdings moyens: {df_funds['num_holdings'].mean():.0f}")
        
        # Stats des holdings
        if not df_holdings.empty:
            logger.info("\n📈 Holdings Statistics:")
            logger.info(f"  • Total positions: {len(df_holdings)}")
            logger.info(f"  • Unique tickers: {df_holdings['ticker'].nunique()}")
            
            # Top tickers par occurrence
            top_tickers = df_holdings['ticker'].value_counts().head(10)
            logger.info("\n🎯 Most Popular Holdings:")
            for ticker, count in top_tickers.items():
                pct = (count / len(df_funds)) * 100
                logger.info(f"    {ticker}: {count} funds ({pct:.1f}%)")
            
            # Concentration moyenne
            avg_concentration = df_holdings.groupby('fund_id')['portfolio_pct'].sum().mean()
            logger.info(f"\n  • Concentration moyenne top 20: {avg_concentration:.1f}%")


# === Import pour compatibilité ===
import random


if __name__ == "__main__":
    # Test du pipeline complet
    logger.info("🚀 HedgeFollow Pipeline Test")
    
    # Créer le scraper
    scraper = HedgeFollowScraper(
        top_n_funds=20,    # Scraper 20 fonds
        top_n_perf=10,     # Garder top 10 par performance
        top_n_holdings=20  # 20 holdings par fond
    )
    
    try:
        # Lancer le pipeline
        df_funds, df_holdings = scraper.run_full_pipeline()
        
        # Afficher le résumé
        print("\n✅ Pipeline terminé avec succès!")
        print(f"  - Fonds scrapés: {len(df_funds)}")
        print(f"  - Holdings totales: {len(df_holdings)}")
        
        # Top 5 fonds
        print("\n🏆 Top 5 Hedge Funds par Performance:")
        print(df_funds[['fund_name', 'perf_3y_annualized', 'aum_billions']].head())
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise
