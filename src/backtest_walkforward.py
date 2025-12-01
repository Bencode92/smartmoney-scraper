"""
Backtest Walk-Forward - Élimine le look-ahead bias

Principe fondamental:
- À chaque date de rebalancement T, on utilise UNIQUEMENT les données ≤ T
- On mesure la performance de T+1 à T_next
- On compare aux benchmarks sur les MÊMES périodes exactes

Auteur: SmartMoney Engine
Version: 1.0.0
"""

import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
import requests

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import (
    OUTPUTS, TWELVE_DATA_KEY, TWELVE_DATA_BASE, 
    TWELVE_DATA_RATE_LIMIT, WEIGHTS, CONSTRAINTS
)


class WalkForwardBacktester:
    """
    Backtest walk-forward sans look-ahead bias.
    
    Méthodologie:
    1. Définir les dates de rebalancement (mensuel, trimestriel, etc.)
    2. À chaque date T:
       - Construire le portefeuille avec données ≤ T uniquement
       - Calculer le turnover vs portefeuille précédent
       - Appliquer les coûts de transaction
    3. Mesurer la performance de T+1 à T_next
    4. Agréger les résultats et comparer aux benchmarks
    """
    
    def __init__(self,
                 prices: pd.DataFrame,
                 build_portfolio_fn: Callable[[pd.Timestamp, pd.DataFrame], pd.Series],
                 benchmarks: Dict[str, pd.Series] = None,
                 tc_bps: float = 10.0,
                 lookback_days: int = 252,
                 risk_free_rate: float = 0.045):
        """
        Initialise le backtester.
        
        Args:
            prices: DataFrame [date x symbol] avec prix de clôture ajustés
            build_portfolio_fn: Fonction(date, prices_history) -> Series[symbol -> weight]
                               Doit retourner les poids du portefeuille à la date donnée
                               en utilisant UNIQUEMENT prices_history (données ≤ date)
            benchmarks: Dict de Series de prix {nom: Series[date -> prix]}
                       Ex: {"SPY": spy_prices, "CAC": cac_prices}
            tc_bps: Coût de transaction en basis points (appliqué au turnover)
            lookback_days: Nombre de jours d'historique pour les calculs (corrélations, etc.)
            risk_free_rate: Taux sans risque annualisé (défaut: 4.5%)
        """
        self.prices = prices.sort_index()
        self.build_portfolio = build_portfolio_fn
        self.benchmarks = benchmarks or {}
        self.tc_bps = tc_bps
        self.lookback_days = lookback_days
        self.risk_free_rate = risk_free_rate
        
        # Calcul des rendements quotidiens
        self.returns = self.prices.pct_change()
        
        # Résultats
        self.results = {}
        self.equity_curve = None
        self.portfolio_returns = None
        self.weights_history = []
        
    def run(self,
            start_date: str = None,
            end_date: str = None,
            rebal_freq: str = "M",
            verbose: bool = True) -> Dict:
        """
        Lance le backtest walk-forward.
        
        Args:
            start_date: Date de début (défaut: lookback jours après premier prix)
            end_date: Date de fin (défaut: dernier prix disponible)
            rebal_freq: Fréquence de rebalancement
                       "W" = hebdomadaire
                       "M" = mensuel (défaut)
                       "Q" = trimestriel
            verbose: Afficher la progression
            
        Returns:
            Dict avec:
                - equity_curve: Series[date -> valeur]
                - returns: Series[date -> rendement quotidien]
                - metrics: Dict des métriques de performance
                - benchmarks: Dict des métriques par benchmark
                - weights_history: Liste des allocations à chaque rebalancement
        """
        if verbose:
            print("\n" + "=" * 60)
            print("📊 BACKTEST WALK-FORWARD")
            print("=" * 60)
        
        # === DÉFINIR LA PÉRIODE ===
        if start_date is None:
            # Commencer après lookback_days pour avoir assez d'historique
            start_idx = min(self.lookback_days, len(self.prices) - 1)
            start_date = self.prices.index[start_idx]
        else:
            start_date = pd.to_datetime(start_date)
            
        if end_date is None:
            end_date = self.prices.index[-1]
        else:
            end_date = pd.to_datetime(end_date)
        
        if verbose:
            print(f"📅 Période: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
            print(f"🔄 Rebalancement: {self._freq_label(rebal_freq)}")
            print(f"💰 Coûts de transaction: {self.tc_bps} bps")
        
        # === DATES DE REBALANCEMENT ===
        mask = (self.prices.index >= start_date) & (self.prices.index <= end_date)
        period_prices = self.prices[mask]
        
        # Resample pour obtenir les fins de période
        rebal_dates = period_prices.resample(rebal_freq).last().index.tolist()
        
        if len(rebal_dates) < 2:
            raise ValueError(f"Pas assez de dates de rebalancement ({len(rebal_dates)}). "
                           f"Essayez une période plus longue ou une fréquence plus élevée.")
        
        if verbose:
            print(f"📆 {len(rebal_dates) - 1} périodes de rebalancement")
        
        # === TRACKING ===
        portfolio_values = [1.0]  # Valeur initiale normalisée à 1
        portfolio_dates = [rebal_dates[0]]
        weights_prev = None
        total_turnover = 0.0
        total_tc = 0.0
        self.weights_history = []
        
        # === BOUCLE WALK-FORWARD ===
        for i in range(len(rebal_dates) - 1):
            date_t = rebal_dates[i]
            date_next = rebal_dates[i + 1]
            
            if verbose:
                print(f"\n  [{i+1}/{len(rebal_dates)-1}] {date_t.strftime('%Y-%m-%d')} → {date_next.strftime('%Y-%m-%d')}")
            
            # === 1. CONSTRUCTION DU PORTEFEUILLE (données ≤ date_t) ===
            hist_start = date_t - timedelta(days=self.lookback_days)
            prices_history = self.prices.loc[hist_start:date_t]
            
            try:
                weights = self.build_portfolio(date_t, prices_history)
                
                # Normaliser et aligner
                weights = weights.reindex(self.prices.columns).fillna(0)
                weight_sum = weights.sum()
                if weight_sum > 0:
                    weights = weights / weight_sum
                else:
                    raise ValueError("Poids nuls")
                    
            except Exception as e:
                if verbose:
                    print(f"    ⚠️ Erreur construction: {e}")
                # Fallback: garder le portefeuille précédent ou equal-weight
                if weights_prev is not None:
                    weights = weights_prev
                else:
                    # Equal weight sur les titres avec prix valides
                    valid = prices_history.iloc[-1].dropna().index
                    weights = pd.Series(1.0 / len(valid), index=valid)
                    weights = weights.reindex(self.prices.columns).fillna(0)
            
            # Sauvegarder les poids
            self.weights_history.append({
                "date": date_t.strftime("%Y-%m-%d"),
                "weights": weights[weights > 0].to_dict()
            })
            
            # === 2. CALCUL DU TURNOVER ET DES COÛTS ===
            if weights_prev is not None:
                turnover = (weights - weights_prev).abs().sum()
            else:
                turnover = weights.abs().sum()  # Premier rebalancement = 100%
            
            tc_cost = turnover * (self.tc_bps / 10000)
            total_turnover += turnover
            total_tc += tc_cost
            
            if verbose:
                n_positions = (weights > 0.001).sum()
                print(f"    ✓ {n_positions} positions | Turnover: {turnover*100:.1f}% | TC: {tc_cost*100:.2f}%")
            
            # === 3. PERFORMANCE SUR LA PÉRIODE [date_t+1, date_next] ===
            # Rendements APRÈS date_t jusqu'à date_next inclus
            period_mask = (self.returns.index > date_t) & (self.returns.index <= date_next)
            period_returns = self.returns[period_mask]
            
            # Valeur courante après coûts de transaction
            current_value = portfolio_values[-1] * (1 - tc_cost)
            
            # Simuler chaque jour
            for idx, daily_ret in period_returns.iterrows():
                # Rendement du portefeuille = somme pondérée des rendements
                port_ret = (weights * daily_ret.fillna(0)).sum()
                current_value *= (1 + port_ret)
                portfolio_values.append(current_value)
                portfolio_dates.append(idx)
            
            weights_prev = weights.copy()
        
        # === CONSTRUIRE LES SÉRIES DE RÉSULTATS ===
        self.equity_curve = pd.Series(portfolio_values, index=portfolio_dates)
        self.portfolio_returns = self.equity_curve.pct_change().dropna()
        
        # === MÉTRIQUES DU PORTEFEUILLE ===
        metrics = self._calculate_metrics(self.portfolio_returns, self.equity_curve)
        metrics["total_turnover_pct"] = round(total_turnover * 100, 1)
        metrics["total_tc_pct"] = round(total_tc * 100, 2)
        metrics["avg_turnover_per_rebal_pct"] = round(total_turnover / (len(rebal_dates) - 1) * 100, 1)
        metrics["n_rebalancings"] = len(rebal_dates) - 1
        metrics["period_start"] = start_date.strftime("%Y-%m-%d")
        metrics["period_end"] = end_date.strftime("%Y-%m-%d")
        
        # === MÉTRIQUES DES BENCHMARKS ===
        benchmark_metrics = {}
        for name, bench_prices in self.benchmarks.items():
            try:
                # Aligner sur les mêmes dates que le portefeuille
                bench_aligned = bench_prices.reindex(self.equity_curve.index).ffill()
                
                if bench_aligned.isna().all():
                    if verbose:
                        print(f"\n⚠️ Benchmark {name}: pas de données sur la période")
                    continue
                
                # Normaliser à 1 au début
                bench_equity = bench_aligned / bench_aligned.iloc[0]
                bench_returns = bench_equity.pct_change().dropna()
                
                bench_met = self._calculate_metrics(bench_returns, bench_equity)
                benchmark_metrics[name] = bench_met
                
                # Alpha
                alpha = metrics["annual_return_pct"] - bench_met["annual_return_pct"]
                metrics[f"alpha_vs_{name}_pct"] = round(alpha, 2)
                
            except Exception as e:
                if verbose:
                    print(f"\n⚠️ Erreur benchmark {name}: {e}")
        
        # === RÉSULTATS FINAUX ===
        self.results = {
            "generated_at": datetime.now().isoformat(),
            "config": {
                "rebal_freq": rebal_freq,
                "tc_bps": self.tc_bps,
                "lookback_days": self.lookback_days,
                "risk_free_rate": self.risk_free_rate
            },
            "portfolio": metrics,
            "benchmarks": benchmark_metrics,
            "equity_curve": self.equity_curve.to_dict(),
            "weights_history": self.weights_history
        }
        
        # === AFFICHAGE RÉSUMÉ ===
        if verbose:
            self._print_summary(metrics, benchmark_metrics)
        
        return self.results
    
    def _calculate_metrics(self, returns: pd.Series, equity: pd.Series) -> Dict:
        """Calcule les métriques de performance standard."""
        n_days = len(returns)
        ann_factor = 252
        
        if n_days == 0:
            return {"error": "Pas de données"}
        
        # === RENDEMENTS ===
        total_return = equity.iloc[-1] / equity.iloc[0] - 1
        annual_return = (1 + total_return) ** (ann_factor / n_days) - 1 if n_days > 0 else 0
        
        # === VOLATILITÉ ===
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(ann_factor)
        
        # === SHARPE RATIO ===
        rf_daily = self.risk_free_rate / ann_factor
        excess_returns = returns - rf_daily
        
        if excess_returns.std() > 0:
            sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(ann_factor)
        else:
            sharpe = 0
        
        # === SORTINO RATIO (downside vol) ===
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_vol = downside_returns.std() * np.sqrt(ann_factor)
            sortino = (annual_return - self.risk_free_rate) / downside_vol if downside_vol > 0 else 0
        else:
            sortino = float('inf')  # Pas de rendements négatifs
        
        # === DRAWDOWN ===
        peak = equity.cummax()
        drawdown = (equity - peak) / peak
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()
        
        # Durée du drawdown max
        in_dd = drawdown < 0
        if in_dd.any():
            dd_periods = (~in_dd).cumsum()
            dd_lengths = in_dd.groupby(dd_periods).sum()
            max_dd_duration = dd_lengths.max() if len(dd_lengths) > 0 else 0
        else:
            max_dd_duration = 0
        
        # === VAR / CVAR (95%) ===
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean() if (returns <= var_95).any() else var_95
        
        # === CALMAR RATIO ===
        calmar = annual_return / abs(max_dd) if max_dd != 0 else float('inf')
        
        # === WIN RATE ===
        win_rate = (returns > 0).mean()
        
        # === BEST / WORST ===
        best_day = returns.max()
        worst_day = returns.min()
        
        return {
            "total_return_pct": round(total_return * 100, 2),
            "annual_return_pct": round(annual_return * 100, 2),
            "annual_vol_pct": round(annual_vol * 100, 2),
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "calmar": round(calmar, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "max_drawdown_date": max_dd_date.strftime("%Y-%m-%d") if pd.notna(max_dd_date) else None,
            "max_drawdown_duration_days": int(max_dd_duration),
            "var_95_daily_pct": round(var_95 * 100, 2),
            "cvar_95_daily_pct": round(cvar_95 * 100, 2),
            "win_rate_pct": round(win_rate * 100, 1),
            "best_day_pct": round(best_day * 100, 2),
            "worst_day_pct": round(worst_day * 100, 2),
            "n_trading_days": n_days
        }
    
    def _freq_label(self, freq: str) -> str:
        """Retourne le label lisible pour une fréquence."""
        labels = {
            "W": "Hebdomadaire",
            "M": "Mensuel",
            "Q": "Trimestriel",
            "Y": "Annuel"
        }
        return labels.get(freq, freq)
    
    def _print_summary(self, metrics: Dict, benchmarks: Dict):
        """Affiche le résumé des résultats."""
        print("\n" + "=" * 60)
        print("📈 RÉSULTATS DU BACKTEST")
        print("=" * 60)
        
        print(f"\n🎯 PORTEFEUILLE:")
        print(f"   Return total: {metrics['total_return_pct']:+.2f}%")
        print(f"   Return annualisé: {metrics['annual_return_pct']:+.2f}%")
        print(f"   Volatilité annualisée: {metrics['annual_vol_pct']:.2f}%")
        print(f"   Sharpe: {metrics['sharpe']:.2f}")
        print(f"   Sortino: {metrics['sortino']:.2f}")
        print(f"   Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
        print(f"   VaR 95% (daily): {metrics['var_95_daily_pct']:.2f}%")
        print(f"   CVaR 95% (daily): {metrics['cvar_95_daily_pct']:.2f}%")
        print(f"   Win Rate: {metrics['win_rate_pct']:.1f}%")
        print(f"   Turnover moyen/rebal: {metrics['avg_turnover_per_rebal_pct']:.1f}%")
        print(f"   Coûts totaux: {metrics['total_tc_pct']:.2f}%")
        
        for name, bench in benchmarks.items():
            if "error" not in bench:
                print(f"\n📊 {name}:")
                print(f"   Return annualisé: {bench['annual_return_pct']:+.2f}%")
                print(f"   Volatilité: {bench['annual_vol_pct']:.2f}%")
                print(f"   Sharpe: {bench['sharpe']:.2f}")
                print(f"   Max Drawdown: {bench['max_drawdown_pct']:.2f}%")
                
                alpha_key = f"alpha_vs_{name}_pct"
                if alpha_key in metrics:
                    alpha = metrics[alpha_key]
                    emoji = "✅" if alpha > 0 else "❌"
                    print(f"   {emoji} Alpha: {alpha:+.2f}%")
    
    def export_report(self, output_dir: Path) -> Path:
        """
        Exporte le rapport de backtest en JSON.
        
        Args:
            output_dir: Dossier de sortie
            
        Returns:
            Path du fichier créé
        """
        if not self.results:
            raise ValueError("Aucun résultat. Lancez run() d'abord.")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = output_dir / "backtest_walkforward.json"
        
        # Convertir les timestamps en strings pour JSON
        results_json = self._prepare_for_json(self.results)
        
        with open(report_path, "w") as f:
            json.dump(results_json, f, indent=2, default=str)
        
        print(f"\n📁 Rapport exporté: {report_path}")
        return report_path
    
    def _prepare_for_json(self, obj):
        """Prépare un objet pour la sérialisation JSON."""
        if isinstance(obj, dict):
            return {k: self._prepare_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._prepare_for_json(v) for v in obj]
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj


class PriceDataLoader:
    """
    Utilitaire pour charger les prix historiques depuis Twelve Data
    et les mettre en cache pour le backtest.
    """
    
    def __init__(self):
        self._last_api_call = 0
        
    def _rate_limit(self):
        """Respecte le rate limit Twelve Data."""
        elapsed = time.time() - self._last_api_call
        wait = (60 / TWELVE_DATA_RATE_LIMIT) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_api_call = time.time()
    
    def fetch_prices(self, 
                     symbols: List[str], 
                     start_date: str = None,
                     outputsize: int = 900) -> pd.DataFrame:
        """
        Récupère les prix historiques pour une liste de symboles.
        
        Args:
            symbols: Liste des tickers
            start_date: Date de début (optionnel)
            outputsize: Nombre de jours max à récupérer
            
        Returns:
            DataFrame [date x symbol] avec les prix de clôture ajustés
        """
        if not TWELVE_DATA_KEY:
            raise ValueError("TWELVE_DATA_KEY non définie")
        
        all_prices = {}
        
        for i, symbol in enumerate(symbols):
            print(f"  [{i+1}/{len(symbols)}] {symbol}...", end=" ")
            
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
                        df = pd.DataFrame(data["values"])
                        df["datetime"] = pd.to_datetime(df["datetime"])
                        df["close"] = df["close"].astype(float)
                        df = df.set_index("datetime")["close"]
                        all_prices[symbol] = df
                        print("✓")
                    else:
                        print(f"⚠️ Pas de données")
                else:
                    print(f"⚠️ HTTP {resp.status_code}")
                    
            except Exception as e:
                print(f"❌ {e}")
        
        if not all_prices:
            raise ValueError("Aucun prix récupéré")
        
        # Combiner en DataFrame
        prices = pd.DataFrame(all_prices)
        prices = prices.sort_index()
        
        # Filtrer par date de début si spécifié
        if start_date:
            prices = prices.loc[start_date:]
        
        print(f"\n✅ {len(prices)} jours de prix pour {len(prices.columns)} tickers")
        return prices
    
    def load_from_cache(self, cache_path: Path) -> pd.DataFrame:
        """Charge les prix depuis un fichier cache."""
        cache_path = Path(cache_path)
        
        if cache_path.suffix == ".parquet":
            return pd.read_parquet(cache_path)
        elif cache_path.suffix == ".csv":
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df
        else:
            raise ValueError(f"Format non supporté: {cache_path.suffix}")
    
    def save_to_cache(self, prices: pd.DataFrame, cache_path: Path):
        """Sauvegarde les prix dans un fichier cache."""
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        if cache_path.suffix == ".parquet":
            prices.to_parquet(cache_path)
        elif cache_path.suffix == ".csv":
            prices.to_csv(cache_path)
        else:
            raise ValueError(f"Format non supporté: {cache_path.suffix}")
        
        print(f"💾 Cache sauvegardé: {cache_path}")


def create_simple_portfolio_builder(engine_class):
    """
    Crée une fonction de construction de portefeuille compatible avec le backtester.
    
    Args:
        engine_class: Classe SmartMoneyEngine (ou équivalent)
        
    Returns:
        Fonction(date, prices_history) -> Series[symbol -> weight]
    """
    def build_portfolio(date: pd.Timestamp, prices_history: pd.DataFrame) -> pd.Series:
        """
        Construit le portefeuille à une date donnée.
        N'utilise QUE prices_history (données ≤ date).
        """
        engine = engine_class()
        
        # 1. Charger les données de base (13F, insiders)
        engine.load_data()
        
        # 2. Filtrer l'univers sur les symboles avec des prix
        valid_symbols = prices_history.columns.tolist()
        engine.universe = engine.universe[engine.universe["symbol"].isin(valid_symbols)]
        
        if engine.universe.empty:
            return pd.Series(dtype=float)
        
        # 3. Calculer les métriques depuis l'historique de prix
        returns = prices_history.pct_change().dropna()
        
        for symbol in engine.universe["symbol"]:
            if symbol in prices_history.columns:
                prices = prices_history[symbol].dropna()
                
                if len(prices) >= 63:
                    # Perf 3M
                    perf_3m = (prices.iloc[-1] / prices.iloc[-63] - 1) * 100
                    engine.universe.loc[engine.universe["symbol"] == symbol, "perf_3m"] = perf_3m
                
                if len(prices) >= 30:
                    # Volatilité 30j
                    ret_30d = prices.pct_change().iloc[-30:]
                    vol_30d = ret_30d.std() * np.sqrt(252) * 100
                    engine.universe.loc[engine.universe["symbol"] == symbol, "vol_30d"] = vol_30d
                
                # Prix actuel
                engine.universe.loc[engine.universe["symbol"] == symbol, "td_price"] = prices.iloc[-1]
        
        # 4. Calculer les scores
        engine.calculate_scores()
        engine.apply_filters()
        
        # 5. Optimisation HRP avec vraies corrélations
        if len(returns.columns) > 1:
            # Filtrer sur l'univers actuel
            univ_symbols = engine.universe["symbol"].tolist()
            valid_cols = [c for c in returns.columns if c in univ_symbols]
            
            if len(valid_cols) > 1:
                corr = returns[valid_cols].corr()
                # Shrinkage Ledoit-Wolf
                shrinkage = 0.2
                corr = (1 - shrinkage) * corr + shrinkage * np.eye(len(corr))
                engine._real_correlation = corr
        
        engine.optimize()
        
        # Retourner les poids
        if engine.portfolio.empty:
            return pd.Series(dtype=float)
        
        weights = engine.portfolio.set_index("symbol")["weight"]
        return weights
    
    return build_portfolio


def run_walkforward_backtest():
    """
    Fonction standalone pour lancer un backtest walk-forward
    sur le dernier portefeuille généré.
    """
    print("=" * 60)
    print("🚀 LANCEMENT DU BACKTEST WALK-FORWARD")
    print("=" * 60)
    
    # Trouver le dernier portefeuille
    dated_dirs = sorted([
        d for d in OUTPUTS.iterdir()
        if d.is_dir() and d.name != "latest"
    ])
    
    if not dated_dirs:
        print("❌ Aucun portefeuille trouvé dans outputs/")
        return
    
    latest_dir = dated_dirs[-1]
    portfolio_file = latest_dir / "portfolio.json"
    
    if not portfolio_file.exists():
        print(f"❌ Fichier non trouvé: {portfolio_file}")
        return
    
    # Charger le portefeuille
    with open(portfolio_file) as f:
        data = json.load(f)
    
    portfolio = data.get("portfolio", [])
    symbols = [p["symbol"] for p in portfolio]
    
    print(f"📂 Portfolio: {portfolio_file}")
    print(f"📊 {len(symbols)} tickers à backtester")
    
    # Vérifier si on a un cache de prix
    cache_path = OUTPUTS / "price_cache.parquet"
    loader = PriceDataLoader()
    
    if cache_path.exists():
        print(f"\n💾 Chargement du cache: {cache_path}")
        prices = loader.load_from_cache(cache_path)
        
        # Vérifier qu'on a tous les symboles
        missing = set(symbols) - set(prices.columns)
        if missing:
            print(f"⚠️ Symboles manquants dans le cache: {missing}")
            print("   Téléchargement des données manquantes...")
            new_prices = loader.fetch_prices(list(missing))
            prices = pd.concat([prices, new_prices], axis=1)
            loader.save_to_cache(prices, cache_path)
    else:
        print(f"\n📥 Téléchargement des prix historiques...")
        # Ajouter les benchmarks
        all_symbols = symbols + ["SPY", "CAC"]
        prices = loader.fetch_prices(all_symbols, outputsize=900)
        loader.save_to_cache(prices, cache_path)
    
    # Séparer benchmarks et portfolio
    benchmark_cols = [c for c in ["SPY", "CAC"] if c in prices.columns]
    benchmarks = {col: prices[col] for col in benchmark_cols}
    portfolio_prices = prices.drop(columns=benchmark_cols, errors="ignore")
    
    # Créer le builder de portefeuille
    from src.engine import SmartMoneyEngine
    build_fn = create_simple_portfolio_builder(SmartMoneyEngine)
    
    # Lancer le backtest
    backtester = WalkForwardBacktester(
        prices=portfolio_prices,
        build_portfolio_fn=build_fn,
        benchmarks=benchmarks,
        tc_bps=10,
        lookback_days=252
    )
    
    results = backtester.run(
        rebal_freq="M",
        verbose=True
    )
    
    # Exporter le rapport
    backtester.export_report(latest_dir)
    
    # Retourner le statut de validation
    portfolio_return = results["portfolio"].get("annual_return_pct", 0)
    spy_return = results.get("benchmarks", {}).get("SPY", {}).get("annual_return_pct", 0)
    
    beats_spy = portfolio_return > spy_return
    
    print("\n" + "=" * 60)
    if beats_spy:
        print(f"✅ VALIDATION: Portefeuille bat SPY ({portfolio_return:+.2f}% vs {spy_return:+.2f}%)")
    else:
        print(f"❌ VALIDATION: Portefeuille sous-performe SPY ({portfolio_return:+.2f}% vs {spy_return:+.2f}%)")
    print("=" * 60)
    
    return beats_spy


if __name__ == "__main__":
    run_walkforward_backtest()
