"""SmartMoney v2.3 — Backtest Engine

Backtest walk-forward avec les nouveaux scores v2.3.

Features:
- Walk-forward avec rebalancement trimestriel
- Scoring v2.3 (value, quality, risk)
- Filtres de liquidité et hard filters
- Contrôle look-ahead
- Métriques complètes
- Comparaison benchmark

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import (
        WEIGHTS_V23, CONSTRAINTS_V23, BACKTEST_V23,
        VALIDATION_V23, RISK_MANAGEMENT
    )
except ImportError:
    WEIGHTS_V23 = {
        "smart_money": 0.15, "insider": 0.10, "momentum": 0.05,
        "value": 0.30, "quality": 0.25, "risk": 0.15,
    }
    CONSTRAINTS_V23 = {
        "min_positions": 12, "max_positions": 20,
        "max_weight": 0.12, "min_score": 0.40,
    }
    BACKTEST_V23 = {
        "rebal_freq": "Q", "tc_bps": 12.0,
        "start_date": "2010-01-01", "end_date": "2024-12-31",
    }
    VALIDATION_V23 = {"min_sharpe": 0.55}
    RISK_MANAGEMENT = {"max_dd_target": -0.25, "max_dd_hard": -0.35}

from .metrics import calculate_metrics, PerformanceMetrics
from .stress_tests import StressTester, StressTestSuite

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Résultat complet d'un backtest."""
    # Métriques principales
    metrics: PerformanceMetrics
    
    # Séries temporelles
    returns: pd.Series
    cumulative_returns: pd.Series
    drawdowns: pd.Series
    
    # Historique
    weights_history: pd.DataFrame
    holdings_history: List[Dict]
    
    # Benchmark
    benchmark_returns: Optional[pd.Series] = None
    benchmark_cumulative: Optional[pd.Series] = None
    
    # Stress tests
    stress_tests: Optional[StressTestSuite] = None
    
    # Validation
    validation_passed: bool = False
    validation_notes: List[str] = field(default_factory=list)


