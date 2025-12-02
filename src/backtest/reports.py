"""SmartMoney v2.3 — Report Generator

Génère des rapports de backtest:
- Texte
- HTML
- JSON

Date: Décembre 2025
"""

import json
import pandas as pd
from typing import Optional
from datetime import datetime
from pathlib import Path
import logging

from .backtest_v23 import BacktestResult
from .stress_tests import generate_stress_report

logger = logging.getLogger(__name__)


def generate_report(
    result: BacktestResult,
    output_path: Optional[str] = None,
    format: str = "text",
) -> str:
    """
    Génère un rapport de backtest.
    
    Args:
        result: Résultats du backtest
        output_path: Chemin de sortie (optionnel)
        format: "text", "html", ou "json"
    
    Returns:
        Rapport formaté
    """
    if format == "text":
        report = _generate_text_report(result)
    elif format == "html":
        report = _generate_html_report(result)
    elif format == "json":
        report = _generate_json_report(result)
    else:
        raise ValueError(f"Format inconnu: {format}")
    
    if output_path:
        Path(output_path).write_text(report)
        logger.info(f"Rapport sauvegradé: {output_path}")
    
    return report


def _generate_text_report(result: BacktestResult) -> str:
    """Génère un rapport texte."""
    m = result.metrics
    
    lines = [
        "=" * 70,
        "SMARTMONEY v2.3 — RAPPORT DE BACKTEST",
        f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        "PÉRIODE",
        "-" * 40,
        f"Début:    {m.start_date}",
        f"Fin:      {m.end_date}",
        f"Périodes: {m.num_periods}",
        "",
        "RENDEMENTS",
        "-" * 40,
        f"Total Return:   {m.total_return:+.1f}%",
        f"CAGR:           {m.cagr:+.1f}%",
        f"Volatilité:     {m.annual_volatility:.1f}%",
        "",
        "RATIOS DE PERFORMANCE",
        "-" * 40,
        f"Sharpe Ratio:   {m.sharpe_ratio:.3f}",
        f"Sortino Ratio:  {m.sortino_ratio:.3f}",
        f"Calmar Ratio:   {m.calmar_ratio:.3f}",
        "",
        "RISQUE",
        "-" * 40,
        f"Max Drawdown:       {m.max_drawdown:.1f}%",
        f"DD Duration:        {m.max_drawdown_duration_days} jours",
        f"Avg Drawdown:       {m.avg_drawdown:.1f}%",
        "",
        "TRADING",
        "-" * 40,
        f"Turnover annuel:    {m.turnover_annual:.0f}%",
        f"Nombre de trades:   {m.num_trades}",
        f"Hit Ratio:          {m.hit_ratio:.1f}%",
        f"Avg Win:            {m.avg_win:.3f}%",
        f"Avg Loss:           {m.avg_loss:.3f}%",
        f"Win/Loss Ratio:     {m.win_loss_ratio:.2f}",
    ]
    
    if m.alpha is not None:
        lines.extend([
            "",
            "VS BENCHMARK",
            "-" * 40,
            f"Alpha:              {m.alpha:+.2f}%",
            f"Beta:               {m.beta:.2f}",
            f"Information Ratio:  {m.information_ratio:.3f}",
            f"Tracking Error:     {m.tracking_error:.2f}%",
        ])
    
    lines.extend([
        "",
        "VALIDATION",
        "-" * 40,
    ])
    
    for note in result.validation_notes:
        lines.append(f"  {note}")
    
    status = "\u2705 PASS" if result.validation_passed else "\u274c FAIL"
    lines.extend([
        "",
        f"STATUT: {status}",
        "=" * 70,
    ])
    
    # Stress tests
    if result.stress_tests:
        lines.extend([
            "",
            "",
            generate_stress_report(result.stress_tests),
        ])
    
    # Top holdings (dernier rebalancement)
    if result.holdings_history:
        last_holdings = result.holdings_history[-1]
        lines.extend([
            "",
            "",
            "=" * 70,
            f"DERNIER PORTEFEUILLE ({last_holdings['date']})",
            "=" * 70,
            "",
            f"{'Symbol':<10} {'Weight':>10} {'Composite':>10} {'Buffett':>10}",
            "-" * 45,
        ])
        
        for h in sorted(last_holdings["holdings"], key=lambda x: -x["weight"]):
            lines.append(
                f"{h['symbol']:<10} {h['weight']*100:>9.1f}% {h['score_composite']:>10.3f} {h['buffett_score']:>10.3f}"
            )
    
    return "\n".join(lines)


