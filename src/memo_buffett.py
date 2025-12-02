"""Memo Warren Buffett Style — Analyse qualitative du portefeuille

Génère un memo d'investissement avec la philosophie Buffett:
- Management & vision long terme
- Moat (avantage concurrentiel durable)
- Qualité comptable (earnings réels vs fictifs)
- Analyse du bilan et de la génération de cash

Date: Décembre 2025
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# === SECTEURS ET MOATS TYPIQUES ===
SECTOR_MOATS = {
    "Technology": {
        "moat_types": ["Network effects", "Switching costs", "Intangible assets (IP)"],
        "risks": ["Disruption rapide", "Dépendance aux talents", "Régulation antitrust"],
        "buffett_view": "Difficile à évaluer, mais les leaders avec pricing power sont attractifs"
    },
    "Financial Services": {
        "moat_types": ["Économies d'échelle", "Coûts de switching", "Marque/confiance"],
        "risks": ["Régulation", "Taux d'intérêt", "Risque systémique"],
        "buffett_view": "Privilégier les assureurs avec float et les banques conservatrices"
    },
    "Healthcare": {
        "moat_types": ["Brevets", "Approbations FDA", "R&D pipeline"],
        "risks": ["Expiration brevets", "Pricing politique", "Échecs cliniques"],
        "buffett_view": "Préférer les entreprises diversifiées avec revenus récurrents"
    },
    "Consumer Defensive": {
        "moat_types": ["Marques fortes", "Distribution", "Habitudes consommateurs"],
        "risks": ["Commoditisation", "Private labels", "Changements consommateurs"],
        "buffett_view": "Cœur du portefeuille Buffett - cash flows prévisibles"
    },
    "Consumer Cyclical": {
        "moat_types": ["Marque premium", "Échelle", "E-commerce"],
        "risks": ["Cyclicité économique", "Disruption retail", "Inventaires"],
        "buffett_view": "Prudence sur le timing, focus sur les leaders de catégorie"
    },
    "Industrials": {
        "moat_types": ["Échelle/coûts", "Relations clients", "Certifications"],
        "risks": ["Cycles économiques", "Capex élevé", "Concurrence internationale"],
        "buffett_view": "Préférer les businesses avec revenus récurrents (services, maintenance)"
    },
    "Energy": {
        "moat_types": ["Actifs low-cost", "Intégration verticale", "Réserves"],
        "risks": ["Prix commodities", "Transition énergétique", "Géopolitique"],
        "buffett_view": "Position tactique, éviter la dépendance aux prix spot"
    },
    "Communication Services": {
        "moat_types": ["Contenu exclusif", "Base utilisateurs", "Données"],
        "risks": ["Changements algorithmes", "Régulation", "Concurrence"],
        "buffett_view": "Network effects puissants mais valorisations souvent élevées"
    },
    "Basic Materials": {
        "moat_types": ["Coûts production", "Localisation", "Intégration"],
        "risks": ["Prix commodities", "Environnement", "Capex"],
        "buffett_view": "Éviter sauf producteurs low-cost avec bilan solide"
    },
}


def analyze_earnings_quality(position: dict) -> dict:
    """
    Analyse la qualité des earnings (Buffett cherche des earnings "réels").
    
    Indicateurs clés:
    - FCF vs Net Income: FCF devrait être >= Net Income
    - Accruals ratio: Plus bas = meilleur
    - Capex ratio: Capex/Revenue indique l'intensité capitalistique
    """
    net_income = position.get("net_income")
    fcf = position.get("fcf")
    revenue = position.get("revenue")
    capex_ratio = position.get("capex_ratio")
    
    quality = {
        "score": "N/A",
        "fcf_vs_income": None,
        "capex_intensity": None,
        "assessment": "Données insuffisantes"
    }
    
    # FCF vs Net Income
    if fcf is not None and net_income is not None and net_income != 0:
        ratio = fcf / net_income if net_income > 0 else -1
        quality["fcf_vs_income"] = round(ratio, 2)
        
        if ratio >= 1.2:
            quality["assessment"] = "🟢 Excellent - FCF supérieur au net income (earnings conservateurs)"
            quality["score"] = "A"
        elif ratio >= 0.8:
            quality["assessment"] = "🟡 Correct - FCF proche du net income"
            quality["score"] = "B"
        elif ratio >= 0.5:
            quality["assessment"] = "🟠 Attention - FCF significativement inférieur (accruals élevés)"
            quality["score"] = "C"
        else:
            quality["assessment"] = "🔴 Prudence - Écart important FCF/Net Income (qualité douteuse)"
            quality["score"] = "D"
    
    # Capex intensity
    if capex_ratio is not None:
        quality["capex_intensity"] = capex_ratio
        if capex_ratio > 15:
            quality["capex_note"] = "Capex élevé - business capital-intensive"
        elif capex_ratio > 8:
            quality["capex_note"] = "Capex modéré"
        else:
            quality["capex_note"] = "Capex faible - business asset-light (favorable)"
    
    return quality


def analyze_balance_sheet(position: dict) -> dict:
    """
    Analyse du bilan selon les critères Buffett.
    
    Buffett préfère:
    - D/E < 0.5 (conservateur)
    - Current ratio > 1.5
    - Cash significatif
    """
    de = position.get("debt_equity")
    cr = position.get("current_ratio")
    roe = position.get("roe")
    
    analysis = {
        "leverage": "N/A",
        "liquidity": "N/A",
        "profitability": "N/A",
        "overall": "Données insuffisantes"
    }
    
    scores = []
    
    # Leverage (D/E)
    if de is not None:
        if de < 0.3:
            analysis["leverage"] = "🟢 Fortress balance sheet (D/E < 0.3)"
            scores.append(3)
        elif de < 0.8:
            analysis["leverage"] = "🟡 Leverage modéré (D/E < 0.8)"
            scores.append(2)
        elif de < 1.5:
            analysis["leverage"] = "🟠 Leverage élevé (D/E < 1.5)"
            scores.append(1)
        else:
            analysis["leverage"] = "🔴 Leverage excessif (D/E > 1.5)"
            scores.append(0)
    
    # Liquidity (Current Ratio)
    if cr is not None:
        if cr > 2:
            analysis["liquidity"] = "🟢 Liquidité excellente (CR > 2)"
            scores.append(3)
        elif cr > 1.5:
            analysis["liquidity"] = "🟡 Liquidité confortable (CR > 1.5)"
            scores.append(2)
        elif cr > 1:
            analysis["liquidity"] = "🟠 Liquidité correcte (CR > 1)"
            scores.append(1)
        else:
            analysis["liquidity"] = "🔴 Risque liquidité (CR < 1)"
            scores.append(0)
    
    # ROE
    if roe is not None:
        if roe > 20:
            analysis["profitability"] = f"🟢 ROE excellent ({roe:.1f}%)"
            scores.append(3)
        elif roe > 15:
            analysis["profitability"] = f"🟡 ROE bon ({roe:.1f}%)"
            scores.append(2)
        elif roe > 10:
            analysis["profitability"] = f"🟠 ROE moyen ({roe:.1f}%)"
            scores.append(1)
        else:
            analysis["profitability"] = f"🔴 ROE faible ({roe:.1f}%)"
            scores.append(0)
    
    # Overall
    if scores:
        avg = sum(scores) / len(scores)
        if avg >= 2.5:
            analysis["overall"] = "Bilan de qualité institutionnelle"
        elif avg >= 1.5:
            analysis["overall"] = "Bilan acceptable avec quelques points d'attention"
        else:
            analysis["overall"] = "Bilan fragile - surveiller de près"
    
    return analysis


def get_moat_analysis(position: dict) -> dict:
    """Analyse du moat basée sur le secteur et les métriques."""
    sector = position.get("sector", "Unknown")
    sector_info = SECTOR_MOATS.get(sector, {
        "moat_types": ["Non catégorisé"],
        "risks": ["Analyse spécifique requise"],
        "buffett_view": "Évaluer au cas par cas"
    })
    
    # Score moat basé sur métriques
    moat_score = 0
    moat_indicators = []
    
    # Marges élevées = pricing power
    margin = position.get("net_margin")
    if margin and margin > 20:
        moat_score += 2
        moat_indicators.append(f"Marge nette élevée ({margin:.1f}%) → pricing power")
    elif margin and margin > 10:
        moat_score += 1
        moat_indicators.append(f"Marge nette correcte ({margin:.1f}%)")
    
    # ROE élevé avec faible dette = avantage compétitif
    roe = position.get("roe")
    de = position.get("debt_equity")
    if roe and roe > 20 and de and de < 0.5:
        moat_score += 2
        moat_indicators.append(f"ROE {roe:.1f}% avec faible dette → capital efficiency")
    elif roe and roe > 15:
        moat_score += 1
        moat_indicators.append(f"ROE solide ({roe:.1f}%)")
    
    # Gross margin élevée
    gross = position.get("gross_margin")
    if gross and gross > 50:
        moat_score += 1
        moat_indicators.append(f"Marge brute élevée ({gross:.1f}%) → différenciation")
    
    # Assessment
    if moat_score >= 4:
        moat_assessment = "🟢 Moat probable - Indicateurs de pricing power et capital efficiency"
    elif moat_score >= 2:
        moat_assessment = "🟡 Moat possible - Quelques avantages compétitifs"
    else:
        moat_assessment = "🟠 Moat incertain - Surveiller la compétition"
    
    return {
        "sector": sector,
        "typical_moats": sector_info["moat_types"],
        "risks": sector_info["risks"],
        "buffett_view": sector_info["buffett_view"],
        "indicators": moat_indicators,
        "assessment": moat_assessment
    }


def generate_position_analysis(position: dict) -> str:
    """Génère l'analyse complète d'une position style Buffett."""
    symbol = position.get("symbol", "N/A")
    company = position.get("company", symbol)
    sector = position.get("sector", "N/A")
    weight = position.get("weight", 0) * 100
    
    # Analyses
    earnings_q = analyze_earnings_quality(position)
    balance = analyze_balance_sheet(position)
    moat = get_moat_analysis(position)
    
    # Scores
    buffett_score = position.get("buffett_score", position.get("score_composite", 0))
    score_value = position.get("score_value", "N/A")
    score_quality = position.get("score_quality_v23", position.get("score_quality", "N/A"))
    score_risk = position.get("score_risk", "N/A")
    
    analysis = f"""
