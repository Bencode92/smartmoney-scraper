# SmartMoney Scraper 🚀

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

📊 **Scraper Python robuste et intelligent pour données hedge funds et superinvestors**

## 🎯 Objectif

Système de scraping professionnel avec anti-détection pour récupérer et consolider les données de :
- **HedgeFollow** : Top hedge funds, holdings, insider trading, stock screener
- **Dataroma** : Superinvestors, holdings, Grand Portfolio, Real-time insiders

## ✨ Fonctionnalités

### 🛡️ Robustesse
- ✅ **Validation des données** : Vérification automatique de la cohérence
- ✅ **Anti-détection** : Rotation de User-Agents et headers intelligents
- ✅ **Monitoring** : Métriques en temps réel et alertes
- ✅ **Tests automatisés** : Suite de tests complète
- ✅ **Gestion d'erreurs** : Retry intelligent avec backoff exponentiel

### 📈 Performance
- 🚀 Cache intelligent avec rafraîchissement automatique
- 📊 Métriques de qualité des données
- 🔄 Pipeline CI/CD via GitHub Actions
- 💾 Support CSV et formats optimisés

## 📦 Installation

```bash
git clone https://github.com/Bencode92/smartmoney-scraper.git
cd smartmoney-scraper
pip install -r requirements.txt
cp .env.example .env
```

## 🚀 Usage

### Utilisation Simple

```python
from src.hedgefollow.funds import get_top_n_funds

# Récupérer les top 10 hedge funds
funds = get_top_n_funds(
    n=10,
    min_aum=1_000_000_000,  # Minimum 1B$ AUM
    min_perf_3y=10.0         # Minimum 10% perf 3 ans
)
print(funds[['name', 'aum_usd', 'perf_3y']])
```

### Pipeline Complet

```bash
# Mise à jour complète avec monitoring
python -m src.hedgefollow.funds

# Ou via les scripts
./scripts/run_pipeline.sh
```

### Tests de Validation

```bash
# Lancer tous les tests
pytest tests/ -v

# Test spécifique avec coverage
pytest tests/test_hedgefollow_scraper.py -v --cov=src
```

## 📊 Architecture Améliorée

```
src/
├── config.py           # Configuration globale
├── validators.py       # 🆕 Validation robuste des données
├── utils/
│   ├── http.py        # 🔥 Anti-détection avancée
│   ├── monitoring.py  # 🆕 Métriques et alertes
│   ├── parsing.py     # Parsing HTML normalisé
│   └── io.py          # I/O optimisé
├── hedgefollow/       # Scrapers HedgeFollow
├── dataroma/          # Scrapers Dataroma
└── pipelines/         # Consolidation intelligente

tests/
└── test_hedgefollow_scraper.py  # 🆕 Tests complets
```

## 🛡️ Fonctionnalités de Sécurité

### Anti-Détection
- **Rotation User-Agent** : 12+ navigateurs différents
- **Headers dynamiques** : Accept-Language, Referer variés
- **Throttling intelligent** : Délais aléatoires et adaptatifs
- **Support proxy** : Rotation de proxies (optionnel)

### Validation des Données
```python
from src.validators import DataValidator

# Validation automatique
DataValidator.validate_funds(df, min_funds=5)
DataValidator.check_data_freshness(df, max_days=7)
```

### Monitoring en Temps Réel
```python
from src.utils.monitoring import track_performance, alerts

@track_performance("my_function")
def scrape_data():
    # Votre code
    pass

# Alertes automatiques
alerts.send_alert(
    "Scraping échoué",
    "Erreur critique détectée",
    level="CRITICAL"
)
```

## 📈 Métriques et KPIs

Le système track automatiquement :
- ⏱️ Temps d'exécution par module
- 📊 Taux de remplissage des colonnes
- ⚠️ Détection d'anomalies (outliers)
- ❌ Taux d'erreur et retry
- 📉 Volume de données scrapées

## 🔧 Configuration Avancée

### Variables d'Environnement

```bash
# API Keys (enrichissement futur)
TWELVE_DATA_API_KEY=your_key_here

# HTTP Settings
HTTP_USER_AGENT="Mozilla/5.0..."  # Optionnel, rotation auto
REQUESTS_SLEEP_SECONDS=2           # Délai entre requêtes

# Scraping Parameters
HEDGEFOLLOW_TOP_N_FUNDS=15
DATAROMA_TOP_N_MANAGERS=10
INSIDER_MIN_VALUE_USD=5000000

# Alerting (optionnel)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## 🧪 Tests et Validation

### Structure des Tests

```python
# Tests unitaires
test_validate_funds_success()      # Validation réussie
test_validate_funds_missing_data() # Gestion données manquantes
test_scraping_with_fallback()      # Stratégies de fallback

# Tests d'intégration
test_full_pipeline()                # Pipeline complet
test_network_resilience()           # Résilience réseau
```

### Lancer les Tests

```bash
# Tests rapides
pytest tests/ -v -m "not integration"

# Tests complets avec rapport
pytest tests/ -v --cov=src --cov-report=html
```

## 📊 Données Générées

### Structure des Données

```
data/
├── raw/
│   ├── hedgefollow/
│   │   ├── funds_top.csv          # Top hedge funds
│   │   ├── holdings_20241124.csv  # Positions détaillées
│   │   └── insiders_20241124.csv  # Trades insiders
│   └── dataroma/
│       ├── managers.csv           # Superinvestors
│       └── holdings_20241124.csv  # Positions
├── processed/
│   └── universe_smartmoney_20241124.csv  # Consolidé
└── metrics.jsonl                  # 🆕 Métriques de monitoring
```

### Format des Données

| Colonne | Type | Description |
|---------|------|-------------|
| fund_id | str | Identifiant unique |
| name | str | Nom du fond |
| aum_usd | float | Assets Under Management |
| perf_3y | float | Performance 3 ans (%) |
| num_holdings | int | Nombre de positions |
| scraped_at | datetime | Timestamp du scraping |

## 🚀 CI/CD avec GitHub Actions

### Workflows Automatisés

- **Daily Scraping** : Mise à jour quotidienne à 6h UTC
- **Weekly Full** : Scraping complet hebdomadaire
- **On Push** : Tests automatiques sur chaque commit

## 📈 Monitoring et Alertes

### Dashboard de Santé

```python
from src.utils.monitoring import check_scraping_health

health = check_scraping_health()
print(f"Status: {health['status']}")
# Output: Status: HEALTHY ✅
```

### Webhook Discord/Slack

Configuration automatique des alertes critiques via webhooks.

## 🔄 Prochaines Étapes

- [x] Validation robuste des données
- [x] Anti-détection avancée
- [x] Monitoring et métriques
- [x] Tests automatisés
- [ ] Enrichissement Twelve Data API
- [ ] Support Parquet/SQLite
- [ ] Dashboard Streamlit
- [ ] ML pour détection de patterns

## 🤝 Contribution

Les contributions sont bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md)

## 📜 License

MIT - Voir [LICENSE](LICENSE)

## ⚠️ Disclaimer

Ce projet est à des fins éducatives. Respectez les conditions d'utilisation des sites scrapés et les limites de rate.

---

**Développé avec ❤️ par [Bencode92](https://github.com/Bencode92)**
