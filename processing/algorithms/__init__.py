# -*- coding: utf-8 -*-
"""Processing algorithms for Ethiopia Data Loader."""

from .clip_by_state import ClipByStateAlgorithm
from .buffer_analysis import BufferAnalysisAlgorithm
from .statistics_algorithm import StatisticsAlgorithm
from .join_attributes import JoinAttributesAlgorithm

__all__ = [
    'ClipByStateAlgorithm',
    'BufferAnalysisAlgorithm',
    'StatisticsAlgorithm',
    'JoinAttributesAlgorithm'
]
