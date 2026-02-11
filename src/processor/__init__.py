"""processor package init"""

from .windowing import aggregate_trades as aggregate_window, compute_score_a
from .ingest_pipeline import IngestPipeline

__all__ = ["aggregate_window", "compute_score_a", "IngestPipeline"]
