"""[DEPRECATED] SmartMoney v2.3 — Quality Composite Scorer (Legacy)

⚠️  Ce fichier est archivé pour rétrocompatibilité.
    Pour les nouveaux projets, utiliser: src/scoring/quality_v30.py

Différences clés v2.3 vs v3.0:
- v2.3: Seuils ABSOLUS (ROE > 15% = bon, ROIC > 25% = excellent)
- v3.0: Percentiles SECTOR-RELATIVE + STABILITÉ 5 ans

Migration:
    AVANT:  from src.scoring import score_quality
    APRÈS:  from src.scoring import score_quality_v30

Date d'archivage: Décembre 2025
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from quality_composite import (
        QualityScorer,
        QualityScore,
        score_quality,
    )
except ImportError as e:
    import warnings
    warnings.warn(f"Impossible d'importer quality_composite: {e}")
    
    class QualityScorer:
        pass
    
    class QualityScore:
        pass
    
    def score_quality(*args, **kwargs):
        raise NotImplementedError("Utiliser score_quality_v30")

__all__ = [
    "QualityScorer",
    "QualityScore",
    "score_quality",
]
