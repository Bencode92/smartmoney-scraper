# Paragraphe pour Investment Committee

## "Pourquoi il n'y a pas de backtest, et pourquoi c'est volontaire"

---

### Version Courte (Pitch 60 secondes)

> *"Je n'ai pas de backtest à vous montrer, et c'est un choix délibéré.*
>
> *Pour construire un backtest sérieux de cette stratégie, j'aurais besoin de données fondamentales historiques (ROE, FCF, marges tels qu'ils étaient à chaque date) et des positions 13F des hedge funds trimestre par trimestre. Ces données coûtent cher et je ne les ai pas.*
>
> *Plutôt que de vous présenter un backtest artificiel avec des proxies ou des données extrapolées — ce qui serait intellectuellement malhonête et facilement démontable — je préfère être transparent.*
>
> *Ce que je vous propose : un moteur théoriquement fondé, techniquement propre, et un programme de forward test sur 12-24 mois pour construire un vrai historique observé."*

---

### Version Complète (Pour document écrit)

#### Pourquoi il n'y a pas de backtest

La stratégie SmartMoney repose sur plusieurs facteurs :
- **Value** : FCF yield, EV/EBIT, P/E relatif
- **Quality** : ROE, ROIC, stabilité des marges
- **Risk** : volatilité, drawdown historique
- **Smart Money** : positions des hedge funds via filings 13F
- **Insider** : transactions des dirigeants (Form 4)

Pour backtester correctement cette stratégie, il faudrait reconstituer, à chaque date historique :
1. Les **fondamentaux tels qu'ils étaient connus** à cette date (pas les données actuelles projetées dans le passé)
2. Les **positions 13F des hedge funds** telles qu'elles étaient publiées
3. La **composition du S&P 500** à cette date (survivorship bias)

**Ces données ne sont pas disponibles dans ma stack actuelle.**

Les sources que j'utilise (Twelve Data, HedgeFollow) fournissent des données **actuelles**, pas des historiques point-in-time.

#### Pourquoi je ne fais pas de "backtest approximatif"

Il serait techniquement possible de construire un "backtest" en utilisant :
- Des proxies académiques (inverse du return 1Y pour Value, Sharpe ratio pour Quality)
- Des données fondamentales actuelles projetées dans le passé
- Des positions 13F simulées ou moyennées

**Je refuse de faire cela pour trois raisons :**

1. **C'est malhonête** — Ce ne serait pas un test de MA stratégie, mais d'une version approximative
2. **C'est détectable** — Un analyste expérimenté verrait immédiatement les incohérences
3. **Ça détruit la crédibilité** — Mieux vaut pas de backtest qu'un backtest bidon

#### Ce que je propose à la place

1. **Un dossier théorique solide**
   - Description précise des facteurs et leur fondement économique (Fama-French, Novy-Marx, etc.)
   - Expositions factorielles typiques du portefeuille
   - Profil de risque attendu (beta, concentration, DD plausibles)

2. **Un code propre et audité**
   - Contraintes enforced par tests unitaires
   - Process transparent et reproductible
   - Pas de "boîte noire"

3. **Un programme de forward test structuré**
   - Modèle figé (v2.4)
   - Rebalancing trimestriel documenté
   - Métriques suivies vs SPY et ETF Quality/Value
   - Durée : 12-24 mois
   - Engagement de ne pas modifier le modèle pendant cette période

4. **Une roadmap claire pour le futur**
   - Si on veut un vrai backtest institutionnel : budget data ~$10-20K/an
   - Sources nécessaires : FactSet, Bloomberg, ou équivalent pour fondamentaux historiques
   - Développement : 4-8 semaines pour pipeline point-in-time

#### Ce que je demande

> *"Je ne vous demande pas de valider un produit pour mandat client.*
>
> *Je vous demande l'autorisation de lancer un programme de test forward sur 12-24 mois, éventuellement avec un petit capital prop (chez moi ou chez vous).*
>
> *Pas d'argent client tant qu'on n'a pas 12-24 mois de vécu réel."*

---

### Réponses aux Objections Prévisibles

**"Pourquoi ne pas utiliser des données gratuites pour le backtest ?"**

> Les données gratuites (Yahoo Finance, etc.) ne fournissent que des prix, pas des fondamentaux historiques point-in-time. Utiliser les fondamentaux actuels pour le passé introduit un biais massif (look-ahead bias).

**"Tous les quants font des backtests, pourquoi pas toi ?"**

> Les quants institutionnels ont accès à Bloomberg, FactSet, CRSP, Compustat — des bases de données qui coûtent $50-100K/an et fournissent des historiques point-in-time. Je n'ai pas ce budget. Je préfère être honnête sur mes limitations.

**"Comment savoir si ta stratégie fonctionne sans backtest ?"**

> C'est précisément pourquoi je propose un forward test. C'est plus lent, mais c'est la seule façon honnête de construire un historique sans les données nécessaires pour un backtest propre.

**"12-24 mois c'est trop long"**

> Je comprends. Mais les alternatives sont :
> - Un backtest bidon qui ne prouve rien
> - Un investissement data de $10-20K/an pour construire un vrai backtest
> Le forward test est le compromis réaliste.

---

### Conclusion

> *"Mon absence de backtest n'est pas un manque de rigueur — c'est une conséquence de ma rigueur.*
>
> *Je refuse de vous vendre des chiffres que je ne peux pas défendre.*
>
> *Ce que je peux défendre : un process clair, des facteurs documentés, un code propre, et un plan pour prouver la stratégie en conditions réelles."*

---

*Document préparé pour présentation Investment Committee*
