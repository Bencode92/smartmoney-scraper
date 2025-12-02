"""SmartMoney Engine Base - Tronc commun pour v2.2 et v2.3

Contient les méthodes partagées:
- load_data(): Chargement des données JSON
- enrich() / enrich_from_history(): Enrichissement API ou historique
- clean_universe(): Nettoyage de l'univers
- optimize(): Optimisation HRP
- export(): Export JSON/CSV

Les engines spécifiques (v2.2, v2.3) héritent de cette base
et implémentent leur propre:
- calculate_scores()
- apply_filters()
"""
import json
import math
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from typing import Dict, Optional, Tuple
from abc import ABC, abstractmethod
import requests
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import (
    DATA_RAW, TWELVE_DATA_KEY, TWELVE_DATA_BASE,
    TWELVE_DATA_RATE_LIMIT, CONSTRAINTS
)

# Import des nouveaux paramètres de config (avec fallback)
try:
    from config import SCORING, CORRELATION, TWELVE_DATA_TICKER_PAUSE
except ImportError:
    SCORING = {
        "use_zscore": True,
        "sector_neutral_quality": True,
        "smart_money_dedup": True,
    }
    CORRELATION = {
        "use_real_correlation": True,
        "lookback_days": 252,
        "shrinkage": 0.2,
        "fallback_intra_sector": 0.7,
        "fallback_inter_sector": 0.4,
    }
    TWELVE_DATA_TICKER_PAUSE = 3


# === CUSTOM JSON ENCODER ===

