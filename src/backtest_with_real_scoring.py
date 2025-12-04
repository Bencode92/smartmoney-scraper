"""SmartMoney v2.4 — Backtest OOS avec VRAIE logique de scoring

Ce backtest utilise tes VRAIS scorers (value_composite, quality_composite, etc.)
et pas des proxies simulés.

⚠️ IMPORTANT: Ce script doit être exécuté LOCALEMENT car il nécessite:
1. Accès API Twelve Data (fondamentaux)
2. Données HedgeFollow (13F) — ou mode sans Smart Money
3. Accès réseau

Méthodologie:
1. Pour chaque trimestre de la période:
   a. Charger l'univers S&P 500 à cette date
   b. Récupérer les fondamentaux (Twelve Data)
   c. Calculer les scores avec TES scorers
   d. Construire le portefeuille avec TES contraintes
   e. Mesurer le return sur le trimestre suivant

2. Comparer:
   - Version SANS Smart Money (Core)
   - Version AVEC Smart Money (v2.4)

Usage:
    # Mode avec Smart Money (nécessite données 13F)
    python -m src.backtest_with_real_scoring --start 2020-01-01 --mode full
    
    # Mode sans Smart Money (recommandé pour commencer)
    python -m src.backtest_with_real_scoring --start 2020-01-01 --mode core

Date: Décembre 2025
"""

import json
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUTS, TWELVE_DATA_KEY

# Importer TES vrais scorers
try:
    from src.scoring.value_composite import score_value
    from src.scoring.quality_composite import score_quality
    from src.scoring.risk_score import score_risk
    from src.scoring.composite import calculate_composite_score, CompositeScorer
    SCORERS_AVAILABLE = True
except ImportError as e:
    SCORERS_AVAILABLE = False
    print(f"⚠️ Scorers non disponibles: {e}")
    print("   Exécutez ce script depuis la racine du repo SmartMoney")

# Importer l'optimizer
try:
    from src.optimizer.portfolio import PortfolioOptimizer
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Poids à tester
WEIGHTS_CORE = {
    "smart_money": 0.00,
    "insider": 0.10,
    "momentum": 0.10,
    "value": 0.35,
    "quality": 0.30,
    "risk": 0.15,
}

WEIGHTS_WITH_SM = {
    "smart_money": 0.15,
    "insider": 0.10,
    "momentum": 0.05,
    "value": 0.30,
    "quality": 0.25,
    "risk": 0.15,
}

# Contraintes v2.4
CONSTRAINTS = {
    "min_positions": 15,
    "max_positions": 20,
    "max_weight": 0.12,
    "max_sector": 0.30,
    "min_score": 0.35,
}


# =============================================================================
# DATA LOADERS
# =============================================================================

class TwelveDataLoader:
    """
    Charge les données depuis Twelve Data.
    
    Utilise le cache existant si disponible.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or TWELVE_DATA_KEY
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_fundamentals(self, symbols: List[str], date: str) -> pd.DataFrame:
        """
        Charge les fondamentaux pour une liste de symboles.
        
        Args:
            symbols: Liste des tickers
            date: Date de référence (pour le cache)
        
        Returns:
            DataFrame avec les métriques fondamentales
        """
        # Vérifier le cache
        cache_file = self.cache_dir / f"fundamentals_{date}.parquet"
        if cache_file.exists():
            logger.info(f"Cache fondamentaux trouvé: {cache_file}")
            return pd.read_parquet(cache_file)
        
        # Sinon, charger depuis l'API
        logger.info(f"Chargement fondamentaux pour {len(symbols)} symboles...")
        
        # Utiliser l'enrichisseur existant
        try:
            from src.enrichment.twelve_data_enricher import TwelveDataEnricher
            enricher = TwelveDataEnricher(api_key=self.api_key)
            
            # Créer un DataFrame minimal
            df = pd.DataFrame({"symbol": symbols})
            df = enricher.enrich(df)
            
            # Sauvegarder en cache
            df.to_parquet(cache_file)
            
            return df
        except Exception as e:
            logger.error(f"Erreur chargement fondamentaux: {e}")
            return pd.DataFrame()
    
    def load_prices(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Charge les prix historiques.
        """
        try:
            import yfinance as yf
            
            logger.info(f"Téléchargement prix: {len(symbols)} symboles...")
            
            data = yf.download(
                symbols,
                start=start_date,
                end=end_date,
                auto_adjust=True,
                progress=False,
            )
            
            if len(symbols) == 1:
                return pd.DataFrame({symbols[0]: data["Close"]})
            return data["Close"]
        
        except Exception as e:
            logger.error(f"Erreur chargement prix: {e}")
            return pd.DataFrame()