def _generate_html_report(result: BacktestResult) -> str:
    """Génère un rapport HTML."""
    m = result.metrics
    status_class = "pass" if result.validation_passed else "fail"
    status_text = "PASS" if result.validation_passed else "FAIL"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SmartMoney v2.3 - Backtest Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f9f9f9; padding: 15px; border-radius: 6px; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1a1a1a; }}
        .positive {{ color: #4CAF50; }}
        .negative {{ color: #f44336; }}
        .status {{ padding: 10px 20px; border-radius: 4px; display: inline-block; font-weight: bold; }}
        .status.pass {{ background: #4CAF50; color: white; }}
        .status.fail {{ background: #f44336; color: white; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .note {{ padding: 5px 0; }}
        .note.pass {{ color: #4CAF50; }}
        .note.fail {{ color: #f44336; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 SmartMoney v2.3 — Rapport de Backtest</h1>
        <p>Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        
        <div class="metric-grid">
            <div class="metric">
                <div class="metric-label">Période</div>
                <div class="metric-value">{m.start_date[:4]}-{m.end_date[:4]}</div>
            </div>
            <div class="metric">
                <div class="metric-label">CAGR</div>
                <div class="metric-value {'positive' if m.cagr > 0 else 'negative'}">{m.cagr:+.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">{m.sharpe_ratio:.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value negative">{m.max_drawdown:.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Volatilité</div>
                <div class="metric-value">{m.annual_volatility:.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Calmar</div>
                <div class="metric-value">{m.calmar_ratio:.2f}</div>
            </div>
        </div>
        
        <h2>Validation</h2>
        <div class="status {status_class}">{status_text}</div>
        <div style="margin-top: 15px;">
    """
    
    for note in result.validation_notes:
        css_class = "pass" if "\u2705" in note else "fail" if "\u274c" in note else ""
        html += f'<div class="note {css_class}">{note}</div>\n'
    
    html += """
        </div>
        
        <h2>Métriques Détaillées</h2>
        <table>
            <tr><th>Métrique</th><th>Valeur</th></tr>
    """
    
    metrics_table = [
        ("Total Return", f"{m.total_return:+.1f}%"),
        ("CAGR", f"{m.cagr:+.1f}%"),
        ("Volatilité Annuelle", f"{m.annual_volatility:.1f}%"),
        ("Sharpe Ratio", f"{m.sharpe_ratio:.3f}"),
        ("Sortino Ratio", f"{m.sortino_ratio:.3f}"),
        ("Calmar Ratio", f"{m.calmar_ratio:.3f}"),
        ("Max Drawdown", f"{m.max_drawdown:.1f}%"),
        ("DD Duration", f"{m.max_drawdown_duration_days} jours"),
        ("Turnover Annuel", f"{m.turnover_annual:.0f}%"),
        ("Hit Ratio", f"{m.hit_ratio:.1f}%"),
        ("Win/Loss Ratio", f"{m.win_loss_ratio:.2f}"),
    ]
    
    if m.alpha is not None:
        metrics_table.extend([
            ("Alpha", f"{m.alpha:+.2f}%"),
            ("Beta", f"{m.beta:.2f}"),
            ("Information Ratio", f"{m.information_ratio:.3f}"),
        ])
    
    for label, value in metrics_table:
        html += f"<tr><td>{label}</td><td>{value}</td></tr>\n"
    
    html += """
        </table>
    </div>
</body>
</html>
    """
    
    return html


def _generate_json_report(result: BacktestResult) -> str:
    """Génère un rapport JSON."""
    m = result.metrics
    
    data = {
        "generated_at": datetime.now().isoformat(),
        "version": "2.3",
        "period": {
            "start": m.start_date,
            "end": m.end_date,
            "num_periods": m.num_periods,
        },
        "returns": {
            "total_return": m.total_return,
            "cagr": m.cagr,
            "annual_volatility": m.annual_volatility,
        },
        "ratios": {
            "sharpe": m.sharpe_ratio,
            "sortino": m.sortino_ratio,
            "calmar": m.calmar_ratio,
        },
        "risk": {
            "max_drawdown": m.max_drawdown,
            "max_dd_duration_days": m.max_drawdown_duration_days,
            "avg_drawdown": m.avg_drawdown,
        },
        "trading": {
            "turnover_annual": m.turnover_annual,
            "num_trades": m.num_trades,
            "hit_ratio": m.hit_ratio,
            "avg_win": m.avg_win,
            "avg_loss": m.avg_loss,
            "win_loss_ratio": m.win_loss_ratio,
        },
        "validation": {
            "passed": result.validation_passed,
            "notes": result.validation_notes,
        },
        "holdings_history": result.holdings_history,
    }
    
    if m.alpha is not None:
        data["benchmark"] = {
            "alpha": m.alpha,
            "beta": m.beta,
            "information_ratio": m.information_ratio,
            "tracking_error": m.tracking_error,
        }
    
    if result.stress_tests:
        data["stress_tests"] = {
            "passed_count": result.stress_tests.passed_count,
            "failed_count": result.stress_tests.failed_count,
            "overall_passed": result.stress_tests.overall_passed,
            "summary": result.stress_tests.summary,
            "results": [
                {
                    "name": r.name,
                    "period": f"{r.start_date} to {r.end_date}",
                    "portfolio_return": r.portfolio_return,
                    "portfolio_max_dd": r.portfolio_max_dd,
                    "passed": r.passed,
                }
                for r in result.stress_tests.results
            ],
        }
    
    return json.dumps(data, indent=2)
