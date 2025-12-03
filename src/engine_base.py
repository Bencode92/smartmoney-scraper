"""SmartMoney Engine Base - Tronc commun pour v2.2 et v2.3

Contient les méthodes partagées:
- load_data(): Chargement des données JSON (S&P 500 ou Smart Money)
- enrich() / enrich_from_history(): Enrichissement API ou historique
- clean_universe(): Nettoyage de l'univers
- optimize(): Optimisation HRP
- export(): Export JSON/CSV

Les engines spécifiques (v2.2, v2.3) héritent de cette base
et implémentent leur propre:
- calculate_scores()
- apply_filters()

v2.4: Support mode S&P 500 (503 tickers) avec plan Ultra Twelve Data
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
    TWELVE_DATA_TICKER_PAUSE = 0.5

# Import config S&P 500 avec fallback
try:
    from config import DATA_SP500, ENRICHMENT_MODE
except ImportError:
    DATA_SP500 = Path(__file__).parent.parent / "data" / "sp500.json"
    ENRICHMENT_MODE = "smart_money"


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
    - Chargement de données (S&P 500 ou Smart Money)
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
        self._enrichment_mode = None  # Stocke le mode utilisé
        
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
    # DATA LOADING - SUPPORTE S&P 500 ET SMART MONEY
    # =========================================================================
    
    def load_data(self, mode: str = None) -> pd.DataFrame:
        """Charge les données selon le mode configuré.
        
        Modes:
        - "sp500": Charge les 503 tickers du S&P 500, enrichit avec signaux smart money
        - "smart_money": Mode legacy, charge uniquement les tickers avec signaux
        
        Args:
            mode: Override du mode (sinon utilise ENRICHMENT_MODE de config ou env var)
        """
        # Déterminer le mode (CLI > env var > config)
        mode = mode or os.getenv("ENRICHMENT_MODE", ENRICHMENT_MODE)
        self._enrichment_mode = mode
        
        stocks = {}
        smart_money_data = {}  # Signaux à fusionner
        
        # =====================================================================
        # Étape 1: Charger les signaux Smart Money (toujours, pour enrichir)
        # =====================================================================
        
        # Grand Portfolio (Dataroma)
        gp_files = list((DATA_RAW / "dataroma" / "grand-portfolio").glob("*.json"))
        if gp_files:
            latest = max(gp_files, key=lambda x: x.stat().st_mtime)
            with open(latest) as f:
                data = json.load(f)
            for s in data.get("stocks", []):
                symbol = s["symbol"]
                smart_money_data[symbol] = {
                    "gp_weight": s.get("portfolio_weight", 0),
                    "gp_buys": s.get("buys_6m", 0),
                    "gp_tier": s.get("buys_tier", "D"),
                    "hold_price": s.get("hold_price", 0),
                    "current_price": s.get("current_price", 0),
                    "low_52w": s.get("low_52w", 0),
                    "high_52w": s.get("high_52w", 0),
                    "pct_above_52w_low": s.get("pct_above_52w_low", 0),
                    "company": s.get("company_name", ""),
                }
        
        # Insider Trades
        insider_files = list((DATA_RAW / "insider").glob("*.json"))
        insider_data = {}
        if insider_files:
            latest = max(insider_files, key=lambda x: x.stat().st_mtime)
            with open(latest) as f:
                data = json.load(f)
            for trade in data.get("trades", []):
                symbol = trade.get("symbol", trade.get("ticker", ""))
                if not symbol:
                    continue
                if symbol not in insider_data:
                    insider_data[symbol] = {
                        "insider_buys": 0,
                        "insider_sells": 0,
                        "insider_net_value": 0,
                        "company": trade.get("company", ""),
                    }
                value = trade.get("value", 0)
                if trade.get("transaction_type", "").lower() in ["buy", "p-purchase", "purchase"]:
                    insider_data[symbol]["insider_buys"] += 1
                    insider_data[symbol]["insider_net_value"] += value
                else:
                    insider_data[symbol]["insider_sells"] += 1
                    insider_data[symbol]["insider_net_value"] -= value
        
        # Fusionner insider dans smart_money_data
        for symbol, idata in insider_data.items():
            if symbol in smart_money_data:
                smart_money_data[symbol].update(idata)
            else:
                smart_money_data[symbol] = idata
        
        # =====================================================================
        # Étape 2: Charger l'univers de base selon le mode
        # =====================================================================
        
        if mode == "sp500":
            # Mode S&P 500: charger les 503 tickers
            sp500_path = Path(DATA_SP500) if isinstance(DATA_SP500, str) else DATA_SP500
            if sp500_path.exists():
                with open(sp500_path) as f:
                    sp500_data = json.load(f)
                
                tickers = sp500_data.get("tickers", [])
                print(f"📊 Mode S&P 500: {len(tickers)} tickers")
                
                for symbol in tickers:
                    stocks[symbol] = {
                        "symbol": symbol,
                        "company": "",
                        # Valeurs par défaut
                        "gp_weight": 0, "gp_buys": 0, "gp_tier": "D",
                        "hold_price": 0, "current_price": 0,
                        "low_52w": 0, "high_52w": 0, "pct_above_52w_low": 0,
                        "insider_buys": 0, "insider_sells": 0, "insider_net_value": 0,
                    }
                    # Enrichir avec signaux smart money si disponibles
                    if symbol in smart_money_data:
                        stocks[symbol].update(smart_money_data[symbol])
                
                # Stats smart money
                sm_count = sum(1 for s in stocks.values() if s.get("gp_buys", 0) > 0)
                insider_count = sum(1 for s in stocks.values() if s.get("insider_buys", 0) > 0)
                print(f"   ├─ {sm_count} avec signaux smart money")
                print(f"   └─ {insider_count} avec achats insiders")
            else:
                print(f"⚠️ Fichier S&P 500 non trouvé: {sp500_path}")
                print("   Fallback vers mode smart_money")
                mode = "smart_money"
                self._enrichment_mode = mode
        
        if mode == "smart_money" or not stocks:
            # Mode legacy: uniquement les tickers avec signaux
            stocks = {
                symbol: {
                    "symbol": symbol,
                    **sdata
                }
                for symbol, sdata in smart_money_data.items()
            }
            print(f"📊 Mode Smart Money: {len(stocks)} tickers")
        
        self.universe = pd.DataFrame(list(stocks.values()))
        
        # Colonnes par défaut - INCLUT SECTOR ET INDUSTRY
        defaults = {
            "gp_weight": 0, "gp_buys": 0, "gp_tier": "D",
            "hold_price": 0, "current_price": 0,
            "low_52w": 0, "high_52w": 0, "pct_above_52w_low": 0,
            "insider_buys": 0, "insider_sells": 0, "insider_net_value": 0,
            "sector": "Unknown", "industry": "Unknown"
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
        """Extrait les fondamentaux des réponses API."""
        result = {
            "roe": None, "roa": None, "debt_equity": None, "current_ratio": None,
            "gross_margin": None, "operating_margin": None, "net_margin": None,
            "capex_ratio": None, "fcf": None, "revenue": None, "net_income": None,
            "ebit": None, "total_debt": None, "cash": None, "interest_expense": None,
            "shares_outstanding": None, "total_equity": None
        }

        if income:
            revenue = self._safe_float(
                income.get("sales")
                or income.get("revenue")
                or income.get("total_revenue")
            )
            net_inc = self._safe_float(
                income.get("net_income")
                or income.get("net_income_common_stockholders")
            )
            gross_profit = self._safe_float(income.get("gross_profit"))
            op_income = self._safe_float(
                income.get("operating_income")
                or income.get("operating_income_loss")
            )
            ebit = self._safe_float(income.get("ebit"))
            interest = self._safe_float(income.get("interest_expense"))

            result["revenue"] = revenue
            result["net_income"] = net_inc
            result["ebit"] = ebit or op_income
            result["interest_expense"] = interest

            if revenue and revenue > 0:
                if gross_profit is not None:
                    result["gross_margin"] = round(gross_profit / revenue * 100, 2)
                if op_income is not None:
                    result["operating_margin"] = round(op_income / revenue * 100, 2)
                if net_inc is not None:
                    result["net_margin"] = round(net_inc / revenue * 100, 2)

        if balance:
            assets = balance.get("assets", {}) or {}
            liabilities = balance.get("liabilities", {}) or {}
            equity = balance.get("shareholders_equity", {}) or {}

            total_assets = self._safe_float(
                assets.get("total_assets")
                or balance.get("total_assets")
            )

            total_equity = self._safe_float(
                equity.get("total_shareholders_equity")
                or equity.get("total_stockholders_equity")
                or equity.get("stockholders_equity")
                or equity.get("total_equity")
                or balance.get("total_equity")
            )
            result["total_equity"] = total_equity

            current_assets_block = assets.get("current_assets", {}) or {}
            current_assets = self._safe_float(
                current_assets_block.get("total_current_assets")
                or current_assets_block.get("current_assets")
                or balance.get("total_current_assets")
            )
            
            # Cash
            cash = self._safe_float(
                current_assets_block.get("cash_and_cash_equivalents")
                or current_assets_block.get("cash")
                or balance.get("cash")
            )
            result["cash"] = cash

            current_liab_block = liabilities.get("current_liabilities", {}) or {}
            current_liabilities = self._safe_float(
                current_liab_block.get("total_current_liabilities")
                or current_liab_block.get("current_liabilities")
                or balance.get("total_current_liabilities")
            )

            non_current_liab_block = liabilities.get("non_current_liabilities", {}) or {}
            short_term_debt = self._safe_float(current_liab_block.get("short_term_debt"))
            long_term_debt = self._safe_float(non_current_liab_block.get("long_term_debt"))
            
            total_debt = None
            if short_term_debt is not None or long_term_debt is not None:
                total_debt = (short_term_debt or 0) + (long_term_debt or 0)
            result["total_debt"] = total_debt

            if current_assets is not None and current_liabilities and current_liabilities > 0:
                result["current_ratio"] = round(current_assets / current_liabilities, 2)

            if total_equity and total_equity > 0 and result["net_income"] is not None:
                result["roe"] = round(result["net_income"] / total_equity * 100, 2)

            if total_debt is not None and total_equity and total_equity > 0:
                result["debt_equity"] = round(total_debt / total_equity, 2)

            if total_assets and total_assets > 0 and result["net_income"] is not None:
                result["roa"] = round(result["net_income"] / total_assets * 100, 2)

        if cashflow:
            op = cashflow.get("operating_activities", {}) or {}
            inv = cashflow.get("investing_activities", {}) or {}

            operating_cf = self._safe_float(
                op.get("operating_cash_flow")
                or op.get("net_cash_provided_by_operating_activities")
                or op.get("cash_flow_from_operating_activities")
            )
            capex = self._safe_float(
                inv.get("capital_expenditures")
                or inv.get("capital_expenditure")
            )
            fcf_direct = self._safe_float(
                cashflow.get("free_cash_flow")
                or op.get("free_cash_flow")
                or inv.get("free_cash_flow")
            )

            if capex is not None:
                capex_abs = abs(capex)
                if result["revenue"] and result["revenue"] > 0:
                    result["capex_ratio"] = round(capex_abs / result["revenue"] * 100, 2)

                if fcf_direct is not None:
                    result["fcf"] = fcf_direct
                elif operating_cf is not None:
                    result["fcf"] = round(operating_cf - capex_abs, 0)
            else:
                if fcf_direct is not None:
                    result["fcf"] = fcf_direct

        if stats:
            stats_root = stats.get("statistics") or stats.get("data") or stats
            fin = stats_root.get("financials", {}) or {}
            fin_bs = fin.get("balance_sheet", {}) or {}
            
            # Shares outstanding
            shares = self._safe_float(
                stats_root.get("shares_outstanding")
                or fin.get("shares_outstanding")
            )
            result["shares_outstanding"] = shares

            if result["roe"] is None:
                roe_raw = self._safe_float(
                    fin.get("return_on_equity_ttm")
                    or fin.get("return_on_equity")
                )
                if roe_raw is not None:
                    result["roe"] = round(roe_raw * 100, 2) if -1 < roe_raw < 1 else round(roe_raw, 2)

            if result["roa"] is None:
                roa_raw = self._safe_float(
                    fin.get("return_on_assets_ttm")
                    or fin.get("return_on_assets")
                )
                if roa_raw is not None:
                    result["roa"] = round(roa_raw * 100, 2) if -1 < roa_raw < 1 else round(roa_raw, 2)

            if result["current_ratio"] is None:
                cr = self._safe_float(
                    fin.get("current_ratio")
                    or fin_bs.get("current_ratio")
                    or fin_bs.get("current_ratio_mrq")
                )
                if cr is not None:
                    result["current_ratio"] = round(cr, 2)

            if result["gross_margin"] is None:
                gm = self._safe_float(fin.get("gross_margin"))
                if gm is not None:
                    result["gross_margin"] = round(gm * 100, 2) if -1 < gm < 1 else round(gm, 2)

            if result["operating_margin"] is None:
                om = self._safe_float(fin.get("operating_margin"))
                if om is not None:
                    result["operating_margin"] = round(om * 100, 2) if -1 < om < 1 else round(om, 2)

            if result["net_margin"] is None:
                pm = self._safe_float(
                    fin.get("profit_margin")
                    or fin.get("net_margin")
                )
                if pm is not None:
                    result["net_margin"] = round(pm * 100, 2) if -1 < pm < 1 else round(pm, 2)

        return result
    
    # =========================================================================
    # ENRICHMENT - SUPPORTE S&P 500 ET SMART MONEY
    # =========================================================================
    
    def enrich(self, top_n: int = None) -> pd.DataFrame:
        """Enrichissement via API Twelve Data (mode live)
        
        Args:
            top_n: Nombre de tickers à enrichir. Si None, enrichit tous les tickers
                   chargés (utile pour mode sp500).
        """
        if self.universe.empty:
            self.load_data()
        
        # Déterminer le mode actuel
        mode = self._enrichment_mode or os.getenv("ENRICHMENT_MODE", ENRICHMENT_MODE)
        
        # Sélection des candidats selon le mode
        if mode == "sp500":
            # Mode S&P 500: enrichir tous les tickers (ou top_n si spécifié)
            if top_n is None:
                candidates = self.universe
            else:
                candidates = self.universe.head(top_n)
        else:
            # Mode smart_money: filtrer sur signaux puis limiter à top_n
            filtered = self.universe[
                (self.universe["gp_buys"] >= self.constraints.get("min_buys", 2)) |
                (self.universe["insider_buys"] > 0)
            ]
            if top_n is None:
                top_n = 40  # Défaut pour smart_money
            candidates = filtered.head(top_n)

        # Vérification clé API
        if not TWELVE_DATA_KEY:
            print("⚠️ Pas de clé API Twelve Data (API_TWELVEDATA)")
            print("   Enrichissement ignoré, données brutes uniquement")
            return self.universe

        print(f"📊 Enrichissement de {len(candidates)} tickers via Twelve Data...")
        print(f"   (Quote + Profile + RSI + TimeSeries + Statistics + Balance + Income + CashFlow)")
        
        # Estimation du temps
        calls_per_ticker = 8
        time_per_call = 60 / TWELVE_DATA_RATE_LIMIT
        time_per_ticker = calls_per_ticker * time_per_call + TWELVE_DATA_TICKER_PAUSE
        estimated_time = len(candidates) * time_per_ticker / 60
        print(
            f"   ⏱️  Temps estimé: ~{estimated_time:.1f} minutes "
            f"(rate limit {TWELVE_DATA_RATE_LIMIT}/min + pause {TWELVE_DATA_TICKER_PAUSE}s/ticker)"
        )

        enriched = []
        for idx, (_, row) in enumerate(candidates.iterrows(), 1):
            symbol = row["symbol"]
            print(f"\n  [{idx}/{len(candidates)}] {symbol}")

            quote = self._fetch_quote(symbol)
            row["td_price"] = float(quote.get("close", row.get("current_price", 0)) or 0)
            row["td_change_pct"] = float(quote.get("percent_change", 0) or 0)
            row["td_volume"] = int(quote.get("volume", 0) or 0)
            row["td_avg_volume"] = int(quote.get("average_volume", 0) or 0)
            ftw = quote.get("fifty_two_week", {}) or {}
            row["td_high_52w"] = float(ftw.get("high", row.get("high_52w", 0)) or 0)
            row["td_low_52w"] = float(ftw.get("low", row.get("low_52w", 0)) or 0)
            print(f"    ✓ Quote: ${row['td_price']:.2f}")

            profile = self._fetch_profile(symbol)
            row["sector"] = profile.get("sector") or "Unknown"
            row["industry"] = profile.get("industry") or "Unknown"
            row["company"] = profile.get("name") or row.get("company", "")
            print(f"    ✓ Profile: {row['sector']}")

            tech = self._fetch_technicals(symbol)
            row["rsi"] = tech.get("rsi", 50.0)
            print(f"    ✓ RSI: {row['rsi']:.1f}")

            prices = self._fetch_time_series(symbol, 900)
            perf_vol = self._calculate_perf_vol(prices)
            row["perf_3m"] = perf_vol["perf_3m"]
            row["perf_ytd"] = perf_vol["perf_ytd"]
            row["vol_30d"] = perf_vol["vol_30d"]
            ytd_str = f"{row['perf_ytd']}%" if row.get("perf_ytd") is not None else "N/A"
            print(f"    ✓ Perf 3M: {row['perf_3m']}% | YTD: {ytd_str} | Vol: {row['vol_30d']}%")

            stats = self._fetch_statistics(symbol)
            balance = self._fetch_balance_sheet(symbol)
            income = self._fetch_income_statement(symbol)
            cashflow = self._fetch_cash_flow(symbol)

            fundamentals = self._extract_fundamentals(stats, balance, income, cashflow)
            for k, v in fundamentals.items():
                row[k] = v

            roe_str = f"{row['roe']:.1f}%" if row.get("roe") is not None else "N/A"
            de_str = f"{row['debt_equity']:.2f}" if row.get("debt_equity") is not None else "N/A"
            margin_str = f"{row['net_margin']:.1f}%" if row.get("net_margin") is not None else "N/A"
            cr_str = f"{row['current_ratio']:.2f}" if row.get("current_ratio") is not None else "N/A"
            print(f"    ✓ Fundamentals: ROE={roe_str} | D/E={de_str} | Margin={margin_str} | CR={cr_str}")

            enriched.append(row)
            
            # Pause inter-ticker
            time.sleep(TWELVE_DATA_TICKER_PAUSE)

        self.universe = pd.DataFrame(enriched)
        
        # S'assurer que sector et industry existent après enrichissement
        if "sector" not in self.universe.columns:
            self.universe["sector"] = "Unknown"
        if "industry" not in self.universe.columns:
            self.universe["industry"] = "Unknown"

        # Vérification couverture
        fundamentals_cols = ["roe", "debt_equity", "net_margin", "current_ratio"]
        existing_cols = [c for c in fundamentals_cols if c in self.universe.columns]
        if existing_cols:
            coverage = self.universe[existing_cols].notna().any(axis=1).mean()
            print(f"\n📊 Coverage fondamentaux (≥1 ratio non nul): {coverage:.0%}")

        print(f"\n✅ Enrichissement terminé: {len(self.universe)} tickers")
        return self.universe
    
    def enrich_from_history(self, prices_history: pd.DataFrame, fundamentals_cache: Dict[str, dict] = None) -> pd.DataFrame:
        """Enrichit l'univers à partir d'un historique de prix pré-chargé (backtest)."""
        if self.universe.empty:
            self.load_data()
        
        print(f"📊 Enrichissement depuis historique de prix ({len(prices_history)} jours)...")
        
        # Stocker les returns pour corrélations réelles
        self._returns_history = prices_history.pct_change().dropna()
        
        enriched = []
        valid_symbols = prices_history.columns.tolist()
        
        for _, row in self.universe.iterrows():
            symbol = row["symbol"]
            
            if symbol not in valid_symbols:
                continue
            
            prices = prices_history[symbol].dropna()
            if len(prices) < 30:
                continue
            
            row["td_price"] = prices.iloc[-1]
            
            if len(prices) >= 252:
                row["td_high_52w"] = prices.iloc[-252:].max()
                row["td_low_52w"] = prices.iloc[-252:].min()
            else:
                row["td_high_52w"] = prices.max()
                row["td_low_52w"] = prices.min()
            
            if len(prices) >= 63:
                row["perf_3m"] = round((prices.iloc[-1] / prices.iloc[-63] - 1) * 100, 2)
            
            current_year = prices.index[-1].year
            year_start = f"{current_year}-01-01"
            ytd_prices = prices.loc[year_start:]
            if len(ytd_prices) > 1:
                row["perf_ytd"] = round((ytd_prices.iloc[-1] / ytd_prices.iloc[0] - 1) * 100, 2)
            
            if len(prices) >= 30:
                returns_30d = prices.pct_change().iloc[-30:]
                row["vol_30d"] = round(returns_30d.std() * np.sqrt(252) * 100, 2)
            
            if len(prices) >= 15:
                delta = prices.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 100
                row["rsi"] = round(100 - (100 / (1 + rs)), 1)
            else:
                row["rsi"] = 50.0
            
            if fundamentals_cache and symbol in fundamentals_cache:
                for k, v in fundamentals_cache[symbol].items():
                    row[k] = v
            
            if "sector" not in row or pd.isna(row.get("sector")):
                row["sector"] = "Unknown"
            if "industry" not in row or pd.isna(row.get("industry")):
                row["industry"] = "Unknown"
            
            enriched.append(row)
        
        self.universe = pd.DataFrame(enriched)
        
        # S'assurer que sector et industry existent
        if "sector" not in self.universe.columns:
            self.universe["sector"] = "Unknown"
        if "industry" not in self.universe.columns:
            self.universe["industry"] = "Unknown"
        
        print(f"✅ {len(self.universe)} tickers enrichis depuis historique")
        return self.universe
    
    # =========================================================================
    # CLEANING
    # =========================================================================
    
    def clean_universe(self, strict: bool = False):
        """Nettoie l'univers en excluant les tickers sans données."""
        # S'assurer que le DataFrame n'est pas vide
        if self.universe.empty:
            print("⚠️ Univers vide, rien à nettoyer")
            return
        
        # S'assurer que les colonnes essentielles existent AVANT tout accès
        if "sector" not in self.universe.columns:
            print("⚠️ Colonne 'sector' manquante - ajout valeur par défaut")
            self.universe["sector"] = "Unknown"
        else:
            # Remplacer les NaN par "Unknown"
            self.universe["sector"] = self.universe["sector"].fillna("Unknown")
        
        if "industry" not in self.universe.columns:
            self.universe["industry"] = "Unknown"
        else:
            self.universe["industry"] = self.universe["industry"].fillna("Unknown")
        
        # Maintenant on peut accéder à sector en toute sécurité
        if not strict:
            mask_bad = self.universe["sector"].eq("Unknown")
        else:
            # Mode strict: exige aussi revenue et net_income
            revenue_missing = self.universe["revenue"].isna() if "revenue" in self.universe.columns else pd.Series([True] * len(self.universe), index=self.universe.index)
            income_missing = self.universe["net_income"].isna() if "net_income" in self.universe.columns else pd.Series([True] * len(self.universe), index=self.universe.index)
            mask_bad = (
                self.universe["sector"].eq("Unknown") |
                revenue_missing |
                income_missing
            )
        
        bad_symbols = self.universe.loc[mask_bad, "symbol"].tolist()
        if bad_symbols:
            print(f"⚠️ Exclusion {len(bad_symbols)} tickers: {bad_symbols[:10]}{'...' if len(bad_symbols) > 10 else ''}")
        
        self.universe = self.universe[~mask_bad].reset_index(drop=True)
        print(f"✅ Univers nettoyé: {len(self.universe)} tickers restants")
    
    # =========================================================================
    # HRP OPTIMIZATION
    # =========================================================================
    
    def _get_correlation_matrix(self, returns: pd.DataFrame = None, shrinkage: float = None) -> pd.DataFrame:
        """Calcule la matrice de corrélation."""
        n = len(self.universe)
        symbols = self.universe["symbol"].tolist()
        
        use_real = CORRELATION.get("use_real_correlation", True)
        
        if returns is None and self._returns_history is not None:
            returns = self._returns_history
        
        if use_real and returns is not None:
            valid_cols = [s for s in symbols if s in returns.columns]
            
            if len(valid_cols) >= 2:
                ret_subset = returns[valid_cols]
                corr_real = ret_subset.corr()
                
                if shrinkage is None:
                    shrinkage = CORRELATION.get("shrinkage", 0.2)
                
                if shrinkage > 0:
                    identity = np.eye(len(corr_real))
                    corr_real = (1 - shrinkage) * corr_real.values + shrinkage * identity
                    corr_real = pd.DataFrame(corr_real, index=valid_cols, columns=valid_cols)
                
                full_corr = self._get_sector_correlation_fallback()
                
                for i, s1 in enumerate(valid_cols):
                    for j, s2 in enumerate(valid_cols):
                        if s1 in full_corr.index and s2 in full_corr.columns:
                            if isinstance(corr_real, pd.DataFrame):
                                full_corr.loc[s1, s2] = corr_real.loc[s1, s2]
                            else:
                                full_corr.loc[s1, s2] = corr_real[i, j]
                
                print(f"   📊 Corrélations réelles calculées ({len(valid_cols)} tickers, shrinkage={shrinkage})")
                return full_corr
        
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
        
        if n == 0:
            print("❌ Aucun ticker dans l'univers après filtres!")
            return pd.DataFrame()
        
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
        
        avg_roe = df["roe"].dropna().mean() if "roe" in df.columns and df["roe"].notna().any() else None
        avg_de = df["debt_equity"].dropna().mean() if "debt_equity" in df.columns and df["debt_equity"].notna().any() else None
        avg_margin = df["net_margin"].dropna().mean() if "net_margin" in df.columns and df["net_margin"].notna().any() else None
        
        self.portfolio_metrics = {
            "positions": len(df),
            "perf_3m": round(perf_3m, 2) if perf_3m else None,
            "perf_ytd": round(perf_ytd, 2) if perf_ytd else None,
            "vol_30d": round(vol, 2) if vol else None,
            "sector_weights": sector_weights,
            "avg_roe": round(avg_roe, 1) if avg_roe is not None else None,
            "avg_debt_equity": round(avg_de, 2) if avg_de is not None else None,
            "avg_net_margin": round(avg_margin, 1) if avg_margin is not None else None
        }
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    def summary(self) -> dict:
        """Retourne un résumé du portefeuille."""
        return {
            "engine_version": self.version,
            "enrichment_mode": self._enrichment_mode or "unknown",
            "universe_size": len(self.universe),
            "portfolio_size": len(self.portfolio),
            **self.portfolio_metrics
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
            "perf_3m", "perf_ytd", "vol_30d",
            "gp_buys", "gp_tier", "insider_buys", "rsi", "td_price",
            "roe", "roa", "debt_equity", "current_ratio",
            "gross_margin", "operating_margin", "net_margin",
            "capex_ratio", "fcf", "revenue", "net_income"
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
                "enrichment_mode": self._enrichment_mode or "unknown",
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
