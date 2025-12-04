# Changelog SmartMoney

## [3.0.0] - 2025-12-04

### 🚀 Version Majeure: "Buffett-Quant"

Refonte complète de la philosophie d'investissement suite au feedback ChatGPT:
> "Si ton vrai ADN mental est Buffett, c'est incohérent d'avoir un moteur factoriel générique."

### Changed

**Poids Composite:**
- Value: 30% → 45%
- Quality: 25% → 35%
- Risk: 15% → 20%
- Smart Money: 15% → 0% (indicateur seulement)
- Insider: 10% → 0% (tie-breaker seulement)
- Momentum: 5% → 0% (supprimé)

**Quality Scorer:**
- AVANT: Seuils absolus (ROE > 15% = bon)
- APRÈS: Sector-relative (ROE ranké dans le secteur) + stabilité 5 ans

**Value Scorer:**
- AVANT: Seuils absolus (FCF yield > 8% = excellent)
- APRÈS: Cross-section (cheap vs pairs) + Margin of Safety vs historique

**Risk Scorer:**
- AVANT: Low vol académique
- APRÈS: Éviter perte permanente de capital (levier, coverage, drawdown)

### Added

- `config_v30.py` — Configuration Buffett-Quant complète
- `src/scoring/quality_v30.py` — Quality sector-relative
- `src/scoring/value_v30.py` — Value avec Margin of Safety
- `src/scoring/risk_v30.py` — Risk perte permanente
- `src/scoring/composite_v30.py` — Agrégation 45/35/20
- `docs/investment_guidelines_v30.md` — Document IC 12 sections
- `MIGRATION_V30.md` — Guide de migration
- `src/scoring/legacy/` — Wrappers rétrocompatibilité

### Deprecated

- `config_v23.py` → Utiliser `config_v30.py`
- `config_v25.py` → Utiliser `config_v30.py`
- `src/scoring/value_composite.py` → Utiliser `value_v30.py`
- `src/scoring/quality_composite.py` → Utiliser `quality_v30.py`
- `src/scoring/risk_score.py` → Utiliser `risk_v30.py`
- `src/scoring/composite.py` → Utiliser `composite_v30.py`

---

## [2.5.0] - 2025-12-03 (jamais déployé)

Version intermédiaire "IC Ready" remplacée par v3.0.

---

## [2.4.0] - 2025-12-01

### Changed
- Score Value cross-sectionnel (percentiles vs seuils absolus)
- Contraintes max_weight et max_sector réellement enforced
- Tests unitaires pour contraintes

---

## [2.3.1] - 2025-11-28

### Added
- Mode Buffett (filtres, scoring, contraintes portefeuille)
- Score Buffett séparé (60% qualité + 40% valorisation)

---

## [2.3.0] - 2025-11-15

### Changed
- Nouveaux poids (smart_money réduit de 45% à 15%)
- Ajout facteurs Value, Quality, Risk
- Hard filters (D/E, coverage, ND/EBITDA)
- Filtres de liquidité

---

## [2.2.0] - 2025-10-01

### Initial
- Première version avec Smart Money 45%, Insider 15%, Momentum 25%, Quality 15%
