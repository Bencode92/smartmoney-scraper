# 🕵️ Insider Tracker - SmartMoney Scraper

## Description

Outil de collecte et d'analyse des transactions insiders (Form 4 SEC). Permet de détecter les signaux bullish/bearish basés sur les achats et ventes des dirigeants.

## Fonctionnalités

### 🔍 Parser Intelligent
- **Auto-détection** du format (OpenInsider, Finviz, CSV/TSV)
- **Parsing des suffixes** : k, M, B automatiquement convertis
- **Détection des rôles** : CEO, CFO, Director, 10% Owner, etc.
- **Classification des trades** : Sale Plan, Open Market, Tax Liability, etc.

### 📊 Analyse des Signaux

| Signal | Interprétation | Indicateur |
|--------|----------------|------------|
| Cluster de ventes (3+ insiders) | 🔴 Bearish fort | Plusieurs dirigeants vendent simultanément |
| Achat CEO/CFO open market | 🟢 Bullish fort | Skin in the game |
| Sale Plan (10b5-1) | ⚪ Neutre | Vente planifiée à l'avance |
| Tax Liability | ⚪ Neutre | Obligation fiscale |
| Grosse transaction (>$5M) | ⚠️ À surveiller | Volume significatif |

### 💾 Export & Intégration
- Export JSON structuré
- Push direct vers GitHub (`data/raw/insider/`)
- Compatible avec le pipeline SmartMoney

## Usage

### 1. Collecter les données

1. Aller sur [OpenInsider](http://openinsider.com/) ou source similaire
2. Filtrer les transactions (ex: >$1M, Past Week)
3. Sélectionner tout le tableau (Ctrl+A dans le tableau)
4. Copier (Ctrl+C)

### 2. Parser

1. Ouvrir `insider_collector.html` dans un navigateur
2. Coller dans la zone de texte
3. Cliquer "🧩 Parser"

### 3. Analyser

- Cliquer "📊 Analyser Signaux" pour voir les alertes
- Utiliser les filtres : Ventes, Achats, CEO/CFO, >$5M

### 4. Exporter

- **Download JSON** : Téléchargement local
- **Push to GitHub** : Envoi direct au repo (nécessite token)

## Structure JSON

```json
{
  "metadata": {
    "last_updated": "2025-11-25",
    "source": "Insider Tracker - SmartMoney Scraper",
    "total_trades": 42
  },
  "summary": {
    "total_transactions": 42,
    "total_sells": 38,
    "total_buys": 4,
    "unique_tickers": 15,
    "total_sell_value_millions": 156.8,
    "total_buy_value_millions": 12.3,
    "net_flow_millions": -144.5,
    "sell_buy_ratio": 9.5
  },
  "signals": {
    "cluster_sells": ["RDDT", "PLTR"],
    "top_net_sellers": [...],
    "top_net_buyers": [...],
    "ceo_cfo_activity": ["NET", "SION"]
  },
  "ticker_summary": [...],
  "insider_trades": [...]
}
```

## Interprétation des Signaux

### 🔴 Signaux Bearish

1. **Cluster de ventes** : 3+ insiders vendent le même ticker
   - Particulièrement significatif si C-suite impliqué
   - Vérifier si ce sont des Sale Plans ou open market

2. **Ratio sell/buy > 5** : Déséquilibre fort vers les ventes

3. **Grosse vente open market** : Vente non planifiée > $10M

### 🟢 Signaux Bullish

1. **Achat CEO/CFO** : Le dirigeant achète avec son propre argent
   - Signal le plus fort car ils connaissent l'entreprise
   - Vérifier le contexte (ex: après une baisse du cours)

2. **Cluster d'achats** : Plusieurs insiders achètent

3. **Ratio sell/buy < 0.5** : Plus d'achats que de ventes

### ⚪ Signaux Neutres

1. **Sale Plan (10b5-1)** : Planifié des mois à l'avance
2. **Tax Liability** : Vente forcée pour payer les impôts
3. **Gift** : Don d'actions (pas de signal prix)

## Configuration GitHub

Pour le push automatique :

1. Créer un token GitHub : Settings → Developer settings → Personal access tokens
2. Permissions requises : `Contents` (Read and write) sur `smartmoney-scraper`
3. Le token est stocké dans localStorage (une seule saisie)

## Intégration Pipeline

```python
# Exemple d'utilisation dans le pipeline
import json

with open('data/raw/insider/insider_trades_2025-11-25.json') as f:
    data = json.load(f)

# Tickers avec clusters de ventes
bearish_tickers = data['signals']['cluster_sells']

# Tickers avec activité C-suite
watch_list = data['signals']['ceo_cfo_activity']

# Filtrer par valeur
large_trades = [t for t in data['insider_trades'] 
                if abs(t['transaction_value_millions']) > 5]
```

## Limitations

- Données manuelles (pas de scraping automatique)
- Dépendant du format source
- Pas d'historique automatique (1 fichier par jour)

## Prochaines améliorations

- [ ] Support SEC EDGAR direct
- [ ] Historique avec diff
- [ ] Alertes email/Telegram
- [ ] Corrélation avec price action
- [ ] Backtesting des signaux

---

**Développé pour SmartMoney Scraper** 🚀