### {symbol} — {company[:30]}
**Secteur:** {sector} | **Poids:** {weight:.1f}% | **Buffett Score:** {buffett_score:.3f}

#### 📊 Scores v2.3
| Value | Quality | Risk (inversé) |
|-------|---------|----------------|
| {score_value if isinstance(score_value, str) else f"{score_value:.2f}"} | {score_quality if isinstance(score_quality, str) else f"{score_quality:.2f}"} | {score_risk if isinstance(score_risk, str) else f"{score_risk:.2f}"} |

#### 🏰 Analyse du Moat
- **Types possibles:** {", ".join(moat["typical_moats"])}
- **Indicateurs:** {"; ".join(moat["indicators"]) if moat["indicators"] else "Données insuffisantes"}
- **Assessment:** {moat["assessment"]}
- **Vue Buffett sur le secteur:** _{moat["buffett_view"]}_

#### 📈 Qualité des Earnings
- **FCF / Net Income:** {earnings_q["fcf_vs_income"] if earnings_q["fcf_vs_income"] else "N/A"}x
- **Assessment:** {earnings_q["assessment"]}
{f'- **Capex:** {earnings_q["capex_note"]}' if earnings_q.get("capex_note") else ""}

#### 💰 Solidité du Bilan
- **Leverage:** {balance["leverage"]}
- **Liquidité:** {balance["liquidity"]}
- **Rentabilité:** {balance["profitability"]}
- **Verdict:** _{balance["overall"]}_

