# SmartMoney v2.4 — Expositions Factorielles

*Documentation technique des expositions aux facteurs de risque*
*Date: 4 décembre 2025*

---

## 📋 POSITIONNEMENT STRATÉGIQUE

> **"Large Cap US Quality/Value avec overlay Smart Money, concentrée."**

SmartMoney v2.4 est une stratégie:
- **Large Cap US**: Univers S&P 500 (≥$10B market cap)
- **Quality**: Sélection sur ROIC, marges, FCF growth
- **Value**: Tilt vers FCF Yield, EV/EBIT, P/E attractifs
- **Smart Money overlay**: Signal des hedge funds (13F) et insiders
- **Concentrée**: 12-20 positions (vs 500 pour SPY)

---

## 🎯 EXPOSITIONS FACTORIELLES

### Matrice des Expositions

| Facteur | Exposition | Source | Poids dans Score |
|---------|------------|--------|------------------|
| **Size** | Large Cap (neutre à positif) | Filtre liquidité + S&P 500 | Implicite |
| **Value** | **Positive** | FCF Yield, EV/EBIT, P/E | 30% |
| **Quality** | **Positive** | ROIC, Marges, FCF Growth | 25% |
| **Momentum** | Légère positive | RSI, Perf 3M | 5% |
| **Low Volatility** | Neutre à positive | Risk score inversé | 15% |
| **Smart Money** | **Positive** | Hedge fund holdings, Insiders | 25% |

### Décomposition par Score

```
Score Composite v2.3 = 
    15% × Smart Money Score    → Exposition Smart Money
  + 10% × Insider Score        → Exposition Smart Money
  +  5% × Momentum Score       → Exposition Momentum
  + 30% × Value Score          → Exposition Value
  + 25% × Quality Score        → Exposition Quality
  + 15% × (1 - Risk Score)     → Exposition Low Vol
```

---

## 📊 BETAS SECTORIELS TYPIQUES

### Allocation Sectorielle Historique (2024)

| Secteur | Allocation Typique | Beta Estimé | Commentaire |
|---------|-------------------|-------------|-------------|
| **Technology** | 15-25% | 1.15-1.25 | Souvent capé à 30% |
| **Financial Services** | 15-25% | 1.00-1.10 | Préféré par Buffett |
| **Healthcare** | 10-15% | 0.85-0.95 | Défensif |
| **Consumer Defensive** | 5-10% | 0.60-0.70 | Très défensif |
| **Energy** | 5-10% | 1.10-1.30 | Cyclique |
| **Industrials** | 5-10% | 1.00-1.10 | Cyclique modéré |
| **Communication Services** | 5-10% | 1.00-1.15 | Mixed |
| **Consumer Cyclical** | 5-10% | 1.10-1.20 | Cyclique |

### Beta Portefeuille Estimé

```
Beta_portfolio ≈ Σ (weight_i × beta_sector_i)

Exemple typique:
  25% × Tech (1.20) = 0.30
+ 20% × Finance (1.05) = 0.21
+ 15% × Health (0.90) = 0.135
+ 10% × Consumer Def (0.65) = 0.065
+ 30% × Autres (1.05) = 0.315
= Beta ≈ 1.025

→ Légèrement au-dessus du marché
```

---

## 📈 APPROXIMATIONS FACTORIELLES

### Value Exposure

**Proxy**: Tilt P/E et FCF Yield

```python
# Approximation Value exposure
value_tilt = (
    (portfolio_pe / spy_pe - 1) * -1 +  # Négatif si P/E plus bas
    (portfolio_fcf_yield / spy_fcf_yield - 1)  # Positif si FCF Yield plus haut
) / 2

# Interprétation:
# > 0.10 : Fort tilt Value
# 0.00-0.10 : Tilt Value modéré
# -0.05-0.00 : Neutre
# < -0.05 : Tilt Growth
```

**Exposition attendue**: +0.05 à +0.15 (tilt Value modéré à fort)

### Quality Exposure

**Proxy**: Tilt ROE et Net Margin

