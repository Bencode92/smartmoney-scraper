# SmartMoney v2.4 — Rapport Backtest OOS

*Généré le 2025-12-04 15:54*

⚠️ **SIMULATION** basée sur factor premiums académiques et rendements SPY réels 2019-2024

---

## 📋 Paramètres

| Paramètre | Valeur |
|-----------|--------|
| Période | 2019-Q1 → 2024-Q3 |
| Trimestres | 23 |
| Benchmark | SPY |
| Méthodologie | Walk-forward trimestriel |

---

## 🎯 Résultats Comparatifs

| Configuration | CAGR | Alpha Total | Alpha/an | Hit Rate | Sharpe | Max DD | IR |
|---------------|------|-------------|----------|----------|--------|--------|----|
| Core (Quality/Value) | +18.83% | +22.53% | +3.92% | 87.0% | 1.23 | -20.38% | 9.26 |
| Core + Smart Money (15%) | +18.14% | +19.17% | +3.33% | 82.6% | 1.15 | -21.10% | 9.24 |
| Smart Money Réduit (5%) | +18.50% | +20.90% | +3.63% | 87.0% | 1.19 | -20.71% | 9.40 |
| SPY (Benchmark) | +14.29% | — | — | — | ~0.65 | — | — |

---

## 🔍 Analyse du Facteur Smart Money

### Impact 0% → 15%

| Métrique | Contribution |
|----------|-------------|
| Alpha Total | **-3.36%** |
| Alpha/an | **-0.58%** |
| Sharpe | **-0.08** |
| Information Ratio | **-0.02** |

### Impact 0% → 5%

| Métrique | Contribution |
|----------|-------------|
| Alpha Total | **-1.63%** |
| Sharpe | **-0.04** |

---

## 🏆 Verdict

### ❌ Smart Money N'AJOUTE PAS de valeur

**Le facteur Smart Money DÉGRADE les performances !**

- Ajouter 15% de Smart Money → **-3.36% d'alpha perdu**
- Ajouter 5% de Smart Money → **-1.63% d'alpha perdu**

**Recommandation:** Réduire Smart Money à 0-5% ou le supprimer complètement

---

## ⚠️ Limitations

1. **Données simulées** - Basées sur factor premiums académiques, pas sur des données réelles
2. **Smart Money simulé** - Le facteur Smart Money est approximé, pas basé sur les vrais 13F
3. **Pas de coûts** - Transaction costs non inclus (~0.3-0.5%/an estimé)
4. **Survivorship bias** - Non traité dans cette simulation

---

## 📌 Prochaines Étapes

1. **Exécuter avec données réelles** via Twelve Data ou yfinance localement
2. **Valider ces résultats** sur l'univers S&P 500 réel
3. **Si confirmé** → Réduire Smart Money à 0-5% dans config_v24.py

```bash
# Exécuter localement avec vraies données
export API_TWELVEDATA="votre_clé"
python -m src.backtest_oos_real --start 2019-01-01 --end 2024-12-31
```

---

*Rapport généré par SmartMoney v2.4 Backtest Engine*
