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
                
                # Agrège les trades par symbol
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
        
        # Convertir en DataFrame
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
    
    # === TWELVE DATA ENRICHMENT ===
    
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
                if "code" not in data:  # pas d'erreur
                    return data
        except Exception as e:
            print(f"⚠️ Twelve Data error {symbol}: {e}")
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
    
    def enrich(self, top_n: int = 50) -> pd.DataFrame:
        """Enrichit les top N candidats avec Twelve Data"""
        if self.universe.empty:
            self.load_data()
        
        # Pré-filtre: tickers avec au moins des données smart money
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
            
            # Technicals
            tech = self._fetch_technicals(symbol)
            row["rsi"] = tech.get("rsi", 50)
            
            enriched.append(row)
            print(f"  ✓ {symbol}")
        
        self.universe = pd.DataFrame(enriched)
        print(f"✅ Enrichissement terminé")
        return self.universe
    
    # === SCORING ===
    
    def score_smart_money(self, row) -> float:
        """Score Smart Money (0-1)"""
        score = 0
        
        # Tier (A=1, B=0.75, C=0.5, D=0.25)
        tier_map = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}
        score += tier_map.get(row.get("gp_tier", "D"), 0.25) * 0.4
        
        # Nombre de buys (normalisé sur 10)
        buys = min(row.get("gp_buys", 0) / 10, 1.0)
        score += buys * 0.4
        
        # Portfolio weight (normalisé)
        weight = min(row.get("gp_weight", 0) / 0.2, 1.0)
        score += weight * 0.2
        
        return round(score, 3)
    
    def score_insider(self, row) -> float:
        """Score Insider (0-1)"""
        buys = row.get("insider_buys", 0)
        sells = row.get("insider_sells", 0)
        net_value = row.get("insider_net_value", 0)
        
        # Ratio buy/sell
        if buys + sells == 0:
            ratio_score = 0.5
        else:
            ratio = buys / (buys + sells)
            ratio_score = ratio
        
        # Net value (normalisé sur $10M)
        value_score = min(max(net_value / 10_000_000, -1), 1)
        value_score = (value_score + 1) / 2  # ramène à 0-1
        
        score = ratio_score * 0.6 + value_score * 0.4
        return round(score, 3)
    
    def score_momentum(self, row) -> float:
        """Score Momentum (0-1)"""
        score = 0
        
        # RSI (optimal 40-60)
        rsi = row.get("rsi", 50)
        if 40 <= rsi <= 60:
            rsi_score = 1.0
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            rsi_score = 0.7
        elif rsi < 30:  # oversold = opportunité
            rsi_score = 0.8
        else:  # >70 overbought
            rsi_score = 0.3
        score += rsi_score * 0.5
        
        # Position vs 52W range
        low = row.get("td_low_52w", row.get("low_52w", 0))
        high = row.get("td_high_52w", row.get("high_52w", 0))
        price = row.get("td_price", row.get("current_price", 0))
        
        if high > low and high > 0:
            position = (price - low) / (high - low)
            # Idéal: mi-range (pas au plus haut ni plus bas)
            range_score = 1 - abs(position - 0.5) * 2
            range_score = max(0, range_score)
        else:
            range_score = 0.5
        score += range_score * 0.5
        
        return round(score, 3)
    
    def score_quality(self, row) -> float:
        """Score Quality simplifié (0-1)"""
        # Sans données fondamentales, on utilise des proxies
        score = 0.5  # Neutre par défaut
        
        # Prix > $10 = plus liquide/institutionnel
        price = row.get("td_price", row.get("current_price", 0))
        if price >= 50:
            score += 0.2
        elif price >= 20:
            score += 0.1
        elif price < 10:
            score -= 0.2
        
        # Volume relatif
        vol = row.get("td_volume", 0)
        avg_vol = row.get("td_avg_volume", 1)
        if avg_vol > 0:
            vol_ratio = vol / avg_vol
            if vol_ratio > 1.5:
                score += 0.1  # Intérêt accru
            elif vol_ratio < 0.5:
                score -= 0.1  # Faible intérêt
        
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
            
            # Score composite
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
        
        # Prix minimum
        price_col = "td_price" if "td_price" in df.columns else "current_price"
        df = df[df[price_col] >= CONSTRAINTS["min_price"]]
        
        # Score minimum
        df = df[df["score_composite"] >= CONSTRAINTS["min_score"]]
        
        # Limite aux top N
        df = df.head(CONSTRAINTS["max_positions"] * 2)  # Garde marge pour HRP
        
        self.universe = df
        print(f"🔍 Filtres: {before} → {len(df)} tickers")
        return self.universe
    
    # === OPTIMISATION HRP ===
    
    def _get_correlation_matrix(self) -> pd.DataFrame:
        """Matrice de corrélation simplifiée (proxy sans historique)"""
        n = len(self.universe)
        symbols = self.universe["symbol"].tolist()
        
        # Corrélation proxy basée sur secteur/caractéristiques
        # En production: utiliser historique de prix
        corr = np.eye(n)
        
        # Ajoute corrélation de base entre tous (marché)
        corr = corr * 0.6 + np.ones((n, n)) * 0.4
        np.fill_diagonal(corr, 1.0)
        
        return pd.DataFrame(corr, index=symbols, columns=symbols)
    
    def _hrp_weights(self, cov: np.ndarray, corr: np.ndarray) -> np.ndarray:
        """Calcul des poids HRP"""
        n = cov.shape[0]
        
        # Distance et clustering
        dist = np.sqrt((1 - corr) / 2)
        np.fill_diagonal(dist, 0)
        
        # Linkage hiérarchique
        condensed = squareform(dist, checks=False)
        link = linkage(condensed, method="ward")
        order = leaves_list(link)
        
        # Recursive bisection
        weights = np.ones(n)
        clusters = [list(order)]
        
        while clusters:
            cluster = clusters.pop()
            if len(cluster) == 1:
                continue
            
            mid = len(cluster) // 2
            left = cluster[:mid]
            right = cluster[mid:]
            
            # Variance de chaque sous-cluster
            var_left = np.mean([cov[i, i] for i in left])
            var_right = np.mean([cov[i, i] for i in right])
            
            # Allocation inverse à la variance
            total_var = var_left + var_right
            if total_var > 0:
                alpha = 1 - var_left / total_var
            else:
                alpha = 0.5
            
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
        
        # Matrice de covariance proxy (volatilité uniforme)
        vol = 0.25  # 25% vol annualisée
        corr = self._get_correlation_matrix().values
        cov = corr * (vol ** 2)
        
        # Poids HRP bruts
        weights = self._hrp_weights(cov, corr)
        
        # Tilt par score (±20%)
        scores = self.universe["score_composite"].values
        score_tilt = scores / scores.mean()
        weights = weights * score_tilt
        weights = weights / weights.sum()
        
        # Contrainte max weight
        weights = np.minimum(weights, CONSTRAINTS["max_weight"])
        weights = weights / weights.sum()
        
        # Assigner au DataFrame
        self.universe["weight"] = weights
        
        # Sélection finale
        self.portfolio = self.universe.nlargest(CONSTRAINTS["max_positions"], "weight").copy()
        
        # Renormaliser
        self.portfolio["weight"] = self.portfolio["weight"] / self.portfolio["weight"].sum()
        self.portfolio["weight"] = self.portfolio["weight"].round(4)
        
        print(f"✅ Portefeuille: {len(self.portfolio)} positions")
        return self.portfolio
    
    # === EXPORT ===
    
    def export(self, output_dir: Path) -> dict:
        """Exporte le portefeuille en JSON et CSV"""
        output_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Prépare les données
        export_cols = [
            "symbol", "company", "weight",
            "score_composite", "score_sm", "score_insider", "score_momentum", "score_quality",
            "gp_buys", "gp_tier", "insider_buys", "rsi"
        ]
        
        # Filtre les colonnes existantes
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
            "portfolio": df.to_dict(orient="records")
        }
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2)
        
        # CSV
        csv_path = output_dir / f"portfolio_{today}.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"📁 Exporté: {json_path.name}, {csv_path.name}")
        return result


# === MAIN ===
if __name__ == "__main__":
    engine = SmartMoneyEngine()
    engine.load_data()
    engine.enrich(top_n=40)
    engine.calculate_scores()
    engine.apply_filters()
    engine.optimize()
    
    from config import OUTPUTS
    engine.export(OUTPUTS)
