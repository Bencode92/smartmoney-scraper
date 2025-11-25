# Dataroma Grand Portfolio Collector

## 📊 Description

Collecteur manuel pour les données **Grand Portfolio** de Dataroma (consensus superinvestors).

## 🔒 Sécurité

- **Token GitHub en mémoire uniquement** (pas de localStorage)
- Le token est demandé à chaque session
- Validation des données avant push

## 🚀 Usage

1. Ouvrir `dataroma_grand_portfolio.html` dans un navigateur
2. Aller sur [dataroma.com/m/g/portfolio.php](https://www.dataroma.com/m/g/portfolio.php)
3. Sélectionner et copier le tableau (de "Symbol" jusqu'à la dernière ligne)
4. Coller dans la zone de texte
5. Cliquer sur "Parser les données"
6. Vérifier la validation et l'aperçu
7. Push to GitHub ou Download JSON

## 📁 Output

Fichier JSON dans `data/raw/dataroma/grand-portfolio/GP_consensus_YYYY-MM-DD.json`

### Structure JSON

```json
{
  "metadata": {
    "source": "Dataroma",
    "dataset": "Grand Portfolio - Superinvestor Consensus",
    "as_of": "2025-11-25"
  },
  "summary": {
    "total_stocks": 10,
    "tier_a_count": 6,
    "tier_b_count": 4
  },
  "stocks": [
    {
      "symbol": "FISV",
      "company_name": "Fiserv Inc.",
      "portfolio_weight": 0.110,
      "buys_6m": 9,
      "buys_tier": "A",
      ...
    }
  ]
}
```

## 🏷️ Tiers de scoring

| Tier | Buys 6M | Signification |
|------|---------|---------------|
| A | ≥ 8 | Très forte conviction |
| B | 6-7 | Forte conviction |
| C | 3-5 | Conviction moyenne |
| D | < 3 | Faible conviction |

## ✅ Validations

- Minimum 5 stocks
- Symbols valides (1-5 lettres)
- Noms de compagnies présents
- Poids portfolio cohérents
- Buys ≥ 1
- Prix actuels > 0
