# SmartMoney Scraper

📊 **Scraper Python pour données hedge funds et superinvestors**

## 🎯 Objectif

Ce projet récupère et consolide les données de :
- **HedgeFollow** : Top hedge funds, holdings, insider trading, stock screener
- **Dataroma** : Superinvestors, holdings, Grand Portfolio, Real-time insiders

## 📦 Installation

```bash
git clone https://github.com/Bencode92/smartmoney-scraper.git
cd smartmoney-scraper
pip install -r requirements.txt
cp .env.example .env
```

## 🚀 Usage

### Mise à jour complète
```bash
./scripts/run_pipeline.sh
```

### Mise à jour par source
```bash
# HedgeFollow uniquement
./scripts/update_hedgefollow.sh

# Dataroma uniquement  
./scripts/update_dataroma.sh
```

### Modules individuels
```bash
# Top hedge funds HedgeFollow
python -m src.hedgefollow.funds

# Holdings d'un fond spécifique
python -m src.hedgefollow.holdings

# Insider trading tracker
python -m src.hedgefollow.insiders
```

## 📊 Données générées

### Raw data (`data/raw/`)
- `hedgefollow/funds_top.csv` : Top hedge funds
- `hedgefollow/holdings_YYYYMMDD.csv` : Positions des fonds
- `hedgefollow/insiders_YYYYMMDD.csv` : Trades insiders
- `dataroma/managers.csv` : Superinvestors
- `dataroma/holdings_YYYYMMDD.csv` : Positions superinvestors
- `dataroma/grand_portfolio_YYYYMMDD.csv` : Agrégat Dataroma

### Processed data (`data/processed/`)
- `universe_smartmoney_YYYYMMDD.csv` : Univers consolidé

## 🛠 Architecture

```
src/
├── config.py          # Configuration globale
├── utils/             # Fonctions utilitaires
│   ├── http.py       # Requêtes HTTP avec retry
│   ├── parsing.py    # Parsing HTML et normalisation
│   └── io.py         # I/O CSV/SQLite
├── hedgefollow/      # Scrapers HedgeFollow
├── dataroma/         # Scrapers Dataroma
└── pipelines/        # Consolidation des données
```

## ⚙️ Configuration

Créez un fichier `.env` à partir de `.env.example` :

```bash
# API Keys (pour enrichissement futur)
TWELVE_DATA_API_KEY=your_key_here

# HTTP Settings
HTTP_USER_AGENT="Mozilla/5.0 (compatible; SmartMoneyBot/0.1)"
REQUESTS_SLEEP_SECONDS=2
```

## 📝 Notes

- **Rate limiting** : 2 secondes entre chaque requête par défaut
- **Retry** : 3 tentatives max en cas d'erreur
- **Stockage** : CSV par défaut, SQLite optionnel
- **Logs** : Tous les scrapes sont loggés dans la console

## 🔄 Prochaines étapes

- [ ] Enrichissement avec Twelve Data (prix, volumes, ratios)
- [ ] Détection automatique de signaux (accumulation, rotation)
- [ ] Dashboard de visualisation
- [ ] Alertes sur changements significatifs

## 📜 License

MIT
