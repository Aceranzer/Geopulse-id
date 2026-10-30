"""
GeoPulse-id package
"""
from src.topsis import shannon_entropy_weights, topsis, TOPSISSolver
from src.xai import (
    boundary_cases,
    cluster_assignment_contributions,
    exact_shapley_topsis,
    explain_local,
    kmeans_feature_importance,
    safe_baseline,
    shapley_global_importance,
    topsis_reference_score,
)

__all__ = [
    "shannon_entropy_weights",
    "topsis",
    "TOPSISSolver",
    "topsis_reference_score",
    "safe_baseline",
    "exact_shapley_topsis",
    "shapley_global_importance",
    "explain_local",
    "kmeans_feature_importance",
    "cluster_assignment_contributions",
    "boundary_cases",
]
