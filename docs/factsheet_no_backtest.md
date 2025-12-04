# SmartMoney v2.4 — Factsheet (Sans Backtest)

**Date:** Décembre 2025  
**Version:** 2.4  
**Statut:** POC / Forward Test

---

## ⚠️ Avertissement Préliminaire

> **Ce document ne contient PAS de track record historique.**
>
> Les conditions pour un backtest rigoureux ne sont pas réunies (absence de données fondamentales et 13F historiques). Plutôt que de présenter des chiffres artificiels, nous choisissons la transparence.
>
> SmartMoney est positionné comme :
> - Un moteur d'idées **théoriquement fondé**
> - Une poche **expérimentale**
> - **Pas** un produit avec track record simulé

---

## 1. Philosophie d'Investissement

### Thèse Centrale

SmartMoney est un moteur systématique de stock-picking qui s'appuie sur des **facteurs documentés académiquement** :

| Facteur | Poids v2.4 | Fondement Économique |
|---------|------------|----------------------|
| **Value** | 30% | Prime de risque pour titres décotés (Fama-French 1992) |
| **Quality** | 25% | Avantage compétitif durable, moat (Novy-Marx 2013) |
| **Risk** | 15% | Anomalie low-volatility (Ang et al. 2006) |
| **Insider** | 10% | Signal informationnel des insiders (Seyhun 1986) |
| **Momentum** | 5% | Persistance des tendances (Jegadeesh-Titman 1993) |
| **Smart Money** | 15% | Suivi des positions HF (à valider empiriquement) |

### Ce que nous ne prétendons PAS

- ❌ Avoir découvert un nouveau facteur magique
- ❌ Avoir un edge sur les 13F (délai 45 jours, information publique)
- ❌ Battre systématiquement le marché

### Ce que nous proposons

- ✅ Un framework discipliné et codé
- ✅ Des expositions factorielles explicites
- ✅ Des contraintes de risque enforced
- ✅ Un processus transparent et auditable

---

## 2. Construction du Portefeuille

### 2.1 Univers

| Paramètre | Valeur |
|-----------|--------|
| Univers de base | S&P 500 |
| Market cap minimum | $10 milliards |
| Liquidité minimum | Volume moyen > $10M/jour |
| Exclusions | Financials leverageés, REITs |

### 2.2 Contraintes (Enforced par code)

| Contrainte | Limite | Test Unitaire |
|------------|--------|---------------|
| Positions | 15-20 | ✅ |
| Poids max par ligne | 12% | ✅ |
| Poids max par secteur | 30% | ✅ |
| Score minimum | 0.35 | ✅ |
| Leverage max D/E | 3.0x | ✅ |

### 2.3 Process de Scoring

```
Univers S&P 500 (500 titres)
        ↓
 Filtres d'éligibilité (~400 titres)
        ↓
 Scoring multi-factoriel
   - Value: FCF yield, EV/EBIT, P/E relatif
   - Quality: ROE, ROIC, marges, stabilité
   - Risk: volatilité, drawdown, leverage
   - Insider: achats/ventes Form 4
   - Momentum: RSI, perf 3-12M
   - Smart Money: positions 13F
        ↓
 Score composite (z-score pondéré)
        ↓
 Sélection top 15-20 titres
        ↓
 Application contraintes
        ↓
 Portefeuille final
```

---

## 3. Profil Factoriel Typique

### 3.1 Expositions vs S&P 500

Basé sur le portefeuille actuel (décembre 2025) :

| Facteur | Portefeuille | S&P 500 | Tilt |
|---------|--------------|---------|------|
| P/E médian | ~18x | ~22x | **Value** |
| ROE médian | ~25% | ~18% | **Quality** |
| FCF Yield médian | ~5.5% | ~3.5% | **Value** |
| Beta médian | ~0.95 | 1.00 | Neutre |
| D/E médian | ~0.8x | ~1.2x | **Défensif** |

### 3.2 Expositions Sectorielles Typiques