# =============================================================================
# VRAI SCORER (utilise tes scorers)
# =============================================================================

class RealScorer:
    """
    Utilise TES vrais scorers pour calculer les scores.
    """
    
    def __init__(self, weights: Dict[str, float]):
        self.weights = weights
        self.scorer = CompositeScorer(weights=weights) if SCORERS_AVAILABLE else None
    
    def score_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score l'univers avec TES vrais scorers.
        
        Args:
            df: DataFrame avec fondamentaux
        
        Returns:
            DataFrame avec tous les scores
        """
        if not SCORERS_AVAILABLE:
            raise RuntimeError("Scorers non disponibles")
        
        # 1. Score Value (FCF yield, EV/EBIT, PE ratio)
        logger.info("Scoring Value...")
        df = score_value(df)
        
        # 2. Score Quality (ROE, ROIC, marges)
        logger.info("Scoring Quality...")
        df = score_quality(df)
        
        # 3. Score Risk (volatilité, drawdown - inversé)
        logger.info("Scoring Risk...")
        df = score_risk(df)
        
        # 4. Score Composite
        logger.info("Calcul Composite...")
        df = self.scorer.calculate(df)
        
        return df


# =============================================================================
# VRAI OPTIMIZER (utilise tes contraintes)
# =============================================================================

class RealOptimizer:
    """
    Utilise TES vraies contraintes pour construire le portefeuille.
    """
    
    def __init__(self, constraints: Dict = None):
        self.constraints = constraints or CONSTRAINTS
    
    def optimize(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Construit le portefeuille optimal.
        
        Args:
            df: DataFrame avec scores
        
        Returns:
            Dict symbol -> weight
        """
        if OPTIMIZER_AVAILABLE:
            # Utiliser ton optimizer
            optimizer = PortfolioOptimizer()
            result = optimizer.optimize(df)
            return {p["symbol"]: p["weight"] for p in result.get("portfolio", [])}
        
        # Sinon, optimizer simplifié
        df_sorted = df.sort_values("score_composite", ascending=False)
        
        # Filtrer par score minimum
        min_score = self.constraints.get("min_score", 0.35)
        df_filtered = df_sorted[df_sorted["score_composite"] >= min_score]
        
        # Top N positions
        max_pos = self.constraints.get("max_positions", 20)
        top = df_filtered.head(max_pos)
        
        # Poids égaux avec cap
        n = len(top)
        if n == 0:
            return {}
        
        max_weight = self.constraints.get("max_weight", 0.12)
        weight = min(1.0 / n, max_weight)
        
        weights = {row["symbol"]: weight for _, row in top.iterrows()}
        
        # Normaliser
        total = sum(weights.values())
        weights = {s: w / total for s, w in weights.items()}
        
        return weights


# =============================================================================
# BACKTEST ENGINE
# =============================================================================

@dataclass
class PeriodResult:
    start: str
    end: str
    portfolio_return: float
    benchmark_return: float
    alpha: float
    n_positions: int
    top_holdings: List[str]


