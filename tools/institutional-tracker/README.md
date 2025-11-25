# 🏦 Institutional Tracker

Collecte et analyse les **Top 100 stocks owned by hedge funds** depuis HedgeFollow ou sources similaires.

## 📋 Usage

1. Ouvrir `institutional_collector.html` dans un navigateur
2. Copier-coller le tableau depuis la source (format vertical)
3. Cliquer **Parser**
4. Vérifier les données dans le tableau
5. **Download JSON** ou **Push to GitHub**

## 📊 Format d'entrée attendu

Le parser attend un format vertical (une donnée par ligne) :

```
NVDA
NVIDIA Corporation
1374    659    565
$ 2.73T
Technology
$86,62
$212,19
```

Où :
- L0: Ticker
- L1: Company Name
- L2: Total Holders | Medium Stakes | Large Stakes
- L3: Value Owned ($B ou $T)
- L4: Sector
- L5-L6: 52W Range (ignoré)

## 📤 Output JSON

```json
{
  "metadata": {
    "last_updated": "2025-01-15",
    "source": "Institutional Tracker - SmartMoney Scraper"
  },
  "summary": {
    "total_stocks": 100,
    "total_value_owned_billions": 15420.5,
    "average_holders_per_stock": 892
  },
  "sector_distribution": [...],
  "top_stocks": [...]
}
```

## 🔗 Intégration GitHub

Les fichiers sont pushés vers `data/raw/institutional/`.

## ⚠️ Limitations

- Parser optimisé pour le format HedgeFollow vertical
- La colonne 52W Range est ignorée (trop variable)
- Tickers limités à 1-6 caractères majuscules
