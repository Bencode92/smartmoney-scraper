"""[DEPRECATED] SmartMoney v2.3 — Risk Scorer (Legacy)

⚠️  Ce fichier est archivé pour rétrocompatibilité.
    Pour les nouveaux projets, utiliser: src/scoring/risk_v30.py

Différences clés v2.3 vs v3.0:
- v2.3: "Low vol" académique (volatilité basse = bon)
- v3.0: Éviter la PERTE PERMANENTE de capital (levier, DD, faillite)

Migration:
    AVANT:  from src.scoring import score_risk
    APRÈS:  from src.scoring import score_risk_v30

Date d'archivage: Décembre 2025
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from risk_score import (
        RiskScorer,
        RiskScore,
        score_risk,
    )
except ImportError as e:
    import warnings
    warnings.warn(f"Impossible d'importer risk_score: {e}")
    
    class RiskScorer:
        pass
    
    class RiskScore:
        pass
    
    def score_risk(*args, **kwargs):
        raise NotImplementedError("Utiliser score_risk_v30")

__all__ = [
    "RiskScorer",
    "RiskScore",
    "score_risk",
]
