"""[DEPRECATED] SmartMoney v2.3 — Composite Scorer (Legacy)

⚠️  Ce fichier est archivé pour rétrocompatibilité.
    Pour les nouveaux projets, utiliser: src/scoring/composite_v30.py

Différences clés v2.3 vs v3.0:
- v2.3: Smart Money 15%, Insider 10%, Momentum 5%
- v3.0: Smart Money 0%, Insider 0%, Momentum 0% (indicateurs only)

Poids v2.3:
    Value: 30%, Quality: 25%, Risk: 15%
    Smart Money: 15%, Insider: 10%, Momentum: 5%

Poids v3.0 (Buffett-Quant):
    Value: 45%, Quality: 35%, Risk: 20%
    Smart Money: 0% (indicateur), Insider: 0% (tie-breaker)

Migration:
    AVANT:  from src.scoring import calculate_composite_score
    APRÈS:  from src.scoring import calculate_all_scores_v30

Date d'archivage: Décembre 2025
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from composite import (
        CompositeScorer,
        calculate_composite_score,
    )
except ImportError as e:
    import warnings
    warnings.warn(f"Impossible d'importer composite: {e}")
    
    class CompositeScorer:
        pass
    
    def calculate_composite_score(*args, **kwargs):
        raise NotImplementedError("Utiliser calculate_all_scores_v30")

__all__ = [
    "CompositeScorer",
    "calculate_composite_score",
]
