"""SmartMoney v2.3 — Métriques de Performance

Calcul des métriques de backtest:
- Sharpe, Sortino, Calmar
- Drawdowns
- Turnover
- Hit ratio

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Métriques de performance d'un backtest."""
    # Rendements
    total_return: float
    cagr: float
    annual_volatility: float
    
    # Ratios
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Drawdowns
    max_drawdown: float
    max_drawdown_duration_days: int
    avg_drawdown: float
    
    # Trading
    turnover_annual: float
    num_trades: int
    hit_ratio: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    
    # Périodes
    start_date: str
    end_date: str
    num_periods: int
    
    # Benchmark
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None
    tracking_error: Optional[float] = None


def calculate_metrics(
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_rate: float = 0.045,
    periods_per_year: int = 252,
    weights_history: Optional[pd.DataFrame] = None,
) -> PerformanceMetrics:
    """
    Calcule les métriques de performance.
    
    Args:
        returns: Série des rendements du portefeuille
        benchmark_returns: Série des rendements du benchmark (optionnel)
        risk_free_rate: Taux sans risque annualisé
        periods_per_year: Nombre de périodes par an (252 pour daily)
        weights_history: DataFrame historique des poids (pour turnover)
    
    Returns:
        PerformanceMetrics avec toutes les métriques
    """
    returns = returns.dropna()
    
    if len(returns) < 10:
        raise ValueError("Pas assez de données pour calculer les métriques")
    
    # === Rendements ===
    total_return = (1 + returns).prod() - 1
    
    years = len(returns) / periods_per_year
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    annual_volatility = returns.std() * np.sqrt(periods_per_year)
    
    # === Sharpe Ratio ===
    excess_returns = returns - risk_free_rate / periods_per_year
    sharpe = (
        excess_returns.mean() / returns.std() * np.sqrt(periods_per_year)
        if returns.std() > 0 else 0
    )
    
    # === Sortino Ratio ===
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.001
    sortino = (
        excess_returns.mean() / downside_std * np.sqrt(periods_per_year)
        if downside_std > 0 else 0
    )
    
    # === Drawdowns ===
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdowns = cumulative / running_max - 1
    
    max_dd = drawdowns.min()
    avg_dd = drawdowns[drawdowns < 0].mean() if (drawdowns < 0).any() else 0
    
    # Durée max drawdown
    dd_duration = _calculate_max_dd_duration(drawdowns)
    
    # === Calmar Ratio ===
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0
    
    # === Trading Stats ===
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    
    hit_ratio = len(wins) / len(returns) if len(returns) > 0 else 0
    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_loss = losses.mean() if len(losses) > 0 else 0
    win_loss = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
    
    # === Turnover ===
    turnover = 0.0
    num_trades = 0
    
    if weights_history is not None and len(weights_history) > 1:
        turnover, num_trades = _calculate_turnover(weights_history, periods_per_year)
    
    # === Benchmark Stats ===
    alpha, beta, ir, te = None, None, None, None
    
    if benchmark_returns is not None:
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) > 10:
            alpha, beta, ir, te = _calculate_benchmark_stats(
                aligned.iloc[:, 0],
                aligned.iloc[:, 1],
                risk_free_rate,
                periods_per_year,
            )
    
    return PerformanceMetrics(
        total_return=round(total_return * 100, 2),
        cagr=round(cagr * 100, 2),
        annual_volatility=round(annual_volatility * 100, 2),
        sharpe_ratio=round(sharpe, 3),
        sortino_ratio=round(sortino, 3),
        calmar_ratio=round(calmar, 3),
        max_drawdown=round(max_dd * 100, 2),
        max_drawdown_duration_days=dd_duration,
        avg_drawdown=round(avg_dd * 100, 2) if avg_dd else 0,
        turnover_annual=round(turnover * 100, 1),
        num_trades=num_trades,
        hit_ratio=round(hit_ratio * 100, 1),
        avg_win=round(avg_win * 100, 3),
        avg_loss=round(avg_loss * 100, 3),
        win_loss_ratio=round(win_loss, 2),
        start_date=str(returns.index[0].date()) if hasattr(returns.index[0], 'date') else str(returns.index[0]),
        end_date=str(returns.index[-1].date()) if hasattr(returns.index[-1], 'date') else str(returns.index[-1]),
        num_periods=len(returns),
        alpha=round(alpha * 100, 2) if alpha else None,
        beta=round(beta, 2) if beta else None,
        information_ratio=round(ir, 3) if ir else None,
        tracking_error=round(te * 100, 2) if te else None,
    )


