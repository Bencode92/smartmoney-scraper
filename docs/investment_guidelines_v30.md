# Investment Guidelines — SmartMoney v3.0 "Buffett-Quant"

**Document IC / Investment Committee**  
**Date:** Décembre 2025  
**Version:** 3.0  
**Statut:** Forward Test

---

## 1. Résumé Exécutif

### 1.1 Ce que c'est

SmartMoney v3.0 est un **moteur quantitatif dont la définition des facteurs reflète les principes de Warren Buffett**:

| Facteur | Poids | Signification Buffett |
|---------|-------|----------------------|
| **Value** | 45% | Prix raisonnable vs secteur et historique |
| **Quality** | 35% | Great business: rentabilité élevée et stable vs pairs |
| **Risk** | 20% | Éviter la perte permanente de capital |

### 1.2 Ce que ce n'est PAS

- ❌ Un clone de Warren Buffett (process différent)
- ❌ Un générateur d'alpha Smart Money (Smart Money = 0%)
- ❌ Une stratégie factorielle générique (définitions Buffett-alignées)
- ❌ Un produit avec track record historique

### 1.3 Pitch en une phrase

> *"Un modèle quantitatif qui traduit la mentalité Buffett en facteurs mesurables: Quality sector-relative + Value avec Margin of Safety + Risk comme évitement de perte permanente."*

---

## 2. Philosophie d'Investissement

### 2.1 Principes Buffett traduits en facteurs

| Principe Buffett | Traduction Quantitative |
|------------------|------------------------|
| "Great business" | Quality sector-relative + stabilité 5 ans |
| "At a fair price" | Value cross-section + Margin of Safety |
| "Don't lose money" | Risk = éviter perte permanente de capital |
| "Circle of competence" | Filtre humain: je comprends le business |
| "Long-term holding" | Turnover 80%/an max, pas de sur-trading |

### 2.2 Ce que je fais (le modèle)

1. **Sélectionner** les candidats par scoring Value + Quality + Risk
2. **Contraindre** le portefeuille (15-20 lignes, 10% max/titre, 30% max/secteur)
3. **Rebalancer** trimestriellement avec discipline

### 2.3 Ce que je fais (le gérant humain)

1. **Filtrer** les titres que je ne comprends pas
2. **Vérifier** qualitativement les top positions (moat, culture, management)
3. **Refuser** de sur-trader si la thèse reste intacte

---

## 3. Définition des Facteurs

### 3.1 QUALITY v3.0 — "Great Business dans son secteur"

**Philosophie:** Buffett ne regarde pas "ROE > 15% en absolu". Il regarde "ROE élevé et durable par rapport à ce que le business peut naturellement faire".

**Composantes:**

| Composante | Poids | Description |
|------------|-------|-------------|
| ROE sector rank (5Y) | 20% | ROE moyen 5 ans, ranké dans le secteur |
| ROIC sector rank (5Y) | 15% | ROIC moyen 5 ans, ranké dans le secteur |
| Margin sector rank (5Y) | 15% | Marge op moyenne 5 ans, rankée secteur |
| ROE stability | 15% | 1 / (1 + std(ROE) sur 5 ans) |
| Margin stability | 15% | 1 / (1 + std(marge) sur 5 ans) |
| Leverage score | 10% | Bas D/E = bon |
| Coverage score | 10% | Coverage élevé = bon |

**Formule:**
```
Quality = 50% Profitabilité relative + 30% Stabilité + 20% Bilan
```

### 3.2 VALUE v3.0 — "Prix raisonnable pour ce type de business"

**Philosophie:** Buffett ne cherche pas les P/E les plus bas. Il cherche un BON business payé à un prix un peu en-dessous de sa valeur ou de son historique.

**Composantes:**

| Composante | Poids | Description |
|------------|-------|-------------|
| FCF yield sector rank | 25% | FCF yield ranké dans le secteur |
| EV/EBIT sector rank | 25% | 1 - rank(EV/EBIT) dans secteur |
| P/E sector rank | 10% | 1 - rank(P/E) dans secteur |
| P/E vs history | 20% | P/E actuel vs P/E moyen 5 ans |
| FCF yield vs history | 20% | FCF yield actuel vs moyenne 5 ans |

