"""
Scraper pour HedgeFollow Hedge Fund Tracker.
Récupère les derniers trades des hedge funds et filtre sur l'univers Smart Money.
"""
import re
import time
import random
from datetime import datetime
from typing import List, Dict, Optional, Set
import pandas as pd
from loguru import logger

from src.config import HEDGEFOLLOW_BASE_URL, RAW_HF_DIR
from src.utils.http import fetch_html
from src.utils.parsing import make_soup, parse_float, clean_text
from src.utils.io import save_df, get_dated_filename
from src.utils.monitoring import track_performance, metrics


class HedgeFundTracker:
    """Scraper pour le Hedge Fund Tracker de HedgeFollow."""
    
    BASE_URL = "https://hedgefollow.com"
    TRACKER_URL = f"{BASE_URL}/tracker.php"
    
    # Types de trades significatifs
    SIGNIFICANT_TRADES = {'Buy', 'New Position', 'Add', 'Increased'}
    
    def __init__(self, min_value_musd: float = 5.0):
        """
        Initialise le tracker.
        
        Args:
            min_value_musd: Valeur minimum de trade en millions USD
        """
        self.min_value_musd = min_value_musd
        self.trades_data = pd.DataFrame()
        
    @track_performance("hedgefollow.scrape_hf_trades")
    def scrape_hedgefund_trades(self, filter_type: str = "all") -> pd.DataFrame:
        """
        Scrape les trades récents des hedge funds.
        
        Args:
            filter_type: Type de filtre ("all", "buys", "sells", "new")
            
        Returns:
            DataFrame avec les trades
        """
        logger.info(f"📈 Scraping Hedge Fund Tracker (filter: {filter_type})...")
        
        try:
            # Construire l'URL avec paramètres
            url = self.TRACKER_URL
            if filter_type != "all":
                url += f"?type={filter_type}"
            
            html = fetch_html(url, use_smart_session=True)
            soup = make_soup(html)
            
            # Trouver le tableau des trades
            table = None
            for selector in ['table.tracker', 'table#hf-tracker', 'table[data-type="tracker"]', 'table']:
                tables = soup.select(selector)
                for t in tables:
                    headers = [th.text.strip().lower() for th in t.find_all('th')]
                    if any('manager' in h or 'fund' in h or 'ticker' in h for h in headers):
                        table = t
                        logger.debug(f"✅ Found HF tracker table with selector: {selector}")
                        break
                if table:
                    break
            
            if not table:
                logger.warning("Cannot find hedge fund tracker table")
                return pd.DataFrame()
            
            # Parser toutes les lignes
            rows = table.find_all('tr')[1:]  # Skip header
            trades_data = []
            
            for idx, row in enumerate(rows, start=1):
                try:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 5:
                        continue
                    
                    # Manager/Fund Name
                    manager_cell = cols[0]
                    manager_link = manager_cell.find('a')
                    manager_name = clean_text(manager_link.text if manager_link else manager_cell.text)
                    
                    # Ticker
                    ticker_cell = cols[1]
                    ticker_link = ticker_cell.find('a')
                    ticker = clean_text(ticker_link.text if ticker_link else ticker_cell.text).upper()
                    
                    # Company name (optionnel)
                    company_name = clean_text(cols[2].text) if len(cols) > 2 else ""
                    
                    # Type de trade (Buy/Sell/New/Exit)
                    trade_type = clean_text(cols[3].text) if len(cols) > 3 else ""
                    
                    # % du portfolio
                    pct_portfolio_text = cols[4].text if len(cols) > 4 else ""
                    pct_portfolio = parse_float(pct_portfolio_text.replace('%', ''))
                    
                    # Changement en shares
                    shares_change_text = cols[5].text if len(cols) > 5 else ""
                    shares_change = self._parse_shares_change(shares_change_text)
                    
                    # Valeur du trade
                    value_text = cols[6].text if len(cols) > 6 else ""
                    trade_value = self._parse_trade_value(value_text)
                    
                    # Prix moyen
                    avg_price_text = cols[7].text if len(cols) > 7 else ""
                    avg_price = parse_float(avg_price_text.replace('$', '').replace(',', ''))
                    
                    # Date de filing
                    filed_date_text = cols[8].text if len(cols) > 8 else ""
                    filed_date = self._parse_date(filed_date_text)
                    
                    # AUM du fund (pour contexte)
                    aum_text = cols[9].text if len(cols) > 9 else ""
                    fund_aum = self._parse_aum(aum_text)
                    
                    trade_data = {
                        'manager_name': manager_name,
                        'ticker': ticker,
                        'company_name': company_name,
                        'trade_type': trade_type,
                        'portfolio_pct': pct_portfolio,
                        'shares_change': shares_change,
                        'trade_value_usd': trade_value,
                        'trade_value_millions': trade_value / 1e6 if trade_value else None,
                        'avg_price': avg_price,
                        'filed_date': filed_date,
                        'fund_aum_billions': fund_aum / 1e9 if fund_aum else None,
                        'is_bullish_trade': self._is_bullish_trade(trade_type),
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    trades_data.append(trade_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing HF trade row {idx}: {e}")
                    continue
            
            df = pd.DataFrame(trades_data)
            
            if df.empty:
                logger.warning("No HF trades parsed")
                return df
            
            # Filtrer par valeur minimum
            df_filtered = df[
                (df['trade_value_millions'].notna()) &
                (df['trade_value_millions'] >= self.min_value_musd)
            ].copy()
            
            logger.info(f"✅ Scraped {len(df)} HF trades, {len(df_filtered)} above ${self.min_value_musd}M")
            
            # Stats par type
            by_type = df_filtered['trade_type'].value_counts()
            logger.info("  Trade types distribution:")
            for trade_type, count in by_type.head().items():
                logger.info(f"    • {trade_type}: {count}")
            
            # Sauvegarder données brutes
            filename = get_dated_filename(f"hf_trades_raw_{filter_type}")
            save_df(df_filtered, RAW_HF_DIR / filename)
            
            self.trades_data = df_filtered
            
            return df_filtered
            
        except Exception as e:
            logger.error(f"Failed to scrape HF trades: {e}")
            return pd.DataFrame()
    
    def filter_by_universe(self, universe: Set[str], df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Filtre les trades HF sur l'univers Smart Money.
        
        Args:
            universe: Set de tickers de l'univers
            df: DataFrame des trades
            
        Returns:
            DataFrame filtré
        """
        if df is None:
            df = self.trades_data
        
        if df.empty:
            logger.warning("No HF trades data to filter")
            return df
        
        # Normaliser tickers
        df['ticker'] = df['ticker'].str.upper()
        
        # Filtrer sur univers
        df_smart = df[df['ticker'].isin(universe)].copy()
        
        # Focus sur trades bullish
        df_smart_bullish = df_smart[df_smart['is_bullish_trade']].copy()
        
        logger.info(f"📊 HF Trades filtering results:")
        logger.info(f"  • Total trades: {len(df)}")
        logger.info(f"  • In Smart Universe: {len(df_smart)}")
        logger.info(f"  • Bullish trades: {len(df_smart_bullish)}")
        
        # Top managers actifs
        if not df_smart_bullish.empty:
            top_managers = df_smart_bullish['manager_name'].value_counts().head(10)
            logger.info("  • Most active managers:")
            for manager, count in top_managers.items():
                total_value = df_smart_bullish[df_smart_bullish['manager_name'] == manager]['trade_value_millions'].sum()
                logger.info(f"    - {manager}: {count} trades (${total_value:.1f}M)")
        
        # Sauvegarder
        save_df(
            df_smart_bullish,
            RAW_HF_DIR.parent / "processed" / "hf_trades_smart_universe.csv"
        )
        
        return df_smart_bullish
    
    def get_consensus_signals(self, min_funds: int = 3) -> pd.DataFrame:
        """
        Identifie les tickers avec consensus d'achat (plusieurs funds achètent).
        
        Args:
            min_funds: Nombre minimum de funds pour un consensus
            
        Returns:
            DataFrame des signaux consensus
        """
        if self.trades_data.empty:
            logger.warning("No HF trades data available")
            return pd.DataFrame()
        
        # Focus sur trades bullish récents
        df = self.trades_data[self.trades_data['is_bullish_trade']].copy()
        
        if df.empty:
            return pd.DataFrame()
        
        # Agrégér par ticker
        consensus = df.groupby('ticker').agg({
            'manager_name': lambda x: list(x.unique()),
            'trade_value_millions': 'sum',
            'portfolio_pct': 'mean',
            'trade_type': lambda x: x.mode()[0] if not x.empty else ''
        }).rename(columns={
            'manager_name': 'funds_buying',
            'trade_value_millions': 'total_value_millions',
            'portfolio_pct': 'avg_portfolio_pct',
            'trade_type': 'most_common_action'
        })
        
        # Ajouter le nombre de funds
        consensus['num_funds'] = consensus['funds_buying'].apply(len)
        
        # Filtrer par consensus minimum
        consensus = consensus[consensus['num_funds'] >= min_funds]
        
        # Trier par nombre de funds puis valeur
        consensus = consensus.sort_values(
            ['num_funds', 'total_value_millions'],
            ascending=False
        )
        
        # Formater la liste des funds
        consensus['funds_list'] = consensus['funds_buying'].apply(
            lambda x: ', '.join(x[:3]) + (f' +{len(x)-3} more' if len(x) > 3 else '')
        )
        
        if not consensus.empty:
            logger.info(f"🎯 Top Consensus Buy Signals (≥{min_funds} funds):")
            for ticker, row in consensus.head(10).iterrows():
                logger.info(
                    f"  • {ticker}: {row['num_funds']} funds, "
                    f"${row['total_value_millions']:.1f}M total ({row['funds_list']})"
                )
        
        return consensus
    
    def get_smart_money_flow(self) -> Dict[str, pd.DataFrame]:
        """
        Analyse les flux Smart Money (entrées vs sorties).
        
        Returns:
            Dict avec DataFrames 'inflows' et 'outflows'
        """
        if self.trades_data.empty:
            return {'inflows': pd.DataFrame(), 'outflows': pd.DataFrame()}
        
        df = self.trades_data.copy()
        
        # Séparer entrées et sorties
        inflows = df[df['is_bullish_trade']].groupby('ticker').agg({
            'trade_value_millions': 'sum',
            'manager_name': 'count'
        }).rename(columns={
            'trade_value_millions': 'inflow_millions',
            'manager_name': 'num_buyers'
        })
        
        outflows = df[~df['is_bullish_trade']].groupby('ticker').agg({
            'trade_value_millions': 'sum',
            'manager_name': 'count'
        }).rename(columns={
            'trade_value_millions': 'outflow_millions',
            'manager_name': 'num_sellers'
        })
        
        # Calculer le flux net
        flow = pd.merge(
            inflows, outflows,
            left_index=True, right_index=True,
            how='outer'
        ).fillna(0)
        
        flow['net_flow_millions'] = flow['inflow_millions'] - flow['outflow_millions']
        flow['flow_ratio'] = flow['inflow_millions'] / (flow['outflow_millions'] + 1)  # +1 pour éviter division par 0
        
        # Trier par flux net
        flow = flow.sort_values('net_flow_millions', ascending=False)
        
        logger.info("💰 Smart Money Flow Analysis:")
        logger.info("  Top Inflows:")
        for ticker, row in flow.head(5).iterrows():
            if row['net_flow_millions'] > 0:
                logger.info(
                    f"    • {ticker}: +${row['net_flow_millions']:.1f}M net "
                    f"({row['num_buyers']:.0f} buyers vs {row['num_sellers']:.0f} sellers)"
                )
        
        logger.info("  Top Outflows:")
        for ticker, row in flow.tail(5).iterrows():
            if row['net_flow_millions'] < 0:
                logger.info(
                    f"    • {ticker}: -${abs(row['net_flow_millions']):.1f}M net "
                    f"({row['num_sellers']:.0f} sellers vs {row['num_buyers']:.0f} buyers)"
                )
        
        return {
            'all_flows': flow,
            'strong_inflows': flow[flow['net_flow_millions'] > self.min_value_musd * 2],
            'strong_outflows': flow[flow['net_flow_millions'] < -self.min_value_musd * 2]
        }
    
    # === Méthodes Helper ===
    
    def _parse_shares_change(self, text: str) -> Optional[float]:
        """Parse le changement en nombre de shares."""
        if not text:
            return None
        
        text = text.strip().replace(',', '')
        
        # Pattern: +1.5M, -250K, etc.
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
    
    def _parse_trade_value(self, text: str) -> Optional[float]:
        """Parse la valeur du trade en USD."""
        if not text:
            return None
        
        text = text.strip().replace('$', '').replace(',', '')
        
        # Pattern: $5.2M, $1.5B
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
    
    def _parse_aum(self, text: str) -> Optional[float]:
        """Parse l'AUM du fund."""
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
            
            return value * 1e9  # Défaut en milliards
        
        return parse_float(text)
    
    def _parse_date(self, text: str) -> Optional[str]:
        """Parse une date au format ISO."""
        if not text:
            return None
        
        text = text.strip()
        
        # Formats possibles
        for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue
        
        return text
    
    def _is_bullish_trade(self, trade_type: str) -> bool:
        """Détermine si le trade est bullish."""
        if not trade_type:
            return False
        
        trade_upper = trade_type.upper()
        
        # Patterns bullish
        bullish_keywords = ['BUY', 'NEW', 'ADD', 'INCREASE', 'INITIATE', 'ACCUMULATE']
        
        return any(keyword in trade_upper for keyword in bullish_keywords)


if __name__ == "__main__":
    # Test du scraper
    from pathlib import Path
    
    logger.info("📈 Testing Hedge Fund Tracker")
    
    # Créer le tracker
    tracker = HedgeFundTracker(min_value_musd=5.0)
    
    # Scraper les trades
    df_trades = tracker.scrape_hedgefund_trades(filter_type="all")
    
    if not df_trades.empty:
        print(f"\n✅ Scraped {len(df_trades)} HF trades")
        print("\nTop 5 trades by value:")
        print(df_trades.nlargest(5, 'trade_value_millions')[
            ['manager_name', 'ticker', 'trade_type', 'trade_value_millions', 'portfolio_pct']
        ])
        
        # Charger l'univers Smart Money
        universe_file = Path("data/processed/smart_universe_tickers.csv")
        if universe_file.exists():
            universe_df = pd.read_csv(universe_file)
            universe_set = set(universe_df['ticker'].str.upper())
            
            # Filtrer
            df_filtered = tracker.filter_by_universe(universe_set, df_trades)
            print(f"\n📊 Filtered to {len(df_filtered)} trades in Smart Universe")
            
            # Consensus
            consensus = tracker.get_consensus_signals(min_funds=2)
            if not consensus.empty:
                print("\n🎯 Consensus Signals:")
                print(consensus[['num_funds', 'total_value_millions', 'funds_list']].head())
            
            # Flow analysis
            flows = tracker.get_smart_money_flow()
            if not flows['strong_inflows'].empty:
                print("\n💰 Strong Inflows:")
                print(flows['strong_inflows'].head())
        else:
            print("\n⚠️ No Smart Universe file found, run smart_money_pipeline.py first")
