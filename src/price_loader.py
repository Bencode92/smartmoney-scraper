"""SmartMoney v2.4 — Price Data Loader

Charge les données de prix historiques pour le backtest walk-forward.
Sources: Cache local > yfinance > Twelve Data API

Date: Décembre 2025
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TWELVE_DATA_KEY, TWELVE_DATA_BASE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "data" / "prices"
CACHE_EXPIRY_DAYS = 1


class PriceLoader:
    """Charge les prix historiques depuis cache/yfinance/TwelveData."""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._yf_available = self._check_yfinance()
        logger.info(f"PriceLoader init (yfinance={self._yf_available})")
    
    def _check_yfinance(self) -> bool:
        try:
            import yfinance
            return True
        except ImportError:
            return False
    
    def load_prices(
        self,
        symbols: List[str],
        start: str = "2020-01-01",
        end: str = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Charge les prix de clôture ajustés."""
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")
        
        all_prices = {}
        missing_symbols = []
        
        # 1. Cache
        if use_cache:
            for symbol in symbols:
                cached = self._load_from_cache(symbol, start, end)
                if cached is not None:
                    all_prices[symbol] = cached
                else:
                    missing_symbols.append(symbol)
        else:
            missing_symbols = symbols.copy()
        
        # 2. API
        if missing_symbols:
            logger.info(f"Fetching {len(missing_symbols)} symbols...")
            if self._yf_available:
                new_prices = self._load_from_yfinance(missing_symbols, start, end)
            else:
                new_prices = self._load_from_twelvedata(missing_symbols, start, end)
            
            for symbol, prices in new_prices.items():
                if prices is not None and not prices.empty:
                    self._save_to_cache(symbol, prices)
                    all_prices[symbol] = prices
        
        if not all_prices:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_prices)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        mask = (df.index >= start) & (df.index <= end)
        return df[mask]
    
    def _load_from_cache(self, symbol: str, start: str, end: str) -> Optional[pd.Series]:
        cache_file = self.cache_dir / f"{symbol}.csv"
        if not cache_file.exists():
            return None
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime > timedelta(days=CACHE_EXPIRY_DAYS):
            return None
        try:
            df = pd.read_csv(cache_file, parse_dates=["date"], index_col="date")
            if df.index.min().strftime("%Y-%m-%d") > start:
                return None
            return df["close"]
        except Exception:
            return None
    
    def _save_to_cache(self, symbol: str, prices: pd.Series):
        try:
            cache_file = self.cache_dir / f"{symbol}.csv"
            df = pd.DataFrame({"close": prices})
            df.index.name = "date"
            df.to_csv(cache_file)
        except Exception as e:
            logger.warning(f"Cache save error {symbol}: {e}")
    
    def _load_from_yfinance(
        self, symbols: List[str], start: str, end: str
    ) -> Dict[str, pd.Series]:
        try:
            import yfinance as yf
            logger.info(f"yfinance: {symbols[:5]}{'...' if len(symbols) > 5 else ''}")
            data = yf.download(
                symbols, start=start, end=end,
                progress=False, auto_adjust=True
            )
            if data.empty:
                return {}
            if len(symbols) == 1:
                return {symbols[0]: data["Close"]}
            prices = {}
            for symbol in symbols:
                if symbol in data["Close"].columns:
                    prices[symbol] = data["Close"][symbol].dropna()
            return prices
        except Exception as e:
            logger.error(f"yfinance error: {e}")
            return {}
    
    def _load_from_twelvedata(
        self, symbols: List[str], start: str, end: str
    ) -> Dict[str, pd.Series]:
        if not TWELVE_DATA_KEY:
            return {}
        import requests
        import time
        prices = {}
        for symbol in symbols:
            try:
                time.sleep(0.5)
                resp = requests.get(
                    f"{TWELVE_DATA_BASE}/time_series",
                    params={
                        "symbol": symbol,
                        "interval": "1day",
                        "start_date": start,
                        "end_date": end,
                        "apikey": TWELVE_DATA_KEY,
                    },
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if "values" not in data:
                    continue
                df = pd.DataFrame(data["values"])
                df["datetime"] = pd.to_datetime(df["datetime"])
                df = df.set_index("datetime").sort_index()
                prices[symbol] = df["close"].astype(float)
            except Exception:
                pass
        return prices
    
    def load_benchmark(
        self, benchmark: str = "SPY", start: str = "2020-01-01", end: str = None
    ) -> pd.DataFrame:
        """Charge benchmark avec métriques."""
        prices_df = self.load_prices([benchmark], start=start, end=end)
        if prices_df.empty:
            return pd.DataFrame()
        df = pd.DataFrame(index=prices_df.index)
        df["close"] = prices_df[benchmark]
        df["return"] = df["close"].pct_change()
        df["cumulative_return"] = (1 + df["return"]).cumprod() - 1
        df["rolling_vol_30d"] = df["return"].rolling(30).std() * np.sqrt(252)
        df["rolling_max"] = df["close"].cummax()
        df["drawdown"] = (df["close"] - df["rolling_max"]) / df["rolling_max"]
        return df


class PortfolioReturnsCalculator:
    """Calcule les returns d'un portefeuille pondéré."""
    
    def __init__(self, price_loader: PriceLoader = None):
        self.loader = price_loader or PriceLoader()
    
    def calculate(
        self, weights: Dict[str, float], start: str, end: str = None
    ) -> pd.DataFrame:
        """Calcule les returns journaliers du portefeuille."""
        symbols = list(weights.keys())
        prices = self.loader.load_prices(symbols, start=start, end=end)
        if prices.empty:
            return pd.DataFrame()
        
        returns = prices.pct_change()
        total_weight = sum(weights.values())
        norm_weights = {s: w / total_weight for s, w in weights.items()}
        
        portfolio_return = pd.Series(0.0, index=returns.index)
        for symbol, weight in norm_weights.items():
            if symbol in returns.columns:
                portfolio_return += weight * returns[symbol].fillna(0)
        
        df = pd.DataFrame(index=returns.index)
        df["portfolio_return"] = portfolio_return
        df["cumulative_return"] = (1 + portfolio_return).cumprod() - 1
        
        # Benchmark comparison
        benchmark = self.loader.load_benchmark("SPY", start=start, end=end)
        if not benchmark.empty:
            df["benchmark_return"] = benchmark["return"]
            df["benchmark_cumulative"] = benchmark["cumulative_return"]
            df["alpha_daily"] = df["portfolio_return"] - df["benchmark_return"]
        
        return df
    
    def calculate_period_stats(
        self, weights: Dict[str, float], start: str, end: str
    ) -> Dict:
        """Calcule les statistiques sur une période."""
        df = self.calculate(weights, start=start, end=end)
        if df.empty:
            return {"error": "No data"}
        
        pf_returns = df["portfolio_return"].dropna()
        total_return = df["cumulative_return"].iloc[-1] * 100
        n_days = len(pf_returns)
        
        # CAGR
        cagr = ((1 + total_return / 100) ** (252 / n_days) - 1) * 100 if n_days > 0 else 0
        
        # Volatility
        volatility = pf_returns.std() * np.sqrt(252) * 100
        
        # Max Drawdown
        cumulative = (1 + pf_returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min() * 100
        
        # Sharpe (rf = 4.5%)
        rf = 4.5 / 252 / 100
        sharpe = (pf_returns.mean() - rf) / pf_returns.std() * np.sqrt(252) if pf_returns.std() > 0 else 0
        
        # Alpha & Tracking Error
        alpha, tracking_error, info_ratio = 0, 0, 0
        if "benchmark_return" in df.columns:
            bm_return = df["benchmark_cumulative"].iloc[-1] * 100
            alpha = total_return - bm_return
            if "alpha_daily" in df.columns:
                alpha_series = df["alpha_daily"].dropna()
                tracking_error = alpha_series.std() * np.sqrt(252) * 100
                if tracking_error > 0:
                    info_ratio = (alpha_series.mean() * 252 * 100) / tracking_error
        
        return {
            "total_return": round(total_return, 2),
            "cagr": round(cagr, 2),
            "volatility": round(volatility, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "alpha": round(alpha, 2),
            "tracking_error": round(tracking_error, 2),
            "information_ratio": round(info_ratio, 2),
            "n_days": n_days,
        }


if __name__ == "__main__":
    # Test
    loader = PriceLoader()
    prices = loader.load_prices(["SPY", "AAPL"], start="2024-01-01")
    print(f"\nPrix chargés: {len(prices)} jours")
    print(prices.tail())
