"""[DEPRECATED] SmartMoney v2.3 — Value Composite Scorer (Legacy)

⚠️  Ce fichier est archivé pour rétrocompatibilité.
    Pour les nouveaux projets, utiliser: src/scoring/value_v30.py

Différences clés v2.3 vs v3.0:
- v2.3: Seuils ABSOLUS (FCF Yield > 8% = excellent)
- v3.0: Percentiles SECTOR-RELATIVE + Margin of Safety vs historique

Migration:
    AVANT:  from src.scoring import score_value
    APRÈS:  from src.scoring import score_value_v30

Date d'archivage: Décembre 2025
"""

# Ré-exporter depuis l'ancien emplacement pour rétrocompatibilité
import sys
from pathlib import Path

# Ajouter le parent au path pour importer l'ancien fichier
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Importer depuis value_composite.py (l'ancien fichier)
try:
    from value_composite import (
        ValueScorer,
        ValueScore,
        ValueScorerCrossSectional,
        ValueScorerSectorNeutral,
        score_value,
        score_value_cross_sectional,
        diagnose_value_distribution,
    )
except ImportError as e:
    import warnings
    warnings.warn(f"Impossible d'importer value_composite: {e}")
    
    # Fallback minimal
    class ValueScorer:
        pass
    
    class ValueScore:
        pass
    
    def score_value(*args, **kwargs):
        raise NotImplementedError("Utiliser score_value_v30")

__all__ = [
    "ValueScorer",
    "ValueScore",
    "score_value",
]
