# SmartMoney v2.4 — Data & Operations Plan

**Plan de continuité des données et opérations**  
**Version:** 1.0  
**Date:** Décembre 2025

---

## 1. Sources de Données

### 1.1 Inventaire

| Source | Type | Usage | Criticité |
|--------|------|-------|----------|
| **Twelve Data** | API | Prix, fondamentaux | 🔴 Critique |
| **HedgeFollow** | Scraping | 13F Hedge Funds | 🟡 Important |
| **SEC EDGAR** | API | Form 4 Insiders | 🟡 Important |
| **Yahoo Finance** | API (yfinance) | Prix backup | 🟢 Backup |

### 1.2 Dépendances par Facteur

| Facteur | Source Principale | Backup | Action si panne |
|---------|-------------------|--------|------------------|
| Value | Twelve Data | Yahoo Finance | Switch auto |
| Quality | Twelve Data | Yahoo Finance | Switch auto |
| Risk | Twelve Data | Yahoo Finance | Switch auto |
| Smart Money | HedgeFollow | SEC EDGAR | Désactiver facteur |
| Insider | SEC EDGAR | — | Désactiver facteur |
| Momentum | Twelve Data | Yahoo Finance | Switch auto |

---

## 2. Plan B par Source

### 2.1 Si Twelve Data tombe

**Détection :** API retourne erreur ou timeout > 5 min

**Action immédiate :**
1. Switch vers yfinance (automatique)
2. Log l'incident
3. Alerte email

**Action sous 24h :**
1. Vérifier statut Twelve Data
2. Contacter support si nécessaire
3. Décider continuation ou pause

**Impact :** Faible (backup disponible)

### 2.2 Si HedgeFollow tombe

**Détection :** Scraping retourne 0 résultats ou erreur HTML

**Action immédiate :**
1. **Désactiver le facteur Smart Money** (poids = 0)
2. Redistribuer les poids aux autres facteurs
3. Log l'incident
4. Alerte email

**Action sous 7 jours :**
1. Implémenter fallback SEC EDGAR
2. Ou migrer vers WhaleWisdom ($500/mois)