```python
# Approximation Quality exposure
quality_tilt = (
    (portfolio_roe / spy_roe - 1) +
    (portfolio_margin / spy_margin - 1)
) / 2

# Interprétation:
# > 0.15 : Fort tilt Quality
# 0.05-0.15 : Tilt Quality modéré
# < 0.05 : Faible tilt Quality
```

**Exposition attendue**: +0.10 à +0.25 (tilt Quality significatif)

### Momentum Exposure

**Proxy**: Perf 3M relative

```python
# Approximation Momentum exposure
momentum_tilt = portfolio_perf_3m - spy_perf_3m

# Interprétation:
# > +3% : Tilt Momentum positif
# -3% à +3% : Neutre
# < -3% : Tilt Momentum négatif
```

**Exposition attendue**: -2% à +5% (légère à modérée selon période)

### Size Exposure

**Proxy**: Market Cap médiane

```python
# Approximation Size exposure
# Large Cap = >$10B, Mid Cap = $2-10B, Small Cap = <$2B

avg_market_cap = portfolio["market_cap"].mean()
median_market_cap = portfolio["market_cap"].median()

# S&P 500 médiane ≈ $30B
# SmartMoney typique: médiane $50-150B (biais megacap)

size_tilt = "Large/Mega Cap" if median_market_cap > 30e9 else "Mid Cap"
```

**Exposition attendue**: Large à Mega Cap (médiane >$50B)

---

## ⚠️ RISQUES FACTORIELS

### Risques Identifiés

| Risque Factoriel | Probabilité | Impact | Période Défavorable |
|------------------|-------------|--------|---------------------|
| **Value Trap** | Moyenne | Élevé | Rally Growth (2020-21) |
| **Quality Crowding** | Moyenne | Moyen | Fin de cycle |
| **Smart Money Herding** | Moyenne | Moyen | Retournement rapide |
| **Concentration** | Élevée | Élevé | Choc sectoriel |
| **Low Vol Reversal** | Faible | Moyen | Sortie de récession |

### Scénarios de Stress Factoriels

| Scénario | Impact Estimé | Facteur Dominant |
|----------|---------------|------------------|
| Rally Tech/Growth | -5% à -10% relatif | Value underperform |
| Hausse taux violente | -10% à -15% | Quality/Growth hit |
| Récession légère | +2% à +5% relatif | Quality outperform |
| Récession sévère | -25% à -35% | Beta ≈ 1 |
| Rotation Value | +5% à +10% relatif | Value outperform |
| Inflation élevée | Variable | Sector-dependent |

---

## 📐 MÉTRIQUES DE SUIVI

### Métriques à Monitorer

```python
FACTOR_METRICS = {
    # Value
    "portfolio_pe": "P/E moyen pondéré",
    "portfolio_fcf_yield": "FCF Yield moyen pondéré",
    "pe_vs_spy": "Ratio P/E portfolio / SPY",
    
    # Quality
    "portfolio_roe": "ROE moyen pondéré",
    "portfolio_margin": "Net Margin moyenne pondérée",
    "roe_vs_spy": "Ratio ROE portfolio / SPY",
    
    # Momentum
    "perf_3m_relative": "Perf 3M vs SPY",
    "avg_rsi": "RSI moyen du portefeuille",
    
    # Risk
    "portfolio_vol": "Volatilité 30j annualisée",
    "tracking_error": "Écart-type des alpha mensuels",
    "max_position": "Poids de la plus grosse position",
    "max_sector": "Poids du plus gros secteur",
    "hhi_concentration": "Indice Herfindahl-Hirschman",
}
```

### Formules de Calcul

