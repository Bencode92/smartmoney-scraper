# Investment Guidelines — SmartMoney v2.5

**Document IC / Investment Committee**  
**Date:** Décembre 2025  
**Version:** 2.5  
**Statut:** Forward Test

---

## 1. Résumé Exécutif

### 1.1 Description

SmartMoney v2.5 est un **moteur systématique de stock-picking US Large Cap**, construit sur une base factorielle **Value + Quality + Risk**.

### 1.2 Positionnement

| Caractéristique | Description |
|-----------------|-------------|
| **Asset Class** | Actions US Large Cap |
| **Univers** | S&P 500 (market cap > $10B) |
| **Style** | Quality/Value |
| **Positions** | 15-20 lignes |
| **Benchmark** | SPY (suivi, pas ciblé) |
| **Rôle portefeuille** | Poche satellite / high conviction |

### 1.3 Ce que c'est

- ✅ Un portefeuille factoriel Quality/Value discipliné
- ✅ Construction equal-weight + tilt par score
- ✅ Process transparent et auditable
- ✅ Contraintes enforced par code

### 1.4 Ce que ce n'est PAS

- ❌ Un clone du portefeuille Buffett (process différent)
- ❌ Un générateur d'alpha Smart Money (non prouvé)
- ❌ Une stratégie relative vs SPY (pas de tracking error cible)
- ❌ Un produit avec track record historique

---

## 2. Philosophie d'Investissement

### 2.1 Thèse Centrale

> "Sélectionner de bonnes entreprises (Quality), à des valorisations raisonnables (Value), avec un profil de risque maîtrisé (Risk)."

### 2.2 Inspiration

La philosophie générale est alignée avec les principes de l'investissement value :
- Acheter de bonnes entreprises
- À un prix raisonnable
- Pour les détenir longtemps

**Cependant**, le process reste **factoriel/quantitatif**, pas un stock-picking 100% bottom-up.

### 2.3 Facteurs Utilisés

| Facteur | Poids | Fondement | Implémentation |
|---------|-------|-----------|----------------|
| **Value** | 40% | Prime value (Fama-French 1992) | FCF yield, EV/EBIT, P/E vs historique |
| **Quality** | 35% | Avantage compétitif (Novy-Marx 2013) | ROE, ROIC, marges, stabilité |
| **Risk** | 25% | Low-vol anomaly (Ang 2006) | Leverage, coverage, volatilité (inversé) |

### 2.4 Facteurs Exclus du Composite

| Signal | Rôle | Raison |
|--------|------|--------|
| **Smart Money** | Indicateur seulement | Non prouvé empiriquement |
| **Insider** | Tie-breaker | Signal faible, bruit élevé |
| **Momentum** | Supprimé | Pas de vue, pas d'edge |

---

## 3. Univers d'Investissement

### 3.1 Définition

| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| Univers de base | S&P 500 | Liquidité, données fiables |
| Market cap minimum | $10 milliards | Large cap pur |
| ADV minimum | $5 millions | Liquidité quotidienne |
| % max ADV/jour | 5% | Impact de marché limité |

### 3.2 Filtres d'Exclusion (Hard Filters)

| Métrique | Seuil | Action |
|----------|-------|--------|
| D/E | > 3.0 | Exclu |
| ND/EBITDA | > 4.0 | Exclu |
| Interest Coverage | < 2.5 | Exclu |
| ROE | < 5% | Exclu |
| Historique | < 5 ans | Exclu |

### 3.3 Secteurs

Tous les secteurs GICS sont éligibles. Pas d'exclusion sectorielle systématique.

---

## 4. Construction du Portefeuille

### 4.1 Process

```
Univers S&P 500 (~500 titres)
        ↓
Filtres d'éligibilité (~350 titres)
        ↓
Scoring Value + Quality + Risk
        ↓
Score composite (z-score pondéré)
        ↓
Sélection top 15-20 titres
        ↓
Sizing equal-weight + tilt (±20%)
        ↓
Application contraintes
        ↓
Portefeuille final
```

### 4.2 Contraintes

| Contrainte | Limite | Enforcement |
|------------|--------|-------------|
| Nombre de positions | 15-20 | Hard |
| Poids max par ligne | 10% | Hard |
| Poids min par ligne | 3% | Hard |
| Poids max par secteur | 30% | Hard |
| Nombre min de secteurs | 4 | Hard |
| Score minimum | 0.40 | Hard |

### 4.3 Règles de Concentration

| Métrique | Limite |
|----------|--------|
| Top 1 position | ≤ 10% |
| Top 5 positions | ≤ 40% |
| Top 10 positions | ≤ 70% |

### 4.4 Sizing

- **Base** : Equal-weight (1/N)
- **Tilt** : ±20% selon score relatif
- **Résultat typique** : 4-6% pour la plupart des lignes

---

## 5. Rebalancing

### 5.1 Fréquence

| Paramètre | Valeur |
|-----------|--------|
| Fréquence | Trimestrielle |
| Dates | Début Q1, Q2, Q3, Q4 |
| Exécution | J+1 (prix de clôture) |

