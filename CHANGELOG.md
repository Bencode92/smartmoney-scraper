# Changelog

Toutes les modifications notables de SmartMoney sont documentées ici.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## [2.4.0] - 2025-12-04

### 🎯 "Version Institutionnalisable"

Première version avec contraintes réellement enforced, backtest walk-forward,
et documentation complète pour présentation Investment Committee.

### Added

#### Étape 1 — Hygiène technique
- ✅ Contraintes `max_weight` et `max_sector` RÉELLEMENT enforced dans l'optimiseur
- ✅ Tests unitaires complets (`tests/test_constraints.py`)
- ✅ Validation automatique des contraintes

#### Étape 2 — Clarification factorielle
- ✅ Score Value **cross-sectionnel** (percentiles vs seuils absolus)
- ✅ 3 modes de scoring : `absolute`, `cross_sectional`, `sector_neutral`
- ✅ Documentation des expositions factorielles (`docs/factor_exposures.md`)
- ✅ Paramètre `VALUE_SCORING_MODE` dans config

#### Étape 3 — Backtest sérieux
- ✅ Walk-forward backtest out-of-sample (`src/backtest_walkforward.py`)
- ✅ Price loader multi-sources (`src/price_loader.py`)
- ✅ Générateur de rapport (`src/generate_backtest_report.py`)
- ✅ Méthodologie documentée (`docs/backtest_methodology.md`)
- ✅ Tests unitaires backtest (`tests/test_backtest.py`)

#### Étape 4 — Usage "pro"
- ✅ Investment Memo 5 pages (`docs/investment_memo.md`)
- ✅ Slide deck 20 slides (`docs/slides_investment_committee.md`)
- ✅ Résumé exécutif automatique

### Changed
- Score Value utilise maintenant les percentiles par défaut (meilleure discrimination)
- Configuration v2.4 avec `FACTOR_EXPOSURE_TARGETS` et `FACTOR_ETF_PROXIES`
- Requirements mis à jour avec `yfinance`

### Fixed
- 🐛 Optimiseur ignorait les contraintes `max_sector` (corrigé)
- 🐛 Clustering des scores Value sur univers homogène (corrigé)

### Documentation
- Investment Memo complet (5 pages)
- Slide deck Investment Committee (20 slides)
- Méthodologie backtest détaillée
- Expositions factorielles documentées

---

## [2.3.0] - 2025-11

### Added
- Refonte du scoring multi-factoriel
- Ajout des facteurs Value et Quality
- Réduction du poids Smart Money (45% → 15%)

### Changed
- `WEIGHTS_V23` avec nouvelle répartition
- Contraintes déclarées (mais non enforced)

---

## [2.2.0] - 2025-10

### Added
- Scoring Smart Money initial
- Pipeline de données 13F
- Insider tracking

---

## [2.1.0] - 2025-09

### Added
- Structure de base du projet
- Scraping données financières
- Configuration initiale

---

## Roadmap v3.0

| Amélioration | Priorité | Timeline |
|--------------|----------|----------|
| Constituants historiques S&P | Haute | Q1 2026 |
| Coûts de transaction explicites | Haute | Q1 2026 |
| Attribution factorielle | Moyenne | Q2 2026 |
| Stress tests automatisés | Moyenne | Q2 2026 |
| Extension Mid Cap | Basse | Q3 2026 |

---

*Maintenu par l'équipe SmartMoney*