**Impact :** Modéré (perte d'un facteur expérimental)

**Nouvelle pondération sans SM :**
```python
WEIGHTS_NO_SM = {
    "smart_money": 0.00,  # Désactivé
    "insider": 0.12,      # +2%
    "momentum": 0.08,     # +3%
    "value": 0.35,        # +5%
    "quality": 0.28,      # +3%
    "risk": 0.17,         # +2%
}
```

### 2.3 Si SEC EDGAR tombe

**Détection :** API retourne erreur ou 0 filings

**Action immédiate :**
1. Désactiver le facteur Insider (poids = 0)
2. Redistribuer les poids
3. Log + alerte

**Impact :** Faible (Insider = 10% seulement)

---

## 3. Monitoring Automatique

### 3.1 Checks Quotidiens

| Check | Seuil d'alerte | Action |
|-------|----------------|--------|
| Taille univers | < 400 titres | Alerte |
| Prix manquants | > 5% | Alerte |
| Market cap nuls | > 2% | Alerte |
| Secteurs manquants | > 1 secteur | Alerte |
| Score composite NaN | > 0% | Erreur |

### 3.2 Checks Hebdomadaires

| Check | Seuil | Action |
|-------|-------|--------|
| Distribution des scores | std < 0.10 | Warning |
| Changement univers | > 20% | Investigation |
| Données 13F fraîches | > 60 jours | Alerte |

### 3.3 Code de Monitoring

```python
def daily_data_check(df: pd.DataFrame) -> Dict:
    """Vérifications quotidiennes."""
    checks = {
        "universe_size": len(df),
        "universe_ok": len(df) >= 400,
        "missing_prices": df["price"].isna().mean(),
        "missing_mcap": df["market_cap"].isna().mean(),
        "missing_sector": df["sector"].isna().mean(),
        "nan_scores": df["score_composite"].isna().sum(),
    }
    
    checks["all_ok"] = (
        checks["universe_ok"] and
        checks["missing_prices"] < 0.05 and
        checks["missing_mcap"] < 0.02 and
        checks["nan_scores"] == 0
    )
    
    return checks
```

---

## 4. Gestion des Anomalies

### 4.1 Types d'Anomalies

| Type | Exemple | Détection | Action |
|------|---------|-----------|--------|
| Prix aberrant | Prix < 0 ou > $10,000 | Automatique | Exclure le titre |
| Market cap aberrant | < $100M pour S&P 500 | Automatique | Exclure le titre |
| Volume nul | Volume = 0 | Automatique | Flag + investigation |
| Changement >50% 1j | Gap inexplicable | Automatique | Flag + vérification |

### 4.2 Règles d'Exclusion

```python
EXCLUSION_RULES = {
    "price_min": 1.0,           # Exclure penny stocks
    "price_max": 50000.0,       # Anomalie
    "mcap_min": 1e9,            # $1B minimum
    "volume_min": 100000,       # 100K volume quotidien
    "price_change_max": 0.50,   # |change| > 50% = flag
}
```

---

## 5. Processus de Rebalancing

### 5.1 Timeline

```
J-7 :  Téléchargement des données
       Vérification qualité
       
J-3 :  Génération du portefeuille candidat
       Review manuel
       
J-1 :  Validation finale
       Préparation des ordres
       
J :    Exécution
       Log des trades
       
J+1 :  Vérification exécution
       Mise à jour positions
```

### 5.2 Checks Pré-Rebalancing

| Check | Condition | Action si échec |
|-------|-----------|------------------|
| Data fraîche | < 48h | Reporter |
| Qualité data | all_ok = True | Reporter |
| Marché ouvert | Pas de fermeture | Reporter |
| VIX | < 40 | Review manuel |

---

## 6. Contacts et Escalade

### 6.1 Contacts Vendors

| Vendor | Contact | SLA |
|--------|---------|-----|
| Twelve Data | support@twelvedata.com | 24h |
| SEC EDGAR | — (public) | N/A |
| HedgeFollow | — (scraping) | N/A |

### 6.2 Escalade Interne

| Niveau | Déclencheur | Action |
|--------|-------------|--------|
| 1 | Alerte monitoring | Investigation |
| 2 | Source down > 24h | Activer backup |
| 3 | Source down > 7j | Migration vendor |
| 4 | Impact matériel | Pause stratégie |

---

## 7. Backup et Récupération

### 7.1 Données à Sauvegarder

| Donnée | Fréquence | Rétention |
|--------|-----------|----------|
| Portefeuilles générés | Chaque run | 5 ans |
| Données brutes univers | Quotidien | 1 an |
| Logs de trading | Chaque trade | 7 ans |
| Rapports de backtest | Chaque run | Permanent |

### 7.2 Localisation

```
data/
├── prices/          # Cache des prix
├── universe/        # Snapshots univers
├── portfolios/      # Historique portfolios
└── logs/            # Logs opérationnels

outputs/
├── YYYY-MM-DD/      # Runs datés
└── backtest/        # Rapports backtest
```

---

## 8. Tests de Continuité

### 8.1 Tests Trimestriels

| Test | Description |
|------|-------------|
| Failover Twelve Data | Simuler panne, vérifier switch yfinance |
| Failover Smart Money | Désactiver HedgeFollow, vérifier redistribution |
| Recovery from backup | Restaurer depuis sauvegarde |

### 8.2 Documentation des Tests

Chaque test doit produire :
1. Date et heure
2. Scénario testé
3. Résultat (pass/fail)
4. Actions correctives si échec

---

## 9. Améliorations Futures

| Amélioration | Priorité | Effort |
|--------------|----------|--------|
| Pipeline EDGAR natif | Haute | 2 semaines |
| Alertes Slack/Email | Moyenne | 1 semaine |
| Dashboard monitoring | Basse | 3 semaines |
| Migration WhaleWisdom | Si HedgeFollow down | 1 semaine |

---

**Document approuvé**  
**Date :** Décembre 2025  
**Version :** 1.0