class BacktestEngine:
    """
    Moteur de backtest walk-forward v2.3.
    
    Pipeline:
    1. Charger données historiques
    2. Pour chaque date de rebalancement:
       a. Filtrer look-ahead
       b. Appliquer filtres liquidité + hard filters
       c. Calculer scores v2.3
       d. Sélectionner top N
       e. Optimiser poids (HRP)
    3. Calculer rendements avec coûts de transaction
    4. Calculer métriques
    5. Valider vs critères
    
    Example:
        >>> engine = BacktestEngine()
        >>> result = engine.run(
        ...     prices=prices_df,
        ...     fundamentals=fundamentals_df,
        ...     start_date="2010-01-01",
        ...     end_date="2024-12-31",
        ... )
        >>> print(f"Sharpe: {result.metrics.sharpe_ratio}")
    """
    
    def __init__(
        self,
        rebal_freq: str = None,
        tc_bps: float = None,
        min_positions: int = None,
        max_positions: int = None,
        max_weight: float = None,
    ):
        """
        Args:
            rebal_freq: Fréquence de rebalancement ("Q", "M", "W")
            tc_bps: Coûts de transaction en basis points
            min_positions: Nombre minimum de positions
            max_positions: Nombre maximum de positions
            max_weight: Poids maximum par position
        """
        self.rebal_freq = rebal_freq or BACKTEST_V23["rebal_freq"]
        self.tc_bps = tc_bps or BACKTEST_V23["tc_bps"]
        self.min_positions = min_positions or CONSTRAINTS_V23["min_positions"]
        self.max_positions = max_positions or CONSTRAINTS_V23["max_positions"]
        self.max_weight = max_weight or CONSTRAINTS_V23["max_weight"]
        
        # Lazy imports
        self._scorers_loaded = False
    
    def _load_scorers(self):
        """Charge les modules de scoring (lazy loading)."""
        if self._scorers_loaded:
            return
        
        from src.scoring.composite import calculate_all_scores
        from src.filters.liquidity import apply_liquidity_filters
        from src.filters.hard_filters import apply_hard_filters
        from src.filters.look_ahead import filter_by_publication_date
        
        self._calculate_scores = calculate_all_scores
        self._apply_liquidity = apply_liquidity_filters
        self._apply_hard_filters = apply_hard_filters
        self._filter_look_ahead = filter_by_publication_date
        
        self._scorers_loaded = True
    
    def run(
        self,
        prices: pd.DataFrame,
        fundamentals: pd.DataFrame,
        smart_money_data: Optional[pd.DataFrame] = None,
        start_date: str = None,
        end_date: str = None,
        benchmark: Optional[pd.Series] = None,
        run_stress_tests: bool = True,
    ) -> BacktestResult:
        """
        Exécute le backtest walk-forward.
        
        Args:
            prices: DataFrame [date x symbol] des prix
            fundamentals: DataFrame des fondamentaux avec colonne 'year'
            smart_money_data: DataFrame des signaux smart money (optionnel)
            start_date: Date de début
            end_date: Date de fin
            benchmark: Série des prix du benchmark
            run_stress_tests: Lancer les stress tests
        
        Returns:
            BacktestResult avec toutes les métriques
        """
        self._load_scorers()
        
        start_date = start_date or BACKTEST_V23["start_date"]
        end_date = end_date or BACKTEST_V23["end_date"]
        
        logger.info("=" * 60)
        logger.info(f"BACKTEST v2.3: {start_date} → {end_date}")
        logger.info(f"Rebalancement: {self.rebal_freq}, TC: {self.tc_bps} bps")
        logger.info("=" * 60)
        
        # Filtrer les prix sur la période
        prices = prices.loc[start_date:end_date]
        
        # Générer les dates de rebalancement
        rebal_dates = self._get_rebal_dates(prices.index, self.rebal_freq)
        logger.info(f"Dates de rebalancement: {len(rebal_dates)}")
        
        # Walk-forward
        weights_history = []
        holdings_history = []
        current_weights = pd.Series(dtype=float)
        
        for i, rebal_date in enumerate(rebal_dates):
            logger.debug(f"Rebalancement {i+1}/{len(rebal_dates)}: {rebal_date.date()}")
            
            # Obtenir les poids pour cette date
            new_weights, holdings = self._rebalance(
                rebal_date,
                prices,
                fundamentals,
                smart_money_data,
            )
            
            if new_weights is not None and len(new_weights) > 0:
                current_weights = new_weights
                weights_history.append({
                    "date": rebal_date,
                    **current_weights.to_dict(),
                })
                holdings_history.append({
                    "date": str(rebal_date.date()),
                    "holdings": holdings,
                })
        
        if not weights_history:
            raise ValueError("Aucun rebalancement réussi")
        
        weights_df = pd.DataFrame(weights_history).set_index("date").fillna(0)
        
        # Calculer les rendements du portefeuille
        returns = self._calculate_portfolio_returns(
            prices,
            weights_df,
            self.tc_bps,
        )
        
        # Benchmark
        benchmark_returns = None
        benchmark_cumulative = None
        if benchmark is not None:
            benchmark_returns = benchmark.pct_change().loc[returns.index]
            benchmark_cumulative = (1 + benchmark_returns).cumprod()
        
        # Métriques
        metrics = calculate_metrics(
            returns,
            benchmark_returns,
            weights_history=weights_df,
        )
        
        # Cumulative returns & drawdowns
        cumulative = (1 + returns).cumprod()
        drawdowns = cumulative / cumulative.expanding().max() - 1
        
        # Stress tests
        stress_results = None
        if run_stress_tests and benchmark_returns is not None:
            logger.info("\nLancement des stress tests...")
            tester = StressTester()
            stress_results = tester.run(returns, benchmark_returns)
        
        # Validation
        validation_passed, validation_notes = self._validate_results(metrics, stress_results)
        
        result = BacktestResult(
            metrics=metrics,
            returns=returns,
            cumulative_returns=cumulative,
            drawdowns=drawdowns,
            weights_history=weights_df,
            holdings_history=holdings_history,
            benchmark_returns=benchmark_returns,
            benchmark_cumulative=benchmark_cumulative,
            stress_tests=stress_results,
            validation_passed=validation_passed,
            validation_notes=validation_notes,
        )
        
        self._log_summary(result)
        
        return result
    
    def _get_rebal_dates(
        self,
        dates: pd.DatetimeIndex,
        freq: str,
    ) -> List[pd.Timestamp]:
        """Génère les dates de rebalancement."""
        if freq == "Q":
            # Fin de trimestre
            rebal_dates = dates[dates.is_quarter_end]
        elif freq == "M":
            # Fin de mois
            rebal_dates = dates[dates.is_month_end]
        elif freq == "W":
            # Chaque vendredi
            rebal_dates = dates[dates.dayofweek == 4]
        else:
            raise ValueError(f"Fréquence inconnue: {freq}")
        
        return list(rebal_dates)
    
    def _rebalance(
        self,
        date: pd.Timestamp,
        prices: pd.DataFrame,
        fundamentals: pd.DataFrame,
        smart_money_data: Optional[pd.DataFrame],
    ) -> Tuple[Optional[pd.Series], List[Dict]]:
        """
        Calcule les nouveaux poids pour une date de rebalancement.
        
        Returns:
            Tuple (weights Series, holdings list)
        """
        try:
            # Construire l'univers à cette date
            universe = self._build_universe(
                date,
                prices,
                fundamentals,
                smart_money_data,
            )
            
            if universe is None or len(universe) < self.min_positions:
                logger.warning(f"{date.date()}: Univers trop petit ({len(universe) if universe is not None else 0})")
                return None, []
            
            # Calculer les scores v2.3
            scored = self._calculate_scores(universe)
            
            # Sélectionner top N
            top_n = scored.nlargest(self.max_positions, "score_composite")
            
            if len(top_n) < self.min_positions:
                logger.warning(f"{date.date()}: Pas assez de positions ({len(top_n)})")
                return None, []
            
            # Calculer les poids (equal weight ou HRP)
            weights = self._calculate_weights(top_n)
            
            # Holdings pour le log
            holdings = [
                {
                    "symbol": row["symbol"],
                    "weight": round(weights.get(row["symbol"], 0), 4),
                    "score_composite": round(row["score_composite"], 3),
                    "buffett_score": round(row.get("buffett_score", 0), 3),
                }
                for _, row in top_n.iterrows()
            ]
            
            return weights, holdings
            
        except Exception as e:
            logger.error(f"{date.date()}: Erreur rebalancement: {e}")
            return None, []
    
    def _build_universe(
        self,
        date: pd.Timestamp,
        prices: pd.DataFrame,
        fundamentals: pd.DataFrame,
        smart_money_data: Optional[pd.DataFrame],
    ) -> Optional[pd.DataFrame]:
        """Construit l'univers filtrable à une date."""
        # Symboles avec prix disponibles
        available_symbols = prices.columns[prices.loc[:date].iloc[-1].notna()].tolist()
        
        if not available_symbols:
            return None
        
        # Filtrer fondamentaux (look-ahead)
        try:
            funda_filtered = self._filter_look_ahead(
                fundamentals,
                as_of_date=str(date.date()),
            )
        except ValueError:
            # Pas de données disponibles
            return None
        
        # Construire le DataFrame
        latest_funda = funda_filtered.groupby("symbol").last().reset_index()
        
        # Ajouter les prix
        price_date = prices.loc[:date].iloc[-1]
        latest_funda["td_price"] = latest_funda["symbol"].map(price_date)
        
        # Calculer market cap si possible
        if "shares_outstanding" in latest_funda.columns:
            latest_funda["market_cap"] = (
                latest_funda["shares_outstanding"] * latest_funda["td_price"]
            )
        
        # Ajouter volatilité 30j
        if len(prices.loc[:date]) >= 30:
            returns_30d = prices.loc[:date].iloc[-30:].pct_change()
            vol_30d = returns_30d.std() * np.sqrt(252) * 100
            latest_funda["vol_30d"] = latest_funda["symbol"].map(vol_30d)
        
        # Ajouter smart money data si disponible
        if smart_money_data is not None:
            sm_cols = ["score_sm", "score_insider", "score_momentum", "gp_buys", "gp_tier"]
            for col in sm_cols:
                if col in smart_money_data.columns:
                    sm_map = smart_money_data.set_index("symbol")[col].to_dict()
                    latest_funda[col] = latest_funda["symbol"].map(sm_map)
        
        # Scores par défaut si manquants
        for col in ["score_sm", "score_insider", "score_momentum"]:
            if col not in latest_funda.columns:
                latest_funda[col] = 0.5
        
        # Appliquer filtres
        try:
            filtered = self._apply_liquidity(latest_funda, verbose=False)
            filtered = self._apply_hard_filters(filtered, verbose=False)
        except Exception as e:
            logger.debug(f"Erreur filtres: {e}")
            filtered = latest_funda
        
        return filtered
    
    def _calculate_weights(self, top_n: pd.DataFrame) -> pd.Series:
        """Calcule les poids (equal weight avec cap)."""
        n = len(top_n)
        base_weight = 1.0 / n
        
        # Appliquer le cap
        weights = pd.Series(
            [min(base_weight, self.max_weight)] * n,
            index=top_n["symbol"].values,
        )
        
        # Renormaliser
        weights = weights / weights.sum()
        
        return weights
    
    def _calculate_portfolio_returns(
        self,
        prices: pd.DataFrame,
        weights_history: pd.DataFrame,
        tc_bps: float,
    ) -> pd.Series:
        """Calcule les rendements du portefeuille avec coûts de transaction."""
        returns = prices.pct_change()
        
        portfolio_returns = []
        current_weights = pd.Series(dtype=float)
        rebal_dates = weights_history.index.tolist()
        
        for date in returns.index:
            # Mise à jour des poids si rebalancement
            if date in rebal_dates:
                new_weights = weights_history.loc[date].dropna()
                new_weights = new_weights[new_weights > 0]
                
                # Coûts de transaction
                if len(current_weights) > 0:
                    turnover = self._calculate_turnover(current_weights, new_weights)
                    tc_cost = turnover * tc_bps / 10000
                else:
                    tc_cost = 0
                
                current_weights = new_weights
            else:
                tc_cost = 0
            
            # Rendement du jour
            if len(current_weights) > 0:
                day_returns = returns.loc[date]
                symbols = [s for s in current_weights.index if s in day_returns.index]
                
                if symbols:
                    port_return = sum(
                        current_weights[s] * day_returns[s]
                        for s in symbols
                        if not pd.isna(day_returns[s])
                    )
                    port_return -= tc_cost
                else:
                    port_return = 0
            else:
                port_return = 0
            
            portfolio_returns.append(port_return)
        
        return pd.Series(portfolio_returns, index=returns.index)
    
    def _calculate_turnover(
        self,
        old_weights: pd.Series,
        new_weights: pd.Series,
    ) -> float:
        """Calcule le turnover entre deux ensembles de poids."""
        all_symbols = set(old_weights.index) | set(new_weights.index)
        
        turnover = 0
        for symbol in all_symbols:
            old_w = old_weights.get(symbol, 0)
            new_w = new_weights.get(symbol, 0)
            turnover += abs(new_w - old_w)
        
        return turnover / 2
    
    def _validate_results(
        self,
        metrics: PerformanceMetrics,
        stress_results: Optional[StressTestSuite],
    ) -> Tuple[bool, List[str]]:
        """Valide les résultats vs critères."""
        notes = []
        passed = True
        
        # Sharpe
        min_sharpe = VALIDATION_V23.get("min_sharpe", 0.55)
        if metrics.sharpe_ratio < min_sharpe:
            passed = False
            notes.append(f"\u274c Sharpe {metrics.sharpe_ratio:.2f} < {min_sharpe}")
        else:
            notes.append(f"\u2705 Sharpe {metrics.sharpe_ratio:.2f} >= {min_sharpe}")
        
        # Max DD
        target_dd = RISK_MANAGEMENT.get("max_dd_target", -0.25) * 100
        hard_dd = RISK_MANAGEMENT.get("max_dd_hard", -0.35) * 100
        
        if metrics.max_drawdown < hard_dd:
            passed = False
            notes.append(f"\u274c Max DD {metrics.max_drawdown:.1f}% < hard limit {hard_dd:.0f}%")
        elif metrics.max_drawdown < target_dd:
            notes.append(f"\u26a0\ufe0f Max DD {metrics.max_drawdown:.1f}% < target {target_dd:.0f}%")
        else:
            notes.append(f"\u2705 Max DD {metrics.max_drawdown:.1f}% > target {target_dd:.0f}%")
        
        # Stress tests
        if stress_results:
            if stress_results.overall_passed:
                notes.append(f"\u2705 Stress tests: {stress_results.passed_count}/{len(stress_results.results)} passés")
            else:
                notes.append(f"\u274c Stress tests: {stress_results.passed_count}/{len(stress_results.results)} passés")
                passed = False
        
        return passed, notes
    
    def _log_summary(self, result: BacktestResult):
        """Affiche le résumé du backtest."""
        m = result.metrics
        
        logger.info("\n" + "=" * 60)
        logger.info("R\u00c9SULTATS BACKTEST v2.3")
        logger.info("=" * 60)
        logger.info(f"Période: {m.start_date} \u2192 {m.end_date}")
        logger.info(f"")
        logger.info(f"RENDEMENTS:")
        logger.info(f"  Total Return: {m.total_return:+.1f}%")
        logger.info(f"  CAGR:         {m.cagr:+.1f}%")
        logger.info(f"  Volatilité:   {m.annual_volatility:.1f}%")
        logger.info(f"")
        logger.info(f"RATIOS:")
        logger.info(f"  Sharpe:  {m.sharpe_ratio:.2f}")
        logger.info(f"  Sortino: {m.sortino_ratio:.2f}")
        logger.info(f"  Calmar:  {m.calmar_ratio:.2f}")
        logger.info(f"")
        logger.info(f"RISQUE:")
        logger.info(f"  Max Drawdown: {m.max_drawdown:.1f}%")
        logger.info(f"  DD Duration:  {m.max_drawdown_duration_days} jours")
        logger.info(f"")
        logger.info(f"TRADING:")
        logger.info(f"  Turnover:   {m.turnover_annual:.0f}%/an")
        logger.info(f"  Hit Ratio:  {m.hit_ratio:.1f}%")
        logger.info(f"  Win/Loss:   {m.win_loss_ratio:.2f}")
        
        if m.alpha is not None:
            logger.info(f"")
            logger.info(f"VS BENCHMARK:")
            logger.info(f"  Alpha: {m.alpha:+.2f}%")
            logger.info(f"  Beta:  {m.beta:.2f}")
            logger.info(f"  IR:    {m.information_ratio:.2f}")
        
        logger.info(f"")
        logger.info(f"VALIDATION:")
        for note in result.validation_notes:
            logger.info(f"  {note}")
        
        status = "\u2705 PASS" if result.validation_passed else "\u274c FAIL"
        logger.info(f"")
        logger.info(f"Statut: {status}")
        logger.info("=" * 60)


def run_backtest(
    prices: pd.DataFrame,
    fundamentals: pd.DataFrame,
    **kwargs,
) -> BacktestResult:
    """
    Fonction helper pour lancer un backtest.
    
    Args:
        prices: DataFrame des prix
        fundamentals: DataFrame des fondamentaux
        **kwargs: Arguments pour BacktestEngine
    
    Returns:
        BacktestResult
    """
    engine = BacktestEngine(**kwargs)
    return engine.run(prices, fundamentals, **kwargs)
