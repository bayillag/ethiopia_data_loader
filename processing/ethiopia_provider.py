# -*- coding: utf-8 -*-
"""
Ethiopia Data Processing Provider for QGIS Processing Framework.

Registers Ethiopia-specific algorithms with QGIS Processing toolbox.
"""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

from .algorithms.clip_by_state import ClipByStateAlgorithm
from .algorithms.buffer_analysis import BufferAnalysisAlgorithm
from .algorithms.statistics_algorithm import StatisticsAlgorithm
from .algorithms.join_attributes import JoinAttributesAlgorithm


class EthiopiaProcessingProvider(QgsProcessingProvider):
    """Processing provider for Ethiopia Data Loader algorithms."""

    def __init__(self):
        """Initialize the provider."""
        super().__init__()

    def id(self):
        """Return the unique provider ID."""
        return 'sudandataloader'

    def name(self):
        """Return the human-readable provider name."""
        return 'Sudan Data Loader'

    def longName(self):
        """Return the long name for the provider."""
        return 'Sudan Data Loader Processing Tools'

    def icon(self):
        """Return the provider icon."""
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'icon.png'
        )
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return super().icon()

    def loadAlgorithms(self):
        """Load all algorithms for this provider."""
        self.addAlgorithm(ClipByStateAlgorithm())
        self.addAlgorithm(BufferAnalysisAlgorithm())
        self.addAlgorithm(StatisticsAlgorithm())
        self.addAlgorithm(JoinAttributesAlgorithm())
