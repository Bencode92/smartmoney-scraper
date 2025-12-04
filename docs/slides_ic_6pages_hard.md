# SmartMoney v2.4 — Deck IC (Version Dure)

*6 slides pour comité qui ne pardonne pas*

---

## Slide 1: Ce que c'est (et ce que ce n'est pas)

### SmartMoney v2.4

**EST :**
> Un moteur systématique de stock-picking Quality/Value
> avec overlay Smart Money **expérimental**

**N'EST PAS :**
- ❌ Un produit institutionnel prêt
- ❌ Une stratégie de protection
- ❌ Un edge différenciant à grande échelle
- ❌ Un remplacement d'ETF Quality/Value

**Statut actuel :** Projet de recherche avancé

---

## Slide 2: Ce que je promets (et ce que je ne promets pas)

### Promesses

| Métrique | Cible | Acceptable | Échec |
|----------|-------|------------|-------|
| Alpha | +100-200 bps/an | +50 bps | < 0 |
| Tracking Error | 10% | 8-15% | > 15% |
| Max DD (normal) | -30% | -35% | -40% |
| **Max DD (crise)** | **-50%** | **-55%** | **> -55%** |

### Ce que je NE promets PAS

- Protection en bear market (β ≈ 1)
- Surperformance chaque année
- Edge Smart Money prouvé

**Worst case assumé : -15% relatif vs SPY sur 3 ans**

---

## Slide 3: Facteurs et faiblesses

### Pondération actuelle

| Facteur | Poids | Statut |
|---------|-------|--------|
| Value | 30% | ✅ Discriminant (v2.4) |
| Quality | 25% | ✅ Standard |
| Risk | 15% | ✅ Fonctionnel |
| **Smart Money** | **15%** | ⚠️ **Non prouvé** |
| Insider | 10% | ✅ Signal propre |
| Momentum | 5% | ⚠️ Faible discrimination |

### Problème Smart Money

> **15% du score pour un facteur sans attribution prouvée**
>
> Recommandation : Réduire à 5% ou 0% jusqu'à preuve OOS

---

## Slide 4: Ce qui manque (bloquant)

### ❌ Non fait

| Élément | Statut | Impact |
|---------|--------|--------|
| Walk-forward OOS | ❌ | **BLOQUANT** |
| Attribution Core vs Core+SM | ❌ | **BLOQUANT** |
| Survivorship bias | ❌ | Biais estimé +50-100 bps |
| Coûts de transaction | ❌ | -30 bps/an estimé |
| Source institutionnelle | ❌ | Risque opérationnel |

### ✅ Fait

| Élément | Commit |
|---------|--------|
| Contraintes enforced | `80adc50` |
| Tests unitaires | `1100230` |
| Value cross-sectionnel | `7ebe7df` |
| Code walk-forward | `412d062` |

---

## Slide 5: Scénarios de stress

### Performance par régime

| Scénario | Impact relatif | Exemple |
|----------|---------------|----------|
| Rally Growth | **-10% à -15%** | 2020-2021 |
| Bull momentum | -5% à -10% | 2017 |
| Rotation Value | +5% à +10% | 2022 H2 |
| Crise systémique | **DD -50%** | 2008 |

### Questions à me poser

1. *"Si 2020-2021 se répète, tu perds -15% relatif. Tu fais quoi ?"*
   → Rien. C'est le risque assumé d'un tilt Value.

2. *"En 2008, tu perds -50%. Pourquoi ne pas hedger ?"*
   → Long-only by design. Ce n'est pas un produit de protection.

---

## Slide 6: Recommandation

### Pour vous (Asset Manager)

| Option | Recommandation |
|--------|----------------|
| Mandat client | ❌ **NON** |
| Test prop 250-500K | ✅ Si OOS positif |
| Moteur de screening | ✅ Immédiatement |
| ETF Quality/Value | ✅ **Meilleur choix si juste expo Q/V** |

### Pour moi (plan 6 mois)

| Mois | Action | Délivrable |
|------|--------|------------|
| M1-M2 | Walk-forward OOS | Rapport publié |
| M2-M3 | Attribution SM | Décision poids |
| M4-M6 | Paper trading | Tracking |

### Phrase de conclusion

> *"Je ne mettrais pas l'argent des clients dedans aujourd'hui.*
> *Mais je suis prêt à faire le travail pour y arriver.*
> *Dans 6 mois, je reviens avec les preuves ou j'arrête."*

---

**Fin du deck**

*Version dure pour comité exigeant*
