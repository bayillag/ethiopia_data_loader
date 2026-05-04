# -*- coding: utf-8 -*-
"""AI and Smart Features for Ethiopia Data Loader."""

from .nl_query import NaturalLanguageQuery, NLQueryDialog
from .smart_reports import SmartReportGenerator
from .anomaly_detection import AnomalyDetector
from .predictions import PredictionEngine
from .recommendations import RecommendationEngine

__all__ = [
    'NaturalLanguageQuery',
    'NLQueryDialog',
    'SmartReportGenerator',
    'AnomalyDetector',
    'PredictionEngine',
    'RecommendationEngine'
]
