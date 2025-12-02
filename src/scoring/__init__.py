"""SmartMoney v2.3 — Scoring Package

Modules de scoring Buffett-style:
- value_composite: FCF yield, EV/EBIT, MoS
- quality_composite: ROIC, marges, FCF growth, discipline
- risk_score: Levier, coverage, volatilité (INVERSÉ)
- composite: Agrégation finale avec poids v2.3
"""

from .value_composite import ValueScorer, score_value
from .quality_composite import QualityScorer, score_quality
from .risk_score import RiskScorer, score_risk
from .composite import CompositeScorer, calculate_composite_score

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
