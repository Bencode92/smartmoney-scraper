"""
Scraper pour HedgeFollow Insider Trading Tracker.
Récupère les transactions insiders significatives et filtre sur l'univers Smart Money.
"""
import re
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import pandas as pd
from loguru import logger

from src.config import HEDGEFOLLOW_BASE_URL, RAW_HF_DIR
from src.utils.http import fetch_html
from src.utils.parsing import make_soup, parse_float, clean_text
from src.utils.io import save_df, get_dated_filename
from src.utils.monitoring import track_performance, metrics


class InsiderTradingTracker:
    """Scraper pour l'Insider Trading Tracker de HedgeFollow."""
    
    BASE_URL = "https://hedgefollow.com"
    INSIDER_URL = f"{BASE_URL}/insiders.php"
    
    # Rôles significatifs à garder
    SIGNIFICANT_ROLES = {
        'CEO', 'CFO', 'COO', 'CTO', 'President', 'Chairman',
        'Director', '10% Owner', 'Officer', 'EVP', 'SVP'
    }
    
    def __init__(self, min_value_musd: float = 5.0):
        """
        Initialise le tracker.
        
        Args:
            min_value_musd: Valeur minimum de transaction en millions USD
        """
        self.min_value_musd = min_value_musd
        self.insiders_data = pd.DataFrame()
        
    @track_performance("hedgefollow.scrape_insider_trades")
    def scrape_insider_trades(self, timeframe: str = "1 Week") -> pd.DataFrame:
        """
        Scrape tous les trades insiders récents.
        
        Args:
            timeframe: Période ("1 Week", "1 Month", "3 Months")
            
        Returns:
            DataFrame avec tous les trades insiders
        """
        logger.info(f"🕵️ Scraping Insider Trading Tracker (timeframe: {timeframe})...")
        
        try:
            # Construire l'URL avec paramètres
            url_params = {
                "1 Week": "period=1w",
                "1 Month": "period=1m",
                "3 Months": "period=3m"
            }
            
            url = self.INSIDER_URL
            if timeframe in url_params:
                url += f"?{url_params[timeframe]}"
            
            html = fetch_html(url, use_smart_session=True)
            soup = make_soup(html)
            
            # Trouver le tableau des insiders
            table = None
            for selector in ['table.insiders', 'table#insider-trades', 'table[data-type="insiders"]', 'table']:
                tables = soup.select(selector)
                for t in tables:
                    headers = [th.text.strip().lower() for th in t.find_all('th')]
                    if any('insider' in h or 'ticker' in h for h in headers):
                        table = t
                        logger.debug(f"✅ Found insider table with selector: {selector}")
                        break
                if table:
                    break
            
            if not table:
                logger.warning("Cannot find insider trading table")
                return pd.DataFrame()
            
            # Parser toutes les lignes
            rows = table.find_all('tr')[1:]  # Skip header
            trades_data = []
            
            for idx, row in enumerate(rows, start=1):
                try:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 5:
                        continue
                    
                    # Ticker
                    ticker_cell = cols[0]
                    ticker_link = ticker_cell.find('a')
                    ticker = clean_text(ticker_link.text if ticker_link else ticker_cell.text).upper()
                    
                    # Insider Name & Role
                    insider_cell = cols[1]
                    insider_text = clean_text(insider_cell.text)
                    
                    # Essayer d'extraire nom et rôle
                    insider_name = insider_text
                    role = ""
                    
                    # Pattern: "Name (Role)" ou "Name - Role"
                    role_match = re.search(r'[(\-]\s*([^)]+)\s*[)\-]?$', insider_text)
                    if role_match:
                        role = role_match.group(1).strip()
                        insider_name = insider_text[:role_match.start()].strip()
                    
                    # Type de transaction (Buy/Sell/Option Exercise)
                    trade_type = clean_text(cols[2].text) if len(cols) > 2 else ""
                    
                    # Nombre de shares
                    shares_text = cols[3].text if len(cols) > 3 else ""
                    shares_traded = self._parse_shares_number(shares_text)
                    
                    # Prix moyen
                    avg_price_text = cols[4].text if len(cols) > 4 else ""
                    avg_price = parse_float(avg_price_text.replace('$', '').replace(',', ''))
                    
                    # Valeur de la transaction
                    value_text = cols[5].text if len(cols) > 5 else ""
                    transaction_value = self._parse_transaction_value(value_text)
                    
                    # Si pas de valeur, calculer
                    if not transaction_value and shares_traded and avg_price:
                        transaction_value = shares_traded * avg_price
                    
                    # Shares détenues après
                    shares_owned_text = cols[6].text if len(cols) > 6 else ""
                    shares_owned_after = self._parse_shares_number(shares_owned_text)
                    
                    # Date de transaction
                    trade_date_text = cols[7].text if len(cols) > 7 else ""
                    trade_date = self._parse_date(trade_date_text)
                    
                    # Date de filing
                    filed_date_text = cols[8].text if len(cols) > 8 else ""
                    filed_date = self._parse_date(filed_date_text)
                    
                    trade_data = {
                        'ticker': ticker,
                        'insider_name': insider_name,
                        'role': role,
                        'trade_type': trade_type,
                        'shares_traded': shares_traded,
                        'avg_price': avg_price,
                        'transaction_value_usd': transaction_value,
                        'transaction_value_millions': transaction_value / 1e6 if transaction_value else None,
                        'shares_owned_after': shares_owned_after,
                        'trade_date': trade_date,
                        'filed_date': filed_date,
                        'is_significant_role': self._is_significant_role(role),
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    trades_data.append(trade_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing insider row {idx}: {e}")
                    continue
            
            df = pd.DataFrame(trades_data)
            
            if df.empty:
                logger.warning("No insider trades parsed")
                return df
            
            # Filtrer par valeur minimum
            df_filtered = df[
                (df['transaction_value_millions'].notna()) &
                (df['transaction_value_millions'] >= self.min_value_musd)
            ].copy()
            
            logger.info(f"✅ Scraped {len(df)} insider trades, {len(df_filtered)} above ${self.min_value_musd}M")
            
            # Sauvegarder données brutes
            filename = get_dated_filename(f"insiders_raw_{timeframe.replace(' ', '_').lower()}")
            save_df(df_filtered, RAW_HF_DIR / filename)
            
            self.insiders_data = df_filtered
            
            return df_filtered
            
        except Exception as e:
            logger.error(f"Failed to scrape insider trades: {e}")
            return pd.DataFrame()
    
    def filter_by_universe(self, universe: Set[str], df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Filtre les trades insiders sur l'univers Smart Money.
        
        Args:
            universe: Set de tickers de l'univers
            df: DataFrame des trades (utilise self.insiders_data si None)
            
        Returns:
            DataFrame filtré
        """
        if df is None:
            df = self.insiders_data
        
        if df.empty:
            logger.warning("No insider data to filter")
            return df
        
        # Normaliser tickers
        df['ticker'] = df['ticker'].str.upper()
        
        # Filtrer sur univers
        df_smart = df[df['ticker'].isin(universe)].copy()
        
        # Filtrer sur rôles significatifs
        df_smart_significant = df_smart[df_smart['is_significant_role']].copy()
        
        logger.info(f"📊 Insider filtering results:")
        logger.info(f"  • Total trades: {len(df)}")
        logger.info(f"  • In Smart Universe: {len(df_smart)}")
        logger.info(f"  • With significant roles: {len(df_smart_significant)}")
        
        # Stats par type
        if not df_smart_significant.empty:
            by_type = df_smart_significant['trade_type'].value_counts()
            logger.info("  • By trade type:")
            for trade_type, count in by_type.items():
                logger.info(f"    - {trade_type}: {count}")
        
        # Sauvegarder
        save_df(
            df_smart_significant,
            RAW_HF_DIR.parent / "processed" / "insiders_smart_universe.csv"
        )
        
        return df_smart_significant
    
    def get_insider_signals(self, lookback_days: int = 7) -> pd.DataFrame:
        """
        Récupère les signaux insiders récents les plus significatifs.
        
        Args:
            lookback_days: Nombre de jours en arrière
            
        Returns:
            DataFrame des signaux
        """
        if self.insiders_data.empty:
            logger.warning("No insider data available")
            return pd.DataFrame()
        
        df = self.insiders_data.copy()
        
        # Filtrer par date
        if 'trade_date' in df.columns:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')
            df = df[df['trade_date'] >= cutoff_date]
        
        # Focus sur les achats (signaux positifs)
        buys = df[df['trade_type'].str.contains('Buy', case=False, na=False)]
        
        # Agrégér par ticker
        if not buys.empty:
            signals = buys.groupby('ticker').agg({
                'transaction_value_millions': 'sum',
                'insider_name': 'count',
                'role': lambda x: ', '.join(x.unique()[:3])
            }).rename(columns={
                'transaction_value_millions': 'total_bought_millions',
                'insider_name': 'num_insiders',
                'role': 'top_roles'
            })
            
            signals = signals.sort_values('total_bought_millions', ascending=False)
            
            logger.info(f"🎯 Top Insider Buy Signals (last {lookback_days} days):")
            for ticker, row in signals.head(10).iterrows():
                logger.info(
                    f"  • {ticker}: ${row['total_bought_millions']:.1f}M by "
                    f"{row['num_insiders']} insiders ({row['top_roles'][:30]}...)"
                )
            
            return signals
        
        return pd.DataFrame()
    
    # === Méthodes Helper ===
    
    def _parse_shares_number(self, text: str) -> Optional[float]:
        """Parse le nombre de shares (peut être en K, M, B)."""
        if not text:
            return None
        
        text = text.strip().replace(',', '')
        
        # Pattern: 1.5M, 250K, etc.
        match = re.match(r'([+-]?\d+\.?\d*)\s*([KMB])?', text, re.I)
        if match:
            value = float(match.group(1))
            suffix = match.group(2)
            
            if suffix:
                suffix = suffix.upper()
                if suffix == 'K':
                    return value * 1e3
                elif suffix == 'M':
                    return value * 1e6
                elif suffix == 'B':
                    return value * 1e9
            
            return value
        
        return parse_float(text)
    
    def _parse_transaction_value(self, text: str) -> Optional[float]:
        """Parse la valeur de transaction en USD."""
        if not text:
            return None
        
        text = text.strip().replace('$', '').replace(',', '')
        
        # Pattern: $5.2M, $150K
        match = re.match(r'([0-9.]+)\s*([KMB])?', text, re.I)
        if match:
            value = float(match.group(1))
            suffix = match.group(2)
            
            if suffix:
                suffix = suffix.upper()
                if suffix == 'K':
                    return value * 1e3
                elif suffix == 'M':
                    return value * 1e6
                elif suffix == 'B':
                    return value * 1e9
            
            return value
        
        return parse_float(text)
    
    def _parse_date(self, text: str) -> Optional[str]:
        """Parse une date au format ISO."""
        if not text:
            return None
        
        text = text.strip()
        
        # Formats possibles: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD
        for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue
        
        return text  # Retourner tel quel si pas parsable
    
    def _is_significant_role(self, role: str) -> bool:
        """Vérifie si le rôle est significatif."""
        if not role:
            return False
        
        role_upper = role.upper()
        
        # Check exact matches
        for sig_role in self.SIGNIFICANT_ROLES:
            if sig_role.upper() in role_upper:
                return True
        
        # Check patterns
        if any(x in role_upper for x in ['CHIEF', 'PRESIDENT', 'DIRECTOR', 'OWNER', 'OFFICER']):
            return True
        
        return False


if __name__ == "__main__":
    # Test du scraper
    from pathlib import Path
    
    logger.info("🕵️ Testing Insider Trading Tracker")
    
    # Créer le tracker
    tracker = InsiderTradingTracker(min_value_musd=5.0)
    
    # Scraper les trades
    df_insiders = tracker.scrape_insider_trades(timeframe="1 Week")
    
    if not df_insiders.empty:
        print(f"\n✅ Scraped {len(df_insiders)} insider trades")
        print("\nTop 5 trades by value:")
        print(df_insiders.nlargest(5, 'transaction_value_millions')[
            ['ticker', 'insider_name', 'role', 'trade_type', 'transaction_value_millions']
        ])
        
        # Charger l'univers Smart Money si disponible
        universe_file = Path("data/processed/smart_universe_tickers.csv")
        if universe_file.exists():
            universe_df = pd.read_csv(universe_file)
            universe_set = set(universe_df['ticker'].str.upper())
            
            # Filtrer
            df_filtered = tracker.filter_by_universe(universe_set, df_insiders)
            print(f"\n📊 Filtered to {len(df_filtered)} trades in Smart Universe")
            
            # Signaux
            signals = tracker.get_insider_signals(lookback_days=7)
            if not signals.empty:
                print("\n🎯 Top Buy Signals:")
                print(signals.head())
        else:
            print("\n⚠️ No Smart Universe file found, run smart_money_pipeline.py first")
