"""SmartMoney Scoring Package

VERSIONS DISPONIBLES:
=====================

v3.0 "Buffett-Quant" (RECOMMANDÉ)
---------------------------------
Philosophie: Traduire la mentalité Buffett en facteurs mesurables.

- Quality: Sector-relative + stabilité 5 ans
- Value: Cross-section + Margin of Safety
- Risk: Éviter la perte permanente de capital
- Smart Money: 0% (indicateur only)
- Insider: 0% (tie-breaker only)

Usage:
    from src.scoring import calculate_all_scores_v30
    df = calculate_all_scores_v30(df)

v2.3 (Legacy)
-------------
Approche factorielle classique avec seuils absolus.

Usage:
    from src.scoring import calculate_composite_score
    df = calculate_composite_score(df)

"""

# =============================================================================
# v3.0 BUFFETT-QUANT (RECOMMANDÉ)
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
# v2.3 LEGACY (Rétrocompatibilité)
# =============================================================================

from .value_composite import ValueScorer, score_value
from .quality_composite import QualityScorer, score_quality
from .risk_score import RiskScorer, score_risk
from .composite import CompositeScorer, calculate_composite_score

# =============================================================================
# ALIAS PAR DÉFAUT → v3.0
# =============================================================================

# Pour les nouveaux usages, pointer vers v3.0
calculate_all_scores = calculate_all_scores_v30

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # === v3.0 Buffett-Quant ===
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
    
    # === Alias par défaut ===
    "calculate_all_scores",
    
    # === v2.3 Legacy ===
    "ValueScorer",
    "score_value",
    "QualityScorer",
    "score_quality",
    "RiskScorer",
    "score_risk",
    "CompositeScorer",
    "calculate_composite_score",
]

# =============================================================================
# VERSION INFO
# =============================================================================

__version__ = "3.0.0"
__version_name__ = "Buffett-Quant"
