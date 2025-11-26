"""Backtest & Benchmark - Compare le portefeuille au S&P 500"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests
import numpy as np
import pandas as pd

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import OUTPUTS, TWELVE_DATA_KEY, TWELVE_DATA_BASE, TWELVE_DATA_RATE_LIMIT


class Backtester:
    """Backtest du portefeuille et comparaison avec benchmark"""
    
    def __init__(self):
        self._last_api_call = 0
        self.benchmark_symbol = "SPY"  # S&P 500 ETF
        self.results = {}
    
    def _rate_limit(self):
        """Respecte le rate limit Twelve Data"""
        elapsed = time.time() - self._last_api_call
        wait = (60 / TWELVE_DATA_RATE_LIMIT) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_api_call = time.time()
    
    def _fetch_time_series(self, symbol: str, outputsize: int = 252) -> pd.DataFrame:
        """Récupère l'historique de prix"""
        if not TWELVE_DATA_KEY:
            return pd.DataFrame()
        
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
                    df = pd.DataFrame(data["values"])
                    df["datetime"] = pd.to_datetime(df["datetime"])
                    df["close"] = df["close"].astype(float)
                    df = df.sort_values("datetime")
                    return df[["datetime", "close"]]
        except Exception as e:
            print(f"⚠️ Time series error {symbol}: {e}")
        return pd.DataFrame()
    
    def load_portfolio_history(self) -> list:
        """Charge l'historique des portefeuilles générés"""
        portfolio_files = sorted(OUTPUTS.glob("portfolio_*.json"))
        
        history = []
        for f in portfolio_files:
            try:
                with open(f) as file:
                    data = json.load(file)
                    date_str = f.stem.replace("portfolio_", "")
                    history.append({
                        "date": date_str,
                        "file": f.name,
                        "positions": len(data.get("portfolio", [])),
                        "portfolio": data.get("portfolio", []),
                        "metrics": data.get("metrics", {})
                    })
            except Exception as e:
                print(f"⚠️ Error loading {f}: {e}")
        
        return history
    
    def calculate_turnover(self, portfolio_old: list, portfolio_new: list) -> dict:
        """Calcule le turnover entre deux portefeuilles"""
        symbols_old = {p["symbol"]: p["weight"] for p in portfolio_old}
        symbols_new = {p["symbol"]: p["weight"] for p in portfolio_new}
        
        all_symbols = set(symbols_old.keys()) | set(symbols_new.keys())
        
        # Entrées et sorties
        entries = set(symbols_new.keys()) - set(symbols_old.keys())
        exits = set(symbols_old.keys()) - set(symbols_new.keys())
        unchanged = set(symbols_old.keys()) & set(symbols_new.keys())
        
        # Turnover = somme des changements de poids / 2
        total_change = 0
        for symbol in all_symbols:
            old_weight = symbols_old.get(symbol, 0)
            new_weight = symbols_new.get(symbol, 0)
            total_change += abs(new_weight - old_weight)
        
        turnover = total_change / 2  # On divise par 2 car chaque changement est compté 2x
        
        return {
            "turnover_pct": round(turnover * 100, 2),
            "entries": list(entries),
            "exits": list(exits),
            "entries_count": len(entries),
            "exits_count": len(exits),
            "unchanged_count": len(unchanged)
        }
    
    def fetch_benchmark(self, days: int = 252) -> pd.DataFrame:
        """Récupère l'historique du benchmark (SPY)"""
        print(f"📊 Récupération benchmark {self.benchmark_symbol}...")
        return self._fetch_time_series(self.benchmark_symbol, days)
    
    def calculate_portfolio_returns(self, portfolio: list, days: int = 90) -> pd.DataFrame:
        """Calcule les rendements du portefeuille basé sur les poids"""
        print(f"📈 Calcul des rendements pour {len(portfolio)} positions...")
        
        # Récupère les prix pour chaque position
        price_data = {}
        for pos in portfolio:
            symbol = pos["symbol"]
            weight = pos["weight"]
            
            df = self._fetch_time_series(symbol, days)
            if not df.empty:
                price_data[symbol] = {
                    "prices": df,
                    "weight": weight
                }
                print(f"  ✓ {symbol}")
        
        if not price_data:
            return pd.DataFrame()
        
        # Trouve les dates communes
        all_dates = None
        for symbol, data in price_data.items():
            dates = set(data["prices"]["datetime"])
            if all_dates is None:
                all_dates = dates
            else:
                all_dates = all_dates & dates
        
        if not all_dates:
            return pd.DataFrame()
        
        all_dates = sorted(all_dates)
        
        # Calcule les rendements pondérés
        portfolio_values = []
        for date in all_dates:
            daily_return = 0
            for symbol, data in price_data.items():
                prices = data["prices"]
                price_row = prices[prices["datetime"] == date]
                if not price_row.empty:
                    daily_return += data["weight"] * price_row["close"].values[0]
            portfolio_values.append({"datetime": date, "value": daily_return})
        
        df = pd.DataFrame(portfolio_values)
        df["return"] = df["value"].pct_change()
        return df
    
    def compare_to_benchmark(self, portfolio: list, days: int = 90) -> dict:
        """Compare le portefeuille au benchmark"""
        print("\n" + "="*60)
        print("📊 BACKTEST vs BENCHMARK")
        print("="*60)
        
        # Benchmark
        bench_df = self.fetch_benchmark(days)
        if bench_df.empty:
            return {"error": "Impossible de récupérer le benchmark"}
        
        bench_df["return"] = bench_df["close"].pct_change()
        bench_total_return = (bench_df["close"].iloc[-1] / bench_df["close"].iloc[0] - 1) * 100
        bench_vol = bench_df["return"].std() * np.sqrt(252) * 100
        
        # Portefeuille (approximation basée sur perf_3m pondérée)
        portfolio_return = sum(p.get("weight", 0) * (p.get("perf_3m", 0) or 0) for p in portfolio)
        portfolio_vol = np.sqrt(sum(p.get("weight", 0)**2 * ((p.get("vol_30d", 25) or 25)/100)**2 for p in portfolio)) * 100
        
        # Alpha et Sharpe
        risk_free_rate = 4.5  # Taux sans risque actuel ~4.5%
        alpha = portfolio_return - bench_total_return
        sharpe_portfolio = (portfolio_return - risk_free_rate/4) / portfolio_vol if portfolio_vol > 0 else 0
        sharpe_bench = (bench_total_return - risk_free_rate/4) / bench_vol if bench_vol > 0 else 0
        
        results = {
            "period_days": days,
            "benchmark": {
                "symbol": self.benchmark_symbol,
                "return_pct": round(bench_total_return, 2),
                "volatility_pct": round(bench_vol, 2),
                "sharpe": round(sharpe_bench, 2)
            },
            "portfolio": {
                "return_pct": round(portfolio_return, 2),
                "volatility_pct": round(portfolio_vol, 2),
                "sharpe": round(sharpe_portfolio, 2),
                "positions": len(portfolio)
            },
            "comparison": {
                "alpha_pct": round(alpha, 2),
                "outperformance": alpha > 0,
                "sharpe_diff": round(sharpe_portfolio - sharpe_bench, 2)
            }
        }
        
        self.results = results
        return results
    
    def calculate_drawdown(self, returns: pd.Series) -> dict:
        """Calcule le drawdown maximum"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        max_dd = drawdown.min() * 100
        max_dd_date = drawdown.idxmin() if not drawdown.empty else None
        
        return {
            "max_drawdown_pct": round(max_dd, 2),
            "max_drawdown_date": str(max_dd_date) if max_dd_date else None
        }
    
    def generate_report(self, portfolio: list, output_dir: Path) -> Path:
        """Génère un rapport de backtest complet"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Compare au benchmark
        comparison = self.compare_to_benchmark(portfolio)
        
        # Charge l'historique pour calculer le turnover
        history = self.load_portfolio_history()
        turnover = None
        if len(history) >= 2:
            turnover = self.calculate_turnover(
                history[-2]["portfolio"],
                history[-1]["portfolio"]
            )
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "benchmark_comparison": comparison,
            "turnover": turnover,
            "portfolio_history": [
                {
                    "date": h["date"],
                    "positions": h["positions"],
                    "perf_3m": h["metrics"].get("perf_3m")
                }
                for h in history
            ]
        }
        
        # Export JSON
        report_path = output_dir / f"backtest_{today}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Affichage
        print("\n" + "-"*60)
        print("📊 RÉSULTATS")
        print("-"*60)
        
        if "error" not in comparison:
            print(f"\n🎯 PORTEFEUILLE:")
            print(f"   Return: {comparison['portfolio']['return_pct']:+.2f}%")
            print(f"   Vol: {comparison['portfolio']['volatility_pct']:.2f}%")
            print(f"   Sharpe: {comparison['portfolio']['sharpe']:.2f}")
            
            print(f"\n📈 BENCHMARK ({comparison['benchmark']['symbol']}):")
            print(f"   Return: {comparison['benchmark']['return_pct']:+.2f}%")
            print(f"   Vol: {comparison['benchmark']['volatility_pct']:.2f}%")
            print(f"   Sharpe: {comparison['benchmark']['sharpe']:.2f}")
            
            print(f"\n⚡ ALPHA: {comparison['comparison']['alpha_pct']:+.2f}%")
            status = "✅ OUTPERFORM" if comparison['comparison']['outperformance'] else "❌ UNDERPERFORM"
            print(f"   {status}")
        
        if turnover:
            print(f"\n🔄 TURNOVER:")
            print(f"   {turnover['turnover_pct']:.1f}% du portefeuille")
            print(f"   Entrées: {turnover['entries_count']} | Sorties: {turnover['exits_count']}")
        
        print(f"\n📁 Rapport exporté: {report_path.name}")
        return report_path


def run_backtest():
    """Lance le backtest sur le dernier portefeuille"""
    # Charge le dernier portefeuille
    portfolio_files = sorted(OUTPUTS.glob("portfolio_*.json"))
    if not portfolio_files:
        print("❌ Aucun portefeuille trouvé")
        return
    
    latest = portfolio_files[-1]
    print(f"📂 Chargement: {latest.name}")
    
    with open(latest) as f:
        data = json.load(f)
    
    portfolio = data.get("portfolio", [])
    
    # Lance le backtest
    backtester = Backtester()
    backtester.generate_report(portfolio, OUTPUTS)


if __name__ == "__main__":
    run_backtest()