### 5.2 Turnover

| Paramètre | Limite |
|-----------|--------|
| Turnover max annuel | 100% |
| No-trade zone | < 1% du portefeuille |
| Coût estimé | 12 bps par trade |

### 5.3 Règles de Stabilité

Pour limiter le trading inutile :
- Pas de trade si ajustement < 1% du portefeuille
- Préférence pour les ajustements lors des rebalancing programmés
- Pas de trading intra-trimestre sauf corporate action majeure

---

## 6. Gestion du Risque

### 6.1 Métriques Surveillées

| Métrique | Cible | Warning | Limite Hard |
|----------|-------|---------|-------------|
| Max Drawdown | -25% | -20% | -35% |
| Beta vs SPY | 0.90-1.10 | Surveillé | Non contrôlé |
| Tracking Error | 8-12% | Surveillé | Non contrôlé |

### 6.2 Contrôle du Beta

> **Important** : Le beta est **surveillé ex-post**, pas **contrôlé ex-ante**.

Nous n'avons pas les outils pour un contrôle de beta formel. Le beta résultant est une conséquence des contraintes sectorielles et de la sélection Quality/Value.

### 6.3 Actions en Cas de Drawdown

| Seuil | Action |
|-------|--------|
| DD > -10% | Monitoring renforcé |
| DD > -20% | Gel des modifications modèle |
| DD > -30% | Review complète avant toute action |
| DD > -35% | Escalation, possible arrêt |

---

## 7. Rôle dans le Portefeuille Global

### 7.1 Positionnement

SmartMoney v2.5 est conçu comme une **poche satellite** dans une allocation diversifiée :

```
Portefeuille Global
├── Core (70-80%)
│   └── ETF diversifiés (SPY, VTI, etc.)
└── Satellite (20-30%)
    └── SmartMoney v2.5 ← ICI
```

### 7.2 Allocation Recommandée

| Type d'investisseur | Allocation SmartMoney |
|---------------------|----------------------|
| Prudent | 5-10% |
| Modéré | 10-20% |
| Dynamique | 20-30% |

### 7.3 Complémentarité

SmartMoney v2.5 apporte :
- Tilt Quality/Value vs marché
- Concentration (15-20 lignes vs 500)
- Sélection active vs passive

---

## 8. Gouvernance

### 8.1 Politique de Changement

| Type | Fréquence max | Délai |
|------|---------------|-------|
| Pondérations facteurs | 1x/an | 30 jours |
| Contraintes | 1x/an | 30 jours |
| Hard filters | 2x/an | 7 jours |
| Bug fixes | Immédiat | Documenté |

### 8.2 Période de Gel

Le modèle v2.5 est **figé** pour le forward test (12-24 mois).

Modifications autorisées :
- Bug fixes techniques (documentés)
- Mise à jour sources de données (si indisponibilité)

Modifications interdites :
- Changement de pondérations
- Ajout/suppression de facteurs
- Modification des contraintes

---

## 9. Limitations et Risques

### 9.1 Limitations Connues

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Pas de backtest historique | Performance inconnue | Forward test 12-24 mois |
| Quality sector-relative non implémenté | Biais sectoriels possibles | Roadmap v2.6 |
| Margin of Safety simpliste | Value pas "Buffett-like" | Roadmap v2.6 |
| Beta non contrôlé | Dérive possible | Monitoring ex-post |

### 9.2 Risques Principaux

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Sous-performance prolongée | Moyenne | Élevé | Forward test, patience |
| Concentration excessive | Faible | Moyen | Contraintes hard |
| Biais sectoriel | Moyenne | Moyen | Cap 30% secteur |
| Drawdown majeur | Faible | Élevé | Limites DD, escalation |

---

## 10. Roadmap Future

### v2.6 — "Buffettisation" (Planifié)

| Amélioration | Description |
|--------------|-------------|
| Quality sector-relative | ROE, marges comparés aux pairs du secteur |
| Stabilité 5-10 ans | Pénaliser la volatilité des métriques |
| Margin of Safety | P/E vs historique propre |
| Buffett Score v2 | Score séparé intégrant ces améliorations |

### Prérequis pour v2.6

- 6+ mois de forward test v2.5
- Données historiques 5-10 ans (fondamentaux)
- Validation de la méthodologie sector-relative

---

## 11. Conclusion

### Ce que nous demandons

> "Autorisation de lancer un programme de forward test sur 12-24 mois, avec éventuellement un petit capital prop. Pas d'argent client tant qu'on n'a pas de vécu réel."

### Ce que nous proposons

- Un moteur **théoriquement fondé** (Value/Quality/Risk)
- Un process **techniquement propre** (contraintes enforced)
- Une **transparence totale** (pas de backtest bidon)
- Un plan de **validation empirique** (forward test)

### Message clé

> "v2.5 est notre noyau institutionnel propre. Simple, défendable, auditable. Les améliorations 'Buffett-like' viendront en v2.6 après validation empirique."

---

*Document préparé pour Investment Committee — Décembre 2025*
