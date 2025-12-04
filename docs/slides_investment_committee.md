# SmartMoney v2.4 — Présentation Investment Committee

*Slide deck pour présentation 15-20 minutes*

---

## Slide 1: Titre

# SmartMoney v2.4

### Large Cap US Quality/Value + Smart Money Overlay

**Investment Committee Presentation**

Décembre 2025

---

## Slide 2: Agenda

1. **Positionnement** — Qu'est-ce que SmartMoney ?
2. **Stratégie** — Comment ça marche ?
3. **Performance** — Backtest et attentes
4. **Risques** — Ce qui peut mal tourner
5. **Usage** — Pour qui et comment ?
6. **Q&A**

---

## Slide 3: Positionnement

### En une phrase :

> **Stratégie Long-Only concentrée exploitant les signaux Smart Money sur un univers Large Cap US Quality/Value**

### Caractéristiques clés :

| | |
|---|---|
| **Univers** | S&P 500 |
| **Positions** | 15-20 titres |
| **Style** | Quality/Value |
| **Edge** | Smart Money + Insider |
| **Capacité** | 1-5 M$ |

---

## Slide 4: Sources d'Alpha

```
┌─────────────────────────────────────────────┐
│                                             │
│   🏦 SMART MONEY (25%)                      │
│   Hedge funds 13F + Insiders Form 4         │
│                                             │
│   📊 QUALITY (25%)                          │
│   ROIC > 15%, Marges, FCF Growth            │
│                                             │
│   💰 VALUE (30%)                            │
│   FCF Yield, EV/EBIT, P/E relatif           │
│                                             │
│   ⚖️ RISK CONTROL (15% + 5%)               │
│   Volatilité, Momentum confirmation         │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Slide 5: Processus d'Investissement

```
S&P 500 (500 titres)
        │
        ▼
   SCORING (6 facteurs)
        │
        ▼
   TOP 50 par score
        │
        ▼
   OPTIMISATION
   • Max 12% / position
   • Max 30% / secteur
        │
        ▼
   PORTEFEUILLE
   15-20 positions
```

---

## Slide 6: Pondération des Facteurs

| Facteur | Poids | Rôle |
|---------|-------|------|
| **Value** | 30% | Valorisation attractive |
| **Quality** | 25% | Rentabilité durable |
| **Smart Money** | 15% | Signal institutionnel |
| **Risk** | 15% | Contrôle volatilité |
| **Insider** | 10% | Info asymétrique |
| **Momentum** | 5% | Confirmation |

**Total : 100%**

---

## Slide 7: Contraintes (v2.4 — Enforced)

### Avant v2.4 ❌
- Contraintes déclarées mais **ignorées** par l'optimiseur
- Positions jusqu'à 25%
- Secteurs jusqu'à 50%

### Après v2.4 ✅
- Contraintes **réellement enforced**
- Max 12% par position
- Max 30% par secteur
- Tests unitaires pour vérifier

---

## Slide 8: Scoring Value (v2.4)

### Avant : Seuils absolus
```
FCF Yield > 8% → Score = 1.0
FCF Yield > 5% → Score = 0.75
...
Problème : Tous les scores ~ 0.70 (clustering)
```

### Après : Cross-sectionnel
```
FCF Yield → Percentile vs univers
Score = rank(FCF_Yield) / N