def _calculate_max_dd_duration(drawdowns: pd.Series) -> int:
    """Calcule la durée maximale du drawdown en jours."""
    in_dd = drawdowns < 0
    
    if not in_dd.any():
        return 0
    
    # Trouver les périodes de drawdown
    dd_starts = in_dd & ~in_dd.shift(1).fillna(False)
    dd_ends = ~in_dd & in_dd.shift(1).fillna(False)
    
    max_duration = 0
    current_start = None
    
    for date, is_start in dd_starts.items():
        if is_start:
            current_start = date
    
    for date, is_end in dd_ends.items():
        if is_end and current_start:
            duration = (date - current_start).days if hasattr(date, 'days') else 1
            max_duration = max(max_duration, duration)
            current_start = None
    
    # Si encore en drawdown
    if current_start and in_dd.iloc[-1]:
        duration = (drawdowns.index[-1] - current_start).days if hasattr(drawdowns.index[-1], 'days') else len(drawdowns)
        max_duration = max(max_duration, duration)
    
    return max_duration


def _calculate_turnover(
    weights_history: pd.DataFrame,
    periods_per_year: int,
) -> Tuple[float, int]:
    """Calcule le turnover annualisé."""
    if len(weights_history) < 2:
        return 0.0, 0
    
    # Différence absolue des poids entre périodes
    weight_changes = weights_history.diff().abs()
    
    # Turnover par période = somme des changements / 2
    turnover_per_period = weight_changes.sum(axis=1) / 2
    
    # Annualiser
    periods = len(weights_history)
    years = periods / periods_per_year
    total_turnover = turnover_per_period.sum()
    annual_turnover = total_turnover / years if years > 0 else 0
    
    # Nombre de trades (changements significatifs)
    significant_changes = (weight_changes > 0.01).sum().sum()
    
    return annual_turnover, int(significant_changes)


def _calculate_benchmark_stats(
    returns: pd.Series,
    benchmark: pd.Series,
    risk_free_rate: float,
    periods_per_year: int,
) -> Tuple[float, float, float, float]:
    """Calcule alpha, beta, IR, tracking error."""
    # Beta
    cov = np.cov(returns, benchmark)
    beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 1
    
    # Alpha (Jensen's)
    rf_per_period = risk_free_rate / periods_per_year
    alpha_per_period = (
        returns.mean() - rf_per_period - 
        beta * (benchmark.mean() - rf_per_period)
    )
    alpha = alpha_per_period * periods_per_year
    
    # Tracking Error
    active_returns = returns - benchmark
    tracking_error = active_returns.std() * np.sqrt(periods_per_year)
    
    # Information Ratio
    ir = active_returns.mean() / active_returns.std() * np.sqrt(periods_per_year) if active_returns.std() > 0 else 0
    
    return alpha, beta, ir, tracking_error


def compare_periods(
    returns: pd.Series,
    periods: Dict[str, Tuple[str, str]],
) -> pd.DataFrame:
    """
    Compare les performances sur différentes périodes.
    
    Args:
        returns: Série des rendements
        periods: Dict {nom: (start_date, end_date)}
    
    Returns:
        DataFrame avec métriques par période
    """
    results = []
    
    for name, (start, end) in periods.items():
        period_returns = returns.loc[start:end]
        
        if len(period_returns) < 5:
            continue
        
        try:
            metrics = calculate_metrics(period_returns)
            results.append({
                "period": name,
                "start": start,
                "end": end,
                "cagr": metrics.cagr,
                "volatility": metrics.annual_volatility,
                "sharpe": metrics.sharpe_ratio,
                "max_dd": metrics.max_drawdown,
                "calmar": metrics.calmar_ratio,
            })
        except Exception as e:
            logger.warning(f"Erreur période {name}: {e}")
    
    return pd.DataFrame(results)
