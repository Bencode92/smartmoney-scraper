# Roadmap v2.6 — "Buffettisation"

**Statut:** Planifié (après validation v2.5)  
**Prérequis:** 6+ mois de forward test v2.5  
**Date cible:** T3-T4 2026

---

## Objectif

Transformer le noyau institutionnel v2.5 en une version plus alignée avec la philosophie Buffett, tout en gardant la discipline factorielle.

---

## 1. Quality v2.6 — Sector-Relative + Stabilité

### 1.1 Problème actuel (v2.5)

- ROE comparé en absolu (10% = 10% partout)
- Un ROE de 10% en Healthcare peut être excellent
- Un ROE de 10% en Tech peut être médiocre
- Pas de prise en compte de la stabilité temporelle

### 1.2 Solution v2.6

```python
# Quality sector-relative
df["roe_sector_rank"] = df.groupby("sector")["roe"].rank(pct=True)
df["margin_sector_rank"] = df.groupby("sector")["operating_margin"].rank(pct=True)

# Stabilité 5 ans
df["roe_5y_avg"] = ...  # Moyenne 5 ans
df["roe_5y_stability"] = 1 / (1 + df["roe_5y_std"])

# Score Quality v2.6
quality_score = (
    0.30 * roe_sector_rank +
    0.25 * margin_sector_rank +
    0.25 * roic_5y_avg_rank +
    0.20 * stability_score
)
```

### 1.3 Composantes Quality v2.6

| Composante | Poids | Description |
|------------|-------|-------------|
| ROE sector rank | 30% | ROE vs pairs du secteur |
| Margin sector rank | 25% | Marge op vs pairs du secteur |
| ROIC 5Y avg | 25% | Rentabilité du capital (moyenne 5 ans) |
| Stability | 20% | Pénalité si volatilité ROE/marges élevée |

### 1.4 Formule de Stabilité

```python
stability_score = 1 / (1 + coefficient_variation_roe_5y)
```

Où `coefficient_variation = std / mean`

---

## 2. Value v2.6 — Cross-Section + Margin of Safety

### 2.1 Problème actuel (v2.5)

- Value purement cross-sectionnelle (cheap vs peers)
- Pas de notion de "discount vs sa propre histoire"
- Pas de vraie Margin of Safety

### 2.2 Solution v2.6

```python
# Value cross-sectionnelle (cheap vs peers)
df["fcf_yield_rank"] = df.groupby("sector")["fcf_yield"].rank(pct=True)
df["ev_ebit_rank"] = 1 - df.groupby("sector")["ev_ebit"].rank(pct=True)

# Margin of Safety (discount vs propre historique)
df["pe_discount"] = (df["pe_10y_avg"] - df["pe_current"]) / df["pe_10y_avg"]
df["fcf_yield_premium"] = (df["fcf_yield_current"] - df["fcf_yield_5y_avg"]) / df["fcf_yield_5y_avg"]

df["mos_score"] = (
    0.50 * norm_cdf(pe_discount) +
    0.50 * norm_cdf(fcf_yield_premium)
)

# Score Value v2.6
value_score = (
    0.60 * value_cross_section +  # Cheap vs peers
    0.40 * mos_score              # Discount vs propre histoire
)
```

### 2.3 Composantes Value v2.6

| Composante | Poids | Description |
|------------|-------|-------------|
| FCF yield sector rank | 25% | FCF yield vs pairs secteur |
| EV/EBIT sector rank | 25% | Multiple vs pairs secteur |
| P/E discount | 25% | P/E actuel vs P/E historique 10 ans |
| FCF yield premium | 25% | FCF yield actuel vs moyenne 5 ans |

### 2.4 Interprétation Margin of Safety

| Situation | Interprétation |
|-----------|----------------|
| P/E actuel < P/E historique | La boîte est moins chère que d'habitude |
| FCF yield actuel > FCF yield historique | Rendement cash meilleur que d'habitude |
| Combinaison des deux | "Great business at a fair price" |

---

## 3. Buffett Score v2.0

### 3.1 Formule

```python
buffett_score_v2 = (
    0.50 * quality_v26 +    # Quality sector-relative + stabilité
    0.35 * value_v26 +      # Cross-section + MoS
    0.15 * risk_score       # Inchangé vs v2.5
)
```

### 3.2 Différence vs Score Composite v2.5

