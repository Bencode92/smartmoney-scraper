"""SmartMoney Engine - Scoring + Optimisation HRP"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
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


class SmartMoneyEngine:
    """Moteur principal: charge données → enrichit → score → optimise"""
    
    def __init__(self):
        self.universe = pd.DataFrame()
        self.portfolio = pd.DataFrame()
        self.portfolio_metrics = {}  # Métriques agrégées
        self._last_api_call = 0
    
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
        
        # Valeurs par défaut
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
    
    def _fetch_quote(self, symbol: str) -> dict:
        """Récupère prix + stats via Twelve Data"""
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
        """Récupère le profil (secteur, industry) via Twelve Data"""
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
        """Récupère RSI via Twelve Data"""
        if not TWELVE_DATA_KEY:
            return {}
        
        self._rate_limit()
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/rsi",
                params={"symbol": symbol, "interval": "1day", "apikey": TWELVE_DATA_KEY},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "values" in data and len(data["values"]) > 0:
                    return {"rsi": float(data["values"][0]["rsi"])}
        except Exception as e:
            print(f"⚠️ RSI error {symbol}: {e}")
        return {}
    
    def _fetch_time_series(self, symbol: str, outputsize: int = 90) -> list:
        """Récupère l'historique de prix via Twelve Data"""
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
    
    def _calculate_perf_vol(self, prices: list) -> dict:
        """Calcule perf 3M, YTD, vol 30j depuis l'historique"""
        result = {"perf_3m": None, "perf_ytd": None, "vol_30d": None}
        
        if not prices or len(prices) < 2:
            return result
        
        try:
            # Prix du plus récent au plus ancien
            current_price = float(prices[0]["close"])
            
            # Perf 3M (environ 63 jours de trading)
            if len(prices) >= 63:
                price_3m = float(prices[62]["close"])
                result["perf_3m"] = round((current_price / price_3m - 1) * 100, 2)
            elif len(prices) >= 30:
                price_old = float(prices[-1]["close"])
                result["perf_3m"] = round((current_price / price_old - 1) * 100, 2)
            
            # Perf YTD
            current_year = datetime.now().year
            for p in prices:
                if p["datetime"].startswith(f"{current_year}-01"):
                    price_ytd = float(p["close"])
                    result["perf_ytd"] = round((current_price / price_ytd - 1) * 100, 2)
                    break
            
            # Vol 30j (annualisée)
            if len(prices) >= 30:
                closes = [float(p["close"]) for p in prices[:30]]
                returns = [(closes[i] / closes[i+1] - 1) for i in range(len(closes)-1)]
                vol = np.std(returns) * np.sqrt(252) * 100
                result["vol_30d"] = round(vol, 2)
        
        except Exception as e:
            print(f"⚠️ Calc error: {e}")
        
        return result
    
    # === ENRICHISSEMENT COMPLET ===
    
    def enrich(self, top_n: int = 50) -> pd.DataFrame:
        """Enrichit les top N candidats avec Twelve Data (quote, profile, time_series)"""
        if self.universe.empty:
            self.load_data()
        
        candidates = self.universe[
            (self.universe["gp_buys"] >= CONSTRAINTS["min_buys"]) |
            (self.universe["insider_buys"] > 0)
        ].head(top_n)
        
        print(f"📊 Enrichissement de {len(candidates)} tickers via Twelve Data...")
        
        enriched = []
        for _, row in candidates.iterrows():
            symbol = row["symbol"]
            
            # Quote
            quote = self._fetch_quote(symbol)
            row["td_price"] = float(quote.get("close", row.get("current_price", 0)))
            row["td_change_pct"] = float(quote.get("percent_change", 0))
            row["td_volume"] = int(quote.get("volume", 0))
            row["td_avg_volume"] = int(quote.get("average_volume", 0))
            row["td_high_52w"] = float(quote.get("fifty_two_week", {}).get("high", row.get("high_52w", 0)))
            row["td_low_52w"] = float(quote.get("fifty_two_week", {}).get("low", row.get("low_52w", 0)))
            
            # Profile (secteur)
            profile = self._fetch_profile(symbol)
            row["sector"] = profile.get("sector", "Unknown")
            row["industry"] = profile.get("industry", "Unknown")
            
            # RSI
            tech = self._fetch_technicals(symbol)
            row["rsi"] = tech.get("rsi", 50)
            
            # Time series (perf, vol)
            prices = self._fetch_time_series(symbol, 90)
            perf_vol = self._calculate_perf_vol(prices)
            row["perf_3m"] = perf_vol["perf_3m"]
            row["perf_ytd"] = perf_vol["perf_ytd"]
            row["vol_30d"] = perf_vol["vol_30d"]
            
            # Champs Quality futurs (vides pour l'instant)
            row["roe"] = None
            row["debt_equity"] = None
            row["capex_ratio"] = None
            
            enriched.append(row)
            print(f"  ✓ {symbol} | {row['sector']} | perf_3m: {row['perf_3m']}%")
        
        self.universe = pd.DataFrame(enriched)
        print(f"✅ Enrichissement terminé")
        return self.universe
    
    # === SCORING ===
    
    def score_smart_money(self, row) -> float:
        """Score Smart Money (0-1)"""
        score = 0
        tier_map = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}
        score += tier_map.get(row.get("gp_tier", "D"), 0.25) * 0.4
        buys = min(row.get("gp_buys", 0) / 10, 1.0)
        score += buys * 0.4
        weight = min(row.get("gp_weight", 0) / 0.2, 1.0)
        score += weight * 0.2
        return round(score, 3)
    
    def score_insider(self, row) -> float:
        """Score Insider (0-1)"""
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
        """Score Momentum (0-1)"""
        score = 0
        
        # RSI
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
        
        # Position vs 52W range
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
        
        # Perf 3M (bonus si positif)
        perf_3m = row.get("perf_3m", 0) or 0
        if perf_3m > 10:
            score += 0.3
        elif perf_3m > 0:
            score += 0.2
        elif perf_3m > -10:
            score += 0.1
        
        return round(min(score, 1.0), 3)
    
    def score_quality(self, row) -> float:
        """Score Quality (0-1) - utilise ROE/Debt si disponibles"""
        score = 0.5
        
        # Prix (proxy liquidité)
        price = row.get("td_price", row.get("current_price", 0))
        if price >= 50:
            score += 0.15
        elif price >= 20:
            score += 0.1
        elif price < 10:
            score -= 0.15
        
        # Volume relatif
        vol = row.get("td_volume", 0)
        avg_vol = row.get("td_avg_volume", 1)
        if avg_vol > 0:
            vol_ratio = vol / avg_vol
            if vol_ratio > 1.5:
                score += 0.1
            elif vol_ratio < 0.5:
                score -= 0.1
        
        # ROE si disponible
        roe = row.get("roe")
        if roe is not None:
            if roe >= 20:
                score += 0.15
            elif roe >= 10:
                score += 0.1
            elif roe < 0:
                score -= 0.15
        
        # Debt/Equity si disponible
        debt_eq = row.get("debt_equity")
        if debt_eq is not None:
            if debt_eq < 0.5:
                score += 0.1
            elif debt_eq > 2:
                score -= 0.1
        
        return round(max(0, min(1, score)), 3)
    
    def calculate_scores(self) -> pd.DataFrame:
        """Calcule tous les scores"""
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
        """Applique les filtres d'exclusion"""
        before = len(self.universe)
        df = self.universe.copy()
        
        price_col = "td_price" if "td_price" in df.columns else "current_price"
        df = df[df[price_col] >= CONSTRAINTS["min_price"]]
        df = df[df["score_composite"] >= CONSTRAINTS["min_score"]]
        df = df.head(CONSTRAINTS["max_positions"] * 2)
        
        self.universe = df
        print(f"🔍 Filtres: {before} → {len(df)} tickers")
        return self.universe
    
    # === OPTIMISATION HRP ===
    
    def _get_correlation_matrix(self) -> pd.DataFrame:
        """Matrice de corrélation basée sur les secteurs"""
        n = len(self.universe)
        symbols = self.universe["symbol"].tolist()
        sectors = self.universe["sector"].tolist() if "sector" in self.universe.columns else ["Unknown"] * n
        
        corr = np.eye(n)
        
        for i in range(n):
            for j in range(i+1, n):
                if sectors[i] == sectors[j] and sectors[i] != "Unknown":
                    corr[i, j] = 0.7  # Même secteur = plus corrélé
                    corr[j, i] = 0.7
                else:
                    corr[i, j] = 0.4  # Secteurs différents
                    corr[j, i] = 0.4
        
        return pd.DataFrame(corr, index=symbols, columns=symbols)
    
    def _hrp_weights(self, cov: np.ndarray, corr: np.ndarray) -> np.ndarray:
        """Calcul des poids HRP"""
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
        """Optimisation HRP avec contraintes"""
        if "score_composite" not in self.universe.columns:
            self.calculate_scores()
            self.apply_filters()
        
        print("⚙️ Optimisation HRP...")
        
        n = len(self.universe)
        if n < CONSTRAINTS["min_positions"]:
            print(f"⚠️ Seulement {n} tickers, minimum {CONSTRAINTS['min_positions']} requis")
        
        # Volatilité par ticker (ou 25% par défaut)
        if "vol_30d" in self.universe.columns:
            vols = self.universe["vol_30d"].fillna(25).values / 100
        else:
            vols = np.full(n, 0.25)
        
        corr = self._get_correlation_matrix().values
        cov = np.outer(vols, vols) * corr
        
        weights = self._hrp_weights(cov, corr)
        
        # Tilt par score
        scores = self.universe["score_composite"].values
        score_tilt = scores / scores.mean()
        weights = weights * score_tilt
        weights = weights / weights.sum()
        
        # Contrainte max weight
        weights = np.minimum(weights, CONSTRAINTS["max_weight"])
        weights = weights / weights.sum()
        
        self.universe["weight"] = weights
        self.portfolio = self.universe.nlargest(CONSTRAINTS["max_positions"], "weight").copy()
        self.portfolio["weight"] = self.portfolio["weight"] / self.portfolio["weight"].sum()
        self.portfolio["weight"] = self.portfolio["weight"].round(4)
        
        # Calcul métriques portefeuille
        self._calculate_portfolio_metrics()
        
        print(f"✅ Portefeuille: {len(self.portfolio)} positions")
        return self.portfolio
    
    def _calculate_portfolio_metrics(self):
        """Calcule les métriques agrégées du portefeuille"""
        df = self.portfolio
        
        # Perf pondérée
        if "perf_3m" in df.columns:
            perf_3m = (df["weight"] * df["perf_3m"].fillna(0)).sum()
        else:
            perf_3m = None
        
        if "perf_ytd" in df.columns:
            perf_ytd = (df["weight"] * df["perf_ytd"].fillna(0)).sum()
        else:
            perf_ytd = None
        
        # Vol approx: sqrt(sum(wi² × voli²))
        if "vol_30d" in df.columns:
            vol = np.sqrt((df["weight"]**2 * (df["vol_30d"].fillna(25)/100)**2).sum()) * 100
        else:
            vol = None
        
        # Répartition sectorielle
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
            "sector_weights": sector_weights
        }
    
    # === EXPORT ===
    
    def export(self, output_dir: Path) -> dict:
        """Exporte le portefeuille en JSON et CSV"""
        output_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        
        export_cols = [
            "symbol", "company", "sector", "weight",
            "score_composite", "score_sm", "score_insider", "score_momentum", "score_quality",
            "perf_3m", "perf_ytd", "vol_30d",
            "gp_buys", "gp_tier", "insider_buys", "rsi", "td_price",
            "roe", "debt_equity", "capex_ratio"
        ]
        
        cols = [c for c in export_cols if c in self.portfolio.columns]
        df = self.portfolio[cols].copy()
        
        # JSON
        json_path = output_dir / f"portfolio_{today}.json"
        result = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "positions": len(df),
                "total_weight": round(df["weight"].sum(), 4)
            },
            "metrics": self.portfolio_metrics,
            "portfolio": df.to_dict(orient="records")
        }
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        # CSV
        csv_path = output_dir / f"portfolio_{today}.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"📁 Exporté: {json_path.name}, {csv_path.name}")
        return result


if __name__ == "__main__":
    engine = SmartMoneyEngine()
    engine.load_data()
    engine.enrich(top_n=40)
    engine.calculate_scores()
    engine.apply_filters()
    engine.optimize()
    
    from config import OUTPUTS
    engine.export(OUTPUTS)
