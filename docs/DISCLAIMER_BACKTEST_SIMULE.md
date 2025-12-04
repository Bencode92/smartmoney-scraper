# ⚠️ AVERTISSEMENT : Backtest Simulé

## Ce que contient ce repo

Le fichier `outputs/backtest_oos/backtest_oos_simulated.json` contient un backtest **SIMULÉ** qui :

- ❌ N'utilise PAS les vrais scorers SmartMoney
- ❌ N'utilise PAS les vraies données fondamentales
- ❌ N'utilise PAS les vraies données 13F
- ❌ Utilise des proxies académiques génériques

## Pourquoi ce fichier existe

Il a été créé comme exercice technique, mais ne représente PAS la performance réelle de la stratégie SmartMoney.

## Ce qu'il faut utiliser à la place

1. **Pour comprendre la stratégie** : `docs/factsheet_no_backtest.md`
2. **Pour le forward test** : `docs/forward_test_protocol.md`
3. **Pour présenter au comité** : `docs/ic_paragraph_no_backtest.md`

## Statut officiel

> **SmartMoney v2.4 n'a PAS de backtest historique valide.**
>
> Les données nécessaires (fondamentaux et 13F historiques point-in-time) ne sont pas disponibles.
>
> La stratégie sera validée par **forward test** sur 12-24 mois.

---

*Ce disclaimer a été ajouté suite à la revue IC de décembre 2025.*
