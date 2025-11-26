"""Dashboard HTML - Visualisation du portefeuille"""
import json
from datetime import datetime
from pathlib import Path


def generate_dashboard(portfolio: dict, output_dir: Path) -> Path:
    """Génère un dashboard HTML autonome"""
    
    today = datetime.now().strftime("%Y-%m-%d")
    metrics = portfolio.get("metrics", {})
    positions = portfolio.get("portfolio", [])
    sector_weights = metrics.get("sector_weights", {})
    
    # Prépare les données pour Chart.js
    sector_labels = list(sector_weights.keys())
    sector_values = list(sector_weights.values())
    
    # Couleurs par secteur
    sector_colors = {
        "Technology": "#3b82f6",
        "Healthcare": "#10b981",
        "Financial Services": "#f59e0b",
        "Consumer Cyclical": "#ef4444",
        "Industrials": "#8b5cf6",
        "Consumer Defensive": "#06b6d4",
        "Energy": "#f97316",
        "Basic Materials": "#84cc16",
        "Communication Services": "#ec4899",
        "Real Estate": "#6366f1",
        "Utilities": "#14b8a6",
        "Unknown": "#9ca3af"
    }
    colors = [sector_colors.get(s, "#9ca3af") for s in sector_labels]
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartMoney Portfolio - {today}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{
            font-size: 1.8rem;
            margin-bottom: 20px;
            color: #38bdf8;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #38bdf8;
        }}
        .metric-value.positive {{ color: #10b981; }}
        .metric-value.negative {{ color: #ef4444; }}
        .metric-label {{
            font-size: 0.85rem;
            color: #94a3b8;
            margin-top: 5px;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        @media (max-width: 900px) {{
            .grid-2 {{ grid-template-columns: 1fr; }}
        }}
        .card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
        }}
        .card h2 {{
            font-size: 1.1rem;
            margin-bottom: 15px;
            color: #94a3b8;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        th, td {{
            padding: 12px 8px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            color: #94a3b8;
            font-weight: 500;
            font-size: 0.8rem;
            text-transform: uppercase;
        }}
        tr:hover {{ background: #334155; }}
        .ticker {{
            font-weight: 600;
            color: #38bdf8;
        }}
        .weight {{ color: #fbbf24; }}
        .positive {{ color: #10b981; }}
        .negative {{ color: #ef4444; }}
        .sector-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            background: #334155;
        }}
        .input-group {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            align-items: center;
        }}
        .input-group label {{
            color: #94a3b8;
        }}
        .input-group input {{
            background: #334155;
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 10px 15px;
            color: #e2e8f0;
            font-size: 1rem;
            width: 150px;
        }}
        .input-group input:focus {{
            outline: none;
            border-color: #38bdf8;
        }}
        #allocation-result {{
            margin-top: 15px;
            padding: 15px;
            background: #0f172a;
            border-radius: 8px;
            max-height: 300px;
            overflow-y: auto;
        }}
        .alloc-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #1e293b;
        }}
        .chart-container {{
            position: relative;
            height: 300px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 SmartMoney Portfolio — {today}</h1>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{metrics.get('positions', 0)}</div>
                <div class="metric-label">Positions</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'positive' if (metrics.get('perf_3m') or 0) >= 0 else 'negative'}">
                    {'+' if (metrics.get('perf_3m') or 0) >= 0 else ''}{metrics.get('perf_3m', 'N/A')}%
                </div>
                <div class="metric-label">Performance 3M</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'positive' if (metrics.get('perf_ytd') or 0) >= 0 else 'negative'}">
                    {'+' if (metrics.get('perf_ytd') or 0) >= 0 else ''}{metrics.get('perf_ytd', 'N/A')}%
                </div>
                <div class="metric-label">Performance YTD</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics.get('vol_30d', 'N/A')}%</div>
                <div class="metric-label">Volatilité 30j</div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="card">
                <h2>Répartition Sectorielle</h2>
                <div class="chart-container">
                    <canvas id="sectorChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h2>Calculateur d'Allocation</h2>
                <div class="input-group">
                    <label for="amount">Montant à investir:</label>
                    <input type="number" id="amount" value="10000" step="1000">
                    <span>€</span>
                </div>
                <div id="allocation-result"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>Positions ({len(positions)})</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Société</th>
                        <th>Secteur</th>
                        <th>Poids</th>
                        <th>Score</th>
                        <th>Perf 3M</th>
                        <th>Perf YTD</th>
                        <th>Vol 30j</th>
                        <th>RSI</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Ajoute les lignes du tableau
    for pos in positions:
        weight = pos.get('weight', 0) * 100
        perf_3m = pos.get('perf_3m')
        perf_ytd = pos.get('perf_ytd')
        vol = pos.get('vol_30d')
        rsi = pos.get('rsi')
        
        perf_3m_class = 'positive' if perf_3m and perf_3m > 0 else 'negative' if perf_3m and perf_3m < 0 else ''
        perf_ytd_class = 'positive' if perf_ytd and perf_ytd > 0 else 'negative' if perf_ytd and perf_ytd < 0 else ''
        
        html += f"""                    <tr>
                        <td class="ticker">{pos.get('symbol', '')}</td>
                        <td>{pos.get('company', '')[:30]}</td>
                        <td><span class="sector-badge">{pos.get('sector', 'N/A')}</span></td>
                        <td class="weight">{weight:.2f}%</td>
                        <td>{pos.get('score_composite', 0):.3f}</td>
                        <td class="{perf_3m_class}">{f'{perf_3m:+.1f}%' if perf_3m is not None else 'N/A'}</td>
                        <td class="{perf_ytd_class}">{f'{perf_ytd:+.1f}%' if perf_ytd is not None else 'N/A'}</td>
                        <td>{f'{vol:.1f}%' if vol is not None else 'N/A'}</td>
                        <td>{f'{rsi:.0f}' if rsi is not None else 'N/A'}</td>
                    </tr>
"""
    
    html += f"""                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Données du portefeuille
        const portfolio = {json.dumps(positions, default=str)};
        
        // Pie Chart secteurs
        const ctx = document.getElementById('sectorChart').getContext('2d');
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(sector_labels)},
                datasets: [{{
                    data: {json.dumps(sector_values)},
                    backgroundColor: {json.dumps(colors)},
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{ color: '#94a3b8', font: {{ size: 11 }} }}
                    }}
                }}
            }}
        }});
        
        // Calculateur d'allocation
        function calculateAllocation() {{
            const amount = parseFloat(document.getElementById('amount').value) || 0;
            const result = document.getElementById('allocation-result');
            
            let html = '';
            portfolio.forEach(pos => {{
                const alloc = amount * pos.weight;
                const price = pos.td_price || pos.current_price || 0;
                const shares = price > 0 ? Math.floor(alloc / price) : 0;
                
                html += `<div class="alloc-row">
                    <span><strong>${{pos.symbol}}</strong> (${{price.toFixed(2)}})</span>
                    <span>${{alloc.toFixed(0)}}€ → ${{shares}} actions</span>
                </div>`;
            }});
            
            result.innerHTML = html;
        }}
        
        document.getElementById('amount').addEventListener('input', calculateAllocation);
        calculateAllocation();
    </script>
</body>
</html>
"""
    
    # Sauvegarde
    html_path = output_dir / f"portfolio_{today}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"📊 Dashboard exporté: {html_path.name}")
    return html_path


if __name__ == "__main__":
    from config import OUTPUTS
    
    # Charge le dernier portfolio
    portfolio_files = list(OUTPUTS.glob("portfolio_*.json"))
    if portfolio_files:
        latest = max(portfolio_files, key=lambda x: x.stat().st_mtime)
        with open(latest) as f:
            portfolio = json.load(f)
        generate_dashboard(portfolio, OUTPUTS)
    else:
        print("❌ Aucun portfolio trouvé")
