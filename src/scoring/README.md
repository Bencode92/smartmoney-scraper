# SmartMoney Scoring Module

## Structure Actuelle (v3.0)

```
src/scoring/
├── __init__.py              # Exports v3.0 (défaut) + legacy v2.3
├── README.md                # Ce fichier
│
├── # === v3.0 BUFFETT-QUANT (ACTIF) ===
├── quality_v30.py           # Quality sector-relative + stabilité 5 ans
├── value_v30.py             # Value cross-section + Margin of Safety
├── risk_v30.py              # Risk éviter perte permanente de capital
├── composite_v30.py         # Agrégation 45/35/20
│
├── # === LEGACY v2.3 (⚠️ DEPRECATED) ===
├── quality_composite.py     # ⚠️ Utiliser quality_v30.py
├── value_composite.py       # ⚠️ Utiliser value_v30.py
├── risk_score.py            # ⚠️ Utiliser risk_v30.py
├── composite.py             # ⚠️ Utiliser composite_v30.py
├── crowding_score.py        # ⚠️ Non utilisé en v3.0
│
└── legacy/                  # Wrappers pour rétrocompatibilité
    ├── __init__.py
    ├── value_v23.py
    ├── quality_v23.py
    ├── risk_v23.py
    └── composite_v23.py
```

---

## Usage Recommandé (v3.0)

```python
# Import par défaut → v3.0
from src.scoring import calculate_all_scores

df = calculate_all_scores(df)
# Ajoute: score_quality_v30, score_value_v30, score_risk_v30, score_composite_v30
```

### Scorers individuels

```python
from src.scoring import score_quality_v30, score_value_v30, score_risk_v30

df = score_quality_v30(df)  # Sector-relative + stabilité
df = score_value_v30(df)    # Cross-section + MoS
df = score_risk_v30(df)     # Perte permanente de capital
```

### Classes pour usage avancé

```python
from src.scoring import CompositeScorerV30

scorer = CompositeScorerV30()
df = scorer.calculate(df)
top20 = scorer.get_top_holdings(df, n=20)
```

---

## Différences v2.3 vs v3.0

| Aspect | v2.3 (deprecated) | v3.0 (actif) |
|--------|-------------------|---------------|
| **Quality** | Seuils absolus (ROE > 15%) | Sector-relative + stabilité 5 ans |
| **Value** | Seuils absolus (FCF > 8%) | Cross-section + Margin of Safety |
| **Risk** | Low vol académique | Éviter perte permanente capital |
| **Poids Value** | 30% | 45% |
| **Poids Quality** | 25% | 35% |
| **Poids Risk** | 15% | 20% |
| **Smart Money** | 15% | 0% (indicateur) |
| **Insider** | 10% | 0% (tie-breaker) |
| **Momentum** | 5% | 0% (supprimé) |

---

## Migration depuis v2.3

Voir `/MIGRATION_V30.md` pour le guide complet.

```python
# AVANT (v2.3 - deprecated)
from src.scoring import calculate_composite_score
df = calculate_composite_score(df)

# APRÈS (v3.0)
from src.scoring import calculate_all_scores_v30
df = calculate_all_scores_v30(df)
```

---

## Colonnes de sortie

### v3.0 (recommandé)

| Colonne | Description |
|---------|-------------|
| `score_quality_v30` | Quality sector-relative [0, 1] |
| `score_value_v30` | Value + MoS [0, 1] |
| `score_risk_v30` | Risk inversé [0, 1] (1 = faible risque) |
| `score_composite_v30` | 45% Value + 35% Quality + 20% Risk |
| `rank_v30` | Rang (1 = meilleur) |

### v2.3 (deprecated)

| Colonne | Description |
|---------|-------------|
| `score_quality` | Quality absolue |
| `score_value` | Value absolue |
| `score_risk` | Risk inversé |
| `score_composite` | Composite v2.3 |
| `buffett_score` | Score Buffett legacy |

---

## Fichiers à supprimer (future release)

Ces fichiers seront supprimés dans une future version majeure :

- [ ] `value_composite.py` → remplacé par `value_v30.py`
- [ ] `quality_composite.py` → remplacé par `quality_v30.py`
- [ ] `risk_score.py` → remplacé par `risk_v30.py`
- [ ] `composite.py` → remplacé par `composite_v30.py`
- [ ] `crowding_score.py` → non utilisé
- [ ] `legacy/` → tout le dossier

---

## Philosophie v3.0 "Buffett-Quant"

> "Je ne prétends pas remplacer le jugement de Warren Buffett.
> En revanche, j'ai construit un modèle quantitatif dont la définition
> des facteurs reflète ses principes."

**Quality** = Rentabilité élevée et stable du capital, par rapport aux pairs, avec un bilan solide.

**Value** = Valorisation raisonnable vs secteur et vs l'historique propre de la société (Margin of Safety).

**Risk** = Éviter les profils susceptibles de générer une perte permanente de capital.
