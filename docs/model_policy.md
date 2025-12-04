# SmartMoney v2.4 — Model Policy

**Document de gouvernance du modèle**  
**Version:** 1.0  
**Date:** Décembre 2025  
**Statut:** En vigueur

---

## 1. Objectif

Ce document définit les règles de gouvernance du modèle SmartMoney v2.4 :
- Ce qui peut être modifié
- Qui peut le modifier
- Quand et comment
- Comment les changements sont documentés

---

## 2. Classification des Changements

### 2.1 Changements Majeurs (Classe A)

**Définition :** Modification de la logique fondamentale du modèle.

| Type | Exemples |
|------|----------|
| Pondérations facteurs | Value 30% → 25% |
| Ajout/suppression facteur | Retirer Smart Money |
| Formule de scoring | Changer le calcul Quality |
| Contraintes structurelles | Max position 12% → 10% |

**Règles :**
- Fréquence : **1x par an maximum**
- Délai : 30 jours avant implémentation
- Validation : Documentation complète + backtest avant/après
- Interdit : Après un drawdown (attendre 60 jours)

### 2.2 Changements Mineurs (Classe B)

**Définition :** Ajustements de paramètres sans changer la logique.

| Type | Exemples |
|------|----------|
| Filtres univers | MCAP min $5B → $10B |
| Seuils de scoring | FCF Yield threshold |
| Paramètres techniques | Nombre de positions 15-20 → 12-18 |

**Règles :**
- Fréquence : **2x par an maximum**
- Délai : 7 jours avant implémentation
- Validation : Justification écrite
- Interdit : Après un drawdown (attendre 30 jours)

### 2.3 Bug Fixes (Classe C)

**Définition :** Correction d'erreurs techniques.

| Type | Exemples |
|------|----------|
| Bug de code | Contrainte non appliquée |
| Erreur de données | Champ mal mappé |
| Problème de calcul | Division par zéro |

**Règles :**
- Fréquence : **Immédiat**
- Délai : 0 (urgence)
- Validation : Test unitaire obligatoire
- Documentation : Post-mortem sous 48h

### 2.4 Changements de Données (Classe D)

**Définition :** Modification des sources de données.

| Type | Exemples |
|------|----------|
| Changement de vendor | HedgeFollow → WhaleWisdom |
| Ajout de source | Nouvelle source insiders |
| Modification API | Changement de champs |

**Règles :**
- Fréquence : **Selon besoin**
- Délai : 14 jours de validation
- Validation : Comparaison ancienne vs nouvelle source
- Documentation : Impact assessment

---

## 3. Période de Gel (Freeze Period)

### 3.1 Après un Drawdown

| Drawdown | Période de gel |
|----------|----------------|
| > -10% | 30 jours |
| > -20% | 60 jours |
| > -30% | 90 jours |

**Pendant le gel :**
- ❌ Aucune modification Classe A ou B
- ✅ Bug fixes autorisés
- ✅ Analyse et documentation autorisées

### 3.2 Après une Surperformance

| Surperformance 12M | Période de gel |
|--------------------|----------------|
| > +10% | 30 jours |

**Raison :** Éviter le curve-fitting opportuniste après une bonne période.

---

## 4. Processus de Validation

### 4.1 Changement Classe A

```
1. Rédaction de la proposition
   - Justification économique (pas juste "perf récente")
   - Impact attendu
   - Risques

2. Backtest avant/après
   - Walk-forward sur 5 ans minimum
   - Métriques : Alpha, Sharpe, Max DD

3. Review
   - Par une personne tierce (même informelle)
   - Délai : 7 jours

4. Décision
   - Go / No-Go
   - Si Go : date d'implémentation

5. Implémentation
   - Commit avec tag version
   - Mise à jour CHANGELOG

6. Monitoring
   - 30 jours de suivi renforcé
```

### 4.2 Changement Classe C (Bug Fix)

```
1. Détection et documentation du bug
2. Correction avec test unitaire
3. Déploiement immédiat
4. Post-mortem sous 48h
   - Cause
   - Impact
   - Prévention future
```

---

## 5. Documentation Obligatoire

### 5.1 Change Log

Chaque modification doit être enregistrée dans `CHANGELOG.md` :

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Changed
- Description du changement
- Raison (NON liée à la performance récente)
- Impact attendu

### Classe
- A / B / C / D

### Validation
- Backtest : Oui/Non
- Review : Nom du reviewer
```

### 5.2 Version Tagging

| Type de changement | Incrément version |
|--------------------|-------------------|
| Classe A | Major (2.4 → 2.5) |
| Classe B | Minor (2.4.0 → 2.4.1) |
| Classe C | Patch (2.4.0 → 2.4.0.1) |
| Classe D | Minor |

---

## 6. Triggers de Risk Management

### 6.1 Triggers Automatiques

| Trigger | Action | Qui décide |
|---------|--------|------------|
| DD > -25% | Review positions | Gérant |
| DD > -35% | Réduction 50% | Comité |
| DD > -40% | Arrêt stratégie | CIO |
| Underperf > -15% sur 12M | Review formel | Comité |
| 4 trimestres négatifs | Arrêt et analyse | CIO |

### 6.2 Triggers de Gouvernance

| Trigger | Action |
|---------|--------|
| Source data indisponible > 7j | Désactiver le facteur |
| Anomalie de données détectée | Freeze + investigation |
| Bug de contrainte détecté | Correction immédiate |

---

## 7. Rôles et Responsabilités

### 7.1 Actuellement (Projet Personnel)

| Rôle | Personne | Responsabilité |
|------|----------|----------------|
| Model Owner | Moi | Tout |
| Reviewer | Auto-review | Validation |

### 7.2 Futur (Si Institutionnalisé)

| Rôle | Responsabilité |
|------|----------------|
| Model Owner | Développement, documentation |
| Model Reviewer | Validation changements |
| Risk Officer | Monitoring, triggers |
| CIO | Décisions arrêt/continuation |

---

## 8. Audit et Compliance

### 8.1 Audit Périodique

| Fréquence | Scope |
|-----------|-------|
| Mensuel | Vérification contraintes respectées |
| Trimestriel | Review performance vs attentes |
| Annuel | Audit complet du modèle |

### 8.2 Documentation à Conserver

- Tous les backtests
- Tous les change logs
- Toutes les décisions de modification
- Post-mortems des bugs

---

## 9. Exceptions

### 9.1 Cas où le gel peut être levé

1. **Changement structurel de marché** documenté
   - Exemple : Changement de régime de la Fed
   - Doit être justifié indépendamment de la performance

2. **Bug critique**
   - Impact matériel sur le portefeuille
   - Correction immédiate requise

3. **Disparition de source de données**
   - Activation du plan B

### 9.2 Cas où le gel ne peut PAS être levé

- "Le modèle sous-performe, il faut changer les poids"
- "Je pense que Value va mieux marcher maintenant"
- "Les hedge funds ne sont plus pertinents"

**Ces justifications sont INTERDITES** car elles sont du curve-fitting déguisé.

---

## 10. Engagement

> **Je m'engage à respecter cette politique de gouvernance.**
>
> Toute déviation sera documentée et justifiée.
>
> Si je ne respecte pas ces règles, je ne mérite pas la confiance d'un investisseur.

---

**Signé :** Model Owner  
**Date :** Décembre 2025  
**Version :** 1.0