class NaNSafeEncoder(json.JSONEncoder):
    """Encode NaN et Infinity comme null pour JSON valide."""
    def default(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
        return super().default(obj)
    
    def encode(self, obj):
        return super().encode(self._clean(obj))
    
    def _clean(self, obj):
        if isinstance(obj, dict):
            return {k: self._clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean(v) for v in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
        return obj


# === DÉCORATEUR RETRY AVEC BACKOFF ===

def with_credit_retry(max_retries: int = 3, base_wait: int = 65):
    """
    Gère automatiquement les erreurs 'You have run out of API credits...'
    avec retry + backoff exponentiel.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, symbol: str, *args, **kwargs):
            for attempt in range(max_retries + 1):
                result = func(self, symbol, *args, **kwargs)

                if result or attempt == max_retries:
                    return result

                if getattr(self, "_last_api_error", None) and "API credits" in self._last_api_error:
                    wait_time = base_wait * (1.5 ** attempt)
                    print(
                        f"    ⏳ Crédits API épuisés, pause {wait_time:.0f}s "
                        f"(tentative {attempt+1}/{max_retries})..."
                    )
                    time.sleep(wait_time)
                    self._last_api_error = None
                else:
                    return result

            return {}
        return wrapper
    return decorator


class SmartMoneyEngineBase(ABC):
    """Classe de base pour les engines SmartMoney.
    
    Fournit les méthodes communes:
    - Chargement de données
    - Enrichissement (API ou historique)
    - Optimisation HRP
    - Export
    
    Les sous-classes doivent implémenter:
    - calculate_scores()
    - apply_filters()
    """
    
    # Version à surcharger dans les sous-classes
    version = "base"
    
    def __init__(self):
        self.universe = pd.DataFrame()
        self.portfolio = pd.DataFrame()
        self.portfolio_metrics = {}
        self._last_api_call = 0
        self._last_api_error = None
        
        # Cache pour corrélations réelles (utilisé par backtest)
        self._real_correlation = None
        self._returns_history = None
        
        # Contraintes (peuvent être surchargées)
        self.constraints = CONSTRAINTS.copy()
    
    # =========================================================================
    # ABSTRACT METHODS - À implémenter dans les sous-classes
    # =========================================================================
    
    @abstractmethod
    def calculate_scores(self) -> pd.DataFrame:
        """Calcule les scores composites. À implémenter dans v2.2/v2.3."""
        pass
    
    @abstractmethod
    def apply_filters(self) -> pd.DataFrame:
        """Applique les filtres sur l'univers. À implémenter dans v2.2/v2.3."""
        pass
    
    # =========================================================================
    # DATA LOADING
    # =========================================================================
    
    def load_data(self) -> pd.DataFrame:
        """Charge et fusionne toutes les sources JSON"""
        stocks = {}
        
        # Grand Portfolio (Dataroma)
        gp_files = list((DATA_RAW / "dataroma" / "grand-portfolio").glob("*.json"))
        if gp_files:
            latest = max(gp_files, key=lambda x: x.stat().st_mtime)
            with open(latest) as f:
                data = json.load(f)
            for s in data.get("stocks", []):
                symbol = s["symbol"]
                stocks[symbol] = {
                    "symbol": symbol,
                    "company": s.get("company_name", ""),
                    "gp_weight": s.get("portfolio_weight", 0),
                    "gp_buys": s.get("buys_6m", 0),
                    "gp_tier": s.get("buys_tier", "D"),
                    "hold_price": s.get("hold_price", 0),
                    "current_price": s.get("current_price", 0),
                    "low_52w": s.get("low_52w", 0),
                    "high_52w": s.get("high_52w", 0),
                    "pct_above_52w_low": s.get("pct_above_52w_low", 0)
                }
        
        # Insider Trades
        insider_files = list((DATA_RAW / "insider").glob("*.json"))
        if insider_files:
            latest = max(insider_files, key=lambda x: x.stat().st_mtime)
            with open(latest) as f:
                data = json.load(f)
            for trade in data.get("trades", []):
                symbol = trade.get("symbol", trade.get("ticker", ""))
                if not symbol:
                    continue
                if symbol not in stocks:
                    stocks[symbol] = {"symbol": symbol, "company": trade.get("company", "")}
                
                if "insider_buys" not in stocks[symbol]:
                    stocks[symbol]["insider_buys"] = 0
                    stocks[symbol]["insider_sells"] = 0
                    stocks[symbol]["insider_net_value"] = 0
                
                value = trade.get("value", 0)
                if trade.get("transaction_type", "").lower() in ["buy", "p-purchase", "purchase"]:
                    stocks[symbol]["insider_buys"] += 1
                    stocks[symbol]["insider_net_value"] += value
                else:
                    stocks[symbol]["insider_sells"] += 1
                    stocks[symbol]["insider_net_value"] -= value
        
        self.universe = pd.DataFrame(list(stocks.values()))
        
        defaults = {
            "gp_weight": 0, "gp_buys": 0, "gp_tier": "D",
            "hold_price": 0, "current_price": 0,
            "low_52w": 0, "high_52w": 0, "pct_above_52w_low": 0,
            "insider_buys": 0, "insider_sells": 0, "insider_net_value": 0
        }
        for col, default in defaults.items():
            if col not in self.universe.columns:
                self.universe[col] = default
            else:
                self.universe[col] = self.universe[col].fillna(default)
        
        print(f"✅ {len(self.universe)} tickers chargés")
        return self.universe
    
    # =========================================================================
    # TWELVE DATA API
    # =========================================================================
    
    def _rate_limit(self):
        """Respecte le rate limit Twelve Data"""
        elapsed = time.time() - self._last_api_call
        wait = (60 / TWELVE_DATA_RATE_LIMIT) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_api_call = time.time()
    
    def _handle_api_response(self, data: dict, endpoint: str, symbol: str) -> bool:
        if isinstance(data, dict) and "code" in data:
            self._last_api_error = data.get("message", str(data.get("code", "")))
            print(f"    ⚠️ {endpoint} {symbol}: {self._last_api_error}")
            return True
        self._last_api_error = None
        return False
    
    def _fetch_quote(self, symbol: str) -> dict:
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/quote",
                params={"symbol": symbol, "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "code" not in data:
                    return data
        except Exception as e:
            print(f"⚠️ Quote error {symbol}: {e}")
        return {}
    
    def _fetch_profile(self, symbol: str) -> dict:
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/profile",
                params={"symbol": symbol, "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "code" not in data:
                    return data
        except Exception as e:
            print(f"⚠️ Profile error {symbol}: {e}")
        return {}
    
    def _fetch_technicals(self, symbol: str) -> dict:
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/rsi",
                params={"symbol": symbol, "interval": "1day", "time_period": 14, "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "values" in data and len(data["values"]) > 0:
                    return {"rsi": float(data["values"][0]["rsi"])}
        except Exception as e:
            print(f"⚠️ RSI error {symbol}: {e}")
        return {}
    
    def _fetch_time_series(self, symbol: str, outputsize: int = 900) -> list:
        if not TWELVE_DATA_KEY:
            return []
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/time_series",
                params={
                    "symbol": symbol,
                    "interval": "1day",
                    "outputsize": outputsize,
                    "order": "ASC",
                    "adjusted": "true",
                    "apikey": TWELVE_DATA_KEY
                },
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                if "values" in data:
                    return data["values"]
        except Exception as e:
            print(f"⚠️ Time series error {symbol}: {e}")
        return []
    
    @with_credit_retry(max_retries=3, base_wait=65)
    def _fetch_statistics(self, symbol: str) -> dict:
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/statistics",
                params={"symbol": symbol, "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if self._handle_api_response(data, "Statistics", symbol):
                    return {}
                return data
        except Exception as e:
            self._last_api_error = None
            print(f"⚠️ Statistics error {symbol}: {e}")
        return {}
    
    @with_credit_retry(max_retries=3, base_wait=65)
    def _fetch_balance_sheet(self, symbol: str) -> dict:
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/balance_sheet",
                params={"symbol": symbol, "period": "annual", "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if self._handle_api_response(data, "Balance sheet", symbol):
                    return {}
                if "balance_sheet" in data and data["balance_sheet"]:
                    return data["balance_sheet"][0]
        except Exception as e:
            self._last_api_error = None
            print(f"⚠️ Balance sheet error {symbol}: {e}")
        return {}
    
    @with_credit_retry(max_retries=3, base_wait=65)
    def _fetch_income_statement(self, symbol: str) -> dict:
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/income_statement",
                params={"symbol": symbol, "period": "annual", "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if self._handle_api_response(data, "Income statement", symbol):
                    return {}
                if "income_statement" in data and data["income_statement"]:
                    return data["income_statement"][0]
        except Exception as e:
            self._last_api_error = None
            print(f"⚠️ Income statement error {symbol}: {e}")
        return {}
    
    @with_credit_retry(max_retries=3, base_wait=65)
    def _fetch_cash_flow(self, symbol: str) -> dict:
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/cash_flow",
                params={"symbol": symbol, "period": "annual", "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if self._handle_api_response(data, "Cash flow", symbol):
                    return {}
                if "cash_flow" in data and data["cash_flow"]:
                    return data["cash_flow"][0]
        except Exception as e:
            self._last_api_error = None
            print(f"⚠️ Cash flow error {symbol}: {e}")
        return {}
    
    # =========================================================================
    # DATA PROCESSING HELPERS
    # =========================================================================
    
    def _safe_float(self, value) -> float:
        """Convertit en float de manière sécurisée, retourne None pour NaN/Inf"""
        if value is None:
            return None
        try:
            f = float(value)
            if math.isnan(f) or math.isinf(f):
                return None
            return f
        except (ValueError, TypeError):
            return None
    
    def _calculate_perf_vol(self, prices: list) -> dict:
        result = {"perf_3m": None, "perf_ytd": None, "vol_30d": None}
        
        if not prices or len(prices) < 2:
            return result

        try:
            closes = []
            dates = []
            for p in prices:
                c = self._safe_float(p.get("close"))
                d = p.get("datetime", "")[:10]
                if c is not None and d:
                    closes.append(c)
                    dates.append(d)

            if len(closes) < 2:
                return result

            current_price = closes[-1]

            def price_n_days_ago(n: int):
                idx = len(closes) - 1 - n
                if idx >= 0:
                    return closes[idx]
                return None

            price_3m = price_n_days_ago(63)
            if price_3m and price_3m > 0:
                result["perf_3m"] = round((current_price / price_3m - 1) * 100, 2)

            current_year = datetime.now().year
            year_start = f"{current_year}-01-01"

            price_ytd = None
            for c, d in zip(closes, dates):
                if d >= year_start:
                    price_ytd = c
                    break

            if price_ytd and price_ytd > 0 and current_price > 0 and price_ytd != current_price:
                result["perf_ytd"] = round((current_price / price_ytd - 1) * 100, 2)

            if len(closes) >= 30:
                recent = closes[-30:]
                returns = []
                for i in range(1, len(recent)):
                    if recent[i-1] and recent[i]:
                        r = recent[i] / recent[i-1] - 1
                        returns.append(r)
                if returns:
                    vol = np.std(returns) * np.sqrt(252) * 100
                    result["vol_30d"] = round(vol, 2)

        except Exception as e:
            print(f"⚠️ Calc error: {e}")

        return result
    
    def _extract_fundamentals(self, stats: dict, balance: dict, income: dict, cashflow: dict) -> dict:
        """Extract fundamentals from API responses."""
        result = {
            "roe": None, "roa": None, "debt_equity": None, "current_ratio": None,
            "gross_margin": None, "operating_margin": None, "net_margin": None,
            "capex_ratio": None, "fcf": None, "revenue": None, "net_income": None,
            "ebit": None, "total_debt": None, "cash": None, "interest_expense": None,
            "shares_outstanding": None, "total_equity": None
        }
        # Implementation truncated for brevity - see full file
        return result
    
    # =========================================================================
    # ENRICHMENT
    # =========================================================================
    
    def enrich(self, top_n: int = 50) -> pd.DataFrame:
        """Enrichissement via API Twelve Data (mode live)"""
        if self.universe.empty:
            self.load_data()
        # Implementation truncated for brevity
        return self.universe
    
    def enrich_from_history(self, prices_history: pd.DataFrame, fundamentals_cache: Dict[str, dict] = None) -> pd.DataFrame:
        """Enrichit l'univers à partir d'un historique de prix pré-chargé."""
        if self.universe.empty:
            self.load_data()
        # Implementation truncated for brevity
        return self.universe
    
    # =========================================================================
    # CLEANING
    # =========================================================================
    
    def clean_universe(self, strict: bool = False):
        df = self.universe
        
        if not strict:
            mask_bad = df["sector"].eq("Unknown")
        else:
            mask_bad = (
                df["sector"].eq("Unknown") |
                df["revenue"].isna() |
                df["net_income"].isna()
            )
        
        bad_symbols = df.loc[mask_bad, "symbol"].tolist()
        if bad_symbols:
            print(f"⚠️ Exclusion {len(bad_symbols)} tickers: {bad_symbols[:10]}{'...' if len(bad_symbols) > 10 else ''}")
        
        self.universe = df[~mask_bad].reset_index(drop=True)
        print(f"✅ Univers nettoyé: {len(self.universe)} tickers restants")
    
    # =========================================================================
    # HRP OPTIMIZATION
    # =========================================================================
    
    def _get_correlation_matrix(self, returns: pd.DataFrame = None, shrinkage: float = None) -> pd.DataFrame:
        """Calcule la matrice de corrélation."""
        # Implementation truncated for brevity
        return self._get_sector_correlation_fallback()
    
    def _get_sector_correlation_fallback(self) -> pd.DataFrame:
        """Retourne la matrice de corrélation approximée par secteur (fallback)."""
        n = len(self.universe)
        symbols = self.universe["symbol"].tolist()
        sectors = self.universe["sector"].tolist() if "sector" in self.universe.columns else ["Unknown"] * n
        
        intra = CORRELATION.get("fallback_intra_sector", 0.7)
        inter = CORRELATION.get("fallback_inter_sector", 0.4)
        
        corr = np.eye(n)
        for i in range(n):
            for j in range(i+1, n):
                if sectors[i] == sectors[j] and sectors[i] != "Unknown":
                    corr[i, j] = intra
                    corr[j, i] = intra
                else:
                    corr[i, j] = inter
                    corr[j, i] = inter
        
        return pd.DataFrame(corr, index=symbols, columns=symbols)
    
    def _hrp_weights(self, cov: np.ndarray, corr: np.ndarray) -> np.ndarray:
        """Calcule les poids HRP."""
        n = cov.shape[0]
        dist = np.sqrt((1 - corr) / 2)
        np.fill_diagonal(dist, 0)
        
        condensed = squareform(dist, checks=False)
        link = linkage(condensed, method="ward")
        order = leaves_list(link)
        
        weights = np.ones(n)
        clusters = [list(order)]
        
        while clusters:
            cluster = clusters.pop()
            if len(cluster) == 1:
                continue
            
            mid = len(cluster) // 2
            left = cluster[:mid]
            right = cluster[mid:]
            
            var_left = np.mean([cov[i, i] for i in left])
            var_right = np.mean([cov[i, i] for i in right])
            
            total_var = var_left + var_right
            alpha = 1 - var_left / total_var if total_var > 0 else 0.5
            
            for i in left:
                weights[i] *= alpha
            for i in right:
                weights[i] *= (1 - alpha)
            
            if len(left) > 1:
                clusters.append(left)
            if len(right) > 1:
                clusters.append(right)
        
        return weights / weights.sum()
    
    def optimize(self, weights_config: dict = None) -> pd.DataFrame:
        """Optimisation HRP avec tilt par score composite."""
        if "score_composite" not in self.universe.columns:
            self.calculate_scores()
            self.apply_filters()
        
        print("⚙️ Optimisation HRP...")
        
        n = len(self.universe)
        min_pos = self.constraints.get("min_positions", 10)
        max_pos = self.constraints.get("max_positions", 20)
        max_weight = self.constraints.get("max_weight", 0.15)
        
        if n < min_pos:
            print(f"⚠️ Seulement {n} tickers, minimum {min_pos} requis")
        
        if "vol_30d" in self.universe.columns:
            vols = self.universe["vol_30d"].fillna(25).values / 100
        else:
            vols = np.full(n, 0.25)
        
        corr = self._get_correlation_matrix().values
        cov = np.outer(vols, vols) * corr
        
        weights = self._hrp_weights(cov, corr)
        
        # Tilt par score composite
        scores = self.universe["score_composite"].values
        
        if SCORING.get("use_zscore", True):
            alpha = 0.5
            scores_z = (scores - scores.mean()) / (scores.std() or 1)
            score_tilt = np.exp(alpha * scores_z)
        else:
            score_tilt = scores / (scores.mean() or 1)
        
        weights = weights * score_tilt
        weights = weights / weights.sum()
        
        # Appliquer les caps
        weights = np.minimum(weights, max_weight)
        weights = weights / weights.sum()
        
        self.universe["weight"] = weights
        self.portfolio = self.universe.nlargest(max_pos, "weight").copy()
        self.portfolio["weight"] = self.portfolio["weight"] / self.portfolio["weight"].sum()
        self.portfolio["weight"] = self.portfolio["weight"].round(4)
        
        self._calculate_portfolio_metrics()
        
        print(f"✅ Portefeuille: {len(self.portfolio)} positions")
        return self.portfolio
    
    def _calculate_portfolio_metrics(self):
        """Calcule les métriques du portefeuille."""
        df = self.portfolio
        
        perf_3m = (df["weight"] * df["perf_3m"].fillna(0)).sum() if "perf_3m" in df.columns else None
        perf_ytd = (df["weight"] * df["perf_ytd"].fillna(0)).sum() if "perf_ytd" in df.columns else None
        
        if "vol_30d" in df.columns:
            vol = np.sqrt((df["weight"]**2 * (df["vol_30d"].fillna(25)/100)**2).sum()) * 100
        else:
            vol = None
        
        sector_weights = {}
        if "sector" in df.columns:
            for _, row in df.iterrows():
                sector = row.get("sector", "Unknown")
                sector_weights[sector] = sector_weights.get(sector, 0) + row["weight"]
            sector_weights = {k: round(v * 100, 1) for k, v in sector_weights.items()}
        
        self.portfolio_metrics = {
            "positions": len(df),
            "perf_3m": round(perf_3m, 2) if perf_3m else None,
            "perf_ytd": round(perf_ytd, 2) if perf_ytd else None,
            "vol_30d": round(vol, 2) if vol else None,
            "sector_weights": sector_weights,
        }
    
    # =========================================================================
    # EXPORT
    # =========================================================================
    
    def export(self, output_dir: Path) -> dict:
        """Exporte le portefeuille."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        export_cols = [
            "symbol", "company", "sector", "industry", "weight",
            "score_composite", "score_sm", "score_insider", "score_momentum", "score_quality",
            "perf_3m", "perf_ytd", "vol_30d"
        ]
        
        # Ajouter colonnes v2.3 si présentes
        v23_cols = ["score_value", "score_quality_v23", "score_risk", "buffett_score"]
        export_cols.extend([c for c in v23_cols if c in self.portfolio.columns])
        
        cols = [c for c in export_cols if c in self.portfolio.columns]
        df = self.portfolio[cols].copy()
        df = df.where(pd.notnull(df), None)
        
        result = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "date": today,
                "positions": len(df),
                "total_weight": round(df["weight"].sum(), 4),
                "engine_version": self.version,
            },
            "metrics": self.portfolio_metrics,
            "portfolio": df.to_dict(orient="records")
        }
        
        # Export JSON
        json_path = output_dir / "portfolio.json"
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2, cls=NaNSafeEncoder, default=str)
        
        # Export CSV
        csv_path = output_dir / "portfolio.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"📁 Exporté: portfolio.json, portfolio.csv")
        return result
