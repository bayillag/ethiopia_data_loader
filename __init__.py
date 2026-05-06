# -*- coding: utf-8 -*-
"""
Ethiopia Data Downloader - QGIS 4 Plugin

This plugin loads Ethiopia administrative boundary data from GeoPackages
and applies QML styles.
"""


def classFactory(iface):
    """
    Load the EthiopiaDataLoader class from the plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    :returns: EthiopiaDataLoader instance
    """
    from .ethiopia_data_loader import EthiopiaDataLoader
    return EthiopiaDataLoader(iface)
