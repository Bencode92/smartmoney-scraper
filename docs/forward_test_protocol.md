# SmartMoney v2.4 — Protocole de Forward Test

**Date de création:** Décembre 2025  
**Durée prévue:** 12-24 mois  
**Responsable:** [Nom]

---

## 1. Objectif

Construire un **historique observé réel** de la stratégie SmartMoney v2.4, sans biais de backtesting.

### Pourquoi un Forward Test ?

| Méthode | Avantages | Inconvénients |
|---------|-----------|---------------|
| **Backtest** | Rapide, beaucoup de données | Biais (look-ahead, survivorship, overfitting) |
| **Forward Test** | Pas de biais, réalité du marché | Lent (12-24 mois minimum) |

> Nous choisissons le forward test car nous n'avons pas les données historiques nécessaires pour un backtest rigoureux.

---

## 2. Paramètres Figés

### 2.1 Modèle

| Paramètre | Valeur | Modifiable ? |
|-----------|--------|-------------|
| Version | v2.4 | ❌ Non |
| Pondérations | smart_money: 15%, value: 30%, quality: 25%, risk: 15%, insider: 10%, momentum: 5% | ❌ Non |
| Contraintes | max_weight: 12%, max_sector: 30%, positions: 15-20 | ❌ Non |
| Univers | S&P 500 | ❌ Non |

### 2.2 Rebalancing

| Paramètre | Valeur |
|-----------|--------|
| Fréquence | **Trimestrielle** (début Q) |
| Dates | 1er janvier, 1er avril, 1er juillet, 1er octobre |
| Exécution | J+1 (prix de clôture) |

### 2.3 Benchmark

| Benchmark | Ticker | Raison |
|-----------|--------|--------|
| Principal | SPY | Marché US large cap |
| Secondaire | QUAL | ETF Quality (iShares) |
| Secondaire | IVE | ETF Value (iShares) |

---

## 3. Processus à Chaque Rebalancing

### Checklist J-1 (veille du rebalancing)

- [ ] Exécuter le pipeline complet : `python main.py`
- [ ] Vérifier les contraintes : `pytest tests/test_constraints.py`
- [ ] Générer le portefeuille : `outputs/YYYY-MM-DD/portfolio.json`
- [ ] Archiver le log complet

### Checklist J (jour du rebalancing)

- [ ] Enregistrer les prix de clôture J-1 pour chaque position
- [ ] Calculer les poids effectifs après rebalancing
- [ ] Logger dans `forward_test_log.json`

### Checklist J+1 à J+90 (période de holding)

- [ ] Ne PAS modifier le modèle
- [ ] Ne PAS rebalancer (sauf corporate action majeure)
- [ ] Tracker la valeur quotidienne du portefeuille

---

## 4. Enregistrement des Données

### 4.1 Format du Log

```json
{
  "rebalancing_date": "2026-01-02",
  "model_version": "v2.4",
  "portfolio": [
    {
      "symbol": "AAPL",
      "weight": 0.08,
      "entry_price": 185.50,
      "score_composite": 0.72,
      "score_value": 0.65,
      "score_quality": 0.78,
      "sector": "Technology"
    }
  ],
  "constraints_check": {
    "max_weight_ok": true,
    "max_sector_ok": true,
    "n_positions": 18
  },
  "benchmark_prices": {
    "SPY": 480.25,
    "QUAL": 152.30,
    "IVE": 175.80
  }
}
```

### 4.2 Fichiers à Conserver

```
forward_test/
├── 2026-Q1/
│   ├── portfolio_20260102.json      # Portefeuille généré
│   ├── prices_entry.csv             # Prix d'entrée
│   ├── prices_exit.csv              # Prix de sortie (fin Q)
│   ├── performance_Q1.json          # Métriques de la période
│   └── log_generation.txt           # Log du pipeline
├── 2026-Q2/
│   └── ...
└── summary.json                     # Résumé cumulé
```

---

## 5. Métriques à Calculer

### 5.1 Par Période (Trimestrielle)

| Métrique | Formule |
|----------|--------|
| Return Portefeuille | (NAV_fin - NAV_début) / NAV_début |
| Return SPY | (SPY_fin - SPY_début) / SPY_début |
| Alpha | Return_PF - Return_SPY |
| Hit Rate | 1 si Alpha > 0, 0 sinon |

