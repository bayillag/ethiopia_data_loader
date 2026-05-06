# -*- coding: utf-8 -*-
"""World Bank Development Indicators Integration for Ethiopia Data Loader."""

from .wb_client import WorldBankClient
from .wb_browser import WorldBankBrowserDialog

__all__ = ['WorldBankClient', 'WorldBankBrowserDialog']
