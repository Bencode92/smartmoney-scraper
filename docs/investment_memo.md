# SmartMoney v2.4 — Investment Memo

**Classification:** Confidentiel  
**Version:** 2.4.0  
**Date:** Décembre 2025  
**Auteur:** Équipe SmartMoney  

---

## Table des Matières

1. [Résumé Exécutif](#1-résumé-exécutif)
2. [Stratégie et Méthodologie](#2-stratégie-et-méthodologie)
3. [Performance et Backtest](#3-performance-et-backtest)
4. [Risques et Limites](#4-risques-et-limites)
5. [Recommandations et Usage](#5-recommandations-et-usage)

---

## 1. Résumé Exécutif

### 1.1 Positionnement

> **SmartMoney v2.4 est une stratégie Long-Only Large Cap US Quality/Value avec overlay Smart Money, concentrée.**

| Caractéristique | Valeur |
|-----------------|--------|
| **Univers** | S&P 500 |
| **Style** | Quality/Value + Smart Money |
| **Positions** | 15-20 titres |
| **Concentration max** | 12% par ligne, 30% par secteur |
| **Rebalancing** | Trimestriel |
| **Capacité cible** | 1-5 M$ |
| **Horizon** | 3-5 ans |

### 1.2 Proposition de Valeur

La stratégie exploite trois sources d'alpha potentiel :

1. **Smart Money Signal (25%)** — Suivi des positions des hedge funds (13F) et transactions insiders
2. **Quality Tilt (25%)** — Sélection de sociétés à haute rentabilité (ROIC, marges, FCF growth)
3. **Value Tilt (30%)** — Valorisation attractive (FCF Yield, EV/EBIT, P/E relatif)

### 1.3 Verdict

| Critère | Objectif | Résultat | Status |
|---------|----------|----------|--------|
| Alpha annualisé | > 2% | À valider | ⏳ |
| Hit Rate | > 55% | À valider | ⏳ |
| Max Drawdown | > -35% | Cible -35% à -40% | ⚠️ |
| Information Ratio | > 0.5 | À valider | ⏳ |

**Recommandation :** Utilisable en **poche satellite** (10-20% du portefeuille) pour investisseurs avec horizon long et tolérance au tracking error.

---

## 2. Stratégie et Méthodologie

### 2.1 Processus d'Investissement

```
┌─────────────────────────────────────────────────────────────────┐
│                     SMARTMONEY v2.4 PIPELINE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. UNIVERS           S&P 500 (500 titres)                     │
│       │                                                         │
│       ▼                                                         │
│  2. SCORING           Multi-factoriel (6 facteurs)             │
│       │               - Smart Money: 15%                        │
│       │               - Insider: 10%                            │
│       │               - Value: 30%                              │
│       │               - Quality: 25%                            │
│       │               - Momentum: 5%                            │
│       │               - Risk: 15% (inversé)                     │
│       ▼                                                         │
│  3. RANKING           Top 50 par score composite                │
│       │                                                         │
│       ▼                                                         │
│  4. OPTIMISATION      Contraintes enforced                      │
│       │               - Max 12% par position                    │
│       │               - Max 30% par secteur                     │
│       │               - 15-20 positions                         │
│       ▼                                                         │
│  5. PORTEFEUILLE      15-20 positions optimisées               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Facteurs de Scoring

#### Smart Money (15%)
- **Source :** Filings 13F (hedge funds), Form 4 (insiders)
- **Signal :** Changements trimestriels des positions institutionnelles
- **Latence :** 45 jours (délai de publication 13F)

#### Insider Activity (10%)
- **Source :** Form 4 SEC
- **Signal :** Ratio achats/ventes, montant relatif
- **Avantage :** Information asymétrique légale

#### Value (30%) — *Cross-sectionnel v2.4*
- **Métriques :** FCF Yield, EV/EBIT, P/E
- **Méthode :** Percentiles vs univers (pas de seuils absolus)
- **Pondération :** 40% FCF Yield, 40% EV/EBIT, 20% P/E

#### Quality (25%)
- **Métriques :** ROIC, Marge opérationnelle, FCF Growth
- **Seuils :** ROIC > 15%, Marge > médiane secteur
- **Stabilité :** Croissance FCF positive sur 3 ans

#### Momentum (5%)
- **Métriques :** RSI, Performance 3 mois
- **Usage :** Confirmation, pas de signal primaire
- **Filtre :** Éviter les titres en chute libre

#### Risk (15%, inversé)
- **Métriques :** Volatilité 30j, Beta, Distance au plus haut
- **Objectif :** Pénaliser les titres trop volatils
- **Calcul :** Score = 1 - Risk_normalized

### 2.3 Optimisation de Portefeuille

```python
# Contraintes v2.4 (RÉELLEMENT enforced)
CONSTRAINTS = {
    "max_weight": 0.12,      # 12% max par position
    "max_sector": 0.30,      # 30% max par secteur
    "min_positions": 15,
    "max_positions": 20,
    "sum_weights": 1.00,     # Fully invested
}

# Objectif : Maximiser le score composite sous contraintes
# Pas d'optimisation mean-variance (pas de matrice de covariance fiable)
```

### 2.4 Expositions Factorielles

| Facteur | Exposition | Source | Benchmark |
|---------|------------|--------|-----------|
| **Market Beta** | 0.95-1.10 | Large Cap US | SPY (1.00) |
| **Value** | +0.05 à +0.15 | FCF Yield, P/E | IVE |
| **Quality** | +0.10 à +0.25 | ROIC, Marges | QUAL |
| **Momentum** | -0.05 à +0.10 | Perf 3M | MTUM |
| **Size** | Large/Mega Cap | S&P 500 | IWB |

---

## 3. Performance et Backtest

### 3.1 Méthodologie de Backtest

| Paramètre | Valeur |
|-----------|--------|
| **Type** | Walk-forward out-of-sample |
| **Période** | 2020-01-01 → 2024-12-31 |
| **Test window** | 1 trimestre |
| **Rebalancing** | Début de trimestre |
| **Paramètres** | FIGÉS pendant tout le backtest |
| **Benchmark** | SPY (SPDR S&P 500 ETF) |

### 3.2 Résultats Attendus (Cibles)

| Métrique | Cible | Acceptable | Échec |
|----------|-------|------------|-------|
| **CAGR** | > 12% | 8-12% | < 8% |
| **Alpha annualisé** | > 2% | 0-2% | < 0% |
| **Hit Rate** | > 55% | 50-55% | < 50% |
| **Sharpe Ratio** | > 0.7 | 0.5-0.7 | < 0.5 |
| **Information Ratio** | > 0.5 | 0.3-0.5 | < 0.3 |
| **Max Drawdown** | > -30% | -30% à -40% | < -40% |
| **Tracking Error** | 8-12% | 6-15% | > 15% |

### 3.3 Performance par Régime de Marché

| Régime | Comportement Attendu | Raison |
|--------|---------------------|--------|
| **Bull Market** | Légère sous-perf | Biais Value/Quality vs Growth |
| **Bear Market** | Surperformance | Quality + Low Vol tilt |
| **Rally Growth** | Sous-perf significative | Value drag |
| **Rotation Value** | Surperformance | Value + Smart Money |
| **Hausse taux** | Neutre à négatif | Dépend du secteur |
| **Récession** | Beta ≈ 1 (pas de protection) | Long-only, pas de hedge |

### 3.4 Pires Scénarios Historiques (Stress Tests)

| Période | Événement | SPY | SmartMoney (estimé) | Commentaire |
|---------|-----------|-----|---------------------|-------------|
| **Mars 2020** | COVID Crash | -34% | -30% à -35% | Beta ≈ 1, pas de protection |
| **2022** | Hausse taux | -19% | -15% à -22% | Value aide, Quality souffre |
| **2015-2016** | Correction | -13% | -10% à -15% | Légère surperf possible |
| **Q4 2018** | Vol spike | -20% | -18% à -22% | Concentration = risque |

---

## 4. Risques et Limites

### 4.1 Risques Principaux

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Concentration** | Haute | Élevé | Limites 12%/30% |
| **Value Trap** | Moyenne | Élevé | Quality overlay |
| **Smart Money Lag** | Moyenne | Moyen | Délai 13F = 45j |
| **Crowding** | Moyenne | Moyen | Diversification facteurs |
| **Drawdown sévère** | Moyenne | Élevé | Sizing approprié |

### 4.2 Limites Structurelles

1. **Long-Only** — Pas de protection en bear market
2. **Large Cap uniquement** — Manque les opportunités small/mid
3. **US uniquement** — Pas de diversification géographique
4. **Pas de timing** — Fully invested en permanence
5. **Latence données** — 13F avec 45 jours de retard

### 4.3 Risques de Modèle

| Risque | Description | Statut |
|--------|-------------|--------|
| **Overfitting** | Paramètres optimisés sur le passé | ⚠️ Atténué par walk-forward |
| **Survivorship bias** | S&P 500 actuel ≠ historique | ⚠️ Non corrigé |
| **Look-ahead bias** | Données futures dans le scoring | ✅ Paramètres figés |
| **Transaction costs** | Non inclus dans backtest | ⚠️ Estimer -0.5%/an |

### 4.4 Scénarios de Sous-Performance

| Scénario | Durée possible | Impact relatif |
|----------|----------------|----------------|
| Rally Tech/Growth pur | 12-24 mois | -10% à -15% |
| Bull market momentum | 6-12 mois | -5% à -10% |
| Rotation sectorielle défavorable | 3-6 mois | -5% à -8% |
| Crowding Smart Money | Variable | -3% à -7% |

---

## 5. Recommandations et Usage

### 5.1 Profil Investisseur Cible

| Critère | Requis |
|---------|--------|
| **Horizon** | ≥ 3 ans (idéal 5 ans) |
| **Tolérance drawdown** | Accepte -35% à -40% |
| **Tracking error** | Accepte 8-12% vs SPY |
| **Sophistication** | Comprend les biais factoriels |
| **Liquidité** | Pas de besoin court terme |

### 5.2 Allocation Recommandée

```
┌─────────────────────────────────────────────────────┐
│              ALLOCATION SUGGÉRÉE                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Core (80-90%)                                      │
│  ├── ETF Broad Market (SPY/VTI): 60-70%            │
│  └── ETF Obligataire (AGG/BND): 20%                │
│                                                     │
│  Satellite (10-20%)                                 │
│  └── SmartMoney v2.4: 10-20%  ◄── ICI              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Sizing :**
- **Conservateur :** 10% du portefeuille total
- **Modéré :** 15% du portefeuille total
- **Agressif :** 20% du portefeuille total (max recommandé)

### 5.3 Opérations

| Aspect | Recommandation |
|--------|----------------|
| **Rebalancing** | Trimestriel (début Q) |
| **Review** | Mensuel (monitoring) |
| **Coûts estimés** | ~0.5% annuel (transactions) |
| **Reporting** | Mensuel vs SPY |

### 5.4 Triggers de Révision

| Trigger | Action |
|---------|--------|
| Drawdown > -25% | Review des positions |
| Underperf SPY > 10% sur 12M | Analyse factorielle |
| Concentration secteur > 35% | Rebalancing forcé |
| 3 trimestres consécutifs négatifs | Revue stratégique |

### 5.5 Évolutions Prévues (v3.0)

| Amélioration | Priorité | Timeline |
|--------------|----------|----------|
| Constituants historiques S&P | Haute | Q1 2026 |
| Coûts de transaction explicites | Haute | Q1 2026 |
| Attribution factorielle | Moyenne | Q2 2026 |
| Extension Mid Cap | Basse | Q3 2026 |
| Stress tests automatisés | Moyenne | Q2 2026 |

---

## Annexes

### A. Paramètres Figés v2.4

```python
WEIGHTS_V23 = {
    "smart_money": 0.15,
    "insider": 0.10,
    "momentum": 0.05,
    "value": 0.30,
    "quality": 0.25,
    "risk": 0.15,
}

CONSTRAINTS_V23 = {
    "max_weight": 0.12,
    "max_sector": 0.30,
    "min_positions": 15,
    "max_positions": 20,
}

VALUE_SCORING_MODE = "cross_sectional"
```

### B. ETF de Référence

| Facteur | ETF | Ticker |
|---------|-----|--------|
| Market | SPDR S&P 500 | SPY |
| Value | iShares S&P 500 Value | IVE |
| Quality | iShares MSCI USA Quality | QUAL |
| Momentum | iShares MSCI USA Momentum | MTUM |
| Low Vol | Invesco S&P 500 Low Vol | SPLV |

### C. Glossaire

| Terme | Définition |
|-------|------------|
| **13F** | Filing trimestriel SEC pour institutions >$100M |
| **Form 4** | Déclaration des transactions insiders |
| **CAGR** | Compound Annual Growth Rate |
| **Hit Rate** | % de périodes avec alpha positif |
| **Information Ratio** | Alpha / Tracking Error |
| **Tracking Error** | Volatilité de l'alpha |
| **FCF Yield** | Free Cash Flow / Market Cap |
| **ROIC** | Return on Invested Capital |

---

**Document préparé pour présentation Investment Committee**

*Ce memo ne constitue pas un conseil en investissement. Les performances passées ne préjugent pas des performances futures. Tout investissement comporte des risques de perte en capital.*

---

**Contacts :**
- Repository : [github.com/Bencode92/smartmoney-scraper](https://github.com/Bencode92/smartmoney-scraper)
- Version : v2.4.0
- Dernière mise à jour : Décembre 2025
