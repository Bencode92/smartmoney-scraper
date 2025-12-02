# SmartMoney Scraper 🚀

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

📊 **Scraper Python robuste et intelligent pour données hedge funds et superinvestors**

---

## 🆕 Version 2.3 — Buffett-Style Scoring

### Changements clés vs v2.2

| Aspect | v2.2 (Legacy) | v2.3 (Buffett-Style) |
|--------|---------------|----------------------|
| Score smart_money | **45%** (dominant) | **15%** (signal secondaire) |
| Score value | ❌ | **30%** (FCF Yield, EV/EBIT, MoS) |
| Score quality | 15% (basique) | **25%** (ROIC, FCF growth, stability) |
| Score risk | Implicite | **15%** (inversé : leverage, coverage) |
| Filtres | Min price + score | Liquidité + Hard filters + Score |
| Univers final | ~60-80 tickers | ~25-35 tickers (plus strict) |

### Usage rapide

```bash
# Nouveau pipeline v2.3 (défaut)
python main.py --engine v23

# Legacy pipeline v2.2
python main.py --engine v22

# Options avancées
python main.py --engine v23 --top-n 50 --dry-run --verbose
```

### Architecture des Engines

```
src/
├── engine_base.py        # Tronc commun (ABC)
│   ├── load_data()       # Chargement JSON
│   ├── enrich()          # API Twelve Data
│   ├── optimize()        # HRP
│   └── export()          # JSON/CSV
│
├── engine_v22.py         # Legacy (smart money dominant)
│   ├── calculate_scores()
│   └── apply_filters()
│
└── engine_v23.py         # Buffett-style
    ├── apply_filters_v23()     # Liquidité + Hard filters
    ├── calculate_scores_v23()  # Value + Quality + Risk
    └── get_top_buffett()       # Top N par Buffett score
```

---

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

### Pipeline Portfolio (v2.3)

```bash
# Génération complète du portefeuille
python main.py --engine v23

# Dry-run (pas d'export)
python main.py --engine v23 --dry-run

# Comparer v2.2 vs v2.3
python main.py --engine v22 --output-dir outputs/v22
python main.py --engine v23 --output-dir outputs/v23
```

### Utilisation Programmatique

```python
from src.engine_v23 import SmartMoneyEngineV23

engine = SmartMoneyEngineV23()
engine.load_data()
engine.enrich(top_n=50)
engine.clean_universe(strict=False)
engine.apply_filters_v23()      # Filtres liquidité + hard
engine.calculate_scores_v23()   # Scoring Buffett-style
engine.apply_filters()          # Filtre score minimum
engine.optimize()               # HRP
engine.export(output_dir)

# Top 10 par Buffett score
print(engine.get_top_buffett(10))
```

### Tests de Validation

```bash
# Tous les tests
pytest tests/ -v

# Tests spécifiques v2.3
pytest tests/test_v23_sprint1.py tests/test_v23_sprint2.py tests/test_v23_sprint3.py -v

# Tests d'isolation architecture (guard)
pytest tests/test_v23_guard.py -v

# Smoke test complet
python scripts/smoke_test_v23_full.py
```

## 📊 Architecture Complète

```
smartmoney-scraper/
├── config.py              # Configuration v2.2
├── config_v23.py          # Configuration v2.3 (poids, contraintes)
├── main.py                # Point d'entrée avec switch --engine
│
├── src/
│   ├── engine_base.py     # Classe abstraite commune
│   ├── engine_v22.py      # Engine legacy
│   ├── engine_v23.py      # Engine Buffett-style
│   │
│   ├── filters/           # 🆕 Filtres v2.3
│   │   ├── liquidity.py   # Market cap, ADV
│   │   ├── hard_filters.py # D/E, Interest Coverage
│   │   └── look_ahead.py  # Contrôle publication lag
│   │
│   ├── scoring/           # 🆕 Scoring v2.3
│   │   ├── value_composite.py   # FCF Yield, EV/EBIT, MoS
│   │   ├── quality_composite.py # ROIC, FCF growth, stability
│   │   ├── risk_score.py        # Leverage, coverage (inversé)
│   │   └── composite.py         # Agrégation + Buffett score
│   │
│   ├── backtest/          # 🆕 Backtest v2.3
│   │   ├── backtest_v23.py # Walk-forward
│   │   ├── metrics.py      # Sharpe, Max DD, etc.
│   │   ├── stress_tests.py # Régimes de marché
│   │   └── reports.py      # Export HTML/CSV
│   │
│   └── validation/        # Validation données
│       └── data_validator.py
│
├── tests/
│   ├── test_v23_sprint1.py  # Tests filtres
│   ├── test_v23_sprint2.py  # Tests scoring
│   ├── test_v23_sprint3.py  # Tests backtest
│   └── test_v23_guard.py    # 🆕 Tests isolation architecture
│
└── scripts/
    ├── smoke_test_v23.py       # Sprint 1
    ├── smoke_test_v23_scoring.py # Sprint 2
    ├── smoke_test_v23_full.py    # Sprint 3
    └── run_backtest_v23.py       # Backtest complet
```

