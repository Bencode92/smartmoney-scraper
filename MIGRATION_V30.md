# Guide de Migration vers SmartMoney v3.0 "Buffett-Quant"

**Date:** Décembre 2025

---

## Résumé

SmartMoney v3.0 représente une refonte majeure de la philosophie d'investissement:

| Aspect | v2.3 | v3.0 |
|--------|------|------|
| Philosophie | Factorielle générique | Buffett-Quant |
| Quality | Seuils absolus | Sector-relative + stabilité |
| Value | Seuils absolus | Cross-section + MoS |
| Risk | Low vol académique | Perte permanente de capital |
| Smart Money | 15% | 0% (indicateur) |
| Insider | 10% | 0% (tie-breaker) |

---

## Migration des Imports

### Scoring

```python
# AVANT (v2.3)
from src.scoring import calculate_composite_score
from src.scoring import score_value, score_quality, score_risk

# APRÈS (v3.0)
from src.scoring import calculate_all_scores_v30
from src.scoring import score_value_v30, score_quality_v30, score_risk_v30

# Ou utiliser l'alias par défaut
from src.scoring import calculate_all_scores  # → v3.0
```

### Configuration

```python
# AVANT (v2.3)
from config_v23 import WEIGHTS_V23, CONSTRAINTS_V23

# APRÈS (v3.0)
from config_v30 import WEIGHTS_V30, CONSTRAINTS_V30
```

---

## Changements de Poids

### v2.3 (déprécié)

```python
WEIGHTS_V23 = {
    "smart_money": 0.15,  # → 0% en v3.0
    "insider": 0.10,      # → 0% en v3.0
    "momentum": 0.05,     # → 0% en v3.0
    "value": 0.30,        # → 45% en v3.0
    "quality": 0.25,      # → 35% en v3.0
    "risk": 0.15,         # → 20% en v3.0
}
```

### v3.0 (actif)

```python
WEIGHTS_V30 = {
    "value": 0.45,        # Prix raisonnable vs secteur + MoS
    "quality": 0.35,      # Great business sector-relative
    "risk": 0.20,         # Éviter perte permanente
    "smart_money": 0.00,  # Indicateur seulement
    "insider": 0.00,      # Tie-breaker seulement
    "momentum": 0.00,     # Supprimé
}
```

---

## Changements de Logique

### Quality

**v2.3:** Seuils absolus
```python
# ROE > 15% = bon (0.70)
# ROE > 20% = très bon (0.85)
```

**v3.0:** Sector-relative + stabilité
```python
# ROE ranké 80e percentile dans le secteur = 0.80
# + pénalité si ROE volatil sur 5 ans
```

### Value

**v2.3:** Seuils absolus
```python
# FCF yield > 8% = excellent (1.0)
# P/E < 15 = bon (0.75)
```

**v3.0:** Cross-section + Margin of Safety
```python
# 60% cross-section: cheap vs pairs du secteur
# 40% MoS: P/E actuel vs P/E historique 5 ans
```

### Risk

**v2.3:** Low vol académique
```python
# Volatilité basse = bon
```

**v3.0:** Éviter perte permanente
```python
# 50% bilan (levier, coverage)
# 30% drawdown (max DD 5 ans)
# 20% volatilité
```

---

## Fichiers Archivés

| Fichier | Nouveau emplacement | Statut |
|---------|---------------------|--------|
| config_v23.py | legacy/config_v23.py | ⚠️ Deprecated |
| config_v25.py | legacy/config_v25.py | ⚠️ Deprecated |
| src/scoring/value_composite.py | src/scoring/legacy/value_v23.py | ⚠️ Deprecated |
| src/scoring/quality_composite.py | src/scoring/legacy/quality_v23.py | ⚠️ Deprecated |
| src/scoring/risk_score.py | src/scoring/legacy/risk_v23.py | ⚠️ Deprecated |
| src/scoring/composite.py | src/scoring/legacy/composite_v23.py | ⚠️ Deprecated |

---

## Nouveaux Fichiers v3.0

| Fichier | Description |
|---------|-------------|
| config_v30.py | Configuration Buffett-Quant |
| src/scoring/quality_v30.py | Quality sector-relative + stabilité |
| src/scoring/value_v30.py | Value cross-section + MoS |
| src/scoring/risk_v30.py | Risk perte permanente |
| src/scoring/composite_v30.py | Agrégation 45/35/20 |
| docs/investment_guidelines_v30.md | Document IC |

---

## Checklist de Migration

- [ ] Mettre à jour les imports de scoring
- [ ] Mettre à jour les imports de config
- [ ] Vérifier que les colonnes de sortie ont changé (`score_quality` → `score_quality_v30`)
- [ ] Tester avec des données de développement
- [ ] Mettre à jour les dashboards/reports

---

## Support

Les anciens fichiers restent disponibles pour rétrocompatibilité,
mais émettront des warnings de dépréciation.

Pour toute question, référer à `docs/investment_guidelines_v30.md`.
