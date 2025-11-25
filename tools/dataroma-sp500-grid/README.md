# Dataroma S&P500 Grid Collector

## 📊 Description

Collecteur pour le **S&P500 Grid** de Dataroma - rankings des superinvestors sur les valeurs S&P500.

## 🎯 Deux métriques

| Métrique | Description |
|----------|-------------|
| **% of total portfolio** | Pondération dans les portfolios agrégés |
| **Last 6 months buys** | Activité d'achat récente |

## 🚀 Usage

### Étape 1: Ownership
1. Aller sur [dataroma.com/m/g/portfolio_b.php](https://www.dataroma.com/m/g/portfolio_b.php)
2. Sélectionner "% of total portfolio"
3. Copier tous les tickers (ordre: gauche→droite, haut→bas)
4. Coller dans "% of Total Portfolio" et cliquer Parser

### Étape 2: 6M Buys  
1. Sur le même site, changer pour "Last 6 months buys"
2. Copier tous les tickers
3. Coller dans "Last 6 Months Buys" et cliquer Parser

### Étape 3: Export
- Les deux métriques sont fusionnées automatiquement
- Score composite calculé pour les tickers présents dans les deux listes
- Push to GitHub ou Download JSON

## 📈 Score Composite

```
composite_score = (ownership_score + buys_score) / 2

// Bonus +20% si top 50 dans les deux listes
if (ownership_rank <= 50 && buys_rank <= 50) {
    composite_score *= 1.2
}
```

## 📁 Output

```
data/raw/dataroma/sp500-grid/SP500_grid_YYYY-MM-DD.json
```

### Structure JSON

```json
{
  "metadata": {
    "source": "Dataroma",
    "dataset": "S&P500 Grid - Superinvestor Rankings"
  },
  "summary": {
    "total_unique_tickers": 450,
    "in_both_lists": 320,
    "top_50_both": 35
  },
  "sp500_ownership": [
    { "ticker": "MSFT", "rank": 1, "score": 100 },
    { "ticker": "AMZN", "rank": 2, "score": 95 }
  ],
  "sp500_6m_buys": [
    { "ticker": "NVDA", "rank": 1, "score": 100 }
  ],
  "composite_rankings": [
    {
      "composite_rank": 1,
      "ticker": "GOOGL",
      "ownership_rank": 3,
      "buys_rank": 2,
      "composite_score": 115,
      "top_50_bonus": true
    }
  ]
}
```

## 🔐 Sécurité

- Token GitHub en mémoire uniquement (session)
- Non persisté dans localStorage