---
"""
    return analysis


def generate_buffett_memo(portfolio_data: dict, output_dir: Path) -> Path:
    """
    Génère un memo d'investissement style Warren Buffett.
    
    Args:
        portfolio_data: Données du portefeuille (de engine.export())
        output_dir: Dossier de sortie
    
    Returns:
        Path du fichier généré
    """
    metadata = portfolio_data.get("metadata", {})
    metrics = portfolio_data.get("metrics", {})
    positions = portfolio_data.get("portfolio", [])
    
    date_str = metadata.get("date", datetime.now().strftime("%Y-%m-%d"))
    engine_version = metadata.get("engine_version", "2.3")
    
    # === HEADER ===
    memo = f"""# 📜 SmartMoney Investment Memo — {date_str}
## _Style Warren Buffett : Qualité, Moat & Long Terme_

---

> "Price is what you pay. Value is what you get." — Warren Buffett

---

## 🎯 Résumé Exécutif

| Métrique | Valeur |
|----------|--------|
| **Positions** | {metrics.get('positions', len(positions))} |
| **Performance 3M** | {metrics.get('perf_3m', 'N/A')}% |
| **Performance YTD** | {metrics.get('perf_ytd', 'N/A')}% |
| **Volatilité 30j** | {metrics.get('vol_30d', 'N/A')}% |
| **ROE moyen** | {metrics.get('avg_roe', 'N/A')}% |
| **D/E moyen** | {metrics.get('avg_debt_equity', 'N/A')} |
| **Marge nette moy.** | {metrics.get('avg_net_margin', 'N/A')}% |

---

## 🧭 Philosophie d'Investissement

Ce portefeuille suit les principes de Warren Buffett :

1. **Cercle de compétence** — Focus sur des businesses compréhensibles
2. **Moat durable** — Avantage concurrentiel défendable
3. **Management intègre** — Allocateurs de capital disciplinés
4. **Marge de sécurité** — Acheter sous la valeur intrinsèque
5. **Horizon long terme** — "Our favorite holding period is forever"