| Secteur | Fourchette typique | vs S&P 500 |
|---------|-------------------|------------|
| Technology | 20-28% | Sous-pondéré |
| Healthcare | 15-22% | Sur-pondéré |
| Financials | 12-18% | Proche |
| Consumer | 10-15% | Variable |
| Industrials | 8-12% | Proche |

### 3.3 Caractéristiques de Risque

| Métrique | Estimation | Source |
|----------|------------|--------|
| Beta attendu | 0.85 - 1.05 | Historique positions |
| Tracking Error | 8% - 12% | Estimation |
| Corrélation SPY | 0.85 - 0.95 | Estimation |

---

## 4. Scénarios de Stress (Prix seulement)

⚠️ **Note:** Ces estimations sont basées sur le profil factoriel du portefeuille, pas sur un backtest.

### 4.1 Comportement Attendu par Régime

| Régime | SPY | Portefeuille | Différence |
|--------|-----|--------------|------------|
| **Rally Growth** | +20% | +15% à +18% | ⬇️ Sous-performance |
| **Marché Normal** | +10% | +10% à +12% | ↔️ Proche |
| **Correction Value** | -10% | -8% à -10% | ⬆️ Légère surperformance |
| **Bear Market** | -30% | -25% à -30% | ⬆️ Modérément défensif |
| **Crise Systémique** | -50% | -40% à -50% | Variable |

### 4.2 Drawdown Maximum Attendu

| Scénario | DD Estimé |
|----------|------------|
| Correction normale | -15% à -25% |
| Bear market | -25% à -35% |
| Crise type 2008/2020 | **-40% à -50%** |

> **Ce n'est PAS un produit de protection.** En crise systémique, le portefeuille peut perdre autant ou plus que le marché.

---

## 5. Facteur Smart Money : Position Honnête

### Ce qu'est le facteur Smart Money

- Suivi des positions des hedge funds via les filings 13F (SEC)
- Délai de publication : **45 jours après fin de trimestre**
- Information **publique et accessible à tous**

### Pourquoi nous l'incluons

- Signal de "conviction" sur certains titres
- Filtre additionnel (pas un alpha générateur)

### Pourquoi il pourrait ne pas fonctionner

- Délai rend l'information potentiellement obsolète
- Crowding : positions populaires des HF peuvent sous-performer
- Edge présumé faible ou nul sur ce facteur seul

### Notre position

> **Nous n'avons pas prouvé que Smart Money apporte de l'alpha.**
>
> Il est inclus à 15% comme overlay expérimental.
> Si le forward test montre qu'il n'ajoute pas de valeur, nous le réduirons ou le supprimerons.

---

## 6. Gouvernance

### 6.1 Politique de Changement

| Type de changement | Fréquence max | Délai |
|--------------------|---------------|-------|
| Pondérations facteurs | 1x/an | 30 jours |
| Filtres univers | 2x/an | 7 jours |
| Bug fixes | Immédiat | Documenté |

### 6.2 Période de Gel

Après drawdown significatif :
- DD > -10% : Pas de changement pendant 30 jours
- DD > -20% : Pas de changement pendant 60 jours
- DD > -30% : Review complète avant toute modification

---

## 7. Ce qu'il faudrait pour un Vrai Backtest

Pour transformer ce POC en stratégie pleinement backtestée :

| Donnée | Source | Coût estimé |
|--------|--------|-------------|
| Fondamentaux historiques | FactSet, S&P, Bloomberg | $5-15K/an |
| 13F historiques | WhaleWisdom, SEC EDGAR | $1-3K/an |
| Développement pipeline | Interne | 2-4 semaines |

**Tant que ces données ne sont pas disponibles, aucun backtest crédible n'est possible.**

---

## 8. Conclusion

### Ce que SmartMoney est

- Un moteur de stock-picking **théoriquement fondé**
- Un framework **techniquement propre**
- Une stratégie **en phase de validation empirique**

### Ce que SmartMoney n'est pas

- Un produit avec track record
- Une stratégie institutionnelle prête à déployer
- Un générateur d'alpha garanti

### Prochaine étape

**Forward Test structuré sur 12-24 mois** pour construire un historique observé réel.

---

*Document généré par SmartMoney Engine v2.4*