### 5.2 Cumulées (Depuis le début)

| Métrique | Calcul |
|----------|--------|
| Return Total | ∏(1 + R_i) - 1 |
| CAGR | (1 + Return_Total)^(1/années) - 1 |
| Alpha Cumulé | Σ Alpha_i |
| Hit Rate | % périodes avec Alpha > 0 |
| Max Drawdown | Max peak-to-trough |
| Sharpe | (CAGR - Rf) / Vol |
| Information Ratio | Alpha_annualisé / Tracking_Error |

---

## 6. Règles de Modification

### 6.1 Modifications INTERDITES

- ❌ Changer les pondérations des facteurs
- ❌ Ajouter/supprimer des facteurs
- ❌ Modifier les seuils de scoring
- ❌ Changer les contraintes (sauf bug)
- ❌ Modifier l'univers

### 6.2 Modifications AUTORISÉES

- ✅ Bug fixes techniques (avec documentation)
- ✅ Amélioration logging/monitoring
- ✅ Mise à jour des sources de données (si indisponibilité)

### 6.3 Procédure de Bug Fix

1. Documenter le bug
2. Corriger avec commit séparé
3. Re-tester les contraintes
4. Logger l'impact potentiel
5. **Ne PAS recalculer les périodes passées**

---

## 7. Critères de Succès

### 7.1 Après 12 Mois (4 trimestres)

| Métrique | Seuil "Encourangeant" | Seuil "Échec" |
|----------|----------------------|---------------|
| Alpha cumulé | > 0% | < -5% |
| Hit Rate | > 50% | < 35% |
| Max DD relatif | < -10% vs SPY | > -15% vs SPY |

### 7.2 Après 24 Mois (8 trimestres)

| Métrique | Seuil "Valide" | Seuil "Échec" |
|----------|----------------|---------------|
| Alpha/an | > +1% | < 0% |
| Hit Rate | > 50% | < 40% |
| Information Ratio | > 0.3 | < 0 |
| Comportement vs attentes | Cohérent | Surprises négatives répétées |

---

## 8. Reporting

### 8.1 Fréquence

| Type | Fréquence | Destinataires |
|------|-----------|---------------|
| Log technique | Chaque rebalancing | Interne |
| Rapport trimestriel | Fin de trimestre | IC si applicable |
| Bilan annuel | Année glissante | IC + parties prenantes |

### 8.2 Contenu du Rapport Trimestriel

1. Performance vs benchmarks
2. Attribution par secteur
3. Principales contributions (+/-)
4. Respect des contraintes
5. Événements notables
6. Comparaison aux attentes

---

## 9. Arrêt Anticipé

### Triggers d'arrêt

| Condition | Action |
|-----------|--------|
| DD > -40% absolu | Revue complète, possible arrêt |
| Alpha < -10% sur 12 mois | Revue complète |
| Bug critique non corrigeable | Arrêt immédiat |
| Source de données indisponible | Pause ou arrêt |

### Procédure d'arrêt

1. Documenter la raison
2. Calculer les métriques finales
3. Archiver tous les logs
4. Rédiger un post-mortem

---

## 10. Engagement

> **Je m'engage à :**
>
> 1. Exécuter ce protocole sans modification pendant 12 mois minimum
> 2. Ne pas "cherry-pick" les résultats
> 3. Publier les résultats même s'ils sont décevants
> 4. Ne pas modifier le modèle en cours de test
> 5. Documenter tous les incidents

**Signature:** _________________ **Date:** _________________

---

## Annexe : Calendrier 2026

| Trimestre | Date Rebalancing | Date Limite Log |
|-----------|------------------|------------------|
| Q1 2026 | 2 janvier 2026 | 3 janvier 2026 |
| Q2 2026 | 1 avril 2026 | 2 avril 2026 |
| Q3 2026 | 1 juillet 2026 | 2 juillet 2026 |
| Q4 2026 | 1 octobre 2026 | 2 octobre 2026 |
| Q1 2027 | 2 janvier 2027 | 3 janvier 2027 |

---

*Protocole créé pour SmartMoney Engine v2.4*