```python
def calculate_factor_metrics(portfolio_df, spy_metrics):
    """Calcule les métriques factorielles du portefeuille."""
    
    weights = portfolio_df["weight"]
    
    metrics = {}
    
    # --- Value ---
    metrics["portfolio_pe"] = (weights * portfolio_df["pe_ratio"].fillna(20)).sum()
    metrics["pe_vs_spy"] = metrics["portfolio_pe"] / spy_metrics["pe"]
    
    fcf_yield = portfolio_df["fcf"] / portfolio_df["market_cap"]
    metrics["portfolio_fcf_yield"] = (weights * fcf_yield.fillna(0)).sum()
    
    # --- Quality ---
    metrics["portfolio_roe"] = (weights * portfolio_df["roe"].fillna(15)).sum()
    metrics["roe_vs_spy"] = metrics["portfolio_roe"] / spy_metrics["roe"]
    
    metrics["portfolio_margin"] = (weights * portfolio_df["net_margin"].fillna(10)).sum()
    
    # --- Momentum ---
    metrics["perf_3m_relative"] = (
        (weights * portfolio_df["perf_3m"].fillna(0)).sum() - 
        spy_metrics["perf_3m"]
    )
    metrics["avg_rsi"] = (weights * portfolio_df["rsi"].fillna(50)).sum()
    
    # --- Concentration ---
    metrics["max_position"] = weights.max()
    metrics["max_sector"] = portfolio_df.groupby("sector")["weight"].sum().max()
    metrics["hhi"] = (weights ** 2).sum()  # 0.05 = diversifié, 0.10+ = concentré
    
    return metrics
```

---

## 📊 BENCHMARKING FACTORIEL

### ETF de Référence par Facteur

| Facteur | ETF Proxy | Ticker | Description |
|---------|-----------|--------|-------------|
| **Value** | iShares S&P 500 Value | IVE | Large Cap Value |
| **Quality** | iShares MSCI USA Quality | QUAL | US Quality |
| **Momentum** | iShares MSCI USA Momentum | MTUM | US Momentum |
| **Low Vol** | Invesco S&P 500 Low Vol | SPLV | Low Volatility |
| **Size (Small)** | iShares Russell 2000 | IWM | Small Cap |
| **Market** | SPDR S&P 500 | SPY | Benchmark |

### Régression Factorielle Suggérée

```python
# Modèle Fama-French + Momentum + Quality
# R_portfolio - R_f = α + β_mkt(R_mkt - R_f) + β_smb(SMB) + β_hml(HML) + β_mom(MOM) + β_qual(QUAL) + ε

# Expositions attendues pour SmartMoney v2.4:
expected_betas = {
    "mkt": 0.95,      # Légèrement défensif
    "smb": -0.10,     # Biais Large Cap
    "hml": +0.15,     # Tilt Value
    "mom": +0.05,     # Léger Momentum
    "qual": +0.20,    # Tilt Quality significatif
}
```

---

## 🎯 POSITIONNEMENT FINAL

### Caractéristiques Clés

| Caractéristique | Valeur | Comparaison SPY |
|-----------------|--------|-----------------|
| **Univers** | S&P 500 | = |
| **Positions** | 12-20 | 500 |
| **Concentration** | Max 12%/position | ~7% (AAPL) |
| **Style** | Quality/Value | Blend |
| **Taille** | Large/Mega Cap | Large Cap |
| **Beta attendu** | 0.95-1.10 | 1.00 |
| **Tracking Error** | 8-12% | 0% |

### Pour Qui ?

✅ **Adapté pour**:
- Investisseurs avec horizon 3-5 ans
- Tolérance au tracking error vs SPY
- Conviction dans les facteurs Quality/Value
- Capacité à supporter sous-performance temporaire

❌ **Non adapté pour**:
- Horizon court terme (<1 an)
- Besoin de coller au benchmark
- Aversion au risque de concentration
- Recherche de performance Growth pure

---

## 📝 CHANGELOG

| Version | Date | Changement |
|---------|------|------------|
| v2.4 | Dec 2025 | Ajout documentation factorielle |
| v2.3 | Nov 2025 | Buffett overlay, scoring v2.3 |
| v2.2 | Oct 2025 | Quality scoring amélioré |

---

*Document généré dans le cadre de l'Étape 2 du plan d'institutionnalisation SmartMoney.*