**Formule:**
```
Value = 60% Cross-section (cheap vs pairs) + 40% Margin of Safety (vs historique)
```

**Margin of Safety:**
```python
pe_discount = (pe_5y_avg - pe_current) / pe_5y_avg
fcf_premium = (fcf_yield_current - fcf_yield_5y_avg) / fcf_yield_5y_avg
mos_score = 0.5 * rank(pe_discount) + 0.5 * rank(fcf_premium)
```

### 3.3 RISK v3.0 — "Éviter la perte permanente de capital"

**Philosophie:** Ce n'est PAS un facteur "low vol" académique. C'est une pénalisation des profils susceptibles de générer une perte PERMANENTE de capital.

> *"Rule #1: Don't lose money. Rule #2: Don't forget rule #1."* — Buffett

**Composantes:**

| Composante | Poids | Description |
|------------|-------|-------------|
| Leverage safe | 25% | Bas D/E = bon |
| Debt/EBITDA safe | 15% | Bas ND/EBITDA = bon |
| Coverage safe | 10% | Coverage élevé = bon |
| Max DD 5Y | 20% | Max drawdown 5 ans (moins = mieux) |
| DD recovery | 10% | Vitesse de recovery |
| Volatility | 20% | Vol annuelle (moins = mieux) |

**Note:** Score INVERSÉ — score élevé = faible risque = BON

---

## 4. Univers d'Investissement

### 4.1 Définition

| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| Univers de base | S&P 500 | Liquidité, données fiables |
| Market cap minimum | $10 milliards | Large cap pur |
| ADV minimum | $5 millions | Liquidité quotidienne |
| Historique minimum | 5 ans | Pour calculs stabilité |

### 4.2 Hard Filters (Exclusions)

| Métrique | Seuil | Raison |
|----------|-------|--------|
| D/E | > 3.0 | Risque faillite |
| ND/EBITDA | > 4.0 | Surendettement |
| Interest Coverage | < 2.5 | Fragilité |
| ROE | < 3% | Business non viable |

**Note:** Le filtre ROE est assoupli (3% vs 8% avant) car le scoring sector-relative fait le tri fin.

---

## 5. Construction du Portefeuille

### 5.1 Process

```
Univers S&P 500 (~500 titres)
        ↓
Hard Filters (~350 titres)
        ↓
Scoring: 45% Value + 35% Quality + 20% Risk
        ↓
Top 30 par score composite
        ↓
FILTRE HUMAIN: "Je comprends ce business?"
        ↓
Top 15-20 retenus
        ↓
Sizing equal-weight + tilt
        ↓
Contraintes appliquées
        ↓
Portefeuille final
```

### 5.2 Contraintes

| Contrainte | Limite |
|------------|--------|
| Nombre de positions | 15-20 |
| Poids max par ligne | 10% |
| Poids min par ligne | 3% |
| Poids max par secteur | 30% |
| Nombre min de secteurs | 4 |
| Top 5 positions | ≤ 40% |
| Top 10 positions | ≤ 70% |

---

## 6. Rebalancing & Discipline

### 6.1 Fréquence

| Paramètre | Valeur |
|-----------|--------|
| Fréquence | Trimestrielle |
| Turnover max | 80%/an |
| No-trade zone | < 1% |

### 6.2 Règle "Ne pas sur-trader"

> *"Our favorite holding period is forever."* — Buffett

Ne PAS sortir d'un titre si:
- Le score ne baisse pas de plus de 10%
- La thèse fondamentale reste intacte
- Juste parce que le trimestre a été difficile

---

## 7. Smart Money & Insider — Position Claire

### 7.1 Pourquoi ils sont à 0%

> *"Tu arrêtes d'avoir une schizophrénie 'Buffett dans le discours, hedge funds & RSI dans la formule'."* — ChatGPT IC Review

**Réalité:**
- Smart Money = information retardée de 45 jours
- Insider = signal bruité, pas prouvé
- Momentum = pas de vue, pas d'edge

**Décision:** Ces signaux sont **hors du composite**. Ils servent uniquement de tags informatifs.

