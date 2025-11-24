# 📊 Smart Money Manual Collector V3

## 🎯 Description

Interface web interactive pour la collecte manuelle des données Smart Money depuis HedgeFollow avec parsing automatique intelligent.

## ✨ Fonctionnalités

### 🤖 Parser Intelligent
- **Auto-détection** du format HedgeFollow
- **Reconnaissance** automatique des séparateurs (tabs, pipes, espaces)
- **Extraction** intelligente des patterns ($, %, M/B/K)
- **Support** multi-formats de données

### 💾 Gestion des Données
- **10 Fonds × 30 Holdings** : Structure complète
- **Sauvegarde locale** : Persistance automatique dans localStorage
- **Export JSON** : Format compatible avec le pipeline d'analyse
- **Stats temps réel** : Progression et métriques

### 🎨 Interface Utilisateur
- **Onglets** avec badges de progression
- **Zone de collage rapide** avec parsing auto
- **Validation visuelle** des données
- **Feedback immédiat** sur le parsing

## 🚀 Usage

### 1. Ouvrir l'Interface
```bash
# Ouvrir directement dans le navigateur
tools/manual-collector/smart_money_collector_v3.html
```

### 2. Collecter les Données

#### Méthode Rapide (Recommandée)
1. Sur HedgeFollow, sélectionner et copier :
   - Le titre du portfolio (ex: "Jim Simons 13F Portfolio")
   - Les infos du fond
   - Le tableau des holdings

2. Dans l'interface :
   - Coller dans la zone "Collage Rapide HedgeFollow"
   - Cliquer "Parser Auto" 🤖
   - Les données se remplissent automatiquement !

#### Méthode Manuelle
- Remplir directement les champs du formulaire
- Utile pour corrections ou ajustements

### 3. Générer et Exporter

```javascript
// Format JSON généré
{
  "metadata": {
    "last_updated": "2024-11-24",
    "source": "HedgeFollow Manual Collection V3",
    "description": "Top hedge funds by performance"
  },
  "top_funds": [
    {
      "fund_id": "renaissance-technologies",
      "fund_name": "Renaissance Technologies",
      "portfolio_manager": "Jim Simons",
      "performance_3y": 19.55,
      "aum_billions": 75.79,
      "total_holdings": 3457,
      "top_holdings": [...]
    }
  ],
  "smart_universe_summary": {
    "total_unique_tickers": 95,
    "tickers_list": [...],
    "most_held_tickers": [...]
  }
}
```

## 📋 Formats Reconnus

### Titre Portfolio
```
Jim Simons 13F Portfolio
```

### Info Fond
```
Renaissance Technologies | Jim Simons | 19.55% | $75.79B | 3457
```

### Holdings
```
# Format 1 - Avec tabs
1.26%	6.88M	$953.51M	12.81%	$60.8	+46.8%

# Format 2 - Avec ticker
RBLX | Roblox Corp | 1.26% | 6.88M | $953.51M
```

## 🛠️ Intégration Pipeline

### Avec le Script Python
```python
from src.analyzers.smart_money_manual import SmartMoneyManualAnalyzer

# Charger et analyser
analyzer = SmartMoneyManualAnalyzer('smart_money_data_2024-11-24.json')
analyzer.process_data()
analyzer.calculate_signals()

# Top signaux
top_signals = analyzer.get_top_signals(20)
print(top_signals)

# Export univers
analyzer.export_universe('smart_universe.csv')
```

### Workflow Complet
```bash
# 1. Collecter via interface
open tools/manual-collector/smart_money_collector_v3.html

# 2. Générer JSON (dans l'interface)
# 3. Analyser
python src/analyzers/analyze_smart_money_manual.py

# 4. Intégrer avec pipeline existant
python -m src.pipelines.smart_money_consolidator
```

## 🎯 Avantages

✅ **Contournement anti-bot** : Pas de scraping automatique
✅ **Contrôle total** : Validation visuelle des données
✅ **Parser intelligent** : Détection automatique du format
✅ **Sauvegarde automatique** : Pas de perte de données
✅ **Compatible** : Format JSON standard du pipeline

## 📊 Métriques

- **Progression** : % de completion en temps réel
- **Badges** : Indicateurs visuels par fond
- **Stats** : Nombre de fonds, holdings, tickers uniques
- **Performance moyenne** : Calcul automatique

## 🔧 Configuration

```javascript
// Dans collector.js
const NUM_FUNDS = 10;     // Nombre de fonds
const NUM_HOLDINGS = 30;  // Holdings par fond
```

## 💾 Stockage Local

Les données sont automatiquement sauvegardées dans `localStorage` :
- Clé : `smartMoneyDataV3`
- Format : JSON stringifié
- Persistance : Entre sessions navigateur

## 🐛 Troubleshooting

### Le parsing ne fonctionne pas ?
- Vérifier le format des données copiées
- S'assurer que les séparateurs sont cohérents
- Utiliser la saisie manuelle en cas d'échec

### Données perdues ?
- Cliquer "Charger" pour récupérer la sauvegarde locale
- Les données sont sauvegardées automatiquement à chaque modification

## 📈 Prochaines Améliorations

- [ ] Support CSV import/export
- [ ] Validation avancée des données
- [ ] Graphiques de visualisation intégrés
- [ ] Support multi-sources (Dataroma, etc.)
- [ ] Mode batch pour plusieurs dates

---

**Développé pour le projet SmartMoney Scraper** 🚀