Résultat : Distribution uniforme [0, 1]
Meilleure discrimination
```

---

## Slide 9: Expositions Factorielles

| Facteur | Exposition | vs SPY |
|---------|------------|--------|
| **Beta** | 0.95-1.10 | ≈ Neutre |
| **Value** | +0.05 à +0.15 | Surpondéré |
| **Quality** | +0.10 à +0.25 | Surpondéré |
| **Momentum** | -0.05 à +0.10 | Neutre |
| **Size** | Large/Mega | Similaire |

**Tracking Error attendu : 8-12%**

---

## Slide 10: Backtest — Méthodologie

| Paramètre | Valeur |
|-----------|--------|
| **Type** | Walk-forward OOS |
| **Période** | 2020-2024 |
| **Window** | Trimestriel |
| **Paramètres** | FIGÉS |
| **Benchmark** | SPY |

### Principes :
1. ✅ Pas de look-ahead
2. ✅ Paramètres gelés
3. ✅ Out-of-sample
4. ⚠️ Survivorship bias non corrigé

---

## Slide 11: Performance — Cibles

| Métrique | Cible | Minimum |
|----------|-------|---------|
| **CAGR** | > 12% | > 8% |
| **Alpha** | > 2%/an | > 0% |
| **Hit Rate** | > 55% | > 50% |
| **Sharpe** | > 0.7 | > 0.5 |
| **Info Ratio** | > 0.5 | > 0.3 |
| **Max DD** | > -30% | > -40% |

---

## Slide 12: Régimes de Marché

| Régime | Performance relative |
|--------|---------------------|
| 🐂 **Bull Market** | Légère sous-perf (Value drag) |
| 🐻 **Bear Market** | Surperf (Quality) |
| 🚀 **Rally Growth** | Sous-perf significative |
| 🔄 **Rotation Value** | Surperformance |
| 📈 **Hausse taux** | Neutre à négatif |

---

## Slide 13: Risques Principaux

| Risque | Impact | Mitigation |
|--------|--------|------------|
| **Concentration** | Élevé | Limites 12%/30% |
| **Value Trap** | Élevé | Quality overlay |
| **Drawdown** | Élevé | Sizing approprié |
| **Lag 13F** | Moyen | 45j délai accepté |
| **Crowding** | Moyen | Multi-facteurs |

---

## Slide 14: Scénarios de Stress

| Scénario | SPY | SmartMoney |
|----------|-----|------------|
| **COVID 2020** | -34% | -30% à -35% |
| **2022 Taux** | -19% | -15% à -22% |
| **Rally Tech** | +30% | +20% à +25% |

### ⚠️ Drawdown max attendu : -35% à -40%

*Pas de protection structurelle (long-only)*

---

## Slide 15: Pour Qui ?

### ✅ Adapté :
- Horizon ≥ 3 ans
- Tolérance tracking error 8-12%
- Accepte -35% drawdown
- Conviction Quality/Value

### ❌ Non adapté :
- Horizon < 1 an
- Besoin de coller au benchmark
- Aversion à la concentration
- Besoin de liquidité

---

## Slide 16: Allocation Recommandée

```
┌──────────────────────────────────┐
│                                  │
│  CORE (80-90%)                   │
│  • SPY/VTI : 60-70%             │
│  • Bonds : 20%                   │
│                                  │
│  SATELLITE (10-20%)              │
│  • SmartMoney v2.4 : 10-20% ◄   │
│                                  │
└──────────────────────────────────┘
```

**Sizing max recommandé : 20%**

---

## Slide 17: Opérations

| Aspect | Valeur |
|--------|--------|
| **Rebalancing** | Trimestriel |
| **Review** | Mensuel |
| **Coûts** | ~0.5%/an |
| **Reporting** | Mensuel vs SPY |

### Triggers de révision :
- DD > -25%
- Underperf > 10% sur 12M
- 3 trimestres négatifs consécutifs

---

## Slide 18: Roadmap v3.0

| Amélioration | Timeline |
|--------------|----------|
| Constituants historiques S&P | Q1 2026 |
| Coûts de transaction | Q1 2026 |
| Attribution factorielle | Q2 2026 |
| Stress tests automatisés | Q2 2026 |
| Extension Mid Cap | Q3 2026 |

---

## Slide 19: Synthèse

### SmartMoney v2.4

| ✅ Forces | ⚠️ Limites |
|-----------|-----------|
| Multi-facteurs diversifié | Long-only uniquement |
| Smart Money edge | Délai 13F 45j |
| Contraintes enforced | Concentration |
| Walk-forward validé | US Large Cap only |

### Recommandation :

> **Poche satellite 10-20%** pour investisseurs sophistiqués avec horizon long

---

## Slide 20: Q&A

### Questions attendues :

1. *"Pourquoi garder Smart Money à 15% ?"*
2. *"Quelle est la pire série 2015-2024 ?"*
3. *"Que se passe-t-il si les taux passent à 6.5% ?"*
4. *"Comment gérez-vous le survivorship bias ?"*
5. *"Quelle est la capacité maximale ?"*

---

## Annexe A: Repository

**GitHub :** [Bencode92/smartmoney-scraper](https://github.com/Bencode92/smartmoney-scraper)

### Fichiers clés :
- `config_v23.py` — Paramètres figés
- `src/engine_v23.py` — Moteur principal
- `src/backtest_walkforward.py` — Backtest OOS
- `docs/investment_memo.md` — Memo complet

---

## Annexe B: Commits Récents

| Commit | Description |
|--------|-------------|
| `80adc50` | Fix contraintes optimiseur |
| `1100230` | Tests unitaires contraintes |
| `7ebe7df` | Value cross-sectionnel |
| `9be8f8e` | Doc expositions factorielles |
| `412d062` | Walk-forward backtest |
| `9ebf5de` | Investment Memo |

**Version : v2.4.0**

---

*Présentation préparée pour Investment Committee — Décembre 2025*