### 7.2 Usage autorisé

| Signal | Rôle | Usage |
|--------|------|-------|
| Smart Money | Indicateur | Affiché dans le dashboard, pas dans le score |
| Insider | Tie-breaker | À score égal (±1%), préférer achats insiders |
| Momentum | N/A | Supprimé |

---

## 8. Rôle du Gérant Humain

### 8.1 Filtre "Circle of Competence"

Sur le top 30 par score, je vire:
- Ce que je ne peux pas expliquer en 2 phrases
- Ce qui est trop techno/opaque pour moi
- Ce qui n'a pas de moat crédible selon moi

### 8.2 Review Qualitative

Pour le top 10 par poids, je lis:
- 10-K / rapport annuel
- Lettres aux actionnaires
- Earnings calls récents

Je vérifie:
- Le moat est-il crédible?
- La culture est-elle saine?
- Le management est-il aligné?

### 8.3 Anti-Sur-Trading

Je refuse de sortir d'un business juste parce que le score bouge un peu sur un trimestre, si la thèse fondamentale reste intacte.

---

## 9. Gestion du Risque

### 9.1 Métriques Surveillées

| Métrique | Cible | Warning | Limite |
|----------|-------|---------|--------|
| Max Drawdown | -25% | -20% | -35% |
| Beta vs SPY | 0.90-1.10 | Surveillé | Non contrôlé |

### 9.2 Actions

| Seuil DD | Action |
|----------|--------|
| > -10% | Monitoring renforcé |
| > -20% | Gel modifications modèle |
| > -30% | Review complète |
| > -35% | Escalation possible arrêt |

---

## 10. Ce que je dis au Comité

> *"Je ne prétends pas remplacer le jugement de Warren Buffett.*
>
> *En revanche, j'ai construit un modèle quantitatif dont la définition des facteurs reflète ses principes:*
>
> *• Quality = rentabilité élevée et stable du capital, par rapport aux pairs, avec un bilan solide.*
>
> *• Value = valorisation raisonnable vs secteur et vs l'historique propre de la société.*
>
> *• Risk = éviter les profils susceptibles de générer une perte permanente de capital.*
>
> *Le moteur me donne une liste disciplinée de candidats. Ensuite, en tant que gérant, j'applique une couche qualitative simple: je ne retiens pas un titre que je ne comprends pas.*
>
> *Smart Money et Insiders ne sont PAS dans le score. Ils servent uniquement d'indicateurs informatifs."*

---

## 11. Limitations et Honnêteté

### 11.1 Ce que le modèle ne fait PAS

| Limitation | Conséquence |
|------------|------------|
| Pas de lecture 10-K automatique | Le moat n'est pas vérifié par le modèle |
| Pas de jugement sur le management | Impossible de détecter les mauvais acteurs |
| Pas de prévision macro | Vulnérable aux retournements de cycle |
| Pas de backtest historique | Performance inconnue avant forward test |

### 11.2 Ce qui manquera toujours

> *"Tu ne comprends pas vraiment le business. Tu ne lis pas les rapports annuels. Tu ne connais pas le management. C'est du quant, pas de l'investing."* — Ce que Buffett dirait

**Réponse honnête:**

> *"C'est vrai. v3.0 n'est pas Buffett. C'est un moteur factoriel avec une couche Buffett-inspired dans la définition des facteurs. Le stock picking humain reste irremplaçable. C'est pourquoi j'ajoute une couche qualitative manuelle."*

---

## 12. Forward Test

### 12.1 Paramètres

| Paramètre | Valeur |
|-----------|--------|
| Durée | 12-24 mois |
| Début | Janvier 2026 |
| Fréquence rebal | Trimestrielle |
| Benchmark | SPY |

### 12.2 Critères de succès (12 mois)

| Métrique | Seuil "Encourageant" | Seuil "Échec" |
|----------|----------------------|---------------|
| Alpha cumulé | > 0% | < -5% |
| Hit Rate | > 50% | < 35% |

---

*Document préparé pour Investment Committee — Décembre 2025*  
*SmartMoney Engine v3.0 "Buffett-Quant"*