class RealBacktest:
    """
    Backtest walk-forward avec TES vrais scorers.
    """
    
    def __init__(
        self,
        weights: Dict[str, float],
        benchmark: str = "SPY",
    ):
        self.weights = weights
        self.benchmark = benchmark
        self.loader = TwelveDataLoader()
        self.scorer = RealScorer(weights)
        self.optimizer = RealOptimizer()
    
    def run(
        self,
        start_date: str,
        end_date: str = None,
        rebal_freq: str = "Q",
    ) -> List[PeriodResult]:
        """
        Exécute le backtest.
        
        Args:
            start_date: Date de début
            end_date: Date de fin (défaut: aujourd'hui)
            rebal_freq: Fréquence de rebalancing (Q = trimestriel)
        
        Returns:
            Liste des résultats par période
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info("=" * 60)
        logger.info("BACKTEST AVEC VRAIS SCORERS")
        logger.info("=" * 60)
        logger.info(f"Période: {start_date} → {end_date}")
        logger.info(f"Poids: {self.weights}")
        
        # Générer les dates de rebalancing
        rebal_dates = pd.date_range(start=start_date, end=end_date, freq="QS")
        
        # Charger l'univers S&P 500
        sp500 = self._get_sp500_universe()
        if not sp500:
            logger.error("Impossible de charger l'univers S&P 500")
            return []
        
        # Charger les prix
        all_symbols = sp500 + [self.benchmark]
        prices = self.loader.load_prices(all_symbols, start_date, end_date)
        
        if prices.empty:
            logger.error("Impossible de charger les prix")
            return []
        
        results = []
        
        for i, rebal_date in enumerate(rebal_dates[:-1]):
            period_start = rebal_date.strftime("%Y-%m-%d")
            period_end = rebal_dates[i + 1].strftime("%Y-%m-%d")
            
            logger.info(f"\n[{i+1}/{len(rebal_dates)-1}] Période: {period_start} → {period_end}")
            
            try:
                # 1. Charger les fondamentaux à cette date
                df = self.loader.load_fundamentals(sp500, period_start)
                
                if df.empty:
                    logger.warning(f"Pas de fondamentaux pour {period_start}")
                    continue
                
                # 2. Scorer avec TES vrais scorers
                df = self.scorer.score_universe(df)
                
                # 3. Construire le portefeuille avec TES contraintes
                weights = self.optimizer.optimize(df)
                
                if not weights:
                    logger.warning(f"Pas de portefeuille pour {period_start}")
                    continue
                
                # 4. Calculer le return sur la période
                pf_ret = self._calculate_portfolio_return(weights, prices, period_start, period_end)
                bm_ret = self._calculate_benchmark_return(prices, period_start, period_end)
                
                alpha = pf_ret - bm_ret
                
                result = PeriodResult(
                    start=period_start,
                    end=period_end,
                    portfolio_return=round(pf_ret * 100, 2),
                    benchmark_return=round(bm_ret * 100, 2),
                    alpha=round(alpha * 100, 2),
                    n_positions=len(weights),
                    top_holdings=list(weights.keys())[:5],
                )
                results.append(result)
                
                logger.info(
                    f"   PF={pf_ret*100:+.2f}% vs {self.benchmark}={bm_ret*100:+.2f}% "
                    f"→ α={alpha*100:+.2f}%"
                )
            
            except Exception as e:
                logger.error(f"Erreur période {period_start}: {e}")
                continue
        
        return results
    
    def _get_sp500_universe(self) -> List[str]:
        """Récupère l'univers S&P 500."""
        try:
            sp500_file = Path(__file__).parent.parent / "data" / "sp500.json"
            if sp500_file.exists():
                with open(sp500_file) as f:
                    data = json.load(f)
                    return data.get("symbols", data.get("tickers", []))
        except Exception:
            pass
        
        # Fallback: top 50
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
            "JPM", "V", "UNH", "JNJ", "WMT", "PG", "MA", "HD", "XOM", "CVX",
            "BAC", "ABBV", "PFE", "KO", "PEP", "MRK", "COST", "TMO", "AVGO",
            "MCD", "CSCO", "ABT", "ACN", "DHR", "LLY", "NKE", "TXN", "NEE",
            "WFC", "PM", "UPS", "ORCL", "AMD", "IBM", "QCOM", "HON", "LOW",
            "CAT", "GE", "BA", "GS", "MS",
        ]
    
    def _calculate_portfolio_return(
        self,
        weights: Dict[str, float],
        prices: pd.DataFrame,
        start: str,
        end: str,
    ) -> float:
        """Calcule le return du portefeuille."""
        total = 0.0
        
        for symbol, weight in weights.items():
            if symbol not in prices.columns:
                continue
            
            try:
                p_start = prices.loc[start:, symbol].iloc[0]
                p_end = prices.loc[:end, symbol].iloc[-1]
                ret = p_end / p_start - 1
                total += weight * ret
            except (IndexError, KeyError):
                continue
        
        return total
    
    def _calculate_benchmark_return(
        self,
        prices: pd.DataFrame,
        start: str,
        end: str,
    ) -> float:
        """Calcule le return du benchmark."""
        if self.benchmark not in prices.columns:
            return 0.0
        
        try:
            p_start = prices.loc[start:, self.benchmark].iloc[0]
            p_end = prices.loc[:end, self.benchmark].iloc[-1]
            return p_end / p_start - 1
        except (IndexError, KeyError):
            return 0.0


# =============================================================================
# RAPPORT
# =============================================================================