## 🔧 Configuration v2.3

### Poids (config_v23.py)

```python
WEIGHTS_V23 = {
    "smart_money": 0.15,  # Réduit de 45%
    "insider": 0.10,
    "momentum": 0.05,
    "value": 0.30,        # Nouveau
    "quality": 0.25,      # Nouveau
    "risk": 0.15,         # Nouveau (inversé)
}
```

### Contraintes

```python
CONSTRAINTS_V23 = {
    "min_positions": 12,
    "max_positions": 20,
    "max_weight": 0.12,
    "min_score": 0.40,
}
```

### Filtres de liquidité

```python
LIQUIDITY_FILTERS = {
    "min_market_cap": 2_000_000_000,  # $2B
    "min_avg_volume": 5_000_000,      # $5M ADV
}
```

## 📈 Outputs v2.3

### portfolio.json

```json
{
  "metadata": {
    "generated_at": "2025-12-02T14:00:00",
    "engine_version": "2.3",
    "positions": 18
  },
  "portfolio": [
    {
      "symbol": "AAPL",
      "weight": 0.0823,
      "score_composite": 0.682,
      "buffett_score": 0.715,
      "score_value": 0.68,
      "score_quality": 0.75,
      "score_risk": 0.72
    }
  ]
}
```

## 🧪 Tests et Validation

### Structure des Tests v2.3

```bash
# Tests d'isolation (CRITIQUE)
pytest tests/test_v23_guard.py -v
# ✅ v2.3 hérite de Base, pas de v2.2
# ✅ Méthodes de scoring locales
# ✅ Poids différents de v2.2

# Tests fonctionnels
pytest tests/test_v23_sprint1.py -v  # Filtres
pytest tests/test_v23_sprint2.py -v  # Scoring
pytest tests/test_v23_sprint3.py -v  # Backtest
```

## 📊 Backtest v2.3

```bash
# Backtest complet
python scripts/run_backtest_v23.py

# Options
python scripts/run_backtest_v23.py \
    --start 2015-01-01 \
    --end 2024-12-31 \
    --rebalance quarterly \
    --output outputs/backtest_v23
```

### Métriques générées

- **Sharpe Ratio** (cible ≥ 0.55)
- **Max Drawdown** (cible ≤ -25%)
- **CAGR** (vs S&P 500)
- **Turnover** annualisé
- **Stress tests** par régime (bull, bear, recovery, sideways)

## 🔄 Prochaines Étapes

- [x] v2.3 Sprint 1 : Filtres (liquidité, hard, look-ahead)
- [x] v2.3 Sprint 2 : Scoring (value, quality, risk)
- [x] v2.3 Sprint 3 : Backtest (walk-forward, stress tests)
- [x] Architecture propre (BaseEngine)
- [ ] Validation sur données réelles
- [ ] Comparaison backtest v2.2 vs v2.3
- [ ] Intégration API enrichissement
- [ ] Dashboard Streamlit

## 🤝 Contribution

Les contributions sont bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md)

## 📜 License

MIT - Voir [LICENSE](LICENSE)

## ⚠️ Disclaimer

Ce projet est à des fins éducatives. Respectez les conditions d'utilisation des sites scrapés et les limites de rate.

---

**Développé avec ❤️ par [Bencode92](https://github.com/Bencode92)**
