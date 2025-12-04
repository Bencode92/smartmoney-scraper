# SmartMoney v2.4 — Investment Memo (Version Révisée)

**Classification:** Confidentiel  
**Version:** 2.4.1-revised  
**Date:** Décembre 2025  
**Statut:** Projet de recherche avancé — NON INVESTISSABLE en l'état

---

## ⚠️ AVERTISSEMENT PRÉLIMINAIRE

> **Ce document décrit un projet de recherche quantitative.**
> 
> SmartMoney v2.4 n'est PAS un produit institutionnel prêt pour mandat client.
> Il peut servir de base pour :
> - Un test prop limité (250-500K€)
> - Un moteur de screening pour gérants fondamentaux
> - Une brique de recherche à industrialiser
>
> **Ce qu'il manque pour être "produit" :**
> - Backtest OOS formel publié
> - Data vendors institutionnels
> - Gouvernance modèle formalisée
> - Attribution factorielle prouvée

---

## 1. Positionnement — Version Honnête

### Ce que SmartMoney EST

> **Un moteur systématique discipliné de stock-picking Quality/Value**, qui fonctionne comme un filtre quant pour identifier 15-20 idées que les fondamentaux valident.
>
> Le facteur Smart Money est un **overlay expérimental** dont l'apport d'alpha n'est pas encore formellement prouvé.

### Ce que SmartMoney N'EST PAS

- ❌ Un produit core
- ❌ Une stratégie de protection
- ❌ Un hedge en bear market
- ❌ Un edge différenciant à l'échelle institutionnelle

### Caractéristiques

| Aspect | Valeur | Commentaire |
|--------|--------|-------------|
| **Univers** | S&P 500 | Large Cap US uniquement |
| **Style** | Quality/Value | Smart Money = overlay expérimental |
| **Positions** | 15-20 | Concentré |
| **Capacité** | 5-10 M$ max | Non scalable |
| **Rôle** | Satellite / Screening | Jamais core |

---

## 2. Edge — Version Réaliste

### Ce que je prétends (et ce que je ne prétends pas)

**Edge principal (modeste) :**
- Framework Quality/Value discipliné et codé
- Rebalancing systématique sans émotion
- Contraintes de risque enforced

**Ce que je NE prétends PAS :**
- Que le facteur Smart Money apporte de l'alpha prouvé
- Que j'ai un edge sur les gros quant shops
- Que la stratégie surperforme dans tous les régimes

### Pourquoi l'edge 13F est probablement faible

| Argument contre | Réalité |
|-----------------|---------|
| Données publiques depuis 20 ans | Oui, largement arbitragé |
| Délai 45 jours | Signal dégradé |
| Tous les quants l'ont trituré | Oui |
| Capacité ridicule | 5-10M$ = pas intéressant pour les gros |

**Conclusion honnête :** L'edge Smart Money est **présumé faible ou nul** jusqu'à preuve du contraire via backtest OOS.

---

## 3. Drawdown — Version Cohérente

### ⚠️ CORRECTION MAJEURE vs Version Précédente

La version précédente contenait une **incohérence frontale** :
- Objectif DD : -30%
- Scénario 2008 : -45% à -55%

**Version corrigée :**

| Régime | Drawdown attendu | Commentaire |
|--------|------------------|-------------|
| **Correction normale** (2011, 2015, 2018) | -15% à -25% | Acceptable |
| **Bear market** (2022) | -25% à -35% | Douloureux mais normal |
| **Crise systémique** (2008, COVID sans rebond) | **-45% à -55%** | Plausible et assumé |

### Ce que ça implique

> **SmartMoney est une stratégie long-only concentrée.**
> 
> En crise systémique type 2008, un drawdown de -50% est **parfaitement plausible**.
> 
> Ce n'est PAS un produit de protection.
> Ce n'est PAS un hedge.
> C'est une poche satellite qui suit le marché avec un léger tilt Quality/Value.

### Seuils de gestion

| Niveau DD | Interprétation | Action |
|-----------|----------------|--------|
| -20% | Normal en bear | Rien |
| -30% | Sévère mais cohérent | Review |
| -40% | Limite haute du "normal" | Réduction 50% |
| -50% | Crise systémique | Évaluation arrêt |
| > -55% | Modèle potentiellement cassé | Arrêt |

---

## 4. Smart Money — Statut Expérimental

### Position actuelle (à revoir)

| Version | Poids Smart Money | Justification |
|---------|-------------------|---------------|
| v2.2 | 45% | Trop élevé, non justifié |
| v2.3/v2.4 | 15% | Réduit par prudence |
| **Recommandé** | **5% ou 0%** | Jusqu'à preuve d'alpha |

### Ce qui manque pour valider Smart Money

1. **Attribution factorielle** : Performance Core vs Core+SM
2. **Walk-forward OOS** : 2015-2024 avec paramètres figés
3. **Score de crowding** : Non implémenté
4. **Source institutionnelle** : Dépendance scraping

### Recommandation

> **Réduire Smart Money à 5% ou 0%** tant que l'attribution n'est pas prouvée.
>
> Vendre le système comme un **moteur Quality/Value discipliné**, pas comme une stratégie "Smart Money".

---

## 5. Backtest — État des Lieux

### Ce qui existe