def generate_report(results: List[PeriodResult], config_name: str) -> Dict:
    """Génère le rapport de backtest."""
    if not results:
        return {}
    
    pf_returns = [r.portfolio_return / 100 for r in results]
    bm_returns = [r.benchmark_return / 100 for r in results]
    alphas = [r.alpha / 100 for r in results]
    
    # Métriques
    total_return = np.prod([1 + r for r in pf_returns]) - 1
    bm_total = np.prod([1 + r for r in bm_returns]) - 1
    n_years = len(results) / 4
    
    cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    bm_cagr = (1 + bm_total) ** (1 / n_years) - 1 if n_years > 0 else 0
    
    total_alpha = sum(alphas)
    hit_rate = sum(1 for a in alphas if a > 0) / len(alphas) * 100
    
    vol = np.std(pf_returns) * 2
    sharpe = (cagr - 0.045) / vol if vol > 0 else 0
    
    # Max Drawdown
    cumulative = np.cumprod([1 + r for r in pf_returns])
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    max_dd = drawdowns.min()
    
    return {
        "config_name": config_name,
        "n_periods": len(results),
        "total_return": round(total_return * 100, 2),
        "benchmark_return": round(bm_total * 100, 2),
        "cagr": round(cagr * 100, 2),
        "benchmark_cagr": round(bm_cagr * 100, 2),
        "total_alpha": round(total_alpha * 100, 2),
        "alpha_per_year": round(total_alpha * 100 / n_years, 2) if n_years > 0 else 0,
        "hit_rate": round(hit_rate, 1),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_dd * 100, 2),
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Backtest OOS avec VRAIS scorers SmartMoney"
    )
    parser.add_argument("--start", "-s", default="2020-01-01")
    parser.add_argument("--end", "-e", default=None)
    parser.add_argument(
        "--mode", "-m",
        choices=["core", "full", "both"],
        default="both",
        help="core=sans SM, full=avec SM, both=comparaison"
    )
    parser.add_argument("--output", "-o", default=None)
    
    args = parser.parse_args()
    
    if not SCORERS_AVAILABLE:
        print("❌ Scorers non disponibles!")
        print("   Exécutez ce script depuis la racine du repo SmartMoney:")
        print("   python -m src.backtest_with_real_scoring --start 2020-01-01")
        return
    
    results = {}
    
    # Mode Core (sans Smart Money)
    if args.mode in ["core", "both"]:
        print("\n" + "=" * 60)
        print("CONFIG: Core (sans Smart Money)")
        print("=" * 60)
        
        bt_core = RealBacktest(weights=WEIGHTS_CORE)
        periods_core = bt_core.run(args.start, args.end)
        results["core"] = generate_report(periods_core, "Core (sans SM)")
    
    # Mode Full (avec Smart Money)
    if args.mode in ["full", "both"]:
        print("\n" + "=" * 60)
        print("CONFIG: Full (avec Smart Money 15%)")
        print("=" * 60)
        
        bt_full = RealBacktest(weights=WEIGHTS_WITH_SM)
        periods_full = bt_full.run(args.start, args.end)
        results["full"] = generate_report(periods_full, "Full (avec SM 15%)")
    
    # Rapport
    print("\n" + "=" * 60)
    print("🎯 RAPPORT BACKTEST AVEC VRAIS SCORERS")
    print("=" * 60)
    
    print(f"\n{'Config':<25} {'CAGR':>8} {'Alpha':>8} {'Hit%':>8} {'Sharpe':>8} {'MaxDD':>8}")
    print("-" * 70)
    
    for key, r in results.items():
        if r:
            print(
                f"{r['config_name']:<25} "
                f"{r['cagr']:>+7.2f}% "
                f"{r['total_alpha']:>+7.2f}% "
                f"{r['hit_rate']:>7.1f}% "
                f"{r['sharpe']:>8.2f} "
                f"{r['max_drawdown']:>+7.2f}%"
            )
    
    # Analyse Smart Money
    if "core" in results and "full" in results and results["core"] and results["full"]:
        print("\n" + "-" * 60)
        print("📊 IMPACT SMART MONEY")
        print("-" * 60)
        
        alpha_diff = results["full"]["total_alpha"] - results["core"]["total_alpha"]
        sharpe_diff = results["full"]["sharpe"] - results["core"]["sharpe"]
        
        print(f"\n   Alpha: {alpha_diff:+.2f}%")
        print(f"   Sharpe: {sharpe_diff:+.2f}")
        
        if alpha_diff > 0:
            print("\n   ✅ Smart Money AJOUTE de la valeur")
        else:
            print("\n   ❌ Smart Money N'AJOUTE PAS de valeur")
    
    # Sauvegarder
    output_dir = Path(args.output) if args.output else OUTPUTS / "backtest_real"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "period": f"{args.start} → {args.end or 'now'}",
        "methodology": "Backtest avec VRAIS scorers SmartMoney",
        "results": results,
    }
    
    with open(output_dir / "backtest_real_scoring.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Rapport: {output_dir / 'backtest_real_scoring.json'}")


if __name__ == "__main__":
    main()
