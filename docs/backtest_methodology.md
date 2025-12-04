# SmartMoney v2.4 — Méthodologie Backtest Walk-Forward

*Dernière mise à jour: Décembre 2025*

---

## 1. Objectif

Valider la stratégie SmartMoney v2.4 de manière **out-of-sample** avec des paramètres **figés** pendant tout le backtest.

### Principes clés

| Principe | Description |
|----------|-------------|
| **No look-ahead** | Paramètres définis AVANT le backtest |
| **Walk-forward** | Périodes de test séquentielles |
| **Out-of-sample** | Chaque période est testée après sa génération |
| **Paramètres figés** | `WEIGHTS_V23` et `CONSTRAINTS_V23` constants |

---

## 2. Structure du Backtest

### 2.1 Périodes

```
|<------ Train (non utilisé) ------>|<-- Test -->|
|           3 ans                    |  1 trimestre |
|                                    |              |
|  Calibration historique            |  Validation  |
|  (réservé pour v3.0)              |  OOS         |
```

- **Test window**: 1 trimestre (3 mois)
- **Rebalancing**: Début de chaque trimestre
- **Univers**: S&P 500 (filtré par le scoring)

### 2.2 Timeline

```
Q1 2020: Génération portfolio → Test Q2 2020
Q2 2020: Génération portfolio → Test Q3 2020
...
Q3 2024: Génération portfolio → Test Q4 2024
```

---

## 3. Paramètres Figés

### 3.1 Poids des Facteurs (v2.4)

```python
WEIGHTS_V23 = {
    "smart_money": 0.15,
    "insider": 0.10,
    "momentum": 0.05,
    "value": 0.30,
    "quality": 0.25,
    "risk": 0.15,
}
```

### 3.2 Contraintes

```python
CONSTRAINTS_V23 = {
    "max_weight": 0.12,      # 12% max par position
    "max_sector": 0.30,      # 30% max par secteur
    "min_positions": 15,
    "max_positions": 20,
}
```

### 3.3 Mode de Scoring Value

```python
VALUE_SCORING_MODE = "cross_sectional"  # Percentiles vs univers
```

---

## 4. Métriques Calculées

### 4.1 Performance

| Métrique | Formule | Interprétation |
|----------|---------|----------------|
| **CAGR** | `(1 + total_return)^(1/n_years) - 1` | Rendement annualisé |
| **Alpha** | `portfolio_return - benchmark_return` | Excès de rendement |
| **Hit Rate** | `% périodes où alpha > 0` | Consistance |
| **Information Ratio** | `alpha_annualisé / tracking_error` | Alpha ajusté du risque |

### 4.2 Risque

| Métrique | Formule | Seuil acceptable |
|----------|---------|------------------|
| **Volatilité** | `std(returns) * sqrt(252)` | 15-20% |
| **Max Drawdown** | `max(cumul - peak) / peak` | > -35% |
| **Tracking Error** | `std(alpha) * sqrt(252)` | 8-12% |
| **Sharpe Ratio** | `(return - rf) / volatility` | > 0.5 |

### 4.3 Concentration

| Métrique | Calcul | Limite |
|----------|--------|--------|
| **Max position** | `max(weights)` | ≤ 12% |
| **Max sector** | `max(sector_weights)` | ≤ 30% |
| **HHI** | `sum(weights^2)` | < 0.10 |

---

## 5. Sources de Données

### 5.1 Prix Historiques

| Source | Priorité | Coût | Fiabilité |
|--------|----------|------|----------|
| Cache local | 1 | Gratuit | Haute |
| yfinance | 2 | Gratuit | Haute |
| Twelve Data | 3 | API limit | Moyenne |

### 5.2 Benchmark

- **Principal**: SPY (SPDR S&P 500 ETF)
- **Secondaire**: ^GSPC (S&P 500 Index)

---

## 6. Rapport de Sortie

### 6.1 Structure JSON

```json
{
  "metadata": {
    "start_date": "2020-01-01",
    "end_date": "2024-12-31",
    "benchmark": "SPY",
    "total_periods": 20,
    "frozen_weights": {...},
    "frozen_constraints": {...}
  },
  "summary": {
    "portfolio_cagr": 12.5,
    "benchmark_cagr": 10.2,
    "total_alpha": 18.5,
    "hit_rate": 65.0,
    "information_ratio": 0.85
  },
  "risk_metrics": {
    "portfolio_volatility": 16.5,
    "tracking_error": 8.2,
    "max_drawdown": -28.5
  },
  "annual_returns": {
    "2020": {"portfolio": 15.2, "benchmark": 18.4, "alpha": -3.2},
    "2021": {...}
  },
  "period_results": [...],
  "worst_periods": [...],
  "best_periods": [...]
}
```

### 6.2 Rapport Markdown

Généré automatiquement avec:
- Tableaux de performance
- Analyse des pires/meilleures périodes
- Verdict et recommandations

---

## 7. Limites et Biais

### 7.1 Biais Potentiels

| Biais | Description | Mitigation |
|-------|-------------|------------|
| **Survivorship** | S&P 500 actuel != historique | Utiliser constituants historiques |
| **Look-ahead** | Données futures dans le scoring | Paramètres figés |
| **Transaction costs** | Non inclus | Ajouter 10-20 bps/trimestre |
| **Slippage** | Non inclus | Conservateur sur les small caps |

### 7.2 Hypothèses Simplificatrices

1. **Rebalancing instantané** au début de chaque trimestre
2. **Pas de coûts de transaction** (conservateur: -0.5% annuel)
3. **Liquidité parfaite** (raisonnable pour S&P 500)
4. **Dividendes réinvestis** (prix ajustés)

---

## 8. Utilisation

### 8.1 Ligne de commande

```bash
# Backtest complet 2020-2024
python -m src.backtest_walkforward --start 2020-01-01 --end 2024-12-31

# Avec rapport Markdown
python -m src.backtest_walkforward --start 2020-01-01 --markdown

# Benchmark différent
python -m src.backtest_walkforward --benchmark QQQ
```

### 8.2 En Python

```python
from src.backtest_walkforward import WalkForwardBacktester

bt = WalkForwardBacktester()
bt.run(start_date="2020-01-01", end_date="2024-12-31")
report = bt.generate_report(output_path="backtest_report.json")

print(f"CAGR: {report.summary['portfolio_cagr']:.2f}%")
print(f"Alpha: {report.summary['total_alpha']:.2f}%")
print(f"Hit Rate: {report.summary['hit_rate']:.1f}%")
```

---

## 9. Critères de Validation

### 9.1 Minimum Viable

| Critère | Seuil | Statut |
|---------|-------|--------|
| Alpha cumulé | > 0% | ❓ |
| Hit Rate | > 50% | ❓ |
| Max Drawdown | > -40% | ❓ |
| Information Ratio | > 0.3 | ❓ |

### 9.2 Objectif "Pro"

| Critère | Seuil | Statut |
|---------|-------|--------|
| Alpha annualisé | > 2% | ❓ |
| Hit Rate | > 55% | ❓ |
| Max Drawdown | > -35% | ❓ |
| Information Ratio | > 0.5 | ❓ |
| Sharpe Ratio | > 0.7 | ❓ |

---

## 10. Prochaines Améliorations (v3.0)

1. **Constituants historiques S&P 500** (survivorship bias)
2. **Coûts de transaction** explicites
3. **Stress tests** (2008, 2020 COVID, 2022 hausse taux)
4. **Factor attribution** (décomposition de l'alpha)
5. **Monte Carlo** pour intervalles de confiance

---

*Document généré pour SmartMoney v2.4 — Étape 3 Backtest*
