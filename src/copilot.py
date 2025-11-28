"""IA Copilot - Génération de rapports et alertes via OpenAI"""
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import OPENAI_KEY, OPENAI_MODEL, OPENAI_MODEL_FAST, OUTPUTS


class Copilot:
    """Assistant IA pour analyse et reporting"""
    
    def __init__(self):
        if not OPENAI_KEY:
            raise ValueError("API_OPENAI non configurée")
        self.client = OpenAI(api_key=OPENAI_KEY)
    
    def _call(self, prompt: str, fast: bool = False) -> str:
        """Appel OpenAI"""
        model = OPENAI_MODEL_FAST if fast else OPENAI_MODEL
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    
    def generate_memo(self, portfolio: dict) -> str:
        """Génère un Investment Memo complet"""
        
        positions = portfolio.get("portfolio", [])
        n = len(positions)
        
        # Top 5 pour analyse détaillée
        top5 = positions[:5] if len(positions) >= 5 else positions
        
        prompt = f"""Tu es un analyste senior en gestion d'actifs. Génère un Investment Memo professionnel.

## DONNÉES DU PORTEFEUILLE

**Date**: {datetime.now().strftime("%Y-%m-%d")}
**Nombre de positions**: {n}

**Top 5 positions**:
{json.dumps(top5, indent=2)}

**Toutes les positions (résumé)**:
{json.dumps([{"symbol": p["symbol"], "weight": p["weight"], "score": p.get("score_composite", 0)} for p in positions], indent=2)}

## FORMAT ATTENDU

Génère un memo structuré avec:

### 1. Vue Globale (3-4 lignes)
- Orientation du portefeuille
- Biais principaux

### 2. Top 5 Convictions
Pour chaque position:
- **TICKER** (poids%)
- Signaux: SmartMoney / Insider / Momentum
- Thèse en 2 phrases max

### 3. Risques Identifiés
- Concentration sectorielle
- Corrélations dangereuses
- Points d'attention

### 4. Scénarios de Stress
- Scénario 1: Impact si Tech -15%
- Scénario 2: Impact si taux +50bps
- Scénario 3: Flight to quality

### 5. Actions Recommandées
- Surveillances
- Triggers de sortie potentiels

Sois factuel, concis, pas de langue de bois. Style institutionnel.
"""
        
        return self._call(prompt)
    
    def generate_alerts(self, portfolio: dict) -> list:
        """Génère des alertes sur le portefeuille"""
        
        positions = portfolio.get("portfolio", [])
        
        prompt = f"""Analyse ce portefeuille et génère des ALERTES si nécessaire.

**Positions**:
{json.dumps(positions, indent=2)}

**Règles d'alerte**:
- Position > 5.5% du portefeuille → alerte concentration
- Score composite < 0.4 → alerte qualité
- RSI > 70 ou < 30 → alerte momentum extrême
- Plus de 3 positions dans le même secteur tech → alerte sectorielle

**Format de sortie**:
Retourne UNIQUEMENT un JSON array d'alertes:
[
  {{
    "level": "warning|critical",
    "type": "concentration|quality|momentum|sector",
    "symbol": "TICKER ou null si global",
    "message": "Description courte de l'alerte"
  }}
]

Si aucune alerte, retourne: []
"""
        
        response = self._call(prompt, fast=True)
        
        # Parse JSON
        try:
            # Nettoie la réponse (enlève markdown si présent)
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean)
        except:
            return [{"level": "warning", "type": "parse_error", "symbol": None, "message": "Impossible de parser les alertes"}]
    
    def answer_question(self, portfolio: dict, question: str) -> str:
        """Répond à une question sur le portefeuille"""
        
        prompt = f"""Tu es un assistant spécialisé en gestion de portefeuille.

**Portefeuille actuel**:
{json.dumps(portfolio, indent=2)}

**Question de l'utilisateur**:
{question}

Réponds de façon concise et factuelle. Si tu ne peux pas répondre avec les données disponibles, dis-le.
"""
        
        return self._call(prompt, fast=True)
    
    def export_memo(self, portfolio: dict, output_dir: Path) -> Path:
        """
        Génère et sauvegarde le memo.
        
        Args:
            portfolio: Données du portefeuille
            output_dir: Dossier daté (ex: outputs/2025-11-28/)
        """
        print("🤖 Génération du memo IA...")
        memo = self.generate_memo(portfolio)
        
        # Sauvegarde (sans suffixe de date, le dossier parent est déjà daté)
        memo_path = output_dir / "memo.md"
        
        # Récupère la date depuis le dossier parent ou metadata
        date_str = portfolio.get("metadata", {}).get("date", datetime.now().strftime("%Y-%m-%d"))
        
        with open(memo_path, "w") as f:
            f.write(f"# Investment Memo - {date_str}\n\n")
            f.write(memo)
        
        print(f"📝 Memo exporté: {output_dir.name}/memo.md")
        return memo_path
    
    def export_alerts(self, portfolio: dict, output_dir: Path) -> Path:
        """
        Génère et sauvegarde les alertes.
        
        Args:
            portfolio: Données du portefeuille
            output_dir: Dossier daté (ex: outputs/2025-11-28/)
        """
        print("🚨 Génération des alertes...")
        alerts = self.generate_alerts(portfolio)
        
        # Sauvegarde (sans suffixe de date)
        alerts_path = output_dir / "alerts.json"
        with open(alerts_path, "w") as f:
            json.dump(alerts, f, indent=2)
        
        n_critical = len([a for a in alerts if a.get("level") == "critical"])
        n_warning = len([a for a in alerts if a.get("level") == "warning"])
        print(f"🚨 Alertes: {n_critical} critiques, {n_warning} warnings → {output_dir.name}/alerts.json")
        
        return alerts_path


# === MAIN ===
if __name__ == "__main__":
    # Test avec le dernier portfolio
    # Cherche d'abord dans outputs/latest/, sinon dans les sous-dossiers datés
    latest_dir = OUTPUTS / "latest"
    
    if latest_dir.exists() and (latest_dir / "portfolio.json").exists():
        portfolio_path = latest_dir / "portfolio.json"
    else:
        # Fallback: cherche dans les sous-dossiers datés
        dated_dirs = sorted([d for d in OUTPUTS.iterdir() if d.is_dir() and d.name != "latest"], reverse=True)
        if not dated_dirs:
            print("❌ Aucun portfolio trouvé. Lance d'abord: python main.py")
            exit(1)
        portfolio_path = dated_dirs[0] / "portfolio.json"
    
    if not portfolio_path.exists():
        print(f"❌ Portfolio non trouvé: {portfolio_path}")
        exit(1)
    
    print(f"📂 Chargement: {portfolio_path}")
    with open(portfolio_path) as f:
        portfolio = json.load(f)
    
    # Exporte dans le même dossier que le portfolio
    output_dir = portfolio_path.parent
    
    copilot = Copilot()
    copilot.export_memo(portfolio, output_dir)
    copilot.export_alerts(portfolio, output_dir)