| Aspect | Composite v2.5 | Buffett Score v2.0 |
|--------|----------------|--------------------|
| Quality | Absolu | Sector-relative + stabilité |
| Value | Cross-section | + Margin of Safety |
| Horizon | Court terme | Long terme (5-10 ans) |
| Philosophie | Factoriel | "Owner-operator" |

---

## 4. Données Requises

### 4.1 Pour Quality v2.6

| Donnée | Historique | Source |
|--------|------------|--------|
| ROE annuel | 5-10 ans | Twelve Data / FactSet |
| Operating Margin | 5-10 ans | Twelve Data / FactSet |
| ROIC | 5 ans | Calculé |
| Sector classification | Actuel | GICS |

### 4.2 Pour Value v2.6

| Donnée | Historique | Source |
|--------|------------|--------|
| P/E | 10 ans | Twelve Data / Yahoo |
| FCF Yield | 5 ans | Calculé |
| EV/EBIT | 5 ans | Calculé |

### 4.3 Coût estimé

Si données non disponibles via Twelve Data :
- FactSet : $10-20K/an
- Bloomberg : $20-50K/an
- Alternative (FMP, Polygon) : $1-5K/an

---

## 5. Implémentation Technique

### 5.1 Nouveaux fichiers

```
src/scoring/
├── quality_v26.py          # Quality sector-relative + stabilité
├── value_v26.py            # Value cross-section + MoS
├── buffett_score_v2.py     # Buffett Score v2.0
└── historical_loader.py    # Chargement données historiques
```

### 5.2 Modifications config

```python
# config_v26.py
QUALITY_V26 = {
    "mode": "sector_relative_with_stability",
    "stability_years": 5,
    "components": {
        "roe_sector_rank": 0.30,
        "margin_sector_rank": 0.25,
        "roic_5y_avg_rank": 0.25,
        "stability": 0.20,
    },
}

VALUE_V26 = {
    "mode": "cross_section_with_mos",
    "mos_years": 10,
    "components": {
        "fcf_yield_sector_rank": 0.25,
        "ev_ebit_sector_rank": 0.25,
        "pe_discount": 0.25,
        "fcf_yield_premium": 0.25,
    },
}
```

---

## 6. Critères de Lancement v2.6

### 6.1 Prérequis

| Critère | Seuil | Statut |
|---------|-------|--------|
| Forward test v2.5 | ≥ 6 mois | ⏳ En cours |
| Données historiques 5Y | Disponibles | ⏳ À vérifier |
| Données historiques 10Y (P/E) | Disponibles | ⏳ À vérifier |
| Tests unitaires sector-relative | Passent | ❌ À créer |
| Validation méthodologie | Documentée | ❌ À faire |

### 6.2 Go/No-Go

**Go si :**
- v2.5 forward test pas catastrophique (alpha ≥ -5%)
- Données historiques disponibles sans coût excessif
- Méthodologie sector-relative validée sur exemples

**No-Go si :**
- v2.5 sous-performe significativement (alpha < -10%)
- Coût données > budget disponible
- Méthodologie sector-relative crée des biais non désirés

---

## 7. Ce que Buffett dirait

### Sur v2.5 (actuel)

> "Tu filtres les cochonneries et tu restes sur des grandes caps lisibles. C'est bien. Mais tu es trop obsédé par des scores, pas assez par le business individuel."

### Sur v2.6 (planifié)

> "Mieux. Tu regardes les marges par rapport aux pairs, la stabilité dans le temps, et si le prix est raisonnable par rapport à l'historique. C'est plus proche de ce que je fais."

### Ce qui manquera toujours

> "Tu ne comprends pas vraiment le business. Tu ne lis pas les rapports annuels. Tu ne connais pas le management. C'est du quant, pas de l'investing."

**Réponse honnête :**
> "C'est vrai. v2.6 n'est pas Buffett. C'est un moteur factoriel avec une couche Buffett-inspired dans la définition des facteurs. Le stock picking humain reste irremplaçable."

---

## 8. Timeline

| Phase | Date cible | Livrable |
|-------|------------|----------|
| v2.5 Forward Test | Jan 2026 - Juin 2026 | 6 mois de track record |
| Review v2.5 | Juil 2026 | Analyse performance, décision Go/No-Go |
| Dev v2.6 | Août-Sept 2026 | Code Quality/Value v2.6 |
| Tests v2.6 | Oct 2026 | Validation, tests unitaires |
| Lancement v2.6 | Nov 2026 | Forward test v2.6 |

---

*Roadmap préparée pour évolution SmartMoney Engine — Décembre 2025*
