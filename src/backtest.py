"""Backtest & Benchmark - Compare le portefeuille au S&P 500 et CAC 40"""
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
    """Backtest du portefeuille et comparaison avec benchmarks"""
    
    def __init__(self):
        self._last_api_call = 0
        self.benchmarks = {
            "SPY": {"name": "S&P 500", "currency": "USD"},
            "CAC": {"name": "CAC 40", "currency": "EUR"}  # Twelve Data symbol for CAC 40
        }
        self.results = {}
        self.validation_result = None
    
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
        history = []
        
        for dated_dir in sorted(OUTPUTS.iterdir()):
            if dated_dir.is_dir() and dated_dir.name != "latest":
                portfolio_file = dated_dir / "portfolio.json"
                if portfolio_file.exists():
                    try:
                        with open(portfolio_file) as f:
                            data = json.load(f)
                            history.append({
                                "date": dated_dir.name,
                                "file": portfolio_file.name,
                                "positions": len(data.get("portfolio", [])),
                                "portfolio": data.get("portfolio", []),
                                "metrics": data.get("metrics", {})
                            })
                    except Exception as e:
                        print(f"⚠️ Error loading {portfolio_file}: {e}")
        
        return history
    
    def calculate_turnover(self, portfolio_old: list, portfolio_new: list) -> dict:
        """Calcule le turnover entre deux portefeuilles"""
        symbols_old = {p["symbol"]: p["weight"] for p in portfolio_old}
        symbols_new = {p["symbol"]: p["weight"] for p in portfolio_new}
        
        all_symbols = set(symbols_old.keys()) | set(symbols_new.keys())
        
        entries = set(symbols_new.keys()) - set(symbols_old.keys())
        exits = set(symbols_old.keys()) - set(symbols_new.keys())
        unchanged = set(symbols_old.keys()) & set(symbols_new.keys())
        
        total_change = 0
        for symbol in all_symbols:
            old_weight = symbols_old.get(symbol, 0)
            new_weight = symbols_new.get(symbol, 0)
            total_change += abs(new_weight - old_weight)
        
        turnover = total_change / 2
        
        return {
            "turnover_pct": round(turnover * 100, 2),
            "entries": list(entries),
            "exits": list(exits),
            "entries_count": len(entries),
            "exits_count": len(exits),
            "unchanged_count": len(unchanged)
        }
    
    def fetch_benchmark(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """Récupère l'historique d'un benchmark"""
        print(f"📊 Récupération benchmark {symbol}...")
        return self._fetch_time_series(symbol, days)
    
    def calculate_benchmark_metrics(self, df: pd.DataFrame, risk_free_rate: float = 4.5) -> dict:
        """Calcule les métriques pour un benchmark"""
        if df.empty:
            return {"error": "No data"}
        
        df["return"] = df["close"].pct_change()
        total_return = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
        vol = df["return"].std() * np.sqrt(252) * 100
        
        # Drawdown
        cumulative = (1 + df["return"].dropna()).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min() * 100
        
        # Sharpe (annualisé sur 90 jours = /4)
        sharpe = (total_return - risk_free_rate/4) / vol if vol > 0 else 0
        
        return {
            "return_pct": round(total_return, 2),
            "volatility_pct": round(vol, 2),
            "sharpe": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "prices": df[["datetime", "close"]].to_dict("records")[-90:]  # Derniers 90 jours pour graphique
        }
    
    def compare_to_benchmarks(self, portfolio: list, days: int = 90) -> dict:
        """Compare le portefeuille à plusieurs benchmarks (SPY + CAC40)"""
        print("\n" + "="*60)
        print("📊 BACKTEST vs BENCHMARKS (SPY + CAC40)")
        print("="*60)
        
        risk_free_rate = 4.5
        
        # Récupère tous les benchmarks
        benchmarks_data = {}
        for symbol, info in self.benchmarks.items():
            df = self.fetch_benchmark(symbol, days)
            if not df.empty:
                metrics = self.calculate_benchmark_metrics(df, risk_free_rate)
                metrics["name"] = info["name"]
                metrics["currency"] = info["currency"]
                metrics["symbol"] = symbol
                benchmarks_data[symbol] = metrics
            else:
                print(f"⚠️ Impossible de récupérer {symbol}")
        
        if not benchmarks_data:
            return {"error": "Impossible de récupérer les benchmarks"}
        
        # Portefeuille (approximation basée sur perf_3m pondérée)
        portfolio_return = sum(p.get("weight", 0) * (p.get("perf_3m", 0) or 0) for p in portfolio)
        portfolio_vol = np.sqrt(sum(p.get("weight", 0)**2 * ((p.get("vol_30d", 25) or 25)/100)**2 for p in portfolio)) * 100
        
        # Calcul du drawdown portfolio (approximation)
        max_dd_portfolio = -portfolio_vol * 0.5  # Estimation conservative
        
        sharpe_portfolio = (portfolio_return - risk_free_rate/4) / portfolio_vol if portfolio_vol > 0 else 0
        
        # Comparaisons avec chaque benchmark
        comparisons = {}
        for symbol, bench in benchmarks_data.items():
            if "error" not in bench:
                alpha = portfolio_return - bench["return_pct"]
                comparisons[symbol] = {
                    "alpha_pct": round(alpha, 2),
                    "outperformance": alpha > 0,
                    "sharpe_diff": round(sharpe_portfolio - bench["sharpe"], 2),
                    "vol_diff": round(portfolio_vol - bench["volatility_pct"], 2)
                }
        
        results = {
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "benchmarks": benchmarks_data,
            "portfolio": {
                "return_pct": round(portfolio_return, 2),
                "volatility_pct": round(portfolio_vol, 2),
                "sharpe": round(sharpe_portfolio, 2),
                "max_drawdown_pct": round(max_dd_portfolio, 2),
                "positions": len(portfolio)
            },
            "comparisons": comparisons
        }
        
        self.results = results
        return results
    
    def validate_outperformance(self, strict: bool = False) -> dict:
        """
        Valide que le portefeuille bat les benchmarks.
        
        Args:
            strict: Si True, exige de battre SPY ET CAC. Si False, un seul suffit.
        
        Returns:
            dict avec:
                - valid: bool - portefeuille valide ou non
                - beats_spy: bool
                - beats_cac: bool
                - portfolio_return: float
                - spy_return: float
                - cac_return: float
                - message: str - explication
        """
        if not self.results or "error" in self.results:
            return {
                "valid": False,
                "message": "Pas de données de backtest disponibles",
                "beats_spy": False,
                "beats_cac": False
            }
        
        portfolio_return = self.results.get("portfolio", {}).get("return_pct", 0)
        spy_return = self.results.get("benchmarks", {}).get("SPY", {}).get("return_pct", 0)
        cac_return = self.results.get("benchmarks", {}).get("CAC", {}).get("return_pct", 0)
        
        beats_spy = portfolio_return > spy_return
        beats_cac = portfolio_return > cac_return
        
        if strict:
            valid = beats_spy and beats_cac
        else:
            valid = beats_spy or beats_cac
        
        # Message explicatif
        if valid:
            if beats_spy and beats_cac:
                message = f"✅ Portefeuille bat SPY ET CAC sur 3M ({portfolio_return:+.2f}% vs SPY {spy_return:+.2f}% vs CAC {cac_return:+.2f}%)"
            elif beats_spy:
                message = f"⚠️ Portefeuille bat SPY mais pas CAC ({portfolio_return:+.2f}% vs SPY {spy_return:+.2f}% vs CAC {cac_return:+.2f}%)"
            else:
                message = f"⚠️ Portefeuille bat CAC mais pas SPY ({portfolio_return:+.2f}% vs SPY {spy_return:+.2f}% vs CAC {cac_return:+.2f}%)"
        else:
            message = f"❌ Portefeuille sous-performe les benchmarks ({portfolio_return:+.2f}% vs SPY {spy_return:+.2f}% vs CAC {cac_return:+.2f}%)"
        
        self.validation_result = {
            "valid": valid,
            "beats_spy": beats_spy,
            "beats_cac": beats_cac,
            "beats_all": beats_spy and beats_cac,
            "portfolio_return": portfolio_return,
            "spy_return": spy_return,
            "cac_return": cac_return,
            "alpha_spy": round(portfolio_return - spy_return, 2),
            "alpha_cac": round(portfolio_return - cac_return, 2),
            "message": message,
            "strict_mode": strict
        }
        
        return self.validation_result
    
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
    
    def generate_report(self, portfolio: list, output_dir: Path, validate: bool = True, strict: bool = True) -> dict:
        """
        Génère un rapport de backtest complet avec multi-benchmarks.
        
        Args:
            portfolio: Liste des positions
            output_dir: Dossier daté (ex: outputs/2025-11-28/)
            validate: Si True, valide la surperformance
            strict: Si True, exige de battre SPY ET CAC
            
        Returns:
            dict avec le rapport et la validation
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Compare aux benchmarks (SPY + CAC40)
        comparison = self.compare_to_benchmarks(portfolio)
        
        # Valide la surperformance
        validation = None
        if validate and "error" not in comparison:
            validation = self.validate_outperformance(strict=strict)
            print("\n" + "-"*60)
            print("🎯 VALIDATION SURPERFORMANCE")
            print("-"*60)
            print(validation["message"])
            if not validation["valid"]:
                print("⚠️  Le portefeuille ne bat pas les benchmarks!")
                print("   Recommandation: Revoir la stratégie de sélection")
        
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
            "validation": validation,
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
        report_path = output_dir / "backtest.json"
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
            print(f"   Max DD: {comparison['portfolio']['max_drawdown_pct']:.2f}%")
            
            for symbol, bench in comparison.get("benchmarks", {}).items():
                if "error" not in bench:
                    print(f"\n📈 {bench['name']} ({symbol}):")
                    print(f"   Return: {bench['return_pct']:+.2f}%")
                    print(f"   Vol: {bench['volatility_pct']:.2f}%")
                    print(f"   Sharpe: {bench['sharpe']:.2f}")
                    print(f"   Max DD: {bench['max_drawdown_pct']:.2f}%")
            
            print(f"\n⚡ ALPHA vs SPY: {comparison['comparisons'].get('SPY', {}).get('alpha_pct', 'N/A')}%")
            print(f"⚡ ALPHA vs CAC: {comparison['comparisons'].get('CAC', {}).get('alpha_pct', 'N/A')}%")
        
        if turnover:
            print(f"\n🔄 TURNOVER:")
            print(f"   {turnover['turnover_pct']:.1f}% du portefeuille")
            print(f"   Entrées: {turnover['entries_count']} | Sorties: {turnover['exits_count']}")
        
        print(f"\n📁 Rapport exporté: {output_dir.name}/{report_path.name}")
        
        return {
            "report": report,
            "report_path": report_path,
            "validation": validation
        }


def run_backtest():
    """Lance le backtest sur le dernier portefeuille"""
    dated_dirs = sorted([
        d for d in OUTPUTS.iterdir() 
        if d.is_dir() and d.name != "latest"
    ])
    
    if not dated_dirs:
        print("❌ Aucun portefeuille trouvé")
        return
    
    latest_dir = dated_dirs[-1]
    portfolio_file = latest_dir / "portfolio.json"
    
    if not portfolio_file.exists():
        print(f"❌ Fichier non trouvé: {portfolio_file}")
        return
    
    print(f"📂 Chargement: {portfolio_file}")
    
    with open(portfolio_file) as f:
        data = json.load(f)
    
    portfolio = data.get("portfolio", [])
    
    # Lance le backtest avec validation stricte
    backtester = Backtester()
    result = backtester.generate_report(portfolio, latest_dir, validate=True, strict=True)
    
    # Retourne le statut de validation
    if result.get("validation"):
        return result["validation"]["valid"]
    return True


if __name__ == "__main__":
    run_backtest()