---

## 🔬 Analyse Détaillée par Position

"""
    
    # === ANALYSE PAR POSITION ===
    # Trier par poids décroissant
    sorted_positions = sorted(positions, key=lambda x: x.get("weight", 0), reverse=True)
    
    # Top 10 ou toutes si moins
    top_positions = sorted_positions[:10]
    
    for pos in top_positions:
        memo += generate_position_analysis(pos)
    
    # === ANALYSE SECTORIELLE ===
    sector_weights = metrics.get("sector_weights", {})
    sorted_sectors = sorted(sector_weights.items(), key=lambda x: -x[1])
    
    memo += """
## 📊 Répartition Sectorielle

| Secteur | Poids | Vue Buffett |
|---------|-------|-------------|
"""
    
    for sector, weight in sorted_sectors[:7]:
        sector_info = SECTOR_MOATS.get(sector, {"buffett_view": "N/A"})
        memo += f"| {sector} | {weight}% | {sector_info['buffett_view'][:50]}... |\n"
    
    # === RISQUES ET POINTS D'ATTENTION ===
    memo += """

---

## ⚠️ Points d'Attention & Risques

### Concentration
"""
    
    # Check concentration
    if sorted_positions:
        top3_weight = sum(p.get("weight", 0) for p in sorted_positions[:3]) * 100
        if top3_weight > 40:
            memo += f"- 🔴 **Concentration élevée** : Top 3 = {top3_weight:.1f}% du portefeuille\n"
        else:
            memo += f"- 🟢 **Diversification correcte** : Top 3 = {top3_weight:.1f}%\n"
    
    # Check sector concentration
    if sorted_sectors:
        top_sector = sorted_sectors[0]
        if top_sector[1] > 35:
            memo += f"- 🔴 **Surexposition sectorielle** : {top_sector[0]} = {top_sector[1]}%\n"
        else:
            memo += f"- 🟢 **Exposition sectorielle équilibrée** : Max = {top_sector[1]}%\n"
    
    # Check high volatility positions
    high_vol = [p for p in positions if (p.get("vol_30d") or 0) > 40]
    if high_vol:
        memo += f"- 🟠 **Positions volatiles** : {len(high_vol)} titres avec vol > 40%\n"
    
    # Check negative ROE
    neg_roe = [p for p in positions if (p.get("roe") or 0) < 0]
    if neg_roe:
        symbols = [p.get("symbol") for p in neg_roe[:3]]
        memo += f"- 🔴 **ROE négatif** : {', '.join(symbols)}\n"
    
    # Check high leverage
    high_de = [p for p in positions if (p.get("debt_equity") or 0) > 2]
    if high_de:
        symbols = [p.get("symbol") for p in high_de[:3]]
        memo += f"- 🟠 **Leverage élevé (D/E > 2)** : {', '.join(symbols)}\n"
    
    # === CONCLUSION ===
    memo += f"""

---

## 📝 Conclusion

Ce portefeuille SmartMoney v{engine_version} combine :
- **Signaux institutionnels** (hedge funds via Dataroma)
- **Achats d'initiés** (skin in the game)
- **Métriques Buffett** (value, quality, risk)

### Recommandations
1. **Revoir trimestriellement** les positions avec ROE < 10% ou D/E > 1.5
2. **Surveiller les moats** — un moat qui s'érode est un signal de vente
3. **Ignorer la volatilité court terme** — focus sur les fondamentaux
4. **Renforcer** les positions de qualité lors des corrections

---

_"Be fearful when others are greedy, and greedy when others are fearful."_

**Généré par SmartMoney Engine v{engine_version}**  
**Date :** {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
    
    # === SAVE ===
    memo_path = output_dir / "memo.md"
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo)
    
    print(f"📜 Memo Buffett exporté: {output_dir.name}/memo.md")
    return memo_path


# === MAIN ===
if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from config import OUTPUTS
    
    # Cherche le dernier portfolio
    dated_dirs = sorted([d for d in OUTPUTS.iterdir() if d.is_dir()], reverse=True)
    if not dated_dirs:
        print("❌ Aucun portfolio trouvé")
        exit(1)
    
    portfolio_path = dated_dirs[0] / "portfolio.json"
    if not portfolio_path.exists():
        print(f"❌ Portfolio non trouvé: {portfolio_path}")
        exit(1)
    
    print(f"📂 Chargement: {portfolio_path}")
    with open(portfolio_path) as f:
        portfolio = json.load(f)
    
    generate_buffett_memo(portfolio, portfolio_path.parent)