| Élément | Statut |
|---------|--------|
| Code walk-forward | ✅ Implémenté (v2.4) |
| Paramètres figés | ✅ Documentés |
| Exécution OOS | ❌ **NON FAIT** |
| Attribution factorielle | ❌ **NON FAIT** |
| Survivorship bias | ❌ **NON CORRIGÉ** |

### Ce qui est requis AVANT tout investissement

1. **Walk-forward 2015-2024** avec paramètres figés au 31/12/2014
2. **Comparaison 2 versions** : Core vs Core+SmartMoney
3. **Publication du résultat** quel qu'il soit

### Engagement

> Je m'engage à publier les résultats du backtest OOS même s'ils sont mauvais.
> Si l'alpha est négatif ou le Sharpe < 0.3, je le dirai.

---

## 6. Scénarios de Performance

### Environnements favorables

| Régime | Performance relative attendue |
|--------|------------------------------|
| Rotation Value | +5% à +10% |
| Marché en range | +2% à +5% |
| Récession légère | +2% à +5% (Quality) |

### Environnements défavorables

| Régime | Performance relative attendue | Exemple historique |
|--------|------------------------------|-------------------|
| Rally Growth pur | **-10% à -15%** | 2020-2021 |
| Bull momentum | **-5% à -10%** | 2017 |
| Crise systémique | **Neutre** (beta ~1) | 2008, Mars 2020 |

### Worst case assumé

> **Sous-performance vs SPY sur 3 ans : -15% relatif**
>
> Scénario : Rally Growth prolongé type 2019-2021.
> C'est le risque principal d'une stratégie Quality/Value.

---

## 7. Usage Recommandé

### Pour qui

| ✅ Adapté | ❌ Non adapté |
|-----------|---------------|
| Horizon ≥ 5 ans | Horizon < 3 ans |
| Accepte -50% DD en crise | Besoin de protection |
| Accepte -15% relatif sur 3 ans | Doit battre SPY chaque année |
| Veut un moteur de screening | Veut un produit "fire and forget" |

### Allocation

```
MAXIMUM RECOMMANDÉ : 10-15% du portefeuille

Raison :
- Concentré (15-20 positions)
- DD potentiel -50%
- Sous-perf possible -15% sur 3 ans
- Pas de protection

→ Poche satellite uniquement
```

### Ce que je ferais personnellement

| Phase | Allocation | Condition |
|-------|------------|-----------|
| Actuelle | 15% patrimoine | En attente OOS |
| Post-OOS positif | 25% patrimoine | Si alpha > 0 |
| Post-OOS négatif | 0-5% | Comme screener uniquement |

---

## 8. Gouvernance & Discipline

### Règles figées

| Aspect | Règle |
|--------|-------|
| Modification pondérations | Annuel max, documenté |
| Période sans toucher | 12-18 mois minimum |
| Modification post-DD | INTERDIT pendant 30 jours |

### Triggers d'arrêt

| Trigger | Action |
|---------|--------|
| DD > -40% | Réduction 50% |
| Underperf > -15% sur 12M | Review formel |
| 4 trimestres négatifs consécutifs | Arrêt et analyse |
| DD > -50% | Arrêt stratégie |

---

## 9. Plan 24 Mois

### Phase 1 : Validation (M1-M6)

| Mois | Action | Livrable |
|------|--------|----------|
| M1-M2 | Walk-forward OOS 2015-2024 | Rapport publié |
| M2-M3 | Attribution Core vs Core+SM | Décision poids SM |
| M4-M6 | Paper trading | Tracking vs modèle |

### Phase 2 : Test Prop (M7-M12)

| Condition | Action |
|-----------|--------|
| Si OOS positif (alpha > 0) | Test live 250-500K€ |
| Si OOS négatif | Arrêt ou refonte |

### Phase 3 : Décision (M13-M24)

| Résultat | Action |
|----------|--------|
| Sharpe > 0.4, Alpha > 100 bps | Scale à 1-2M€ |
| Sharpe 0.3-0.4, Alpha 0-100 bps | Maintien comme screener |
| Sharpe < 0.3 ou Alpha < 0 | Arrêt |

---

## 10. Conclusion Honnête

### Ce que SmartMoney v2.4 est aujourd'hui

> Un **projet de recherche avancé** au niveau d'un POC quant.
>
> Suffisant pour :
> - Test prop 250-500K€
> - Moteur de screening
> - Base de développement
>
> Insuffisant pour :
> - Mandat client
> - Produit institutionnel
> - Allocation significative

### Pourquoi vous pourriez quand même être intéressé

1. Framework Quality/Value codé et testé
2. Contraintes de risque enforced (v2.4)
3. Approche honnête et documentée
4. Potentiel comme brique de recherche

### Pourquoi vous devriez probablement acheter un ETF à la place

> Si votre objectif est une exposition Quality/Value Large Cap US :
>
> **Achetez QUAL + IVE.**
>
> Moins cher, plus scalable, track record vérifié.
>
> SmartMoney n'a de sens que si vous voulez un moteur propriétaire ou une brique de recherche interne.

---

**Document préparé pour Investment Committee**

*Ce memo décrit un projet de recherche, pas un produit d'investissement.*

---

**Version:** 2.4.1-revised  
**Changements vs v2.4.0:**
- Correction incohérence DD (-30% → -50% assumé en crise)
- Smart Money reclassé comme "expérimental"
- Backtest OOS identifié comme bloquant
- Positionnement revu (recherche, pas produit)
