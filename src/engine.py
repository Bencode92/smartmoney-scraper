"""SmartMoney Engine - Scoring + Optimisation HRP"""
import json
import math
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import requests
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import (
    DATA_RAW, TWELVE_DATA_KEY, TWELVE_DATA_BASE,
    TWELVE_DATA_RATE_LIMIT, WEIGHTS, CONSTRAINTS
)


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


class SmartMoneyEngine:
    """Moteur principal: charge données → enrichit → score → optimise"""
    
    def __init__(self):
        self.universe = pd.DataFrame()
        self.portfolio = pd.DataFrame()
        self.portfolio_metrics = {}
        self._last_api_call = 0
        self._last_api_error = None
    
    # === DATA LOADING ===
    
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
    
    # === TWELVE DATA API ===
    
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
        result = {
            "roe": None, "roa": None, "debt_equity": None, "current_ratio": None,
            "gross_margin": None, "operating_margin": None, "net_margin": None,
            "capex_ratio": None, "fcf": None, "revenue": None, "net_income": None
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

            result["revenue"] = revenue
            result["net_income"] = net_inc

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

            current_assets_block = assets.get("current_assets", {}) or {}
            current_assets = self._safe_float(
                current_assets_block.get("total_current_assets")
                or current_assets_block.get("current_assets")
                or balance.get("total_current_assets")
            )

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
                if (
                    result["capex_ratio"] is None
                    and result["revenue"] and result["revenue"] > 0
                    and operating_cf is not None
                    and fcf_direct is not None
                    and fcf_direct <= operating_cf
                ):
                    implied_capex = operating_cf - fcf_direct
                    capex_abs = abs(implied_capex)
                    result["capex_ratio"] = round(capex_abs / result["revenue"] * 100, 2)

                if fcf_direct is not None:
                    result["fcf"] = fcf_direct

        if stats:
            stats_root = stats.get("statistics") or stats.get("data") or stats
            fin = stats_root.get("financials", {}) or {}
            fin_bs = fin.get("balance_sheet", {}) or {}

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
    
    # === ENRICHISSEMENT ===
    
    def enrich(self, top_n: int = 50) -> pd.DataFrame:
        if self.universe.empty:
            self.load_data()

        candidates = self.universe[
            (self.universe["gp_buys"] >= CONSTRAINTS["min_buys"]) |
            (self.universe["insider_buys"] > 0)
        ].head(top_n)

        print(f"📊 Enrichissement de {len(candidates)} tickers via Twelve Data...")
        print(f"   (Quote + Profile + RSI + TimeSeries + Statistics + Balance + Income + CashFlow)")
        estimated_time = len(candidates) * 8 / TWELVE_DATA_RATE_LIMIT
        print(
            f"   ⏱️  Temps estimé théorique: ~{estimated_time:.1f} minutes "
            f"(hors pauses liées aux crédits, rate limit {TWELVE_DATA_RATE_LIMIT}/min)"
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

        self.universe = pd.DataFrame(enriched)

        fundamentals_cols = ["roe", "debt_equity", "net_margin", "current_ratio"]
        existing_cols = [c for c in fundamentals_cols if c in self.universe.columns]
        if existing_cols:
            coverage = self.universe[existing_cols].notna().any(axis=1).mean()
            print(f"\n📊 Coverage fondamentaux (≥1 ratio non nul): {coverage:.0%}")
            if coverage < 0.5:
                missing = self.universe[self.universe[existing_cols].isna().all(axis=1)]["symbol"].tolist()
                print(f"⚠️ Beaucoup de tickers sans fondamentaux, ex: {missing[:10]}{'...' if len(missing) > 10 else ''}")

        if "perf_ytd" in self.universe.columns:
            ytd_coverage = self.universe["perf_ytd"].notna().mean()
            print(f"📊 Coverage perf_ytd: {ytd_coverage:.0%}")

        print(f"\n✅ Enrichissement terminé")
        return self.universe
    
    # === NETTOYAGE ===
    
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
    
    # === SCORING ===
    
    def score_smart_money(self, row) -> float:
        score = 0
        tier_map = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}
        score += tier_map.get(row.get("gp_tier", "D"), 0.25) * 0.4
        buys = min(row.get("gp_buys", 0) / 10, 1.0)
        score += buys * 0.4
        weight = min(row.get("gp_weight", 0) / 0.2, 1.0)
        score += weight * 0.2
        return round(score, 3)
    
    def score_insider(self, row) -> float:
        buys = row.get("insider_buys", 0)
        sells = row.get("insider_sells", 0)
        net_value = row.get("insider_net_value", 0)
        
        if buys + sells == 0:
            ratio_score = 0.5
        else:
            ratio_score = buys / (buys + sells)
        
        value_score = min(max(net_value / 10_000_000, -1), 1)
        value_score = (value_score + 1) / 2
        
        return round(ratio_score * 0.6 + value_score * 0.4, 3)
    
    def score_momentum(self, row) -> float:
        score = 0
        
        rsi = row.get("rsi", 50)
        if 40 <= rsi <= 60:
            rsi_score = 1.0
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            rsi_score = 0.7
        elif rsi < 30:
            rsi_score = 0.8
        else:
            rsi_score = 0.3
        score += rsi_score * 0.4
        
        low = row.get("td_low_52w", row.get("low_52w", 0))
        high = row.get("td_high_52w", row.get("high_52w", 0))
        price = row.get("td_price", row.get("current_price", 0))
        
        if high > low and high > 0:
            position = (price - low) / (high - low)
            range_score = 1 - abs(position - 0.5) * 2
            range_score = max(0, range_score)
        else:
            range_score = 0.5
        score += range_score * 0.3
        
        perf_3m = row.get("perf_3m", 0) or 0
        if perf_3m > 15:
            score += 0.3
        elif perf_3m > 5:
            score += 0.25
        elif perf_3m > 0:
            score += 0.2
        elif perf_3m > -10:
            score += 0.1
        
        return round(min(score, 1.0), 3)
    
    def score_quality(self, row) -> float:
        score = 0.5
        has_fundamentals = False
        
        roe = row.get("roe")
        if roe is not None:
            has_fundamentals = True
            if roe >= 25:
                score += 0.20
            elif roe >= 15:
                score += 0.15
            elif roe >= 10:
                score += 0.10
            elif roe >= 0:
                score += 0.05
            else:
                score -= 0.15
        
        debt_eq = row.get("debt_equity")
        if debt_eq is not None:
            has_fundamentals = True
            if debt_eq < 0.3:
                score += 0.15
            elif debt_eq < 0.7:
                score += 0.10
            elif debt_eq < 1.5:
                score += 0.05
            elif debt_eq > 3:
                score -= 0.15
            else:
                score -= 0.05
        
        net_margin = row.get("net_margin")
        if net_margin is not None:
            has_fundamentals = True
            if net_margin >= 20:
                score += 0.15
            elif net_margin >= 10:
                score += 0.10
            elif net_margin >= 5:
                score += 0.05
            elif net_margin < 0:
                score -= 0.10
        
        capex_ratio = row.get("capex_ratio")
        sector = row.get("sector", "Unknown")
        if capex_ratio is not None:
            has_fundamentals = True
            if sector in ["Technology", "Industrials", "Communication Services"]:
                if 5 <= capex_ratio <= 15:
                    score += 0.10
                elif capex_ratio > 15:
                    score += 0.05
            else:
                if capex_ratio < 5:
                    score += 0.10
                elif capex_ratio < 10:
                    score += 0.05
        
        current_ratio = row.get("current_ratio")
        if current_ratio is not None:
            has_fundamentals = True
            if current_ratio >= 1.5:
                score += 0.05
            elif current_ratio < 1:
                score -= 0.05
        
        fcf = row.get("fcf")
        if fcf is not None:
            has_fundamentals = True
            if fcf > 0:
                score += 0.05
            else:
                score -= 0.05
        
        if not has_fundamentals:
            price = row.get("td_price", row.get("current_price", 0))
            if price >= 50:
                score += 0.10
            elif price >= 20:
                score += 0.05
            elif price < 10:
                score -= 0.10
            
            vol = row.get("td_volume", 0)
            avg_vol = row.get("td_avg_volume", 1)
            if avg_vol > 0:
                vol_ratio = vol / avg_vol
                if vol_ratio > 1.5:
                    score += 0.05
                elif vol_ratio < 0.5:
                    score -= 0.05
        
        return round(max(0, min(1, score)), 3)
    
    def calculate_scores(self) -> pd.DataFrame:
        if self.universe.empty:
            self.load_data()
        
        print("📈 Calcul des scores...")
        
        scores = []
        for _, row in self.universe.iterrows():
            sm = self.score_smart_money(row)
            ins = self.score_insider(row)
            mom = self.score_momentum(row)
            qual = self.score_quality(row)
            
            composite = (
                WEIGHTS["smart_money"] * sm +
                WEIGHTS["insider"] * ins +
                WEIGHTS["momentum"] * mom +
                WEIGHTS["quality"] * qual
            )
            
            row["score_sm"] = sm
            row["score_insider"] = ins
            row["score_momentum"] = mom
            row["score_quality"] = qual
            row["score_composite"] = round(composite, 3)
            scores.append(row)
        
        self.universe = pd.DataFrame(scores)
        self.universe = self.universe.sort_values("score_composite", ascending=False)
        
        print(f"✅ Scores calculés pour {len(self.universe)} tickers")
        return self.universe
    
    # === FILTRES ===
    
    def apply_filters(self) -> pd.DataFrame:
        before = len(self.universe)
        df = self.universe.copy()
        
        price_col = "td_price" if "td_price" in df.columns else "current_price"
        df = df[df[price_col] >= CONSTRAINTS["min_price"]]
        df = df[df["score_composite"] >= CONSTRAINTS["min_score"]]
        df = df.head(CONSTRAINTS["max_positions"] * 2)
        
        self.universe = df
        print(f"🔍 Filtres: {before} → {len(df)} tickers")
        return self.universe
    
    # === HRP ===
    
    def _get_correlation_matrix(self) -> pd.DataFrame:
        n = len(self.universe)
        symbols = self.universe["symbol"].tolist()
        sectors = self.universe["sector"].tolist() if "sector" in self.universe.columns else ["Unknown"] * n
        
        corr = np.eye(n)
        for i in range(n):
            for j in range(i+1, n):
                if sectors[i] == sectors[j] and sectors[i] != "Unknown":
                    corr[i, j] = 0.7
                    corr[j, i] = 0.7
                else:
                    corr[i, j] = 0.4
                    corr[j, i] = 0.4
        
        return pd.DataFrame(corr, index=symbols, columns=symbols)
    
    def _hrp_weights(self, cov: np.ndarray, corr: np.ndarray) -> np.ndarray:
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
    
    def optimize(self) -> pd.DataFrame:
        if "score_composite" not in self.universe.columns:
            self.calculate_scores()
            self.apply_filters()
        
        print("⚙️ Optimisation HRP...")
        
        n = len(self.universe)
        if n < CONSTRAINTS["min_positions"]:
            print(f"⚠️ Seulement {n} tickers, minimum {CONSTRAINTS['min_positions']} requis")
        
        if "vol_30d" in self.universe.columns:
            vols = self.universe["vol_30d"].fillna(25).values / 100
        else:
            vols = np.full(n, 0.25)
        
        corr = self._get_correlation_matrix().values
        cov = np.outer(vols, vols) * corr
        
        weights = self._hrp_weights(cov, corr)
        
        scores = self.universe["score_composite"].values
        score_tilt = scores / scores.mean()
        weights = weights * score_tilt
        weights = weights / weights.sum()
        
        weights = np.minimum(weights, CONSTRAINTS["max_weight"])
        weights = weights / weights.sum()
        
        self.universe["weight"] = weights
        self.portfolio = self.universe.nlargest(CONSTRAINTS["max_positions"], "weight").copy()
        self.portfolio["weight"] = self.portfolio["weight"] / self.portfolio["weight"].sum()
        self.portfolio["weight"] = self.portfolio["weight"].round(4)
        
        self._calculate_portfolio_metrics()
        
        print(f"✅ Portefeuille: {len(self.portfolio)} positions")
        return self.portfolio
    
    def _calculate_portfolio_metrics(self):
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
    
    # === EXPORT ===
    
    def export(self, output_dir: Path) -> dict:
        """
        Exporte le portefeuille directement dans le dossier spécifié.
        Utilise NaNSafeEncoder pour garantir un JSON valide (NaN → null).
        """
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
        
        cols = [c for c in export_cols if c in self.portfolio.columns]
        df = self.portfolio[cols].copy()
        
        # Remplacer les NaN par None dans le DataFrame avant export
        df = df.where(pd.notnull(df), None)
        
        # Construire le résultat
        result = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "date": today,
                "positions": len(df),
                "total_weight": round(df["weight"].sum(), 4)
            },
            "metrics": self.portfolio_metrics,
            "portfolio": df.to_dict(orient="records")
        }
        
        # Export JSON avec encodeur sécurisé pour NaN
        json_path = output_dir / "portfolio.json"
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2, cls=NaNSafeEncoder, default=str)
        
        # Export CSV
        csv_path = output_dir / "portfolio.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"📁 Exporté: portfolio.json, portfolio.csv")
        return result


if __name__ == "__main__":
    engine = SmartMoneyEngine()
    engine.load_data()
    engine.enrich(top_n=40)
    engine.clean_universe(strict=False)
    engine.calculate_scores()
    engine.apply_filters()
    engine.optimize()
    
    from config import OUTPUTS
    today = datetime.now().strftime("%Y-%m-%d")
    dated_dir = OUTPUTS / today
    dated_dir.mkdir(parents=True, exist_ok=True)
    engine.export(dated_dir)
