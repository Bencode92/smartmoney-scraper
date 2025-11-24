"""
Pipeline optimisé HedgeFollow : Top AUM → Top Perf → Top Holdings
Stratégie exacte : 20 plus gros AUM → 10 meilleurs 3Y → 30 holdings chacun
"""
import re
import time
import random
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
from loguru import logger

from src.config import HEDGEFOLLOW_BASE_URL, RAW_HF_DIR
from src.utils.http import fetch_html
from src.utils.parsing import make_soup, parse_float, parse_int, clean_text, slugify
from src.utils.io import save_df, get_dated_filename
from src.utils.monitoring import track_performance, alerts, metrics
from src.validators import DataValidator


class HedgeFollowSmartMoneyPipeline:
    """Pipeline Smart Money : AUM → Performance → Holdings → Univers."""
    
    BASE_URL = "https://hedgefollow.com"
    FUNDS_URL = f"{BASE_URL}/funds.php"
    
    def __init__(self, 
                 top_n_aum: int = 20,
                 top_n_perf: int = 10, 
                 top_n_holdings: int = 30):
        """
        Initialise le pipeline Smart Money.
        
        Args:
            top_n_aum: Nombre de fonds par AUM à garder (défaut: 20)
            top_n_perf: Nombre de top performers à garder (défaut: 10)
            top_n_holdings: Nombre de holdings par fond (défaut: 30)
        """
        self.top_n_aum = top_n_aum
        self.top_n_perf = top_n_perf
        self.top_n_holdings = top_n_holdings
        self.funds_data = pd.DataFrame()
        self.holdings_data = pd.DataFrame()
        self.smart_universe = set()
        
    @track_performance("hedgefollow.scrape_all_funds")
    def scrape_all_funds(self, max_funds: int = 100) -> pd.DataFrame:
        """
        Scrape TOUS les fonds du tableau principal (ou max_funds).
        On triera par AUM après.
        
        Args:
            max_funds: Nombre max de fonds à scraper
            
        Returns:
            DataFrame avec tous les fonds scrapés
        """
        logger.info(f"🎯 Scraping ALL funds from HedgeFollow (max {max_funds})...")
        
        try:
            html = fetch_html(self.FUNDS_URL, use_smart_session=True)
            soup = make_soup(html)
            
            # Trouver le tableau principal
            table = None
            for selector in ['table.funds-table', 'table#funds', 'table[data-type="funds"]', 'table']:
                tables = soup.select(selector)
                for t in tables:
                    headers = [th.text.strip().lower() for th in t.find_all('th')]
                    if any('fund' in h or 'manager' in h for h in headers):
                        table = t
                        logger.debug(f"✅ Found funds table with selector: {selector}")
                        break
                if table:
                    break
            
            if not table:
                raise ValueError("Cannot find funds table on page")
            
            # Parser TOUTES les lignes (jusqu'à max_funds)
            rows = table.find_all('tr')[1:]  # Skip header
            funds_data = []
            
            for idx, row in enumerate(rows[:max_funds], start=1):
                try:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 3:  # Minimum: nom, perf, AUM
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
                    
                    # Parser la performance 3Y
                    perf_text = cols[1].text if len(cols) > 1 else ''
                    perf_3y = self._parse_performance(perf_text)
                    
                    # Parser AUM - CRITIQUE pour le tri
                    aum_text = cols[2].text if len(cols) > 2 else ''
                    aum_usd = self._parse_aum(aum_text)
                    
                    # Autres métriques
                    num_holdings = parse_int(cols[3].text) if len(cols) > 3 else None
                    top20_conc = parse_float(cols[4].text) if len(cols) > 4 else None
                    turnover = parse_float(cols[5].text) if len(cols) > 5 else None
                    rating = self._extract_rating(row)
                    
                    fund_data = {
                        'scrape_rank': idx,
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
                    
                except Exception as e:
                    logger.warning(f"Error parsing fund row {idx}: {e}")
                    continue
            
            df_all = pd.DataFrame(funds_data)
            
            if df_all.empty or len(df_all) < 10:
                raise ValueError(f"Only {len(df_all)} funds extracted, expected at least 10")
            
            logger.info(f"✅ Scraped {len(df_all)} funds total from HedgeFollow")
            
            # Sauvegarder TOUS les fonds scrapés
            save_df(df_all, RAW_HF_DIR / "funds_all_scraped.csv")
            
            return df_all
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape all funds: {e}")
            alerts.send_alert("HedgeFollow Funds Scraping Failed", str(e), "ERROR")
            raise
    
    def filter_top_by_aum(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Filtre les top N fonds par AUM (plus gros gestionnaires).
        
        Args:
            df: DataFrame des fonds
            
        Returns:
            DataFrame des top N par AUM
        """
        if df is None or df.empty:
            raise ValueError("No funds data to filter")
        
        # Filtrer les fonds avec AUM valide
        df_valid = df[df['aum_billions'].notna()].copy()
        
        # Trier par AUM décroissant et prendre top N
        df_top_aum = df_valid.sort_values('aum_billions', ascending=False).head(self.top_n_aum).copy()
        
        # Ajouter le rang AUM
        df_top_aum['rank_aum'] = range(1, len(df_top_aum) + 1)
        
        logger.info(f"🏦 Selected top {len(df_top_aum)} funds by AUM:")
        for _, row in df_top_aum.head(5).iterrows():
            logger.info(f"  #{row['rank_aum']}: {row['fund_name']}: ${row['aum_billions']:.1f}B")
        
        # Sauvegarder
        save_df(df_top_aum, RAW_HF_DIR / "funds_top20_by_aum.csv")
        self.funds_data = df_top_aum
        
        return df_top_aum
    
    def filter_top_performers(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Parmi les top AUM, garde les top N par performance 3Y.
        
        Args:
            df: DataFrame des top AUM
            
        Returns:
            DataFrame des top performers
        """
        if df is None:
            df = self.funds_data
        
        if df.empty:
            raise ValueError("No funds data to filter")
        
        # Filtrer les fonds avec performance valide et positive
        df_valid = df[
            (df['perf_3y_annualized'].notna()) & 
            (df['perf_3y_annualized'] > 0)
        ].copy()
        
        # Prendre les top N par performance
        df_top = df_valid.nlargest(self.top_n_perf, 'perf_3y_annualized').copy()
        
        # Ajouter le rang performance
        df_top['rank_perf_3y'] = range(1, len(df_top) + 1)
        
        logger.info(f"🎯 Selected top {len(df_top)} funds by 3Y performance:")
        for _, row in df_top.iterrows():
            logger.info(
                f"  #{row['rank_perf_3y']}: {row['fund_name']}: "
                f"{row['perf_3y_annualized']:.2f}% (AUM: ${row['aum_billions']:.1f}B)"
            )
        
        # Sauvegarder
        save_df(df_top, RAW_HF_DIR / "funds_top10_aum_and_perf.csv")
        
        return df_top
    
    @track_performance("hedgefollow.scrape_fund_holdings")
    def scrape_fund_holdings(self, fund_id: str, fund_url: str) -> pd.DataFrame:
        """
        Scrape TOUTES les holdings d'un fond, puis filtre top 30.
        
        Args:
            fund_id: Identifiant du fond
            fund_url: URL de la page du fond
            
        Returns:
            DataFrame avec les top 30 holdings
        """
        if not fund_url:
            logger.warning(f"No URL for fund {fund_id}, skipping holdings")
            return pd.DataFrame()
        
        logger.info(f"📊 Scraping ALL holdings for {fund_id}...")
        
        try:
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
            
            # Parser TOUTES les holdings
            holdings_data = []
            rows = holdings_table.find_all('tr')[1:]  # Skip header
            
            for idx, row in enumerate(rows, start=1):
                try:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 3:
                        continue
                    
                    # Ticker et nom
                    ticker_cell = cols[0]
                    ticker_link = ticker_cell.find('a')
                    
                    if ticker_link:
                        ticker = clean_text(ticker_link.text).upper()
                    else:
                        ticker = clean_text(ticker_cell.text).upper()
                    
                    company_name = clean_text(cols[1].text) if len(cols) > 1 else ''
                    
                    # % du portfolio - CRITIQUE pour le tri
                    pct_portfolio = parse_float(cols[2].text) if len(cols) > 2 else None
                    
                    # Shares et valeur
                    shares_owned = self._parse_shares(cols[3].text) if len(cols) > 3 else None
                    value_owned = self._parse_value(cols[4].text) if len(cols) > 4 else None
                    
                    # Activité récente
                    latest_activity = self._parse_activity(cols[5].text) if len(cols) > 5 else None
                    
                    holding = {
                        'fund_id': fund_id,
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
            
            if df_holdings.empty:
                logger.warning(f"No holdings parsed for {fund_id}")
                return df_holdings
            
            # TRIER PAR % PORTFOLIO et garder TOP 30
            df_holdings = df_holdings.sort_values('portfolio_pct', ascending=False, na_position='last')
            df_holdings = df_holdings.head(self.top_n_holdings).copy()
            df_holdings['position'] = range(1, len(df_holdings) + 1)
            
            logger.info(f"  → Kept top {len(df_holdings)} holdings (from {len(holdings_data)} total)")
            
            return df_holdings
            
        except Exception as e:
            logger.error(f"Failed to scrape holdings for {fund_id}: {e}")
            return pd.DataFrame()
    
    def scrape_all_holdings(self, funds_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Scrape les holdings pour tous les fonds du DataFrame.
        
        Args:
            funds_df: DataFrame des fonds
            
        Returns:
            DataFrame consolidé de toutes les holdings
        """
        if funds_df is None or funds_df.empty:
            raise ValueError("No funds data provided")
        
        all_holdings = []
        
        for idx, fund in funds_df.iterrows():
            fund_id = fund['fund_id']
            fund_url = fund['fund_url']
            
            # Scraper les holdings
            holdings = self.scrape_fund_holdings(fund_id, fund_url)
            
            if not holdings.empty:
                # Ajouter infos du fond
                holdings['fund_name'] = fund['fund_name']
                holdings['fund_perf_3y'] = fund['perf_3y_annualized']
                holdings['fund_aum_billions'] = fund['aum_billions']
                holdings['fund_rank_aum'] = fund.get('rank_aum', None)
                holdings['fund_rank_perf'] = fund.get('rank_perf_3y', None)
                
                all_holdings.append(holdings)
            
            # Pause entre fonds
            time.sleep(random.uniform(3, 5))
        
        # Consolider
        if all_holdings:
            df_all = pd.concat(all_holdings, ignore_index=True)
            
            # Sauvegarder avec date
            filename = get_dated_filename("holdings_top10funds_30each")
            save_df(df_all, RAW_HF_DIR / filename)
            
            self.holdings_data = df_all
            logger.info(f"✅ Total holdings: {len(df_all)} positions from {len(all_holdings)} funds")
            
            return df_all
        else:
            logger.warning("No holdings data collected")
            return pd.DataFrame()
    
    def build_smart_universe(self, holdings_df: pd.DataFrame = None) -> pd.Series:
        """
        Construit l'univers de tickers Smart Money.
        
        Args:
            holdings_df: DataFrame des holdings
            
        Returns:
            Series des tickers uniques
        """
        if holdings_df is None:
            holdings_df = self.holdings_data
        
        if holdings_df.empty:
            raise ValueError("No holdings data to build universe")
        
        # Extraire les tickers uniques
        tickers = holdings_df['ticker'].dropna().str.upper().unique()
        self.smart_universe = set(tickers)
        
        # Compter la fréquence
        ticker_counts = holdings_df['ticker'].value_counts()
        
        logger.info(f"🌎 Smart Money Universe built:")
        logger.info(f"  • Total unique tickers: {len(self.smart_universe)}")
        logger.info(f"  • Average funds per ticker: {ticker_counts.mean():.1f}")
        
        # Top tickers
        logger.info("  • Most popular tickers:")
        for ticker, count in ticker_counts.head(10).items():
            pct = (count / len(funds_df) * 100) if 'funds_df' in locals() else count * 10
            logger.info(f"    - {ticker}: {count} funds ({pct:.0f}%)")
        
        # Sauvegarder l'univers
        universe_df = pd.DataFrame({
            'ticker': sorted(list(self.smart_universe)),
            'count_in_funds': [ticker_counts.get(t, 0) for t in sorted(list(self.smart_universe))]
        })
        save_df(universe_df, RAW_HF_DIR.parent / "processed" / "smart_universe_tickers.csv")
        
        return pd.Series(sorted(list(self.smart_universe)), name='ticker')
    
    def run_full_pipeline(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        """
        Execute le pipeline complet Smart Money.
        
        Returns:
            Tuple (DataFrame funds, DataFrame holdings, Series universe)
        """
        logger.info("=" * 60)
        logger.info("🚀 Starting Smart Money Pipeline")
        logger.info("=" * 60)
        
        # Étape 1: Scraper TOUS les fonds
        df_all_funds = self.scrape_all_funds(max_funds=100)
        metrics.record_metric("funds_scraped_total", len(df_all_funds))
        
        # Étape 2: Filtrer top 20 par AUM
        df_top_aum = self.filter_top_by_aum(df_all_funds)
        metrics.record_metric("funds_top_aum", len(df_top_aum))
        
        # Étape 3: Filtrer top 10 par performance 3Y
        df_top_funds = self.filter_top_performers(df_top_aum)
        metrics.record_metric("funds_top_perf", len(df_top_funds))
        
        # Étape 4: Scraper holdings (30 par fond)
        df_holdings = self.scrape_all_holdings(df_top_funds)
        metrics.record_metric("holdings_scraped", len(df_holdings))
        
        # Étape 5: Construire l'univers Smart Money
        universe = self.build_smart_universe(df_holdings)
        metrics.record_metric("universe_tickers", len(universe))
        
        # Analyser
        self._analyze_results(df_top_funds, df_holdings, universe)
        
        logger.info("=" * 60)
        logger.info("✅ Smart Money Pipeline completed!")
        logger.info("=" * 60)
        
        return df_top_funds, df_holdings, universe
    
    # === Méthodes Helper (inchangées) ===
    
    def _parse_performance(self, text: str) -> Optional[float]:
        """Parse la performance avec gestion des formats variés."""
        if not text:
            return None
        
        text = text.strip()
        
        # Chercher performance annualisée entre parenthèses
        ann_match = re.search(r'\(([+-]?\d+\.?\d*)%?\s*Ann', text)
        if ann_match:
            return parse_float(ann_match.group(1))
        
        # Sinon première valeur %
        pct_match = re.search(r'([+-]?\d+\.?\d*)%', text)
        if pct_match:
            perf_3y = parse_float(pct_match.group(1))
            if perf_3y and abs(perf_3y) > 50:  # Probablement total 3Y
                # Conversion approximative annualisée
                return ((1 + perf_3y/100) ** (1/3) - 1) * 100
            return perf_3y
        
        return parse_float(text)
    
    def _parse_aum(self, text: str) -> Optional[float]:
        """Parse AUM avec gestion des suffixes (T/B/M)."""
        if not text:
            return None
        
        text = text.strip().replace('$', '').replace(',', '')
        
        match = re.match(r'([0-9.]+)\s*([TBM])?', text, re.I)
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
            
            return value * 1e9
        
        return parse_float(text)
    
    def _parse_shares(self, text: str) -> Optional[float]:
        """Parse nombre de shares."""
        if not text:
            return None
        
        text = text.strip().replace(',', '')
        
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
        """Parse valeur monétaire."""
        if not text:
            return None
        
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
            
            if value > 1000:
                return value * 1e6
            
            return value * 1e9
        
        return parse_float(text)
    
    def _parse_activity(self, text: str) -> Optional[float]:
        """Parse activité récente."""
        if not text:
            return None
        
        match = re.search(r'([+-]?\d+\.?\d*)%', text)
        if match:
            return parse_float(match.group(1))
        
        return None
    
    def _extract_rating(self, row) -> Optional[float]:
        """Extrait le rating."""
        stars = row.find_all(class_=re.compile(r'star|rating'))
        if stars:
            full_stars = len([s for s in stars if 'full' in str(s) or '★' in str(s)])
            return float(full_stars)
        return None
    
    def _analyze_results(self, df_funds: pd.DataFrame, df_holdings: pd.DataFrame, universe: pd.Series):
        """Analyse et affiche les statistiques."""
        logger.info("\n📊 === ANALYSE SMART MONEY ===")
        
        # Stats fonds
        logger.info("\n🏦 Top Funds (AUM + Performance):")
        logger.info(f"  • Nombre de fonds: {len(df_funds)}")
        logger.info(f"  • Performance moyenne 3Y: {df_funds['perf_3y_annualized'].mean():.2f}%")
        logger.info(f"  • AUM total: ${df_funds['aum_billions'].sum():.1f}B")
        logger.info(f"  • AUM moyen: ${df_funds['aum_billions'].mean():.1f}B")
        
        # Stats holdings
        if not df_holdings.empty:
            logger.info("\n📈 Holdings Analysis:")
            logger.info(f"  • Total positions: {len(df_holdings)}")
            logger.info(f"  • Positions par fond: {len(df_holdings) / len(df_funds):.0f}")
            logger.info(f"  • Concentration moyenne top 30: {df_holdings.groupby('fund_id')['portfolio_pct'].sum().mean():.1f}%")
        
        # Stats univers
        logger.info(f"\n🌍 Smart Universe:")
        logger.info(f"  • Tickers uniques: {len(universe)}")
        logger.info(f"  • Provenant de {len(df_funds)} fonds élite")


if __name__ == "__main__":
    # Test du nouveau pipeline
    logger.info("🚀 Smart Money Pipeline Test")
    
    pipeline = HedgeFollowSmartMoneyPipeline(
        top_n_aum=20,      # 20 plus gros AUM
        top_n_perf=10,     # 10 meilleurs performers
        top_n_holdings=30  # 30 holdings par fond
    )
    
    try:
        df_funds, df_holdings, universe = pipeline.run_full_pipeline()
        
        print("\n✅ Pipeline Smart Money terminé!")
        print(f"  - Fonds élite: {len(df_funds)}")
        print(f"  - Holdings totales: {len(df_holdings)}")
        print(f"  - Univers tickers: {len(universe)}")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise
