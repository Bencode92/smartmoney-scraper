"""SmartMoney Legacy Scorers (v2.3)

⚠️  DEPRECATED — Utilisé uniquement pour rétrocompatibilité

Pour les nouveaux projets, utiliser les scorers v3.0:
    from src.scoring import calculate_all_scores_v30

Ces scorers utilisent des seuils ABSOLUS (ROE > 15% = bon)
au lieu des percentiles SECTOR-RELATIVE de v3.0.

Migration:
    AVANT (v2.3):  from src.scoring import calculate_composite_score
    APRÈS (v3.0):  from src.scoring import calculate_all_scores_v30

Date d'archivage: Décembre 2025
"""

import warnings

def _emit_deprecation_warning():
    warnings.warn(
        "Les scorers legacy v2.3 sont dépréciés. "
        "Utiliser les scorers v3.0: from src.scoring import calculate_all_scores_v30",
        DeprecationWarning,
        stacklevel=3
    )

# Imports avec warning
try:
    from .value_v23 import ValueScorer, score_value
    from .quality_v23 import QualityScorer, score_quality
    from .risk_v23 import RiskScorer, score_risk
    from .composite_v23 import CompositeScorer, calculate_composite_score
except ImportError:
    # Fallback si les fichiers n'existent pas encore
    pass

__all__ = [
    "ValueScorer",
    "score_value",
    "QualityScorer",
    "score_quality",
    "RiskScorer",
    "score_risk",
    "CompositeScorer",
    "calculate_composite_score",
]
