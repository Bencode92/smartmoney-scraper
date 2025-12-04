"""SmartMoney Scoring Package

VERSIONS DISPONIBLES:
=====================

v3.0 "Buffett-Quant" (ACTIF - RECOMMANDÉ)
-----------------------------------------
Philosophie: Traduire la mentalité Buffett en facteurs mesurables.

Poids:
- Value: 45% (cross-section + Margin of Safety)
- Quality: 35% (sector-relative + stabilité 5 ans)
- Risk: 20% (éviter perte permanente de capital)
- Smart Money: 0% (indicateur only)
- Insider: 0% (tie-breaker only)

Usage:
    from src.scoring import calculate_all_scores_v30
    # ou
    from src.scoring import calculate_all_scores  # alias par défaut
    
    df = calculate_all_scores(df)

v2.3 (⚠️ DEPRECATED - Legacy)
-----------------------------
Approche factorielle avec seuils absolus et Smart Money/Insider dans le score.

⚠️  Déprécié en faveur de v3.0. Gardé uniquement pour rétrocompatibilité.

Usage (déprécié):
    from src.scoring import calculate_composite_score  # ⚠️ deprecated
    
Migration:
    AVANT:  calculate_composite_score(df)
    APRÈS:  calculate_all_scores_v30(df)

"""

import warnings

# =============================================================================
# v3.0 BUFFETT-QUANT (ACTIF - RECOMMANDÉ)
# =============================================================================

from .quality_v30 import (
    QualityScorerV30,
    QualityScoreV30,
    score_quality_v30,
)

from .value_v30 import (
    ValueScorerV30,
    ValueScoreV30,
    score_value_v30,
)

from .risk_v30 import (
    RiskScorerV30,
    RiskScoreV30,
    score_risk_v30,
)

from .composite_v30 import (
    CompositeScorerV30,
    CompositeResultV30,
    calculate_all_scores_v30,
)

# =============================================================================
# ALIAS PAR DÉFAUT → v3.0
# =============================================================================

# Pour les nouveaux usages, pointer vers v3.0
calculate_all_scores = calculate_all_scores_v30

# =============================================================================
# v2.3 LEGACY (⚠️ DEPRECATED)
# =============================================================================

def _deprecated_import_warning(name: str):
    """Émet un warning pour les imports legacy."""
    warnings.warn(
        f"'{name}' est déprécié (v2.3). "
        f"Utiliser les scorers v3.0: calculate_all_scores_v30()",
        DeprecationWarning,
        stacklevel=3
    )

# Importer depuis les fichiers legacy (qui re-exportent depuis les originaux)
# Cela garde la rétrocompatibilité tout en signalant la dépréciation
try:
    from .legacy.value_v23 import ValueScorer, score_value
    from .legacy.quality_v23 import QualityScorer, score_quality
    from .legacy.risk_v23 import RiskScorer, score_risk
    from .legacy.composite_v23 import CompositeScorer, calculate_composite_score
except ImportError:
    # Fallback: importer directement depuis les anciens fichiers
    # (au cas où legacy/ n'existe pas encore)
    from .value_composite import ValueScorer, score_value
    from .quality_composite import QualityScorer, score_quality
    from .risk_score import RiskScorer, score_risk
    from .composite import CompositeScorer, calculate_composite_score

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # === v3.0 Buffett-Quant (RECOMMANDÉ) ===
    "QualityScorerV30",
    "QualityScoreV30",
    "score_quality_v30",
    "ValueScorerV30",
    "ValueScoreV30",
    "score_value_v30",
    "RiskScorerV30",
    "RiskScoreV30",
    "score_risk_v30",
    "CompositeScorerV30",
    "CompositeResultV30",
    "calculate_all_scores_v30",
    
    # === Alias par défaut → v3.0 ===
    "calculate_all_scores",
    
    # === v2.3 Legacy (⚠️ DEPRECATED) ===
    "ValueScorer",       # ⚠️ deprecated
    "score_value",       # ⚠️ deprecated
    "QualityScorer",     # ⚠️ deprecated
    "score_quality",     # ⚠️ deprecated
    "RiskScorer",        # ⚠️ deprecated
    "score_risk",        # ⚠️ deprecated
    "CompositeScorer",   # ⚠️ deprecated
    "calculate_composite_score",  # ⚠️ deprecated
]

# =============================================================================
# VERSION INFO
# =============================================================================

__version__ = "3.0.0"
__version_name__ = "Buffett-Quant"
__legacy_version__ = "2.3.0"
